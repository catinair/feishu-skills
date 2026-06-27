#!/usr/bin/env python3
"""
base_update.py -- 更新多维表格记录

用法：
    python3 base_update.py --app base_token_or_url --table table_id --record rec_xxx --fields '{"字段名": "新值"}'
    python3 base_update.py --app base_token_or_url --table table_id --record rec_xxx --fields-file update.json
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from feishu_common import create_client, print_json, extract_base_info, cli_run, confirm_action_or_exit


def main():
    parser = argparse.ArgumentParser(description="更新多维表格记录")
    parser.add_argument("--app", required=True, help="base token 或完整 URL")
    parser.add_argument("--table", help="数据表 ID（可选，默认从 URL 提取）")
    parser.add_argument("--record", required=True, help="记录 ID（record_id）")
    parser.add_argument("--fields", help="字段值 JSON 字符串（与 --fields-file 二选一）")
    parser.add_argument("--fields-file", help="字段值 JSON 文件路径（与 --fields 二选一）")
    parser.add_argument("--yes", "-y", action="store_true", help="跳过确认")
    args = parser.parse_args()

    fields = None
    if args.fields_file:
        with open(args.fields_file, "r", encoding="utf-8") as f:
            fields = json.load(f)
    elif args.fields:
        fields = json.loads(args.fields)
    else:
        print("ERROR: --fields 或 --fields-file 必须指定一个", file=sys.stderr)
        sys.exit(1)

    confirm_action_or_exit("base_update", f"确认更新记录 {args.record}?", yes=args.yes)

    app_token, table_id_from_url = extract_base_info(args.app)
    table_id = args.table or table_id_from_url
    if not table_id:
        print("ERROR: 无法从 URL 提取 table_id，请手动指定 --table", file=sys.stderr)
        sys.exit(1)

    client = create_client()
    result = client.base_update_record(app_token, table_id, args.record, fields)
    print_json(result)


if __name__ == "__main__":
    cli_run(main)
