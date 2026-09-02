#!/usr/bin/env python3
"""
drive_list.py -- 列出文件夹中的文件
用法: python3 drive_list.py [--folder-token fldcnxxx] [--order-by EditedTime] [--direction DESC]
"""

import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from feishu_common import create_client, print_json, cli_run
import argparse


def main():
    parser = argparse.ArgumentParser(description="列出文件夹中的文件")
    parser.add_argument("--folder-token", help="文件夹 token（省略则列出根目录）")
    parser.add_argument("--page-size", type=int, default=200, help="每页数量")
    parser.add_argument("--max", type=int, help="最大返回条数")
    parser.add_argument(
        "--order-by", choices=["EditedTime", "CreatedTime"], help="排序字段"
    )
    parser.add_argument("--direction", choices=["ASC", "DESC"], help="排序方向")
    parser.add_argument("--user-id-type", help="用户 ID 类型：open_id/user_id/union_id")
    args = parser.parse_args()

    client = create_client()
    files = client.list_files(
        folder_token=args.folder_token,
        page_size=args.page_size,
        max_results=args.max,
        order_by=args.order_by,
        direction=args.direction,
        user_id_type=args.user_id_type,
    )
    print_json({"total": len(files), "files": files})


if __name__ == "__main__":
    cli_run(main)
