#!/usr/bin/env python3
"""
im_messages_search.py -- 搜索消息

用法:
    # 按关键词搜索
    python3 im_messages_search.py --query "项目进展"

    # 限定群组和发送者
    python3 im_messages_search.py --query "周报" --chat-ids "oc_xxx,oc_yyy" --senders "ou_xxx"

    # 限定时间范围
    python3 im_messages_search.py --query "会议" --start "2026-01-01T00:00:00+08:00" --end "2026-01-31T23:59:59+08:00"
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from feishu_common import create_client, print_json, cli_run
import argparse


def main():
    parser = argparse.ArgumentParser(description="搜索消息")
    parser.add_argument("--query", default=None, help="搜索关键词")
    parser.add_argument("--chat-ids", default=None, help="限定会话 ID，逗号分隔")
    parser.add_argument("--senders", default=None, help="发送者 open_id，逗号分隔")
    parser.add_argument("--start", default=None, help="开始时间（ISO 8601 格式，如 2026-01-01T00:00:00+08:00）")
    parser.add_argument("--end", default=None, help="结束时间（ISO 8601 格式）")
    parser.add_argument("--page-size", type=int, default=20, help="每页条数（1-50，默认 20）")
    parser.add_argument("--page-token", default=None, help="分页 token")
    args = parser.parse_args()

    chat_ids = None
    if args.chat_ids:
        chat_ids = [c.strip() for c in args.chat_ids.split(",") if c.strip()]

    senders = None
    if args.senders:
        senders = [s.strip() for s in args.senders.split(",") if s.strip()]

    client = create_client()
    result = client.im_search_messages(
        query=args.query,
        chat_ids=chat_ids,
        senders=senders,
        start_time=args.start,
        end_time=args.end,
        page_size=args.page_size,
        page_token=args.page_token,
    )
    print_json(result)


if __name__ == "__main__":
    cli_run(main)
