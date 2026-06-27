#!/usr/bin/env python3
"""
base_view_filter_set.py -- 设置视图筛选条件

用法:
    python3 base_view_filter_set.py --app base_token_or_url --table table_id --view view_id --json '{"logic":"and","conditions":[["fldStatus","==","Todo"]]}'

filter JSON 示例:
    {"logic": "and", "conditions": [["field_id", "operator", "value"], ...]}
    常用 operator: ==, !=, <, <=, >, >=, contains, is_empty, is_not_empty
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from feishu_common import create_client, print_json, extract_base_info, cli_run
import argparse


def main():
    parser = argparse.ArgumentParser(description="设置视图筛选条件")
    parser.add_argument("--app", required=True, help="Base token 或 URL")
    parser.add_argument("--table", required=True, help="数据表 ID")
    parser.add_argument("--view", required=True, help="视图 ID")
    parser.add_argument("--json", required=True, help="筛选条件 JSON 字符串")
    args = parser.parse_args()

    app_token, table_id = extract_base_info(args.app)
    if not table_id and args.table:
        table_id = args.table
    if not table_id:
        raise RuntimeError("缺少 --table 参数，且 URL 中未包含 table_id")

    filter_config = json.loads(args.json)

    client = create_client()
    result = client.base_set_view_filter(app_token, table_id, args.view, filter_config)
    print_json(result)


if __name__ == "__main__":
    cli_run(main)
