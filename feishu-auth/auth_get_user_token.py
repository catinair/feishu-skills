#!/usr/bin/env python3
"""
auth_get_user_token.py -- 获取飞书 user_access_token（OAuth2 授权码模式，v2 接口）

前置条件：
    在飞书开放平台 → 应用详情 → 安全设置 → 重定向 URL 中，
    添加 redirect_uri（默认 http://localhost:8080/callback）。
    localhost 地址可以直接使用，无需公网域名。

用法：
    python auth_get_user_token.py
    python auth_get_user_token.py --redirect-uri http://localhost:19876/callback
    python auth_get_user_token.py --minimal               # 仅请求 offline_access
    python auth_get_user_token.py --scope "im:message im:chat"  # 手动指定 scope
    python auth_get_user_token.py --print-auth-url --json  # 仅输出授权链接（JSON 格式）
    python auth_get_user_token.py --callback-url "<URL>" --json  # 从回调 URL 提取 code 完成授权
    python auth_get_user_token.py --code "<CODE>" --json   # 直接提供 code 完成授权

scope 来源：
    默认从 config/permissions.json 读取 user scopes（含 offline_access）。
    --minimal 可跳过自动读取，仅请求 offline_access。
    --scope 可手动指定，覆盖自动读取。

参数：
    --redirect-uri      重定向 URL（默认 http://localhost:8080/callback），需在飞书开放平台配置
    --minimal           仅请求 offline_access scope，不自动加载全部 user scope
    --scope             手动指定 scope（空格分隔），覆盖自动读取
    --auto-callback     启动本地 HTTP server 自动捕获回调 code（仅本地环境可用）
    --callback-timeout  自动回调最长等待秒数（默认 300）
    --print-auth-url    仅生成并输出授权链接，不等待回调。搭配 --json 输出结构化 JSON
    --callback-url      从浏览器回调 URL 中提取 code 并完成授权（平台环境推荐）
    --code              直接提供 authorization code 完成授权
    --json              以 JSON 格式输出结果，方便机器解析（平台/Agent 环境建议使用）

流程（本地环境）：
    1. 运行脚本，授权链接保存到配置目录的 _auth_url.txt
    2. 从该文件复制链接到浏览器（不要从终端输出复制，避免 URL 被截断），完成飞书授权
    3. 浏览器跳转到 redirect_uri（页面会报错，看地址栏即可）
    4. 复制地址栏中含 ?code=... 的完整 URL，粘贴回终端
    5. 脚本自动换取 token 并写入凭证文件（通过 resolver 自动选择目录）
    6. 自动从 API 拉取用户信息写入 settings.json
    7. 自动从 API 拉取 tenant scopes 写入 permissions.json
    8. user 模式下自动生成默认 risk_policy.json

流程（平台/Agent 环境）：
    1. 运行 python auth_get_user_token.py --print-auth-url --json
    2. 将输出中的 auth_url 发给用户，用户在本地浏览器打开并完成飞书授权
    3. 用户将浏览器跳转后的完整回调 URL（含 ?code=...）贴回对话
    4. 运行 python auth_get_user_token.py --callback-url "<用户贴回的 URL>" --json
    5. 脚本自动提取 code、换取 token、保存凭证并输出结果 JSON
    6. 也可由 Agent 直接提取 code 参数，用 --code "<CODE>" --json 完成授权

token 刷新：
    脚本会同时获取 refresh_token（需 scope=offline_access），有效期约 30 天。
    user_access_token 过期后，客户端会自动用 refresh_token 续期，无需手动操作。
    仅当 refresh_token 也过期时，才需要重新运行此脚本。

端口冲突：
    默认端口 8080 可能被占用，用 --redirect-uri 指定其他端口（如 19876），
    但需同步在飞书开放平台更新重定向 URL。
"""

import argparse
import json
import socket
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))
from feishu_common import FeishuClient, cli_run, log_config_paths, print_json, write_default_risk_policy
from feishu_common._config_loader import (
    get_config_context,
    resolve_config_path,
    get_config_dir,
    safe_write_json,
    load_credentials_data,
    load_permissions_config,
)
from feishu_common._endpoint_registry import ENDPOINT_REGISTRY, BOTH, USER_ONLY

