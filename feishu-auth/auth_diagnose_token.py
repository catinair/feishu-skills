#!/usr/bin/env python3
"""
auth_diagnose_token.py -- 飞书 token 状态诊断（云模式）

读取当前 credentials.json 状态以及 Bitable 中的 refresh_token，输出 access_token /
refresh_token 的过期时间、指纹，便于排查 token 刷新问题。

用法：
    python3 feishu-auth/auth_diagnose_token.py
    python3 feishu-auth/auth_diagnose_token.py --refresh  # 触发一次刷新并观察日志
"""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from feishu_common import create_client, cli_run, log_config_paths
from feishu_common._config_loader import resolve_config_path, load_credentials_data, resolve_token_history_path


def _fingerprint(token):
    if not token or len(token) < 12:
        return "<empty>"
    return f"{token[:6]}...{token[-4:]}"


def main():
    parser = argparse.ArgumentParser(description="飞书 token 状态诊断")
    parser.add_argument("--refresh", action="store_true", help="触发一次 user_access_token 刷新")
    args = parser.parse_args()

    log_config_paths()

    creds_path = resolve_config_path("credentials.json", for_write=True)
    history_path = resolve_token_history_path(for_write=True)
    print(f"\n凭证文件路径: {creds_path}", file=sys.stderr)
    print(f"token 历史文件路径: {history_path}", file=sys.stderr)

    try:
        data, resolved_path = load_credentials_data()
    except Exception as e:
        print(f"读取凭证失败: {e}", file=sys.stderr)
        sys.exit(1)

    client = create_client()

    now = time.time()
    at = data.get("userAccessToken")
    at_expire = data.get("userTokenExpire", 0)
    scopes = data.get("userScopes", [])

    cloud_enabled = bool(client._cloud_token_manager)
    bitable_app_token = None
    bitable_table_id = None
    rt = None
    rt_expire = 0
    rt_read_error = None
    if cloud_enabled:
        bitable_app_token = client._cloud_token_manager.bitable_app_token
        bitable_table_id = client._cloud_token_manager.bitable_table_id
        try:
            rt = client._cloud_token_manager.peek_refresh_token()
            rt_expire = client._cloud_token_manager.get_refresh_token_expire()
        except Exception as e:
            rt_read_error = str(e)
            print(f"从 Bitable 读取 refresh_token 失败: {e}", file=sys.stderr)
    else:
        print("警告: 未配置 Bitable 基础设施，无法读取 refresh_token", file=sys.stderr)

    print(f"resolved_read_path: {resolved_path}", file=sys.stderr)
    print(f"access_token:  {_fingerprint(at)}", file=sys.stderr)
    print(f"  expires_in:  {int(at_expire - now) if at_expire else 'unknown'} seconds", file=sys.stderr)
    print(f"  expired:     {at_expire > 0 and now > at_expire}", file=sys.stderr)
    print(f"refresh_token: {_fingerprint(rt)}", file=sys.stderr)
    print(f"  source:      Bitable", file=sys.stderr)
    print(f"user_scopes:   {len(scopes)} items", file=sys.stderr)

    result = {
        "credentials_path": str(creds_path),
        "token_history_path": str(history_path),
        "resolved_read_path": str(resolved_path) if resolved_path else None,
        "cloud_mode_enabled": cloud_enabled,
        "bitable_app_token": bitable_app_token,
        "bitable_table_id": bitable_table_id,
        "access_token_fingerprint": _fingerprint(at),
        "access_token_expires_in": int(at_expire - now) if at_expire else None,
        "access_token_expired": at_expire > 0 and now > at_expire,
        "refresh_token_fingerprint": _fingerprint(rt),
        "refresh_token_source": "bitable",
        "refresh_token_expires_in": int(rt_expire - now) if rt_expire else None,
        "refresh_token_read_error": rt_read_error,
        "user_scope_count": len(scopes),
    }

    if args.refresh:
        print("\n--refresh 已指定，正在触发一次刷新...", file=sys.stderr)
        before_at_expire = client.creds.get("userTokenExpire", 0)
        try:
            new_token = client._ensure_user_token()
            result["refresh_triggered"] = True
            result["refresh_succeeded"] = bool(new_token)
            result["after_refresh_access_token_fingerprint"] = _fingerprint(
                client.creds.get("userAccessToken")
            )
            result["after_refresh_access_token_expires_in"] = int(
                client.creds.get("userTokenExpire", 0) - time.time()
            ) if client.creds.get("userTokenExpire") else None
            # 云模式下刷新后本地 credentials.json 仍不保存 refresh_token
            result["after_refresh_refresh_token_source"] = "bitable"
            if client._cloud_token_manager:
                result["refresh_attempts"] = client._cloud_token_manager.get_last_refresh_attempts()
                result["bitable_record_id"] = client._cloud_token_manager.get_last_record_id()
                try:
                    result["after_refresh_refresh_token_fingerprint"] = _fingerprint(
                        client._cloud_token_manager.peek_refresh_token()
                    )
                    result["after_refresh_refresh_token_expires_in"] = int(
                        client._cloud_token_manager.get_refresh_token_expire() - time.time()
                    )
                except Exception as e:
                    result["after_refresh_refresh_token_error"] = str(e)
            # 缓存写回状态：如果 _ensure_user_token 成功且 userTokenExpire 被更新，说明缓存成功
            result["cache_write_status"] = (
                "updated"
                if client.creds.get("userTokenExpire", 0) > before_at_expire
                else "no_change"
            )
        except Exception as e:
            result["refresh_triggered"] = True
            result["refresh_succeeded"] = False
            result["refresh_error"] = str(e)
    else:
        result["refresh_triggered"] = False

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    cli_run(main)
