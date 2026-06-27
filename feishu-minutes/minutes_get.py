#!/usr/bin/env python3
"""
minutes_get.py -- 获取飞书妙记基本信息
用法: python3 minutes_get.py --token obcnxxx
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from feishu_common import cli_run, create_client, print_json
import argparse


def main():
    parser = argparse.ArgumentParser(description="获取妙记基本信息")
    parser.add_argument("--token", required=True, help="妙记 token（从妙记 URL 中获取）")
    args = parser.parse_args()

    client = create_client()
    result = client.minutes_get(args.token)
    print_json(result)


if __name__ == "__main__":
    cli_run(main)