# OAuth scope 名称修正：飞书权限管理页面的名称与 OAuth scope 不总是一致。
# 当 registry 中的 scope 名与 OAuth 实际可请求的 scope 名不一致时，在此处建立映射。
# 注意：此处只影响 OAuth 授权请求阶段，不影响运行时的权限检查。
_SCOPE_FIXES = {
    # 示例："registry:scope:name": "oauth:scope:name"
}

# 核心 user scopes：首次 OAuth 授权或推导失败时使用的最小必要 scope 集合。
# 这些 scope 为飞书应用基础功能所必需，无需管理员审批即可使用。
CORE_USER_SCOPES = {
    "offline_access",
    "auth:user.id:read",
    "im:message",
    "contact:user.base:readonly",
}

# [DEPRECATED] _DEFAULT_SCOPES 已不再用于 _load_user_scopes() 的正常流程。
# 首次 OAuth scope 策略已改为 tenant 推导 + CORE_USER_SCOPES fallback。
# 保留此变量仅供参考：它记录了曾经推荐的全量 scope 列表。
_DEFAULT_SCOPES = sorted({
    # 基础
    "offline_access",
    "auth:user.id:read",
    # IM
    "im:message",
    "im:chat",
    # 通讯录
    "contact:user.base:readonly",
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
    # 以下需管理员审批，不纳入默认列表：
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
    "calendar:calendar:read",
    "calendar:calendar:readonly",
    "calendar:calendar.event:read",
    "calendar:calendar.event:create",
    "calendar:calendar.event:update",
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
    # 以下需管理员审批，不纳入默认列表：
    # "docs:permission.member",  # 查看、新增、更新、删除云文档协作者
    # 画板
    "board:whiteboard:node:read",
})


def _warn_admin_approval_scopes(scopes):
    """若 scopes 包含可能需要管理员审批的权限，向 stderr 输出预警。"""
    from feishu_common._endpoint_registry import ADMIN_APPROVAL_SCOPES
    flagged = set(scopes) & ADMIN_APPROVAL_SCOPES
    if not flagged:
        return
    print("=" * 60, file=sys.stderr)
    print("授权链接包含以下可能需要管理员审批的 scope:", file=sys.stderr)
    for s in sorted(flagged):
        print(f"  - {s}", file=sys.stderr)
    print("若授权后仍无法使用，请联系管理员审批并重新发布应用。", file=sys.stderr)
    print("=" * 60, file=sys.stderr)


def _derive_user_scopes_from_tenant_scopes(tenant_scopes):
    """根据应用已开通的 tenant scopes，从 endpoint registry 推导需要的 user scopes。

    规则：对于每个支持 user 身份的端点，如果其所需的 tenant scopes 非空且已全部开通，
    则将该端点所需的 user scopes 加入推荐列表。tenant scopes 为空的端点（纯 user 接口）
    不纳入推导，避免申请超出应用能力范围的权限。
    """
    tenant_set = set(tenant_scopes)
    user_scopes = set()
    for config in ENDPOINT_REGISTRY.values():
        identity = config.get("identity")
        if identity not in (BOTH, USER_ONLY):
            continue
        required_tenant = set(config.get("scopes", {}).get("tenant", []))
        if not required_tenant:
            continue
        if not required_tenant.issubset(tenant_set):
            continue
        user_scopes.update(config.get("scopes", {}).get("user", []))
    return sorted(user_scopes)


