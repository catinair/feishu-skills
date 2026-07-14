#!/usr/bin/env python3
"""
setup_check.py -- 飞书 Skills 环境配置检测

检测当前项目配置完整性，输出 JSON 状态报告。
供 setup SKILL.md 引导流程调用，判断哪些步骤已完成、哪些需要引导。

用法：
    python3 feishu-setup/setup_check.py
    python3 feishu-setup/setup_check.py --json    # 纯 JSON 输出
"""

import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from feishu_common import write_default_risk_policy, load_default_identity
from feishu_common._config_loader import (
    resolve_config_path,
    get_config_dir,
    get_config_context,
    load_credentials_data,
    get_runtime_config_dir,
)
from feishu_common._endpoint_registry import ENDPOINT_REGISTRY, ADMIN_APPROVAL_SCOPES

# 核心业务需要的最低 user scopes
CORE_USER_SCOPES = {
    "offline_access",           # refresh_token 必需
    "auth:user.id:read",        # 用户身份基础
    "im:message",               # 发送消息
    "contact:user.base:readonly",  # 通讯录查询
}

# 推荐的完整 user scopes（用于评估配置丰富度）
RECOMMENDED_USER_SCOPES = CORE_USER_SCOPES | {
    # IM
    "im:chat",
    # 通讯录
    "contact:user:search",
    "contact:department.base:readonly",
    # 文档
    "docx:document",
    "docx:document:readonly",
    "docx:document.block:convert",
    "docs:document.comment:read",
    "docs:document.comment:create",
    # 云空间（免审）
    "drive:drive.search:readonly",
    "drive:drive.metadata:readonly",
    "drive:drive:version",
    "drive:drive:version:readonly",
    "drive:file:upload",
    "space:folder:create",
    # 以下需管理员审批，不纳入默认推荐：
    # "drive:drive:readonly",  # 查看、评论和下载云空间中所有文件
    # "drive:file",            # 上传、下载文件到云空间
    # 表格
    "sheets:spreadsheet",
    "sheets:spreadsheet:create",
    "sheets:spreadsheet.meta:read",
    # 多维表格
    "bitable:app",
    "base:block:create",
    "base:block:update",
    "base:block:delete",
    # 知识库
    "wiki:wiki:readonly",
    "wiki:wiki",
    # 日程
    "calendar:calendar.event:read",
    "calendar:calendar.event:create",
    "calendar:calendar.event:delete",
    "calendar:calendar.free_busy:read",
    # 任务
    "task:task:read",
    "task:task:write",
    "task:comment:read",
    "task:comment:write",
    # 妙记
    "minutes:minutes.artifacts:read",
    "minutes:minutes.basic:read",
    # 权限管理（免审）
    "docs:permission.member:readonly",
    "docs:permission.member:create",
    # 以下需管理员审批，不纳入默认推荐：
    # "docs:permission.member",  # 查看、新增、更新、删除云文档协作者
    # 画板
    "board:whiteboard:node:read",
}


def check_python():
    """Python 版本 >= 3.9"""
    v = sys.version_info
    ok = v >= (3, 9)
    return {
        "python_ready": ok,
        "python_version": f"{v.major}.{v.minor}.{v.micro}",
        "python_detail": "OK" if ok else f"需要 Python >= 3.9，当前 {v.major}.{v.minor}.{v.micro}",
    }


def check_credentials():
    """credentials.json 存在且有 appId/appSecret"""
    path = resolve_config_path("credentials.json")
    result = {"credentials_ready": False, "credentials_valid": False}

    if not path.exists():
        result["detail"] = f"文件不存在: {path}"
        return result

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        result["detail"] = f"文件解析失败: {e}"
        return result

    app_id = data.get("appId", "")
    app_secret = data.get("appSecret", "")
    result["credentials_ready"] = bool(app_id and app_secret)

    if not result["credentials_ready"]:
        result["credentials_detail"] = "缺少 appId 或 appSecret"
        return result

    for key in ("appId", "appSecret"):
        val = data.get(key, "")
        if val in ("REDACTED", "xxx"):
            result["credentials_detail"] = (
                f"{key} 仍为占位符 '{val}'，请填入真实凭证。"
                f"获取方式：飞书开放平台 → 应用详情 → 凭证与基础信息"
            )
            return result

    result["credentials_valid"] = True
    result["app_id_prefix"] = app_id[:10] + "..." if len(app_id) > 10 else app_id
    result["brand"] = data.get("brand", "feishu")
    result["credentials_detail"] = "OK"
    return result


