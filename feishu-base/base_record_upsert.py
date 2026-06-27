#!/usr/bin/env python3
"""
base_record_upsert.py -- 更新或插入记录

用法:
    # 更新已有记录（提供 record_id）
    python3 base_record_upsert.py --app base_token_or_url --table table_id --record rec_xxx --fields '{"姓名": "李四"}'

    # 创建新记录（不提供 record_id）
    python3 base_record_upsert.py --app base_token_or_url --table table_id --fields '{"姓名": "张三", "电话": "13800138000"}'
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from feishu_common import create_client, confirm_action_or_exit, print_json, extract_base_info, cli_run
import argparse


def main():
    parser = argparse.ArgumentParser(description="更新或插入记录")
    parser.add_argument("--app", required=True, help="Base token 或 URL")
    parser.add_argument("--table", required=True, help="数据表 ID")
    parser.add_argument("--record", default=None, help="记录 ID（提供则更新，否则创建）")
    parser.add_argument("--fields", required=True, help="字段值 JSON 对象")
    parser.add_argument("--yes", "-y", action="store_true", help="跳过确认")
    args = parser.parse_args()

    app_token, table_id = extract_base_info(args.app)
    if not table_id and args.table:
        table_id = args.table
    if not table_id:
        raise RuntimeError("缺少 --table 参数，且 URL 中未包含 table_id")

    fields = json.loads(args.fields)

    client = create_client()
    action = "更新" if args.record else "创建"
    confirm_action_or_exit(
        "base_record_upsert",
        f"确认{action}数据表 {table_id} 中的记录?",
        yes=args.yes,
        is_trusted=False,
    )
    result = client.base_upsert_record(app_token, table_id, fields, record_id=args.record)
    print_json(result)


if __name__ == "__main__":
    cli_run(main)
