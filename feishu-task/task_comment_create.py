#!/usr/bin/env python3
"""
task_comment_create.py -- 为飞书任务创建评论
用法:
  # 发表评论
  python3 task_comment_create.py --resource-id <task_guid> --content "评论内容"

  # 回复某条评论
  python3 task_comment_create.py --resource-id <task_guid> --content "回复内容" --reply-to <comment_id>
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from feishu_common import cli_run, confirm_action_or_exit, create_client, print_json
import argparse

def main():
    parser = argparse.ArgumentParser(description="为飞书任务创建评论")
    parser.add_argument("--resource-id", required=True, help="任务 GUID")
    parser.add_argument("--content", required=True, help="评论内容")
    parser.add_argument("--reply-to", help="回复的评论 ID")
    parser.add_argument("--yes", "-y", action="store_true", help="跳过确认")
    args = parser.parse_args()

    client = create_client()
    confirm_action_or_exit(
        "task_comment_create",
        f"确认为任务 {args.resource_id} 创建评论?",
        yes=args.yes,
        is_trusted=False,
    )
    result = client.task_comment_create(
        resource_id=args.resource_id,
        content=args.content,
        reply_to_comment_id=args.reply_to,
    )
    print_json(result)

if __name__ == "__main__":
    cli_run(main)
