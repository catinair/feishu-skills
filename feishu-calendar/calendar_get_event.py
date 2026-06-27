#!/usr/bin/env python3
"""
calendar_get_event.py -- 查询单个日程详情

用法：
    python calendar_get_event.py <event_id>
    python calendar_get_event.py bcba0bea-c4a6-4f82-b1dd-d03188603974_0 --raw
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from feishu_common import create_client, cli_run, print_json


def main():
    parser = argparse.ArgumentParser(description="查询飞书日程详情")
    parser.add_argument("event_id", help="日程 event_id")
    parser.add_argument("--calendar-id", default="primary", help="日历 ID，默认 primary")
    parser.add_argument("--raw", action="store_true", help="输出完整原始 JSON")
    args = parser.parse_args()

    client = create_client()
    data = client.calendar_get_event(args.event_id, calendar_id=args.calendar_id)
    event = data.get("event", data)

    if args.raw:
        print_json(data if "event" in data else {"event": event})
        return

    start = event.get("start_time", {})
    end = event.get("end_time", {})
    result = {
        "event_id": event.get("event_id", ""),
        "summary": event.get("summary", ""),
        "description": event.get("description", ""),
        "start": start.get("date_time", start.get("timestamp", "")),
        "end": end.get("date_time", end.get("timestamp", "")),
        "organizer": event.get("organizer", {}).get("id", ""),
        "attendees": [
            {"id": a.get("id", ""), "type": a.get("type", ""), "status": a.get("status", "")}
            for a in event.get("attendees", [])
        ],
        "location": event.get("location", {}),
        "visibility": event.get("visibility", ""),
        "status": event.get("status", ""),
        "app_link": event.get("app_link", ""),
    }
    print_json(result)


if __name__ == "__main__":
    cli_run(main)
