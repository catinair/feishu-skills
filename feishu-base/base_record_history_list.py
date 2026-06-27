#!/usr/bin/env python3
"""
base_record_history_list.py -- 查询记录变更历史

用法:
    python3 base_record_history_list.py --app base_token_or_url --table table_id --record rec_xxx
    python3 base_record_history_list.py --app base_token_or_url --table table_id --record rec_xxx --page-size 50

分页说明:
    返回结果中的最后一条记录的 version 值可作为下一页的 max_version 参数传入。
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from feishu_common import create_client, print_json, extract_base_info, cli_run
import argparse


def main():
    parser = argparse.ArgumentParser(description="查询记录变更历史")
    parser.add_argument("--app", required=True, help="Base token 或 URL")
    parser.add_argument("--table", required=True, help="数据表 ID")
    parser.add_argument("--record", required=True, help="记录 ID")
    parser.add_argument("--page-size", type=int, default=30, help="分页大小（默认 30）")
    parser.add_argument("--max-version", type=int, default=None, help="分页参数（上一页最后一条的 version）")
    args = parser.parse_args()

    app_token, table_id = extract_base_info(args.app)
    if not table_id and args.table:
        table_id = args.table
    if not table_id:
        raise RuntimeError("缺少 --table 参数，且 URL 中未包含 table_id")

    client = create_client()
    result = client.base_list_record_history(
        app_token, table_id, args.record,
        page_size=args.page_size,
        max_version=args.max_version
    )
    print_json(result)


if __name__ == "__main__":
    cli_run(main)
