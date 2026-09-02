#!/usr/bin/env python3
"""
im_list_chats.py -- 列出当前身份有权限的群聊
用法: python3 im_list_chats.py [--page-size 50] [--sort-type ByActiveTimeDesc]
"""

import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from feishu_common import create_client, print_json, cli_run
import argparse


def main():
    parser = argparse.ArgumentParser(description="列出当前身份有权限的群聊")
    parser.add_argument("--page-size", type=int, default=50, help="每页数量")
    parser.add_argument("--max", type=int, help="最大返回条数")
    parser.add_argument("--page-token", help="分页 token；提供后仅返回单页")
    parser.add_argument("--user-id-type", help="用户 ID 类型：open_id/user_id/union_id")
    parser.add_argument(
        "--sort-type", help="排序方式，如 ByCreateTimeAsc / ByActiveTimeDesc"
    )
    parser.add_argument(
        "--identity", choices=["user", "tenant"], help="强制使用 user 或 tenant 身份"
    )
    args = parser.parse_args()

    client = create_client()
    use_user_token = (
        {"user": True, "tenant": False}.get(args.identity) if args.identity else None
    )
    result = client.im_list_chats(
        page_size=args.page_size,
        max_results=args.max,
        page_token=args.page_token,
        user_id_type=args.user_id_type,
        sort_type=args.sort_type,
        use_user_token=use_user_token,
    )
    if isinstance(result, dict):
        print_json(result)
    else:
        print_json({"total": len(result), "chats": result})


if __name__ == "__main__":
    cli_run(main)
