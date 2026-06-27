#!/usr/bin/env python3
"""
base_copy.py -- 复制多维表格

用法:
    python3 base_copy.py --app base_token_or_url --name "新表格名称"
    python3 base_copy.py --app base_token_or_url --name "新表格名称" --folder-token fldcnxxx
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from feishu_common import create_client, confirm_action_or_exit, print_json, extract_base_info, DEFAULT_FOLDER_TOKEN, cli_run, is_trusted_folder
import argparse


def main():
    parser = argparse.ArgumentParser(description="复制多维表格")
    parser.add_argument("--app", required=True, help="源 Base token 或 URL")
    parser.add_argument("--name", required=True, help="新表格名称")
    parser.add_argument("--folder-token", default=DEFAULT_FOLDER_TOKEN, help="目标文件夹 token（默认指定文件夹）")
    parser.add_argument("--yes", "-y", action="store_true", help="跳过确认")
    args = parser.parse_args()

    app_token, _ = extract_base_info(args.app)
    client = create_client()
    confirm_action_or_exit(
        "base_copy",
        f"确认复制多维表格 {app_token} 到文件夹 {args.folder_token}，新名称为「{args.name}」?",
        yes=args.yes,
        is_trusted=is_trusted_folder(args.folder_token),
    )
    result = client.base_copy(app_token, name=args.name, folder_token=args.folder_token)
    print_json(result)


if __name__ == "__main__":
    cli_run(main)
