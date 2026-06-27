#!/usr/bin/env python3
"""
shortcut_doc_media_insert.py -- 上传本地媒体并插入文档 Shortcut

用法：
    python shortcut_doc_media_insert.py --doc DOC_TOKEN --file image.png
    python shortcut_doc_media_insert.py --doc DOC_URL --file report.pdf --type file

拼装步骤：
    1. 上传本地文件/图片到飞书
    2. 在文档末尾创建 block（image 或 file）
    3. 将 block 与上传的 file_token 绑定

注意：
    仅支持 docx 文档。
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from feishu_common import cli_run, confirm_action_or_exit, create_client, print_json, extract_doc_id


def main():
    parser = argparse.ArgumentParser(description="上传本地媒体并插入文档 Shortcut")
    parser.add_argument("--doc", required=True, help="文档 URL 或 token")
    parser.add_argument("--file", required=True, help="本地文件路径")
    parser.add_argument("--type", default="auto", choices=["auto", "image", "file"],
                        help="媒体类型（auto 自动推断）")
    parser.add_argument("--yes", "-y", action="store_true", help="跳过确认")
    args = parser.parse_args()

    doc_id = extract_doc_id(args.doc)
    file_path = Path(args.file)
    if not file_path.exists():
        raise RuntimeError(f"文件不存在: {args.file}")

    # 推断类型
    media_type = args.type
    if media_type == "auto":
        ext = file_path.suffix.lower()
        image_exts = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}
        media_type = "image" if ext in image_exts else "file"

    confirm_action_or_exit(
        "doc_write",
        f"将把 {args.file} ({media_type}) 插入文档 {doc_id} 末尾",
        yes=args.yes,
    )

    client = create_client()

    # 1. 上传文件
    if media_type == "image":
        file_token = client.upload_image(str(file_path))
    else:
        upload_result = client.upload_file(str(file_path))
        file_token = upload_result.get("file_token", "")

    # 2. 获取文档 root block 的 children 数量（用于在末尾插入）
    root_block = client.document_block_info(doc_id, doc_id)
    children = root_block.get("children", [])
    insert_index = len(children)

    # 3. 创建 block
    block_type = 27 if media_type == "image" else 23  # 27=image, 23=file
    create_result = client.document_create_child_blocks(
        document_id=doc_id,
        parent_block_id=doc_id,
        children=[{"block_type": block_type}],
        index=insert_index,
    )
    new_blocks = create_result.get("children", [])
    if not new_blocks:
        raise RuntimeError("创建 block 失败")
    new_block_id = new_blocks[0].get("block_id", "")

    # 4. 更新 block 绑定 file_token
    if media_type == "image":
        update_body = {"image": {"token": file_token}}
    else:
        update_body = {"file": {"token": file_token, "name": file_path.name}}

    client.document_update_block(doc_id, new_block_id, update_body)

    print_json({
        "inserted": True,
        "document_id": doc_id,
        "block_id": new_block_id,
        "media_type": media_type,
        "file_token": file_token,
        "file_name": file_path.name,
    })


if __name__ == "__main__":
    cli_run(main)
