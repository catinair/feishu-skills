#!/usr/bin/env python3
"""
base_field_create.py -- 创建字段

用法:
    python3 base_field_create.py --app base_token_or_url --table table_id --name "字段名" --type 1
    python3 base_field_create.py --app base_token_or_url --table table_id --name "状态" --type 3 --property '{"options": [{"name": "选项A", "color": 0}]}'

常见字段类型：
  1=文本, 2=数字, 3=单选, 4=多选, 5=日期, 7=复选框, 11=人员, 13=电话, 15=超链接, 17=附件
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from feishu_common import create_client, confirm_action_or_exit, print_json, extract_base_info, cli_run
import argparse


def main():
    parser = argparse.ArgumentParser(description="创建字段")
    parser.add_argument("--app", required=True, help="Base token 或 URL")
    parser.add_argument("--table", required=True, help="数据表 ID")
    parser.add_argument("--name", required=True, help="字段名称")
    parser.add_argument("--type", required=True, type=int, help="字段类型编号（如 1=文本, 3=单选）")
    parser.add_argument("--ui-type", default=None, help="UI 类型，如 Text, Email, Phone, Url, Rating 等")
    parser.add_argument("--property", default=None, help="字段属性 JSON（如单选选项、数字格式等）")
    parser.add_argument("--yes", "-y", action="store_true", help="跳过确认")
    parser.add_argument("--raw", action="store_true", help="输出完整原始 JSON")
    args = parser.parse_args()

    app_token, table_id = extract_base_info(args.app)
    if not table_id and args.table:
        table_id = args.table
    if not table_id:
        raise RuntimeError("缺少 --table 参数，且 URL 中未包含 table_id")

    property_obj = None
    if args.property:
        property_obj = json.loads(args.property)

    client = create_client()
    confirm_action_or_exit(
        "base_field_create",
        f"确认在数据表 {table_id} 中创建字段「{args.name}」(类型 {args.type})?",
        yes=args.yes,
        is_trusted=False,
    )
    result = client.base_create_field(app_token, table_id, args.name, args.type, ui_type=args.ui_type, property=property_obj)
    if args.raw:
        print_json(result)
        return

    field = result.get("field", result) if isinstance(result, dict) else {}
    print_json({
        "status": "ok",
        "field_id": field.get("field_id", ""),
        "field_name": field.get("field_name", ""),
        "type": field.get("type"),
    })


if __name__ == "__main__":
    cli_run(main)
