#!/usr/bin/env python3
"""
im_upload_image.py -- 上传图片到飞书
用法: python3 im_upload_image.py --path ./image.png
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from feishu_common import create_client, confirm_action_or_exit, print_json, cli_run
import argparse

def main():
    parser = argparse.ArgumentParser(description="上传图片到飞书")
    parser.add_argument("--path", required=True, help="图片文件路径")
    parser.add_argument("--yes", "-y", action="store_true", help="跳过确认")
    args = parser.parse_args()

    client = create_client()
    confirm_action_or_exit(
        "im_upload_image",
        f"确认上传图片 {args.path} 到飞书?",
        yes=args.yes,
        is_trusted=False,
    )
    key = client.upload_image(args.path)
    print_json({"image_key": key})

if __name__ == "__main__":
    cli_run(main)
