#!/usr/bin/env python3
"""
drive_list.py -- 列出文件夹中的文件
用法: python3 drive_list.py [--folder-token fldcnxxx]
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from feishu_common import create_client, print_json, cli_run
import argparse

def main():
    parser = argparse.ArgumentParser(description="列出文件夹中的文件")
    parser.add_argument("--folder-token", help="文件夹 token（省略则列出根目录）")
    args = parser.parse_args()

    client = create_client()
    files = client.list_files(folder_token=args.folder_token)
    print_json({"total": len(files), "files": files})

if __name__ == "__main__":
    cli_run(main)
