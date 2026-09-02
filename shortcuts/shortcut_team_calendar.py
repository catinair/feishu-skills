#!/usr/bin/env python3
"""
shortcut_team_calendar.py — 团队日程管理 Shortcut

三步链路：
  1. 批量订阅团队日历（需订阅者权限）
  2. 诊断权限状态（谁还是游客、谁已是订阅者）
  3. 批量查询团队本周日程

用法:
  # 订阅指定日历
  python3 shortcuts/shortcut_team_calendar.py --subscribe <calendar_id> [<calendar_id> ...]

  # 诊断：列出所有可访问日历的权限状态
  python3 shortcuts/shortcut_team_calendar.py --diagnose

  # 查询团队本周日程
  python3 shortcuts/shortcut_team_calendar.py --report [--names "夏草,一月,银川"]

  # 一键：订阅 + 诊断 + 报告
  python3 shortcuts/shortcut_team_calendar.py --full --calendar-ids "id1,id2,id3"
"""

import argparse
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from feishu_common import create_client, cli_run, print_json

TZ = timezone(timedelta(hours=8))


def _week_range():
    """返回本周一 00:00 和下周一 00:00 的时间戳。"""
    now = datetime.now(TZ)
    monday = now - timedelta(days=now.weekday())
    monday_start = monday.replace(hour=0, minute=0, second=0, microsecond=0)
    next_monday = monday_start + timedelta(days=7)
    return str(int(monday_start.timestamp())), str(int(next_monday.timestamp()))


def _calendar_list(payload):
    """兼容不同返回结构，提取 calendar list。"""
    return payload.get("data", {}).get(
        "calendar_list", payload.get("calendars", payload.get("calendar_list", []))
    )


def _event_items(payload):
    """兼容不同返回结构，提取 event items。"""
    return payload.get("data", {}).get("items", payload.get("items", []))


def cmd_subscribe(client, calendar_ids, json_output=False):
    """批量订阅日历。"""
    results = []
    for cid in calendar_ids:
        try:
            resp = client.calendar_subscribe(cid)
            ok = resp.get("code", 0) == 0 if isinstance(resp, dict) else True
            item = {"calendar_id": cid, "ok": ok, "response": resp}
            results.append(item)
            if not json_output:
                if ok:
                    print(f"✅ 已订阅/已切换订阅状态: {cid}")
                else:
                    print(
                        f"❌ 订阅失败: {cid} → [{resp.get('code')}] {resp.get('msg', '')}"
                    )
        except Exception as e:
            item = {"calendar_id": cid, "ok": False, "error": str(e)}
            results.append(item)
            if not json_output:
                print(f"❌ 订阅失败: {cid} → {e}")
    return results


def cmd_diagnose(client, json_output=False):
    """诊断：列出所有可访问日历，尝试查日程判断权限级别。"""
    calendars = client.calendar_list_calendars()
    cal_list = _calendar_list(calendars)

    if not cal_list:
        if not json_output:
            print("无可访问日历")
        return []

    start, end = _week_range()
    results = []

    for cal in cal_list:
        cid = cal.get("calendar_id", "")
        name = cal.get("summary", cal.get("summary_override", ""))
        cal_type = cal.get("type", "")

        if cal_type == "google":
            continue

        try:
            events = client.calendar_list_events(
                cid, page_size=50, start_time=start, end_time=end
            )
            items = _event_items(events)
            can_see_detail = any(ev.get("summary") for ev in items)
            level = "订阅者" if can_see_detail else "游客"
        except Exception:
            level = "游客"

        results.append(
            {
                "name": name,
                "calendar_id": cid,
                "type": cal_type,
                "level": level,
            }
        )

    if not json_output:
        print(f"\n{'成员':<12} {'类型':<10} {'权限':<8}")
        print("-" * 35)
        for r in sorted(results, key=lambda x: x["name"]):
            icon = "✅" if r["level"] == "订阅者" else "⚠️"
            print(f"{icon} {r['name']:<10} {r['type']:<10} {r['level']:<8}")

        tourists = [r for r in results if r["level"] == "游客"]
        if tourists:
            print(
                f"\n⚠️ {len(tourists)} 位成员仍为「游客」，仅能看到忙闲，无法查看日程详情。"
            )
            print("请提醒对方将你的日历权限从「游客」升级为「订阅者」。")

    return results


