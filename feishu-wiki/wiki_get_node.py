#!/usr/bin/env python3
"""
wiki_get_node.py -- 查询 wiki 节点信息（URL 转真实 token）
用法: python3 wiki_get_node.py --token wikcnxxx_or_url

输出包含 obj_type（docx/sheet/bitable 等）和 obj_token（真实文档 token）
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from feishu_common import create_client, print_json, cli_run
import argparse

def extract_wiki_token(arg):
    """从 wiki URL 中提取 token"""
    if "/wiki/" in arg:
        return arg.split("/wiki/")[-1].split("?")[0].split("/")[0]
    return arg

def main():
    parser = argparse.ArgumentParser(description="查询 wiki 节点信息")
    parser.add_argument("--token", required=True, help="wiki token 或完整 URL")
    args = parser.parse_args()

    wiki_token = extract_wiki_token(args.token)

    client = create_client()
    result = client.wiki_get_node(wiki_token)
    print_json(result)

if __name__ == "__main__":
    cli_run(main)
