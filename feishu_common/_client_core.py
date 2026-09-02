#!/usr/bin/env python3
"""
_client_core.py -- 飞书客户端核心 HTTP 与鉴权能力
"""

import json
import os
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from ._config_loader import (
    load_credentials_data,
    load_default_identity,
    load_granted_scopes,
    resolve_config_path,
    resolve_token_cache_path,
    safe_write_json,
)
from ._endpoint_registry import (
    ENDPOINT_REGISTRY,
    APP_ONLY,
    USER_ONLY,
    ADMIN_APPROVAL_SCOPES,
)
from ._permission_helper import (
    is_permission_error as _is_permission_error,
    extract_missing_scopes as _extract_missing_scopes,
    format_permission_hint as _format_permission_hint,
)

# 常见飞书错误码中文提示
FEISHU_ERROR_CODES = {
    99991672: "权限不足，请在飞书开放平台开通所需权限后重新发布应用",
    2091001: "参数无效，请检查请求参数的类型或格式",
    2091002: "资源不存在，请检查 token 是否正确",
    2091003: "妙记转写中，请稍后重试",
    2091004: "资源已删除",
    2091005: "无权访问该资源，请检查分享设置或权限配置",
    1062009: "文件大小与声明不一致",
    131005: "Wiki 节点不存在",
    1254041: "Excel 数据区域非法",
    1254004: "Spreadsheet token 无效",
    1254036: "Sheet ID 无效",
    1254001: "参数错误",
    1770003: "文档不存在或无权限",
    1770004: "文档块不存在",
    1000001: "access_token 无效或已过期，请清除 token 缓存后重试",
    112005: "app 身份权限不足",
    1130001: "应用未开通该权限",
}

DEFAULT_TIMEOUT = 30

BRAND_DOMAINS = {
    "feishu": "https://open.feishu.cn",
    "lark": "https://open.larksuite.com",
}


