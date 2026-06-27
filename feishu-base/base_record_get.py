#!/usr/bin/env python3
"""
base_record_get.py -- 获取单条记录详情

用法:
    python3 base_record_get.py --app base_token_or_url --table table_id --record rec_xxx
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from feishu_common import create_client, print_json, extract_base_info, cli_run
import argparse


def main():
    parser = argparse.ArgumentParser(description="获取单条记录详情")
    parser.add_argument("--app", required=True, help="Base token 或 URL")
    parser.add_argument("--table", required=True, help="数据表 ID")
    parser.add_argument("--record", required=True, help="记录 ID")
    args = parser.parse_args()

    app_token, table_id = extract_base_info(args.app)
    if not table_id and args.table:
        table_id = args.table
    if not table_id:
        raise RuntimeError("缺少 --table 参数，且 URL 中未包含 table_id")

    client = create_client()
    result = client.base_get_record(app_token, table_id, args.record)
    print_json(result)


if __name__ == "__main__":
    cli_run(main)
