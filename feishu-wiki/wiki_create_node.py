#!/usr/bin/env python3
"""
wiki_create_node.py -- 在 Wiki 知识空间创建节点

用法：
    python wiki_create_node.py "会议纪要" --space your_space_id
    python wiki_create_node.py "数据表" --space your_space_id --type sheet
    python wiki_create_node.py "子文档" --space your_space_id --parent OUxxxxx --type docx

支持的 obj_type：docx（默认）、sheet、bitable、mindnote、slides
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from feishu_common import confirm_action_or_exit, create_client, cli_run, print_json


def main():
    parser = argparse.ArgumentParser(description="在 Wiki 知识空间创建节点")
    parser.add_argument("title", help="节点标题")
    parser.add_argument("--space", required=True, help="知识空间 ID（space_id）")
    parser.add_argument("--type", default="docx", choices=["docx", "sheet", "bitable", "mindnote", "slides"],
                        help="节点类型，默认 docx")
    parser.add_argument("--parent", help="父节点 token（不传则创建在根目录）")
    parser.add_argument("--wiki-base-url", default="https://example.feishu.cn",
                        help="知识库基础 URL（默认 https://example.feishu.cn）")
    parser.add_argument("--yes", "-y", action="store_true", help="跳过确认")
    args = parser.parse_args()

    parent_info = f"，父节点: {args.parent}" if args.parent else ""
    confirm_action_or_exit(
        "wiki_create_node",
        f"将在 Wiki 空间 [{args.space}] 创建 {args.type} 节点: {args.title}{parent_info}",
        yes=args.yes,
    )

    client = create_client()
    data = client.wiki_create_node(
        space_id=args.space,
        obj_type=args.type,
        title=args.title,
        parent_node_token=args.parent,
    )
    node = data.get("node", {})
    print_json({
        "node_token": node.get("node_token", ""),
        "obj_token": node.get("obj_token", ""),
        "title": node.get("title", ""),
        "obj_type": node.get("obj_type", ""),
        "space_id": node.get("space_id", ""),
        "parent_node_token": node.get("parent_node_token", ""),
        "url": f"{args.wiki_base_url.rstrip('/')}/wiki/{node.get('node_token', '')}",
    })


if __name__ == "__main__":
    cli_run(main)
