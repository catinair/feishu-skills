#!/usr/bin/env python3
"""
calendar_list_events.py -- 查询日程列表

用法：
    python calendar_list_events.py
    python calendar_list_events.py --calendar-id primary --limit 10
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from feishu_common import create_client, cli_run, print_json


def main():
    parser = argparse.ArgumentParser(description="查询飞书日程列表")
    parser.add_argument("--calendar-id", default="primary", help="日历 ID，默认 primary")
    parser.add_argument("--limit", type=int, default=50, help="最大返回条数（默认 50）")
    parser.add_argument("--raw", action="store_true", help="输出完整原始 JSON")
    args = parser.parse_args()

    client = create_client()

    events = []
    page_token = None
    while len(events) < args.limit:
        data = client.calendar_list_events(
            calendar_id=args.calendar_id,
            page_size=min(max(args.limit - len(events), 50), 50),
            page_token=page_token,
        )
        items = data.get("items", [])
        events.extend(items)
        if not data.get("has_more"):
            break
        page_token = data.get("page_token")
        if not page_token:
            break

    if args.raw:
        print_json({"items": events, "total": len(events)})
        return

    results = []
    for ev in events:
        start = ev.get("start_time", {})
        end = ev.get("end_time", {})
        results.append({
            "event_id": ev.get("event_id", ""),
            "summary": ev.get("summary", ""),
            "start": start.get("date_time", start.get("timestamp", "")),
            "end": end.get("date_time", end.get("timestamp", "")),
            "organizer": ev.get("organizer", {}).get("id", ""),
            "status": ev.get("status", ""),
            "app_link": ev.get("app_link", ""),
        })

    print_json({"events": results, "total": len(results)})


if __name__ == "__main__":
    cli_run(main)
