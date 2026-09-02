#!/usr/bin/env python3
"""
drive_search.py -- 调用 Drive 原生搜索接口搜索文件
用法: python3 drive_search.py --query "关键词" [--folder-token fldcnxxx] [--order-by EditedTime] [--direction DESC]
"""

import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from feishu_common import create_client, print_json, cli_run
import argparse


def main():
    parser = argparse.ArgumentParser(description="搜索 drive 文件")
    parser.add_argument("--query", required=True, help="搜索关键词")
    parser.add_argument("--folder-token", help="限制在指定文件夹内搜索")
    parser.add_argument("--page-size", type=int, default=200, help="每页数量")
    parser.add_argument("--max", type=int, help="最大返回条数")
    parser.add_argument("--page-token", help="分页 token；提供后仅返回单页")
    parser.add_argument(
        "--order-by", choices=["EditedTime", "CreatedTime"], help="排序字段"
    )
    parser.add_argument("--direction", choices=["ASC", "DESC"], help="排序方向")
    args = parser.parse_args()

    client = create_client()
    result = client.search_files(
        args.query,
        folder_token=args.folder_token,
        page_size=args.page_size,
        max_results=args.max,
        page_token=args.page_token,
        order_by=args.order_by,
        direction=args.direction,
    )
    print_json(result)


if __name__ == "__main__":
    cli_run(main)
