#!/usr/bin/env python3
"""
sheet_info.py -- 获取电子表格元数据（sheet_id、行列数等）
用法: python3 sheet_info.py --token shtcnxxx
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from feishu_common import create_client, print_json, cli_run
import argparse

def main():
    parser = argparse.ArgumentParser(description="获取电子表格元数据")
    parser.add_argument("--token", required=True, help="表格 token")
    args = parser.parse_args()

    client = create_client()
    result = client.sheet_get_info(args.token)
    print_json(result)

if __name__ == "__main__":
    cli_run(main)
