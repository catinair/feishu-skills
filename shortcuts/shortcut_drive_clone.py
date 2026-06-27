#!/usr/bin/env python3
"""
shortcut_drive_clone.py -- Drive 文件/文件夹复制 Shortcut

支持两种场景：
    1. 单文件复制（用户指定）：
       python shortcut_drive_clone.py --source FILE_TOKEN --target FOLDER_TOKEN --name "副本"

    2. 批量复制（模板化/自动化）：
       python shortcut_drive_clone.py --source-folder FOLDER_TOKEN --target FOLDER_TOKEN
       python shortcut_drive_clone.py --source-folder FOLDER_TOKEN --target FOLDER_TOKEN --filter "周报"

安全：写操作默认需要确认，--yes 跳过。
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from feishu_common import cli_run, confirm_action_or_exit, create_client, print_json, DEFAULT_FOLDER_TOKEN


def main():
    parser = argparse.ArgumentParser(description="Drive 文件/文件夹复制 Shortcut")
    parser.add_argument("--source", help="源文件 token（单文件复制）")
    parser.add_argument("--source-folder", help="源文件夹 token（批量复制）")
    parser.add_argument("--target", required=True, help="目标文件夹 token")
    parser.add_argument("--name", help="新文件名称（单文件复制时）")
    parser.add_argument("--filter", help="批量复制时按名称过滤（模糊匹配）")
    parser.add_argument("--type", help="源文件类型（单文件复制时，如 docx/sheet/bitable）")
    parser.add_argument("--yes", "-y", action="store_true", help="跳过确认")
    args = parser.parse_args()

    if not (args.source or args.source_folder):
        parser.error("请提供 --source（单文件）或 --source-folder（批量）之一")
    if args.source and not args.name:
        parser.error("单文件复制需要提供 --name")

    client = create_client()

    if args.source:
        # 单文件复制
        file_type = args.type
        if not file_type:
            # 尝试从文件名推断
            if "." in args.name:
                ext = args.name.rsplit(".", 1)[-1].lower()
                type_map = {"docx": "docx", "xlsx": "sheet", "sheet": "sheet", "csv": "sheet",
                            "pdf": "file", "png": "file", "jpg": "file", "jpeg": "file"}
                file_type = type_map.get(ext, "docx")
            else:
                file_type = "docx"

        confirm_action_or_exit(
            "drive_create",
            f"将复制文件 {args.source} 到文件夹 {args.target}，新名称: {args.name}",
            yes=args.yes,
        )

        result = client.copy_file(args.source, args.name, file_type, args.target)
        print_json({"mode": "single", "copied": result})

    else:
        # 批量复制
        files = client.list_files(folder_token=args.source_folder, page_size=200)
        if args.filter:
            query = args.filter.lower()
            files = [f for f in files if query in f.get("name", "").lower()]

        if not files:
            print_json({"mode": "batch", "source_folder": args.source_folder, "target": args.target,
                        "matched": 0, "copied": []})
            return

        file_list = "\n".join(f"  - {f.get('name')} ({f.get('type')})" for f in files[:10])
        more = f"\n  ... 还有 {len(files) - 10} 个" if len(files) > 10 else ""
        confirm_action_or_exit(
            "drive_create",
            f"将从文件夹 {args.source_folder} 复制 {len(files)} 个文件到 {args.target}\n{file_list}{more}",
            yes=args.yes,
        )

        copied = []
        for f in files:
            try:
                result = client.copy_file(f["token"], f["name"], f["type"], args.target)
                copied.append({"source": f["token"], "name": f["name"], "result": result})
            except RuntimeError as e:
                copied.append({"source": f["token"], "name": f["name"], "error": str(e)})

        print_json({"mode": "batch", "source_folder": args.source_folder, "target": args.target,
                    "matched": len(files), "copied": copied})


if __name__ == "__main__":
    cli_run(main)
