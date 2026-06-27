#!/usr/bin/env python3
"""
shortcut_meeting_notify.py -- 创建日程并发送通知 Shortcut

用法：
    python shortcut_meeting_notify.py "周会" --start "2026-04-25 14:00" --end "2026-04-25 15:00" --chat-id oc_xxx
    python shortcut_meeting_notify.py "项目复盘" --start "2026-04-25 10:00" --end "2026-04-25 11:30" --chat-id oc_xxx --location "会议室 A"

拼装步骤：
    1. 创建日程
    2. 发送会议通知消息到群聊
"""

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from feishu_common import cli_run, confirm_action_or_exit, create_client, print_json


def parse_time(value):
    """解析时间字符串为时间戳"""
    import datetime
    if value.isdigit():
        return int(value)
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            dt = datetime.datetime.strptime(value, fmt)
            dt = dt.replace(tzinfo=datetime.timezone(datetime.timedelta(hours=8)))
            return int(dt.timestamp())
        except ValueError:
            continue
    return value


def main():
    parser = argparse.ArgumentParser(description="创建日程并发送通知")
    parser.add_argument("summary", help="会议标题")
    parser.add_argument("--start", required=True, help="开始时间（如 2026-04-25 14:00）")
    parser.add_argument("--end", required=True, help="结束时间")
    parser.add_argument("--chat-id", required=True, help="通知群聊 ID")
    parser.add_argument("--desc", help="会议描述")
    parser.add_argument("--location", help="地点")
    parser.add_argument("--yes", "-y", action="store_true", help="跳过确认")
    args = parser.parse_args()

    start_ts = parse_time(args.start)
    end_ts = parse_time(args.end)

    confirm_action_or_exit(
        "calendar_create_event",
        f"将创建日程「{args.summary}」并通知群 {args.chat_id}\n时间: {args.start} - {args.end}",
        yes=args.yes,
    )

    client = create_client()

    # 1. 创建日程
    data = client.calendar_create_event(
        summary=args.summary,
        description=args.desc,
        start_time=start_ts,
        end_time=end_ts,
        location=args.location,
    )
    event = data.get("event", {})
    event_id = event.get("event_id", "")
    app_link = event.get("app_link", "")

    # 2. 发送通知
    location_info = f"\n📍 地点: {args.location}" if args.location else ""
    text = f"📅 新日程: {args.summary}\n🕐 时间: {args.start} - {args.end}{location_info}\n🔗 {app_link}"
    notify_result = client.im_send_text(args.chat_id, "chat_id", text)

    print_json({
        "created": True,
        "event_id": event_id,
        "summary": args.summary,
        "start": args.start,
        "end": args.end,
        "url": app_link,
        "notified": args.chat_id,
        "notify_message_id": notify_result.get("message_id", ""),
    })


if __name__ == "__main__":
    cli_run(main)
