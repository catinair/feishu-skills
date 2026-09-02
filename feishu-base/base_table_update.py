#!/usr/bin/env python3
"""
base_table_update.py -- 更新数据表（重命名）

用法:
    python3 base_table_update.py --app base_token_or_url --table table_id --name "新表名"
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from feishu_common import create_client, print_json, extract_base_info, cli_run
import argparse


def main():
    parser = argparse.ArgumentParser(description="更新数据表")
    parser.add_argument("--app", required=True, help="Base token 或 URL")
    parser.add_argument("--table", required=True, help="数据表 ID")
    parser.add_argument("--name", required=True, help="新的数据表名称")
    parser.add_argument("--raw", action="store_true", help="输出完整原始 JSON")
    args = parser.parse_args()

    app_token, table_id = extract_base_info(args.app)
    if not table_id and args.table:
        table_id = args.table
    if not table_id:
        raise RuntimeError("缺少 --table 参数，且 URL 中未包含 table_id")

    client = create_client()
    result = client.base_update_table(app_token, table_id, args.name)
    if args.raw:
        print_json(result)
        return

    data = result.get("data", result) if isinstance(result, dict) else {}
    table = data.get("table", data) if isinstance(data, dict) else {}
    print_json({
        "status": "ok",
        "table_id": table.get("table_id", ""),
        "name": table.get("name", ""),
    })


if __name__ == "__main__":
    cli_run(main)