def check_settings():
    """settings.json 存在且配置有效。

    tenant 模式下只需 default_identity 为 tenant；
    user 模式下额外需要 user.name。
    """
    path = resolve_config_path("settings.json")
    result = {"settings_ready": False, "default_identity": None, "user_name": None}

    if not path.exists():
        result["detail"] = f"文件不存在: {path}"
        return result

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        result["settings_detail"] = f"文件解析失败: {e}"
        return result

    result["default_identity"] = data.get("default_identity", "user")
    user = data.get("user", {})
    result["user_name"] = user.get("name", "")

    if result["default_identity"] == "tenant":
        result["settings_ready"] = True
        result["settings_detail"] = "OK"
    elif result["default_identity"] == "user":
        result["settings_ready"] = bool(result["user_name"])
        if not result["settings_ready"]:
            result["settings_detail"] = "user 模式下缺少 user.name"
        else:
            result["settings_detail"] = "OK"
    else:
        result["settings_detail"] = f"无效的 default_identity: {result['default_identity']}"
    return result


def check_user_token():
    """user_access_token 存在、未过期、scope 检测；token 过期时只输出 next_command，不自动刷新。"""
    path = resolve_config_path("credentials.json")
    result = {
        "user_token_ready": False,
        "user_token_expired": None,
        "user_token_scopes": [],
        "user_token_scopes_sufficient": False,
        "user_token_scopes_recommended": False,
        "oauth_version": "unknown",
        "has_refresh_token": False,
        "refresh_token_expired": None,
        "next_command": None,
    }

    try:
        data, _ = load_credentials_data()
    except RuntimeError:
        result["user_token_detail"] = f"凭证文件不存在: {path}"
        result["next_command"] = "配置应用凭证（appId + appSecret）"
        return result
    except (json.JSONDecodeError, OSError) as e:
        result["user_token_detail"] = f"文件解析失败: {e}"
        return result

    token = data.get("userAccessToken", "") or data.get("user_access_token", "")
    if not token:
        result["user_token_detail"] = "user_access_token 未配置"
        result["next_command"] = "python3 feishu-auth/auth_get_user_token.py --print-auth-url --json"
        return result

    # OAuth 版本检测：v2 token 通常是长 JWT（>500 字符）
    result["oauth_version"] = "v2" if len(token) > 500 else "v1"

    # 刷新 token 状态（无论是否过期都显示）
    expire = data.get("userTokenExpire", 0)
    now = time.time()
    refresh_expire = data.get("refreshTokenExpire", 0)
    result["has_refresh_token"] = bool(data.get("refreshToken", ""))
    result["refresh_token_expired"] = refresh_expire > 0 and now > refresh_expire

    if expire > 0 and now > expire:
        result["user_token_expired"] = True
        result["user_token_ready"] = False

        # refresh_token 有效 -> 给出刷新命令，由业务脚本/_ensure_user_token() 单一入口刷新
        if result["has_refresh_token"] and not result["refresh_token_expired"]:
            result["user_token_detail"] = "user_access_token 已过期，refresh_token 有效，由业务脚本自动刷新"
            result["next_command"] = "python3 feishu-auth/auth_diagnose_token.py --refresh"
            return result

        # refresh_token 无效 或 刷新失败 -> 给出精确重新授权命令
        result["next_command"] = "python3 feishu-auth/auth_get_user_token.py --print-auth-url --json"
        if "user_token_detail" not in result:
            result["user_token_detail"] = f"user_access_token 已过期（{int(now - expire)} 秒前），refresh_token 无效或刷新失败"
        return result

    result["user_token_expired"] = False
    result["user_token_ready"] = True

    # Scope 检测
    scopes = set(data.get("userScopes", []))
    result["user_token_scopes"] = sorted(scopes)
    result["user_token_scopes_sufficient"] = CORE_USER_SCOPES.issubset(scopes)
    result["user_token_scopes_recommended"] = RECOMMENDED_USER_SCOPES.issubset(scopes)

    missing_core = CORE_USER_SCOPES - scopes
    if missing_core:
        result["missing_core_scopes"] = sorted(missing_core)

    result["user_token_detail"] = "OK"
    return result


