#!/usr/bin/env python3
"""
base_data_query.py -- Base 数据查询（JSON DSL 聚合查询）

用法:
    # 按字段分组统计
    python3 base_data_query.py --app base_token --dsl '{"dimensions":[{"field_id":"fldStatus"}],"measures":[{"field_id":"fldAmount","aggregator":"SUM"}]}'

    # 从文件读取 DSL
    python3 base_data_query.py --app base_token --dsl-file query.json

DSL 示例:
{
  "dimensions": [{"field_id": "fldStatus"}],
  "measures": [{"field_id": "fldAmount", "aggregator": "SUM"}],
  "filter": {"logic": "and", "conditions": [["fldDate", ">=", "2024-01-01"]]}
}

常用 aggregator: SUM, AVG, MAX, MIN, COUNT
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from feishu_common import create_client, print_json, extract_base_info, cli_run
import argparse


def main():
    parser = argparse.ArgumentParser(description="Base 数据查询（JSON DSL 聚合查询）")
    parser.add_argument("--app", required=True, help="Base token 或 URL")
    parser.add_argument("--dsl", default=None, help="查询 DSL JSON 字符串")
    parser.add_argument("--dsl-file", default=None, help="查询 DSL JSON 文件路径")
    args = parser.parse_args()

    app_token, _ = extract_base_info(args.app)

    if args.dsl_file:
        with open(args.dsl_file, 'r', encoding='utf-8') as f:
            dsl = json.load(f)
    elif args.dsl:
        dsl = json.loads(args.dsl)
    else:
        raise RuntimeError("请提供 --dsl 或 --dsl-file 之一")

    if "dimensions" not in dsl and "measures" not in dsl:
        raise RuntimeError("DSL 必须包含 dimensions 或 measures 至少一个")

    client = create_client()
    result = client.base_query_data(app_token, dsl)
    print_json(result)


if __name__ == "__main__":
    cli_run(main)
