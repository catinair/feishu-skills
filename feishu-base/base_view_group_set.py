#!/usr/bin/env python3
"""
base_view_group_set.py -- 设置视图分组配置

用法:
    python3 base_view_group_set.py --app base_token_or_url --table table_id --view view_id --json '[{"field_id":"fldStatus"}]'

group JSON 示例:
    [{"field_id": "fldStatus"}]
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from feishu_common import create_client, print_json, extract_base_info, cli_run
import argparse


def main():
    parser = argparse.ArgumentParser(description="设置视图分组配置")
    parser.add_argument("--app", required=True, help="Base token 或 URL")
    parser.add_argument("--table", required=True, help="数据表 ID")
    parser.add_argument("--view", required=True, help="视图 ID")
    parser.add_argument("--json", required=True, help="分组配置 JSON 字符串")
    args = parser.parse_args()

    app_token, table_id = extract_base_info(args.app)
    if not table_id and args.table:
        table_id = args.table
    if not table_id:
        raise RuntimeError("缺少 --table 参数，且 URL 中未包含 table_id")

    group_config = json.loads(args.json)

    client = create_client()
    result = client.base_set_view_group(app_token, table_id, args.view, group_config)
    print_json(result)


if __name__ == "__main__":
    cli_run(main)