def _load_user_scopes(client=None):
    """加载 user scopes，优先从应用已开通 tenant scopes 推导，失败回退到核心 scope。

    策略：
    1. 从本地 permissions.json 读取已开通 tenant scopes 并推导
    2. 若提供了 client，在线同步 tenant scopes 并推导
    3. 以上均失败时回退到 CORE_USER_SCOPES

    Returns:
        (scopes, source): scopes 为排序后的 scope 列表，source 为
        "tenant_derived" 或 "core_fallback"。
    """
    # 尝试从 permissions.json 本地推导
    try:
        data = load_permissions_config()
    except (json.JSONDecodeError, OSError):
        data = None

    if data:
        tenant_scopes = data.get("scopes", {}).get("tenant", [])
        if tenant_scopes:
            derived = set(_derive_user_scopes_from_tenant_scopes(tenant_scopes))
            merged = derived | CORE_USER_SCOPES
            fixed = set()
            for s in merged:
                fixed.add(_SCOPE_FIXES.get(s, s))
            _warn_admin_approval_scopes(fixed)
            return sorted(fixed), "tenant_derived"

    # 如果有 client，尝试在线同步 tenant scopes
    if client is not None:
        try:
            from auth_sync_permissions import fetch_tenant_scopes
            tenant_scopes = fetch_tenant_scopes(client)
            if tenant_scopes:
                derived = set(_derive_user_scopes_from_tenant_scopes(tenant_scopes))
                merged = derived | CORE_USER_SCOPES
                fixed = set()
                for s in merged:
                    fixed.add(_SCOPE_FIXES.get(s, s))
                _warn_admin_approval_scopes(fixed)
                return sorted(fixed), "tenant_derived"
        except Exception as e:
            print(f"   ⚠ 同步 tenant scopes 失败，将使用核心 scope: {e}", file=sys.stderr)

    # 回退到核心 scope
    fixed = set()
    for s in CORE_USER_SCOPES:
        fixed.add(_SCOPE_FIXES.get(s, s))
    _warn_admin_approval_scopes(fixed)
    return sorted(fixed), "core_fallback"


def _build_auth_url(client, scopes, redirect_uri):
    """构建 OAuth v2 授权页面 URL。

    Args:
        client: FeishuClient 实例（需有 app_id 属性）。
        scopes: scope 字符串列表。
        redirect_uri: 回调地址。

    Returns:
        完整的授权 URL 字符串。
    """
    scope_str = " ".join(scopes)
    return (
        f"https://accounts.feishu.cn/open-apis/authen/v1/authorize"
        f"?client_id={client.app_id}"
        f"&redirect_uri={urllib.parse.quote(redirect_uri, safe='')}"
        f"&scope={urllib.parse.quote(scope_str, safe='')}"
        f"&response_type=code"
    )


def _extract_code_from_url(url):
    """从回调 URL 中提取 authorization code 参数。

    Args:
        url: 浏览器回调的完整 URL。

    Returns:
        authorization code 字符串。

    Raises:
        RuntimeError: URL 中不包含 code 参数。
    """
    parsed = urllib.parse.urlparse(url)
    codes = urllib.parse.parse_qs(parsed.query).get("code", [])
    if not codes:
        raise RuntimeError(f"无法从回调 URL 提取 code: {url}")
    return codes[0]


def exchange_code_for_token(client, code, redirect_uri):
    """用授权码换取 user_access_token（OAuth v2）"""
    url = f"{client.base_url}/open-apis/authen/v2/oauth/token"
    body = json.dumps({
        "grant_type": "authorization_code",
        "client_id": client.app_id,
        "client_secret": client.app_secret,
        "code": code,
        "redirect_uri": redirect_uri,
    }).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"换取 token 失败: HTTP {e.code} | {e.read().decode()[:300]}") from e
    if data.get("code") != 0:
        raise RuntimeError(f"换取 token 失败: {data}")
    return data


