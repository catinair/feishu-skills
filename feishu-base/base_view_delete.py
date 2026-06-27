#!/usr/bin/env python3
"""
base_view_delete.py -- 删除视图

用法:
    python3 base_view_delete.py --app base_token_or_url --table table_id --view vew_xxx [--yes]
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from feishu_common import confirm_action_or_exit, create_client, print_json, extract_base_info, cli_run
import argparse


def main():
    parser = argparse.ArgumentParser(description="删除视图")
    parser.add_argument("--app", required=True, help="Base token 或 URL")
    parser.add_argument("--table", required=True, help="数据表 ID")
    parser.add_argument("--view", required=True, help="视图 ID")
    parser.add_argument("--yes", "-y", action="store_true", help="跳过确认")
    args = parser.parse_args()

    app_token, table_id = extract_base_info(args.app)
    if not table_id and args.table:
        table_id = args.table
    if not table_id:
        raise RuntimeError("缺少 --table 参数，且 URL 中未包含 table_id")

    confirm_action_or_exit("base_delete", f"确认删除视图 {args.view}?", yes=args.yes)

    client = create_client()
    result = client.base_delete_view(app_token, table_id, args.view)
    print_json(result)


if __name__ == "__main__":
    cli_run(main)
