#!/usr/bin/env python3
"""
im_send_message.py -- 发送消息到群聊或用户
用法:
  # 发送文本消息到群聊
  python3 im_send_message.py --receive-id oc_xxx --type chat_id --text "Hello"

  # 发送富文本消息
  python3 im_send_message.py --receive-id oc_xxx --type chat_id --title "标题" --post-lines '[[{"tag":"text","text":"内容"}]]'
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from feishu_common import (
    cli_run,
    confirm_action_or_exit,
    create_client,
    is_trusted_chat,
    is_trusted_user,
    print_json,
)
import argparse
import json

def main():
    parser = argparse.ArgumentParser(description="发送消息")
    parser.add_argument("--receive-id", required=True, help="接收者 ID（chat_id 或 open_id）")
    parser.add_argument("--type", required=True, choices=["chat_id", "open_id", "user_id"], help="接收者类型")
    parser.add_argument("--text", help="文本消息内容（与 --title 二选一）")
    parser.add_argument("--title", help="富文本消息标题（与 --text 二选一）")
    parser.add_argument("--post-lines", help="富文本内容 JSON（二维数组）")
    parser.add_argument("--identity", choices=["user", "tenant"], help="强制使用 user 或 tenant 身份发送")
    parser.add_argument("--raw", action="store_true", help="输出完整原始 JSON")
    parser.add_argument("--yes", "-y", action="store_true", help="跳过确认")
    args = parser.parse_args()

    content_lines = None
    if args.text:
        preview = args.text[:100]
    elif args.title and args.post_lines:
        content_lines = json.loads(args.post_lines)
        preview = args.title
    else:
        print("ERROR: --text 或 (--title + --post-lines) 必须指定一组", file=sys.stderr)
        sys.exit(1)

    trusted_target = False
    if args.type == "chat_id":
        trusted_target = is_trusted_chat(args.receive_id)
    elif args.type == "user_id":
        trusted_target = is_trusted_user(args.receive_id)

    confirm_action_or_exit(
        "im_send_message",
        f"将发送消息到 {args.type}={args.receive_id}\n内容预览: {preview}",
        yes=args.yes,
        is_trusted=trusted_target,
    )

    client = create_client()

    use_user_token = {"user": True, "tenant": False}.get(args.identity) if args.identity else None

    if args.text:
        result = client.im_send_text(args.receive_id, args.type, args.text, use_user_token=use_user_token)
    else:
        result = client.im_send_post(args.receive_id, args.type, args.title, content_lines, use_user_token=use_user_token)

    if args.raw:
        print_json(result)
        return

    # Determine where the message data lives (wrapped or unwrapped)
    if isinstance(result, dict):
        if "data" in result and isinstance(result["data"], dict):
            msg_data = result["data"]
            status = "ok" if result.get("code") == 0 else "error"
        else:
            msg_data = result
            status = "ok" if ("code" not in msg_data or msg_data.get("code") == 0) else "error"
    else:
        msg_data = {}
        status = "ok"

    summary = {
        "status": status,
        "message_id": msg_data.get("message_id", ""),
        "chat_id": msg_data.get("chat_id", ""),
        "msg_type": msg_data.get("msg_type", ""),
        "create_time": msg_data.get("create_time", ""),
    }

    sender = msg_data.get("sender")
    if isinstance(sender, dict):
        summary["sender_type"] = sender.get("sender_type", "")

    print_json(summary)

if __name__ == "__main__":
    cli_run(main)