def _auto_populate_settings(client, creds_path):
    """授权后自动从 API 拉取用户信息，写入 settings.json"""
    settings_path = resolve_config_path("settings.json", for_write=True)
    try:
        # contact_get_self 返回最完整的基础信息（name, email, user_id, open_id）
        me = client.contact_get_self()
        open_id = me.get("open_id", "")
        user_info = {
            "name": me.get("name", ""),
            "en_name": me.get("en_name", ""),
            "user_id": me.get("user_id", ""),
            "open_id": open_id,
            "email": me.get("email", ""),
        }
        # contact_get_user 补充部门等组织信息（基础字段不如 contact_get_self 全）
        if open_id:
            try:
                full = client.contact_get_user(open_id, user_id_type="open_id")
                u = full.get("user", full)
                dept_path = u.get("department_path", [])
                if dept_path:
                    user_info["department"] = dept_path[0].get("department_name", {}).get("name", "")
                    user_info["department_id"] = dept_path[0].get("department_id", "")
                if u.get("job_title"):
                    user_info["job_title"] = u["job_title"]
            except Exception:
                pass  # 组织信息获取失败时保留基础信息

        # 读取现有 settings，合并 user 字段
        settings = {}
        if settings_path.exists():
            try:
                settings = json.loads(settings_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        settings["default_identity"] = "user"
        settings["user"] = {**settings.get("user", {}), **user_info}
        safe_write_json(settings_path, settings)
        print(f"   用户信息已自动写入 {settings_path}（{user_info['name']}）", file=sys.stderr)
        return True, None
    except Exception as e:
        print(f"   ⚠ 自动填充 settings 失败: {e}", file=sys.stderr)
        return False, str(e)


def _auto_sync_permissions(client, user_scopes):
    """授权后自动从 API 拉取 tenant scopes，写入 permissions.json"""
    from auth_sync_permissions import fetch_tenant_scopes, build_permissions_payload
    permissions_path = resolve_config_path("permissions.json", for_write=True)
    try:
        tenant_scopes = fetch_tenant_scopes(client)
        payload = build_permissions_payload(tenant_scopes, user_scopes or [])
        safe_write_json(permissions_path, payload)
        print(f"   权限已自动同步到 {permissions_path}（tenant={len(tenant_scopes)}, user={len(user_scopes or [])}）", file=sys.stderr)
        return True, None
    except Exception as e:
        print(f"   ⚠ 自动同步 permissions 失败: {e}", file=sys.stderr)
        return False, str(e)


def _exchange_and_finish(client, code, redirect_uri, creds_write_path,
                         creds_source_path, json_mode=False):
    """用授权码换取 token 并完成后续设置：保存凭证、重建 client、
    自动填充 settings、同步权限、写入 risk policy。

    Args:
        client: FeishuClient 实例。
        code: 授权码。
        redirect_uri: 回调地址。
        creds_write_path: 凭证写入路径。
        creds_source_path: 凭证源路径。
        json_mode: 为 True 时以 JSON 格式输出结果到 stdout。

    Returns:
        (success: bool, info: dict)
    """
    # Exchange code for token (OAuth v2)
    print("\n正在换取 user_access_token...", file=sys.stderr)
    token_data = exchange_code_for_token(client, code, redirect_uri)

    user_access_token = token_data.get("access_token", "")
    refresh_token = token_data.get("refresh_token", "")
    expires_in = token_data.get("expires_in", 0)
    refresh_expires_in = token_data.get("refresh_token_expires_in", 0) or 2592000  # 默认 30 天
    scope_text = token_data.get("scope", "")
    user_scopes = sorted({item for item in scope_text.split() if item})

    if not user_access_token:
        raise RuntimeError(f"响应中未包含 access_token: {token_data}")

    # 云模式下 Bitable 基础设施必须已配置
    if not client._cloud_token_manager:
        raise RuntimeError(
            "cloud mode: Bitable infrastructure is not configured. "
            "Please run python3 feishu-setup/setup_bitable_infrastructure.py first."
        )

    # 保存凭证：userAccessToken 写入 credentials.json 作为非权威缓存；
    # refresh_token 通过 CloudTokenManager 写入 Bitable（不落地本地）。
    bitable_record_id = client._save_user_token(
        user_access_token,
        refresh_token,
        expires_in,
        refresh_expires_in,
        scopes=user_scopes,
    )

    print(f"\n✅ user_access_token 已保存到 {creds_write_path}", file=sys.stderr)
    print(f"   有效期: {expires_in} 秒（约 {expires_in // 3600} 小时）", file=sys.stderr)
    if refresh_token:
        print(
            f"   refresh_token 已追加到 Bitable，有效期 {refresh_expires_in} 秒"
            f"（约 {refresh_expires_in // 86400} 天）。",
            file=sys.stderr,
        )
    if user_scopes:
        print(f"   已记录 user scopes: {len(user_scopes)} 项。", file=sys.stderr)

    # 必须用写入新 token 后的凭证重新创建 client，否则旧 client 仍持有过期 token，
    # 调用 API 时会触发 refresh_token 刷新逻辑，可能把刚写入的新 token 覆盖或清空。
    client = FeishuClient(str(creds_write_path))
    settings_populated, settings_error = _auto_populate_settings(client, creds_source_path)
    permissions_synced, permissions_error = _auto_sync_permissions(client, user_scopes)

    risk_policy_created = write_default_risk_policy()
    if risk_policy_created:
        print(f"   已自动生成默认 risk_policy.json（user 模式）", file=sys.stderr)

    cloud_manager = client._cloud_token_manager
    result = {
        "success": True,
        "token_path": str(creds_write_path),
        "expires_in": expires_in,
        "refresh_expires_in": refresh_expires_in,
        "scopes": user_scopes,
        "cloud_mode_enabled": bool(cloud_manager),
        "bitable_app_token": cloud_manager.bitable_app_token if cloud_manager else None,
        "bitable_table_id": cloud_manager.bitable_table_id if cloud_manager else None,
        "refresh_token_fingerprint": f"{refresh_token[:6]}...{refresh_token[-4:]}" if refresh_token and len(refresh_token) >= 12 else "<empty>",
        "bitable_record_id": bitable_record_id,
        "settings_populated": settings_populated,
        "settings_error": settings_error,
        "permissions_synced": permissions_synced,
        "permissions_error": permissions_error,
        "risk_policy_created": risk_policy_created,
    }

    if json_mode:
        print_json(result)

    return True, result


class _CallbackHandler(BaseHTTPRequestHandler):
    """本地回调 HTTP handler，提取 ?code=... 后停止服务。"""

    code = None

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)
        codes = query.get("code", [])
        if codes:
            _CallbackHandler.code = codes[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                "<html><body><h1>授权成功</h1><p>请回到终端继续操作。</p></body></html>".encode("utf-8")
            )
        else:
            self.send_response(400)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                "<html><body><h1>授权失败</h1><p>未找到 code 参数。</p></body></html>".encode("utf-8")
            )

    def log_message(self, format, *args):
        # 静默访问日志，保持终端干净
        pass


