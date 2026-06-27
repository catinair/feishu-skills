#!/usr/bin/env python3
"""
task_get.py -- 获取飞书任务详情
用法: python3 task_get.py --guid <task_guid>
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from feishu_common import cli_run, create_client, print_json
import argparse

def main():
    parser = argparse.ArgumentParser(description="获取飞书任务详情")
    parser.add_argument("--guid", required=True, help="任务 GUID")
    args = parser.parse_args()

    client = create_client()
    result = client.task_get(task_guid=args.guid)
    print_json(result)

if __name__ == "__main__":
    cli_run(main)
