#!/usr/bin/env python3
"""
setup_scopes.py -- 权限检测与批量开通

读取 scopes_batch_import.json 中的目标权限清单，对比当前 permissions.json 已开通的权限，
找出缺口，通过飞书 API 批量开通权限。

优先使用飞书 API 直接更新（免审权限即时生效），API 不可用时回退到 scope-apply 链接。

用法：
    python3 feishu-setup/setup_scopes.py
    python3 feishu-setup/setup_scopes.py --json
    python3 feishu-setup/setup_scopes.py --missing
    python3 feishu-setup/setup_scopes.py --apply    # 输出全量开通链接
    python3 feishu-setup/setup_scopes.py --minimal  # 仅 Bitable 基础设施 6 个免审权限
"""

import argparse
import json
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from feishu_common import print_json, cli_run, create_client
from feishu_common._config_loader import (
    load_credentials_data,
    load_permissions_config,
)

# 目标权限清单路径
SCOPES_BATCH_FILE = Path(__file__).parent / "scopes_batch_import.json"

# 飞书应用权限更新 API（优先尝试）
SCOPE_UPDATE_API = "/open-apis/security/v1/app_admin_scope/update"

# Bitable 基础设施创建所需的最小免审权限（Step 1.5 专用）
MINIMAL_BITABLE_SCOPES = [
    "bitable:app",
    "base:app:create",
    "base:table:create",
    "base:block:create",
    "base:record:create",
    "base:record:update",
]


