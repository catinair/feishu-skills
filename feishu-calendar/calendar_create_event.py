#!/usr/bin/env python3
"""
calendar_create_event.py -- 创建飞书日程

用法：
    python calendar_create_event.py "周会" --start "2026-04-25 14:00" --end "2026-04-25 15:00"
    python calendar_create_event.py "跨时区会议" --start-timestamp 1774442400 --end-timestamp 1774446000
    python calendar_create_event.py "项目复盘" --start "2026-04-25 10:00" --end "2026-04-25 11:30" --location "会议室 A" --desc "季度复盘"

时间格式支持：
    - ISO 格式: 2026-04-25T14:00:00+08:00
    - 简单格式: 2026-04-25 14:00（自动补 +08:00）
    - 时间戳: 1774442400（秒）
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
    # 纯数字 = 时间戳
    if isinstance(value, str) and value.isdigit():
        return int(value)
    # 纯日期 2026-04-25
    if re.match(r"^\d{4}-\d{2}-\d{2}$", value):
        return value
    # ISO 格式（已含时区）→ 解析为 timestamp
    if "T" in value and ("+" in value or "Z" in value):
        ts = value[:-1] + "+00:00" if value.endswith("Z") else value
        try:
            dt = datetime.datetime.fromisoformat(ts)
            return int(dt.timestamp())
        except ValueError:
            return value
    # 简单格式 2026-04-25 14:00 → 解析为 timestamp
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            dt = datetime.datetime.strptime(value, fmt)
            dt = dt.replace(tzinfo=datetime.timezone(datetime.timedelta(hours=8)))
            return int(dt.timestamp())
        except ValueError:
            continue
    return value


def main():
    parser = argparse.ArgumentParser(description="创建飞书日程")
    parser.add_argument("summary", help="日程标题")
    parser.add_argument("--start", help="开始时间（如 2026-04-25 14:00 或时间戳）")
    parser.add_argument("--end", help="结束时间")
    parser.add_argument("--start-timestamp", type=int, help="开始时间戳（秒）")
    parser.add_argument("--end-timestamp", type=int, help="结束时间戳（秒）")
    parser.add_argument("--desc", "-d", help="日程描述")
    parser.add_argument("--location", "-l", help="地点")
    parser.add_argument("--calendar-id", default="primary", help="日历 ID，默认 primary")
    parser.add_argument("--identity", choices=["user", "tenant"], help="强制使用 user 或 tenant 身份创建")
    parser.add_argument("--raw", action="store_true", help="输出完整原始 JSON")
    parser.add_argument("--yes", "-y", action="store_true", help="跳过确认")
    args = parser.parse_args()

    start = parse_time(args.start) or args.start_timestamp
    end = parse_time(args.end) or args.end_timestamp

    if start is None or end is None:
        parser.error("必须提供 --start/--end 或 --start-timestamp/--end-timestamp")

    confirm_action_or_exit("calendar_create_event", f"确认创建日程「{args.summary}」?", yes=args.yes)

    client = create_client()
    use_user_token = {"user": True, "tenant": False}.get(args.identity) if args.identity else None
    data = client.calendar_create_event(
        calendar_id=args.calendar_id,
        summary=args.summary,
        description=args.desc,
        start_time=start,
        end_time=end,
        location=args.location,
        use_user_token=use_user_token,
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
