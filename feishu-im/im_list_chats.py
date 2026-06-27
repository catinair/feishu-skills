#!/usr/bin/env python3
"""
im_list_chats.py -- 列出当前身份有权限的群聊
用法: python3 im_list_chats.py [--page-size 50]
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from feishu_common import create_client, print_json, cli_run
import argparse

def main():
    parser = argparse.ArgumentParser(description="列出当前身份有权限的群聊")
    parser.add_argument("--page-size", type=int, default=50, help="每页数量")
    args = parser.parse_args()

    client = create_client()
    chats = client.im_list_chats(page_size=args.page_size)
    print_json({"total": len(chats), "chats": chats})

if __name__ == "__main__":
    cli_run(main)
