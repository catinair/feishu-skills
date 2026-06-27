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

scope 来源：
    默认从 config/permissions.json 读取 user scopes（含 offline_access）。
    --minimal 可跳过自动读取，仅请求 offline_access。
    --scope 可手动指定，覆盖自动读取。

流程：
    1. 运行脚本，授权链接保存到配置目录的 _auth_url.txt
    2. 从该文件复制链接到浏览器（不要从终端输出复制，避免 URL 被截断），完成飞书授权
    3. 浏览器跳转到 redirect_uri（页面会报错，看地址栏即可）
    4. 复制地址栏中含 ?code=... 的完整 URL，粘贴回终端
    5. 脚本自动换取 token 并写入凭证文件（通过 resolver 自动选择目录）
    6. 自动从 API 拉取用户信息写入 settings.json
    7. 自动从 API 拉取 tenant scopes 写入 permissions.json
    8. user 模式下自动生成默认 risk_policy.json

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
from feishu_common import FeishuClient, cli_run, write_default_risk_policy
from feishu_common._config_loader import (
    resolve_config_path,
    get_config_dir,
    safe_write_json,
    load_credentials_data,
)

# OAuth scope 名称修正：飞书权限管理页面的名称与 OAuth scope 不总是一致
_SCOPE_FIXES = {
    "im:message.send_as_user": "im:message",
}

# 完整推荐 scopes（覆盖所有 endpoint registry 中声明的 user scopes）
# 首次授权时使用此列表，后续从 permissions.json 读取
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


def _load_user_scopes():
    """加载 user scopes，将 permissions.json 中已有的与代码推荐列表合并。

    这样新增端点后，无需用户手动修改 permissions.json，重新授权时会自动请求新 scope。
    首次授权（permissions.json 不存在）时直接返回完整推荐 scopes。
    """
    path = resolve_config_path("permissions.json")
    default_set = set(_DEFAULT_SCOPES)
    if not path.exists():
        return sorted(default_set)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return sorted(default_set)
    existing = set(data.get("scopes", {}).get("user", []))
    if not existing:
        return sorted(default_set)
    merged = existing | default_set
    fixed = set()
    for s in merged:
        fixed.add(_SCOPE_FIXES.get(s, s))
    fixed.add("offline_access")
    return sorted(fixed)


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
    except Exception as e:
        print(f"   ⚠ 自动填充 settings 失败: {e}", file=sys.stderr)