def check_permissions():
    """permissions.json 存在且有 tenant scopes"""
    path = resolve_config_path("permissions.json")
    result = {"permissions_ready": False, "tenant_scope_count": 0, "user_scope_count": 0}

    if not path.exists():
        result["permissions_detail"] = f"文件不存在: {path}（运行 auth_sync_permissions.py 同步）"
        return result

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        result["permissions_detail"] = f"文件解析失败: {e}"
        return result

    scopes = data.get("scopes", {})
    tenant = scopes.get("tenant", [])
    user = scopes.get("user", [])
    result["tenant_scope_count"] = len(tenant)
    result["user_scope_count"] = len(user)
    result["permissions_ready"] = len(tenant) > 0
    result["permissions_detail"] = "OK" if result["permissions_ready"] else "tenant scopes 为空"
    return result


def check_admin_approval_scopes():
    """扫描 permissions.json 中已声明但可能需要管理员审批的 scope，提前预警。"""
    path = resolve_config_path("permissions.json")
    result = {"admin_approval_warnings": []}

    if not path.exists():
        return result

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return result

    scopes = data.get("scopes", {})
    declared_tenant = set(scopes.get("tenant", []))
    declared_user = set(scopes.get("user", []))
    declared = declared_tenant | declared_user

    flagged = declared & ADMIN_APPROVAL_SCOPES
    if not flagged:
        return result

    # 找出受影响的 registry 方法
    affected = {"tenant": {}, "user": {}}
    for method_name, entry in ENDPOINT_REGISTRY.items():
        for identity_type in ("tenant", "user"):
            required = set(entry.get("scopes", {}).get(identity_type, []))
            overlap = required & flagged
            for scope in overlap:
                affected[identity_type].setdefault(scope, []).append(method_name)

    warnings = []
    for scope in sorted(flagged):
        methods_tenant = affected["tenant"].get(scope, [])
        methods_user = affected["user"].get(scope, [])
        methods = sorted(set(methods_tenant + methods_user))
        warnings.append({
            "scope": scope,
            "reason": "该 scope 可能需要飞书管理员审批才能在平台生效",
            "affected_methods": methods[:10],  # 最多展示 10 个，避免过长
            "action": "在飞书开放平台 → 权限管理 → 申请并联系管理员审批，审批通过后重新发布应用并重新授权",
        })

    result["admin_approval_warnings"] = warnings
    return result


def check_risk_policy(identity="user"):
    """risk_policy.json 状态检测。

    tenant 模式要求配置 trusted_folder_tokens；user 模式下文件存在且结构有效即可。
    """
    path = resolve_config_path("risk_policy.json")
    result = {"risk_policy_ready": False}

    if not path.exists():
        result["risk_policy_detail"] = f"文件不存在: {path}"
        return result

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        result["risk_policy_detail"] = f"文件解析失败: {e}"
        return result

    workspace = data.get("workspace", {})
    tokens = workspace.get("trusted_folder_tokens", [])
    result["trusted_folder_count"] = len(tokens)

    messaging = data.get("messaging", {})
    result["trusted_user_count"] = len(messaging.get("trusted_users", []))
    result["trusted_chat_count"] = len(messaging.get("trusted_chats", []))
    result["restricted_chat_count"] = len(messaging.get("restricted_chats", []))

    if identity == "user":
        result["risk_policy_ready"] = True
        result["risk_policy_detail"] = f"OK (user 模式可选，{len(tokens)} 个信任文件夹)"
    else:
        result["risk_policy_ready"] = len(tokens) > 0
        result["risk_policy_detail"] = "OK" if result["risk_policy_ready"] else "tenant 模式需配置 trusted_folder_tokens"
    return result


