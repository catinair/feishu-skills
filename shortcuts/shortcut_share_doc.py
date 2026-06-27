#!/usr/bin/env python3
"""
shortcut_share_doc.py -- 创建文档并分享 Shortcut

用法：
    python shortcut_share_doc.py --title "会议纪要" --chat-id oc_xxx
    python shortcut_share_doc.py --title "项目方案" --chat-id oc_xxx --members ou_xxx,ou_yyy --perm edit

拼装步骤：
    1. 创建空 docx
    2. 添加协作者权限（可选）
    3. 发送文档链接到群聊
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
    is_trusted_chat,
    is_trusted_folder,
    print_json,
)


def main():
    parser = argparse.ArgumentParser(description="创建文档并分享 Shortcut")
    parser.add_argument("--title", required=True, help="文档标题")
    parser.add_argument("--chat-id", required=True, help="要通知的群聊 ID")
    parser.add_argument("--members", help="协作者 ID 列表（逗号分隔，默认不添加）")
    parser.add_argument("--perm", default="edit", choices=["view", "edit", "full_access"],
                        help="协作者权限（默认 edit）")
    parser.add_argument("--folder", default=DEFAULT_FOLDER_TOKEN, help="创建位置（默认文件夹）")
    parser.add_argument("--yes", "-y", action="store_true", help="跳过确认")
    args = parser.parse_args()

    message = f"将创建文档「{args.title}」并分享到群 {args.chat_id}"
    if args.members:
        message += f"\n协作者: {args.members} (权限: {args.perm})"
    confirm_action_or_exit(
        "doc_create",
        message,
        yes=args.yes,
        is_trusted=is_trusted_folder(args.folder) and is_trusted_chat(args.chat_id),
    )

    client = create_client()

    # 1. 创建文档
    doc = client.document_create(title=args.title, folder_token=args.folder)
    doc_token = doc.get("document_id", "")
    web_domain = {"feishu": "feishu.cn", "lark": "larksuite.com"}.get(client.brand, "feishu.cn")
    doc_url = f"https://{web_domain}/docx/{doc_token}"

    # 2. 添加权限
    if args.members:
        for member_id in args.members.split(","):
            member_id = member_id.strip()
            if member_id:
                try:
                    client.perm_add_member(doc_token, "docx", member_id, "user_id", args.perm)
                except RuntimeError as e:
                    print(f"Warning: 添加权限失败 {member_id}: {e}", file=sys.stderr)

    # 3. 发送到群
    text = f"📄 新文档: {args.title}\n🔗 {doc_url}"
    notify_result = client.im_send_text(args.chat_id, "chat_id", text)

    print_json({
        "created": True,
        "title": args.title,
        "document_id": doc_token,
        "url": doc_url,
        "shared_to": args.chat_id,
        "notify_message_id": notify_result.get("message_id", ""),
        "permissions": args.perm if args.members else None,
    })


if __name__ == "__main__":
    cli_run(main)
