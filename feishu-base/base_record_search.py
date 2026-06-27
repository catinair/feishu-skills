#!/usr/bin/env python3
"""
base_record_search.py -- 高级搜索记录（支持复杂 filter/sort）

用法:
    # 基础搜索（查询所有）
    python3 base_record_search.py --app base_token_or_url --table table_id

    # 带筛选条件
    python3 base_record_search.py --app base_token --table table_id       --filter '{"conjunction": "and", "conditions": [{"field_name": "状态", "operator": "is", "value": ["进行中"]}]}'

    # 带筛选+排序+指定返回字段
    python3 base_record_search.py --app base_token --table table_id       --filter-file filter.json       --sort '[{"field_name": "日期", "desc": false}]'       --fields '["姓名", "电话", "日期"]'

filter.json 示例：
{
  "conjunction": "and",
  "conditions": [
    {"field_name": "状态", "operator": "is", "value": ["进行中"]},
    {"field_name": "截止日期", "operator": "isLess", "value": ["ExactDate", "1772121600000"]}
  ]
}

常用 operator: is, isNot, contains, doesNotContain, isEmpty, isNotEmpty, isGreater, isGreaterEqual, isLess, isLessEqual
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from feishu_common import create_client, print_json, extract_base_info, cli_run
import argparse


def main():
    parser = argparse.ArgumentParser(description="高级搜索记录")
    parser.add_argument("--app", required=True, help="Base token 或 URL")
    parser.add_argument("--table", required=True, help="数据表 ID")
    parser.add_argument("--filter", default=None, help="筛选条件 JSON 字符串")
    parser.add_argument("--filter-file", default=None, help="筛选条件 JSON 文件路径")
    parser.add_argument("--sort", default=None, help="排序规则 JSON 字符串")
    parser.add_argument("--fields", default=None, help="指定返回字段名数组 JSON")
    parser.add_argument("--page-size", type=int, default=500, help="每页条数（最大 500，默认 500）")
    args = parser.parse_args()

    app_token, table_id = extract_base_info(args.app)
    if not table_id and args.table:
        table_id = args.table
    if not table_id:
        raise RuntimeError("缺少 --table 参数，且 URL 中未包含 table_id")

    filter_obj = None
    if args.filter_file:
        with open(args.filter_file, 'r', encoding='utf-8') as f:
            filter_obj = json.load(f)
    elif args.filter:
        filter_obj = json.loads(args.filter)

    sort_obj = None
    if args.sort:
        sort_obj = json.loads(args.sort)

    field_names = None
    if args.fields:
        field_names = json.loads(args.fields)

    client = create_client()
    result = client.base_search_records(app_token, table_id, filter=filter_obj, sort=sort_obj, field_names=field_names, page_size=args.page_size)
    print_json(result)


if __name__ == "__main__":
    cli_run(main)
