#!/usr/bin/env python3
"""
task_comment_list.py -- 获取飞书任务的评论列表
用法:
  python3 task_comment_list.py --resource-id <task_guid>
  python3 task_comment_list.py --resource-id <task_guid> --direction desc --max 10
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from feishu_common import cli_run, create_client, print_json
import argparse

def main():
    parser = argparse.ArgumentParser(description="获取飞书任务的评论列表")
    parser.add_argument("--resource-id", required=True, help="任务 GUID")
    parser.add_argument("--direction", default="asc", choices=["asc", "desc"], help="排序方式")
    parser.add_argument("--page-size", type=int, default=50, help="每页数量（1-100）")
    parser.add_argument("--max", type=int, help="最大返回条数")
    args = parser.parse_args()

    client = create_client()
    result = client.task_comment_list(
        resource_id=args.resource_id,
        direction=args.direction,
        page_size=args.page_size,
        max_results=args.max,
    )
    print_json(result)

if __name__ == "__main__":
    cli_run(main)
