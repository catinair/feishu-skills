#!/usr/bin/env python3
"""
perm_doc_list.py -- 列出文档/表格/多维表格的协作者
用法: python3 perm_doc_list.py --token doxcnxxx --type docx [--page-size 50] [--max 500]
"""

import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from feishu_common import create_client, print_json, cli_run
import argparse


def main():
    parser = argparse.ArgumentParser(description="列出文档协作者")
    parser.add_argument("--token", required=True, help="文档/表格/多维表格 token")
    parser.add_argument(
        "--type", required=True, help="类型：docx/sheet/bitable/file/mindnote/slides"
    )
    parser.add_argument("--page-size", type=int, default=50, help="每页数量")
    parser.add_argument("--page-token", help="分页 token；提供后仅返回单页")
    parser.add_argument("--max", type=int, help="自动分页最大返回条数")
    args = parser.parse_args()

    client = create_client()
    result = client.perm_list_members(
        args.token,
        args.type,
        page_size=args.page_size,
        page_token=args.page_token,
        max_results=args.max,
    )
    print_json(result)


if __name__ == "__main__":
    cli_run(main)