def _capture_callback_code(redirect_uri, timeout=300):
    """启动本地 HTTP server 等待 OAuth 回调，返回 code。

    Args:
        redirect_uri: 回调地址，必须是 http://host:port/path 格式
        timeout: 最长等待秒数
    Returns:
        提取到的 authorization code
    Raises:
        RuntimeError: 超时或无法启动服务
    """
    parsed = urllib.parse.urlparse(redirect_uri)
    if not parsed.port:
        raise RuntimeError(f"无法从 redirect_uri 解析端口: {redirect_uri}")
    port = parsed.port
    host = parsed.hostname or "localhost"

    _CallbackHandler.code = None
    server = HTTPServer((host, port), _CallbackHandler)
    server.timeout = 1  # 每次 handle_request 阻塞 1 秒

    def serve():
        while _CallbackHandler.code is None:
            try:
                server.handle_request()
            except Exception:
                break

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()

    print(f"   已启动本地回调服务: http://{host}:{port}", file=sys.stderr)
    print("   请用浏览器打开授权链接，授权后浏览器将自动跳转回本地服务。", file=sys.stderr)

    deadline = time.time() + timeout
    while _CallbackHandler.code is None and time.time() < deadline:
        time.sleep(0.5)

    server.server_close()
    thread.join(timeout=2)

    if _CallbackHandler.code is None:
        raise RuntimeError(f"等待回调超时（{timeout} 秒），未收到 authorization code")
    return _CallbackHandler.code


