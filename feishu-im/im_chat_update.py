#!/usr/bin/env python3
"""
im_chat_update.py -- 修改群聊信息（转让群主、改名等）
用法:
  python3 im_chat_update.py --chat-id oc_xxx --owner-id ou_xxx   # 转让群主
  python3 im_chat_update.py --chat-id oc_xxx --name "新群名"       # 修改群名
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from feishu_common import create_client, confirm_action_or_exit, print_json, cli_run, is_trusted_chat
import argparse


def main():
    parser = argparse.ArgumentParser(description="修改群聊信息")
    parser.add_argument("--chat-id", required=True, help="群聊 chat_id")
    parser.add_argument("--owner-id", help="新群主 open_id")
    parser.add_argument("--name", help="新群名")
    parser.add_argument("--description", help="新群描述")
    parser.add_argument("--yes", "-y", action="store_true", help="跳过确认")
    parser.add_argument("--raw", action="store_true", help="输出完整原始 JSON")
    args = parser.parse_args()

    kwargs = {}
    if args.owner_id:
        kwargs["owner_id"] = args.owner_id
    if args.name:
        kwargs["name"] = args.name
    if args.description:
        kwargs["description"] = args.description
    if not kwargs:
        print("Error: 至少提供一个修改项（--owner-id / --name / --description）", file=sys.stderr)
        sys.exit(1)

    client = create_client()
    confirm_action_or_exit(
        "im_chat_update",
        f"确认修改群聊 {args.chat_id} 的信息?",
        yes=args.yes,
        is_trusted=is_trusted_chat(args.chat_id),
    )
    result = client.im_chat_update(args.chat_id, **kwargs)
    if args.raw:
        print_json(result)
        return

    data = result.get("data", result) if isinstance(result, dict) else {}
    chat = data.get("chat", data) if isinstance(data, dict) else {}
    print_json({
        "status": "ok",
        "chat_id": chat.get("chat_id", args.chat_id),
        "name": chat.get("name", ""),
        "description": chat.get("description", ""),
    })


if __name__ == "__main__":
    cli_run(main)
