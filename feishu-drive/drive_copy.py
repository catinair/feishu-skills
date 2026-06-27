#!/usr/bin/env python3
"""
drive_copy.py -- 复制文件到目标文件夹
用法: python3 drive_copy.py --file-token xxx --name "副本" --type docx --folder-token fldcnxxx
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from feishu_common import DEFAULT_FOLDER_TOKEN, cli_run, confirm_action_or_exit, create_client, is_trusted_folder, print_json
import argparse

def main():
    parser = argparse.ArgumentParser(description="复制文件")
    parser.add_argument("--file-token", required=True, help="源文件 token")
    parser.add_argument("--name", required=True, help="新文件名称")
    parser.add_argument("--type", required=True, help="文件类型：docx/sheet/bitable/file/doc/mindnote/slides")
    parser.add_argument("--folder-token", default=DEFAULT_FOLDER_TOKEN, help="目标文件夹 token（可选，默认指定文件夹）")
    parser.add_argument("--yes", "-y", action="store_true", help="跳过确认")
    args = parser.parse_args()

    client = create_client()
    confirm_action_or_exit(
        "drive_copy",
        f"确认复制文件 {args.file_token} 到文件夹 {args.folder_token}，新名称为「{args.name}」?",
        yes=args.yes,
        is_trusted=is_trusted_folder(args.folder_token),
    )
    result = client.copy_file(args.file_token, args.name, args.type, args.folder_token)
    print_json(result)

if __name__ == "__main__":
    cli_run(main)
