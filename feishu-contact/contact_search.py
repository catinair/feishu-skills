#!/usr/bin/env python3
"""
contact_search.py -- 搜索飞书用户

用法：
    python contact_search.py 张三
    python contact_search.py 张三 --limit 10

注意：
    使用 Search API（/open-apis/search/v1/user），需要 user_access_token。
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from feishu_common import cli_run, create_client, print_json


def main():
    parser = argparse.ArgumentParser(description="搜索飞书用户")
    parser.add_argument("query", help="搜索关键词（姓名、拼音等）")
    parser.add_argument("--limit", type=int, default=20, help="最大返回条数（默认 20）")
    parser.add_argument("--raw", action="store_true", help="输出完整原始 JSON")
    args = parser.parse_args()

    client = create_client()
    users = client.contact_search_users(
        args.query,
        limit=args.limit,
    )

    if args.raw:
        print_json({"items": users, "total": len(users)})
        return

    results = []
    for u in users:
        results.append({
            "user_id": u.get("user_id", ""),
            "open_id": u.get("open_id", ""),
            "union_id": u.get("union_id", ""),
            "name": u.get("name", ""),
            "en_name": u.get("en_name", ""),
            "email": u.get("email", ""),
            "mobile": u.get("mobile", ""),
            "job_title": u.get("job_title", ""),
            "status": u.get("status", {}).get("is_activated", False),
        })

    print_json({"users": results, "total": len(results)})


if __name__ == "__main__":
    cli_run(main)