def _load_target_scopes():
    """从 scopes_batch_import.json 读取目标权限清单。"""
    if not SCOPES_BATCH_FILE.exists():
        return {"tenant": [], "user": []}
    with open(SCOPES_BATCH_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("scopes", {"tenant": [], "user": []})


def _load_granted_scopes():
    """从 permissions.json 读取已开通的权限。"""
    data = load_permissions_config()
    if not data:
        return {"tenant": [], "user": []}
    return data.get("scopes", {"tenant": [], "user": []})


def _load_app_id():
    """读取 credentials.json 中的 appId。"""
    try:
        data, _ = load_credentials_data()
        return data.get("appId", "")
    except Exception:
        return ""


def _build_scope_apply_url(app_id, scopes):
    """生成飞书开放平台权限申请链接。"""
    base = (
        f"https://open.feishu.cn/page/scope-apply?clientID={urllib.parse.quote(app_id)}"
    )
    if scopes:
        base += f"&scopes={urllib.parse.quote(','.join(scopes))}"
    return base


def _update_scopes_via_api(client, scopes):
    """通过飞书 API 批量更新应用权限。

    使用 tenant token 调用 scope 更新接口。
    返回 (success, error_message)。
    """
    try:
        resp = client._request(
            "POST",
            SCOPE_UPDATE_API,
            body={"scopes": scopes},
            use_user_token=False,
        )
        code = resp.get("code", -1)
        if code == 0:
            return True, None
        return False, f"API 返回 code={code} msg={resp.get('msg', '')}"
    except Exception as e:
        return False, str(e)


def _build_report(target, granted, app_id, missing_only=False):
    """构建权限缺口报告。"""
    tenant_target = set(target.get("tenant", []))
    user_target = set(target.get("user", []))
    tenant_granted = set(granted.get("tenant", []))
    user_granted = set(granted.get("user", []))

    tenant_missing = sorted(tenant_target - tenant_granted)
    user_missing = sorted(user_target - user_granted)
    all_missing = sorted(set(tenant_missing + user_missing))

    report = {
        "app_id": app_id,
        "summary": {
            "tenant_target": len(tenant_target),
            "user_target": len(user_target),
            "tenant_granted": len(tenant_granted),
            "user_granted": len(user_granted),
            "tenant_missing": len(tenant_missing),
            "user_missing": len(user_missing),
            "total_missing": len(all_missing),
            "all_ready": len(tenant_missing) == 0 and len(user_missing) == 0,
        },
        "missing": {
            "tenant": tenant_missing,
            "user": user_missing,
            "all": all_missing,
        },
    }

    if all_missing:
        report["apply_url"] = _build_scope_apply_url(app_id, all_missing)

    if missing_only and not report["summary"]["all_ready"]:
        report["summary"]["tenant_target"] = len(tenant_missing)
        report["summary"]["user_target"] = len(user_missing)
        report["summary"]["tenant_granted"] = 0
        report["summary"]["user_granted"] = 0

    return report


def _try_auto_update(client, report):
    """尝试通过 API 自动更新权限，更新 report 中的结果。"""
    if report["summary"]["all_ready"]:
        return

    all_missing = report["missing"]["all"]
    print(f"正在通过 API 批量开通 {len(all_missing)} 项权限...", file=sys.stderr)

    success, error = _update_scopes_via_api(client, all_missing)
    report["api_update"] = {
        "attempted": True,
        "success": success,
        "error": error,
    }

    if success:
        report["api_update"]["note"] = (
            "权限已通过 API 更新。免审权限即时生效，需审批的权限已提交申请。"
        )
        print("权限更新成功。", file=sys.stderr)
    else:
        report["api_update"]["note"] = (
            f"API 更新失败: {error}。请使用下方的 apply_url 链接手动开通。"
        )
        print(f"API 更新失败: {error}", file=sys.stderr)


def _human_report(report):
    """生成人类可读的文本报告。"""
    lines = []
    s = report["summary"]

    lines.append("=" * 60)
    lines.append("飞书 Skills 权限缺口检测")
    lines.append("=" * 60)
    if report["app_id"]:
        lines.append(f"应用 ID: {report['app_id']}")
    lines.append("")
    lines.append(
        f"目标权限: tenant={s['tenant_target']} 项, user={s['user_target']} 项"
    )
    lines.append(
        f"已开通:   tenant={s['tenant_granted']} 项, user={s['user_granted']} 项"
    )
    lines.append(
        f"缺 口:   tenant={s['tenant_missing']} 项, user={s['user_missing']} 项"
    )
    lines.append("")

    if s["all_ready"]:
        lines.append("所有权限已就绪，无需操作。")
        return "\n".join(lines)

    api = report.get("api_update", {})
    if api.get("success"):
        lines.append(f"API 更新: {api['note']}")
        lines.append("")
    elif api.get("attempted"):
        lines.append(f"API 更新: {api['note']}")
        lines.append("")

    missing = report["missing"]["all"]
    if missing:
        lines.append("缺失权限列表:")
        for scope in missing:
            lines.append(f"  - {scope}")
        lines.append(f"  共 {len(missing)} 项")
        lines.append("")
        if "apply_url" in report:
            lines.append(f"开通链接: {report['apply_url']}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="检测飞书应用权限缺口，批量开通权限")
    parser.add_argument(
        "--json",
        action="store_true",
        help="以 JSON 格式输出",
    )
    parser.add_argument(
        "--missing",
        action="store_true",
        help="仅显示有缺口的权限",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="输出开通链接（优先尝试 API 自动更新）",
    )
    parser.add_argument(
        "--minimal",
        action="store_true",
        help="仅输出 Bitable 基础设施所需的 6 个免审权限链接（Step 1.5 专用）",
    )
    parser.add_argument(
        "--no-api",
        action="store_true",
        help="跳过 API 自动更新，仅输出 scope-apply 链接",
    )
    args = parser.parse_args()

    app_id = _load_app_id()
    if not app_id:
        msg = "未找到 appId，请先完成 Step 1（创建/绑定飞书应用）"
        if args.json or args.minimal:
            print_json({"ok": False, "error": msg})
        else:
            print(msg, file=sys.stderr)
        sys.exit(1)

    # --minimal：只输出 Bitable 基础设施所需的 6 个免审权限链接
    if args.minimal:
        print(_build_scope_apply_url(app_id, MINIMAL_BITABLE_SCOPES))
        return

    target = _load_target_scopes()
    granted = _load_granted_scopes()

    report = _build_report(target, granted, app_id, missing_only=args.missing)

    # 尝试 API 自动更新
    if not report["summary"]["all_ready"] and not args.no_api:
        try:
            client = create_client()
            _try_auto_update(client, report)
        except Exception as e:
            report["api_update"] = {
                "attempted": True,
                "success": False,
                "error": str(e),
                "note": f"无法创建 API 客户端: {e}。请使用下方的 apply_url 链接。",
            }
            print(f"API 更新跳过（无法创建客户端）: {e}", file=sys.stderr)

    if args.apply:
        if report["summary"]["all_ready"]:
            print("所有权限已就绪，无需申请。")
            return
        api = report.get("api_update", {})
        if api.get("success"):
            print("权限已通过 API 更新。")
            return
        if "apply_url" in report:
            print(report["apply_url"])
        return

    if args.json:
        print_json(report)
    else:
        print(_human_report(report))


if __name__ == "__main__":
    cli_run(main)
