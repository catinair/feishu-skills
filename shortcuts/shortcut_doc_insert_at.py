#!/usr/bin/env python3
"""
shortcut_doc_insert_at.py -- 向飞书文档指定位置插入内容 Shortcut

在任意 block（容器）下插入 Markdown 内容，支持追加到末尾、插入开头或指定索引位置。
典型场景：向表格单元格、标题下、列表项、特定容器等位置精准插入内容。

用法：
    # 追加到指定 block 末尾（默认）
    python shortcut_doc_insert_at.py --doc DOC_URL --parent BLOCK_ID --markdown "内容"

    # 从文件读取内容并插入
    python shortcut_doc_insert_at.py --doc DOC_URL --parent BLOCK_ID --markdown-file content.md

    # 插入到开头
    python shortcut_doc_insert_at.py --doc DOC_URL --parent BLOCK_ID --markdown "内容" --prepend

    # 指定索引位置插入
    python shortcut_doc_insert_at.py --doc DOC_URL --parent BLOCK_ID --markdown "内容" --index 2

    # 查看目标 block 信息（类型、当前子节点数）
    python shortcut_doc_insert_at.py --doc DOC_URL --parent BLOCK_ID --info
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from feishu_common import (
    cli_run,
    confirm_action_or_exit,
    create_client,
    extract_doc_id,
    print_json,
)

# block_type → 可读名称
BLOCK_TYPE_NAMES = {
    1: "page", 2: "text", 3: "heading1", 4: "heading2", 5: "heading3",
    6: "heading4", 7: "heading5", 8: "heading6", 9: "heading7", 10: "heading8",
    11: "heading9", 12: "bullet", 13: "ordered", 14: "code", 15: "quote",
    16: "divider", 17: "todo", 19: "callout", 22: "table", 23: "file",
    24: "table_row", 25: "table_cell", 27: "image", 28: "unsupport",
    29: "undefined", 30: "diagram", 31: "table_v2", 32: "audio",
    33: "iframe", 34: "chat_card", 35: "label", 36: "quote_container",
    37: "code_block", 38: "okr", 39: "okr_objective", 40: "okr_key_result",
    41: "okr_progress", 42: "okr_rollback_reason", 43: "okr_confidence",
    44: "okr_key_result_v2", 45: "okr_objective_v2", 46: "okr_progress_v2",
}


def get_parent_info(client, doc_id, parent_id):
    """获取目标父 block 的信息"""
    block = client.document_block_info(doc_id, parent_id)
    bt = block.get("block_type", 0)
    children = block.get("children", [])
    return {
        "block_id": parent_id,
        "block_type": bt,
        "block_type_name": BLOCK_TYPE_NAMES.get(bt, f"type_{bt}"),
        "children_count": len(children),
        "has_children": len(children) > 0,
    }


def extract_text_from_block(block):
    """从 block 中提取纯文本内容（用于展示）"""
    bt = block.get("block_type", 0)
    content_key = None
    for key in ["text", "heading1", "heading2", "heading3", "heading4",
                "heading5", "heading6", "heading7", "heading8", "heading9",
                "bullet", "ordered", "code", "quote", "callout", "todo"]:
        if key in block:
            content_key = key
            break
    if not content_key:
        return ""
    elements = block[content_key].get("elements", [])
    parts = []
    for elem in elements:
        if "text_run" in elem:
            parts.append(elem["text_run"].get("content", ""))
        elif "mention_user" in elem:
            parts.append(f"@user")
        elif "mention_doc" in elem:
            parts.append(f"[[doc]]")
    return "".join(parts)


def main():
    parser = argparse.ArgumentParser(
        description="向飞书文档指定 block 位置插入 Markdown 内容"
    )
    parser.add_argument("--doc", required=True, help="文档 URL 或 token")
    parser.add_argument("--parent", "-p", required=True,
                        help="目标父 block_id（插入到这个 block 下面）")

    # 内容来源（二选一）
    content_group = parser.add_mutually_exclusive_group(required=False)
    content_group.add_argument("--markdown", "-m", help="Markdown 内容字符串")
    content_group.add_argument("--markdown-file", "-f", help="Markdown 文件路径")

    # 位置控制
    pos_group = parser.add_mutually_exclusive_group()
    pos_group.add_argument("--append", "-a", action="store_true", default=True,
                           help="追加到末尾（默认）")
    pos_group.add_argument("--prepend", action="store_true",
                           help="插入到开头")
    pos_group.add_argument("--index", "-i", type=int,
                           help="指定插入索引位置")

    # 辅助
    parser.add_argument("--info", action="store_true",
                        help="仅查看目标 block 信息，不插入")
    parser.add_argument("--yes", "-y", action="store_true",
                        help="跳过确认")

    args = parser.parse_args()

    client = create_client()
    doc_id = extract_doc_id(args.doc)

    # 获取目标 block 信息
    try:
        info = get_parent_info(client, doc_id, args.parent)
    except RuntimeError as e:
        print(f"获取目标 block 信息失败: {e}", file=sys.stderr)
        sys.exit(1)

    # --info 模式：仅展示信息
    if args.info:
        print_json({
            "document_id": doc_id,
            "parent_block": info,
        })
        return

    # 读取 markdown 内容
    markdown = None
    if args.markdown_file:
        md_path = Path(args.markdown_file)
        if not md_path.exists():
            raise RuntimeError(f"文件不存在: {args.markdown_file}")
        markdown = md_path.read_text(encoding="utf-8")
    elif args.markdown:
        markdown = args.markdown
    else:
        print("ERROR: --markdown 或 --markdown-file 必须指定一个", file=sys.stderr)
        sys.exit(1)

    if not markdown.strip():
        raise RuntimeError("内容为空")

    # 确定插入位置
    if args.prepend:
        insert_index = 0
    elif args.index is not None:
        insert_index = args.index
        if insert_index < 0:
            raise RuntimeError("--index 不能为负数")
    else:
        # append（默认）：在现有子节点末尾追加
        insert_index = info["children_count"]

    # 确认
    pos_desc = {
        0: "开头" if info["children_count"] > 0 else "空容器内",
    }.get(insert_index, f"索引 {insert_index} 处")
    if args.append and insert_index == info["children_count"] and info["children_count"] > 0:
        pos_desc = "末尾"

    msg = (
        f"将向 {info['block_type_name']}({args.parent[:12]}...) "
        f"的{pos_desc}插入 {len(markdown.encode('utf-8')) / 1024:.1f} KB 内容"
    )
    confirm_action_or_exit("doc_write", msg, yes=args.yes)

    # 转换 markdown → blocks
    convert_data = client.markdown_to_blocks(markdown)
    blocks = convert_data.get("blocks", [])
    first_level_ids = convert_data.get("first_level_block_ids", [])
    convert_warnings = convert_data.get("warnings", [])

    if not blocks:
        raise RuntimeError("Markdown 转换结果为空")

    # 清洗
    blocks = client._sanitize_blocks(blocks)

    # 插入
    try:
        result = client.insert_blocks(
            document_id=doc_id,
            blocks=blocks,
            first_level_block_ids=first_level_ids,
            index=insert_index,
            parent_block_id=args.parent,
        )
    except RuntimeError as e:
        # 提供更有针对性的错误提示
        err_str = str(e)
        if "1770004" in err_str or "block 不存在" in err_str:
            raise RuntimeError(
                f"插入失败: 目标 block {args.parent[:12]}... 可能不是容器类型，"
                f"或该 block 不支持插入子内容"
            ) from e
        raise

    output = {
        "inserted": True,
        "document_id": doc_id,
        "parent_block": {
            "block_id": args.parent,
            "block_type_name": info["block_type_name"],
            "children_before": info["children_count"],
        },
        "position": {
            "index": insert_index,
            "mode": "prepend" if args.prepend else ("append" if args.index is None else "index"),
        },
        "blocks_total": len(blocks),
        "first_level_count": len(first_level_ids),
    }

    if convert_warnings:
        output["convert_warnings"] = convert_warnings

    print_json(output)


if __name__ == "__main__":
    cli_run(main)
