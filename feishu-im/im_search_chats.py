#!/usr/bin/env python3
"""
im_search_chats.py -- 按关键字搜索群组（含未加入的公开群）
用法: python3 im_search_chats.py --query "全员MVP"
"""

import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from feishu_common import create_client, print_json, cli_run
import argparse


def main():
    parser = argparse.ArgumentParser(description="按关键字搜索群组")
    parser.add_argument("--query", required=True, help="搜索关键字")
    parser.add_argument("--page-size", type=int, default=50, help="每页数量")
    parser.add_argument("--max", type=int, help="最大返回条数")
    parser.add_argument("--page-token", help="分页 token；提供后仅返回单页")
    parser.add_argument(
        "--search-types",
        nargs="+",
        choices=["private", "external", "public_joined", "public_not_joined"],
        help="群组类型过滤，如 public_not_joined",
    )
    parser.add_argument(
        "--identity", choices=["user", "tenant"], help="强制使用 user 或 tenant 身份"
    )
    args = parser.parse_args()

    client = create_client()
    use_user_token = (
        {"user": True, "tenant": False}.get(args.identity) if args.identity else None
    )
    result = client.im_search_chats(
        query=args.query,
        page_size=args.page_size,
        max_results=args.max,
        page_token=args.page_token,
        search_types=args.search_types,
        use_user_token=use_user_token,
    )
    print_json(result)


if __name__ == "__main__":
    cli_run(main)
