#!/usr/bin/env python3
"""
shortcut_base_sync_csv.py -- 将本地 CSV 增量同步到多维表格

核心逻辑：比对 CSV 与 Base 现有记录，仅导入差异（新增/更新）。

用法:
    # 仅创建新增记录（最安全，默认行为）
    python3 shortcuts/shortcut_base_sync_csv.py --app base_token --table table_id --input data.csv --key "订单号"

    # 同时更新已有记录
    python3 shortcuts/shortcut_base_sync_csv.py --app base_token --table table_id --input data.csv --key "订单号" --update

    # 同时删除 Base 中 CSV 没有的行（危险，需 --yes 确认）
    python3 shortcuts/shortcut_base_sync_csv.py --app base_token --table table_id --input data.csv --key "订单号" --update --delete --yes

    # 多字段联合主键
    python3 shortcuts/shortcut_base_sync_csv.py --app base_token --table table_id --input data.csv --key "姓名,手机号"

特性:
    - CSV 列名自动匹配 Base 字段名（大小写不敏感、空格/下划线互换）
    - 智能类型转换（复用 import_csv 逻辑）
    - 按主键比对，精确识别新增/更新/删除/无变化
    - 批量操作（创建每批 500，更新每批 500）
    - 默认仅新增，更新和删除需显式开启
"""

import argparse
import csv
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from feishu_common import cli_run, confirm_action_or_exit, create_client, extract_base_info


# ── 类型转换（复用 import_csv 逻辑）──

def normalize_name(name):
    n = name.strip().lower()
    n = n.replace("_", " ")
    return n


def parse_date(value):
    value = str(value).strip()
    if not value:
        return None
    if value.isdigit():
        n = int(value)
        return n if n > 1_000_000_000_000 else n * 1000
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S",
                "%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"):
        try:
            dt = datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
            return int(dt.timestamp() * 1000)
        except ValueError:
            continue
    return None


def convert_value(value, field_type, field_name):
    if value is None or str(value).strip() == "":
        return None
    s = str(value).strip()

    if field_type == 1:
        return s
    if field_type == 2:
        try:
            return float(s) if "." in s else int(s)
        except ValueError:
            raise RuntimeError(f"字段 '{field_name}' 要求数字，收到: {s}")
    if field_type == 3:
        return s
    if field_type == 4:
        return [p.strip() for p in s.split(",") if p.strip()]
    if field_type == 5:
        ts = parse_date(s)
        if ts is None:
            raise RuntimeError(f"字段 '{field_name}' 要求日期，无法解析: {s}")
        return ts
    if field_type == 7:
        return s.lower() in ("true", "yes", "1", "y", "是")
    if field_type == 13:
        return s
    if field_type == 15:
        m = re.match(r"^(.*?)\s*\((https?://[^)]+)\)\s*$", s)
        return {"text": m.group(1).strip(), "link": m.group(2)} if m else {"text": s, "link": s}
    if field_type in (18, 22):
        return [{"id": p.strip()} for p in s.split(",") if p.strip()]
    if field_type == 23:
        return {"location": s, "location_type": "text"}
    if field_type == 24:
        return [{"id": p.strip()} for p in s.split(",") if p.strip()]
    return s


# ── 比对逻辑 ──

def build_key(row, key_cols, col_to_field):
    """根据主键列构建唯一标识字符串"""
    parts = []
    for col in key_cols:
        field_name = col_to_field.get(col, col)
        parts.append(str(row.get(col, "")).strip())
    return "\x00".join(parts)


def build_record_key(record_fields, key_field_names):
    """根据记录字段和主键字段名构建唯一标识字符串"""
    parts = []
    for fn in key_field_names:
        v = record_fields.get(fn, "")
        if isinstance(v, list):
            v = ", ".join(str(i) if not isinstance(i, dict) else str(i.get("name", i.get("id", ""))) for i in v)
        elif isinstance(v, dict):
            v = str(v.get("text", v.get("location", str(v))))
        parts.append(str(v).strip())
    return "\x00".join(parts)


