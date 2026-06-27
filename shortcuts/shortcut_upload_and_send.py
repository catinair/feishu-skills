#!/usr/bin/env python3
"""
shortcut_upload_and_send.py -- 上传本地文件/图片并发送 Shortcut

用法：
    python shortcut_upload_and_send.py --file report.pdf --chat-id oc_xxx
    python shortcut_upload_and_send.py --file screenshot.png --user-id ou_xxx --text "请看截图"
    python shortcut_upload_and_send.py --file data.xlsx --chat-id oc_xxx --text "本周数据"

拼装步骤：
    1. 上传本地文件/图片到飞书
    2. 自动推断 msg_type（file / image）
    3. 发送消息到指定群或用户
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from feishu_common import cli_run, confirm_action_or_exit, create_client, print_json


def main():
    parser = argparse.ArgumentParser(description="上传本地文件/图片并发送")
    parser.add_argument("--file", required=True, help="本地文件路径")
    parser.add_argument("--chat-id", help="目标群聊 ID（与 --user-id 二选一）")
    parser.add_argument("--user-id", help="目标用户 open_id（与 --chat-id 二选一）")
    parser.add_argument("--text", help=" accompanying 文本消息（可选）")
    parser.add_argument("--yes", "-y", action="store_true", help="跳过确认")
    args = parser.parse_args()

    if not (args.chat_id or args.user_id):
        parser.error("请提供 --chat-id 或 --user-id")

    target = args.chat_id or args.user_id
    confirm_action_or_exit(
        "im_send_message",
        f"将上传并发送文件 {args.file} 到 {target}",
        yes=args.yes,
    )

    client = create_client()
    path = Path(args.file)
    if not path.exists():
        raise RuntimeError(f"文件不存在: {args.file}")

    # 判断文件类型
    ext = path.suffix.lower()
    image_exts = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}
    is_image = ext in image_exts

    # 1. 上传
    if is_image:
        file_token = client.upload_image(str(path))
        msg_type = "image"
    else:
        # 使用 drive upload
        result = client.upload_file(str(path))
        file_token = result.get("file_token", "")
        msg_type = "file"

    # 2. 发送
    receive_id = args.chat_id or args.user_id
    receive_id_type = "chat_id" if args.chat_id else "open_id"

    text_message_id = ""
    if args.text:
        text_result = client.im_send_text(receive_id, receive_id_type, args.text)
        text_message_id = text_result.get("message_id", "")

    if is_image:
        data = client.im_send_image(receive_id, receive_id_type, file_token)
    else:
        data = client.im_send_file(receive_id, receive_id_type, file_token)

    print_json({
        "sent": True,
        "file": str(path),
        "msg_type": msg_type,
        "file_token": file_token,
        "target": receive_id,
        "message_id": data.get("message_id", ""),
        "text_message_id": text_message_id or None,
    })


if __name__ == "__main__":
    cli_run(main)
