#!/usr/bin/env python3
"""
shortcut_notify_group.py -- 群富文本通知 Shortcut

用法：
    python shortcut_notify_group.py --chat-id oc_xxx --title "周会通知" --content "本周五 14:00 开周会，请准时参加。"
    python shortcut_notify_group.py --chat-id oc_xxx --title "项目进度" --content "第一阶段已完成，第二阶段预计下周开始。" --yes

拼装步骤：
    1. 将文本构造为富文本 post 格式（支持简单 markdown：@人、加粗、链接）
    2. 发送到指定群聊
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from feishu_common import cli_run, confirm_action_or_exit, create_client, is_trusted_chat, print_json


def build_post_content(title, text):
    """将简单文本构造为飞书 post 消息格式"""
    lines = text.split("\n")
    content = []
    for line in lines:
        if not line.strip():
            continue
        parts = []
        # 处理 @user_id 格式
        line = re.sub(r"@user:([a-zA-Z0-9_-]+)", r"{{@user:\1}}", line)
        # 处理 [text](url) 链接
        line = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"{{link:\1:\2}}", line)
        # 处理 **bold**
        line = re.sub(r"\*\*([^*]+)\*\*", r"{{bold:\1}}", line)

        # 解析标记
        pos = 0
        while pos < len(line):
            m = re.search(r"\{\{(@user:[a-zA-Z0-9_-]+|link:[^:]+:[^}]+|bold:[^}]+)\}\}", line[pos:])
            if m:
                if m.start() > 0:
                    parts.append({"tag": "text", "text": line[pos:pos + m.start()]})
                tag_content = m.group(1)
                if tag_content.startswith("@user:"):
                    user_id = tag_content[6:]
                    parts.append({"tag": "at", "user_id": user_id})
                elif tag_content.startswith("link:"):
                    _, link_text, link_url = tag_content.split(":", 2)
                    parts.append({"tag": "a", "text": link_text, "href": link_url})
                elif tag_content.startswith("bold:"):
                    bold_text = tag_content[5:]
                    parts.append({"tag": "text", "text": bold_text, "style": ["bold"]})
                pos += m.end()
            else:
                parts.append({"tag": "text", "text": line[pos:]})
                break

        content.append(parts)

    return {
        "zh_cn": {
            "title": title,
            "content": content,
        }
    }


def main():
    parser = argparse.ArgumentParser(description="群富文本通知 Shortcut")
    parser.add_argument("--chat-id", required=True, help="群聊 ID")
    parser.add_argument("--title", required=True, help="通知标题")
    parser.add_argument("--content", required=True, help="通知内容（支持 @user:xxx、**bold**、[text](url)）")
    parser.add_argument("--yes", "-y", action="store_true", help="跳过确认")
    args = parser.parse_args()

    confirm_action_or_exit(
        "im_send_message",
        f"将在群 {args.chat_id} 发送通知:\n标题: {args.title}\n内容: {args.content[:100]}...",
        yes=args.yes,
        is_trusted=is_trusted_chat(args.chat_id),
    )

    client = create_client()
    post_content = build_post_content(args.title, args.content)

    data = client.im_send_post(
        args.chat_id, "chat_id",
        title=args.title,
        content_lines=post_content["zh_cn"]["content"]
    )

    print_json({
        "sent": True,
        "chat_id": args.chat_id,
        "title": args.title,
        "message_id": data.get("message_id", ""),
    })


if __name__ == "__main__":
    cli_run(main)
