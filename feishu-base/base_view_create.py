#!/usr/bin/env python3
"""
base_view_create.py -- 创建视图

用法:
    python3 base_view_create.py --app base_token_or_url --table table_id --name "新视图" --type grid

视图类型: grid(表格), kanban(看板), gallery(画册), gantt(甘特图)
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from feishu_common import create_client, confirm_action_or_exit, print_json, extract_base_info, cli_run
import argparse


def main():
    parser = argparse.ArgumentParser(description="创建视图")
    parser.add_argument("--app", required=True, help="Base token 或 URL")
    parser.add_argument("--table", required=True, help="数据表 ID")
    parser.add_argument("--name", required=True, help="视图名称")
    parser.add_argument("--type", default="grid", help="视图类型: grid/kanban/gallery/gantt（默认 grid）")
    parser.add_argument("--yes", "-y", action="store_true", help="跳过确认")
    args = parser.parse_args()

    app_token, table_id = extract_base_info(args.app)
    if not table_id and args.table:
        table_id = args.table
    if not table_id:
        raise RuntimeError("缺少 --table 参数，且 URL 中未包含 table_id")

    client = create_client()
    confirm_action_or_exit(
        "base_view_create",
        f"确认在数据表 {table_id} 中创建{args.type}视图「{args.name}」?",
        yes=args.yes,
        is_trusted=False,
    )
    result = client.base_create_view(app_token, table_id, args.name, args.type)
    print_json(result)


if __name__ == "__main__":
    cli_run(main)
