#!/usr/bin/env python3
"""
contact_colleagues.py -- 查询当前用户同部门的所有人员
用法: python3 contact_colleagues.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from feishu_common import cli_run, create_client, print_json
import argparse


def main():
    parser = argparse.ArgumentParser(description="查询当前用户同部门的所有人员")
    parser.add_argument("--raw", action="store_true", help="输出完整原始 JSON")
    args = parser.parse_args()

    client = create_client()
    result = client.contact_colleagues()

    if args.raw:
        print_json(result)
        return

    me = result["me"]
    members = result["members"]
    dept_id = result["department_id"]
    dept_name = result.get("department_name", "")

    print(f"当前用户: {me.get('name', '-')} ({me.get('open_id', '-')})")
    print(f"部门: {dept_name or dept_id}")
    print(f"同部门共 {len(members)} 人:\n")
    for u in members:
        name = u.get("name", u.get("en_name", "-"))
        oid = u.get("open_id", "-")
        uid = u.get("user_id", "-")
        print(f"  {name} | open_id: {oid} | user_id: {uid}")


if __name__ == "__main__":
    cli_run(main)
