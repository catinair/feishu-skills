#!/usr/bin/env python3
"""
minutes_artifacts.py -- 获取飞书妙记 AI 产物（总结、章节、待办）
用法: python3 minutes_artifacts.py --token obcnxxx
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from feishu_common import cli_run, create_client
import argparse
import json


def format_artifacts(data):
    """将 AI 产物格式化为易读文本"""
    lines = []
    summary = data.get("summary", "")
    if summary:
        lines.append("=== 妙记总结 ===")
        lines.append(summary)
        lines.append("")

    chapters = data.get("minute_chapters", [])
    if chapters:
        lines.append("=== 章节纪要 ===")
        for ch in chapters:
            title = ch.get("title", "未命名章节")
            start = ch.get("start_ms", "")
            stop = ch.get("stop_ms", "")
            content = ch.get("summary_content", "")
            lines.append(f"\n【{title}】({start}ms - {stop}ms)")
            lines.append(content)
        lines.append("")

    todos = data.get("minute_todos", [])
    if todos:
        lines.append("=== 待办事项 ===")
        for todo in todos:
            content = todo.get("content", "")
            assignees = todo.get("assignees", [])
            assignee_str = ", ".join(assignees) if assignees else "未指定"
            lines.append(f"- [ ] {content} (@{assignee_str})")
        lines.append("")

    if not lines:
        return "暂无 AI 产物内容（妙记可能尚未生成总结）"
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="获取妙记 AI 产物（总结、章节、待办）")
    parser.add_argument("--token", required=True, help="妙记 token")
    parser.add_argument("--output", help="输出文件路径（可选，默认打印到 stdout）")
    parser.add_argument("--raw", action="store_true", help="输出原始 JSON")
    args = parser.parse_args()

    client = create_client()
    result = client.minutes_artifacts(args.token)

    if args.raw:
        output = json.dumps(result, ensure_ascii=False, indent=2)
    else:
        output = format_artifacts(result)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"AI 产物已保存到: {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    cli_run(main)
