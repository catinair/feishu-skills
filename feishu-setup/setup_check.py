#!/usr/bin/env python3
"""
setup_check.py -- 飞书 Skills 环境配置检测

检测当前项目配置完整性，输出 JSON 状态报告。
供 setup SKILL.md 引导流程调用，判断哪些步骤已完成、哪些需要引导。

用法：
    python3 feishu-setup/setup_check.py
    python3 feishu-setup/setup_check.py --json    # 纯 JSON 输出
"""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from feishu_common import (
    write_default_risk_policy,
    load_default_identity,
    log_config_paths,
    create_client,
)
from feishu_common._config_loader import (
    resolve_config_path,
    get_config_context,
    load_credentials_data,
    load_settings,
    load_permissions_config,
    load_risk_policy,
    get_default_folder_token,
    trusted_folder_tokens,
    SKILL_ROOT,
)
from feishu_common._endpoint_registry import ENDPOINT_REGISTRY, ADMIN_APPROVAL_SCOPES

# 核心业务需要的最低 user scopes
CORE_USER_SCOPES = {
    "offline_access",  # refresh_token 必需
    "auth:user.id:read",  # 用户身份基础
    "im:message",  # 发送消息
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


def _canonical_config_path(filename):
    """返回配置文件的 canonical 路径（详情展示用，会按需创建平台运行时目录）。"""
    return resolve_config_path(filename, for_write=True)


def _config_found(filename):
    """判断配置文件是否存在（canonical 路径或平台 skill-root fallback）。"""
    if resolve_config_path(filename, for_write=False).exists():
        return True
    if get_config_context()["is_platform"]:
        fallback = SKILL_ROOT / "config" / filename
        if fallback.exists():
            return True
    return False


def _extract_bitable_ids(settings: dict):
    """从已加载的 settings 字典中提取 Bitable 基础设施 ID。

    唯一的字段路径定义点：两处调用方（_bitable_configured / check_bitable_infrastructure）
    都经过这里，避免字段名漂移引发的静默 bug。

    返回 (app_token, table_id) 二元组，任一为 None 表示未配置。
    """
    infra = settings.get("infrastructure", {}).get("bitable", {})
    app_token = infra.get("app_token")
    table_id = infra.get("tables", {}).get("token_backup")
    return app_token, table_id


def _bitable_configured():
    """检查 settings.json 中是否已配置 Bitable 基础设施（app_token + table_id）。"""
    settings_path = resolve_config_path("settings.json", for_write=False)
    if not settings_path.exists():
        return False
    try:
        with open(settings_path) as f:
            settings = json.load(f)
    except (json.JSONDecodeError, OSError):
        return False
    app_token, table_id = _extract_bitable_ids(settings)
    return bool(app_token and table_id)


def _get_rt_expire_time() -> float:
    """从 Bitable 读取最新 refresh_token 的过期时间戳，失败返回 0。

    仅在 Bitable 基础设施已配置且凭证完整时尝试读取，不触发 token 刷新。
    """
    if not _bitable_configured():
        return 0.0
    try:
        from feishu_common.cloud_token_manager import CloudTokenManager

        settings = load_settings()
        creds_data, _ = load_credentials_data()
        app_id = creds_data.get("appId")
        app_secret = creds_data.get("appSecret")
        if not app_id or not app_secret:
            return 0.0
        app_token, table_id = _extract_bitable_ids(settings)
        if not app_token or not table_id:
            return 0.0
        manager = CloudTokenManager(
            app_id=app_id,
            app_secret=app_secret,
            bitable_infra={"app_token": app_token, "table_id": table_id},
        )
        return manager.get_refresh_token_expire()
    except Exception:
        return 0.0


def check_python():
    """Python 版本 >= 3.9"""
    v = sys.version_info
    ok = v >= (3, 9)
    return {
        "python_ready": ok,
        "python_version": f"{v.major}.{v.minor}.{v.micro}",
        "python_detail": "OK"
        if ok
        else f"需要 Python >= 3.9，当前 {v.major}.{v.minor}.{v.micro}",
    }


def check_credentials():
    """credentials.json 存在（或环境变量提供）且有 appId/appSecret"""
    path = _canonical_config_path("credentials.json")
    result = {"credentials_ready": False, "credentials_valid": False}

    try:
        data, _ = load_credentials_data()
    except RuntimeError:
        result["credentials_detail"] = f"文件不存在: {path}"
        return result
    except (json.JSONDecodeError, OSError) as e:
        result["credentials_detail"] = f"文件解析失败: {e}"
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
    """settings.json 存在且有 default_identity。

    用户信息（user.name/open_id 等）在 OAuth 授权后由 auth_get_user_token.py 自动填充，
    setup 阶段不再要求手动输入名字。
    """
    path = _canonical_config_path("settings.json")
    result = {
        "settings_ready": False,
        "default_identity": None,
        "user_name": None,
    }

    try:
        data = load_settings()
    except (json.JSONDecodeError, OSError) as e:
        result["settings_detail"] = f"文件解析失败: {e}"
        return result

    if not _config_found("settings.json"):
        result["settings_detail"] = f"文件不存在: {path}"
        return result

    result["default_identity"] = data.get("default_identity", "user")
    user = data.get("user", {})
    result["user_name"] = user.get("name", "")
    # 只要 default_identity 存在即认为 settings 就绪；user.name 由授权后自动填充
    result["settings_ready"] = bool(result["default_identity"])

    if not result["settings_ready"]:
        result["settings_detail"] = "缺少 default_identity"
    elif not result["user_name"]:
        result["settings_detail"] = "OK (user 信息将在 OAuth 授权后自动填充)"
    else:
        result["settings_detail"] = "OK"
    return result


def check_user_token():
    """user_access_token 存在、未过期；refresh_token 状态按模式（Bitable/本地）检测。

    云模式（已配置 Bitable）：refresh_token 唯一持久化在 Bitable，credentials.json 不应含 RT。
    非云模式（本地/开源部署）：refresh_token 保存在 credentials.json，由业务脚本自动刷新。
    """
    path = _canonical_config_path("credentials.json")
    bitable_configured = _bitable_configured()
    result = {
        "user_token_ready": False,
        "user_token_expired": None,
        "user_token_scopes": [],
        "user_token_scopes_sufficient": False,
        "user_token_scopes_recommended": False,
        "oauth_version": "unknown",
        "refresh_token_source": "bitable" if bitable_configured else "local",
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

    # 云模式下 credentials.json 不应包含 refresh_token（RT 唯一持久化在 Bitable）
    if bitable_configured and data.get("refreshToken"):
        result["user_token_detail"] = (
            "cloud mode: credentials.json 中仍包含 refresh_token，请先迁移到 Bitable"
        )
        result["next_command"] = "python3 feishu-setup/setup_bitable_infrastructure.py"
        return result

    token = data.get("userAccessToken", "") or data.get("user_access_token", "")
    if not token:
        result["user_token_detail"] = "user_access_token 未配置"
        if bitable_configured:
            result["next_command"] = (
                "python3 feishu-auth/auth_device_flow.py --begin --qr --json"
            )
        else:
            result["next_command"] = (
                "python3 feishu-auth/auth_get_user_token.py --print-auth-url --json"
            )
        return result

    # OAuth 版本检测：v2 token 通常是长 JWT（>500 字符）
    result["oauth_version"] = "v2" if len(token) > 500 else "v1"

    # 过期检测
    expire = data.get("userTokenExpire", 0)
    now = time.time()
    if expire > 0 and now > expire:
        result["user_token_expired"] = True
        result["user_token_ready"] = False

        if bitable_configured:
            # 云模式：RT 过期时间从 Bitable 读取
            rt_expire = _get_rt_expire_time()
            if rt_expire > 0 and now > rt_expire:
                days_unused = int((now - rt_expire) / 86400)
                result["user_token_detail"] = (
                    f"user_access_token 已过期，且 refresh_token 已过期"
                    f"（超过 {days_unused} 天未续期）。请重新授权"
                )
                result["next_command"] = (
                    "python3 feishu-auth/auth_device_flow.py --begin --qr --json"
                )
            else:
                result["user_token_detail"] = (
                    "user_access_token 已过期，可使用 refresh_token 自动刷新"
                )
                result["next_command"] = (
                    "python3 feishu-auth/auth_diagnose_token.py --refresh"
                )
        else:
            # 非云模式：AT 过期一律建议由业务脚本自动刷新。
            # _ensure_user_token() 会先重载磁盘 RT 再刷新，刷新失败才需要重新授权。
            result["user_token_detail"] = (
                "user_access_token 已过期，由业务脚本自动刷新"
            )
            result["next_command"] = (
                "python3 feishu-auth/auth_diagnose_token.py --refresh"
            )
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
    path = _canonical_config_path("permissions.json")
    result = {
        "permissions_ready": False,
        "tenant_scope_count": 0,
        "user_scope_count": 0,
    }

    try:
        data = load_permissions_config()
    except (json.JSONDecodeError, OSError) as e:
        result["permissions_detail"] = f"文件解析失败: {e}"
        return result

    if not _config_found("permissions.json"):
        result["permissions_detail"] = (
            f"文件不存在: {path}（运行 auth_sync_permissions.py 同步）"
        )
        return result

    scopes = data.get("scopes", {})
    tenant = scopes.get("tenant", [])
    user = scopes.get("user", [])
    result["tenant_scope_count"] = len(tenant)
    result["user_scope_count"] = len(user)
    result["permissions_ready"] = len(tenant) > 0
    result["permissions_detail"] = (
        "OK" if result["permissions_ready"] else "tenant scopes 为空"
    )
    return result


def check_admin_approval_scopes():
    """扫描 permissions.json 中已声明但可能需要管理员审批的 scope，提前预警。"""
    result = {"admin_approval_warnings": []}

    try:
        data = load_permissions_config()
    except (json.JSONDecodeError, OSError):
        return result

    if not _config_found("permissions.json"):
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
        warnings.append(
            {
                "scope": scope,
                "reason": "该 scope 可能需要飞书管理员审批才能在平台生效",
                "affected_methods": methods[:10],  # 最多展示 10 个，避免过长
                "action": "在飞书开放平台 → 权限管理 → 申请并联系管理员审批，审批通过后重新发布应用并重新授权",
            }
        )

    result["admin_approval_warnings"] = warnings
    return result


def check_risk_policy(identity="user"):
    """risk_policy.json 状态检测。

    tenant 模式要求配置 trusted_folder_tokens；user 模式下文件存在且结构有效即可。
    """
    path = _canonical_config_path("risk_policy.json")
    result = {"risk_policy_ready": False}

    try:
        data = load_risk_policy()
    except (json.JSONDecodeError, OSError) as e:
        result["risk_policy_detail"] = f"文件解析失败: {e}"
        return result

    if not _config_found("risk_policy.json"):
        result["risk_policy_detail"] = f"文件不存在: {path}"
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
        result["risk_policy_detail"] = (
            "OK"
            if result["risk_policy_ready"]
            else "tenant 模式需配置 trusted_folder_tokens"
        )
    return result


def check_default_workspace_folder():
    """检测默认工作区文件夹是否已配置（用于应用身份创建的资源落地）。"""
    result = {
        "default_workspace_folder_ready": False,
        "default_workspace_folder_token": None,
        "default_workspace_folder_label": None,
        "default_workspace_folder_detail": None,
    }

    try:
        token = get_default_folder_token()
    except RuntimeError as e:
        result["default_workspace_folder_detail"] = f"未配置默认文件夹: {e}"
        return result

    result["default_workspace_folder_token"] = token
    result["default_workspace_folder_ready"] = bool(token)

    # 找到对应的 label
    policy = load_risk_policy()
    for item in policy.get("workspace", {}).get("trusted_folder_tokens", []):
        if item.get("token") == token:
            result["default_workspace_folder_label"] = item.get("label", "")
            break

    if token in trusted_folder_tokens():
        result["default_workspace_folder_detail"] = (
            f"OK (label={result.get('default_workspace_folder_label') or '-'}, token={token[:10]}...)"
        )
    else:
        result["default_workspace_folder_detail"] = (
            f"token 不在 trusted_folder_tokens 中，请检查 risk_policy.json"
        )
        result["default_workspace_folder_ready"] = False

    return result


def check_bitable_infrastructure():
    """检测 Bitable 基础设施是否已在 setup 阶段创建并可访问。"""
    result = {
        "bitable_infrastructure_ready": False,
        "bitable_infrastructure_configured": False,
        "bitable_infrastructure_accessible": False,
        "bitable_access_error": None,
        "bitable_app_token": None,
        "bitable_table_id": None,
    }

    try:
        settings = load_settings()
    except (json.JSONDecodeError, OSError) as e:
        result["bitable_infrastructure_detail"] = f"读取 settings.json 失败: {e}"
        return result

    app_token, table_id = _extract_bitable_ids(settings)

    if not app_token or not table_id:
        result["bitable_infrastructure_detail"] = "未配置 Bitable 基础设施"
        return result

    result["bitable_infrastructure_configured"] = True
    result["bitable_app_token"] = app_token
    result["bitable_table_id"] = table_id

    # 尝试访问确认表格仍存在（需要 tenant token，避免触发 user token 刷新）
    try:
        client = create_client()
        client.base_get(app_token, use_user_token=False)
        result["bitable_infrastructure_accessible"] = True
        result["bitable_infrastructure_ready"] = True
        result["bitable_infrastructure_detail"] = "OK"
    except Exception as e:
        # 访问失败可能是网络或权限问题，不影响配置判定，但会单独报告
        result["bitable_infrastructure_accessible"] = False
        result["bitable_access_error"] = str(e)
        # 仍视为 ready：配置已存在，业务脚本调用时会自动触发访问/刷新
        result["bitable_infrastructure_ready"] = True
        result["bitable_infrastructure_detail"] = f"已配置 (访问校验失败: {e})"

    return result


def run_all_checks():
    """运行所有检测，返回完整状态报告。setup_check 不触发 token 刷新。"""
    ctx = get_config_context()
    report = {
        "config_dir": str(ctx["config_dir"]),
        "config_dir_source": ctx["source"],
        "is_platform": ctx["is_platform"],
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
        check_default_workspace_folder(),
        check_bitable_infrastructure(),
        check_admin_approval_scopes(),
    ]

    for c in checks:
        report.update(c)

    # 云模式下 Bitable 基础设施是 refresh_token 的唯一存储，必须存在
    bitable_required = True

    # user 模式下 risk_policy 可选
    risk_required = identity != "user"

    # 汇总
    all_ready = all(
        [
            report.get("python_ready"),
            report.get("credentials_valid"),
            report.get("settings_ready"),
            report.get("user_token_ready"),
            report.get("user_token_scopes_sufficient"),
            report.get("permissions_ready"),
            report.get("bitable_infrastructure_ready"),
            risk_required and report.get("risk_policy_ready") or not risk_required,
        ]
    )
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
                recommendations.append(
                    f"运行以下命令重新授权: {report['next_command']}"
                )
            else:
                recommendations.append(report["next_command"])
    if report.get("user_token_ready") and not report.get(
        "user_token_scopes_sufficient"
    ):
        missing.append("user_token_scopes")
        missing_sc = report.get("missing_core_scopes", [])
        recommendations.append(f"重新授权以获取核心 scope: {', '.join(missing_sc)}")
    if not report.get("permissions_ready"):
        missing.append("permissions")
        recommendations.append("运行 auth_sync_permissions.py 同步权限")
    if risk_required and not report.get("risk_policy_ready"):
        missing.append("risk_policy")
        recommendations.append(
            "tenant 模式下需配置 risk_policy.json 中的 trusted_folder_tokens"
        )
    if not report.get("default_workspace_folder_ready"):
        recommendations.append(
            "建议配置默认工作区文件夹：用 tenant 身份创建根文件夹并共享给用户 full_access，"
            "然后在 risk_policy.json workspace.trusted_folder_tokens 中标记 default"
        )
    bitable_configured = report.get("bitable_infrastructure_configured")
    bitable_accessible = report.get("bitable_infrastructure_accessible")
    if not bitable_configured:
        missing.append("bitable_infrastructure")
        recommendations.append(
            "运行 python3 feishu-setup/setup_bitable_infrastructure.py 创建多维表格基础设施"
        )
    elif not bitable_accessible:
        recommendations.append(
            "Bitable 基础设施已配置但访问校验失败，可能是网络/权限问题；"
            "若业务脚本持续报错，请重新运行 setup_bitable_infrastructure.py"
        )

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


def main():
    parser = argparse.ArgumentParser(description="飞书 Skills 环境配置检测")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出")
    parser.add_argument(
        "--fix", action="store_true", help="自动修复可修复项（如生成默认 risk_policy）"
    )
    # 注意：setup_check 不再提供自动刷新入口，避免与业务脚本形成双触发点竞态。
    # token 刷新统一由业务脚本在 _ensure_user_token() 中处理。
    # 使用 parse_known_args，避免被 pytest 等外部参数干扰
    args, _ = parser.parse_known_args()

    log_config_paths()
    report = run_all_checks()

    if args.fix:
        fixed = []
        if load_default_identity() == "user" and not report.get("risk_policy_ready"):
            if write_default_risk_policy():
                fixed.append("risk_policy.json")
        report = run_all_checks()
        report["fixed"] = fixed
        if args.json:
            print(json.dumps(report, indent=2, ensure_ascii=False))
            return
        print(f"已自动修复: {', '.join(fixed) if fixed else '无'}")
        print()

    if args.json:
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
        (
            "默认工作区文件夹",
            "default_workspace_folder_ready",
            "default_workspace_folder_detail",
        ),
        (
            "多维表格基础设施",
            "bitable_infrastructure_ready",
            "bitable_infrastructure_detail",
        ),
    ]

    print(
        f"配置目录: {report.get('config_dir')} (来源: {report.get('config_dir_source')})"
    )
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
