#!/usr/bin/env python3
"""
calendar_list_events.py -- 查询日程列表

用法：
    python calendar_list_events.py
    python calendar_list_events.py --calendar-id primary --limit 10 --start 2026-07-27T00:00:00+08:00 --end 2026-08-03T00:00:00+08:00
"""

import argparse
import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from feishu_common import create_client, cli_run, print_json


def main():
    parser = argparse.ArgumentParser(description="查询飞书日程列表")
    parser.add_argument(
        "--calendar-id", default="primary", help="日历 ID，默认 primary"
    )
    parser.add_argument("--limit", type=int, default=50, help="最大返回条数（默认 50）")
    parser.add_argument(
        "--start", help="开始时间：秒级时间戳或 ISO 字符串；默认本周一 00:00"
    )
    parser.add_argument(
        "--end", help="结束时间：秒级时间戳或 ISO 字符串；默认下周一 00:00"
    )
    parser.add_argument("--anchor-time", help="锚点时间：秒级时间戳或 ISO 字符串")
    parser.add_argument("--sync-token", help="增量同步 token")
    parser.add_argument("--show-deleted", action="store_true", help="包含已删除日程")
    parser.add_argument("--raw", action="store_true", help="输出完整原始 JSON")
    args = parser.parse_args()

    client = create_client()

    now = datetime.datetime.now().astimezone()
    week_start = (now - datetime.timedelta(days=now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    week_end = week_start + datetime.timedelta(days=7)
    start_time = args.start or week_start.isoformat()
    end_time = args.end or week_end.isoformat()

    events = []
    page_token = None
    while len(events) < args.limit:
        data = client.calendar_list_events(
            calendar_id=args.calendar_id,
            page_size=50,
            page_token=page_token,
            start_time=start_time,
            end_time=end_time,
            anchor_time=args.anchor_time,
            sync_token=args.sync_token,
            show_deleted=args.show_deleted if args.show_deleted else None,
        )
        items = data.get("items", [])
        events.extend(items)
        if not data.get("has_more"):
            break
        page_token = data.get("page_token")
        if not page_token:
            break

    if args.raw:
        print_json(
            {
                "items": events,
                "total": len(events),
                "start": start_time,
                "end": end_time,
            }
        )
        return

    results = []
    for ev in events:
        start = ev.get("start_time", {})
        end = ev.get("end_time", {})
        results.append(
            {
                "event_id": ev.get("event_id", ""),
                "summary": ev.get("summary", ""),
                "start": start.get("date_time", start.get("timestamp", "")),
                "end": end.get("date_time", end.get("timestamp", "")),
                "organizer": ev.get("organizer", {}).get("id", ""),
                "status": ev.get("status", ""),
                "app_link": ev.get("app_link", ""),
            }
        )

    print_json(
        {"events": results, "total": len(results), "start": start_time, "end": end_time}
    )


if __name__ == "__main__":
    cli_run(main)
