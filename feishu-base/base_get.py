#!/usr/bin/env python3
"""
base_get.py -- 获取多维表格信息

用法:
    python3 base_get.py --app base_token_or_url
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from feishu_common import create_client, print_json, extract_base_info, cli_run
import argparse


def main():
    parser = argparse.ArgumentParser(description="获取多维表格信息")
    parser.add_argument("--app", required=True, help="Base token 或 URL")
    args = parser.parse_args()

    app_token, _ = extract_base_info(args.app)
    client = create_client()
    result = client.base_get(app_token)
    print_json(result)


if __name__ == "__main__":
    cli_run(main)
