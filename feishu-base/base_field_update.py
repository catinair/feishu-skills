#!/usr/bin/env python3
"""
base_field_update.py -- 更新字段

用法:
    python3 base_field_update.py --app base_token_or_url --table table_id --field fld_xxx --name "新字段名"
    python3 base_field_update.py --app base_token_or_url --table table_id --field fld_xxx --property '{"options": [{"name": "新选项", "color": 1}]}'
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from feishu_common import create_client, print_json, extract_base_info, cli_run
import argparse


def main():
    parser = argparse.ArgumentParser(description="更新字段")
    parser.add_argument("--app", required=True, help="Base token 或 URL")
    parser.add_argument("--table", required=True, help="数据表 ID")
    parser.add_argument("--field", required=True, help="字段 ID")
    parser.add_argument("--name", default=None, help="新的字段名称")
    parser.add_argument("--type", default=None, type=int, help="字段类型编号（如 1=文本, 3=单选）")
    parser.add_argument("--property", default=None, help="字段属性 JSON")
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
    result = client.base_update_field(app_token, table_id, args.field, field_name=args.name, field_type=args.type, property=property_obj)
    print_json(result)


if __name__ == "__main__":
    cli_run(main)
