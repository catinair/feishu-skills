#!/usr/bin/env python3
"""
base_field_delete.py -- 删除字段

用法:
    python3 base_field_delete.py --app base_token_or_url --table table_id --field fld_xxx [--yes]
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from feishu_common import confirm_action_or_exit, create_client, print_json, extract_base_info, cli_run
import argparse


def main():
    parser = argparse.ArgumentParser(description="删除字段")
    parser.add_argument("--app", required=True, help="Base token 或 URL")
    parser.add_argument("--table", required=True, help="数据表 ID")
    parser.add_argument("--field", required=True, help="字段 ID")
    parser.add_argument("--yes", "-y", action="store_true", help="跳过确认")
    parser.add_argument("--raw", action="store_true", help="输出完整原始 JSON")
    args = parser.parse_args()

    app_token, table_id = extract_base_info(args.app)
    if not table_id and args.table:
        table_id = args.table
    if not table_id:
        raise RuntimeError("缺少 --table 参数，且 URL 中未包含 table_id")

    confirm_action_or_exit("base_delete", f"确认删除字段 {args.field}?", yes=args.yes)

    client = create_client()
    result = client.base_delete_field(app_token, table_id, args.field)
    if args.raw:
        print_json(result)
        return

    print_json({
        "status": "ok",
        "deleted": result.get("deleted", False),
        "field_id": result.get("field_id", args.field),
    })


if __name__ == "__main__":
    cli_run(main)
