#!/usr/bin/env python3
"""
drive_export.py -- 导出文档为本地文件

用法:
    # 导出 docx 为 PDF
    python3 drive_export.py --token doccnxxx --doc-type docx --file-extension pdf --output ./doc.pdf

    # 导出 sheet 为 CSV（需指定 sub-id 即 sheet_id）
    python3 drive_export.py --token shtcnxxx --doc-type sheet --file-extension csv --sub-id 0edxxx --output ./sheet.csv

支持的文档类型: doc, docx, sheet, bitable
支持的导出格式: docx, pdf, xlsx, csv, markdown

输出路径说明：
    --output 指定本地保存路径，不传则使用导出文件名保存到当前目录。
    建议显式指定路径，避免文件散落在工作目录或 skill 目录下。
    示例: python3 drive_export.py --token xxx --doc-type docx --format pdf --output ~/Downloads/doc.pdf
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from feishu_common import create_client, print_json, cli_run
import argparse


def main():
    parser = argparse.ArgumentParser(description="导出文档为本地文件")
    parser.add_argument("--token", required=True, help="文档 token")
    parser.add_argument("--doc-type", required=True, choices=["doc", "docx", "sheet", "bitable"], help="文档类型")
    parser.add_argument("--file-extension", required=True, choices=["docx", "pdf", "xlsx", "csv", "markdown"], help="导出格式")
    parser.add_argument("--sub-id", default=None, help="子表 ID（sheet/bitable 导出 csv 时必填）")
    parser.add_argument("--output", default=None, help="本地保存路径（默认使用导出文件名）")
    parser.add_argument("--max-attempts", type=int, default=30, help="最大轮询次数（默认 30）")
    parser.add_argument("--poll-interval", type=int, default=2, help="轮询间隔秒数（默认 2）")
    args = parser.parse_args()

    if args.file_extension == "csv" and args.doc_type in ("sheet", "bitable") and not args.sub_id:
        raise RuntimeError("导出 sheet/bitable 为 csv 时必须提供 --sub-id")

    client = create_client()
    result = client.drive_export(
        args.token,
        args.doc_type,
        args.file_extension,
        sub_id=args.sub_id,
        output_path=args.output,
        max_attempts=args.max_attempts,
        poll_interval=args.poll_interval,
    )
    print_json(result)


if __name__ == "__main__":
    cli_run(main)
