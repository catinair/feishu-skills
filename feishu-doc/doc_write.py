#!/usr/bin/env python3
"""
doc_write.py -- 写入 Markdown 到飞书文档（追加模式）
用法: python3 doc_write.py --doc doxcnxxx --markdown "# 标题"
       python3 doc_write.py --doc doxcnxxx --markdown-file content.md
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from feishu_common import (
    confirm_action_or_exit,
    create_client,
    print_json,
    extract_doc_id,
    cli_run,
)
import argparse

def main():
    parser = argparse.ArgumentParser(description="写入 Markdown 到飞书文档")
    parser.add_argument("--doc", required=True, help="文档 ID 或 URL")
    parser.add_argument("--markdown", help="Markdown 内容字符串")
    parser.add_argument("--markdown-file", help="Markdown 文件路径")
    parser.add_argument("--yes", "-y", action="store_true", help="跳过确认")
    parser.add_argument("--raw", action="store_true", help="输出完整原始 JSON")
    args = parser.parse_args()

    markdown = None
    if args.markdown_file:
        with open(args.markdown_file, "r", encoding="utf-8") as f:
            markdown = f.read()
    elif args.markdown:
        markdown = args.markdown
    else:
        print("ERROR: --markdown 或 --markdown-file 必须指定一个", file=sys.stderr)
        sys.exit(1)

    confirm_action_or_exit("doc_write", f"确认写入文档 {args.doc}?", yes=args.yes)

    client = create_client()
    doc_id = extract_doc_id(args.doc)
    result = client.write_markdown(doc_id, markdown)
    if args.raw:
        print_json(result)
        return

    print_json(result)

if __name__ == "__main__":
    cli_run(main)
