#!/usr/bin/env python3
"""
wiki_list_all_nodes.py -- 递归遍历知识空间所有节点
用法:
  python3 wiki_list_all_nodes.py --space-id your_space_id
  python3 wiki_list_all_nodes.py --space-id your_space_id --wiki-base-url https://example.feishu.cn
  python3 wiki_list_all_nodes.py --space-id your_space_id --max-depth 3
  python3 wiki_list_all_nodes.py --space-id your_space_id --filter "医药"
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from feishu_common import create_client, print_json, cli_run
import argparse


def collect_nodes(client, space_id, parent_node_token=None, wiki_base_url=None,
                  depth=0, max_depth=None, title_filter=None):
    """递归收集节点，返回扁平列表（每项含 depth 和 url）"""
    nodes = client.wiki_list_nodes(space_id, parent_node_token=parent_node_token)

    # 按 title 过滤（仅过滤当前层级）
    if title_filter:
        nodes = [n for n in nodes if title_filter.lower() in n.get("title", "").lower()]

    result = []
    for node in nodes:
        node_token = node.get("node_token", "")
        entry = {
            "depth": depth,
            "title": node.get("title", ""),
            "node_token": node_token,
            "obj_token": node.get("obj_token", ""),
            "obj_type": node.get("obj_type", ""),
            "node_type": node.get("node_type", ""),
            "has_child": node.get("has_child", False),
            "parent_node_token": node.get("parent_node_token", ""),
        }
        if wiki_base_url:
            entry["url"] = f"{wiki_base_url.rstrip('/')}/wiki/{node_token}"

        result.append(entry)

        # 递归子节点
        if node.get("has_child") and (max_depth is None or depth + 1 < max_depth):
            children = collect_nodes(
                client, space_id,
                parent_node_token=node_token,
                wiki_base_url=wiki_base_url,
                depth=depth + 1,
                max_depth=max_depth,
                title_filter=None,  # 过滤仅作用于顶层
            )
            result.extend(children)

    return result


def main():
    parser = argparse.ArgumentParser(description="递归遍历知识空间所有节点")
    parser.add_argument("--space-id", required=True, help="知识空间 ID")
    parser.add_argument("--wiki-base-url", help="知识库基础 URL（如 https://example.feishu.cn），用于拼接节点链接")
    parser.add_argument("--max-depth", type=int, help="最大遍历深度（默认无限制）")
    parser.add_argument("--filter", dest="title_filter", help="按标题过滤（仅顶层，大小写不敏感）")
    args = parser.parse_args()

    client = create_client()
    nodes = collect_nodes(
        client, args.space_id,
        wiki_base_url=args.wiki_base_url,
        max_depth=args.max_depth,
        title_filter=args.title_filter,
    )

    # 统计
    stats = {
        "total": len(nodes),
        "by_type": {},
        "by_node_type": {},
        "max_depth_reached": max((n["depth"] for n in nodes), default=0),
    }
    for n in nodes:
        obj_type = n["obj_type"]
        node_type = n["node_type"]
        stats["by_type"][obj_type] = stats["by_type"].get(obj_type, 0) + 1
        stats["by_node_type"][node_type] = stats["by_node_type"].get(node_type, 0) + 1

    print_json({"stats": stats, "nodes": nodes})


if __name__ == "__main__":
    cli_run(main)
