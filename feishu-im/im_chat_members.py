#!/usr/bin/env python3
"""
im_chat_members.py -- 查询群聊成员列表
用法: python3 im_chat_members.py --chat-id oc_xxx [--user-id-type user_id] [--page-size 100] [--max 500]
"""

import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from feishu_common import create_client, print_json, cli_run
import argparse


def main():
    parser = argparse.ArgumentParser(description="查询群聊成员")
    parser.add_argument("--chat-id", required=True, help="群聊 chat_id")
    parser.add_argument(
        "--user-id-type",
        default="user_id",
        help="成员 ID 类型：user_id/open_id/union_id（默认 user_id）",
    )
    parser.add_argument("--page-size", type=int, default=100, help="每页数量")
    parser.add_argument("--page-token", help="分页 token；提供后仅返回单页")
    parser.add_argument("--max", type=int, help="自动分页最大返回条数")
    args = parser.parse_args()

    client = create_client()
    result = client.im_chat_members(
        args.chat_id,
        member_id_type=args.user_id_type,
        page_size=args.page_size,
        page_token=args.page_token,
        max_results=args.max,
    )
    print_json(result)


if __name__ == "__main__":
    cli_run(main)
