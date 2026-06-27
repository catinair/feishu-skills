#!/usr/bin/env python3
"""
shortcut_doc_upload_md.py -- 上传 Markdown 文件为飞书云文档 Shortcut

用法：
    python shortcut_doc_upload_md.py --path ./report.md
    python shortcut_doc_upload_md.py --path ./report.md --title "我的报告"
    python shortcut_doc_upload_md.py --path ./report.md --folder fldcnxxx

拼装步骤：
    1. 读取本地 Markdown 文件
    2. 创建空 docx（使用文件名或指定标题）
    3. 将 Markdown 内容写入文档
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
    parser = argparse.ArgumentParser(description="上传 Markdown 文件为飞书云文档")
    parser.add_argument("--path", required=True, help="本地 Markdown 文件路径")
    parser.add_argument("--title", help="文档标题（默认使用文件名）")
    parser.add_argument("--folder", default=DEFAULT_FOLDER_TOKEN, help="创建位置（默认文件夹）")
    parser.add_argument("--yes", "-y", action="store_true", help="跳过确认")
    args = parser.parse_args()

    # 验证文件
    md_path = Path(args.path)
    if not md_path.exists():
        raise RuntimeError(f"文件不存在: {args.path}")
    if not md_path.suffix.lower() in (".md", ".markdown"):
        raise RuntimeError(f"不是 Markdown 文件: {args.path}")

    # 读取内容
    markdown = md_path.read_text(encoding="utf-8")
    if not markdown.strip():
        raise RuntimeError("文件内容为空")

    # 标题：优先用 --title，否则用文件名（去掉扩展名）
    title = args.title or md_path.stem

    size_kb = len(markdown.encode("utf-8")) / 1024
    message = f"将上传「{md_path.name}」({size_kb:.1f} KB) 为飞书文档「{title}」"
    confirm_action_or_exit(
        "doc_create",
        message,
        yes=args.yes,
        is_trusted=is_trusted_folder(args.folder),
    )

    client = create_client()

    # 1. 创建文档
    doc = client.document_create(title=title, folder_token=args.folder)
    doc_token = doc.get("document_id", "")
    if not doc_token:
        raise RuntimeError("创建文档失败：未返回 document_id")

    # 2. 写入 Markdown 内容
    result = client.write_markdown(doc_token, markdown)

    web_domain = {"feishu": "feishu.cn", "lark": "larksuite.com"}.get(client.brand, "feishu.cn")
    output = {
        "uploaded": True,
        "title": title,
        "source_file": str(md_path),
        "document_id": doc_token,
        "url": f"https://{web_domain}/docx/{doc_token}",
        "size_bytes": len(markdown.encode("utf-8")),
        "blocks_total": result.get("blocks_total", 0),
        "blocks_inserted": result.get("blocks_inserted", 0),
    }
    warnings = result.get("warnings", [])
    if warnings:
        output["warnings"] = warnings
    print_json(output)


if __name__ == "__main__":
    cli_run(main)
