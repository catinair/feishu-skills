#!/usr/bin/env python3
"""
Device Flow 用户授权脚本
替代原有的 Authorization Code Flow，无需重定向 URL，适用于云端/沙箱环境。

与现有授权体系的兼容性：
  - 复用 FeishuClient / CloudTokenManager 进行 token 持久化
  - 复用 _auto_populate_settings / _auto_sync_permissions / write_default_risk_policy
  - 仅替换了"获取 token"的方式（Device Flow 替代 Authorization Code Flow）

用法:
  发起授权（输出链接 + 可选二维码）:
    python3 auth_device_flow.py --begin [--qr] [--scopes "scope1 scope2"] [--json]

  轮询获取 token 并持久化（用户确认授权后运行）:
    python3 auth_device_flow.py --poll [--json]

  仅轮询获取 token，不持久化（调试用）:
    python3 auth_device_flow.py --poll --no-save [--json]

  查看当前状态:
    python3 auth_device_flow.py --status [--json]
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))
from feishu_common import cli_run, print_json, write_default_risk_policy
from feishu_common._config_loader import (
    get_config_context,
    resolve_config_path,
    get_config_dir,
    safe_write_json,
    load_credentials_data,
    get_runtime_config_dir,
)

# ── 默认权限 ──────────────────────────────────────────────

DEFAULT_SCOPES = [
    "offline_access",
    "auth:user.id:read",
    "im:message",
    "im:chat",
    "docx:document",
    "docx:document:readonly",
    "sheets:spreadsheet",
    "drive:file:upload",
    "bitable:app",
    "calendar:calendar:read",
    "contact:user.base:readonly",
    "wiki:wiki:readonly",
    "base:block:create",
    "sheets:spreadsheet:create",
    "space:folder:create",
]

# ── 状态文件 ──────────────────────────────────────────────


def _state_path():
    return get_config_dir(for_write=True) / "device_flow_state.json"


# ── 工具函数 ──────────────────────────────────────────────


def _accounts_base(brand):
    return (
        "https://accounts.feishu.cn"
        if brand == "feishu"
        else "https://accounts.larksuite.com"
    )


def _open_base(brand):
    return (
        "https://open.feishu.cn" if brand == "feishu" else "https://open.larksuite.com"
    )


def _post_form(url, data, auth=None):
    encoded = urllib.parse.urlencode(data).encode("utf-8")
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    if auth:
        headers["Authorization"] = auth
    req = urllib.request.Request(url, data=encoded, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        return {"error": f"http_{e.code}", "error_description": body}


# ── 发起授权 ──────────────────────────────────────────────


def cmd_begin(scopes, generate_qr, json_output):
    creds_data, _ = load_credentials_data()
    brand = creds_data.get("brand", "feishu")
    app_id = creds_data["appId"]
    app_secret = creds_data["appSecret"]

    import base64

    basic_auth = "Basic " + base64.b64encode(f"{app_id}:{app_secret}".encode()).decode()

    url = f"{_accounts_base(brand)}/oauth/v1/device_authorization"
    resp = _post_form(
        url,
        {
            "client_id": app_id,
            "scope": " ".join(scopes),
        },
        auth=basic_auth,
    )

    if "error" in resp and "device_code" not in resp:
        if json_output:
            print_json(
                {"ok": False, "error": resp.get("error_description", resp["error"])}
            )
        else:
            print(
                f"授权发起失败: {resp.get('error_description', resp['error'])}",
                file=sys.stderr,
            )
        sys.exit(1)

    state = {
        "device_code": resp["device_code"],
        "interval": resp.get("interval", 5),
        "expires_in": resp.get("expires_in", 300),
        "brand": brand,
    }
    sp = _state_path()
    sp.parent.mkdir(parents=True, exist_ok=True)
    # 先删旧文件，避免 overlay FS 上 os.replace 替换已有文件静默失效
    sp.unlink(missing_ok=True)
    safe_write_json(sp, state)

    verification_url = resp.get(
        "verification_uri_complete", resp.get("verification_uri", "")
    )
    sep = "&" if "?" in verification_url else "?"
    verification_url = f"{verification_url}{sep}from=feishu-skills"

    user_code = resp.get("user_code", "N/A")
    expires_in = resp["expires_in"]

    if json_output:
        print_json(
            {
                "ok": True,
                "verification_url": verification_url,
                "user_code": user_code,
                "expires_in": expires_in,
                "state_path": str(sp),
            }
        )
    else:
        print(f"验证链接: {verification_url}")
        print(f"授权码:   {user_code}")
        print(f"有效期:   {expires_in}s ({expires_in // 60} 分钟)")
        print(f"状态文件: {sp}")

    if generate_qr:
        try:
            import qrcode

            qr_path = sp.with_suffix(".png")
            img = qrcode.make(verification_url)
            img.save(str(qr_path))
            if json_output:
                print_json({"qr_path": str(qr_path)})
            else:
                print(f"二维码:   {qr_path}")
        except ImportError:
            if not json_output:
                print(
                    "(二维码生成需要 qrcode 库: pip install qrcode[pil])",
                    file=sys.stderr,
                )


# ── 轮询 Token ────────────────────────────────────────────


def _poll_device_token(creds_data, state, json_output):
    """轮询获取 token，返回 (access_token, refresh_token, scope_text, user_scopes)"""
    brand = state.get("brand", creds_data.get("brand", "feishu"))
    app_id = creds_data["appId"]
    app_secret = creds_data["appSecret"]
    device_code = state["device_code"]
    interval = state["interval"]
    expires_in = state["expires_in"]

    deadline = time.time() + expires_in
    cur_interval = interval
    attempt = 0
    token_url = f"{_open_base(brand)}/open-apis/authen/v2/oauth/token"

    while time.time() < deadline:
        attempt += 1
        time.sleep(cur_interval)
        resp = _post_form(
            token_url,
            {
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                "device_code": device_code,
                "client_id": app_id,
                "client_secret": app_secret,
            },
        )

        code = resp.get("code", -1)
        error = resp.get("error", "")

        if code == 0 and resp.get("access_token"):
            access_token = resp["access_token"]
            refresh_token = resp.get("refresh_token", "")
            scope_text = resp.get("scope", "")
            user_scopes = sorted({s for s in scope_text.split() if s})
            # 使用 API 真实过期时间，而非硬编码默认值
            token_expires_in = resp.get("expires_in", 7200)
            refresh_token_expires_in = resp.get("refresh_token_expires_in", 604800)
            return (
                access_token,
                refresh_token,
                scope_text,
                user_scopes,
                attempt,
                token_expires_in,
                refresh_token_expires_in,
            )

        elif error == "authorization_pending":
            if not json_output:
                print(f"  [{attempt}] 等待用户确认...", flush=True)
            continue
        elif error == "slow_down":
            cur_interval = min(cur_interval + 5, 60)
            if not json_output:
                print(f"  [{attempt}] slow_down, 间隔增至 {cur_interval}s", flush=True)
        else:
            raise RuntimeError(
                f"{error}: {resp.get('error_description', resp.get('msg', ''))}"
            )

    raise RuntimeError("授权超时，用户未在有效期内确认")


def _verify_token(access_token, brand):
    """调用 user_info 验证 token 有效性，返回 user_info dict 或 None"""
    url = f"{_open_base(brand)}/open-apis/authen/v1/user_info"
    req = urllib.request.Request(
        url, headers={"Authorization": f"Bearer {access_token}"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("code") == 0:
                return data.get("data", {})
    except Exception:
        pass
    return None


def _cleanup_state():
    sp = _state_path()
    sp.unlink(missing_ok=True)
    sp.with_suffix(".png").unlink(missing_ok=True)


def cmd_poll(json_output, save=True):
    sp = _state_path()
    if not sp.exists():
        msg = "未找到授权状态文件，请先运行 --begin"
        if json_output:
            print_json({"ok": False, "error": msg})
        else:
            print(msg, file=sys.stderr)
        sys.exit(1)

    with open(sp) as f:
        state = json.load(f)

    creds_data, creds_source_path = load_credentials_data()
    creds_write_path = resolve_config_path("credentials.json", for_write=True)

    # 轮询获取 token
    (
        access_token,
        refresh_token,
        scope_text,
        user_scopes,
        attempts,
        expires_in,
        refresh_expires_in,
    ) = _poll_device_token(creds_data, state, json_output)

    # 验证 token
    user_info = _verify_token(
        access_token, state.get("brand", creds_data.get("brand", "feishu"))
    )
    if user_info is None:
        msg = "token 验证失败"
        if json_output:
            print_json({"ok": False, "error": msg})
        else:
            print(msg, file=sys.stderr)
        sys.exit(1)

    if not save:
        _cleanup_state()
        if json_output:
            print_json(
                {
                    "ok": True,
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "scope": scope_text,
                    "user_name": user_info.get("name", ""),
                    "attempts": attempts,
                    "saved": False,
                }
            )
        else:
            print(f"授权成功 (尝试 {attempts} 次)")
            print(f"用户:     {user_info.get('name', '未知')}")
            print(f"scope:    {scope_text}")
            print(f"(未持久化，--no-save 模式)")
        return

    # ── 持久化（复用现有体系）──
    from feishu_common import FeishuClient

    # 先创建 client 以获取 CloudTokenManager
    client = FeishuClient(str(creds_write_path))
    creds_write_path = resolve_config_path("credentials.json", for_write=True)

    ticket = client._token_fingerprint(access_token)
    print(f"正在保存 user_access_token {ticket}...", file=sys.stderr)

    # 保存 token（走 CloudTokenManager → bitable + credentials.json）
    # 使用 _poll_device_token 从 API 返回中取到的真实过期时间
    bitable_record_id = client._save_user_token(
        access_token, refresh_token, expires_in, refresh_expires_in, scopes=user_scopes
    )

    if not creds_source_path:
        creds_source_path = creds_write_path
    client = FeishuClient(str(creds_write_path))

    # 自动填充 settings
    from auth_get_user_token import _auto_populate_settings

    settings_ok, settings_err = _auto_populate_settings(client, creds_source_path)

    # 自动同步权限
    from auth_sync_permissions import fetch_tenant_scopes, build_permissions_payload

    permissions_path = resolve_config_path("permissions.json", for_write=True)
    permissions_ok, permissions_err = False, None
    try:
        tenant_scopes = fetch_tenant_scopes(client)
        payload = build_permissions_payload(tenant_scopes, user_scopes or [])
        safe_write_json(permissions_path, payload)
        print(
            f"   权限已自动同步到 {permissions_path}（tenant={len(tenant_scopes)}, user={len(user_scopes or [])}）",
            file=sys.stderr,
        )
        permissions_ok = True
    except Exception as e:
        print(f"   ⚠ 自动同步 permissions 失败: {e}", file=sys.stderr)
        permissions_err = str(e)

    # 风险策略
    risk_policy_created = write_default_risk_policy()
    if risk_policy_created:
        print(f"   已自动生成默认 risk_policy.json（user 模式）", file=sys.stderr)

    _cleanup_state()

    cloud_manager = client._cloud_token_manager
    result = {
        "ok": True,
        "token_path": str(creds_write_path),
        "expires_in": expires_in,
        "refresh_expires_in": refresh_expires_in,
        "scopes": user_scopes,
        "cloud_mode_enabled": bool(cloud_manager),
        "bitable_app_token": cloud_manager.bitable_app_token if cloud_manager else None,
        "bitable_table_id": cloud_manager.bitable_table_id if cloud_manager else None,
        "refresh_token_fingerprint": f"{refresh_token[:6]}...{refresh_token[-4:]}"
        if refresh_token and len(refresh_token) >= 12
        else "<empty>",
        "bitable_record_id": bitable_record_id,
        "settings_populated": settings_ok,
        "settings_error": settings_err,
        "permissions_synced": permissions_ok,
        "permissions_error": permissions_err,
        "risk_policy_created": risk_policy_created,
        "user_name": user_info.get("name", ""),
        "attempts": attempts,
    }

    if json_output:
        print_json(result)
    else:
        print(f"\n✅ 授权成功 (尝试 {attempts} 次)")
        print(f"   用户:     {user_info.get('name', '未知')}")
        print(f"   scope:    {scope_text}")
        if refresh_token:
            print(
                f"   refresh_token: 已保存到 Bitable，有效期 {refresh_expires_in} 秒（约 {refresh_expires_in // 86400} 天）"
            )
        else:
            print(f"   refresh_token: 无")
        print(f"   凭证路径: {creds_write_path}")


# ── 状态查询 ──────────────────────────────────────────────


def cmd_status(json_output):
    sp = _state_path()
    if sp.exists():
        with open(sp) as f:
            state = json.load(f)
        remaining = state["expires_in"] - (time.time() - sp.stat().st_mtime)
        if json_output:
            print_json(
                {
                    "ok": True,
                    "active": True,
                    "remaining_seconds": int(max(0, remaining)),
                    "state": state,
                }
            )
        else:
            print(f"有进行中的授权: 剩余约 {int(max(0, remaining))}s")
    else:
        if json_output:
            print_json({"ok": True, "active": False})
        else:
            print("没有进行中的授权")


# ── 入口 ──────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="飞书 Device Flow 用户授权")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--begin", action="store_true", help="发起 Device Authorization")
    group.add_argument("--poll", action="store_true", help="轮询获取 token 并持久化")
    group.add_argument("--status", action="store_true", help="查看当前状态")
    parser.add_argument("--qr", action="store_true", help="生成二维码（需 qrcode 库）")
    parser.add_argument("--scopes", type=str, help="自定义 scope 列表，空格分隔")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")
    parser.add_argument(
        "--no-save", action="store_true", help="仅获取 token，不持久化（调试用）"
    )

    args = parser.parse_args()

    scopes = args.scopes.split() if args.scopes else DEFAULT_SCOPES

    if args.begin:
        cmd_begin(scopes, args.qr, args.json)
    elif args.poll:
        cmd_poll(args.json, save=not args.no_save)
    elif args.status:
        cmd_status(args.json)


if __name__ == "__main__":
    cli_run(main)
