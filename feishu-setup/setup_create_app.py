#!/usr/bin/env python3
"""
应用创建/绑定脚本
通过 lark-cli 同款 Device Flow 流程，让用户扫码即可创建新应用或绑定已有应用，
无需手动去飞书开放平台后台操作。

与 auth_device_flow.py 的区别：
  - auth_device_flow.py：获取用户授权 token（需要已有应用凭证）
  - setup_create_app.py：创建/绑定应用，获取 app_id + app_secret（前置步骤）

用法:
  发起创建/绑定（输出链接 + 可选二维码）:
    python3 setup_create_app.py --begin [--qr] [--json]

  轮询获取凭证并写入 credentials.json:
    python3 setup_create_app.py --poll [--json]

  查看当前状态:
    python3 setup_create_app.py --status [--json]
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))
from feishu_common import cli_run, print_json
from feishu_common._config_loader import (
    resolve_config_path,
    get_config_dir,
    safe_write_json,
    load_credentials_data,
)

# ── 端点 ──────────────────────────────────────────────────

ACCOUNTS_BASE = "https://accounts.feishu.cn"
REGISTRATION_URL = f"{ACCOUNTS_BASE}/oauth/v1/app/registration"

# ── 状态文件 ──────────────────────────────────────────────


def _state_path():
    return get_config_dir(for_write=True) / "app_registration_state.json"


# ── 工具函数 ──────────────────────────────────────────────


def _post_form(url, data):
    encoded = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=encoded,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        return {"error": f"http_{e.code}", "error_description": body}


# ── 发起 ──────────────────────────────────────────────────


def cmd_begin(generate_qr, json_output):
    resp = _post_form(
        REGISTRATION_URL,
        {
            "action": "begin",
            "archetype": "PersonalAgent",
            "auth_method": "client_secret",
            "request_user_info": "open_id tenant_brand",
        },
    )

    if "error" in resp and "device_code" not in resp:
        if json_output:
            print_json(
                {
                    "ok": False,
                    "error": resp.get("error_description", resp["error"]),
                }
            )
        else:
            print(
                f"发起失败: {resp.get('error_description', resp['error'])}",
                file=sys.stderr,
            )
        sys.exit(1)

    state = {
        "device_code": resp["device_code"],
        "interval": resp.get("interval", 5),
        "expires_in": resp.get("expires_in", 300),
    }
    sp = _state_path()
    sp.parent.mkdir(parents=True, exist_ok=True)
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
        print()
        print("请打开链接，选择「创建新应用」或「关联已有应用」")

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


# ── 轮询 ──────────────────────────────────────────────────


def _poll_registration(device_code, interval, expires_in, json_output):
    deadline = time.time() + expires_in
    cur_interval = interval
    attempt = 0

    while time.time() < deadline:
        attempt += 1
        time.sleep(cur_interval)
        resp = _post_form(
            REGISTRATION_URL,
            {
                "action": "poll",
                "device_code": device_code,
            },
        )

        if resp.get("client_id"):
            return {
                "app_id": resp["client_id"],
                "app_secret": resp["client_secret"],
                "user_open_id": resp.get("user_info", {}).get("open_id", ""),
                "tenant_brand": resp.get("user_info", {}).get("tenant_brand", "feishu"),
            }, attempt

        error = resp.get("error", "")
        if error == "authorization_pending":
            if not json_output:
                print(f"  [{attempt}] 等待用户确认...", flush=True)
            continue
        elif error == "slow_down":
            cur_interval = min(cur_interval + 5, 60)
            if not json_output:
                print(f"  [{attempt}] slow_down, 间隔增至 {cur_interval}s", flush=True)
        elif error in ("access_denied", "expired_token", "invalid_grant"):
            raise RuntimeError(f"{error}: {resp.get('error_description', error)}")
        else:
            raise RuntimeError(f"未知错误: {resp}")

    raise RuntimeError("操作超时，用户未在有效期内确认")


def _cleanup_state():
    sp = _state_path()
    sp.unlink(missing_ok=True)
    sp.with_suffix(".png").unlink(missing_ok=True)


def cmd_poll(json_output):
    sp = _state_path()
    if not sp.exists():
        msg = "未找到状态文件，请先运行 --begin"
        if json_output:
            print_json({"ok": False, "error": msg})
        else:
            print(msg, file=sys.stderr)
        sys.exit(1)

    with open(sp) as f:
        state = json.load(f)

    # 轮询获取凭证
    result, attempts = _poll_registration(
        state["device_code"],
        state["interval"],
        state["expires_in"],
        json_output,
    )

    app_id = result["app_id"]
    app_secret = result["app_secret"]
    brand = result["tenant_brand"]
    user_open_id = result["user_open_id"]

    # 写入 credentials.json
    creds_path = resolve_config_path("credentials.json", for_write=True)
    existing = {}
    try:
        existing = load_credentials_data()[0]
    except Exception:
        pass

    creds = {
        "appId": app_id,
        "appSecret": app_secret,
        "brand": brand,
    }
    safe_write_json(creds_path, creds)

    _cleanup_state()

    if json_output:
        print_json(
            {
                "ok": True,
                "app_id": app_id,
                "brand": brand,
                "user_open_id": user_open_id,
                "credentials_path": str(creds_path),
                "attempts": attempts,
            }
        )
    else:
        print(
            f"\n✅ 应用{'绑定' if existing.get('appId') else '创建'}成功 (尝试 {attempts} 次)"
        )
        print(f"   App ID:     {app_id}")
        print(f"   品牌:       {brand}")
        print(f"   凭证路径:   {creds_path}")
        print(f"   下一步:     运行 python3 feishu-auth/auth_device_flow.py --begin")


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
                }
            )
        else:
            print(f"有进行中的操作，剩余约 {int(max(0, remaining))}s")
    else:
        if json_output:
            print_json({"ok": True, "active": False})
        else:
            print("没有进行中的操作")


# ── 入口 ──────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="创建/绑定飞书应用")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--begin", action="store_true", help="发起应用创建/绑定")
    group.add_argument(
        "--poll", action="store_true", help="轮询获取凭证并写入 credentials.json"
    )
    group.add_argument("--status", action="store_true", help="查看当前状态")
    parser.add_argument("--qr", action="store_true", help="生成二维码（需 qrcode 库）")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")

    args = parser.parse_args()

    if args.begin:
        cmd_begin(args.qr, args.json)
    elif args.poll:
        cmd_poll(args.json)
    elif args.status:
        cmd_status(args.json)


if __name__ == "__main__":
    cli_run(main)
