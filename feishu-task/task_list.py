#!/usr/bin/env python3
"""
task_list.py -- 列取当前用户负责的飞书任务（需 user_access_token）
用法: python3 task_list.py [--completed true|false] [--start 2026-07-01T00:00:00+08:00] [--end 2026-08-01T00:00:00+08:00]
"""

import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from feishu_common import cli_run, create_client, print_json
import argparse


def main():
    parser = argparse.ArgumentParser(description="列取当前用户负责的飞书任务")
    parser.add_argument(
        "--completed", choices=["true", "false"], help="过滤：true=已完成 false=未完成"
    )
    parser.add_argument("--start", help="创建时间起点：秒级时间戳或 ISO 字符串")
    parser.add_argument("--end", help="创建时间终点：秒级时间戳或 ISO 字符串")
    parser.add_argument("--page-size", type=int, default=50, help="每页数量（1-100）")
    parser.add_argument("--max", type=int, help="最大返回条数")
    args = parser.parse_args()

    completed = None
    if args.completed == "true":
        completed = True
    elif args.completed == "false":
        completed = False

    client = create_client()
    result = client.task_list(
        completed=completed,
        page_size=args.page_size,
        max_results=args.max,
        start_time=args.start,
        end_time=args.end,
    )
    print_json(result)


if __name__ == "__main__":
    cli_run(main)
