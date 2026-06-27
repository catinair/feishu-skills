#!/usr/bin/env python3
"""
shortcut_base_clone_table.py -- 克隆多维表格的表结构（字段+视图）到新表

用法:
    python3 shortcuts/shortcut_base_clone_table.py --app base_token_or_url --table table_id --name "新表名"
    python3 shortcuts/shortcut_base_clone_table.py --app base_token_or_url --table table_id --name "新表名" --target-app other_base_token

特性:
    - 复制所有字段定义（名称、类型、属性）
    - 复制所有视图（名称、类型）
    - 不复制数据记录
    - 支持克隆到同一个 Base 或其他 Base

注意:
    - 单选/多选字段的选项颜色会保留，但 option ID 会重新生成
    - 视图的高级配置（筛选、排序、分组等）需要 Base v3 权限，当前仅复制基础视图
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from feishu_common import cli_run, confirm_action_or_exit, create_client, print_json, extract_base_info


def main():
    parser = argparse.ArgumentParser(description="克隆表结构到新表")
    parser.add_argument("--app", required=True, help="源 Base token 或 URL")
    parser.add_argument("--table", required=True, help="源数据表 ID")
    parser.add_argument("--name", required=True, help="新表名称")
    parser.add_argument("--target-app", default=None, help="目标 Base token（默认同源 Base）")
    parser.add_argument("--yes", "-y", action="store_true", help="跳过确认")
    args = parser.parse_args()

    app_token, table_id = extract_base_info(args.app)
    if not table_id and args.table:
        table_id = args.table
    if not table_id:
        raise RuntimeError("缺少 --table 参数，且 URL 中未包含 table_id")

    target_app = args.target_app or app_token

    client = create_client()

    # 获取源表信息
    source_table = client.base_get_table(app_token, table_id)
    source_name = source_table.get("table", {}).get("name", table_id)

    # 获取字段列表
    fields_data = client.base_list_fields(app_token, table_id)
    source_fields = fields_data.get("items", [])

    # 获取视图列表
    views_data = client.base_list_views(app_token, table_id)
    source_views = views_data.get("items", [])

    # 确认
    confirm_action_or_exit(
        "base_create",
        f"将从表 '{source_name}' 克隆结构到新表 '{args.name}'\n"
        f"  - 字段数: {len(source_fields)}\n"
        f"  - 视图数: {len(source_views)}\n"
        f"  - 目标 Base: {target_app}\n"
        f"  - 不复制数据记录",
        yes=args.yes,
    )

    # 创建新表
    created_table = client.base_create_table(target_app, args.name)
    new_table_id = created_table.get("table_id") or created_table.get("table", {}).get("table_id")
    if not new_table_id:
        raise RuntimeError(f"创建表失败，未返回 table_id: {created_table}")

    def _clean_property(prop, field_type):
        """清理字段 property 中的源表特有 ID，避免创建失败"""
        if not isinstance(prop, dict):
            return prop
        prop = dict(prop)
        # 单选/多选字段：移除 option id（新表会重新生成）
        if field_type in (3, 4) and "options" in prop:
            prop["options"] = [
                {k: v for k, v in opt.items() if k != "id"}
                for opt in prop["options"]
                if isinstance(opt, dict)
            ]
        return prop

    # 复制字段
    created_fields = []
    field_errors = []
    for f in source_fields:
        try:
            result = client.base_create_field(
                target_app, new_table_id,
                field_name=f["field_name"],
                field_type=f["type"],
                property=_clean_property(f.get("property"), f["type"]),
                ui_type=f.get("ui_type")
            )
            created_fields.append({
                "source_field_id": f.get("field_id"),
                "field_name": f["field_name"],
                "result": result
            })
        except RuntimeError as e:
            field_errors.append({
                "field_name": f["field_name"],
                "error": str(e)
            })

    # 复制视图
    created_views = []
    view_errors = []
    for v in source_views:
        try:
            result = client.base_create_view(
                target_app, new_table_id,
                view_name=v.get("view_name", "视图"),
                view_type=v.get("view_type", "grid")
            )
            created_views.append({
                "source_view_id": v.get("view_id"),
                "view_name": v.get("view_name"),
                "result": result
            })
        except RuntimeError as e:
            view_errors.append({
                "view_name": v.get("view_name"),
                "error": str(e)
            })

    result = {
        "source": {"app_token": app_token, "table_id": table_id, "table_name": source_name},
        "target": {"app_token": target_app, "table_id": new_table_id, "table_name": args.name},
        "fields": {"total": len(source_fields), "created": len(created_fields), "errors": len(field_errors), "items": created_fields},
        "views": {"total": len(source_views), "created": len(created_views), "errors": len(view_errors), "items": created_views},
    }
    if field_errors:
        result["field_errors"] = field_errors
    if view_errors:
        result["view_errors"] = view_errors

    print_json(result)


if __name__ == "__main__":
    cli_run(main)
