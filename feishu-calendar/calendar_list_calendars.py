#!/usr/bin/env python3
"""
calendar_list_calendars.py -- 查询日历列表

用法：
    python calendar_list_calendars.py
    python calendar_list_calendars.py --limit 10 --raw
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from feishu_common import create_client, cli_run, print_json


def main():
    parser = argparse.ArgumentParser(description="查询飞书日历列表")
    parser.add_argument("--limit", type=int, default=None, help="最大返回条数（默认不过滤）")
    parser.add_argument("--raw", action="store_true", help="输出完整原始 JSON")
    args = parser.parse_args()

    client = create_client()
    data = client.calendar_list_calendars()
    calendars = data.get("calendar_list", [])
    if args.limit is not None:
        calendars = calendars[:args.limit]

    if args.raw:
        print_json({"calendars": calendars, "total": len(calendars)})
        return

    results = []
    for cal in calendars:
        results.append({
            "calendar_id": cal.get("calendar_id", ""),
            "summary": cal.get("summary", ""),
            "description": cal.get("description", ""),
            "permission": cal.get("permission", ""),
            "type": cal.get("type", ""),
        })

    print_json({"calendars": results, "total": len(results)})


if __name__ == "__main__":
    cli_run(main)