class FeishuClientCore:
    """飞书 API 客户端（纯 Python 标准库）"""

    def __init__(self, credentials_path=None):
        self.creds = self._load_credentials(credentials_path)
        self.brand = self.creds.get("brand", "feishu")
        self.base_url = BRAND_DOMAINS.get(self.brand, BRAND_DOMAINS["feishu"])
        self.app_id = self.creds["appId"]
        self.app_secret = self.creds["appSecret"]
        self.user_access_token = self.creds.get("userAccessToken")
        self._token = None
        self._token_expire = 0
        self._cloud_token_manager = self._create_cloud_token_manager()

    def _create_cloud_token_manager(self):
        """云模式下创建 CloudTokenManager；Bitable 基础设施不存在时返回 None。"""
        infra = self._load_bitable_infrastructure()
        if not infra:
            print(
                "client_core: cloud_mode_enabled=false, "
                "reason=Bitable infrastructure not found in settings.json; "
                "run python3 feishu-setup/setup_bitable_infrastructure.py to enable cloud mode",
                file=sys.stderr,
            )
            return None
        from .cloud_token_manager import CloudTokenManager

        def _persist(event, **extra):
            self._persist_token_history(event, **extra)

        return CloudTokenManager(
            app_id=self.app_id,
            app_secret=self.app_secret,
            bitable_infra=infra,
            instance_id=os.environ.get("FEISHU_INSTANCE_ID", ""),
            persist_history=_persist,
        )

    @staticmethod
    def _load_credentials(path):
        """读取应用凭证（自动通过 resolver 定位 credentials.json）"""
        data, resolved_path = load_credentials_data(path)
        for key in ("appId", "appSecret"):
            if key not in data or not data[key]:
                raise RuntimeError(f"Missing '{key}' in credentials file")
            if data[key] in ("REDACTED", "xxx"):
                raise RuntimeError(
                    f"凭证文件 {resolved_path or 'credentials.json'} 中的 {key} 仍为占位符 '{data[key]}'，"
                    f"请填入真实的飞书应用凭证。"
                    f"获取方式：飞书开放平台 → 应用详情 → 凭证与基础信息"
                )
        data["_source_path"] = str(resolved_path) if resolved_path else None
        return data

    def set_user_access_token(self, token):
        """显式覆盖 user_access_token。"""
        self.user_access_token = token

    def _log_token_event(self, message):
        """输出 token 相关诊断信息到 stderr。"""
        print(message, file=sys.stderr)

    @staticmethod
    def _token_fingerprint(token):
        """返回 token 的脱敏指纹，用于日志排查。"""
        if not token or len(token) < 12:
            return "<empty>"
        return f"{token[:6]}...{token[-4:]}"

    def _log_token_state(self, prefix):
        """记录当前 token 状态（脱敏）。"""
        now = time.time()
        at = self.user_access_token
        at_expire = self.creds.get("userTokenExpire", 0)
        # 云模式下 refresh_token 只存在于 Bitable，本地凭证中无 RT 字段。
        cloud_enabled = bool(self._cloud_token_manager)
        rt = None
        rt_expire = 0
        peek_error = None
        bitable_app_token = None
        bitable_table_id = None
        if cloud_enabled:
            bitable_app_token = self._cloud_token_manager.bitable_app_token
            bitable_table_id = self._cloud_token_manager.bitable_table_id
            try:
                rt = self._cloud_token_manager.peek_refresh_token()
                rt_expire = self._cloud_token_manager.get_refresh_token_expire()
            except Exception as e:
                rt = None
                rt_expire = 0
                peek_error = str(e)
        parts = [
            f"{prefix}:",
            f"cloud_mode_enabled={cloud_enabled}",
            f"AT={self._token_fingerprint(at)}",
            f"AT_expire_in={int(at_expire - now) if at_expire else 'unknown'}s",
            f"RT={self._token_fingerprint(rt)}",
            f"RT_expire_in={int(rt_expire - now) if rt_expire else 'unknown'}s",
        ]
        if bitable_app_token:
            parts.append(f"bitable_app_token={bitable_app_token}")
        if bitable_table_id:
            parts.append(f"bitable_table_id={bitable_table_id}")
        if peek_error:
            parts.append(f"peek_error={peek_error}")
        self._log_token_event(" ".join(parts))

    def _persist_token_history(
        self, event, *, old_at=None, new_at=None, old_rt=None, new_rt=None, **extra
    ):
        """持久化 token 事件历史到 JSONL 文件。

        默认只记录 token fingerprint；设置环境变量 FEISHU_TOKEN_HISTORY_FULL=1
        后才会写入完整 token 值（仅用于极端调试场景，注意文件安全）。
        历史记录失败不应影响主流程。
        """
        try:
            from ._config_loader import append_token_history
        except Exception:
            return

        def _mask(token):
            if not token:
                return ""
            if os.environ.get("FEISHU_TOKEN_HISTORY_FULL") == "1":
                return str(token)
            return self._token_fingerprint(token)

        cloud_enabled = bool(self._cloud_token_manager)
        bitable_app_token = None
        bitable_table_id = None
        if cloud_enabled:
            bitable_app_token = self._cloud_token_manager.bitable_app_token
            bitable_table_id = self._cloud_token_manager.bitable_table_id
        record = {
            "ts": time.time(),
            "pid": os.getpid(),
            "event": event,
            "app_id": self.app_id,
            "identity": self.creds.get("_identity", "user"),
            "cloud_mode_enabled": cloud_enabled,
            "bitable_app_token": bitable_app_token,
            "bitable_table_id": bitable_table_id,
            "old_at_fp": _mask(old_at),
            "new_at_fp": _mask(new_at),
            "old_rt_fp": _mask(old_rt),
            "new_rt_fp": _mask(new_rt),
            "source_path": self.creds.get("_source_path", ""),
        }
        record.update(extra)
        try:
            append_token_history(record)
        except Exception:
            pass

    def _save_user_token(
        self, access_token, refresh_token, expires_in, refresh_expires_in, scopes=None
    ):
        """云模式下保存 user_access_token 到 credentials.json 缓存，并将 refresh_token 写入 Bitable。

        credentials.json 只保留 userAccessToken 作为非权威缓存；refresh_token 的唯一持久化
        位置是 Bitable token_backup 表。

        Returns:
            bitable_record_id: 如果 refresh_token 被写入 Bitable，返回对应 record_id；否则返回 None。
        """
        from ._config_loader import FEISHU_CONFIG_DIR_ENV, get_runtime_config_dir

        platform_active = get_runtime_config_dir() is not None
        env_override = bool(os.environ.get(FEISHU_CONFIG_DIR_ENV))

        if platform_active or env_override:
            creds_write_path = resolve_config_path("credentials.json", for_write=True)
        else:
            source_path = self.creds.get("_source_path")
            creds_write_path = (
                Path(source_path)
                if source_path
                else resolve_config_path("credentials.json", for_write=True)
            )

        old_at = self.creds.get("userAccessToken")
        self._persist_token_history(
            "save_attempt",
            old_at=old_at,
            new_at=access_token,
            new_rt=refresh_token,
            at_expire_in=expires_in,
            rt_expire_in=refresh_expires_in,
        )

        try:
            with open(creds_write_path, "r", encoding="utf-8") as f:
                creds = json.load(f)
        except Exception:
            creds = dict(self.creds)

        now = time.time()
        bitable_record_id = None

        # 云模式下 refresh_token 的唯一持久化位置是 Bitable，必须先写入成功。
        # 若 Bitable 写入失败，则本次保存整体失败，避免本地 credentials 与新 RT 不同步。
        if refresh_token and self._cloud_token_manager:
            bitable_record_id = self._cloud_token_manager.save_refresh_token(
                refresh_token, now + refresh_expires_in
            )
            print(
                "client_core: refresh_token persisted to Bitable "
                f"(record_id={bitable_record_id}, "
                f"app_token={self._cloud_token_manager.bitable_app_token}, "
                f"table_id={self._cloud_token_manager.bitable_table_id}, "
                f"rt_fingerprint={self._token_fingerprint(refresh_token)})",
                file=sys.stderr,
            )

        creds["userAccessToken"] = access_token
        creds["userTokenExpire"] = now + expires_in
        if scopes is not None:
            creds["userScopes"] = sorted(set(scopes))
        # 云模式下 refresh_token 不写入本地文件（仅在 Bitable 持久化）；
        # 非云模式下 refresh_token 需要写入 credentials.json 供本地 OAuth 刷新。
        if self._cloud_token_manager:
            creds.pop("refreshToken", None)
            creds.pop("refreshTokenExpire", None)
        else:
            if refresh_token:
                creds["refreshToken"] = refresh_token
                creds["refreshTokenExpire"] = now + refresh_expires_in
            else:
                creds["refreshToken"] = ""
                creds.pop("refreshTokenExpire", None)
        creds.pop("_source_path", None)

        safe_write_json(creds_write_path, creds, mode=0o600)

        self._persist_token_history(
            "save_success",
            old_at=old_at,
            new_at=access_token,
            new_rt=refresh_token,
            at_expire_in=expires_in,
            rt_expire_in=refresh_expires_in,
            bitable_record_id=bitable_record_id,
        )

        self.user_access_token = access_token
        self.creds["userAccessToken"] = access_token
        self.creds["userTokenExpire"] = now + expires_in
        if scopes is not None:
            self.creds["userScopes"] = sorted(set(scopes))
        # 非云模式保留内存中的 refresh_token，供后续本地刷新使用
        if self._cloud_token_manager:
            self.creds.pop("refreshToken", None)
            self.creds.pop("refreshTokenExpire", None)
        else:
            if refresh_token:
                self.creds["refreshToken"] = refresh_token
                self.creds["refreshTokenExpire"] = now + refresh_expires_in
            else:
                self.creds["refreshToken"] = ""
                self.creds.pop("refreshTokenExpire", None)
        return bitable_record_id

    def _load_bitable_infrastructure(self):
        """从当前配置目录的 settings.json 加载 Bitable 基础设施配置。

        优先使用 resolver 解析的 canonical settings.json；若不存在，则回退到
        credentials.json 源目录下的 settings.json，保持对自定义凭证路径的兼容。
        """
        # 1) canonical 路径（resolver 会根据平台/env覆盖选择正确的目录）
        settings_path = resolve_config_path("settings.json", for_write=False)
        if not settings_path.exists():
            # 2) fallback：credentials.json 所在目录
            source_path = self.creds.get("_source_path")
            if source_path:
                settings_path = Path(source_path).parent / "settings.json"
                if not settings_path.exists():
                    return None
            else:
                return None

        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                settings = json.load(f)
        except Exception:
            return None

        infra = settings.get("infrastructure", {}).get("bitable", {})
        app_token = infra.get("app_token")
        table_id = infra.get("tables", {}).get("token_backup")
        if not app_token or not table_id:
            return None
        return {"app_token": app_token, "table_id": table_id}

    def _parse_error_body(self, body):
        """尝试解析飞书错误响应体，返回可读取的 dict。"""
        if not body:
            return None
        try:
            return json.loads(body)
        except Exception:
            return None

    def _ensure_token(self):
        """获取 tenant_access_token，支持文件缓存"""
        now = time.time()
        if self._token and now < self._token_expire - 60:
            return self._token

        cache_file = resolve_token_cache_path()
        if cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    cache = json.load(f)
                if (
                    cache.get("app_id") == self.app_id
                    and cache.get("brand") == self.brand
                    and cache.get("expire", 0) > now + 60
                ):
                    self._token = cache["token"]
                    self._token_expire = cache["expire"]
                    print(
                        "client_core: using cached tenant_access_token "
                        f"(expires_in={int(self._token_expire - now)}s)",
                        file=sys.stderr,
                    )
                    return self._token
            except Exception as e:
                print(
                    f"client_core: token_cache_read_failed for tenant_access_token: {e}",
                    file=sys.stderr,
                )

        url = f"{self.base_url}/open-apis/auth/v3/tenant_access_token/internal"
        body = json.dumps(
            {"app_id": self.app_id, "app_secret": self.app_secret}
        ).encode()
        req = urllib.request.Request(
            url, data=body, headers={"Content-Type": "application/json"}
        )
        try:
            resp = urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT)
            data = json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            raise RuntimeError(
                f"Failed to get tenant_access_token: HTTP {e.code}"
            ) from e

        if data.get("code") != 0:
            raise RuntimeError(f"Token request failed: {data}")

        self._token = data["tenant_access_token"]
        self._token_expire = now + data.get("expire", 7200)
        write_path = resolve_token_cache_path(for_write=True)
        safe_write_json(
            write_path,
            {
                "app_id": self.app_id,
                "brand": self.brand,
                "token": self._token,
                "expire": self._token_expire,
            },
        )
        return self._token

    # ── 本地（非云）模式 Token 刷新（从云平台版合并回）──────────────

    def _reload_user_token_from_disk(self):
        """刷新失败后重读凭证文件，兜底并发刷新或跨进程更新。"""
        from ._config_loader import FEISHU_CONFIG_DIR_ENV, get_runtime_config_dir

        candidate_paths = []
        platform_active = get_runtime_config_dir() is not None
        env_override = bool(os.environ.get(FEISHU_CONFIG_DIR_ENV))

        source_path = self.creds.get("_source_path")
        if platform_active or env_override:
            # 平台/env 覆盖模式下，先检查 canonical 路径，再检查 fallback 来源
            candidate_paths.append(resolve_config_path("credentials.json"))
            if source_path:
                candidate_paths.append(Path(source_path))
        else:
            # 本地模式下，source_path 就是当前使用的凭证文件路径，只检查它。
            # 避免测试或本地多进程场景下误读到其他位置（如项目根目录）的旧 token。
            if source_path:
                candidate_paths.append(Path(source_path))
            else:
                candidate_paths.append(resolve_config_path("credentials.json"))

        now = time.time()
        seen = set()
        for path in candidate_paths:
            if not path:
                continue
            path = Path(path)
            path_key = str(path)
            if path_key in seen or not path.exists():
                continue
            seen.add(path_key)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    creds = json.load(f)
            except Exception:
                continue

            disk_token = creds.get("userAccessToken") or creds.get("user_access_token")
            disk_expire = creds.get("userTokenExpire", 0)
            # 提前 30 分钟认为 token 有效，减少多个进程同时触发刷新的概率
            if disk_token and (not disk_expire or now < disk_expire - 1800):
                creds["_source_path"] = str(path)
                self.creds.update(creds)
                self.user_access_token = disk_token
                self._log_token_event(f"user token reloaded from disk: {path}")
                return disk_token
        return None

    # ── Token 刷新 ────────────────────────────────────────────────

    def _retry_refresh_after_failure(self):
        """刷新失败后尝试从磁盘重新加载并再次刷新（竞态兜底）。"""
        pid = os.getpid()
        self._log_token_event(f"refresh: pid={pid} attempting to recover from disk after failure")

        # 最多尝试 3 次，带随机抖动，避免多个失败进程同时醒来再次竞争
        for attempt in range(1, 4):
            reloaded = self._reload_user_token_from_disk()
            if reloaded:
                self._log_token_event(
                    f"refresh: pid={pid} recovered via disk reload on attempt {attempt}"
                )
                return reloaded

            if attempt < 3:
                wait = 1.0 + random.random() * 2.0  # 1.0 ~ 3.0 秒
                self._log_token_event(
                    f"refresh: pid={pid} no valid token on disk, waiting {wait:.2f}s (attempt {attempt}/3)"
                )
                time.sleep(wait)

        self._log_token_event(f"refresh: pid={pid} recovery failed, no valid token found on disk after 3 attempts")
        return None

    def _refresh_user_token(self):
        """用 refresh_token 刷新 user_access_token。成功返回新 token，失败返回 None。"""
        pid = os.getpid()
        self._log_token_event(f"refresh: pid={pid}")
        self._log_token_state("refresh")

        # 刷新前先从磁盘读取最新凭证，减少多进程竞态：
        # 如果其他进程已经刷新过，磁盘上的 AT 可能已有效，直接用新的；
        # 即使 AT 仍过期，磁盘上的 RT 也可能已被更新为最新值。
        source_path = self.creds.get("_source_path")
        if source_path:
            self._log_token_event(f"refresh: reloading credentials from {source_path} before API call")
            reloaded_at = self._reload_user_token_from_disk()
            if reloaded_at:
                self._log_token_event(
                    f"refresh: disk has valid AT={self._token_fingerprint(reloaded_at)}, skipping API call"
                )
                return reloaded_at
            self._log_token_state("refresh after reload")
        else:
            self._log_token_event("refresh: no _source_path, skipping pre-reload from disk")

        refresh_token = self.creds.get("refreshToken")
        if not refresh_token:
            self._log_token_event("refresh: no refresh_token available")
            return None

        # 检查 refresh_token 是否过期（0 表示未知有效期，仍尝试刷新）
        refresh_expire = self.creds.get("refreshTokenExpire", 0)
        if refresh_expire > 0 and time.time() > refresh_expire:
            self._log_token_event(f"refresh: refresh_token expired {int(time.time() - refresh_expire)}s ago")
            return None

        self._log_token_event(
            f"refresh: pid={pid} calling Feishu API with RT={self._token_fingerprint(refresh_token)}"
        )

        url = f"{self.base_url}/open-apis/authen/v2/oauth/token"
        body = json.dumps({
            "grant_type": "refresh_token",
            "client_id": self.app_id,
            "client_secret": self.app_secret,
            "refresh_token": refresh_token,
        }).encode()
        req = urllib.request.Request(url, data=body, headers={
            "Content-Type": "application/json",
        })
        data = None
        try:
            resp = urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT)
            data = json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            # HTTP 4xx/5xx 时读取响应体，获取具体错误码
            body = ""
            try:
                body = e.read().decode("utf-8")
            except Exception:
                pass
            self._log_token_event(
                f"user token refresh failed: HTTP {e.code} body={body}"
            )
            data = self._parse_error_body(body)
        except Exception as e:
            self._log_token_event(f"user token refresh failed: network/request error: {e}")

        if not data:
            return self._retry_refresh_after_failure()

        code = data.get("code")
        msg = data.get("msg", "")
        has_access = bool(data.get("access_token"))
        has_refresh = bool(data.get("refresh_token"))
        expires_in = data.get("expires_in", 7200)
        refresh_expires_in = data.get("refresh_token_expires_in", 2592000)
        self._log_token_event(
            f"refresh: pid={pid} API response code={code} msg={msg} "
            f"has_access_token={has_access} has_refresh_token={has_refresh} "
            f"expires_in={expires_in} refresh_expires_in={refresh_expires_in}"
        )

        if code != 0:
            self._log_token_event(f"user token refresh failed: code={code} msg={msg}")
            return self._retry_refresh_after_failure()

        new_token = data.get("access_token", "")
        new_refresh = data.get("refresh_token", "")
        scope_text = data.get("scope", "")
        scopes = [item for item in scope_text.split() if item]

        if not new_token:
            self._log_token_event("user token refresh failed: response missing access_token")
            return self._retry_refresh_after_failure()

        if not new_refresh:
            # 飞书 v2 OAuth 刷新成功后通常应返回新 RT；若缺失，可能是并发导致
            # 另一个进程已经消耗了旧 RT 并写入了新 RT。优先从磁盘重载。
            self._log_token_event(
                "refresh: API returned new AT but no new RT, old RT likely consumed; "
                "trying disk reload"
            )
            reloaded = self._reload_user_token_from_disk()
            if reloaded:
                self._log_token_event("refresh: recovered new RT from disk after API omitted it")
                return reloaded

            # 磁盘上也没有新 RT：保存新 AT，但清空 RT，避免下次用已失效的 RT
            self._log_token_event(
                "refresh: no new RT on disk; saving AT but clearing RT, re-authorization will be required"
            )
            self._save_user_token(new_token, "", expires_in, refresh_expires_in, scopes=scopes)
            return new_token

        self._save_user_token(new_token, new_refresh, expires_in, refresh_expires_in, scopes=scopes)
        return new_token

    # ── Token 获取 ────────────────────────────────────────────────
    def _ensure_user_token(self):
        """获取 user_access_token，云模式下由 CloudTokenManager 从 Bitable 管理。"""
        now = time.time()
        token_expire = self.creds.get("userTokenExpire", 0)

        # 若内存/凭证缓存中的 user_access_token 仍有效（提前 30 分钟刷新），直接返回
        if self.user_access_token and (not token_expire or now < token_expire - 1800):
            print(
                f"client_core: using cached user_access_token "
                f"(expires_in={int(token_expire - now) if token_expire else 'unknown'}s, "
                f"fingerprint={self._token_fingerprint(self.user_access_token)})",
                file=sys.stderr,
            )
            return self.user_access_token

        print(
            "client_core: cached user_access_token missing/expired, delegating to CloudTokenManager",
            file=sys.stderr,
        )

        if not self._cloud_token_manager:
            # 非云模式（本地/普通部署）：走本地 OAuth 刷新逻辑，
            # 基于 credentials.json 中的 refresh_token 刷新 user_access_token。
            refreshed = self._refresh_user_token()
            if refreshed:
                return refreshed
            if self.user_access_token:
                raise RuntimeError(
                    "user_access_token 已过期且 refresh_token 刷新失败。\n"
                    "请重新授权：python3 feishu-auth/auth_get_user_token.py\n"
                    "或临时切换到应用身份：在 settings.json 中设置 \"default_identity\": \"tenant\""
                )
            raise RuntimeError(
                "user_access_token 未配置，但当前默认身份为 user。\n"
                "请先完成用户授权：python3 feishu-auth/auth_get_user_token.py\n"
                "或切换到应用身份：在 settings.json 中设置 \"default_identity\": \"tenant\""
            )

        token = self._cloud_token_manager.get_user_access_token()
        # 把 CloudTokenManager 返回的有效 user_access_token 缓存到 credentials.json，
        # 避免每个新进程都重复刷新，减少 refresh_token 消耗。
        expire = self._cloud_token_manager.get_user_access_token_expire()
        expires_in = max(0, int(expire - time.time())) if expire else 7200
        try:
            self._save_user_token(token, "", expires_in, 0)
            print(
                "client_core: cached refreshed user_access_token to credentials.json "
                f"(cache_write_succeeded=true, expires_in={expires_in}s)",
                file=sys.stderr,
            )
            self._persist_token_history("cache_at_succeeded", expires_in=expires_in)
        except Exception as e:
            # 本地缓存失败不应阻塞 API 调用，但应留下痕迹
            self.user_access_token = token
            self.creds["userAccessToken"] = token
            self.creds["userTokenExpire"] = time.time() + expires_in
            print(
                f"client_core: cache_write_succeeded=false, failed to cache AT to credentials.json: {e}",
                file=sys.stderr,
            )
            self._persist_token_history("cache_at_failed", error=str(e))
        return token

    def _resolve_and_get_token(self):
        """根据身份解析策略返回合适的 token（用于不走 _request 的场景如二进制下载）。"""
        caller_name = self._detect_caller_method()
        use_user = self._resolve_identity(caller_name, None)
        return self._ensure_user_token() if use_user else self._ensure_token()

    def _token_for_method(self, method_name, use_user_token=None):
        """为指定 registry 方法名解析 token（供 shortcut 等非 mixin 场景复用）。"""
        use_user = self._resolve_identity(method_name, use_user_token)
        return self._ensure_user_token() if use_user else self._ensure_token()

    def _request_raw(self, method, path_or_url, query=None, method_name=None):
        """发送请求并返回原始 urllib 响应对象（供二进制下载等复杂场景使用）。

        Args:
            method: HTTP 方法
            path_or_url: API path（以 / 开头）或完整 URL
            query: URL query 参数
            method_name: 对应 registry 方法名，用于身份解析
        Returns:
            urllib response 对象
        """
        use_user = self._resolve_identity(
            method_name or self._detect_caller_method(), None
        )
        token = self._ensure_user_token() if use_user else self._ensure_token()

        if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
            url = path_or_url
        else:
            url = f"{self.base_url}{path_or_url}"
        if query:
            url += "?" + urllib.parse.urlencode(query, doseq=True)

        req = urllib.request.Request(
            url, method=method, headers={"Authorization": f"Bearer {token}"}
        )
        try:
            return urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT)
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"HTTP {e.code} | URL: {url}") from e
        except urllib.error.URLError as e:
            raise RuntimeError(f"Network error: {e.reason} | URL: {url}") from e

    def _download_url(self, url, save_path, method_name=None):
        """统一二进制下载入口：按 registry / 默认身份解析 token，流式写入文件。

        Args:
            url: 完整下载 URL（含 base_url 与 path）
            save_path: 本地保存路径
            method_name: 对应 registry 方法名，用于身份解析
        Returns:
            保存后的文件路径
        """
        resp = self._request_raw("GET", url, method_name=method_name)
        save = Path(save_path)
        save.parent.mkdir(parents=True, exist_ok=True)
        with open(save, "wb") as f:
            f.write(resp.read())
        return str(save)

    def _detect_caller_method(self):
        """Walk up the call stack to find the public mixin method name."""
        for depth in range(2, 5):
            try:
                frame = sys._getframe(depth)
            except ValueError:
                break
            name = frame.f_code.co_name
            if not name.startswith("_") and name in ENDPOINT_REGISTRY:
                return name
        return None

    def _resolve_identity(self, method_name, use_user_token):
        """Resolve which token to use for an API call.

        Args:
            method_name: The mixin method name (e.g., "document_create")
            use_user_token: True (explicit user), False (explicit app),
                            None (auto-resolve)

        Returns:
            True to use user token, False to use app token
        """
        default_identity = load_default_identity()
        default_user = default_identity == "user"

        entry = ENDPOINT_REGISTRY.get(method_name)

        # --- Priority 1: Explicit caller override ---
        if use_user_token is not None:
            if entry is None:
                resolved = use_user_token
                reason = f"explicit use_user_token={use_user_token}"
            else:
                identity = entry["identity"]
                if use_user_token and identity == APP_ONLY:
                    raise RuntimeError(
                        f"'{method_name}' 是飞书 API 限制的仅应用身份接口（APP_ONLY），不支持 user_access_token。\n"
                        f"请移除 use_user_token=True 参数，让系统自动使用应用身份调用。\n"
                        f"如果应用身份权限不足，需要在飞书开放平台给自建应用开通对应权限。"
                    )
                if not use_user_token and identity == USER_ONLY:
                    raise RuntimeError(
                        f"'{method_name}' 是仅用户身份接口（USER_ONLY），不支持 tenant_access_token。\n"
                        f"请确保凭证文件中 user_access_token 有效，"
                        f"或运行 python3 feishu-auth/auth_get_user_token.py 重新授权。"
                    )
                resolved = use_user_token
                reason = f"explicit use_user_token={use_user_token}"
            print(
                f"Resolved identity for '{method_name}': {'user' if resolved else 'tenant'} (reason: {reason})",
                file=sys.stderr,
            )
            return resolved

        # --- Priority 2: Registry-driven resolution ---
        if entry is not None:
            identity = entry["identity"]

            if identity == APP_ONLY:
                resolved = False
                reason = "endpoint is APP_ONLY"
                print(
                    f"Resolved identity for '{method_name}': tenant (reason: {reason})",
                    file=sys.stderr,
                )
                return False
            if identity == USER_ONLY:
                resolved = True
                reason = "endpoint is USER_ONLY"
                print(
                    f"Resolved identity for '{method_name}': user (reason: {reason})",
                    file=sys.stderr,
                )
                return True

            # BOTH: check granted scopes
            granted = load_granted_scopes()
            scopes = entry["scopes"]
            tenant_scopes = set(scopes.get("tenant", []))
            user_scopes = set(scopes.get("user", []))

            tenant_ok = not tenant_scopes or tenant_scopes.issubset(granted["tenant"])
            user_ok = not user_scopes or user_scopes.issubset(granted["user"])

            if user_ok and not tenant_ok:
                resolved = True
                reason = "user scope available, tenant scope missing"
                print(
                    f"Resolved identity for '{method_name}': user (reason: {reason})",
                    file=sys.stderr,
                )
                return True
            if tenant_ok and not user_ok:
                resolved = False
                reason = "tenant scope available, user scope missing"
                print(
                    f"Resolved identity for '{method_name}': tenant (reason: {reason})",
                    file=sys.stderr,
                )
                return False
            # Both OK or neither OK: use global default
            resolved = default_user
            reason = f"default_identity={default_identity}, both scopes available"
            print(
                f"Resolved identity for '{method_name}': {'user' if resolved else 'tenant'} (reason: {reason})",
                file=sys.stderr,
            )
            return resolved

        # --- Priority 3: Not in registry, use global default ---
        resolved = default_user
        reason = f"default_identity={default_identity}, no registry entry"
        print(
            f"Resolved identity for '{method_name}': {'user' if resolved else 'tenant'} (reason: {reason})",
            file=sys.stderr,
        )
        return resolved

    def _check_required_scopes(self, method_name, use_user_token):
        """调用前权限预检：根据 registry 和当前身份检查 scope 是否就绪。

        缺失时抛出包含缺失 scope、当前身份、解决路径的 RuntimeError。
        若本地没有任何权限数据（permissions.json / credentials.userScopes 均不存在），
        则跳过预检，避免在尚未完成授权的环境中阻塞调用。
        """
        if not method_name:
            return
        entry = ENDPOINT_REGISTRY.get(method_name)
        if not entry:
            return

        identity_type = "user" if use_user_token else "tenant"
        required = set(entry.get("scopes", {}).get(identity_type, []))
        if not required:
            return

        granted = load_granted_scopes()
        granted_set = granted.get(identity_type, set())

        # 对 user 身份，同时以 credentials.json 中实际 OAuth 授权返回的 userScopes 为准
        has_user_scope_data = False
        if use_user_token:
            cred_user_scopes = set(self.creds.get("userScopes", []))
            if cred_user_scopes:
                has_user_scope_data = True
            granted_set = granted_set | cred_user_scopes

        # 没有任何权限数据时跳过预检（常见于测试环境或尚未授权）
        from ._config_loader import PERMISSIONS_FILE

        has_permission_file = PERMISSIONS_FILE.exists()
        if not has_permission_file and not (use_user_token and has_user_scope_data):
            return

        missing = required - granted_set
        if not missing:
            return

        identity_label = (
            "用户身份 (user_access_token)"
            if use_user_token
            else "应用身份 (tenant_access_token)"
        )
        scope_list = ", ".join(sorted(missing))
        existing = ", ".join(sorted(granted_set)) or "无"

        # 判断是“权限未开通”还是“权限未请求”
        tenant_scopes_declared = set(entry.get("scopes", {}).get("tenant", []))
        user_scopes_declared = set(entry.get("scopes", {}).get("user", []))
        if use_user_token:
            requested = set(self.creds.get("userScopes", []))
            not_requested = missing - requested
            if not_requested:
                reason = (
                    f"当前 OAuth 授权未请求这些 scope。\n"
                    f"解决: 重新运行 python3 feishu-auth/auth_get_user_token.py，"
                    f"确保请求 scope 包含: {scope_list}"
                )
            else:
                reason = (
                    f"这些 scope 已在 OAuth 中请求，但可能未在飞书开放平台开通或管理员未审批。\n"
                    f"解决: 在飞书开放平台 → 权限管理 → 申请并发布这些权限，然后重新授权。"
                )
        else:
            reason = (
                f"应用身份缺少这些 scope。\n"
                f"解决: 在飞书开放平台 → 权限管理 → 申请并发布这些权限，"
                f"然后运行 python3 feishu-auth/auth_sync_permissions.py 刷新 permissions.json。"
            )

        raise RuntimeError(
            f"权限预检失败: '{method_name}' 需要以下 scope: {scope_list}\n"
            f"当前身份: {identity_label}\n"
            f"已有 scopes: {existing}\n"
            f"{reason}\n"
            f"如希望使用另一身份调用，可修改 settings.json 中的 default_identity。"
        )

    def _admin_approval_hint(self, method_name, use_user_token):
        """API 权限错误后补充诊断：检查所需 scope 是否包含已知需管理员审批的 scope。"""
        if not method_name:
            return ""
        entry = ENDPOINT_REGISTRY.get(method_name)
        if not entry:
            return ""

        identity_type = "user" if use_user_token else "tenant"
        required = set(entry.get("scopes", {}).get(identity_type, []))
        admin_required = required & ADMIN_APPROVAL_SCOPES
        if not admin_required:
            return ""

        scopes = ", ".join(sorted(admin_required))
        return (
            f"\n注意: 该操作需要以下可能需管理员审批的 scope: {scopes}\n"
            f"permissions.json 中声明了这些权限，但飞书平台可能尚未完成管理员审批。\n"
            f"解决: 在飞书开放平台 → 权限管理 → 找到这些权限 → 申请并联系管理员审批，"
            f"审批通过后重新发布应用并重新授权。"
        )

    def _request(
        self,
        method,
        path,
        body=None,
        query=None,
        headers=None,
        use_user_token=None,
        max_retries=0,
        stream_to=None,
        method_name=None,
    ):
        """发送 HTTP 请求并解析响应

        Args:
            use_user_token: 是否使用 user_access_token（Contact 等敏感接口需要）
            max_retries: 最大重试次数，默认 0（不重试）。仅对 5xx 和网络错误重试。
            stream_to: 如果提供路径，将响应内容写入该文件（用于下载场景）
            method_name: 指定 registry 方法名，用于非 mixin 调用场景（如内部管理接口）
        """
        if use_user_token is None:
            caller_name = method_name or self._detect_caller_method()
            use_user_token = self._resolve_identity(caller_name, None)
        else:
            caller_name = method_name or self._detect_caller_method()

        # 调用前权限预检
        self._check_required_scopes(caller_name, use_user_token)

        if use_user_token:
            token = self._ensure_user_token()
        else:
            token = self._ensure_token()
        url = f"{self.base_url}{path}"
        if query:
            url += "?" + urllib.parse.urlencode(query, doseq=True)

        req_body = None
        if body is not None:
            if isinstance(body, bytes):
                req_body = body
            else:
                req_body = json.dumps(body, ensure_ascii=False).encode("utf-8")

        resp_data = None
        for attempt in range(max_retries + 1):
            req_headers = {"Authorization": f"Bearer {token}"}
            if headers:
                req_headers.update(headers)
            if req_body is not None and not isinstance(body, bytes):
                req_headers.setdefault("Content-Type", "application/json")

            req = urllib.request.Request(
                url, data=req_body, headers=req_headers, method=method
            )
            try:
                resp = urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT)
                if stream_to:
                    save = Path(stream_to)
                    save.parent.mkdir(parents=True, exist_ok=True)
                    with open(save, "wb") as f:
                        f.write(resp.read())
                    return str(save)
                resp_data = resp.read().decode("utf-8")
                if attempt > 0:
                    print(
                        f"client_core: request succeeded after {attempt + 1} attempts "
                        f"({method} {url})",
                        file=sys.stderr,
                    )
                break
            except urllib.error.HTTPError as e:
                if e.code >= 500 and attempt < max_retries:
                    print(
                        f"client_core: retrying request attempt {attempt + 2}/{max_retries + 1} "
                        f"for {method} {url}: HTTP {e.code}",
                        file=sys.stderr,
                    )
                    time.sleep(1 * (1 << attempt))
                    continue
                resp_data = e.read().decode("utf-8")
                try:
                    err_json = json.loads(resp_data)
                    biz_code = err_json.get("code", "")
                    biz_msg = FEISHU_ERROR_CODES.get(biz_code, err_json.get("msg", ""))
                    detail = (
                        f"[{biz_code}] {biz_msg}"
                        if biz_msg
                        else f"[{biz_code}] {err_json.get('msg', '')}"
                    )
                except json.JSONDecodeError:
                    detail = resp_data[:200]
                hint = ""
                if biz_code and _is_permission_error(biz_code):
                    missing = (
                        _extract_missing_scopes(err_json)
                        if isinstance(err_json, dict)
                        else []
                    )
                    hint = "\n\n" + _format_permission_hint(
                        self.app_id, missing, biz_code
                    )
                    hint += self._admin_approval_hint(caller_name, use_user_token)
                elif e.code == 400 and ("权限" in detail or "未开通" in detail):
                    hint = self._admin_approval_hint(caller_name, use_user_token)
                raise RuntimeError(
                    f"HTTP {e.code} | {detail} | URL: {url}{hint}"
                    f"{' (after ' + str(attempt + 1) + ' attempts)' if attempt > 0 else ''}"
                ) from e
            except urllib.error.URLError as e:
                if attempt < max_retries:
                    print(
                        f"client_core: retrying request attempt {attempt + 2}/{max_retries + 1} "
                        f"for {method} {url}: network error {e.reason}",
                        file=sys.stderr,
                    )
                    time.sleep(1 * (1 << attempt))
                    continue
                raise RuntimeError(
                    f"Network error: {e.reason} | URL: {url}"
                    f"{' (after ' + str(attempt + 1) + ' attempts)' if attempt > 0 else ''}"
                ) from e

        try:
            data = json.loads(resp_data)
        except json.JSONDecodeError:
            return resp_data
        code = data.get("code")
        if code is not None and code != 0:
            biz_msg = FEISHU_ERROR_CODES.get(code, data.get("msg", ""))
            detail = (
                f"[{code}] {biz_msg}" if biz_msg else f"[{code}] {data.get('msg', '')}"
            )
            hint = ""
            if _is_permission_error(code):
                missing = (
                    _extract_missing_scopes(data) if isinstance(data, dict) else []
                )
                hint = "\n\n" + _format_permission_hint(self.app_id, missing, code)
                hint += self._admin_approval_hint(caller_name, use_user_token)
            elif "权限" in detail or "未开通" in detail:
                hint = self._admin_approval_hint(caller_name, use_user_token)
            raise RuntimeError(f"{detail} | URL: {url}{hint}")
        return data.get("data", data)

    def _paginate(
        self,
        method,
        path,
        *,
        items_key="items",
        page_token_key="page_token",
        has_more_key="has_more",
        max_results=None,
        page_token_in="query",
        page_size=50,
        extra_query=None,
        extra_body=None,
        use_user_token=None,
    ):
        """通用自动分页辅助方法

        Args:
            method: HTTP 方法
            path: API 路径
            items_key: 响应中 items 的键名
            page_token_key: 响应中 page_token 的键名
            has_more_key: 响应中 has_more 的键名
            max_results: 最大返回条数，None 表示不限制
            page_token_in: page_token 放在 "query" 还是 "body"
            page_size: 每页条数
            extra_query: 额外的 query 参数
            extra_body: 额外的 body 参数
            use_user_token: 是否使用 user_access_token

        Returns:
            list of items
        """
        results = []
        page_token = None
        page_count = 0
        max_pages = 10000
        while page_count < max_pages:
            page_count += 1
            if page_token_in == "body":
                body = dict(extra_body or {})
                body["page_size"] = page_size
                if page_token:
                    body["page_token"] = page_token
                data = self._request(
                    method,
                    path,
                    body=body,
                    query=extra_query,
                    use_user_token=use_user_token,
                )
            else:
                query = dict(extra_query or {})
                query["page_size"] = page_size
                if page_token:
                    query["page_token"] = page_token
                data = self._request(
                    method,
                    path,
                    query=query,
                    body=extra_body,
                    use_user_token=use_user_token,
                )
            items = data.get(items_key, [])
            results.extend(items)
            if page_count == 1 or page_count % 10 == 0:
                print(
                    f"client_core: pagination fetched page {page_count}, "
                    f"total items so far: {len(results)}",
                    file=sys.stderr,
                )
            if max_results is not None and len(results) >= max_results:
                return results[:max_results]
            if not data.get(has_more_key):
                break
            page_token = data.get(page_token_key)
            if not page_token:
                print(
                    "client_core: pagination breaking because page_token is empty "
                    f"while {has_more_key} is still true (page {page_count})",
                    file=sys.stderr,
                )
                break
        if page_count >= max_pages:
            print(
                f"client_core: pagination reached max_pages={max_pages}, returning {len(results)} items",
                file=sys.stderr,
            )
        return results

    def clear_token_cache(self):
        """清除本地 token 缓存"""
        self._token = None
        self._token_expire = 0
        try:
            resolve_token_cache_path().unlink()
        except FileNotFoundError:
            pass