def main():
    parser = argparse.ArgumentParser(description="获取飞书 user_access_token")
    parser.add_argument("--redirect-uri", default="http://localhost:8080/callback",
                        help="重定向 URL（必须已在飞书开放平台配置）")
    parser.add_argument("--minimal", action="store_true",
                        help="仅请求 offline_access，不自动加载全部 user scope")
    parser.add_argument("--scope", default=None,
                        help="手动指定 scope（空格分隔），覆盖自动读取")
    parser.add_argument("--auto-callback", action="store_true",
                        help="启动本地 HTTP server 自动捕获回调 code（默认手动粘贴）")
    parser.add_argument("--callback-timeout", type=int, default=300,
                        help="自动回调最长等待秒数（默认 300）")
    parser.add_argument("--print-auth-url", action="store_true",
                        help="仅生成并输出授权链接，不等待回调")
    parser.add_argument("--callback-url", default=None,
                        help="从浏览器回调 URL 中提取 code 并完成授权")
    parser.add_argument("--code", default=None,
                        help="直接提供 authorization code 完成授权")
    parser.add_argument("--json", action="store_true",
                        help="以 JSON 格式输出结果")
    args = parser.parse_args()

    log_config_paths()

    config_dir = get_config_dir(for_write=True)
    creds_write_path = resolve_config_path("credentials.json", for_write=True)
    # 读取支持 fallback：平台首次运行时可能从 skill-root 的 credentials.json 读取
    creds_data, creds_source_path = load_credentials_data()
    if not creds_source_path:
        creds_source_path = creds_write_path
    client = FeishuClient(str(creds_source_path))

    # Step 1: Determine scopes
    if args.scope:
        scopes = sorted(set(args.scope.split()))
        scope_source = "manual"
        _warn_admin_approval_scopes(scopes)
    elif args.minimal:
        scopes = ["offline_access"]
        scope_source = "minimal"
        _warn_admin_approval_scopes(scopes)
    else:
        scopes, scope_source = _load_user_scopes(client)

    # Step 2: Build auth URL (OAuth v2)
    auth_url = _build_auth_url(client, scopes, args.redirect_uri)

    # --print-auth-url mode: 仅输出授权链接并退出
    if args.print_auth_url:
        auth_url_path = config_dir / "_auth_url.txt"
        auth_url_path.write_text(auth_url, encoding="utf-8")
        ctx = get_config_context()
        result = {
            "auth_url": auth_url,
            "scopes": scopes,
            "scope_source": scope_source,
            "config_dir": str(ctx["config_dir"]),
            "source": ctx["source"],
        }
        if args.json:
            print_json(result)
        else:
            print(auth_url)
        return

    # Step 3: Get authorization code
    if args.code:
        code = args.code
    elif args.callback_url:
        code = _extract_code_from_url(args.callback_url)
    elif args.auto_callback:
        # 自动捕获回调：先写入授权文件并打印指引
        auth_url_path = config_dir / "_auth_url.txt"
        auth_url_path.write_text(auth_url, encoding="utf-8")

        _print_auth_instructions(args, auth_url, auth_url_path, config_dir,
                                 scopes, scope_source, auto_callback=True)

        code = _capture_callback_code(args.redirect_uri, timeout=args.callback_timeout)
        # 清理临时授权链接文件
        try:
            auth_url_path.unlink(missing_ok=True)
        except Exception:
            pass
    else:
        # 默认交互模式：写入文件并等待手动粘贴
        auth_url_path = config_dir / "_auth_url.txt"
        auth_url_path.write_text(auth_url, encoding="utf-8")

        _print_auth_instructions(args, auth_url, auth_url_path, config_dir,
                                 scopes, scope_source, auto_callback=False)

        callback_url = input("\n请粘贴回调 URL: ").strip()
        if not callback_url:
            print("未提供回调 URL，已取消。", file=sys.stderr)
            sys.exit(0)
        code = _extract_code_from_url(callback_url)
        # 清理临时授权链接文件
        try:
            auth_url_path.unlink(missing_ok=True)
        except Exception:
            pass

    # Step 4: Exchange and finish
    _exchange_and_finish(client, code, args.redirect_uri, creds_write_path,
                         creds_source_path, json_mode=args.json)


def _print_auth_instructions(args, auth_url, auth_url_path, config_dir,
                             scopes, scope_source, auto_callback=False):
    """向 stderr 输出授权操作指引。"""
    print("=" * 60, file=sys.stderr)
    print("请按以下步骤操作：", file=sys.stderr)
    print("1. 确保已在飞书开放平台 → 安全设置 → 重定向 URL", file=sys.stderr)
    print(f"   中配置了: {args.redirect_uri}", file=sys.stderr)
    print(f"2. 授权链接已保存到: {auth_url_path}", file=sys.stderr)
    print(f"   配置目录: {config_dir}", file=sys.stderr)
    if auto_callback:
        print("   已启用 --auto-callback，脚本会自动捕获浏览器回调", file=sys.stderr)
    else:
        print("   请用浏览器打开该文件中的链接并完成授权", file=sys.stderr)
    print(f"   （请求 {len(scopes)} 个 scope）", file=sys.stderr)
    if not auto_callback:
        print("3. 授权后，从浏览器地址栏复制完整的回调 URL", file=sys.stderr)
        print("   （包含 ?code=... 的那一串）", file=sys.stderr)
    if scope_source == "tenant_derived":
        print(f"   权限来源: 从已开通 tenant scopes 推导", file=sys.stderr)
    elif scope_source == "core_fallback":
        print(f"   权限来源: 核心 scope（未检测到已开通权限）", file=sys.stderr)
    print("=" * 60, file=sys.stderr)


if __name__ == "__main__":
    cli_run(main)
