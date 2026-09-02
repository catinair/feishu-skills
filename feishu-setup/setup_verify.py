#!/usr/bin/env python3
"""
setup_verify.py -- 在线验证 token 和 API 端点

作为 setup_check.py 的补充，对已检查就绪的 token 进行联网验证，
确保 token 真的有效（未被吊销、scope 足够）。

用法:
  # 验证所有 token
  python3 setup_verify.py [--json]

  # 仅验证用户 token
  python3 setup_verify.py --user-only [--json]

  # 仅验证租户 token
  python3 setup_verify.py --tenant-only [--json]
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))
from feishu_common import cli_run, print_json
from feishu_common._config_loader import load_credentials_data, get_config_context


# ── 工具函数 ──────────────────────────────────────────────


def _open_base(brand):
    return (
        "https://open.feishu.cn" if brand == "feishu" else "https://open.larksuite.com"
    )


def _accounts_base(brand):
    return (
        "https://accounts.feishu.cn"
        if brand == "feishu"
        else "https://accounts.larksuite.com"
    )


def _get_tenant_token(app_id, app_secret, brand):
    """获取 tenant_access_token"""
    url = f"{_accounts_base(brand)}/oauth/v3/token"
    data = urllib.parse.urlencode(
        {
            "grant_type": "client_credentials",
            "client_id": app_id,
            "client_secret": app_secret,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            if result.get("code") == 0:
                return result["access_token"], None
            return None, f"获取失败: [{result.get('code')}] {result.get('msg', '')}"
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}"
    except Exception as e:
        return None, str(e)


def _call_api(url, token, method="GET"):
    """调用飞书 API，返回 (data, error)"""
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {token}"},
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data, None
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            return json.loads(body), f"HTTP {e.code}"
        except json.JSONDecodeError:
            return None, f"HTTP {e.code}: {body[:200]}"
    except Exception as e:
        return None, str(e)


# ── 验证函数 ──────────────────────────────────────────────


def verify_user_token(access_token, brand):
    """验证 user_access_token 是否有效"""
    url = f"{_open_base(brand)}/open-apis/authen/v1/user_info"
    data, error = _call_api(url, access_token)
    if error:
        return {
            "ok": False,
            "error": error,
            "detail": "token 无效或已吊销",
        }
    if data.get("code") != 0:
        return {
            "ok": False,
            "error": f"[{data.get('code')}] {data.get('msg', '')}",
            "detail": "token 存在但 API 调用失败",
        }
    return {
        "ok": True,
        "user_name": data.get("data", {}).get("name", ""),
        "open_id": data.get("data", {}).get("open_id", ""),
        "detail": "OK",
    }


def verify_tenant_token(app_id, app_secret, brand):
    """验证 tenant_access_token 是否能获取"""
    token, error = _get_tenant_token(app_id, app_secret, brand)
    if error:
        return {
            "ok": False,
            "error": error,
            "detail": "无法获取 tenant_access_token",
        }

    # 进一步验证：用 TAT 调用 bot/info
    url = f"{_open_base(brand)}/open-apis/bot/v3/info"
    data, api_error = _call_api(url, token)
    if api_error:
        return {
            "ok": False,
            "error": api_error,
            "detail": "tenant token 可获取但 bot/info 调用失败",
            "tat_valid": True,
        }
    if data.get("code") != 0:
        return {
            "ok": False,
            "error": f"[{data.get('code')}] {data.get('msg', '')}",
            "detail": "bot/info 调用失败，可能 Bot 未启用",
            "tat_valid": True,
        }
    return {
        "ok": True,
        "bot_name": data.get("data", {}).get("bot", {}).get("app_name", ""),
        "detail": "OK",
        "tat_valid": True,
    }


def verify_openapi_endpoint(brand):
    """验证 Open API 端点是否可达"""
    url = f"{_open_base(brand)}/open-apis/authen/v1/user_info"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            # 没 token 肯定返回错误，但只要 HTTP 能通就算端点可达
            return {"ok": True, "detail": "reachable"}
    except Exception as e:
        return {"ok": False, "error": str(e), "detail": "unreachable"}


# ── 主流程 ────────────────────────────────────────────────


def run_verify(json_output, user_only=False, tenant_only=False):
    creds_data, creds_source_path = load_credentials_data()
    brand = creds_data.get("brand", "feishu")
    app_id = creds_data["appId"]
    app_secret = creds_data["appSecret"]

    results = {}

    # 端点可达性
    if not user_only and not tenant_only:
        results["endpoint"] = verify_openapi_endpoint(brand)

    # 用户 token 验证
    if not tenant_only:
        user_token = creds_data.get("userAccessToken", "")
        if user_token:
            results["user_token"] = verify_user_token(user_token, brand)
        else:
            results["user_token"] = {
                "ok": False,
                "error": "未找到 user_access_token",
                "detail": "请先完成用户授权",
            }

    # 租户 token 验证
    if not user_only:
        results["tenant_token"] = verify_tenant_token(app_id, app_secret, brand)

    # 汇总
    all_ok = all(v.get("ok", False) for v in results.values())

    if json_output:
        print_json(
            {
                "ok": all_ok,
                "results": results,
                "app_id": app_id,
                "brand": brand,
            }
        )
    else:
        print("=" * 50)
        print("飞书 Skills 在线验证")
        print("=" * 50)
        for name, result in results.items():
            status = "✅" if result.get("ok") else "❌"
            label = {
                "endpoint": "Open API 端点",
                "user_token": "用户 Token",
                "tenant_token": "租户 Token",
            }.get(name, name)
            print(f"\n{status} {label}")
            if result.get("ok"):
                for k, v in result.items():
                    if k not in ("ok", "detail", "tat_valid"):
                        print(f"   {k}: {v}")
            else:
                print(f"   错误: {result.get('error', '未知')}")
                print(f"   说明: {result.get('detail', '')}")

        print(f"\n{'=' * 50}")
        print(f"总体: {'✅ 全部通过' if all_ok else '❌ 存在问题'}")


# ── 入口 ──────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="飞书 token 在线验证")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")
    parser.add_argument("--user-only", action="store_true", help="仅验证用户 token")
    parser.add_argument("--tenant-only", action="store_true", help="仅验证租户 token")
    args = parser.parse_args()

    if args.user_only and args.tenant_only:
        print("--user-only 和 --tenant-only 不能同时使用", file=sys.stderr)
        sys.exit(1)

    run_verify(args.json, args.user_only, args.tenant_only)


if __name__ == "__main__":
    cli_run(main)
