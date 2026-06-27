#!/usr/bin/env python3
"""
minutes_transcript.py -- 导出飞书妙记转写内容
用法: python3 minutes_transcript.py --token obcnxxx [--output ./transcript.txt]
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from feishu_common import cli_run, create_client
import argparse
import json


def format_transcript(data):
    """将转写内容格式化为纯文本"""
    lines = []
    segments = data.get("segments", [])
    for seg in segments:
        speaker = seg.get("speaker", "未知")
        start = seg.get("start_time", "")
        end = seg.get("end_time", "")
        text = seg.get("text", "")
        lines.append(f"[{start} - {end}] {speaker}: {text}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="导出妙记转写内容")
    parser.add_argument("--token", required=True, help="妙记 token")
    parser.add_argument("--output", help="输出文件路径（可选，默认打印到 stdout）")
    parser.add_argument("--raw", action="store_true", help="输出原始 JSON 而非格式化文本")
    args = parser.parse_args()

    client = create_client()
    result = client.minutes_transcript(args.token)

    if args.raw:
        output = json.dumps(result, ensure_ascii=False, indent=2)
    else:
        minute = result.get("minute", {})
        title = minute.get("title", "未命名妙记")
        duration = minute.get("duration", "")
        lines = [f"标题: {title}", f"时长: {duration}ms", "", "=== 转写内容 ===", ""]
        lines.append(format_transcript(result))
        output = "\n".join(lines)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"转写内容已保存到: {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    cli_run(main)
