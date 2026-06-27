#!/usr/bin/env python3
"""
sheet_export_csv.py -- 导出电子表格为 CSV

用法:
    # 导出默认 sheet 为 CSV
    python3 sheet_export_csv.py --token shtcnxxx --output ./sheet.csv

    # 导出指定 sheet 为 CSV
    python3 sheet_export_csv.py --token shtcnxxx --sheet-id 0edxxx --output ./sheet.csv

    # 从 URL 自动提取 token
    python3 sheet_export_csv.py --url "https://xxx.feishu.cn/sheets/shtcnxxx" --output ./sheet.csv

输出路径说明：
    --output 为必填参数，指定 CSV 文件的本地保存路径。
    建议使用绝对路径，避免文件散落在 skill 目录下。
    示例: python3 sheet_export_csv.py --token xxx --output ~/Downloads/sheet.csv
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from feishu_common import create_client, print_json, cli_run
import argparse


def extract_sheet_token(url_or_token):
    """从 URL 提取 spreadsheet token 或直接返回 token"""
    if url_or_token.startswith("http"):
        import re
        m = re.search(r"/sheets/([a-zA-Z0-9]+)", url_or_token)
        if m:
            return m.group(1)
    return url_or_token


def main():
    parser = argparse.ArgumentParser(description="导出电子表格为 CSV")
    parser.add_argument("--token", default=None, help="表格 token")
    parser.add_argument("--url", default=None, help="表格 URL（与 --token 二选一）")
    parser.add_argument("--sheet-id", default=None, help="Sheet ID（不填则导出默认 sheet）")
    parser.add_argument("--output", default=None, help="本地保存路径（默认使用表格名.csv）")
    args = parser.parse_args()

    token = args.token
    if args.url:
        token = extract_sheet_token(args.url)
    if not token:
        raise RuntimeError("请提供 --token 或 --url")

    client = create_client()

    # 如果不提供 sheet_id，获取默认 sheet
    sheet_id = args.sheet_id
    if not sheet_id:
        info = client.sheet_get_info(token)
        sheets = info.get("sheets", [])
        if not sheets:
            raise RuntimeError("无法获取表格的 sheet 列表")
        sheet_id = sheets[0].get("sheet_id")

    result = client.drive_export(token, "sheet", "csv", sub_id=sheet_id, output_path=args.output)
    print_json(result)


if __name__ == "__main__":
    cli_run(main)