def cmd_report(client, filter_names=None, json_output=False):
    """查询团队本周日程。"""
    calendars = client.calendar_list_calendars()
    cal_list = _calendar_list(calendars)

    if filter_names:
        filter_names = [n.strip() for n in filter_names]

    start, end = _week_range()
    all_events = []

    for cal in cal_list:
        cid = cal.get("calendar_id", "")
        name = cal.get("summary", cal.get("summary_override", ""))
        cal_type = cal.get("type", "")

        if cal_type == "google" or cal_type == "shared":
            continue
        if filter_names and name not in filter_names:
            continue

        try:
            events = client.calendar_list_events(
                cid, page_size=50, start_time=start, end_time=end
            )
            items = _event_items(events)
            for ev in items:
                if ev.get("status") == "cancelled":
                    continue
                summary = ev.get("summary", "")
                if not summary:
                    continue
                st = ev.get("start_time", {})
                et = ev.get("end_time", {})
                start_ts = int(st.get("timestamp", 0))
                end_ts = int(et.get("timestamp", 0))
                all_events.append(
                    {
                        "name": name,
                        "calendar_id": cid,
                        "summary": summary,
                        "start": start_ts,
                        "end": end_ts,
                    }
                )
        except Exception:
            pass

    all_events.sort(key=lambda x: x["start"])

    if not json_output:
        print(f"\n团队本周日程 ({len(all_events)} 条)")
        print("=" * 60)
        current_day = None
        for ev in all_events:
            dt = datetime.fromtimestamp(ev["start"], tz=TZ)
            day = dt.strftime("%m/%d %a")
            if day != current_day:
                current_day = day
                print(f"\n── {day} ──")
            start_str = dt.strftime("%H:%M")
            end_str = datetime.fromtimestamp(ev["end"], tz=TZ).strftime("%H:%M")
            print(f"  {start_str}-{end_str}  [{ev['name']}] {ev['summary']}")

    return all_events


def main():
    parser = argparse.ArgumentParser(description="团队日程管理 Shortcut")
    parser.add_argument(
        "--subscribe",
        nargs="+",
        metavar="CALENDAR_ID",
        help="订阅指定日历；再次调用同一日历会取消订阅",
    )
    parser.add_argument("--diagnose", action="store_true", help="诊断团队成员日历权限")
    parser.add_argument("--report", action="store_true", help="查询团队本周日程")
    parser.add_argument("--full", action="store_true", help="一键：订阅 + 诊断 + 报告")
    parser.add_argument(
        "--calendar-ids", type=str, help="待订阅的日历 ID 列表，逗号分隔"
    )
    parser.add_argument("--names", type=str, help="按名称过滤成员，逗号分隔")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")

    args = parser.parse_args()
    client = create_client()
    output = {}

    if args.subscribe:
        output["subscribe"] = cmd_subscribe(client, args.subscribe, args.json)
    elif args.diagnose:
        output["diagnose"] = cmd_diagnose(client, args.json)
    elif args.report:
        output["report"] = cmd_report(
            client,
            filter_names=args.names.split(",") if args.names else None,
            json_output=args.json,
        )
    elif args.full:
        if args.calendar_ids:
            cids = [c.strip() for c in args.calendar_ids.split(",") if c.strip()]
            output["subscribe"] = cmd_subscribe(client, cids, args.json)
        output["diagnose"] = cmd_diagnose(client, args.json)
        output["report"] = cmd_report(
            client,
            filter_names=args.names.split(",") if args.names else None,
            json_output=args.json,
        )
    else:
        parser.print_help()
        return

    if args.json:
        print_json(output)


if __name__ == "__main__":
    cli_run(main)
