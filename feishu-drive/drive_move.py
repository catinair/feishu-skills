#!/usr/bin/env python3
"""
drive_move.py -- 移动文件到目标文件夹
用法: python3 drive_move.py --file-token xxx --type file --target-folder-token fldcnxxx
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from feishu_common import create_client, confirm_action_or_exit, print_json, cli_run, is_trusted_folder
import argparse


def main():
    parser = argparse.ArgumentParser(description="移动文件到目标文件夹")
    parser.add_argument("--file-token", required=True, help="文件 token")
    parser.add_argument("--type", required=True, help="文件类型：docx/sheet/bitable/file/folder/doc/mindnote/slides")
    parser.add_argument("--target-folder-token", required=True, help="目标文件夹 token")
    parser.add_argument("--yes", "-y", action="store_true", help="跳过确认")
    parser.add_argument("--raw", action="store_true", help="输出完整原始 JSON")
    args = parser.parse_args()

    client = create_client()
    confirm_action_or_exit(
        "drive_move",
        f"确认移动文件 {args.file_token} 到文件夹 {args.target_folder_token}?",
        yes=args.yes,
        is_trusted=is_trusted_folder(args.target_folder_token),
    )
    result = client.move_file(args.file_token, args.type, args.target_folder_token)
    if args.raw:
        print_json(result)
        return

    file_info = result if isinstance(result, dict) else {}
    print_json({
        "status": "ok",
        "file_token": file_info.get("token", ""),
        "name": file_info.get("name", ""),
        "type": file_info.get("type", ""),
    })


if __name__ == "__main__":
    cli_run(main)
