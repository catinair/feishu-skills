#!/usr/bin/env python3
"""
slides_upload_media.py -- 上传本地图片到幻灯片

用法:
    python3 slides_upload_media.py --path ./image.png --presentation doxcnxxx

    # 从 Wiki URL 自动解析
    python3 slides_upload_media.py --path ./image.png --presentation "https://xxx.feishu.cn/wiki/xxx"
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from feishu_common import create_client, confirm_action_or_exit, print_json, cli_run
import argparse


def main():
    parser = argparse.ArgumentParser(description="上传媒体到幻灯片")
    parser.add_argument("--path", required=True, help="本地图片路径（最大 20MB）")
    parser.add_argument("--presentation", required=True, help="幻灯片 token 或 URL")
    parser.add_argument("--yes", "-y", action="store_true", help="跳过确认")
    args = parser.parse_args()

    # 从 URL 提取 token
    presentation_token = args.presentation
    if presentation_token.startswith("http"):
        import re
        # 尝试匹配 wiki 或 slides URL
        m = re.search(r"/(?:wiki|slides)/([a-zA-Z0-9]+)", presentation_token)
        if m:
            presentation_token = m.group(1)

    client = create_client()
    confirm_action_or_exit(
        "slides_upload_media",
        f"确认上传文件 {args.path} 到幻灯片 {presentation_token}?",
        yes=args.yes,
        is_trusted=False,
    )
    result = client.slides_upload_media(args.path, presentation_token)
    print_json(result)


if __name__ == "__main__":
    cli_run(main)
