#!/usr/bin/env python3
"""
doc_comments.py -- 获取云文档评论列表 / 回复评论 / 创建评论

用法：
    # 查看评论
    python3 feishu-doc/doc_comments.py --doc doxcnxxx
    python3 feishu-doc/doc_comments.py --doc doxcnxxx --solved
    python3 feishu-doc/doc_comments.py --doc doxcnxxx --json

    # 创建全文评论
    python3 feishu-doc/doc_comments.py --doc doxcnxxx --create-comment "评论内容"

    # 回复评论
    python3 feishu-doc/doc_comments.py --doc doxcnxxx --reply-comment COMMENT_ID --reply-text "回复内容"
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))
from feishu_common import cli_run, confirm_action_or_exit, create_client, print_json


def format_time(timestamp):
    """将秒级时间戳转为可读格式"""
    if not timestamp:
        return ""
    try:
        return datetime.fromtimestamp(int(timestamp)).strftime("%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        return str(timestamp)


def extract_reply_text(elements):
    """从回复内容元素中提取纯文本"""
    texts = []
    for elem in elements or []:
        elem_type = elem.get("type", "")
        if elem_type == "text_run":
            text_run = elem.get("text_run", {})
            if text_run.get("text"):
                texts.append(text_run["text"])
        elif elem_type == "person":
            person = elem.get("person", {})
            user_id = person.get("user_id", "")
            texts.append(f"@{user_id[:8]}...")
        elif elem_type == "docs_link":
            docs_link = elem.get("docs_link", {})
            url = docs_link.get("url", "")
            texts.append(f"[{url[:30]}...]")
    return "".join(texts)


def print_comments_human(comments):
    """以人类可读格式打印评论"""
    if not comments:
        print("暂无评论")
        return

    print(f"共 {len(comments)} 条评论\n")

    for i, comment in enumerate(comments, 1):
        comment_id = comment.get("comment_id", "")
        user_id = comment.get("user_id", "")
        create_time = format_time(comment.get("create_time"))
        is_solved = comment.get("is_solved", False)
        solved_time = format_time(comment.get("solved_time"))
        solver_id = comment.get("solver_user_id", "")
        is_whole = comment.get("is_whole", False)
        quote = comment.get("quote", "")

        status_icon = "✅" if is_solved else "⬜"
        scope_label = "[全文]" if is_whole else "[局部]"

        print(f"{'─' * 60}")
        print(f"{status_icon} 评论 #{i} {scope_label}")
        print(f"   ID: {comment_id}")
        print(f"   作者: {user_id}")
        print(f"   创建时间: {create_time}")
        if is_solved:
            print(f"   解决时间: {solved_time}  解决人: {solver_id}")
        if quote:
            print(f"   引用: \"{quote}\"")

        reply_list = comment.get("reply_list", {})
        replies = reply_list.get("replies", []) if reply_list else []

        if replies:
            print(f"\n   回复 ({len(replies)} 条):")
            for j, reply in enumerate(replies, 1):
                reply_id = reply.get("reply_id", "")
                reply_user = reply.get("user_id", "")
                reply_time = format_time(reply.get("create_time"))
                content = reply.get("content", {})
                elements = content.get("elements", []) if content else []
                text = extract_reply_text(elements)

                print(f"   └─ #{j} [{reply_time}] {reply_user[:12]}: {text}")

                reactions = reply.get("reactions", [])
                if reactions:
                    reaction_strs = [f"{r.get('reaction_key', '')}({r.get('count', 0)})" for r in reactions]
                    print(f"      表情: {', '.join(reaction_strs)}")
        else:
            print("   暂无回复")

        print()


def main():
    parser = argparse.ArgumentParser(description="获取云文档评论列表")
    parser.add_argument("--doc", required=True, help="文档 token（如 doxcnxxx）")
    parser.add_argument("--type", default="docx", choices=["docx", "sheet", "slides", "file"], help="文档类型")
    parser.add_argument("--whole", action="store_true", help="只显示全文评论")
    parser.add_argument("--solved", action="store_true", help="只显示已解决的评论")
    parser.add_argument("--unsolved", action="store_true", help="只显示未解决的评论")
    parser.add_argument("--reactions", action="store_true", help="获取评论的表情回复")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出（而非人类可读格式）")
    parser.add_argument("--max", type=int, help="最多获取多少条评论")
    parser.add_argument("--create-comment", help="创建全文评论（评论内容）")
    parser.add_argument("--reply-comment", help="要回复的评论 ID")
    parser.add_argument("--reply-text", help="回复内容文本")
    args = parser.parse_args()

    client = create_client()

    # 创建评论模式
    if args.create_comment:
        confirm_action_or_exit(
            "doc_write",
            f"确认在文档 {args.doc} 创建全文评论?",
        )
        result = client.document_comment_create(
            file_token=args.doc,
            text=args.create_comment,
            file_type=args.type,
        )
        comment_id = result.get("data", {}).get("comment_id", "unknown")
        print_json({"created": True, "comment_id": comment_id, "result": result})
        return

    # 回复模式
    if args.reply_comment:
        if not args.reply_text:
            print("错误: --reply-text 必填", file=sys.stderr)
            sys.exit(1)
        confirm_action_or_exit(
            "doc_write",
            f"确认回复文档 {args.doc} 的评论 {args.reply_comment}?",
        )
        result = client.document_comment_reply(
            file_token=args.doc,
            comment_id=args.reply_comment,
            text=args.reply_text,
            file_type=args.type,
        )
        print_json({"replied": True, "comment_id": args.reply_comment, "reply": result})
        return

    # 处理 solved 过滤
    is_solved = None
    if args.solved:
        is_solved = True
    elif args.unsolved:
        is_solved = False

    comments = client.document_comments_all(
        file_token=args.doc,
        file_type=args.type,
        is_whole=args.whole or None,
        is_solved=is_solved,
        need_reaction=args.reactions,
        max_results=args.max,
    )

    if args.json:
        print_json({"count": len(comments), "comments": comments})
    else:
        print_comments_human(comments)


if __name__ == "__main__":
    cli_run(main)
