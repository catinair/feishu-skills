#!/usr/bin/env python3
"""
task_create.py -- 创建飞书任务
用法: python3 task_create.py --summary "任务标题" [--description "描述"] [--due-timestamp 1675742789470] [--due-all-day] [--member ou_xxx]
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from feishu_common import cli_run, confirm_action_or_exit, create_client, print_json
import argparse

def main():
    parser = argparse.ArgumentParser(description="创建飞书任务")
    parser.add_argument("--summary", required=True, help="任务标题")
    parser.add_argument("--description", help="任务描述")
    parser.add_argument("--due-timestamp", help="截止时间戳（毫秒）")
    parser.add_argument("--due-all-day", action="store_true", help="截止时间是否精确到天")
    parser.add_argument("--member", action="append", help="负责人 open_id（可多次指定）")
    parser.add_argument("--extra", help="自定义附带数据")
    parser.add_argument("--yes", "-y", action="store_true", help="跳过确认")
    parser.add_argument("--raw", action="store_true", help="输出完整原始 JSON")
    args = parser.parse_args()

    due = None
    if args.due_timestamp:
        due = {"timestamp": args.due_timestamp, "is_all_day": args.due_all_day}

    members = None
    if args.member:
        members = [{"id": m, "type": "user", "role": "assignee"} for m in args.member]

    client = create_client()
    confirm_action_or_exit(
        "task_create",
        f"确认创建任务「{args.summary}」?",
        yes=args.yes,
        is_trusted=False,
    )
    result = client.task_create(
        summary=args.summary,
        description=args.description,
        due=due,
        members=members,
        extra=args.extra,
    )
    if args.raw:
        print_json(result)
        return

    task = result if isinstance(result, dict) else {}
    print_json({
        "status": "ok",
        "task_guid": task.get("guid", ""),
        "summary": task.get("summary", ""),
        "completed": task.get("completed", False),
    })

if __name__ == "__main__":
    cli_run(main)
