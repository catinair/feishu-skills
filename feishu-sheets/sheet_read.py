#!/usr/bin/env python3
"""
sheet_read.py -- 读取电子表格单元格
用法: python3 sheet_read.py --token shtcnxxx --sheet 0 --range A1:B10
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from feishu_common import create_client, print_json, cli_run
import argparse

def main():
    parser = argparse.ArgumentParser(description="读取电子表格单元格")
    parser.add_argument("--token", required=True, help="表格 token")
    parser.add_argument("--sheet", required=True, help="sheet ID（可从 sheet_info.py 获取）")
    parser.add_argument("--range", required=True, help="单元格范围，如 A1:B10")
    args = parser.parse_args()

    client = create_client()
    result = client.sheet_read(args.token, args.sheet, args.range)
    print_json(result)

if __name__ == "__main__":
    cli_run(main)
