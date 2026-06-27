#!/usr/bin/env python3
"""
perm_doc_list.py -- 列出文档/表格/多维表格的协作者
用法: python3 perm_doc_list.py --token doxcnxxx --type docx
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from feishu_common import create_client, print_json, cli_run
import argparse


def main():
    parser = argparse.ArgumentParser(description="列出文档协作者")
    parser.add_argument("--token", required=True, help="文档/表格/多维表格 token")
    parser.add_argument("--type", required=True, help="类型：docx/sheet/bitable/file/mindnote/slides")
    args = parser.parse_args()

    client = create_client()
    result = client.perm_list_members(args.token, args.type)
    print_json(result)


if __name__ == "__main__":
    cli_run(main)
