#!/usr/bin/env python3
"""
auth_sync_permissions.py -- 从飞书开放平台同步当前应用已开通权限

默认行为：
    - 使用 tenant_access_token 调用 application/v6/scopes
    - 刷新目标文件中的 tenant scopes
    - 默认从 credentials.json 读取 user scopes（以 OAuth 授权结果为准）

典型用法：
    python3 feishu-auth/auth_sync_permissions.py
    python3 feishu-auth/auth_sync_permissions.py --replace-user-from <凭证文件路径>

说明：
    application/v6/scopes 官方接口当前可直接查询应用已开通的 tenant scopes。
    user scopes 的官方自动查询能力在本仓库里尚未统一接入，因此脚本默认保留目标文件现有的 user scopes，
    也支持从另一个 JSON 文件覆盖 user scopes。
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from feishu_common import cli_run, create_client
from feishu_common._config_loader import (
    resolve_config_path,
    load_credentials_data,
    safe_write_json,
)
from feishu_common._endpoint_registry import ADMIN_APPROVAL_SCOPES


SCOPES_API_PATH = "/open-apis/application/v6/scopes"


def _resolve_credentials_read_path():
    """解析默认凭证读取路径，支持平台运行时路径 fallback 到 skill-root。"""
    try:
        data, resolved_path = load_credentials_data()
        return resolved_path
    except Exception:
        return resolve_config_path("credentials.json")


def _load_scope_file(path):
    if not path.exists():
        return {"scopes": {"tenant": [], "user": []}}
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    scopes = data.get("scopes", {})
    return {
        "scopes": {
            "tenant": sorted(set(scopes.get("tenant", []))),
            "user": sorted(set(scopes.get("user", []))),
        }
    }


def _load_user_scopes_from_credentials(path):
    if path is None:
        return []
    path = Path(path)
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return sorted(set(data.get("userScopes", [])))


def _normalize_path(path_str):
    path = Path(path_str)
    if not path.is_absolute():
        path = Path(__file__).parent.parent / path
    return path


def fetch_tenant_scopes(client):
    # application/v6/scopes 是内部管理接口，已在 ENDPOINT_REGISTRY 注册为 APP_ONLY
    data = client._request("GET", SCOPES_API_PATH, method_name="application_scopes")
    items = data.get("scopes", [])
    tenant_scopes = []
    for item in items:
        if item.get("scope_type") != "tenant":
            continue
        if item.get("grant_status") != 1:
            continue
        scope_name = item.get("scope_name")
        if scope_name:
            tenant_scopes.append(scope_name)
    return sorted(set(tenant_scopes))


def build_permissions_payload(tenant_scopes, existing_user_scopes):
    tenant_set = set(tenant_scopes)
    user_set = set(existing_user_scopes)
    all_declared = tenant_set | user_set
    admin_approval = sorted(all_declared & ADMIN_APPROVAL_SCOPES)
    return {
        "scopes": {
            "tenant": sorted(tenant_set),
            "user": sorted(user_set),
        },
        "admin_approval_scopes": admin_approval,
    }


def main():
    parser = argparse.ArgumentParser(description="同步当前应用已开通权限到 JSON 文件")
    parser.add_argument(
        "--target",
        default=None,
        help="输出文件路径，默认使用运行时配置目录的 permissions.json",
    )
    parser.add_argument(
        "--credentials",
        default=None,
        help="凭证文件路径，默认使用运行时配置目录的 credentials.json",
    )
    parser.add_argument(
        "--replace-user-from",
        help="从另一个 permissions JSON 文件覆盖 user scopes；不传则保留目标文件现有 user scopes",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="只输出结果到 stdout，不写入文件",
    )
    args = parser.parse_args()

    target_path = _normalize_path(args.target) if args.target else resolve_config_path("permissions.json", for_write=True)
    credentials_path = _normalize_path(args.credentials) if args.credentials else _resolve_credentials_read_path()
    source_data = _load_scope_file(target_path)

    if args.replace_user_from:
        user_source_path = _normalize_path(args.replace_user_from)
        cred_scopes = _load_user_scopes_from_credentials(user_source_path)
        if cred_scopes:
            source_data["scopes"]["user"] = cred_scopes
        else:
            source_data = _load_scope_file(user_source_path)
    else:
        source_data["scopes"]["user"] = _load_user_scopes_from_credentials(credentials_path)

    client = create_client(str(credentials_path))
    tenant_scopes = fetch_tenant_scopes(client)
    payload = build_permissions_payload(tenant_scopes, source_data["scopes"]["user"])

    if args.stdout:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return

    safe_write_json(target_path, payload)
    print(
        json.dumps(
            {
                "updated": True,
                "target": str(target_path),
                "tenant_scopes": len(payload["scopes"]["tenant"]),
                "user_scopes": len(payload["scopes"]["user"]),
                "user_source": args.replace_user_from or "preserve-target",
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    cli_run(main)
