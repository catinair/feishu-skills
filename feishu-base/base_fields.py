#!/usr/bin/env python3
"""
base_fields.py -- 列出多维表格数据表的所有字段

用法:
    python3 base_fields.py --app base_token_or_url --table table_id [--view view_id]
"""

import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from feishu_common import create_client, print_json, extract_base_info, cli_run
import argparse


def main():
    parser = argparse.ArgumentParser(description="列出数据表的所有字段")
    parser.add_argument("--app", required=True, help="Base token 或 URL")
    parser.add_argument("--table", required=True, help="数据表 ID")
    parser.add_argument("--view", help="视图 ID；提供后按视图过滤字段")
    args = parser.parse_args()

    app_token, table_id = extract_base_info(args.app)
    if not table_id and args.table:
        table_id = args.table
    if not table_id:
        raise RuntimeError("缺少 --table 参数，且 URL 中未包含 table_id")

    client = create_client()
    result = client.base_list_fields(app_token, table_id, view_id=args.view)
    print_json(result)


if __name__ == "__main__":
    cli_run(main)
