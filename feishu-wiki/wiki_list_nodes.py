#!/usr/bin/env python3
"""
wiki_list_nodes.py -- 列出知识空间下的节点
用法:
  python3 wiki_list_nodes.py --space-id 123456
  python3 wiki_list_nodes.py --space-id 123456 --parent-node-token MV0qwHubqiloBmkoGS3cFYo8nNc
  python3 wiki_list_nodes.py --space-id 123456 --page-size 50
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from feishu_common import create_client, print_json, cli_run
import argparse

def main():
    parser = argparse.ArgumentParser(description="列出知识空间下的节点")
    parser.add_argument("--space-id", required=True, help="知识空间 ID")
    parser.add_argument("--parent-node-token", help="父节点 token（不传则列出根节点）")
    parser.add_argument("--page-size", type=int, default=50, help="每页数量")
    args = parser.parse_args()

    client = create_client()
    nodes = client.wiki_list_nodes(
        args.space_id,
        parent_node_token=args.parent_node_token,
        page_size=args.page_size,
    )
    print_json({"total": len(nodes), "nodes": nodes})

if __name__ == "__main__":
    cli_run(main)
