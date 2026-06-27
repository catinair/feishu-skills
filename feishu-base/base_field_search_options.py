#!/usr/bin/env python3
"""
base_field_search_options.py -- 搜索字段选项（适用于单选/多选字段）

用法:
    # 列出字段所有选项
    python3 base_field_search_options.py --app base_token_or_url --table table_id --field fld_xxx

    # 按关键词搜索选项
    python3 base_field_search_options.py --app base_token_or_url --table table_id --field fld_xxx --keyword "选项A"
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from feishu_common import create_client, print_json, extract_base_info, cli_run
import argparse


def main():
    parser = argparse.ArgumentParser(description="搜索字段选项")
    parser.add_argument("--app", required=True, help="Base token 或 URL")
    parser.add_argument("--table", required=True, help="数据表 ID")
    parser.add_argument("--field", required=True, help="字段 ID")
    parser.add_argument("--keyword", default=None, help="搜索关键词")
    parser.add_argument("--offset", type=int, default=0, help="分页偏移（默认 0）")
    parser.add_argument("--limit", type=int, default=30, help="分页大小（默认 30）")
    args = parser.parse_args()

    app_token, table_id = extract_base_info(args.app)
    if not table_id and args.table:
        table_id = args.table
    if not table_id:
        raise RuntimeError("缺少 --table 参数，且 URL 中未包含 table_id")

    client = create_client()
    result = client.base_search_field_options(
        app_token, table_id, args.field,
        keyword=args.keyword, offset=args.offset, limit=args.limit
    )
    print_json(result)


if __name__ == "__main__":
    cli_run(main)
