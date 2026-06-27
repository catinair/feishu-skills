#!/usr/bin/env python3
"""
minutes_statistics.py -- 获取飞书妙记访问统计
用法: python3 minutes_statistics.py --token obcnxxx
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from feishu_common import cli_run, create_client, print_json
import argparse


def main():
    parser = argparse.ArgumentParser(description="获取妙记访问统计数据")
    parser.add_argument("--token", required=True, help="妙记 token")
    args = parser.parse_args()

    client = create_client()
    result = client.minutes_statistics(args.token)
    print_json(result)


if __name__ == "__main__":
    cli_run(main)
