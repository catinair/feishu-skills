#!/usr/bin/env python3
"""
shortcut_doc_analyze.py -- 文档结构化分析 Shortcut

获取飞书 docx 的完整 block 树，输出结构化数据（保留 block_id、层级关系、
类型、内容），方便 AI 做精确分析和后续操作。

相比 doc_read.py（输出 Markdown），此脚本保留更底层的结构信息。

用法：
    python shortcut_doc_analyze.py --doc DOC_TOKEN --format json
    python shortcut_doc_analyze.py --doc DOC_URL --format tree
    python shortcut_doc_analyze.py --doc DOC_TOKEN --format llm

输出格式：
    json  - 完整结构化 JSON
    tree  - 缩进树形文本（人类可读）
    llm   - LLM 友好格式（简洁层级 + 内容）
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from feishu_common import create_client, cli_run, print_json, extract_doc_id


def build_block_tree(blocks):
    """构建 block 映射和父子关系"""
    block_map = {b["block_id"]: b for b in blocks}
    children_map = {}
    for b in blocks:
        pid = b.get("parent_id", "")
        if pid:
            children_map.setdefault(pid, []).append(b)
    return block_map, children_map


def extract_block_content(block):
    """从 block 中提取文本内容"""
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
            parts.append(f"@user:{elem['mention_user'].get('user_id', '')}")
        elif "mention_doc" in elem:
            parts.append(f"[[{elem['mention_doc'].get('title', '')}]]")
        elif "link" in elem:
            parts.append(elem["link"].get("text", ""))
    return "".join(parts)


def format_tree(block_map, children_map, block_id, depth=0, max_depth=20):
    """生成缩进树形文本"""
    if depth > max_depth:
        return []
    block = block_map.get(block_id)
    if not block:
        return []
    bt = block.get("block_type", 0)
    content = extract_block_content(block)
    indent = "  " * depth
    lines = [f"{indent}[{bt}] {content[:80]}{'...' if len(content) > 80 else ''}"]
    for child in children_map.get(block_id, []):
        lines.extend(format_tree(block_map, children_map, child["block_id"], depth + 1, max_depth))
    return lines


def format_llm(block_map, children_map, block_id, depth=0):
    """生成 LLM 友好格式"""
    block = block_map.get(block_id)
    if not block:
        return []
    bt = block.get("block_type", 0)
    content = extract_block_content(block)
    if not content and bt not in (1, 22, 23):
        # 跳过无内容的非容器块
        pass

    lines = []
    prefix = "  " * depth
    type_labels = {1: "PAGE", 3: "H1", 4: "H2", 5: "H3", 6: "H4", 7: "H5",
                   12: "BULLET", 13: "ORDERED", 14: "CODE", 15: "QUOTE",
                   17: "TODO", 19: "CALLOUT", 22: "TABLE", 23: "FILE", 27: "IMAGE"}
    label = type_labels.get(bt, f"T{bt}")

    if content:
        lines.append(f"{prefix}[{label}] {content}")
    elif bt == 1:
        lines.append(f"{prefix}[{label}] ---")

    for child in children_map.get(block_id, []):
        lines.extend(format_llm(block_map, children_map, child["block_id"], depth + 1))
    return lines


def main():
    parser = argparse.ArgumentParser(description="文档结构化分析 Shortcut")
    parser.add_argument("--doc", required=True, help="文档 URL 或 token")
    parser.add_argument("--format", default="json", choices=["json", "tree", "llm"],
                        help="输出格式")
    parser.add_argument("--max-depth", type=int, default=20, help="最大递归深度")
    args = parser.parse_args()

    client = create_client()
    doc_id = extract_doc_id(args.doc)

    # 获取完整 block 树
    blocks_data = client.document_blocks_all(doc_id)
    blocks = blocks_data.get("items", [])
    if not blocks:
        print_json({"document_id": doc_id, "total_blocks": 0, "items": []})
        return

    block_map, children_map = build_block_tree(blocks)

    if args.format == "json":
        # 输出带层级结构的 JSON
        def build_json(block_id):
            block = block_map.get(block_id)
            if not block:
                return None
            bt = block.get("block_type", 0)
            item = {
                "block_id": block_id,
                "block_type": bt,
                "parent_id": block.get("parent_id", ""),
                "content": extract_block_content(block),
                "children": [],
            }
            for child in children_map.get(block_id, []):
                child_json = build_json(child["block_id"])
                if child_json:
                    item["children"].append(child_json)
            return item

        root_blocks = [b for b in blocks if not b.get("parent_id")]
        result = [build_json(b["block_id"]) for b in root_blocks]
        print_json({"document_id": doc_id, "total_blocks": len(blocks), "tree": result})

    elif args.format == "tree":
        root_blocks = [b for b in blocks if not b.get("parent_id")]
        lines = []
        for b in root_blocks:
            lines.extend(format_tree(block_map, children_map, b["block_id"], 0, args.max_depth))
        print("\n".join(lines))

    elif args.format == "llm":
        root_blocks = [b for b in blocks if not b.get("parent_id")]
        lines = []
        for b in root_blocks:
            lines.extend(format_llm(block_map, children_map, b["block_id"], 0))
        print("\n".join(lines))


if __name__ == "__main__":
    cli_run(main)