def _auto_sync_permissions(client, user_scopes):
    """授权后自动从 API 拉取 tenant scopes，写入 permissions.json"""
    from auth_sync_permissions import fetch_tenant_scopes, build_permissions_payload
    permissions_path = resolve_config_path("permissions.json", for_write=True)
    try:
        tenant_scopes = fetch_tenant_scopes(client)
        payload = build_permissions_payload(tenant_scopes, user_scopes or [])
        safe_write_json(permissions_path, payload)
        print(f"   权限已自动同步到 {permissions_path}（tenant={len(tenant_scopes)}, user={len(user_scopes or [])}）", file=sys.stderr)
    except Exception as e:
        print(f"   ⚠ 自动同步 permissions 失败: {e}", file=sys.stderr)


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
    args = parser.parse_args()

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
    elif args.minimal:
        scopes = ["offline_access"]
    else:
        scopes = _load_user_scopes()

    scope_str = " ".join(scopes)

    # Step 2: Construct auth URL (OAuth v2)
    auth_url = (
        f"https://accounts.feishu.cn/open-apis/authen/v1/authorize"
        f"?client_id={client.app_id}"
        f"&redirect_uri={urllib.parse.quote(args.redirect_uri, safe='')}"
        f"&scope={urllib.parse.quote(scope_str, safe='')}"
        f"&response_type=code")

    # 将授权链接写入文件，避免终端/对话复述时 URL 被意外截断或篡改
    auth_url_path = config_dir / "_auth_url.txt"
    auth_url_path.write_text(auth_url, encoding="utf-8")
    config_dir_for_display = config_dir

    print("=" * 60, file=sys.stderr)
    print("请按以下步骤操作：", file=sys.stderr)
    print("1. 确保已在飞书开放平台 → 安全设置 → 重定向 URL", file=sys.stderr)
    print(f"   中配置了: {args.redirect_uri}", file=sys.stderr)
    print(f"2. 授权链接已保存到: {auth_url_path}", file=sys.stderr)
    print(f"   配置目录: {config_dir_for_display}", file=sys.stderr)
    if args.auto_callback:
        print("   已启用 --auto-callback，脚本会自动捕获浏览器回调", file=sys.stderr)
    else:
        print("   请用浏览器打开该文件中的链接并完成授权", file=sys.stderr)
    print(f"   （请求 {len(scopes)} 个 scope）", file=sys.stderr)
    if not args.auto_callback:
        print("3. 授权后，从浏览器地址栏复制完整的回调 URL", file=sys.stderr)
        print("   （包含 ?code=... 的那一串）", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    # Step 3: Get authorization code
    if args.auto_callback:
        code = _capture_callback_code(args.redirect_uri, timeout=args.callback_timeout)
    else:
        callback_url = input("\n请粘贴回调 URL: ").strip()
        if not callback_url:
            print("未提供回调 URL，已取消。", file=sys.stderr)
            sys.exit(0)
        parsed = urllib.parse.urlparse(callback_url)
        query_params = urllib.parse.parse_qs(parsed.query)
        codes = query_params.get("code", [])
        if not codes:
            raise RuntimeError(f"无法从 URL 中提取 code，请检查回调 URL: {callback_url}")
        code = codes[0]

    # Step 4: Exchange code for token (OAuth v2)
    print("\n正在换取 user_access_token...", file=sys.stderr)
    token_data = exchange_code_for_token(client, code, args.redirect_uri)

    user_access_token = token_data.get("access_token", "")
    refresh_token = token_data.get("refresh_token", "")
    expires_in = token_data.get("expires_in", 0)
    refresh_expires_in = token_data.get("refresh_token_expires_in", 0) or 2592000  # 默认 30 天
    scope_text = token_data.get("scope", "")
    user_scopes = sorted({item for item in scope_text.split() if item})

    if not user_access_token:
        raise RuntimeError(f"响应中未包含 access_token: {token_data}")

    # Step 5: Save to credentials.json
    now = time.time()
    with open(creds_source_path, "r", encoding="utf-8") as f:
        creds = json.load(f)
    creds["userAccessToken"] = user_access_token
    creds["userTokenExpire"] = now + expires_in
    if refresh_token:
        creds["refreshToken"] = refresh_token
        creds["refreshTokenExpire"] = now + refresh_expires_in
    if user_scopes:
        creds["userScopes"] = user_scopes
    safe_write_json(creds_write_path, creds, mode=0o600)

    print(f"\n✅ user_access_token 已保存到 {creds_write_path}", file=sys.stderr)
    print(f"   有效期: {expires_in} 秒（约 {expires_in // 3600} 小时）", file=sys.stderr)
    if refresh_token:
        print(f"   refresh_token 也已保存，有效期 {refresh_expires_in} 秒（约 {refresh_expires_in // 86400} 天）。", file=sys.stderr)
    if user_scopes:
        print(f"   已记录 user scopes: {len(user_scopes)} 项。", file=sys.stderr)

    # Step 6: 自动拉取用户信息写入 settings.json
    _auto_populate_settings(client, creds_source_path)

    # Step 7: 自动同步 tenant scopes 写入 permissions.json
    _auto_sync_permissions(client, user_scopes)

    # Step 8: user 模式下自动生成默认 risk_policy.json
    if write_default_risk_policy():
        print(f"   已自动生成默认 risk_policy.json（user 模式）", file=sys.stderr)


if __name__ == "__main__":
    cli_run(main)
