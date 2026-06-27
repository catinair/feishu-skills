#!/usr/bin/env python3
"""
base_view_rename.py -- 重命名视图

用法:
    python3 base_view_rename.py --app base_token_or_url --table table_id --view vew_xxx --name "新名称"
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from feishu_common import create_client, print_json, extract_base_info, cli_run
import argparse


def main():
    parser = argparse.ArgumentParser(description="重命名视图")
    parser.add_argument("--app", required=True, help="Base token 或 URL")
    parser.add_argument("--table", required=True, help="数据表 ID")
    parser.add_argument("--view", required=True, help="视图 ID")
    parser.add_argument("--name", required=True, help="新的视图名称")
    args = parser.parse_args()

    app_token, table_id = extract_base_info(args.app)
    if not table_id and args.table:
        table_id = args.table
    if not table_id:
        raise RuntimeError("缺少 --table 参数，且 URL 中未包含 table_id")

    client = create_client()
    result = client.base_rename_view(app_token, table_id, args.view, args.name)
    print_json(result)


if __name__ == "__main__":
    cli_run(main)
