#!/usr/bin/env python3
"""
base_query.py -- 查询多维表格记录

用法:
  # 简单精确匹配：字段名=值（自动转为飞书 CurrentValue 格式）
  python3 base_query.py --app <url> --table <id> --filter "文档标题=CLI"

  # JSON filter（支持 contains 等高级操作符，自动走 POST search 接口）
  python3 base_query.py --app <url> --table <id> \
    --filter '{"conjunction":"and","conditions":[{"field_name":"文档标题","operator":"contains","value":["CLI"]}]}'

  # 原始 CurrentValue 格式（仅支持 = 精确匹配）
  python3 base_query.py --app <url> --table <id> \
    --filter 'CurrentValue.[fldGSFMs7u]="CLI"'

  # 无 filter 全量查询
  python3 base_query.py --app <url> --table <id>
"""

import sys, os, json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from feishu_common import create_client, print_json, extract_base_info, cli_run
import argparse


def _parse_filter(filter_str):
    """解析 --filter 参数，返回 (filter_type, filter_value)

    filter_type:
      - "simple": 简单 key=value 格式，转为 GET filter
      - "currentvalue": 原始 CurrentValue.[field]="value" 格式，直传 GET
      - "json": JSON 对象格式，走 POST search
    """
    if not filter_str:
        return None, None

    filter_str = filter_str.strip()

    # JSON 格式：以 { 开头
    if filter_str.startswith("{"):
        try:
            parsed = json.loads(filter_str)
            return "json", parsed
        except json.JSONDecodeError:
            pass

    # CurrentValue 格式：以 CurrentValue 开头
    if filter_str.startswith("CurrentValue"):
        return "currentvalue", filter_str

    # 简单 key=value 格式
    if "=" in filter_str:
        return "simple", filter_str

    # 默认当作 CurrentValue 格式
    return "currentvalue", filter_str


def main():
    parser = argparse.ArgumentParser(
        description="查询多维表格记录",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  --filter "文档标题=CLI"                                   # 简单精确匹配
  --filter '{"conjunction":"and","conditions":[...]}'       # JSON 高级过滤
  --filter 'CurrentValue.[fldxxx]="值"'                     # 原始 CurrentValue 格式
        """,
    )
    parser.add_argument("--app", required=True, help="base token 或完整 URL")
    parser.add_argument("--table", help="数据表 ID（可选，默认从 URL 提取）")
    parser.add_argument(
        "--filter",
        help="筛选条件。支持三种格式：\n"
        "  1) 简单格式: 字段名=值（如 '文档标题=CLI'）\n"
        "  2) JSON 格式: 飞书 filter_info 对象（自动走 POST search 接口，支持 contains 等高级操作符）\n"
        '  3) CurrentValue 格式: CurrentValue.[字段]="值"（仅支持 = 精确匹配，兼容旧用法）',
    )
    parser.add_argument("--page-size", type=int, default=500, help="每页数量")
    parser.add_argument("--max-results", type=int, help="最大返回条数（默认不限制）")
    args = parser.parse_args()

    app_token, table_id_from_url = extract_base_info(args.app)
    table_id = args.table or table_id_from_url
    if not table_id:
        print("ERROR: 无法从 URL 提取 table_id，请手动指定 --table", file=sys.stderr)
        sys.exit(1)

    client = create_client()
    filter_type, filter_value = _parse_filter(args.filter)

    if filter_type == "json":
        # JSON 格式：走 POST /records/search 接口
        result = client.base_search_records(
            app_token,
            table_id,
            filter=filter_value,
            page_size=args.page_size,
            max_results=args.max_results,
        )
        # base_search_records 返回 {"items": [...]}，统一为 {"records": [...]}
        result["records"] = result.pop("items", [])
    elif filter_type == "simple":
        # 简单 key=value 格式：转为 CurrentValue 表达式
        key, _, value = filter_value.partition("=")
        key = key.strip()
        value = value.strip()
        filter_expr = f'CurrentValue.[{key}]="{value}"'
        result = client.base_query_records(
            app_token,
            table_id,
            page_size=args.page_size,
            filter_expr=filter_expr,
            max_results=args.max_results,
        )
    elif filter_type == "currentvalue":
        # CurrentValue 格式：直传
        result = client.base_query_records(
            app_token,
            table_id,
            page_size=args.page_size,
            filter_expr=filter_value,
            max_results=args.max_results,
        )
    else:
        # 无 filter，全量查询
        result = client.base_query_records(
            app_token,
            table_id,
            page_size=args.page_size,
            max_results=args.max_results,
        )

    print_json(result)


if __name__ == "__main__":
    cli_run(main)
