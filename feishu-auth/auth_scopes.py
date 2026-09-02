#!/usr/bin/env python3
"""auth_scopes.py -- 查看应用已开通权限与项目能力域的匹配情况。

用法：
    python3 feishu-auth/auth_scopes.py
    python3 feishu-auth/auth_scopes.py --domain im
    python3 feishu-auth/auth_scopes.py --missing
    python3 feishu-auth/auth_scopes.py --json

说明：
    - 读取 config/permissions.json 中已同步的 tenant/user scopes
    - 对照 feishu_common/_endpoint_registry.py 中的能力声明
    - 输出各能力域的权限就绪状态、已开通 scope、缺失 scope
    - 本脚本只"查看"和"诊断"，不会申请或修改飞书开放平台权限
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))
from feishu_common import print_json, cli_run
from feishu_common._endpoint_registry import ENDPOINT_REGISTRY, APP_ONLY
from feishu_common._config_loader import (
    load_credentials_data,
    load_default_identity,
    load_permissions_config,
)


def _guess_domain(method_name):
    """根据端点名称猜测所属能力域。

    端点名有两种常见模式：
      - 能力域前缀 + 动作：im_create_chat, calendar_list_events
      - 动作 + 能力域后缀：copy_file, upload_file, list_files
    因此不能只看前缀，需要综合关键词匹配。
    """
    name = method_name.lower()

    # 前缀匹配（最可靠）
    prefix_map = [
        ("im_", "消息与群聊"),
        ("contact_", "通讯录"),
        ("calendar_", "日历"),
        ("task_", "任务"),
        ("sheet_", "电子表格"),
        ("base_", "多维表格"),
        ("bitable_", "多维表格"),
        ("wiki_", "知识库"),
        ("minutes_", "妙记"),
        ("perm_", "权限管理"),
        ("slides_", "幻灯片"),
        ("approval_", "审批"),
        ("application_", "应用管理"),
        ("event_", "事件订阅"),
        ("vc_", "视频会议"),
        ("document_", "云文档"),
        ("drive_", "云空间"),
    ]
    for prefix, domain in prefix_map:
        if name.startswith(prefix):
            return domain

    # 关键词匹配（兜底）
    if "chat" in name or "message" in name or name in {"upload_image"}:
        return "消息与群聊"
    if "file" in name or "folder" in name:
        return "云空间"
    if "document" in name or "markdown" in name or "blocks" in name:
        return "云文档"
    if "sheet" in name:
        return "电子表格"
    if "board" in name:
        return "画板"

    return "其他"


def _load_permissions():
    """读取 permissions.json（含平台 skill-root fallback）。"""
    data = load_permissions_config()
    return data or {"scopes": {"tenant": [], "user": []}, "admin_approval_scopes": []}


def _load_app_id():
    """读取 credentials.json 中的 appId。"""
    try:
        data, _ = load_credentials_data()
        return data.get("appId", "")
    except Exception:
        return ""


def _collect_domain_scopes():
    """遍历 endpoint registry，按能力域聚合所需的 tenant/user scopes。"""
    domains = {}
    for method, config in ENDPOINT_REGISTRY.items():
        identity = config.get("identity", APP_ONLY)
        scopes = config.get("scopes", {})
        tenant_scopes = set(scopes.get("tenant", []))
        user_scopes = set(scopes.get("user", []))

        domain = _guess_domain(method)
        entry = domains.setdefault(
            domain,
            {
                "methods": [],
                "tenant_required": set(),
                "user_required": set(),
                "identity": set(),
            },
        )
        entry["methods"].append(method)
        entry["tenant_required"].update(tenant_scopes)
        entry["user_required"].update(user_scopes)
        entry["identity"].add(identity)
    return domains


def _build_report(permissions, domains, full_mode=False):
    """构建按能力域分组的权限诊断报告。

    Args:
        permissions: 从 permissions.json 加载的权限数据
        domains: 从 ENDPOINT_REGISTRY 聚合的能力域信息
        full_mode: 若为 True，BOTH 端点要求 tenant + user 同时满足；
                   若为 False（默认），根据 default_identity 判断：
                   - user 默认时，BOTH 端点只需 user 满足
                   - tenant 默认时，BOTH 端点只需 tenant 满足
    """
    tenant_granted = set(permissions.get("scopes", {}).get("tenant", []))
    user_granted = set(permissions.get("scopes", {}).get("user", []))
    default_identity = load_default_identity() if not full_mode else None

    report = {
        "app_id": _load_app_id(),
        "summary": {
            "tenant_scopes": len(tenant_granted),
            "user_scopes": len(user_granted),
            "domains_ready": 0,
            "domains_total": len(domains),
        },
        "domains": {},
    }

    for domain, info in sorted(domains.items()):
        tenant_required = info["tenant_required"]
        user_required = info["user_required"]
        identities = info["identity"]

        tenant_missing = sorted(tenant_required - tenant_granted) if tenant_required else []
        user_missing = sorted(user_required - user_granted) if user_required else []

        # 判断该域是否涉及 user 身份调用（BOTH 或 USER_ONLY）
        supports_user = bool(
            identities & {"user_only", "both"} and user_required
        )
        # 判断该域是否涉及 tenant 身份调用（BOTH 或 APP_ONLY）
        supports_tenant = bool(
            identities & {"app_only", "both"} and tenant_required
        )

        if full_mode:
            # 完整模式：所有支持的权限都必须满足
            ready = not tenant_missing
            if supports_user:
                ready = ready and not user_missing
        else:
            # 根据默认身份判断 BOTH 端点
            if "both" in identities:
                if default_identity == "user":
                    # 默认 user 身份：只需 user scope 满足
                    ready = not user_missing
                elif default_identity == "tenant":
                    # 默认 tenant 身份：只需 tenant scope 满足
                    ready = not tenant_missing
                else:
                    # 兜底：双方都要满足（与旧行为一致）
                    ready = not tenant_missing and not user_missing
            elif supports_user and not supports_tenant:
                # USER_ONLY：必须 user 满足
                ready = not user_missing
            elif supports_tenant and not supports_user:
                # APP_ONLY：必须 tenant 满足
                ready = not tenant_missing
            else:
                # 混合或空：双方都要满足
                ready = not tenant_missing and not user_missing

        report["domains"][domain] = {
            "ready": ready,
            "identities": sorted(identities),
            "methods_count": len(info["methods"]),
            "tenant": {
                "required": sorted(tenant_required),
                "granted": sorted(tenant_required & tenant_granted),
                "missing": tenant_missing,
            },
            "user": {
                "required": sorted(user_required),
                "granted": sorted(user_required & user_granted),
                "missing": user_missing,
            },
        }
        if ready:
            report["summary"]["domains_ready"] += 1

    return report


def _filter_missing(report):
    """只保留有缺失权限的域。"""
    missing_domains = {}
    for domain, info in report["domains"].items():
        if info["tenant"]["missing"] or info["user"]["missing"]:
            missing_domains[domain] = info
    report["domains"] = missing_domains
    report["summary"]["domains_ready"] = report["summary"]["domains_total"] - len(
        missing_domains
    )
    return report


# 域别名：支持中英文/缩写输入
_DOMAIN_ALIASES = {
    "im": "消息与群聊",
    "chat": "消息与群聊",
    "message": "消息与群聊",
    "contact": "通讯录",
    "calendar": "日历",
    "task": "任务",
    "doc": "云文档",
    "docx": "云文档",
    "document": "云文档",
    "drive": "云空间",
    "file": "云空间",
    "sheets": "电子表格",
    "sheet": "电子表格",
    "base": "多维表格",
    "bitable": "多维表格",
    "wiki": "知识库",
    "minutes": "妙记",
    "perm": "权限管理",
    "permission": "权限管理",
    "slides": "幻灯片",
    "approval": "审批",
    "application": "应用管理",
    "event": "事件订阅",
    "vc": "视频会议",
    "board": "画板",
    "other": "其他",
}


def _resolve_domain_input(domain_input, available_domains):
    """把用户输入的域别名解析为内部使用的域名称。"""
    domain_input = domain_input.strip()
    if domain_input in available_domains:
        return domain_input
    normalized = _DOMAIN_ALIASES.get(domain_input.lower())
    if normalized and normalized in available_domains:
        return normalized
    raise RuntimeError(f"未知能力域: {domain_input}。可用域: {sorted(available_domains)}")


def _filter_domain(report, domain):
    """只保留指定能力域。"""
    available = set(report["domains"].keys())
    resolved = _resolve_domain_input(domain, available)
    report["domains"] = {resolved: report["domains"][resolved]}
    report["summary"]["domains_total"] = 1
    report["summary"]["domains_ready"] = 1 if report["domains"][resolved]["ready"] else 0
    return report


def _human_report(report):
    """生成人类可读的文本报告。"""
    lines = []
    lines.append("=" * 60)
    lines.append("飞书 Skills 权限诊断")
    lines.append("=" * 60)
    if report["app_id"]:
        lines.append(f"应用 ID: {report['app_id']}")
    lines.append(
        f"已开通权限: tenant={report['summary']['tenant_scopes']} 项, "
        f"user={report['summary']['user_scopes']} 项"
    )
    lines.append(
        f"能力域就绪: {report['summary']['domains_ready']}/"
        f"{report['summary']['domains_total']}"
    )
    lines.append("")

    for domain, info in sorted(report["domains"].items()):
        status = "✅ 就绪" if info["ready"] else "❌ 未就绪"
        lines.append(f"{status} {domain}（{info['methods_count']} 个接口）")

        tenant_missing = info["tenant"]["missing"]
        user_missing = info["user"]["missing"]

        if tenant_missing:
            lines.append(f"   缺少 tenant scope: {', '.join(tenant_missing)}")
        if user_missing:
            lines.append(f"   缺少 user scope: {', '.join(user_missing)}")
        if info["ready"]:
            lines.append("   权限已满足")
        lines.append("")

    if report["summary"]["domains_ready"] < report["summary"]["domains_total"]:
        lines.append("提示: 如需使用未就绪的域，请去飞书开放平台 → 权限管理")
        lines.append("      开通对应 scope 后，重新运行 auth_get_user_token.py 授权。")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="查看应用已开通权限与能力域匹配情况")
    parser.add_argument(
        "--domain",
        help="只查看指定能力域（如 im、drive、base）",
    )
    parser.add_argument(
        "--missing",
        action="store_true",
        help="只显示有缺失权限的域",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="以 JSON 格式输出",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="完整视图：BOTH 端点要求 tenant + user 同时满足（默认按 default_identity 判断）",
    )
    args = parser.parse_args()

    permissions = _load_permissions()
    domains = _collect_domain_scopes()
    report = _build_report(permissions, domains, full_mode=args.full)

    if args.missing:
        report = _filter_missing(report)
    if args.domain:
        report = _filter_domain(report, args.domain)

    if args.json:
        print_json(report)
    else:
        print(_human_report(report))


if __name__ == "__main__":
    cli_run(main)
