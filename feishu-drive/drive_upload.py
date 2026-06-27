#!/usr/bin/env python3
"""
drive_upload.py -- 上传本地文件到飞书云空间或多维表格
用法:
  python3 drive_upload.py --path ./file.pdf [--folder-token fldcnxxx]
  python3 drive_upload.py --path ./file.pdf --parent-type bitable_file --parent-node APP_TOKEN
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from feishu_common import DEFAULT_FOLDER_TOKEN, cli_run, confirm_action_or_exit, create_client, is_trusted_folder, print_json
import argparse


def main():
    parser = argparse.ArgumentParser(description="上传文件到飞书云空间或多维表格")
    parser.add_argument("--path", required=True, help="本地文件路径")
    parser.add_argument("--folder-token", default=DEFAULT_FOLDER_TOKEN, help="目标文件夹 token（parent_type=explorer 时生效，默认指定文件夹）")
    parser.add_argument("--parent-type", default=None, help="上传目标类型：explorer（云空间）或 bitable_file（多维表格）")
    parser.add_argument("--parent-node", default=None, help="上传目标节点：文件夹 token 或多维表格 app_token")
    parser.add_argument("--yes", "-y", action="store_true", help="跳过确认")
    args = parser.parse_args()

    client = create_client()
    confirm_action_or_exit(
        "drive_upload",
        f"确认上传文件 {args.path} 到文件夹 {args.folder_token}?",
        yes=args.yes,
        is_trusted=is_trusted_folder(args.folder_token),
    )
    result = client.upload_file(
        args.path,
        folder_token=args.folder_token,
        parent_type=args.parent_type,
        parent_node=args.parent_node,
    )
    print_json(result)


if __name__ == "__main__":
    cli_run(main)
