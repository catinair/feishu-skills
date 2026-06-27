#!/usr/bin/env python3
"""
calendar_delete_event.py -- 删除飞书日程

用法：
    python calendar_delete_event.py <event_id>
    python calendar_delete_event.py bcba0bea-c4a6-4f82-b1dd-d03188603974_0 --yes
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from feishu_common import confirm_action_or_exit, create_client, cli_run, print_json


def main():
    parser = argparse.ArgumentParser(description="删除飞书日程")
    parser.add_argument("event_id", help="日程 event_id")
    parser.add_argument("--calendar-id", default="primary", help="日历 ID，默认 primary")
    parser.add_argument("--yes", "-y", action="store_true", help="跳过确认")
    args = parser.parse_args()

    confirm_action_or_exit("calendar_delete_event", f"确认删除日程 {args.event_id}?", yes=args.yes)

    client = create_client()
    client.calendar_delete_event(args.event_id, calendar_id=args.calendar_id)
    print_json({"deleted": True, "event_id": args.event_id})


if __name__ == "__main__":
    cli_run(main)
