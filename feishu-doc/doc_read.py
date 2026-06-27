#!/usr/bin/env python3
"""
doc_read.py -- 读取飞书文档 block 树
用法: python3 doc_read.py --doc doxcnxxx [--page-token xxx]
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from feishu_common import create_client, print_json, cli_run
import argparse

def main():
    parser = argparse.ArgumentParser(description="读取飞书文档 block 树")
    parser.add_argument("--doc", required=True, help="文档 ID")
    parser.add_argument("--page-token", help="分页 token")
    args = parser.parse_args()

    client = create_client()
    result = client.document_blocks(args.doc, page_token=args.page_token)
    print_json(result)

if __name__ == "__main__":
    cli_run(main)
