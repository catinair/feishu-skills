#!/usr/bin/env python3
"""
sheet_append.py -- 向电子表格追加行
用法: python3 sheet_append.py --token shtcnxxx --sheet 0 --values '[["李四",30]]'
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from feishu_common import confirm_action_or_exit, create_client, print_json, cli_run
import argparse
import json
import sys

def main():
    parser = argparse.ArgumentParser(description="向电子表格追加行")
    parser.add_argument("--token", required=True, help="表格 token")
    parser.add_argument("--sheet", required=True, help="sheet ID")
    parser.add_argument("--values", required=True, help="二维数组 JSON 字符串")
    parser.add_argument("--raw", action="store_true", help="输出完整原始 JSON")
    parser.add_argument("--yes", "-y", action="store_true", help="跳过确认")
    args = parser.parse_args()

    values = json.loads(args.values)

    confirm_action_or_exit("sheet_append", f"确认向 {args.token} 追加行?", yes=args.yes)

    client = create_client()
    result = client.sheet_append(args.token, args.sheet, values)

    if args.raw:
        print_json(result)
        return

    print_json({
        "status": "ok",
        "spreadsheetToken": result.get("spreadsheetToken", ""),
        "sheetId": result.get("sheetId", ""),
        "range": result.get("range", ""),
    })

if __name__ == "__main__":
    cli_run(main)
