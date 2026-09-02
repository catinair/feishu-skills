#!/usr/bin/env python3
"""
perm_bitable_private.py -- 将多维表格设为私有（关闭外链、外部访问）

用于把存储 refresh_token 等敏感数据的 Bitable 限制为仅所有者/应用可管理，
避免组织内其他成员通过链接或搜索访问。

用法:
  python3 feishu-perm/perm_bitable_private.py --app-token VuvbXxxxxx
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from feishu_common import cli_run, create_client, print_json, confirm_action_or_exit
import argparse


def main():
    parser = argparse.ArgumentParser(description="将多维表格设为私有")
    parser.add_argument("--app-token", required=True, help="多维表格 app_token")
    parser.add_argument("--yes", "-y", action="store_true", help="跳过确认")
    parser.add_argument("--raw", action="store_true", help="输出完整原始 JSON")
    args = parser.parse_args()

    confirm_action_or_exit(
        "perm_bitable_private",
        f"确认将多维表格 {args.app_token} 设为私有（关闭外链/外部访问）？",
        yes=args.yes,
    )

    client = create_client()
    result = client._request(
        "PATCH",
        f"/open-apis/drive/v1/permissions/{args.app_token}/public",
        query={"type": "bitable"},
        body={
            "external_access": False,
            "link_share_entity": "closed",
            "security_entity": "only_full_access",
        },
        use_user_token=False,
        method_name="drive_permission_patch",
    )

    if args.raw:
        print_json(result)
        return

    permission = result.get("permission_public", {}) if isinstance(result, dict) else {}
    print_json({
        "status": "ok",
        "app_token": args.app_token,
        "external_access": permission.get("external_access"),
        "link_share_entity": permission.get("link_share_entity"),
        "security_entity": permission.get("security_entity"),
    })


if __name__ == "__main__":
    cli_run(main)
