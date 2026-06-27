#!/usr/bin/env python3
"""
wiki_list_spaces.py -- 列出知识空间
用法: python3 wiki_list_spaces.py [--page-size 50]
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from feishu_common import create_client, print_json, cli_run
import argparse

def main():
    parser = argparse.ArgumentParser(description="列出知识空间")
    parser.add_argument("--page-size", type=int, default=50, help="每页数量")
    args = parser.parse_args()

    client = create_client()
    spaces = client.wiki_list_spaces(page_size=args.page_size)
    print_json({"total": len(spaces), "spaces": spaces})

if __name__ == "__main__":
    cli_run(main)
