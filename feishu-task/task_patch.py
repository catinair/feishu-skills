#!/usr/bin/env python3
"""
task_patch.py -- 更新飞书任务（标题、描述、截止时间、完成状态等）
用法:
  # 完成任务
  python3 task_patch.py --guid <guid> --complete

  # 恢复未完成
  python3 task_patch.py --guid <guid> --uncomplete

  # 更新标题
  python3 task_patch.py --guid <guid> --summary "新标题"

  # 更新截止时间
  python3 task_patch.py --guid <guid> --due-timestamp 1675742789470 --due-all-day
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from feishu_common import cli_run, confirm_action_or_exit, create_client, print_json
import argparse

def main():
    parser = argparse.ArgumentParser(description="更新飞书任务")
    parser.add_argument("--guid", required=True, help="任务 GUID")
    parser.add_argument("--summary", help="新标题")
    parser.add_argument("--description", help="新描述")
    parser.add_argument("--due-timestamp", help="新截止时间戳（毫秒）")
    parser.add_argument("--due-all-day", action="store_true", help="截止时间是否精确到天")
    parser.add_argument("--start-timestamp", help="新开始时间戳（毫秒）")
    parser.add_argument("--start-all-day", action="store_true", help="开始时间是否精确到天")
    parser.add_argument("--complete", action="store_true", help="标记任务为已完成")
    parser.add_argument("--uncomplete", action="store_true", help="恢复任务为未完成")
    parser.add_argument("--yes", "-y", action="store_true", help="跳过确认")
    parser.add_argument("--raw", action="store_true", help="输出完整原始 JSON")
    args = parser.parse_args()

    update_fields = []
    task_data = {}

    if args.summary is not None:
        update_fields.append("summary")
        task_data["summary"] = args.summary
    if args.description is not None:
        update_fields.append("description")
        task_data["description"] = args.description
    if args.due_timestamp:
        update_fields.append("due")
        task_data["due"] = {"timestamp": args.due_timestamp, "is_all_day": args.due_all_day}
    if args.start_timestamp:
        update_fields.append("start")
        task_data["start"] = {"timestamp": args.start_timestamp, "is_all_day": args.start_all_day}
    if args.complete:
        import time
        update_fields.append("completed_at")
        task_data["completed_at"] = str(int(time.time() * 1000))
    if args.uncomplete:
        update_fields.append("completed_at")
        task_data["completed_at"] = "0"

    if not update_fields:
        parser.error("至少指定一个要修改的字段")

    client = create_client()
    confirm_action_or_exit(
        "task_patch",
        f"确认更新任务 {args.guid}?",
        yes=args.yes,
        is_trusted=False,
    )
    result = client.task_patch(
        task_guid=args.guid,
        update_fields=update_fields,
        task_data=task_data,
    )
    if args.raw:
        print_json(result)
        return

    task = result if isinstance(result, dict) else {}
    print_json({
        "status": "ok",
        "task_guid": task.get("guid", args.guid),
        "summary": task.get("summary", ""),
        "completed": task.get("completed", False),
        "completed_at": task.get("completed_at", ""),
    })

if __name__ == "__main__":
    cli_run(main)
