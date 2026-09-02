#!/usr/bin/env python3
"""Cloud-only token manager for feishu-skills.

In cloud deployments the local overlay filesystem cannot
reliably persist credentials.json. This module treats Feishu Bitable as the
single source of truth for refresh_token:

- Every refresh appends a new record to the Bitable token_backup table.
- Reads always fetch the latest record (sorted by updated_at descending).
- user_access_token is cached in memory until it is close to expiry.

No refresh_token is ever written to local credentials.json.
"""

import json
import os
import random
import sys
import time
import urllib.error
import urllib.request
from typing import Callable, Dict, Optional, Tuple


DEFAULT_TIMEOUT = 30


def _token_fingerprint(token: str) -> str:
    """返回 token 的脱敏指纹，用于日志排查。"""
    if not token or len(token) < 12:
        return "<empty>"
    return f"{token[:6]}...{token[-4:]}"


def _extract_text(field_value):
    """Bitable 文本字段可能返回 [{'text': '...', 'type': 'text'}]，提取纯文本。"""
    if isinstance(field_value, str):
        return field_value
    if isinstance(field_value, list):
        return "".join(
            item.get("text", "") for item in field_value if isinstance(item, dict)
        )
    return ""


class CloudTokenManager:
    """Manages user_access_token with refresh_token stored only in Bitable."""

    def __init__(
        self,
        app_id: str,
        app_secret: str,
        bitable_infra: Dict[str, str],
        *,
        base_url: str = "https://open.feishu.cn",
        instance_id: Optional[str] = None,
        persist_history: Optional[Callable] = None,
    ):
        self.app_id = app_id
        self.app_secret = app_secret
        self.bitable_app_token = bitable_infra["app_token"]
        self.bitable_table_id = bitable_infra["table_id"]
        self.base_url = base_url.rstrip("/")
        self.instance_id = instance_id or os.environ.get("FEISHU_INSTANCE_ID", "")
        self._persist_history = persist_history or (lambda **kwargs: None)

        # In-memory caches
        self._tenant_token: Optional[str] = None
        self._tenant_token_expire: float = 0
        self._user_access_token: Optional[str] = None
        self._user_token_expire: float = 0
        # Diagnostics / last operation metadata
        self._last_record_id: Optional[str] = None
        self._last_refresh_attempts: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_user_access_token(self) -> str:
        """Return a valid user_access_token, refreshing via Bitable if needed."""
        now = time.time()
        if self._user_access_token and (
            not self._user_token_expire or now < self._user_token_expire - 1800
        ):
            print(
                f"cloud_token_manager: using cached user_access_token "
                f"(expires_in={int(self._user_token_expire - now)}s, "
                f"fingerprint={_token_fingerprint(self._user_access_token)})",
                file=sys.stderr,
            )
            return self._user_access_token

        print(
            "cloud_token_manager: cached user_access_token missing/expired, "
            "reading latest refresh_token from Bitable...",
            file=sys.stderr,
        )
        refresh_token = self._read_latest_refresh_token()
        if not refresh_token:
            raise RuntimeError(
                "cloud mode: no refresh_token found in Bitable. "
                "Please authorize first: python3 feishu-auth/auth_get_user_token.py"
            )

        print(
            f"cloud_token_manager: refreshing user_access_token "
            f"(rt_fingerprint={_token_fingerprint(refresh_token)})",
            file=sys.stderr,
        )
        self._last_refresh_attempts = 0
        access_token, new_refresh_token, new_refresh_expire = self._refresh_with_retry(
            refresh_token
        )
        if not new_refresh_token:
            raise RuntimeError(
                "refresh succeeded but Feishu returned no new refresh_token; "
                "aborting to avoid overwriting the existing Bitable record"
            )

        # Append the new refresh_token record to Bitable immediately.
        try:
            record_id = self._append_refresh_token(
                new_refresh_token, new_refresh_expire
            )
        except Exception as e:
            # A new single-use refresh_token was generated but could not be persisted.
            # Make the potential data loss explicit so the AI/user knows to re-authorize.
            print(
                "cloud_token_manager: CRITICAL new refresh_token generated but Bitable append failed "
                f"(rt_fingerprint={_token_fingerprint(new_refresh_token)}): {e}",
                file=sys.stderr,
            )
            self._persist_history(
                event="bitable_append_failed",
                error=str(e),
                rt_fingerprint=_token_fingerprint(new_refresh_token),
            )
            raise RuntimeError(
                "new refresh_token generated but Bitable append failed after retries; "
                "the new single-use refresh_token may be lost. "
                "Please run python3 feishu-auth/auth_get_user_token.py to re-authorize."
            ) from e

        print(
            "cloud_token_manager: user_access_token refreshed and new refresh_token appended to Bitable "
            f"(at_fingerprint={_token_fingerprint(access_token)}, "
            f"new_rt_fingerprint={_token_fingerprint(new_refresh_token)}, "
            f"record_id={record_id})",
            file=sys.stderr,
        )
        return access_token

    def peek_refresh_token(self) -> Optional[str]:
        """Return the latest refresh_token from Bitable without refreshing (diagnostics)."""
        return self._read_latest_refresh_token()

    def save_refresh_token(
        self, refresh_token: str, refresh_token_expire: float
    ) -> None:
        """Persist an initial refresh_token to Bitable (used after OAuth)."""
        self._append_refresh_token(refresh_token, refresh_token_expire)

    def get_user_access_token_expire(self) -> float:
        """Return the cached user_access_token expire timestamp (0 if not cached)."""
        return self._user_token_expire

    def get_refresh_token_expire(self) -> float:
        """Return the latest refresh_token expire timestamp from Bitable (0 if not found)."""
        record = self._read_latest_refresh_token_record()
        if not record:
            return 0.0
        fields = record.get("fields", {})
        expire = fields.get("refresh_token_expire", 0)
        try:
            return float(expire) if expire else 0.0
        except (TypeError, ValueError):
            return 0.0

    def get_last_record_id(self) -> Optional[str]:
        """Return the record_id of the last successful Bitable append (if any)."""
        return self._last_record_id

    def get_last_refresh_attempts(self) -> int:
        """Return the number of attempts used by the last refresh (0 if not refreshed yet)."""
        return self._last_refresh_attempts

    # ------------------------------------------------------------------
    # Feishu API helpers
    # ------------------------------------------------------------------

    def _get_tenant_access_token(self) -> str:
        """Fetch and cache tenant_access_token (needed for Bitable API calls)."""
        now = time.time()
        if self._tenant_token and self._tenant_token_expire > now + 60:
            return self._tenant_token

        url = f"{self.base_url}/open-apis/auth/v3/tenant_access_token/internal"
        body = json.dumps(
            {"app_id": self.app_id, "app_secret": self.app_secret}
        ).encode("utf-8")
        req = urllib.request.Request(
            url, data=body, headers={"Content-Type": "application/json"}, method="POST"
        )

        try:
            resp = urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT)
            data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body_text = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"failed to get tenant_access_token for app_id={self.app_id}: "
                f"HTTP {e.code} {body_text}"
            ) from e

        if data.get("code") != 0:
            raise RuntimeError(
                f"failed to get tenant_access_token for app_id={self.app_id}: "
                f"{data.get('code')} {data.get('msg')}"
            )

        self._tenant_token = data["tenant_access_token"]
        self._tenant_token_expire = now + data.get("expire", 7200)
        return self._tenant_token

    def _refresh_user_token(self, refresh_token: str) -> Tuple[str, str, float]:
        """Call Feishu to refresh user token. Returns (access_token, refresh_token, refresh_expire)."""
        url = f"{self.base_url}/open-apis/authen/v2/oauth/token"
        body = json.dumps(
            {
                "grant_type": "refresh_token",
                "client_id": self.app_id,
                "client_secret": self.app_secret,
                "refresh_token": refresh_token,
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            url, data=body, headers={"Content-Type": "application/json"}, method="POST"
        )

        try:
            resp = urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT)
            data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body_text = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"refresh_user_token failed for app_id={self.app_id}: "
                f"HTTP {e.code} {body_text}"
            ) from e

        # 飞书 OAuth token 接口错误可能使用 OAuth 标准格式（error/error_description）
        # 也可能使用飞书格式（code/msg）。优先识别标准错误。
        if data.get("error"):
            raise RuntimeError(
                f"refresh_user_token failed for app_id={self.app_id}: "
                f"{data.get('error')} - {data.get('error_description', '')}"
            )

        # 飞书 token 接口成功响应有两种形态：
        # 1) 标准 OAuth2 扁平格式：{token_type, access_token, refresh_token, expires_in, ...}
        # 2) 飞书包裹格式：{code: 0, msg: "ok", data: {access_token, ...}}
        # 因此优先取 data.data，不存在时直接使用顶层字段。
        if data.get("code") is not None and data.get("code") != 0:
            raise RuntimeError(
                f"refresh_user_token failed for app_id={self.app_id}: "
                f"{data.get('code')} {data.get('msg')}"
            )

        token_data = data.get("data") if isinstance(data.get("data"), dict) else data
        if not token_data or "access_token" not in token_data:
            raise RuntimeError(
                f"refresh_user_token failed for app_id={self.app_id}: "
                f"response missing access_token, response={data}"
            )
        access_token = token_data["access_token"]
        new_refresh_token = token_data.get("refresh_token", "")
        expires_in = token_data.get("expires_in", 7200)
        refresh_expires_in = token_data.get(
            "refresh_token_expires_in", 604800
        )  # default 7 days (Feishu OAuth actual)

        now = time.time()
        self._user_access_token = access_token
        self._user_token_expire = now + expires_in

        return access_token, new_refresh_token, now + refresh_expires_in

    @staticmethod
    def _is_race_error(error_text: str) -> bool:
        """判断刷新错误是否可能是多实例竞态导致（旧 RT 已被其他实例消费）。"""
        text = error_text.lower()
        indicators = [
            "invalid_grant",
            "invalid refresh_token",
            "invalid_refresh_token",
            "refresh_token invalid",
            "token has been revoked",
            "refresh token has been revoked",
        ]
        return any(ind in text for ind in indicators)

    def _refresh_with_retry(
        self, refresh_token: str, max_attempts: int = 3
    ) -> Tuple[str, str, float]:
        """Refresh with retry on race-induced invalid refresh_token.

        若错误表明旧 RT 可能已被其他实例消费，则重新读取 Bitable 最新记录并重试。
        若 Bitable 中仍无新 RT，则判定为真正的 RT 失效，不再重试。
        """
        last_error: Optional[Exception] = None
        for attempt in range(max_attempts):
            try:
                print(
                    f"cloud_token_manager: refresh attempt {attempt + 1}/{max_attempts}",
                    file=sys.stderr,
                )
                self._last_refresh_attempts = attempt + 1
                return self._refresh_user_token(refresh_token)
            except RuntimeError as e:
                last_error = e
                error_text = str(e)
                is_race = self._is_race_error(error_text)
                print(
                    f"cloud_token_manager: refresh attempt {attempt + 1}/{max_attempts} failed: "
                    f"race={is_race}, error={error_text}",
                    file=sys.stderr,
                )
                if is_race and attempt < max_attempts - 1:
                    print(
                        "cloud_token_manager: refresh race possible, "
                        "re-reading latest refresh_token from Bitable...",
                        file=sys.stderr,
                    )
                    self._persist_history(
                        event="refresh_race_retry",
                        attempt=attempt + 1,
                        error=error_text,
                    )
                    time.sleep(random.uniform(0.2, 0.8) * (attempt + 1))
                    latest = self._read_latest_refresh_token()
                    if latest and latest != refresh_token:
                        print(
                            f"cloud_token_manager: found newer refresh_token in Bitable "
                            f"(fingerprint={_token_fingerprint(latest)}), will retry",
                            file=sys.stderr,
                        )
                        refresh_token = latest
                        continue
                    print(
                        "cloud_token_manager: Bitable still holds the same refresh_token; "
                        "treating as permanently revoked.",
                        file=sys.stderr,
                    )
                    self._persist_history(
                        event="refresh_token_revoked",
                        attempt=attempt + 1,
                        error=error_text,
                    )
                    print(
                        "cloud_token_manager: refresh_token 已过期或无效，"
                        "请重新授权：python3 feishu-auth/auth_device_flow.py --begin --qr --json",
                        file=sys.stderr,
                    )
                    raise RuntimeError(
                        "refresh_token 已过期或无效，请重新授权："
                        "python3 feishu-auth/auth_device_flow.py --begin --qr --json"
                    ) from last_error
                raise
        raise RuntimeError(
            f"refresh_token 刷新失败（已重试 {max_attempts} 次），"
            "请重新授权：python3 feishu-auth/auth_device_flow.py --begin --qr --json"
        ) from last_error

    # ------------------------------------------------------------------
    # Bitable helpers
    # ------------------------------------------------------------------

    def _bitable_request(
        self, method: str, path: str, body: Optional[Dict] = None
    ) -> Dict:
        """Call Bitable API with tenant token."""
        token = self._get_tenant_access_token()
        url = f"{self.base_url}{path}"
        data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body else None
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            method=method,
        )

        try:
            resp = urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT)
            return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body_text = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Bitable API error: {e.code} {body_text}") from e

    def _read_latest_refresh_token_record(self) -> Optional[dict]:
        """Return the latest refresh_token record (dict) for this app_id from Bitable."""
        path = (
            f"/open-apis/bitable/v1/apps/{self.bitable_app_token}"
            f"/tables/{self.bitable_table_id}/records/search"
        )
        body = {
            "filter": {
                "conjunction": "and",
                "conditions": [
                    {
                        "field_name": "app_id",
                        "operator": "is",
                        "value": [self.app_id],
                    }
                ],
            }
        }

        result = self._bitable_request("POST", path, body)
        if result.get("code") != 0:
            raise RuntimeError(
                f"failed to search Bitable records for app_id={self.app_id} "
                f"(app_token={self.bitable_app_token}, table_id={self.bitable_table_id}): "
                f"{result.get('code')} {result.get('msg')}"
            )

        items = result.get("data", {}).get("items", [])
        if not items:
            return None

        # Sort by refresh_token_expire descending (newer tokens have later
        # expiration) and take the latest. Fallback to updated_at if needed.
        sorted_items = sorted(
            items,
            key=lambda item: (
                item.get("fields", {}).get("refresh_token_expire") or 0,
                item.get("fields", {}).get("updated_at") or 0,
            ),
            reverse=True,
        )
        return sorted_items[0]

    def _read_latest_refresh_token(self) -> Optional[str]:
        """Return the latest refresh_token for this app_id from Bitable."""
        latest = self._read_latest_refresh_token_record()
        if not latest:
            return None

        fields = latest.get("fields", {})
        refresh_token = _extract_text(fields.get("refresh_token", ""))

        self._persist_history(
            event="bitable_read_latest",
            record_id=latest.get("record_id"),
            updated_at=fields.get("updated_at"),
        )
        return refresh_token or None

    def _append_refresh_token(
        self, refresh_token: str, refresh_token_expire: float, max_attempts: int = 3
    ) -> str:
        """Append a new refresh_token record to Bitable with retry.

        这是云模式下 refresh_token 唯一持久化位置，写入失败会导致新 RT 丢失、
        后续刷新失败，因此必须重试。

        Returns:
            新创建记录的 record_id。
        """
        path = (
            f"/open-apis/bitable/v1/apps/{self.bitable_app_token}"
            f"/tables/{self.bitable_table_id}/records"
        )
        fields = {
            "app_id": self.app_id,
            "refresh_token": refresh_token,
            "refresh_token_expire": int(refresh_token_expire),
            "updated_at": int(time.time() * 1000),
            "updated_by_pid": str(os.getpid()),
            "instance_id": self.instance_id,
        }

        last_error: Optional[Exception] = None
        last_status: str = "unknown"
        for attempt in range(max_attempts):
            try:
                result = self._bitable_request("POST", path, {"fields": fields})
                if result.get("code") != 0:
                    last_status = f"{result.get('code')} {result.get('msg')}"
                    raise RuntimeError(
                        f"failed to append refresh_token to Bitable: {last_status}"
                    )
                record_id = result.get("data", {}).get("record", {}).get("record_id")
                self._last_record_id = record_id
                self._persist_history(
                    event="bitable_append",
                    record_id=record_id,
                    app_token=self.bitable_app_token,
                    table_id=self.bitable_table_id,
                )
                print(
                    "cloud_token_manager: appended refresh_token to Bitable "
                    f"(record_id={record_id}, app_token={self.bitable_app_token}, "
                    f"table_id={self.bitable_table_id})",
                    file=sys.stderr,
                )
                return record_id
            except Exception as e:
                last_error = e
                last_status = str(e)
                print(
                    f"cloud_token_manager: append refresh_token to Bitable failed "
                    f"(attempt {attempt + 1}/{max_attempts}): {e}",
                    file=sys.stderr,
                )
                if attempt < max_attempts - 1:
                    time.sleep(random.uniform(0.5, 1.5) * (attempt + 1))

        raise last_error or RuntimeError(
            f"failed to append refresh_token to Bitable after {max_attempts} attempts: "
            f"last_status={last_status}"
        )