def fields_equal(csv_val, base_val, field_type):
    """判断 CSV 值和 Base 值是否相等（考虑类型差异）"""
    if csv_val is None and (base_val is None or base_val == "" or base_val == []):
        return True
    if csv_val is None or base_val is None:
        return False

    # 统一为字符串比较
    def normalize(v):
        if isinstance(v, list):
            return [str(i).strip() for i in v]
        if isinstance(v, dict):
            return str(v)
        return str(v).strip()

    return normalize(csv_val) == normalize(base_val)


def main():
    parser = argparse.ArgumentParser(description="将本地 CSV 增量同步到多维表格")
    parser.add_argument("--app", required=True, help="Base token 或 URL")
    parser.add_argument("--table", required=True, help="数据表 ID")
    parser.add_argument("--input", "-i", required=True, help="本地 CSV 文件路径")
    parser.add_argument("--key", required=True, help="主键字段（CSV 列名），多字段用逗号分隔，如 '订单号' 或 '姓名,手机号'")
    parser.add_argument("--update", action="store_true", help="同时更新 Base 中已有但值不同的记录")
    parser.add_argument("--delete", action="store_true", help="删除 Base 中 CSV 没有的行（危险）")
    parser.add_argument("--encoding", default="utf-8-sig", help="CSV 编码（默认 utf-8-sig）")
    parser.add_argument("--batch-size", type=int, default=500, help="每批操作条数（默认 500）")
    parser.add_argument("--yes", "-y", action="store_true", help="跳过确认")
    args = parser.parse_args()

    batch_size = min(args.batch_size, 500)

    app_token, table_id = extract_base_info(args.app)
    if not table_id and args.table:
        table_id = args.table
    if not table_id:
        raise RuntimeError("缺少 --table 参数，且 URL 中未包含 table_id")

    key_cols = [k.strip() for k in args.key.split(",") if k.strip()]
    if not key_cols:
        raise RuntimeError("--key 不能为空")

    client = create_client()

    # ── 读取 CSV ──
    input_path = Path(args.input)
    if not input_path.exists():
        raise RuntimeError(f"CSV 文件不存在: {args.input}")

    with open(input_path, "r", newline="", encoding=args.encoding) as f:
        reader = csv.DictReader(f)
        csv_columns = reader.fieldnames or []
        csv_rows = list(reader)

    if not csv_rows:
        print("CSV 文件没有数据行", file=sys.stderr)
        return

    # ── 获取 Base 字段和记录 ──
    fields_data = client.base_list_fields(app_token, table_id)
    base_fields = fields_data.get("items", [])
    field_type_map = {f["field_name"]: f.get("type", 1) for f in base_fields}
    field_map_norm = {normalize_name(f["field_name"]): f for f in base_fields}

    # CSV 列 → Base 字段映射
    col_to_field = {}
    skipped_cols = []
    for col in csv_columns:
        norm = normalize_name(col)
        if norm in field_map_norm:
            col_to_field[col] = field_map_norm[norm]["field_name"]
        else:
            skipped_cols.append(col)

    # 检查主键是否都能匹配
    key_field_names = []
    for col in key_cols:
        if col not in col_to_field:
            raise RuntimeError(f"主键列 '{col}' 无法匹配到 Base 字段。CSV 列: {csv_columns}, Base 字段: {[f['field_name'] for f in base_fields]}")
        key_field_names.append(col_to_field[col])

    # 获取现有记录
    records_data = client.base_query_records(app_token, table_id)
    base_records = records_data.get("records", [])

    # 建立 Base 记录索引（按主键）
    base_index = {}
    for r in base_records:
        k = build_record_key(r.get("fields", {}), key_field_names)
        base_index[k] = r

    # ── 比对 ──
    unsupported_types = {11: "人员", 17: "附件", 20: "公式", 21: "查找引用"}

    to_create = []
    to_update = []
    unchanged = 0
    key_errors = []

    for idx, row in enumerate(csv_rows, 1):
        row_key = build_key(row, key_cols, col_to_field)
        if not any(row.get(c, "").strip() for c in key_cols):
            key_errors.append(f"第 {idx} 行: 主键字段为空，已跳过")
            continue

        # 构建字段值
        row_fields = {}
        for col, field_name in col_to_field.items():
            ft = field_type_map.get(field_name, 1)
            if ft in unsupported_types:
                continue
            try:
                val = convert_value(row.get(col), ft, field_name)
                if val is not None:
                    row_fields[field_name] = val
            except RuntimeError as e:
                key_errors.append(f"第 {idx} 行: {e}")
                break
        else:
            if row_key not in base_index:
                to_create.append({"fields": row_fields})
            else:
                if not args.update:
                    unchanged += 1
                    continue
                # 检查是否有变化
                base_fields_data = base_index[row_key].get("fields", {})
                changed = False
                for fn, new_val in row_fields.items():
                    if not fields_equal(new_val, base_fields_data.get(fn), field_type_map.get(fn, 1)):
                        changed = True
                        break
                if changed:
                    to_update.append({
                        "record_id": base_index[row_key]["record_id"],
                        "fields": row_fields
                    })
                else:
                    unchanged += 1

    # 删除：Base 中有但 CSV 中没有
    to_delete = []
    if args.delete:
        csv_keys = {build_key(row, key_cols, col_to_field) for row in csv_rows}
        for k, r in base_index.items():
            if k not in csv_keys:
                to_delete.append(r["record_id"])

    # ── 报告 ──
    print(f"比对结果: CSV {len(csv_rows)} 行 vs Base {len(base_records)} 条", file=sys.stderr)
    print(f"  新增: {len(to_create)}", file=sys.stderr)
    print(f"  更新: {len(to_update)}", file=sys.stderr)
    print(f"  无变化: {unchanged}", file=sys.stderr)
    if args.delete:
        print(f"  待删除: {len(to_delete)}", file=sys.stderr)
    if key_errors:
        print(f"  错误/跳过: {len(key_errors)}", file=sys.stderr)
        for e in key_errors[:5]:
            print(f"    {e}", file=sys.stderr)
        if len(key_errors) > 5:
            print(f"    ... 还有 {len(key_errors) - 5} 条", file=sys.stderr)
    if skipped_cols:
        print(f"  未匹配列: {', '.join(skipped_cols)}", file=sys.stderr)

    if not to_create and not to_update and not to_delete:
        print("无需同步。", file=sys.stderr)
        return

    # ── 确认 ──
    actions = []
    if to_create:
        actions.append(f"创建 {len(to_create)} 条")
    if to_update:
        actions.append(f"更新 {len(to_update)} 条")
    if to_delete:
        actions.append(f"删除 {len(to_delete)} 条")
    confirm_action_or_exit("base_batch_create", f"确认执行: {' / '.join(actions)}?", yes=args.yes)

    # ── 执行 ──
    created = 0
    updated = 0
    deleted = 0
    errors = []

    # 批量创建
    for i in range(0, len(to_create), batch_size):
        batch = to_create[i:i + batch_size]
        try:
            client.base_batch_create_records(app_token, table_id, batch)
            created += len(batch)
        except RuntimeError as e:
            errors.append(f"创建失败 ({i + 1}-{i + len(batch)}): {e}")

    # 批量更新
    for i in range(0, len(to_update), batch_size):
        batch = to_update[i:i + batch_size]
        try:
            client.base_batch_update_records(app_token, table_id, batch)
            updated += len(batch)
        except RuntimeError as e:
            errors.append(f"更新失败 ({i + 1}-{i + len(batch)}): {e}")

    # 批量删除
    if to_delete:
        for i in range(0, len(to_delete), batch_size):
            batch = to_delete[i:i + batch_size]
            try:
                client.base_batch_delete_records(app_token, table_id, batch)
                deleted += len(batch)
            except RuntimeError as e:
                errors.append(f"删除失败 ({i + 1}-{i + len(batch)}): {e}")

    # ── 结果 ──
    print(f"同步完成: 创建 {created} / 更新 {updated} / 删除 {deleted}")
    if errors:
        print(f"错误 ({len(errors)}):")
        for e in errors[:10]:
            print(f"  {e}")
        if len(errors) > 10:
            print(f"  ... 还有 {len(errors) - 10} 条")


if __name__ == "__main__":
    cli_run(main)
