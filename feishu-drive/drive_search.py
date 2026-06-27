#!/usr/bin/env python3
"""
drive_search.py -- 按名称搜索 drive 文件（客户端过滤，非全文搜索）
用法: python3 drive_search.py --query "关键词" [--folder-token fldcnxxx]
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from feishu_common import create_client, print_json, cli_run
import argparse

def main():
    parser = argparse.ArgumentParser(description="按名称搜索 drive 文件")
    parser.add_argument("--query", required=True, help="搜索关键词")
    parser.add_argument("--folder-token", help="限制在指定文件夹内搜索")
    parser.add_argument("--page-size", type=int, default=200, help="扫描的最大文件数")
    args = parser.parse_args()

    client = create_client()
    result = client.search_files(args.query, folder_token=args.folder_token, page_size=args.page_size)
    print_json(result)

if __name__ == "__main__":
    cli_run(main)
