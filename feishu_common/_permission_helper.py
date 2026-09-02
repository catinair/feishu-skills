#!/usr/bin/env python3
"""
权限错误诊断辅助模块
从飞书 API 权限错误响应中提取缺失 scope，生成开发者控制台申请链接。

用法:
  from feishu_common._permission_helper import diagnose_permission_error

  try:
      client.some_api_call()
  except RuntimeError as e:
      hint = diagnose_permission_error(e, app_id, response_body)
      if hint:
          print(hint)  # 输出包含 scope-apply 链接的修复指引
"""

import json
import urllib.parse


# ── 权限错误码 ────────────────────────────────────────────

PERMISSION_ERROR_CODES = {
    99991672: "应用权限不足",
    99991679: "用户权限不足",
    112005: "应用未开通所需权限",
    1130001: "权限未开通",
}


def extract_missing_scopes(error_response):
    """从飞书权限错误响应中提取缺失的 scope 列表。

    Args:
        error_response: 飞书 API 返回的错误 JSON（dict），或原始字符串。

    Returns:
        list[str]: 缺失的 scope 列表，如 ["drive:file:upload"]。
                   如果无法提取，返回空列表。

    飞书权限错误响应格式示例:
      {
        "code": 99991672,
        "msg": "Access denied",
        "error": {
          "permission_violations": [
            {"subject": "drive:file:upload"},
            {"subject": "docs:document:write"}
          ]
        }
      }
    """
    if isinstance(error_response, str):
        try:
            error_response = json.loads(error_response)
        except (json.JSONDecodeError, ValueError):
            return []

    if not isinstance(error_response, dict):
        return []

    # 方式 1: 标准 permission_violations 格式
    err_block = error_response.get("error", {})
    violations = err_block.get("permission_violations", [])
    if violations:
        scopes = []
        for v in violations:
            if isinstance(v, dict) and v.get("subject"):
                scopes.append(v["subject"])
            elif isinstance(v, str):
                scopes.append(v)
        if scopes:
            return scopes

    # 方式 2: 飞书部分端点返回的 msg 中包含 scope 关键词
    msg = error_response.get("msg", "")
    if "scope" in msg.lower() or "权限" in msg:
        # 尝试从 msg 中提取 scope 格式的字符串
        import re

        pattern = r"[\w]+:[\w]+(?:\.[\w]+)*"
        scopes = re.findall(pattern, msg)
        if scopes:
            return scopes

    return []


def build_scope_apply_url(app_id, scopes):
    """生成飞书开发者控制台权限申请链接。

    Args:
        app_id: 飞书应用 ID，如 "cli_a925cfd72dbadcee"
        scopes: 缺失的 scope 列表

    Returns:
        str: 完整的 scope-apply 链接
    """
    base = (
        f"https://open.feishu.cn/page/scope-apply?clientID={urllib.parse.quote(app_id)}"
    )
    if scopes:
        base += f"&scopes={urllib.parse.quote(','.join(scopes))}"
    return base


def is_permission_error(error_code):
    """判断给定的飞书业务错误码是否为权限相关错误。

    Args:
        error_code: 飞书 API 返回的 code 字段（int 或 str）

    Returns:
        bool
    """
    try:
        code = int(error_code)
    except (ValueError, TypeError):
        return False
    return code in PERMISSION_ERROR_CODES


def format_permission_hint(app_id, missing_scopes, error_code=None):
    """生成用户友好的权限错误修复指引。

    Args:
        app_id: 飞书应用 ID
        missing_scopes: 缺失的 scope 列表
        error_code: 飞书错误码（可选）

    Returns:
        str: 格式化后的指引文本
    """
    lines = []
    if error_code and int(error_code) in PERMISSION_ERROR_CODES:
        lines.append(
            f"权限错误 [{error_code}]: {PERMISSION_ERROR_CODES[int(error_code)]}"
        )
    else:
        lines.append("权限不足")

    if missing_scopes:
        lines.append(f"缺失的权限: {', '.join(missing_scopes)}")
        apply_url = build_scope_apply_url(app_id, missing_scopes)
        lines.append(f"请访问以下链接申请权限:")
        lines.append(f"  {apply_url}")
        lines.append(f"申请后需重新发布应用并重新授权。")
    else:
        lines.append("无法自动识别缺失权限，请在飞书开放平台检查应用权限配置。")

    return "\n".join(lines)


def try_diagnose_permission_error(exception, app_id, response_body=None):
    """尝试从异常中诊断权限错误，返回修复指引或 None。

    这是一个便捷函数，适合在现有错误处理中插入调用。

    Args:
        exception: RuntimeError 异常对象
        app_id: 飞书应用 ID
        response_body: 原始 API 响应体（dict 或 str），如果为 None 则尝试从异常消息中提取

    Returns:
        str or None: 如果诊断出权限错误，返回修复指引文本；否则返回 None
    """
    error_msg = str(exception)

    # 尝试从错误消息中提取错误码
    import re

    code_match = re.search(r"\[(\d+)\]", error_msg)
    error_code = code_match.group(1) if code_match else None

    if error_code and not is_permission_error(error_code):
        return None

    # 尝试提取缺失 scope
    missing_scopes = []
    if response_body:
        missing_scopes = extract_missing_scopes(response_body)

    if not missing_scopes:
        # 尝试从错误消息中提取
        scope_pattern = r"[\w]+:[\w]+(?:\.[\w]+)*"
        found = re.findall(scope_pattern, error_msg)
        # 过滤掉常见的非 scope 字符串
        missing_scopes = [s for s in found if "/" not in s and "http" not in s]

    if missing_scopes or (error_code and is_permission_error(error_code)):
        return format_permission_hint(app_id, missing_scopes, error_code)

    return None


# ── 命令行入口（调试用）───────────────────────────────────

if __name__ == "__main__":
    import sys

    # 测试: 解析示例错误响应
    sample = {
        "code": 99991672,
        "msg": "Access denied",
        "error": {"permission_violations": [{"subject": "drive:file:upload"}]},
    }
    scopes = extract_missing_scopes(sample)
    print(f"缺失 scope: {scopes}")
    if scopes:
        print(f"申请链接: {build_scope_apply_url('cli_example', scopes)}")
        print()
        print(format_permission_hint("cli_example", scopes, "99991672"))
