#!/usr/bin/env python3
"""
im_create_chat.py -- 创建群聊
用法: python3 im_create_chat.py --name "群名称" [--description "描述"]
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from feishu_common import create_client, confirm_action_or_exit, print_json, cli_run
import argparse

def main():
    parser = argparse.ArgumentParser(description="创建群聊")
    parser.add_argument("--name", required=True, help="群名称")
    parser.add_argument("--description", default="", help="群描述")
    parser.add_argument("--yes", "-y", action="store_true", help="跳过确认")
    args = parser.parse_args()

    client = create_client()
    confirm_action_or_exit(
        "im_create_chat",
        f"确认创建群聊「{args.name}」?",
        yes=args.yes,
        is_trusted=False,
    )
    result = client.im_create_chat(name=args.name, description=args.description)
    print_json(result)

if __name__ == "__main__":
    cli_run(main)
