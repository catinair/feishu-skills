#!/usr/bin/env python3
"""
_shared.py -- 飞书 Skill 公共模块
纯 Python 标准库（Pillow 可选，用于画板图片裁剪）。
提供工具函数和从子模块 re-export 的共享能力。
"""

import json
import sys

# Re-export from sub-modules to maintain backward compatibility
from ._client import FeishuClient, DEFAULT_FOLDER_TOKEN
from ._config_loader import (
    allows_implicit_confirmation,
    default_credentials_path,
    get_risk_policy_path,
    is_manual_only_action,
    load_default_identity,
    load_user_config,
    prompt_for_confirmation,
    prompt_for_strong_confirmation,
    requires_confirmation_for_action,
    should_confirm_action,
)
from ._docx_converter import BlockToMarkdownConverter, MediaExtractor


def print_json(data):
    """打印 JSON 到 stdout"""
    print(json.dumps(data, indent=2, ensure_ascii=False))


def extract_doc_id(arg):
    """从 URL 或 token 中提取 document_id"""
    for prefix in ("/docx/", "/doc/", "/wiki/"):
        if prefix in arg:
            return arg.split(prefix)[-1].split("?")[0].split("/")[0]
    return arg


def extract_base_info(arg):
    """从 base URL 中提取 app_token 和 table_id
    
    支持格式：
    - https://xxx.feishu.cn/base/XqA3bAtGpaWjflsryxfcadp7nmf?table=tblOflmn3KGcgUsn
    - XqA3bAtGpaWjflsryxfcadp7nmf/tblOflmn3KGcgUsn
    - XqA3bAtGpaWjflsryxfcadp7nmf
    """
    app_token = arg
    table_id = ""
    if "/base/" in arg:
        parts = arg.split("/base/")[-1]
        app_token = parts.split("?")[0].split("/")[0]
        if "table=" in arg:
            table_id = arg.split("table=")[-1].split("&")[0]
    elif "/" in arg:
        app_token, table_id = arg.split("/", 1)
    return app_token, table_id


# ── 部门人员查询 ──


def create_client(credentials_path=None):
    """创建客户端，默认通过 resolver 自动定位凭证文件。

    当 credentials_path 为 None 时，使用 _config_loader 的 resolver，
    支持平台运行时路径与 skill-root 的 fallback。
    """
    return FeishuClient(credentials_path)


def confirm_action_or_exit(action_name, message, *, yes=False, is_trusted=False, identity=None):
    """按风险策略决定是否确认，拒绝时直接退出。

    当 risk_policy.json 存在时，所有决策均显式输出到 stderr，
    提醒 AI Agent 遵守风控要求。

    Args:
        identity: "user" 或 "tenant"，None 时从 settings.json 读取
    """
    if identity is None:
        identity = load_default_identity()

    policy_path = get_risk_policy_path()

    # user 模式 + 无 risk_policy.json：用户自身权限即信任边界，静默放行
    if identity == "user" and not policy_path.exists():
        return

    # ── 显式输出风控决策（有 risk_policy.json 时必定输出）──

    # manual_only：最高优先级——建议引导用户在飞书界面完成
    if is_manual_only_action(action_name):
        if yes:
            print(f"[风控] {action_name}: 手动优先操作，已通过 --yes 显式确认执行", file=sys.stderr)
            return
        print(f"[风控] {action_name}: 手动优先操作（manual_only），建议引导用户在飞书界面完成", file=sys.stderr)
        confirmed = prompt_for_strong_confirmation(message)
        if not confirmed:
            print("已取消。", file=sys.stderr)
            sys.exit(0)
        return

    # always_confirm：策略要求始终确认
    if requires_confirmation_for_action(action_name):
        if yes:
            print(f"[风控] {action_name}: 策略要求 always_confirm，已通过 --yes 确认执行", file=sys.stderr)
            return
        print(f"[风控] {action_name}: 策略要求 always_confirm，需要用户确认", file=sys.stderr)
        confirmed = prompt_for_confirmation(message)
        if not confirmed:
            print("已取消。", file=sys.stderr)
            sys.exit(0)
        return

    # allow_without_confirmation：免确认，但显式告知决策依据
    if allows_implicit_confirmation(action_name, is_trusted=is_trusted):
        if is_trusted:
            print(f"[风控] {action_name} → 信任目标: 免确认执行", file=sys.stderr)
        else:
            print(f"[风控] {action_name}: 免确认执行（allow_without_confirmation）", file=sys.stderr)
        return

    # 未命中任何策略：默认需确认
    if yes:
        print(f"[风控] {action_name}: 已通过 --yes 确认执行", file=sys.stderr)
        return
    print(f"[风控] {action_name}: 未在免确认列表中，需要用户确认", file=sys.stderr)
    confirmed = prompt_for_confirmation(message)
    if not confirmed:
        print("已取消。", file=sys.stderr)
        sys.exit(0)


def lookup_contact(name=None, openid=None, user_id=None, leader=None, client=None):
    """查询人员信息（纯 API）

    Args:
        name: 按姓名模糊查询
        openid: 按 openid 精确查询
        user_id: 按 user_id 精确查询
        leader: 按直属上级查询（遍历部门成员）
        client: FeishuClient 实例（必须）

    Returns:
        匹配的人员列表，每项为 dict
    """
    if not client:
        raise RuntimeError("lookup_contact 需要 client 参数（纯 API 模式）")

    results = []
    if name:
        api_results = client.contact_search_users(name, limit=20)
        for u in api_results:
            results.append(_api_user_to_row(u))
    elif openid:
        u = client.contact_get_user(openid, user_id_type="open_id")
        results.append(_api_user_to_row(u.get("user", u)))
    elif user_id:
        u = client.contact_get_user(user_id, user_id_type="user_id")
        results.append(_api_user_to_row(u.get("user", u)))
    elif leader:
        # 没有直接的"按上级查"API，提示使用部门查询
        raise RuntimeError("按直属上级查询暂不支持纯 API 模式，请使用 contact_colleagues.py 查询同部门人员")
    else:
        raise RuntimeError("请指定查询条件: --name / --openid / --user-id")
    return results


def _api_user_to_row(u):
    """将 API 返回的用户数据标准化为 dict"""
    dept_ids = u.get("department_ids", [])
    raw_status = u.get("status", {})
    if isinstance(raw_status, dict):
        is_active = raw_status.get("is_activated", False)
    else:
        is_active = bool(raw_status)
    return {
        "name": u.get("name", ""),
        "nickname": u.get("nickname", ""),
        "user_id": u.get("user_id", ""),
        "open_id": u.get("open_id", ""),
        "email": u.get("email", ""),
        "department_ids": dept_ids,
        "department_id": dept_ids[0] if dept_ids else "",
        "status": "在职" if is_active else "未知",
    }


# ── 通用 CLI 入口 ──

def cli_run(main_func):
    """统一 CLI 入口，捕获异常并输出结构化错误到 stderr"""
    try:
        main_func()
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nCancelled.", file=sys.stderr)
        sys.exit(130)
    except FileNotFoundError as e:
        print(f"Error: File not found: {e}", file=sys.stderr)
        sys.exit(1)
