#!/usr/bin/env python3
"""
im_chat_add_members.py -- 向群聊添加成员
用法: python3 im_chat_add_members.py --chat-id oc_xxx --members id1,id2 [--user-id-type user_id]
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from feishu_common import create_client, confirm_action_or_exit, print_json, cli_run, is_trusted_chat
import argparse


def main():
    parser = argparse.ArgumentParser(description="向群聊添加成员")
    parser.add_argument("--chat-id", required=True, help="群聊 chat_id")
    parser.add_argument("--members", required=True, help="成员 ID 列表，逗号分隔")
    parser.add_argument("--user-id-type", default="user_id", help="成员 ID 类型：user_id/open_id/union_id（默认 user_id）")
    parser.add_argument("--yes", "-y", action="store_true", help="跳过确认")
    args = parser.parse_args()

    member_ids = [m.strip() for m in args.members.split(",") if m.strip()]
    client = create_client()
    confirm_action_or_exit(
        "im_chat_add_members",
        f"确认向群聊 {args.chat_id} 添加 {len(member_ids)} 名成员?",
        yes=args.yes,
        is_trusted=is_trusted_chat(args.chat_id),
    )
    result = client.im_chat_add_members(args.chat_id, member_ids, member_id_type=args.user_id_type)
    print_json(result)


if __name__ == "__main__":
    cli_run(main)
