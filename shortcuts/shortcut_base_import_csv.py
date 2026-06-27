#!/usr/bin/env python3
"""
shortcut_base_import_csv.py -- 从 CSV 导入数据到多维表格

用法:
    python3 shortcuts/shortcut_base_import_csv.py --app base_token_or_url --table table_id --input data.csv

特性:
    - 自动匹配 CSV 列名与字段名（大小写不敏感、支持空格/下划线互换）
    - 智能类型转换（数字、日期、单选、多选、复选框等）
    - 批量创建，每批最多 500 条
    - 跳过不支持导入的字段类型（人员、附件等），输出警告

CSV 格式要求:
    - 第一行为列名（建议与字段名一致）
    - 日期列支持格式: 2024-01-15, 2024/01/15, 2024-01-15T10:30:00
    - 多选列用逗号分隔: "选项A, 选项B"
    - 复选框列: true/false, yes/no, 1/0
"""

import argparse
import csv
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from feishu_common import cli_run, confirm_action_or_exit, create_client, extract_base_info


def normalize_name(name):
    """规范化名称用于匹配：去空格、转小写、下划线空格互换"""
    n = name.strip().lower()
    n = n.replace("_", " ")
    return n


def parse_date(value):
    """尝试多种格式解析日期为毫秒时间戳"""
    value = str(value).strip()
    if not value:
        return None
    # 纯数字（已经是毫秒或秒级时间戳）
    if value.isdigit():
        n = int(value)
        if n > 1_000_000_000_000:  # 毫秒
            return n
        return n * 1000  # 秒 → 毫秒
    formats = [
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%Y%m%d",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(value, fmt)
            dt = dt.replace(tzinfo=timezone.utc)
            return int(dt.timestamp() * 1000)
        except ValueError:
            continue
    return None


def convert_value(value, field_type, field_name):
    """将 CSV 字符串转换为飞书字段值"""
    if value is None or str(value).strip() == "":
        return None

    s = str(value).strip()

    # 文本
    if field_type == 1:
        return s

    # 数字
    if field_type == 2:
        try:
            if "." in s:
                return float(s)
            return int(s)
        except ValueError:
            raise RuntimeError(f"字段 '{field_name}' 要求数字类型，但收到: {s}")

    # 单选
    if field_type == 3:
        return s

    # 多选 → 逗号分隔数组
    if field_type == 4:
        return [p.strip() for p in s.split(",") if p.strip()]

    # 日期
    if field_type == 5:
        ts = parse_date(s)
        if ts is None:
            raise RuntimeError(f"字段 '{field_name}' 要求日期类型，但无法解析: {s}")
        return ts

    # 复选框
    if field_type == 7:
        return s.lower() in ("true", "yes", "1", "y", "是")

    # 电话
    if field_type == 13:
        return s

    # 超链接 → 尝试解析 "text (link)" 格式
    if field_type == 15:
        m = re.match(r"^(.*?)\s*\((https?://[^)]+)\)\s*$", s)
        if m:
            return {"text": m.group(1).strip(), "link": m.group(2)}
        return {"text": s, "link": s}

    # 关联记录 → 逗号分隔的 record_id 数组
    if field_type in (18, 22):
        ids = [p.strip() for p in s.split(",") if p.strip()]
        return [{"id": rid} for rid in ids]

    # 地理位置
    if field_type == 23:
        return {"location": s, "location_type": "text"}

    # 群组
    if field_type == 24:
        ids = [p.strip() for p in s.split(",") if p.strip()]
        return [{"id": gid} for gid in ids]

    # 其他默认文本
    return s


def main():
    parser = argparse.ArgumentParser(description="从 CSV 导入数据到多维表格")
    parser.add_argument("--app", required=True, help="Base token 或 URL")
    parser.add_argument("--table", required=True, help="数据表 ID")
    parser.add_argument("--input", "-i", required=True, help="输入 CSV 文件路径")
    parser.add_argument("--encoding", default="utf-8-sig", help="CSV 编码（默认 utf-8-sig）")
    parser.add_argument("--skip-confirm", action="store_true", help="跳过确认（批量写操作）")
    parser.add_argument("--batch-size", type=int, default=500, help="每批创建条数（默认 500，最大 500）")
    args = parser.parse_args()

    batch_size = min(args.batch_size, 500)

    app_token, table_id = extract_base_info(args.app)
    if not table_id and args.table:
        table_id = args.table
    if not table_id:
        raise RuntimeError("缺少 --table 参数，且 URL 中未包含 table_id")

    client = create_client()

    # 读取 CSV
    input_path = Path(args.input)
    if not input_path.exists():
        raise RuntimeError(f"CSV 文件不存在: {args.input}")

    with open(input_path, "r", newline="", encoding=args.encoding) as f:
        reader = csv.DictReader(f)
        csv_columns = reader.fieldnames or []
        rows = list(reader)

    if not rows:
        print("CSV 文件没有数据行", file=sys.stderr)
        return

    # 获取字段列表
    fields_data = client.base_list_fields(app_token, table_id)
    fields = fields_data.get("items", [])
    field_map = {normalize_name(f["field_name"]): f for f in fields}

    # 建立 CSV 列 → 字段的映射
    col_to_field = {}
    skipped_cols = []
    for col in csv_columns:
        norm = normalize_name(col)
        if norm in field_map:
            col_to_field[col] = field_map[norm]
        else:
            skipped_cols.append(col)

    if not col_to_field:
        raise RuntimeError(
            f"CSV 列名与字段名无法匹配。CSV 列: {csv_columns}，"
            f"数据表字段: {[f['field_name'] for f in fields]}"
        )

    # 检查是否有不支持导入的字段类型
    unsupported_types = {11: "人员", 17: "附件", 20: "公式", 21: "查找引用"}
    warn_fields = []
    for col, field in col_to_field.items():
        ft = field.get("type", 1)
        if ft in unsupported_types:
            warn_fields.append(f"  - {col} ({unsupported_types[ft]}): 该类型不支持 CSV 导入，将跳过")

    # 确认信息
    print(f"准备从 {args.input} 导入 {len(rows)} 条记录到数据表 {table_id}", file=sys.stderr)
    print(f"匹配字段 ({len(col_to_field)}/{len(csv_columns)}): {', '.join(col_to_field.keys())}", file=sys.stderr)
    if skipped_cols:
        print(f"未匹配列 (跳过): {', '.join(skipped_cols)}", file=sys.stderr)
    if warn_fields:
        print("字段警告:", file=sys.stderr)
        for w in warn_fields:
            print(w, file=sys.stderr)

    confirm_action_or_exit("base_batch_create", "确认导入?", yes=args.skip_confirm)

    # 构建记录并批量创建
    records = []
    success = 0
    errors = []

    for idx, row in enumerate(rows, 1):
        fields_data = {}
        for col, field in col_to_field.items():
            ft = field.get("type", 1)
            if ft in unsupported_types:
                continue
            try:
                val = convert_value(row.get(col), ft, field["field_name"])
                if val is not None:
                    fields_data[field["field_name"]] = val
            except RuntimeError as e:
                errors.append(f"第 {idx} 行: {e}")
                break
        else:
            records.append({"fields": fields_data})

        if len(records) >= batch_size:
            try:
                result = client.base_batch_create_records(app_token, table_id, records)
                success += len(records)
                records = []
            except RuntimeError as e:
                errors.append(f"批量创建失败 (第 {idx - len(records) + 1}-{idx} 行): {e}")
                records = []

    # 最后一批
    if records:
        try:
            result = client.base_batch_create_records(app_token, table_id, records)
            success += len(records)
        except RuntimeError as e:
            errors.append(f"批量创建失败 (最后一批): {e}")

    print(f"导入完成: 成功 {success}/{len(rows)} 条")
    if errors:
        print(f"错误 ({len(errors)} 条):")
        for e in errors[:10]:
            print(f"  {e}")
        if len(errors) > 10:
            print(f"  ... 还有 {len(errors) - 10} 条错误")


if __name__ == "__main__":
    cli_run(main)