def run_all_checks():
    """运行所有检测，返回完整状态报告。setup_check 不触发 token 刷新。"""
    ctx = get_config_context()
    report = {
        "config_dir": str(ctx["config_dir"]),
        "config_dir_source": ctx["source"],
    }

    # 先读取 default_identity，用于决定 risk_policy 是否必填
    identity = load_default_identity()

    checks = [
        check_python(),
        check_credentials(),
        check_settings(),
        check_user_token(),
        check_permissions(),
        check_risk_policy(identity=identity),
        check_admin_approval_scopes(),
    ]

    for c in checks:
        report.update(c)

    # user 模式下 risk_policy 可选
    risk_required = identity != "user"

    # 汇总
    all_ready = all([
        report.get("python_ready"),
        report.get("credentials_valid"),
        report.get("settings_ready"),
        report.get("user_token_ready"),
        report.get("user_token_scopes_sufficient"),
        report.get("permissions_ready"),
        risk_required and report.get("risk_policy_ready") or not risk_required,
    ])
    report["all_ready"] = all_ready

    # 缺失项
    missing = []
    recommendations = []

    if not report.get("python_ready"):
        missing.append("python_version")
    if not report.get("credentials_valid"):
        missing.append("credentials")
    if not report.get("settings_ready"):
        missing.append("settings")
    if not report.get("user_token_ready"):
        missing.append("user_token")
        if report.get("next_command"):
            # 优先输出精确命令
            if report["next_command"].startswith("python3"):
                recommendations.append(f"运行以下命令重新授权: {report['next_command']}")
            else:
                recommendations.append(report["next_command"])
        elif report.get("user_token_expired") and not report.get("has_refresh_token"):
            recommendations.append("user_access_token 已过期且没有 refresh_token，需重新授权")
        elif report.get("user_token_expired") and report.get("refresh_token_expired"):
            recommendations.append("refresh_token 已过期，需重新授权")
    if report.get("user_token_ready") and not report.get("user_token_scopes_sufficient"):
        missing.append("user_token_scopes")
        missing_sc = report.get("missing_core_scopes", [])
        recommendations.append(f"重新授权以获取核心 scope: {', '.join(missing_sc)}")
    if not report.get("permissions_ready"):
        missing.append("permissions")
        recommendations.append("运行 auth_sync_permissions.py 同步权限")
    if risk_required and not report.get("risk_policy_ready"):
        missing.append("risk_policy")
        recommendations.append("tenant 模式下需配置 risk_policy.json 中的 trusted_folder_tokens")

    if report.get("oauth_version") == "v1":
        recommendations.append("检测到 v1 OAuth token，建议重新授权获取 v2 token")

    # 管理员审批类 scope 预警
    admin_warnings = report.get("admin_approval_warnings", [])
    if admin_warnings:
        for w in admin_warnings:
            recommendations.append(
                f"权限预警: {w['scope']} 可能需要管理员审批才能生效，"
                f"影响操作: {', '.join(w['affected_methods'][:5])}"
            )

    report["missing"] = missing
    report["recommendations"] = recommendations

    return report


