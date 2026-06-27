#!/usr/bin/env python3
"""
im_messages_reply.py -- 回复指定消息

用法：
    python im_messages_reply.py --message-id om_xxx --text "收到"
    python im_messages_reply.py --message-id om_xxx --text "好的" --yes

注意：
    --message-id 是原消息的 message_id（不是 root_id）。
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from feishu_common import cli_run, confirm_action_or_exit, create_client, print_json


def main():
    parser = argparse.ArgumentParser(description="回复指定消息")
    parser.add_argument("--message-id", required=True, help="原消息 message_id")
    parser.add_argument("--text", required=True, help="回复内容")
    parser.add_argument("--yes", "-y", action="store_true", help="跳过确认")
    args = parser.parse_args()

    confirm_action_or_exit("im_send_message", f"确认回复消息 {args.message_id[:30]}...?", yes=args.yes)

    client = create_client()
    msg = client.im_reply_message(
        args.message_id, "text", {"text": args.text}
    )
    print_json({
        "message_id": msg.get("message_id", ""),
        "parent_id": msg.get("parent_id", ""),
        "root_id": msg.get("root_id", ""),
        "chat_id": msg.get("chat_id", ""),
        "msg_type": msg.get("msg_type", ""),
        "create_time": msg.get("create_time", ""),
    })


if __name__ == "__main__":
    cli_run(main)
