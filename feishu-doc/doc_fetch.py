#!/usr/bin/env python3
"""
doc_fetch.py -- 导出飞书文档为 Markdown + 下载媒体

支持 docx / wiki 链接，输出标准 Markdown 语法（![]() / []()），
自动下载所有媒体附件（含画板官方 API 导出 + 自动裁剪）。

用法: python3 doc_fetch.py --doc doxcnxxx [--output-dir ./downloads]

输出路径说明：
    --output-dir 指定导出目录，默认 ./downloads（当前工作目录下）。
    建议显式指定一个专用目录，避免在项目或 skill 目录下产生临时文件。
    示例: python3 doc_fetch.py --doc doxcnxxx --output-dir ~/Downloads/feishu
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from feishu_common import create_client, BlockToMarkdownConverter, MediaExtractor, print_json, extract_doc_id, cli_run
import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="导出飞书文档为 Markdown + 下载媒体")
    parser.add_argument("--doc", required=True, help="文档 ID、wiki ID 或 URL")
    parser.add_argument("--output-dir", default="./downloads", help="输出目录（默认 ./downloads）")
    args = parser.parse_args()

    client = create_client()
    doc_id = extract_doc_id(args.doc)

    # wiki 链接提取出的 token 可能不是真实 docx token，先尝试 docx API，失败时回退到 wiki API
    doc_title = doc_id
    try:
        doc_info = client.document_info(doc_id)
        doc_title = doc_info.get("title", doc_id)
    except RuntimeError as e:
        err = str(e)
        if "404" in err or "403" in err:
            try:
                wiki_info = client.wiki_get_node(doc_id)
                obj_token = wiki_info.get("node", {}).get("obj_token", "")
                if obj_token:
                    doc_id = obj_token
                    doc_info = client.document_info(doc_id)
                    doc_title = doc_info.get("title", doc_title)
            except RuntimeError:
                pass

    data = client.document_blocks_all(doc_id)
    items = data.get("items", [])
    if not items:
        print("ERROR: 文档中没有 block", file=sys.stderr)
        sys.exit(1)

    media = MediaExtractor.extract(items)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # 下载媒体，建立 token -> 路径映射
    downloaded = []
    failed = []
    media_map = {}
    for m in media:
        token = m.get("token", "")
        if not token:
            continue
        media_type = m.get("type", "unknown")
        try:
            if media_type == "board":
                result_path = client.download_board(token, str(out_dir))
            else:
                result_path = client.download_media(token, str(out_dir))
            rel_path = os.path.relpath(result_path, out_dir)
            media_map[token] = rel_path
            downloaded.append({"token": token, "type": media_type, "file": os.path.basename(result_path)})
        except RuntimeError as e:
            failed.append({"token": token, "type": media_type, "error": str(e)})

    # 用 media_map 生成标准 Markdown
    converter = BlockToMarkdownConverter(items, media_map=media_map)
    markdown = converter.convert()

    md_path = out_dir / "document.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(markdown)

    media_path = out_dir / "media.json"
    with open(media_path, "w", encoding="utf-8") as f:
        json.dump({
            "document_id": doc_id,
            "title": doc_title,
            "total_blocks": len(items),
            "media_count": len(media),
            "downloaded": len(downloaded),
            "download_failed": len(failed),
            "media": media,
            "downloaded_files": downloaded,
            "failed_downloads": failed,
        }, f, indent=2, ensure_ascii=False)

    print_json({
        "document_id": doc_id,
        "title": doc_title,
        "markdown_file": str(md_path),
        "media_manifest": str(media_path),
        "total_blocks": len(items),
        "media_count": len(media),
        "media_downloaded": len(downloaded),
        "media_failed": len(failed),
    })


if __name__ == "__main__":
    cli_run(main)
