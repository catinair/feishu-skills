#!/usr/bin/env python3
"""
perm_doc_share.py -- 给文档/表格/多维表格添加协作者
用法: python3 perm_doc_share.py --token doxcnxxx --type docx --member-id ou_xxx --member-type openid --perm view
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from feishu_common import confirm_action_or_exit, create_client, print_json, cli_run
import argparse


def main():
    parser = argparse.ArgumentParser(description="添加文档协作者")
    parser.add_argument("--token", required=True, help="文档/表格/多维表格 token")
    parser.add_argument("--type", required=True, help="类型：docx/sheet/bitable/file/mindnote/slides")
    parser.add_argument("--member-id", required=True, help="协作者 ID")
    parser.add_argument("--member-type", default="openid", help="协作者类型：openid/union_id/user_id/openchat/department_id（默认 openid）")
    parser.add_argument("--perm", default="view", help="权限：view/edit/full_access（默认 view）")
    parser.add_argument("--yes", "-y", action="store_true", help="跳过确认")
    args = parser.parse_args()

    confirm_action_or_exit(
        "perm_doc_share",
        f"确认给 {args.token} 添加协作者 {args.member_id}（权限: {args.perm}）?",
        yes=args.yes,
    )

    client = create_client()
    result = client.perm_add_member(args.token, args.type, args.member_id, args.member_type, args.perm)
    print_json(result)


if __name__ == "__main__":
    cli_run(main)
