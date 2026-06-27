#!/usr/bin/env python3
"""
drive_download.py -- 下载 drive 文件或文档媒体
用法: python3 drive_download.py --token xxx --output ./file.pdf --type file
       python3 drive_download.py --token xxx --output ./image.png --type media

输出路径说明：
    --output 为必填参数，指定完整的本地保存路径。
    建议使用绝对路径或明确的目标目录，避免文件散落在 skill 目录下。
    示例: python3 drive_download.py --token xxx --output ~/Downloads/file.pdf --type file
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from feishu_common import create_client, print_json, cli_run
import argparse

def main():
    parser = argparse.ArgumentParser(description="下载文件或文档媒体")
    parser.add_argument("--token", required=True, help="文件 token 或 media token")
    parser.add_argument("--output", required=True, help="保存路径")
    parser.add_argument("--type", default="file", choices=["file", "media"],
                        help="下载类型：file（drive 文件）或 media（文档媒体）")
    args = parser.parse_args()

    client = create_client()
    if args.type == "media":
        path = client.download_media(args.token, args.output)
    else:
        path = client.download_file(args.token, args.output)
    print_json({"saved_to": path, "type": args.type})

if __name__ == "__main__":
    cli_run(main)
