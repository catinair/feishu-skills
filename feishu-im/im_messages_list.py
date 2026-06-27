#!/usr/bin/env python3
"""
im_messages_list.py -- 获取群聊/会话消息列表

用法：
    python im_messages_list.py --chat-id oc_xxx
    python im_messages_list.py --chat-id oc_xxx --limit 20
    python im_messages_list.py --chat-id oc_xxx --start-time 1777000000000

注意：
    --start-time / --end-time 为 Unix 时间戳（毫秒）。
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from feishu_common import create_client, cli_run, print_json


def main():
    parser = argparse.ArgumentParser(description="获取群聊/会话消息列表")
    parser.add_argument("--chat-id", required=True, help="群聊或会话 ID（chat_id）")
    parser.add_argument("--limit", type=int, default=20, help="最大返回条数（默认 20）")
    parser.add_argument("--start-time", type=int, help="起始时间（毫秒时间戳）")
    parser.add_argument("--end-time", type=int, help="结束时间（毫秒时间戳）")
    parser.add_argument("--raw", action="store_true", help="输出完整原始 JSON")
    args = parser.parse_args()

    client = create_client()

    messages = []
    page_token = None
    while len(messages) < args.limit:
        page_size = min(args.limit - len(messages), 50)
        data = client.im_messages_list(
            container_id=args.chat_id,
            container_id_type="chat",
            page_size=page_size,
            page_token=page_token,
            start_time=args.start_time,
            end_time=args.end_time,
        )
        items = data.get("items", [])
        messages.extend(items)
        if not data.get("has_more"):
            break
        page_token = data.get("page_token")
        if not page_token:
            break

    if args.raw:
        print_json({"items": messages, "total": len(messages)})
        return

    results = []
    for msg in messages:
        body = msg.get("body", {})
        content = body.get("content", "")
        results.append({
            "message_id": msg.get("message_id", ""),
            "root_id": msg.get("root_id", ""),
            "parent_id": msg.get("parent_id", ""),
            "msg_type": msg.get("msg_type", ""),
            "sender": msg.get("sender", {}).get("id", ""),
            "create_time": msg.get("create_time", ""),
            "chat_id": msg.get("chat_id", ""),
            "content": content[:200] + "..." if len(content) > 200 else content,
        })

    print_json({"messages": results, "total": len(results)})


if __name__ == "__main__":
    cli_run(main)
