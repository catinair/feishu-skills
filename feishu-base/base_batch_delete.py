#!/usr/bin/env python3
"""
base_batch_delete.py -- 批量删除多维表格记录

用法:
    python3 base_batch_delete.py --app base_token_or_url --table table_id --records rec1,rec2,rec3
    python3 base_batch_delete.py --app base_token_or_url --table table_id --records-file record_ids.json

record_ids.json 格式：
["rec_xxx", "rec_yyy", "rec_zzz"]
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from feishu_common import create_client, print_json, extract_base_info, cli_run, confirm_action_or_exit
import argparse


def main():
    parser = argparse.ArgumentParser(description="批量删除记录")
    parser.add_argument("--app", required=True, help="Base token 或 URL")
    parser.add_argument("--table", required=True, help="数据表 ID")
    parser.add_argument("--records", help="逗号分隔的 record_id 列表")
    parser.add_argument("--records-file", help="record_id 数组 JSON 文件路径")
    parser.add_argument("--yes", "-y", action="store_true", help="跳过确认")
    parser.add_argument("--raw", action="store_true", help="输出完整原始 JSON")
    args = parser.parse_args()

    app_token, table_id = extract_base_info(args.app)
    if not table_id and args.table:
        table_id = args.table
    if not table_id:
        raise RuntimeError("缺少 --table 参数，且 URL 中未包含 table_id")

    record_ids = []
    if args.records:
        record_ids = [r.strip() for r in args.records.split(",") if r.strip()]
    elif args.records_file:
        with open(args.records_file, 'r', encoding='utf-8') as f:
            record_ids = json.load(f)
    else:
        raise RuntimeError("请提供 --records 或 --records-file")

    if not record_ids:
        raise RuntimeError("record_id 列表为空")

    confirm_action_or_exit("base_batch_delete", f"确认删除 {len(record_ids)} 条记录?", yes=args.yes)

    client = create_client()
    result = client.base_batch_delete_records(app_token, table_id, record_ids)
    if args.raw:
        print_json(result)
        return

    print_json({
        "status": "ok",
        "deleted": result.get("deleted", 0),
        "record_ids": result.get("record_ids", []),
    })


if __name__ == "__main__":
    cli_run(main)
