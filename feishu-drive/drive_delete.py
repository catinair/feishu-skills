#!/usr/bin/env python3
"""
drive_delete.py -- 删除文件或文件夹
用法: python3 drive_delete.py --file-token xxx --type file --yes
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from feishu_common import create_client, cli_run, confirm_action_or_exit
import argparse


def main():
    parser = argparse.ArgumentParser(description="删除飞书云空间中的文件或文件夹")
    parser.add_argument("--file-token", required=True, help="文件 token")
    parser.add_argument("--type", required=True, help="文件类型：docx/sheet/bitable/file/folder/doc/mindnote/slides")
    parser.add_argument("--yes", "-y", action="store_true", help="跳过确认提示（仍保留风险警告）")
    args = parser.parse_args()

    # drive_delete 在 risk_policy 中标记为 manual_only；
    # confirm_action_or_exit 会要求输入 YES 确认，--yes 可显式绕过
    confirm_action_or_exit(
        "drive_delete",
        f"确认删除 {args.type} 类型文件/文件夹 {args.file_token}？此操作不可恢复。",
        yes=args.yes,
        is_trusted=False,
    )

    client = create_client()
    result = client.delete_file(args.file_token, args.type)
    print(f"已删除: {args.file_token}")
    print(result)


if __name__ == "__main__":
    cli_run(main)
