#!/usr/bin/env python3
"""
im_chat_info.py -- 获取群聊详情
用法: python3 im_chat_info.py --chat-id oc_xxx
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from feishu_common import create_client, print_json, cli_run
import argparse


def main():
    parser = argparse.ArgumentParser(description="获取群聊详情")
    parser.add_argument("--chat-id", required=True, help="群聊 chat_id")
    args = parser.parse_args()

    client = create_client()
    result = client.im_chat_info(args.chat_id)
    print_json(result)


if __name__ == "__main__":
    cli_run(main)
