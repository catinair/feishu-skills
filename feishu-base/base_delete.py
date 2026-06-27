#!/usr/bin/env python3
"""
base_delete.py -- 删除多维表格记录

用法：
    python3 base_delete.py --app base_token_or_url --table table_id --record rec_xxx
    python3 base_delete.py --app base_token_or_url --table table_id --record rec_xxx --yes
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from feishu_common import create_client, print_json, extract_base_info, cli_run, confirm_action_or_exit


def main():
    parser = argparse.ArgumentParser(description="删除多维表格记录")
    parser.add_argument("--app", required=True, help="base token 或完整 URL")
    parser.add_argument("--table", help="数据表 ID（可选，默认从 URL 提取）")
    parser.add_argument("--record", required=True, help="记录 ID（record_id）")
    parser.add_argument("--yes", "-y", action="store_true", help="跳过确认")
    args = parser.parse_args()

    confirm_action_or_exit("base_delete", f"确认删除记录 {args.record}?", yes=args.yes)

    app_token, table_id_from_url = extract_base_info(args.app)
    table_id = args.table or table_id_from_url
    if not table_id:
        print("ERROR: 无法从 URL 提取 table_id，请手动指定 --table", file=sys.stderr)
        sys.exit(1)

    client = create_client()
    result = client.base_delete_record(app_token, table_id, args.record)
    print_json(result)


if __name__ == "__main__":
    cli_run(main)
