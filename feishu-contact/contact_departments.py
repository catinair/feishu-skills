#!/usr/bin/env python3
"""
contact_departments.py -- 查询飞书部门架构

用法：
    python contact_departments.py --list
    python contact_departments.py --get 8a612b6c9184b118
    python contact_departments.py --members 8a612b6c9184b118
    python contact_departments.py --tree
    python contact_departments.py --all-members
    python contact_departments.py --all-members --output csv > members.csv

注意：
    --members 和 --all-members 优先使用 user_access_token（返回完整字段），
    token 过期时自动降级到 tenant_access_token（返回基础字段）。
"""

import argparse
import csv
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from feishu_common import create_client, cli_run, print_json


_fallback_warned = False


def _fetch_members(client, dept_id, dept_id_type="department_id"):
    """获取部门成员，user_access_token 优先，失败自动降级到 tenant_access_token"""
    global _fallback_warned
    try:
        members = client.contact_find_by_department(
            dept_id, department_id_type=dept_id_type, use_user_token=True,
        )
        return members, "user"
    except RuntimeError as e:
        err_msg = str(e)
        if "99991677" in err_msg or "401" in err_msg or "过期" in err_msg:
            if not _fallback_warned:
                print(f"  [提示] user_access_token 过期，已降级到 tenant_access_token", file=sys.stderr)
                _fallback_warned = True
            members = client.contact_find_by_department(
                dept_id, department_id_type=dept_id_type, use_user_token=False,
            )
            return members, "tenant"
        raise


def _format_member(m):
    """统一成员输出格式"""
    u = m if isinstance(m, dict) else {}
    status = u.get("status", {})
    if isinstance(status, dict):
        is_active = status.get("is_activated", False)
        is_resigned = status.get("is_resigned", False)
        status_str = "离职" if is_resigned else ("在职" if is_active else "未知")
    else:
        status_str = "未知"
    return {
        "user_id": u.get("user_id", ""),
        "open_id": u.get("open_id", ""),
        "name": u.get("name", ""),
        "en_name": u.get("en_name", ""),
        "email": u.get("email", ""),
        "employee_no": u.get("employee_no", ""),
        "job_title": u.get("job_title", ""),
        "department_ids": u.get("department_ids", []),
        "status": status_str,
    }


def main():
    parser = argparse.ArgumentParser(description="查询飞书部门架构")
    parser.add_argument("--list", action="store_true", help="列出所有部门")
    parser.add_argument("--get", metavar="DEPT_ID", help="获取单个部门详情")
    parser.add_argument("--members", metavar="DEPT_ID", help="查询部门成员")
    parser.add_argument("--all-members", action="store_true", help="拉取全部门成员（去重）")
    parser.add_argument("--tree", action="store_true", help="以树形结构展示部门层级")
    parser.add_argument("--output", choices=["json", "csv"], default="json", help="输出格式，默认 json")
    parser.add_argument("--department-id-type", default="department_id",
                        choices=["department_id", "open_department_id"],
                        help="部门 ID 类型，默认 department_id")
    parser.add_argument("--raw", action="store_true", help="输出完整原始 JSON")
    args = parser.parse_args()

    if not (args.list or args.get or args.members or args.tree or args.all_members):
        parser.error("请提供 --list、--get、--members、--tree 或 --all-members 之一")

    client = create_client()

    if args.list:
        depts = client.contact_list_departments(department_id_type=args.department_id_type)
        if args.raw:
            print_json({"departments": depts, "total": len(depts)})
            return
        results = []
        for d in depts:
            results.append({
                "department_id": d.get("department_id", ""),
                "open_department_id": d.get("open_department_id", ""),
                "name": d.get("name", ""),
                "member_count": d.get("member_count", 0),
                "leader_user_id": d.get("leader_user_id", ""),
                "parent_department_id": d.get("parent_department_id", ""),
            })
        print_json({"departments": results, "total": len(results)})

    elif args.get:
        data = client.contact_get_department(args.get, department_id_type=args.department_id_type)
        dept = data.get("department", data)
        if args.raw:
            print_json(data if "department" in data else {"department": dept})
            return
        print_json({
            "department_id": dept.get("department_id", ""),
            "open_department_id": dept.get("open_department_id", ""),
            "name": dept.get("name", ""),
            "i18n_name": dept.get("i18n_name", {}),
            "member_count": dept.get("member_count", 0),
            "leader_user_id": dept.get("leader_user_id", ""),
            "parent_department_id": dept.get("parent_department_id", ""),
            "order": dept.get("order", ""),
        })

    elif args.members:
        members, token_type = _fetch_members(client, args.members, args.department_id_type)
        if args.raw:
            print_json({"members": members, "total": len(members), "token_type": token_type})
            return
        results = [_format_member(m) for m in members]
        print_json({"members": results, "total": len(results), "token_type": token_type})

    elif args.all_members:
        depts = client.contact_list_departments(
            fetch_child=True, department_id_type=args.department_id_type,
        )
        seen = {}
        all_members = []
        for i, dept in enumerate(depts):
            dept_id = dept.get("department_id", "")
            dept_name = dept.get("name", "")
            print(f"[{i+1}/{len(depts)}] {dept_name} ...", file=sys.stderr, end=" ")
            try:
                members, _ = _fetch_members(client, dept_id, args.department_id_type)
                count = 0
                for m in members:
                    uid = m.get("user_id", "") if isinstance(m, dict) else ""
                    if uid and uid not in seen:
                        seen[uid] = True
                        all_members.append(_format_member(m))
                        count += 1
                print(f"{len(members)} 人 (新增 {count})", file=sys.stderr)
            except Exception as e:
                print(f"跳过: {e}", file=sys.stderr)

        print(f"\n共 {len(all_members)} 人（去重后）", file=sys.stderr)

        if args.output == "csv":
            output = io.StringIO()
            fields = ["name", "user_id", "open_id", "email", "employee_no", "job_title", "status"]
            writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(all_members)
            print(output.getvalue(), end="")
        else:
            print_json({"members": all_members, "total": len(all_members)})

    elif args.tree:
        depts = client.contact_list_departments(
            fetch_child=True, department_id_type=args.department_id_type,
        )
        dept_map = {}
        for d in depts:
            dept_map[d.get("department_id", "")] = d
            oid = d.get("open_department_id", "")
            if oid:
                dept_map[oid] = d

        def build_tree(parent_id, depth=0):
            children = []
            for d in depts:
                if d.get("parent_department_id") == parent_id:
                    children.append(d)
            for c in sorted(children, key=lambda x: x.get("order", "") or ""):
                prefix = "  " * depth + ("└─ " if depth > 0 else "")
                name = c.get("name", "")
                did = c.get("department_id", "")
                count = c.get("member_count", 0)
                print(f"{prefix}{name} (id={did}, members={count})")
                build_tree(c.get("department_id", ""), depth + 1)

        build_tree("0")


if __name__ == "__main__":
    cli_run(main)
