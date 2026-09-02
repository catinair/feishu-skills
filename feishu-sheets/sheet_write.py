#!/usr/bin/env python3
"""
sheet_write.py -- 写入电子表格单元格
用法: python3 sheet_write.py --token shtcnxxx --sheet 0 --range A1:B2 --values '[["姓名","年龄"],["张三",25]]'
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from feishu_common import confirm_action_or_exit, create_client, print_json, cli_run
import argparse
import json
import sys

def main():
    parser = argparse.ArgumentParser(description="写入电子表格单元格")
    parser.add_argument("--token", required=True, help="表格 token")
    parser.add_argument("--sheet", required=True, help="sheet ID")
    parser.add_argument("--range", required=True, help="单元格范围，如 A1:B2")
    parser.add_argument("--values", required=True, help="二维数组 JSON 字符串")
    parser.add_argument("--raw", action="store_true", help="输出完整原始 JSON")
    parser.add_argument("--yes", "-y", action="store_true", help="跳过确认")
    args = parser.parse_args()

    values = json.loads(args.values)

    confirm_action_or_exit("sheet_write", f"确认写入 {args.token} 的 {args.range}?", yes=args.yes)

    client = create_client()
    result = client.sheet_write(args.token, args.sheet, args.range, values)

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
