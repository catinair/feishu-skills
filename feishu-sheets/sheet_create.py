#!/usr/bin/env python3
"""
sheet_create.py -- 创建电子表格
用法: python3 sheet_create.py --title "表格名称" [--folder-token fldcnxxx]
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from feishu_common import DEFAULT_FOLDER_TOKEN, cli_run, confirm_action_or_exit, create_client, is_trusted_folder, print_json
import argparse

def main():
    parser = argparse.ArgumentParser(description="创建电子表格")
    parser.add_argument("--title", help="表格标题")
    parser.add_argument("--folder-token", default=DEFAULT_FOLDER_TOKEN, help="父文件夹 token（可选，默认指定文件夹）")
    parser.add_argument("--yes", "-y", action="store_true", help="跳过确认")
    parser.add_argument("--raw", action="store_true", help="输出完整原始 JSON")
    args = parser.parse_args()

    client = create_client()
    confirm_action_or_exit(
        "sheet_create",
        f"确认在文件夹 {args.folder_token} 下创建电子表格「{args.title or '未命名'}」?",
        yes=args.yes,
        is_trusted=is_trusted_folder(args.folder_token),
    )
    result = client.sheet_create(title=args.title, folder_token=args.folder_token)
    if args.raw:
        print_json(result)
        return

    spreadsheet = result if isinstance(result, dict) else {}
    print_json({
        "status": "ok",
        "spreadsheet_token": spreadsheet.get("spreadsheet_token", ""),
        "title": spreadsheet.get("title", ""),
        "url": spreadsheet.get("url", ""),
    })

if __name__ == "__main__":
    cli_run(main)
