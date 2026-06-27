#!/usr/bin/env python3
"""
calendar_freebusy.py -- 查询用户忙闲状态

用法：
    python calendar_freebusy.py --user-id your_user_id --date 2026-04-25
    python calendar_freebusy.py --openid ou_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx --start "2026-04-25T09:00:00+08:00" --end "2026-04-25T18:00:00+08:00"

注意：
    Calendar 忙闲 API 仅支持 open_id。如传 --user-id，会先通过 contact API 获取 open_id。
"""

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from feishu_common import create_client, cli_run, print_json


def main():
    parser = argparse.ArgumentParser(description="查询飞书用户忙闲状态")
    parser.add_argument("--user-id", help="按 user_id 查询（会自动转换为 open_id）")
    parser.add_argument("--openid", help="按 open_id 查询（推荐）")
    parser.add_argument("--date", help="查询日期（如 2026-04-25，默认当天 09:00-18:00）")
    parser.add_argument("--start", help="开始时间（ISO 格式，如 2026-04-25T09:00:00+08:00）")
    parser.add_argument("--end", help="结束时间（ISO 格式）")
    parser.add_argument("--raw", action="store_true", help="输出完整原始 JSON")
    args = parser.parse_args()

    if not (args.user_id or args.openid):
        parser.error("请提供 --user-id 或 --openid")

    client = create_client()

    # 解析时间范围
    if args.date:
        time_min = f"{args.date}T00:00:00+08:00"
        time_max = f"{args.date}T23:59:59+08:00"
    elif args.start and args.end:
        time_min = args.start
        time_max = args.end
    else:
        parser.error("请提供 --date 或同时提供 --start 和 --end")

    # 获取 open_id
    if args.openid:
        open_id = args.openid
    else:
        user_data = client.contact_get_user(args.user_id, user_id_type="user_id")
        user = user_data.get("user", {})
        open_id = user.get("open_id", "")
        if not open_id:
            raise RuntimeError(f"无法获取 user_id={args.user_id} 的 open_id")

    data = client.calendar_freebusy(open_id, time_min, time_max)

    if args.raw:
        print_json(data)
        return

    busy_list = data.get("freebusy_list", [])
    results = []
    for item in busy_list:
        results.append({
            "start": item.get("start_time", ""),
            "end": item.get("end_time", ""),
        })

    print_json({
        "user_id": args.user_id or open_id,
        "time_range": {"start": time_min, "end": time_max},
        "busy_slots": results,
        "total_busy": len(results),
    })


if __name__ == "__main__":
    cli_run(main)