def print_suggest_scopes():
    """输出推荐 scope 列表，供用户在飞书控制台批量搜索开通。"""
    from feishu_common._endpoint_registry import ENDPOINT_REGISTRY

    # 收集所有 user scopes
    all_user_scopes = set()
    for entry in ENDPOINT_REGISTRY.values():
        all_user_scopes.update(entry.get("scopes", {}).get("user", []))

    # 合并推荐 scopes
    merged = sorted(RECOMMENDED_USER_SCOPES | all_user_scopes)

    print("=" * 50)
    print("推荐开通的 scope 列表")
    print("=" * 50)
    print()
    print("在飞书开放平台 → 权限管理 中，搜索以下 scope 名称并开通：")
    print()

    # 按类别分组输出
    categories = {
        "基础": ["offline_access", "auth:user.id:read"],
        "IM 消息": [],
        "通讯录": [],
        "文档": [],
        "云空间": [],
        "表格": [],
        "多维表格": [],
        "知识库": [],
        "日程": [],
        "任务": [],
        "妙记": [],
        "权限管理": [],
        "画板": [],
    }
    category_keywords = {
        "IM 消息": "im:",
        "通讯录": "contact:",
        "文档": ["docx:", "docs:document.comment"],
        "云空间": ["drive:", "space:"],
        "表格": "sheets:",
        "多维表格": ["bitable:", "base:"],
        "知识库": "wiki:",
        "日程": "calendar:",
        "任务": "task:",
        "妙记": "minutes:",
        "权限管理": "docs:permission",
        "画板": "board:",
    }

    for scope in merged:
        placed = False
        for cat, keywords in category_keywords.items():
            if isinstance(keywords, list):
                if any(scope.startswith(k) for k in keywords):
                    categories[cat].append(scope)
                    placed = True
                    break
            elif scope.startswith(keywords):
                categories[cat].append(scope)
                placed = True
                break
        if not placed and scope not in categories["基础"]:
            categories["基础"].append(scope)

    for cat, scopes in categories.items():
        if not scopes:
            continue
        print(f"  【{cat}】")
        for s in scopes:
            is_admin = s in ADMIN_APPROVAL_SCOPES
            suffix = "  ← 需管理员审批" if is_admin else ""
            print(f"    {s}{suffix}")
        print()

    print(f"共 {len(merged)} 个 scope。标注「需管理员审批」的可跳过，对应功能暂不可用。")
    print()
    print("提示：可以一次性全选开通，OAuth 授权时会自动获取所有已开通的权限。")


def main():
    json_only = "--json" in sys.argv
    fix_mode = "--fix" in sys.argv
    suggest_scopes = "--suggest-scopes" in sys.argv

    if suggest_scopes:
        print_suggest_scopes()
        return

    report = run_all_checks()

    if fix_mode:
        fixed = []
        if load_default_identity() == "user" and not report.get("risk_policy_ready"):
            if write_default_risk_policy():
                fixed.append("risk_policy.json")
        report = run_all_checks()
        report["fixed"] = fixed
        if json_only:
            print(json.dumps(report, indent=2, ensure_ascii=False))
            return
        print(f"已自动修复: {', '.join(fixed) if fixed else '无'}")
        print()

    if json_only:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return

    # 人类可读输出
    print("=" * 50)
    print("飞书 Skills 环境配置检测")
    print("=" * 50)

    items = [
        ("Python 版本", "python_ready", "python_detail"),
        ("应用凭证", "credentials_valid", "credentials_detail"),
        ("用户配置", "settings_ready", "settings_detail"),
        ("用户 Token", "user_token_ready", "user_token_detail"),
        ("权限文件", "permissions_ready", "permissions_detail"),
        ("风险策略", "risk_policy_ready", "risk_policy_detail"),
    ]

    print(f"配置目录: {report.get('config_dir')} (来源: {report.get('config_dir_source')})")
    print()

    for label, key, detail_key in items:
        status = "PASS" if report.get(key) else "FAIL"
        icon = "+" if status == "PASS" else "x"
        detail = report.get(detail_key, "")
        print(f"  [{icon}] {label}: {detail}")

    # 显式输出下一步命令
    if report.get("next_command"):
        print(f"  → 下一步: {report['next_command']}")

    admin_warnings = report.get("admin_approval_warnings", [])
    if admin_warnings:
        print()
        print("管理员审批权限预警:")
        for w in admin_warnings:
            print(f"  [!] {w['scope']} — 影响: {', '.join(w['affected_methods'][:3])}")
            print(f"      修复: 请管理员在飞书后台审批并重新发布应用")

    print()

    if report["all_ready"]:
        print("所有配置就绪，可以正常使用。")
    else:
        print(f"缺失项: {', '.join(report['missing'])}")
        if report["recommendations"]:
            print("建议:")
            for r in report["recommendations"]:
                print(f"  - {r}")

    print()
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
