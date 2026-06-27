#!/usr/bin/env python3
"""
shortcut_doc_download.py -- 文档完整下载到本地 Shortcut

将飞书 docx 的文本内容（Markdown）和所有媒体附件（图片、文件块）
下载到本地文件夹，方便后续离线处理或导入其他系统。

用法：
    python shortcut_doc_download.py --doc DOC_TOKEN --output ./downloads
    python shortcut_doc_download.py --doc DOC_URL --output ./downloads

输出路径说明：
    --output 指定输出根目录，脚本会在其下创建 {doc_id}/ 子目录存放内容。
    建议使用绝对路径或专用目录，避免在 skill 目录下产生临时文件。
    示例: python shortcut_doc_download.py --doc DOC_TOKEN --output ~/Downloads/feishu

输出结构：
    {output}/
        {doc_id}/
            {doc_title}.md   # 文档 Markdown 内容（使用文档真实标题）
            media/           # 媒体资源
                image_xxx.png
                file_xxx.pdf
"""

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from feishu_common import create_client, cli_run, print_json, extract_doc_id


def main():
    parser = argparse.ArgumentParser(description="文档完整下载到本地 Shortcut")
    parser.add_argument("--doc", required=True, help="文档 URL 或 token")
    parser.add_argument("--output", "-o", default="./downloads", help="输出目录（默认 ./downloads）")
    parser.add_argument("--raw", action="store_true", help="输出完整原始 JSON")
    args = parser.parse_args()

    client = create_client()
    doc_id = extract_doc_id(args.doc)

    # 1. 获取文档基本信息和标题
    # wiki 链接提取出的 token 可能不是真实 docx token，先尝试 docx API，失败时回退到 wiki API 查询 obj_token
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
        # 如果 wiki 查询也失败，继续用原始 doc_id

    # 清理文件名非法字符
    safe_title = "".join(c for c in doc_title if c not in '\\/:*?"<>|').strip() or doc_id
    safe_title = safe_title[:100]  # 限制长度

    blocks_data = client.document_blocks_all(doc_id)
    blocks = blocks_data.get("items", [])

    # 2. 提取媒体资源
    from feishu_common import MediaExtractor
    media_list = MediaExtractor.extract(blocks)

    # 3. 创建输出目录（文件夹仍用 doc_id）
    out_dir = Path(args.output) / doc_id
    out_dir.mkdir(parents=True, exist_ok=True)
    media_dir = out_dir / "media"
    media_dir.mkdir(exist_ok=True)

    # 4. 下载媒体资源，建立 token -> 相对路径映射
    # download_media() 会自动从 Content-Disposition / Content-Type 推断文件名
    downloaded = []
    errors = []
    media_map = {}
    for media in media_list:
        token = media.get("token", "")
        media_type = media.get("type", "")
        try:
            if media_type == "board":
                result_path = client.download_board(token, str(media_dir))
            else:
                result_path = client.download_media(token, str(media_dir))
            rel_path = os.path.relpath(result_path, out_dir)
            media_map[token] = rel_path
            downloaded.append({"type": media_type, "token": token, "path": result_path})
        except RuntimeError as e:
            errors.append({"type": media_type, "token": token, "error": str(e)})

    # 5. 转换为 Markdown（传入 media_map 使用标准 Markdown 语法引用媒体）
    from feishu_common import BlockToMarkdownConverter
    converter = BlockToMarkdownConverter(blocks, media_map=media_map)
    markdown = converter.convert()

    # 6. 写入 Markdown（文件名用文档标题）
    md_path = out_dir / f"{safe_title}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(markdown)

    result = {
        "document_id": doc_id,
        "output_dir": str(out_dir),
        "markdown_file": str(md_path),
        "total_blocks": len(blocks),
        "media_count": len(media_list),
        "downloaded": len(downloaded),
        "download_errors": len(errors),
        "files": downloaded,
        "errors": errors,
    }

    if args.raw:
        print_json(result)
        return

    print_json({
        "document_id": doc_id,
        "output_dir": str(out_dir),
        "markdown": str(md_path),
        "media_dir": str(media_dir),
        "media_count": len(media_list),
        "downloaded": len(downloaded),
        "errors": len(errors),
    })


if __name__ == "__main__":
    cli_run(main)
