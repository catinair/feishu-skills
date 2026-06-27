#!/usr/bin/env python3
"""
base_tables.py -- 列出多维表格中的所有数据表
用法: python3 base_tables.py --app base_token_or_url
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from feishu_common import create_client, print_json, extract_base_info, cli_run
import argparse

def main():
    parser = argparse.ArgumentParser(description="列出多维表格中的数据表")
    parser.add_argument("--app", required=True, help="base token 或完整 URL")
    args = parser.parse_args()

    app_token, _ = extract_base_info(args.app)

    client = create_client()
    result = client.base_list_tables(app_token)
    print_json(result)

if __name__ == "__main__":
    cli_run(main)
