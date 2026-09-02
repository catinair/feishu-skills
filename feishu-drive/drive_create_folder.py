#!/usr/bin/env python3
"""
drive_create_folder.py -- 创建飞书云文档文件夹

用法：
    python3 drive_create_folder.py "新项目资料"
    python3 drive_create_folder.py "子文件夹" --parent FzThf8mdGlv2lMdPSjLclpxpnmu
    python3 drive_create_folder.py "应用根文件夹" --parent "" --identity tenant

安全提示：
    在默认文件夹内创建免确认；其他位置会提示确认。
    --parent 传空字符串 "" 时表示在云空间根目录创建。
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from feishu_common import (
    DEFAULT_FOLDER_TOKEN,
    cli_run,
    confirm_action_or_exit,
    create_client,
    is_trusted_folder,
    print_json,
)


def main():
    parser = argparse.ArgumentParser(description="创建飞书云文档文件夹")
    parser.add_argument("name", help="文件夹名称")
    parser.add_argument("--parent", "-p", default=None, help="父文件夹 token（不传则使用默认文件夹；传空字符串则在根目录创建）")
    parser.add_argument("--identity", choices=["user", "tenant"], help="强制使用 user 或 tenant 身份创建")
    parser.add_argument("--yes", "-y", action="store_true", help="跳过确认")
    args = parser.parse_args()

    client = create_client()
    # None -> 默认文件夹；"" -> 根目录；其他 -> 指定父文件夹
    parent = DEFAULT_FOLDER_TOKEN if args.parent is None else args.parent
    use_user_token = {"user": True, "tenant": False}.get(args.identity) if args.identity else None

    confirm_action_or_exit(
        "drive_create",
        f"将在文件夹 {parent or '(根目录)'} 下创建新目录「{args.name}」",
        yes=args.yes,
        is_trusted=is_trusted_folder(parent),
    )

    data = client.create_folder(args.name, folder_token=args.parent, use_user_token=use_user_token)
    result = {
        "folder_token": data.get("token", ""),
        "url": data.get("url", ""),
        "name": args.name,
        "parent_token": parent,
    }
    print_json(result)


if __name__ == "__main__":
    cli_run(main)
