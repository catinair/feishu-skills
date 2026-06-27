#!/usr/bin/env python3
"""
doc_token.py -- 获取并显示当前 tenant_access_token

用法:
    python3 feishu-doc/doc_token.py
    python3 feishu-doc/doc_token.py --credentials /path/to/creds.json

输出包含 token 值、过期时间、缓存状态等信息。
"""
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from feishu_common import FeishuClient, print_json, cli_run
from feishu_common._config_loader import default_credentials_path
import argparse


def main():
    parser = argparse.ArgumentParser(description="获取飞书 tenant_access_token")
    parser.add_argument(
        "--credentials",
        default=str(default_credentials_path()),
        help="凭证文件路径（默认: 使用运行时配置目录的 credentials.json）",
    )
    args = parser.parse_args()

    creds_path = args.credentials
    if not os.path.isabs(creds_path):
        creds_path = os.path.join(os.path.dirname(__file__), '..', creds_path)

    client = FeishuClient(creds_path)
    token = client._ensure_token()

    # 尝试读取缓存信息
    cache_info = {}
    try:
        from feishu_common._config_loader import resolve_token_cache_path
        cache_file = resolve_token_cache_path()
        if cache_file.exists():
            import json
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached = json.load(f)
            cache_info = {
                "cached": True,
                "expire": cached.get("expire"),
                "expires_in_human": None,
            }
            exp = cached.get("expire", 0)
            if exp:
                remaining = exp - time.time()
                if remaining > 0:
                    cache_info["expires_in_human"] = f"{int(remaining)}s (~{int(remaining/60)}min)"
                else:
                    cache_info["expires_in_human"] = "expired"
        else:
            cache_info = {"cached": False}
    except Exception:
        cache_info = {"cached": False}

    print_json({
        "tenant_access_token": token,
        "token_prefix": token[:20] + "..." if len(token) > 20 else token,
        "cache": cache_info,
    })


if __name__ == "__main__":
    cli_run(main)
