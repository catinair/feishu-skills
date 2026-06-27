#!/usr/bin/env python3
"""
shortcut_base_export_csv.py -- 将多维表格数据导出为 CSV

用法:
    python3 shortcuts/shortcut_base_export_csv.py --app base_token_or_url --table table_id --output data.csv

输出路径说明：
    --output 指定 CSV 文件的本地保存路径。
    建议使用绝对路径，避免文件散落在 skill 目录下。
    示例: python3 shortcuts/shortcut_base_export_csv.py --app xxx --table yyy --output ~/Downloads/data.csv

特性:
    - 自动分页拉取全部记录
    - 智能字段值展平（人员取姓名、附件取文件名、多选逗号分隔等）
    - 日期字段自动转换为 ISO 8601 格式
"""

import argparse
import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from feishu_common import create_client, cli_run, extract_base_info


def flatten_value(value, field_type):
    """将飞书字段值展平为 CSV 友好的字符串"""
    if value is None or value == "":
        return ""

    # 文本、单选、数字、电话 → 直接字符串化
    if field_type in (1, 2, 3, 13):
        return str(value)

    # 多选 → 逗号分隔
    if field_type == 4:
        if isinstance(value, list):
            return ", ".join(str(v) for v in value)
        return str(value)

    # 日期 → 毫秒时间戳转 ISO 8601
    if field_type == 5:
        try:
            ts = int(value)
            dt = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
            return dt.strftime("%Y-%m-%dT%H:%M:%S")
        except (ValueError, TypeError):
            return str(value)

    # 复选框
    if field_type == 7:
        return "true" if value else "false"

    # 人员 → 取 name 逗号分隔
    if field_type == 11:
        if isinstance(value, list):
            names = []
            for item in value:
                if isinstance(item, dict):
                    name = item.get("name") or item.get("en_name") or item.get("id", "")
                    names.append(name)
                else:
                    names.append(str(item))
            return ", ".join(names)
        return str(value)

    # 超链接 → text (link)
    if field_type == 15:
        if isinstance(value, dict):
            text = value.get("text", "")
            link = value.get("link", "")
            return f"{text} ({link})" if link else text
        return str(value)

    # 附件 → 取 name 逗号分隔
    if field_type == 17:
        if isinstance(value, list):
            names = []
            for item in value:
                if isinstance(item, dict):
                    names.append(item.get("name", item.get("file_token", "")))
                else:
                    names.append(str(item))
            return ", ".join(names)
        return str(value)

    # 关联记录 / 双向关联
    if field_type in (18, 22):
        if isinstance(value, list):
            ids = []
            for item in value:
                if isinstance(item, dict):
                    rid = item.get("record_ids") or item.get("id") or ""
                    if isinstance(rid, list):
                        ids.extend(rid)
                    else:
                        ids.append(str(rid))
                else:
                    ids.append(str(item))
            return ", ".join(ids)
        return str(value)

    # 地理位置
    if field_type == 23:
        if isinstance(value, dict):
            return value.get("location", "")
        return str(value)

    # 群组
    if field_type == 24:
        if isinstance(value, list):
            ids = [item.get("id", str(item)) if isinstance(item, dict) else str(item) for item in value]
            return ", ".join(ids)
        return str(value)

    # 公式、查找引用、自动编号等 → 直接字符串化
    return str(value)


def main():
    parser = argparse.ArgumentParser(description="将多维表格数据导出为 CSV")
    parser.add_argument("--app", required=True, help="Base token 或 URL")
    parser.add_argument("--table", required=True, help="数据表 ID")
    parser.add_argument("--output", "-o", required=True, help="输出 CSV 文件路径")
    parser.add_argument("--encoding", default="utf-8-sig", help="CSV 编码（默认 utf-8-sig，Excel 兼容）")
    args = parser.parse_args()

    app_token, table_id = extract_base_info(args.app)
    if not table_id and args.table:
        table_id = args.table
    if not table_id:
        raise RuntimeError("缺少 --table 参数，且 URL 中未包含 table_id")

    client = create_client()

    # 获取字段列表
    fields_data = client.base_list_fields(app_token, table_id)
    fields = fields_data.get("items", [])
    if not fields:
        print("警告: 该数据表没有字段", file=sys.stderr)
        return

    # 建立字段名和类型映射
    field_names = [f["field_name"] for f in fields]
    field_type_map = {f["field_name"]: f.get("type", 1) for f in fields}

    # 查询所有记录
    records_data = client.base_query_records(app_token, table_id)
    records = records_data.get("records", [])
    if not records:
        print(f"警告: 该数据表没有记录，仅导出表头（{len(fields)} 个字段）", file=sys.stderr)

    # 写入 CSV
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    with open(output, "w", newline="", encoding=args.encoding) as f:
        writer = csv.writer(f)
        writer.writerow(field_names)

        for record in records:
            row = []
            for fname in field_names:
                raw_value = record.get("fields", {}).get(fname)
                flat = flatten_value(raw_value, field_type_map.get(fname, 1))
                row.append(flat)
            writer.writerow(row)

    print(f"导出完成: {output} ({len(records)} 条记录, {len(fields)} 个字段)")


if __name__ == "__main__":
    cli_run(main)
