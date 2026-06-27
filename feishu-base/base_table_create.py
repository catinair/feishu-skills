#!/usr/bin/env python3
"""
base_table_create.py -- 在多维表格中创建数据表

用法:
    python3 base_table_create.py --app base_token_or_url --name "新表名"
    python3 base_table_create.py --app base_token_or_url --name "新表名" --fields-file fields.json

fields.json 示例：
[
    {"field_name": "姓名", "type": 1},
    {"field_name": "年龄", "type": 2},
    {"field_name": "状态", "type": 3, "property": {"options": [{"name": "在职"}, {"name": "离职"}]}}
]
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from feishu_common import create_client, confirm_action_or_exit, print_json, extract_base_info, cli_run
import argparse


def main():
    parser = argparse.ArgumentParser(description="在多维表格中创建数据表")
    parser.add_argument("--app", required=True, help="Base token 或 URL")
    parser.add_argument("--name", required=True, help="数据表名称")
    parser.add_argument("--fields-file", help="字段定义 JSON 文件路径（可选）")
    parser.add_argument("--yes", "-y", action="store_true", help="跳过确认")
    args = parser.parse_args()

    app_token, _ = extract_base_info(args.app)
    fields = None
    if args.fields_file:
        with open(args.fields_file, 'r', encoding='utf-8') as f:
            fields = json.load(f)

    client = create_client()
    confirm_action_or_exit(
        "base_table_create",
        f"确认在多维表格 {app_token} 中创建数据表「{args.name}」?",
        yes=args.yes,
        is_trusted=False,
    )
    result = client.base_create_table(app_token, name=args.name, fields=fields)
    print_json(result)


if __name__ == "__main__":
    cli_run(main)
