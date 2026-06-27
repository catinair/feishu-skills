#!/usr/bin/env python3
"""
calendar_update_event.py -- 更新飞书日程

用法：
    python calendar_update_event.py <event_id> --summary "新标题"
    python calendar_update_event.py <event_id> --start "2026-04-25 14:00" --end "2026-04-25 15:00"
    python calendar_update_event.py <event_id> --desc "更新描述" --location "会议室 B" --yes
"""

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from feishu_common import confirm_action_or_exit, create_client, cli_run, print_json


def parse_time(value):
    """将时间字符串转换为 API 所需格式（timestamp 或 date）"""
    import datetime
    if value is None:
        return None
    if isinstance(value, str) and value.isdigit():
        return int(value)
    if re.match(r"^\d{4}-\d{2}-\d{2}$", value):
        return value
    if "T" in value and ("+" in value or "Z" in value):
        ts = value[:-1] + "+00:00" if value.endswith("Z") else value
        try:
            dt = datetime.datetime.fromisoformat(ts)
            return int(dt.timestamp())
        except ValueError:
            return value
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            dt = datetime.datetime.strptime(value, fmt)
            dt = dt.replace(tzinfo=datetime.timezone(datetime.timedelta(hours=8)))
            return int(dt.timestamp())
        except ValueError:
            continue
    return value


def main():
    parser = argparse.ArgumentParser(description="更新飞书日程")
    parser.add_argument("event_id", help="日程 ID")
    parser.add_argument("--calendar-id", default="primary", help="日历 ID，默认 primary")
    parser.add_argument("--summary", help="日程标题")
    parser.add_argument("--desc", "-d", help="日程描述")
    parser.add_argument("--start", help="开始时间")
    parser.add_argument("--end", help="结束时间")
    parser.add_argument("--start-timestamp", type=int, help="开始时间戳（秒）")
    parser.add_argument("--end-timestamp", type=int, help="结束时间戳（秒）")
    parser.add_argument("--location", "-l", help="地点")
    parser.add_argument("--raw", action="store_true", help="输出完整原始 JSON")
    parser.add_argument("--yes", "-y", action="store_true", help="跳过确认")
    args = parser.parse_args()

    start = parse_time(args.start) or args.start_timestamp
    end = parse_time(args.end) or args.end_timestamp

    confirm_action_or_exit(
        "calendar_update_event",
        f"确认更新日程 {args.event_id[:30]}...?",
        yes=args.yes,
    )

    client = create_client()
    data = client.calendar_update_event(
        event_id=args.event_id,
        calendar_id=args.calendar_id,
        summary=args.summary,
        description=args.desc,
        start_time=start,
        end_time=end,
        location=args.location,
    )
    event = data.get("event", {})

    if args.raw:
        print_json(data if "event" in data else {"event": event})
        return

    result = {
        "event_id": event.get("event_id", ""),
        "summary": event.get("summary", ""),
        "app_link": event.get("app_link", ""),
        "status": event.get("status", ""),
    }
    print_json(result)


if __name__ == "__main__":
    cli_run(main)
