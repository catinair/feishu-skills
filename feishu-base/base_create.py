#!/usr/bin/env python3
"""
base_create.py -- 创建多维表格
用法: python3 base_create.py --name "表格名称" [--folder-token fldcnxxx]
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from feishu_common import DEFAULT_FOLDER_TOKEN, cli_run, confirm_action_or_exit, create_client, is_trusted_folder, print_json
import argparse

def main():
    parser = argparse.ArgumentParser(description="创建多维表格")
    parser.add_argument("--name", required=True, help="多维表格名称")
    parser.add_argument("--folder-token", default=DEFAULT_FOLDER_TOKEN, help="父文件夹 token（可选，默认指定文件夹）")
    parser.add_argument("--yes", "-y", action="store_true", help="跳过确认")
    parser.add_argument("--raw", action="store_true", help="输出完整原始 JSON")
    args = parser.parse_args()

    client = create_client()
    confirm_action_or_exit(
        "base_create",
        f"确认在文件夹 {args.folder_token} 下创建多维表格「{args.name}」?",
        yes=args.yes,
        is_trusted=is_trusted_folder(args.folder_token),
    )
    result = client.base_create(name=args.name, folder_token=args.folder_token)
    if args.raw:
        print_json(result)
        return

    print_json({
        "status": "ok",
        "app_token": result.get("app_token", ""),
        "name": result.get("name", ""),
    })

if __name__ == "__main__":
    cli_run(main)
