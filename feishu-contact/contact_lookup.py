#!/usr/bin/env python3
"""
contact_lookup.py -- 部门人员信息查询（纯 API）
用法:
  python3 contact_lookup.py --name 夏草          # 按姓名模糊查询
  python3 contact_lookup.py --openid ou_xxx      # 按 openid 精确查询
  python3 contact_lookup.py --user-id uid_xxx    # 按 user_id 精确查询
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from feishu_common import lookup_contact, create_client, cli_run
import argparse


def print_person(p):
    print(f"  姓名: {p.get('name', '-')}")
    print(f"  花名: {p.get('nickname', '-')}")
    print(f"  open_id: {p.get('open_id', '-')}")
    print(f"  user_id: {p.get('user_id', '-')}")
    print(f"  邮箱: {p.get('email', '-')}")
    print(f"  部门: {p.get('department_id', '-')}")
    print(f"  状态: {p.get('status', '-')}")
    print()


def main():
    parser = argparse.ArgumentParser(description="查询部门人员信息（纯 API）")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--name", help="按姓名模糊查询")
    group.add_argument("--openid", help="按 openid 精确查询")
    group.add_argument("--user-id", help="按 user_id 精确查询")
    args = parser.parse_args()

    client = create_client()

    if args.name:
        results = lookup_contact(name=args.name, client=client)
    elif args.openid:
        results = lookup_contact(openid=args.openid, client=client)
    elif args.user_id:
        results = lookup_contact(user_id=args.user_id, client=client)

    if not results:
        print("未找到匹配人员")
        return

    print(f"找到 {len(results)} 人:\n")
    for p in results:
        print_person(p)


if __name__ == "__main__":
    cli_run(main)
