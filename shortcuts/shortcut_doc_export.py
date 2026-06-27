#!/usr/bin/env python3
"""
shortcut_doc_export.py -- 文档导出为本地文件 Shortcut

支持导出 docx / sheet / bitable 为以下格式：
    - markdown（docx 直接 fetch，最快）
    - pdf / docx / xlsx / csv（通过 Drive 导出任务，需轮询）

用法：
    python shortcut_doc_export.py --token DOC_TOKEN --type docx --format markdown --output ./docs
    python shortcut_doc_export.py --token SHEET_TOKEN --type sheet --format xlsx --output ./reports
    python shortcut_doc_export.py --token BITABLE_TOKEN --type bitable --format csv --output ./data

输出路径说明：
    --output 指定输出目录，导出文件会以 {token}.{ext} 命名存放在该目录下。
    建议使用绝对路径或专用目录，避免在 skill 目录下产生临时文件。
    示例: python shortcut_doc_export.py --token xxx --type docx --format markdown --output ~/Downloads/feishu

拼装步骤：
    markdown: 直接 fetch docx raw content → 写本地文件
    其他格式: 复用 DriveMixin.drive_export → 轮询 → 下载到本地
"""

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from feishu_common import create_client, cli_run, print_json, extract_doc_id


def main():
    parser = argparse.ArgumentParser(description="文档导出为本地文件 Shortcut")
    parser.add_argument("--token", required=True, help="文档 token 或 URL")
    parser.add_argument("--type", required=True, choices=["docx", "sheet", "bitable"],
                        help="文档类型")
    parser.add_argument("--format", required=True, choices=["markdown", "pdf", "docx", "xlsx", "csv"],
                        help="导出格式")
    parser.add_argument("--output", "-o", default=".", help="输出目录（默认当前目录）")
    parser.add_argument("--sub-id", help="sheet/bitable 的子表 ID（csv 导出时可能需要）")
    args = parser.parse_args()

    client = create_client()
    token = extract_doc_id(args.token)

    ext = args.format
    if args.format == "markdown":
        ext = "md"
    save_path = Path(args.output) / f"{token}.{ext}"
    save_path.parent.mkdir(parents=True, exist_ok=True)

    if args.format == "markdown":
        if args.type != "docx":
            raise RuntimeError("markdown 导出仅支持 docx 类型")
        print("正在导出 markdown（直接模式）...", file=sys.stderr)
        content = client.document_raw_content(token)
        with open(save_path, "w", encoding="utf-8") as f:
            f.write(content)
        result_path = str(save_path)
    else:
        print(f"正在创建导出任务（{args.type} → {args.format}）...", file=sys.stderr)
        result = client.drive_export(
            token=token,
            doc_type=args.type,
            file_extension=args.format,
            sub_id=args.sub_id,
            output_path=str(save_path),
        )
        result_path = result.get("saved_path", str(save_path))

    print_json({
        "exported": True,
        "token": token,
        "type": args.type,
        "format": args.format,
        "save_path": result_path,
    })


if __name__ == "__main__":
    cli_run(main)
