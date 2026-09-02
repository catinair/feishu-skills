#!/usr/bin/env python3
"""
base_record_download_attachment.py -- 下载记录中的附件到本地

用法:
    # 下载记录中所有附件字段的文件
    python3 base_record_download_attachment.py       --app base_token_or_url       --table table_id       --record rec_xxx       --output ./downloads

    # 只下载指定字段的附件
    python3 base_record_download_attachment.py       --app base_token_or_url       --table table_id       --record rec_xxx       --field "附件"       --output ./downloads
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from feishu_common import create_client, print_json, extract_base_info, cli_run
import argparse


def main():
    parser = argparse.ArgumentParser(description="下载记录附件到本地")
    parser.add_argument("--app", required=True, help="Base token 或 URL")
    parser.add_argument("--table", required=True, help="数据表 ID")
    parser.add_argument("--record", required=True, help="记录 ID")
    parser.add_argument("--field", default=None, help="附件字段名称（不传则下载所有附件字段）")
    parser.add_argument("--output", "-o", default="./downloads", help="输出目录（默认 ./downloads）")
    args = parser.parse_args()

    app_token, table_id = extract_base_info(args.app)
    if not table_id and args.table:
        table_id = args.table
    if not table_id:
        raise RuntimeError("缺少 --table 参数，且 URL 中未包含 table_id")

    client = create_client()
    result = client.base_download_attachments(
        app_token, table_id, args.record,
        field_name=args.field,
        output_dir=args.output,
    )
    print_json(result)


if __name__ == "__main__":
    cli_run(main)
