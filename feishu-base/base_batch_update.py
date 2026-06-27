#!/usr/bin/env python3
"""
base_batch_update.py -- 批量更新多维表格记录

用法:
    python3 base_batch_update.py --app base_token_or_url --table table_id --records-file records.json

records.json 格式：
[
    {"record_id": "rec_xxx", "fields": {"姓名": "张三", "状态": "在职"}},
    {"record_id": "rec_yyy", "fields": {"姓名": "李四", "状态": "离职"}}
]
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from feishu_common import create_client, print_json, extract_base_info, cli_run, confirm_action_or_exit
import argparse


def main():
    parser = argparse.ArgumentParser(description="批量更新记录")
    parser.add_argument("--app", required=True, help="Base token 或 URL")
    parser.add_argument("--table", required=True, help="数据表 ID")
    parser.add_argument("--records-file", required=True, help="记录数据 JSON 文件路径")
    parser.add_argument("--yes", "-y", action="store_true", help="跳过确认")
    args = parser.parse_args()

    with open(args.records_file, 'r', encoding='utf-8') as f:
        records = json.load(f)

    confirm_action_or_exit("base_batch_update", f"确认批量更新 {len(records)} 条记录?", yes=args.yes)

    app_token, table_id = extract_base_info(args.app)
    if not table_id and args.table:
        table_id = args.table
    if not table_id:
        raise RuntimeError("缺少 --table 参数，且 URL 中未包含 table_id")

    client = create_client()
    result = client.base_batch_update_records(app_token, table_id, records)
    print_json({"updated": len(result), "records": result})


if __name__ == "__main__":
    cli_run(main)
