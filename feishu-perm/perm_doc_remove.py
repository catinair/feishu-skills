#!/usr/bin/env python3
"""
perm_doc_remove.py -- 移除文档/表格/多维表格的协作者
用法: python3 perm_doc_remove.py --token doxcnxxx --type docx --member-id ou_xxx
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from feishu_common import confirm_action_or_exit, create_client, print_json, cli_run
import argparse


def main():
    parser = argparse.ArgumentParser(description="移除文档协作者")
    parser.add_argument("--token", required=True, help="文档/表格/多维表格 token")
    parser.add_argument("--type", required=True, help="类型：docx/sheet/bitable/file/mindnote/slides")
    parser.add_argument("--member-id", required=True, help="协作者 ID")
    parser.add_argument("--yes", "-y", action="store_true", help="跳过确认")
    args = parser.parse_args()

    confirm_action_or_exit(
        "perm_doc_remove",
        f"确认移除协作者 {args.member_id} 从 {args.token}?",
        yes=args.yes,
    )

    client = create_client()
    result = client.perm_remove_member(args.token, args.type, args.member_id)
    print_json(result)


if __name__ == "__main__":
    cli_run(main)
