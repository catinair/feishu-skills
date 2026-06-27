#!/usr/bin/env python3
"""
base_query.py -- 查询多维表格记录
用法: python3 base_query.py --app base_token_or_url --table table_id [--filter "字段名=值"]
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from feishu_common import create_client, print_json, extract_base_info, cli_run
import argparse

def main():
    parser = argparse.ArgumentParser(description="查询多维表格记录")
    parser.add_argument("--app", required=True, help="base token 或完整 URL")
    parser.add_argument("--table", help="数据表 ID（可选，默认从 URL 提取）")
    parser.add_argument("--filter", help="筛选条件（飞书 filter 表达式）")
    parser.add_argument("--page-size", type=int, default=500, help="每页数量")
    args = parser.parse_args()

    app_token, table_id_from_url = extract_base_info(args.app)
    table_id = args.table or table_id_from_url
    if not table_id:
        print("ERROR: 无法从 URL 提取 table_id，请手动指定 --table", file=sys.stderr)
        sys.exit(1)

    client = create_client()
    result = client.base_query_records(
        app_token, table_id,
        page_size=args.page_size, filter_expr=args.filter
    )
    print_json(result)

if __name__ == "__main__":
    cli_run(main)
