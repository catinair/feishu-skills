#!/usr/bin/env python3
"""
setup_bitable_infrastructure.py -- 创建 refresh_token 云端备份所需的多维表格基础设施

在 setup 阶段运行一次，创建：
- 一个归应用所有的多维表格（使用 tenant_access_token）
- 一个名为 token_backup 的表，用于跨实例共享 refresh_token

创建成功后，把 app_token 和 table_id 写入 settings.json 的 infrastructure.bitable
字段。后续刷新成功时会自动备份 RT 到该表，刷新失败时可从该表恢复。

用法：
    python3 feishu-setup/setup_bitable_infrastructure.py
    python3 feishu-setup/setup_bitable_infrastructure.py --force  # 强制重建
    python3 feishu-setup/setup_bitable_infrastructure.py --yes   # 跳过确认
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from feishu_common import (
    cli_run,
    create_client,
    log_config_paths,
    confirm_action_or_exit,
)
from feishu_common._config_loader import (
    resolve_config_path,
    load_credentials_data,
    load_settings,
    safe_write_json,
)


BITABLE_NAME = "feishu-skills-refreshtoken"
TABLE_NAME = "token_backup"
TABLE_ALIAS = "token_backup"

# token_backup 表字段定义
# 类型说明：1=文本，2=数字，5=日期时间
TOKEN_BACKUP_FIELDS = [
    {"field_name": "app_id", "type": 1},
    {"field_name": "refresh_token", "type": 1},
    {"field_name": "refresh_token_expire", "type": 2},
    {"field_name": "updated_at", "type": 5},
    {"field_name": "updated_by_pid", "type": 1},
    {"field_name": "instance_id", "type": 1},
]

# 创建 Bitable 基础设施的必需 tenant scopes。
# 注意：drive:drive 等云空间权限与创建 Bitable 无关，不需要在此处检查。
REQUIRED_TENANT_SCOPES = {
    "base:app:create",
    "base:table:create",
    "base:block:create",
    "base:record:create",
    "base:record:update",
    "bitable:app",
}


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_infrastructure(settings):
    return settings.get("infrastructure", {}).get("bitable", {})


def _check_existing_infrastructure(settings_path):
    """检查 settings.json 中是否已有 bitable 基础设施配置。"""
    if not settings_path.exists():
        return None
    try:
        settings = load_settings()
    except Exception:
        return None
    infra = _load_infrastructure(settings)
    if infra.get("app_token") and infra.get("tables", {}).get(TABLE_ALIAS):
        return infra
    return None


def _find_existing_bitable_in_drive(client, app_id):
    """在 Drive 中搜索已创建的 feishu-skills-refreshtoken 多维表格。

    按修改时间倒序遍历同名 Bitable，验证其包含 token_backup 表且存在
    当前 app_id 的记录后返回基础设施信息。用于本地/云环境共享同一套 Bitable。
    """
    print(f"正在搜索是否已有 {BITABLE_NAME} 多维表格...", file=sys.stderr)
    try:
        result = client._request(
            "GET",
            "/open-apis/drive/v1/files",
            query={"page_size": 200},
            use_user_token=False,
            method_name="drive_list_files",
        )
    except Exception as e:
        print(f"警告: 搜索 Drive 文件失败: {e}", file=sys.stderr)
        return None

    files = result.get("files", [])
    candidates = [
        f for f in files if f.get("type") == "bitable" and f.get("name") == BITABLE_NAME
    ]
    if not candidates:
        print(f"未找到 {BITABLE_NAME} 多维表格", file=sys.stderr)
        return None

    # 按修改时间倒序，优先使用最新的
    candidates.sort(key=lambda f: int(f.get("modified_time", 0)), reverse=True)

    for candidate in candidates:
        app_token = candidate.get("token")
        if not app_token:
            continue
        try:
            client.base_get(app_token, use_user_token=False)
        except Exception as e:
            print(f"候选 {app_token[:12]}... 无法访问，跳过: {e}", file=sys.stderr)
            continue

        try:
            tables_resp = client.base_list_tables(app_token, use_user_token=False)
        except Exception as e:
            print(f"候选 {app_token[:12]}... 列出表失败，跳过: {e}", file=sys.stderr)
            continue

        table_id = None
        for table in tables_resp.get("items", []):
            if table.get("name") == TABLE_NAME or table.get("table_id") == TABLE_NAME:
                table_id = table.get("table_id")
                break
        if not table_id:
            print(
                f"候选 {app_token[:12]}... 未找到 {TABLE_NAME} 表，跳过",
                file=sys.stderr,
            )
            continue

        # 验证表中是否已有当前 app_id 的记录
        try:
            records = client.base_search_records(
                app_token,
                table_id,
                filter={
                    "conjunction": "and",
                    "conditions": [
                        {
                            "field_name": "app_id",
                            "operator": "is",
                            "value": [app_id],
                        }
                    ],
                },
                max_results=1,
                use_user_token=False,
            )
        except Exception as e:
            print(f"候选 {app_token[:12]}... 查询记录失败，跳过: {e}", file=sys.stderr)
            continue

        if records.get("items"):
            print(
                f"找到已存在的 Bitable: app_token={app_token}, table_id={table_id}",
                file=sys.stderr,
            )
            return {
                "app_token": app_token,
                "url": candidate.get("url", ""),
                "created_at": _now_iso(),
                "tables": {TABLE_ALIAS: table_id},
            }

    print("未找到包含当前 app_id 记录的有效 Bitable", file=sys.stderr)
    return None


def _check_tenant_scopes(client):
    """确认应用已开通创建 Bitable 基础设施所需的 tenant scopes。

    Returns:
        (ok: bool, missing: set)
    """
    try:
        data = client._request(
            "GET", "/open-apis/application/v6/scopes", method_name="application_scopes"
        )
    except Exception as e:
        print(f"无法查询应用权限: {e}", file=sys.stderr)
        return False, REQUIRED_TENANT_SCOPES.copy()

    granted = set()
    for item in data.get("scopes", []):
        if item.get("scope_type") == "tenant" and item.get("grant_status") == 1:
            granted.add(item.get("scope_name"))

    missing = REQUIRED_TENANT_SCOPES - granted
    if missing:
        print(
            f"缺少必要的 tenant scope: {', '.join(sorted(missing))}\n"
            "请在飞书开放平台 → 权限管理 → 开通这些权限，并联系管理员审批（如需），"
            "然后重新发布应用。",
            file=sys.stderr,
        )
        return False, missing
    return True, set()


def _verify_bitable_accessible(client, app_token):
    """确认 Bitable 可被访问（使用应用身份，避免触发 user token 刷新）。"""
    try:
        client.base_get(app_token, use_user_token=False)
        return True, None
    except Exception as e:
        print(f"无法访问已配置的多维表格: {e}", file=sys.stderr)
        return False, str(e)


def _create_infrastructure(client, app_id, folder_token=None):
    """创建 Bitable app、token_backup 表及初始记录。"""
    print(f"正在创建多维表格「{BITABLE_NAME}」...", file=sys.stderr)
    app = client.base_create(
        name=BITABLE_NAME,
        folder_token=folder_token,
        use_user_token=False,
    )
    app_token = app.get("app_token")
    app_url = app.get("url", "")
    if not app_token:
        raise RuntimeError(f"创建多维表格失败：响应中缺少 app_token，响应={app}")
    print(f"已创建: app_token={app_token}", file=sys.stderr)

    print(f"正在创建表「{TABLE_NAME}」...", file=sys.stderr)
    table_resp = client.base_create_table(
        app_token,
        name=TABLE_NAME,
        fields=TOKEN_BACKUP_FIELDS,
        use_user_token=False,
    )
    table_id = table_resp.get("table_id")
    if not table_id:
        raise RuntimeError(f"创建表失败：响应中缺少 table_id，响应={table_resp}")
    print(f"已创建表: table_id={table_id}", file=sys.stderr)

    print("正在写入初始占位记录...", file=sys.stderr)
    record = client.base_create_record(
        app_token,
        table_id,
        fields={
            "app_id": app_id,
            "refresh_token": "",
            "refresh_token_expire": 0,
            "updated_at": int(time.time() * 1000),
            "updated_by_pid": "",
            "instance_id": "",
        },
        use_user_token=False,
    )
    record_id = record.get("record_id")
    print(f"已写入初始记录: record_id={record_id}", file=sys.stderr)

    infra = {
        "app_token": app_token,
        "url": app_url,
        "created_at": _now_iso(),
        "tables": {
            TABLE_ALIAS: table_id,
        },
    }
    return infra, record_id


def _backup_current_refresh_token(client, creds):
    """把 creds 中当前的 refresh_token 追加到 Bitable（失败不抛异常）。"""
    current_rt = creds.get("refreshToken", "")
    current_rt_expire = creds.get("refreshTokenExpire", 0)
    if not current_rt:
        return False, "no local refresh_token to backup"
    if not client._cloud_token_manager:
        print(
            "警告: 未找到 Bitable 基础设施配置，无法备份 refresh_token", file=sys.stderr
        )
        return False, "Bitable infrastructure not configured"
    try:
        print("正在把当前 refresh_token 追加到 Bitable...", file=sys.stderr)
        client._cloud_token_manager.save_refresh_token(current_rt, current_rt_expire)
        return True, None
    except Exception as e:
        print(f"备份当前 refresh_token 到 Bitable 失败（非关键）: {e}", file=sys.stderr)
        return False, str(e)


def _strip_local_refresh_token(creds):
    """云模式下迁移完成后，移除 credentials.json 中的本地 refresh_token 字段。"""
    if not creds.get("refreshToken"):
        return False, "no local refresh_token to strip"
    try:
        creds_path = resolve_config_path("credentials.json", for_write=True)
        if not creds_path.exists():
            return False, "credentials.json does not exist"
        with open(creds_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "refreshToken" in data or "refreshTokenExpire" in data:
            data.pop("refreshToken", None)
            data.pop("refreshTokenExpire", None)
            safe_write_json(creds_path, data, mode=0o600)
            print("已清理 credentials.json 中的本地 refresh_token", file=sys.stderr)
            return True, None
        return False, "no local refresh_token fields in file"
    except Exception as e:
        print(
            f"清理 credentials.json 中的 refresh_token 失败（非关键）: {e}",
            file=sys.stderr,
        )
        return False, str(e)


def main():
    parser = argparse.ArgumentParser(
        description="创建 refresh_token 云端备份所需的多维表格基础设施"
    )
    parser.add_argument(
        "--force", action="store_true", help="强制重新创建（会丢失旧表中的备份数据）"
    )
    parser.add_argument("--yes", "-y", action="store_true", help="跳过确认")
    parser.add_argument("--folder-token", help="指定父文件夹 token（可选）")
    args = parser.parse_args()

    log_config_paths()

    result = {
        "created": False,
        "reason": None,
        "error": None,
        "tenant_scopes_ok": None,
        "missing_scopes": [],
        "backup_succeeded": None,
        "backup_error": None,
        "local_refresh_token_stripped": None,
        "local_refresh_token_strip_error": None,
        "infrastructure": None,
    }

    settings_path = resolve_config_path("settings.json", for_write=True)
    existing = None if args.force else _check_existing_infrastructure(settings_path)
    if existing:
        accessible, access_error = _verify_bitable_accessible(
            create_client(), existing["app_token"]
        )
        if accessible:
            # 基础设施已存在：也把当前 RT 追加一次，方便首次 setup 后补录
            client = create_client()
            try:
                creds, _ = load_credentials_data()
                backup_ok, backup_err = _backup_current_refresh_token(client, creds)
                result["backup_succeeded"] = backup_ok
                result["backup_error"] = backup_err
                if backup_ok:
                    stripped, strip_err = _strip_local_refresh_token(creds)
                    result["local_refresh_token_stripped"] = stripped
                    result["local_refresh_token_strip_error"] = strip_err
            except Exception as e:
                print(f"读取凭证或备份失败（非关键）: {e}", file=sys.stderr)
                result["backup_error"] = str(e)
            result["reason"] = "infrastructure already exists"
            result["infrastructure"] = existing
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return
        else:
            # 已配置但访问失败，继续尝试 Drive 复用或新建
            print(
                f"settings.json 中已有 Bitable 配置但访问失败: {access_error}，"
                "尝试搜索 Drive 复用或新建...",
                file=sys.stderr,
            )

    # 读取应用 ID
    try:
        creds, _ = load_credentials_data()
        app_id = creds.get("appId", "")
    except Exception as e:
        result["error"] = f"读取 credentials.json 失败: {e}"
        print(json.dumps(result, indent=2, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
    if not app_id:
        result["error"] = "credentials.json 中缺少 appId"
        print(json.dumps(result, indent=2, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)

    client = create_client()

    # settings.json 没有时，尝试在 Drive 中搜索已存在的 Bitable（跨环境复用）
    if not args.force:
        drive_infra = _find_existing_bitable_in_drive(client, app_id)
        if drive_infra:
            _save_infrastructure_settings(settings_path, drive_infra)
            backup_ok, backup_err = _backup_and_strip_local_rt(client, result)
            result["backup_succeeded"] = backup_ok
            result["backup_error"] = backup_err
            result["created"] = False
            result["reason"] = "reused existing Bitable from drive"
            result["infrastructure"] = drive_infra
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return

    # 需要全新创建
    scopes_ok, missing = _check_tenant_scopes(client)
    result["tenant_scopes_ok"] = scopes_ok
    result["missing_scopes"] = sorted(missing)
    if not scopes_ok:
        result["error"] = f"缺少必要的 tenant scope: {', '.join(sorted(missing))}"
        print(json.dumps(result, indent=2, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)

    confirm_action_or_exit(
        "base_create",
        f"确认创建多维表格「{BITABLE_NAME}」用于 refresh_token 云端备份?",
        yes=args.yes,
    )

    try:
        infra, record_id = _create_infrastructure(
            client, app_id, folder_token=args.folder_token
        )
    except Exception as e:
        result["error"] = f"创建基础设施失败: {e}"
        print(json.dumps(result, indent=2, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)

    _save_infrastructure_settings(settings_path, infra)
    backup_ok, backup_err = _backup_and_strip_local_rt(client, result)
    result["backup_succeeded"] = backup_ok
    result["backup_error"] = backup_err

    result["created"] = True
    result["reason"] = "created new Bitable"
    result["infrastructure"] = infra
    print(json.dumps(result, indent=2, ensure_ascii=False))


def _save_infrastructure_settings(settings_path, infra):
    """将 Bitable 基础设施信息写入 settings.json（保留已有字段）。"""
    try:
        settings = load_settings() if settings_path.exists() else {}
    except Exception:
        settings = {}

    if not settings:
        settings = {"default_identity": "user", "user": {}}

    settings.setdefault("infrastructure", {})["bitable"] = infra
    safe_write_json(settings_path, settings, mode=0o600)


def _backup_and_strip_local_rt(client, result):
    """把当前 credentials.json 中的 refresh_token 追加到 Bitable 并清理本地字段。

    Returns:
        (backup_succeeded: bool, backup_error: str or None)
    """
    try:
        creds, _ = load_credentials_data()
    except Exception as e:
        print(f"读取凭证失败（非关键）: {e}", file=sys.stderr)
        return False, str(e)

    # 需要先重新创建 client，让它能读到刚写入的 Bitable 基础设施配置。
    client = create_client()
    backup_ok, backup_err = _backup_current_refresh_token(client, creds)

    # 云模式下迁移完成后，清理 credentials.json 中的本地 refresh_token
    if backup_ok:
        stripped, strip_err = _strip_local_refresh_token(creds)
        result["local_refresh_token_stripped"] = stripped
        result["local_refresh_token_strip_error"] = strip_err
    return backup_ok, backup_err


if __name__ == "__main__":
    cli_run(main)
