#!/usr/bin/env python3
"""
base_record_upload_attachment.py -- 上传附件到记录的指定字段

用法:
    python3 base_record_upload_attachment.py       --app base_token_or_url       --table table_id       --record rec_xxx       --field "附件"       --path ./document.pdf
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from feishu_common import create_client, confirm_action_or_exit, print_json, extract_base_info, cli_run
import argparse


def main():
    parser = argparse.ArgumentParser(description="上传附件到记录字段")
    parser.add_argument("--app", required=True, help="Base token 或 URL")
    parser.add_argument("--table", required=True, help="数据表 ID")
    parser.add_argument("--record", required=True, help="记录 ID")
    parser.add_argument("--field", required=True, help="附件字段名称")
    parser.add_argument("--path", required=True, help="本地文件路径")
    parser.add_argument("--yes", "-y", action="store_true", help="跳过确认")
    args = parser.parse_args()

    app_token, table_id = extract_base_info(args.app)
    if not table_id and args.table:
        table_id = args.table
    if not table_id:
        raise RuntimeError("缺少 --table 参数，且 URL 中未包含 table_id")

    client = create_client()
    confirm_action_or_exit(
        "base_record_upload_attachment",
        f"确认上传文件 {args.path} 到记录 {args.record} 的字段「{args.field}」?",
        yes=args.yes,
        is_trusted=False,
    )
    result = client.base_upload_attachment(app_token, table_id, args.record, args.field, args.path)
    print_json(result)


if __name__ == "__main__":
    cli_run(main)
