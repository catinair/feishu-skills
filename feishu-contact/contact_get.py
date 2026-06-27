#!/usr/bin/env python3
"""
contact_get.py -- 查询飞书用户详情

用法：
    python contact_get.py --user-id your_user_id
    python contact_get.py --openid ou_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    python contact_get.py --user-id your_user_id --raw

与 contact_lookup.py 的区别：
- contact_lookup.py 是统一入口（--name / --openid / --user-id）
- contact_get.py 专注详情查询，支持 --raw 输出
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from feishu_common import create_client, cli_run, print_json


def main():
    parser = argparse.ArgumentParser(description="查询飞书用户详情")
    parser.add_argument("--user-id", help="按 user_id 查询")
    parser.add_argument("--openid", help="按 open_id 查询")
    parser.add_argument("--union-id", help="按 union_id 查询")
    parser.add_argument("--raw", action="store_true", help="输出完整原始 JSON")
    args = parser.parse_args()

    if not (args.user_id or args.openid or args.union_id):
        parser.error("请提供 --user-id、--openid 或 --union-id 之一")

    client = create_client()

    if args.user_id:
        user_id = args.user_id
        id_type = "user_id"
    elif args.openid:
        user_id = args.openid
        id_type = "open_id"
    else:
        user_id = args.union_id
        id_type = "union_id"

    data = client.contact_get_user(user_id, user_id_type=id_type)
    user = data.get("user", {})

    if args.raw or not user:
        print_json(data)
        return

    # 精简输出
    result = {
        "user_id": user.get("user_id", ""),
        "open_id": user.get("open_id", ""),
        "union_id": user.get("union_id", ""),
        "name": user.get("name", ""),
        "en_name": user.get("en_name", ""),
        "nickname": user.get("nickname", ""),
        "email": user.get("email", ""),
        "mobile": user.get("mobile", ""),
        "department_ids": user.get("department_ids", []),
        "job_title": user.get("job_title", ""),
        "status": user.get("status", {}).get("is_activated", False),
        "avatar": user.get("avatar", {}).get("avatar_72", ""),
    }
    print_json(result)


if __name__ == "__main__":
    cli_run(main)
