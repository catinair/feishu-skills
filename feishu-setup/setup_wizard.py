#!/usr/bin/env python3
"""
setup_wizard.py -- 飞书 Skills 一键配置向导

串联凭证写入 → OAuth 授权 → 权限同步 → 风险策略生成 → 验证，
用户只需提供 appId + appSecret，其余全自动。

用法：
    python3 feishu-setup/setup_wizard.py --app-id cli_xxx --app-secret yyy
    python3 feishu-setup/setup_wizard.py                    # 交互式输入
    python3 feishu-setup/setup_wizard.py --app-id cli_xxx   # app-secret 交互输入
    python3 feishu-setup/setup_wizard.py --check            # 仅检测环境，不配置
    python3 feishu-setup/setup_wizard.py --redirect-uri http://localhost:19876/callback

前置条件（用户需手动完成）：
    1. 在飞书开放平台创建自建应用
    2. 开通所需权限（运行 setup_check.py --suggest-scopes 查看推荐列表）
    3. 配置重定向 URL（默认 http://localhost:8080/callback）
"""

import argparse
import getpass
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from feishu_common._config_loader import (
    resolve_config_path,
    safe_write_json,
)
from feishu_common import write_default_risk_policy


def _validate_app_id(app_id: str) -> bool:
    """验证 App ID 格式"""
    if not app_id.startswith("cli_"):
        print(f"错误: App ID 应以 'cli_' 开头，当前值: {app_id}", file=sys.stderr)
        return False
    if len(app_id) < 10:
        print(f"错误: App ID 长度异常: {app_id}", file=sys.stderr)
        return False
    return True


def _write_credentials(app_id: str, app_secret: str) -> Path:
    """写入 credentials.json，返回写入路径"""
    creds_path = resolve_config_path("credentials.json", for_write=True)
    creds = {
        "appId": app_id,
        "appSecret": app_secret,
        "brand": "feishu",
    }
    safe_write_json(creds_path, creds, mode=0o600)
    print(f"凭证已写入: {creds_path}")
    return creds_path


def _run_auth(redirect_uri: str) -> bool:
    """调用 auth_get_user_token.py 完成 OAuth 授权"""
    auth_script = Path(__file__).parent.parent / "feishu-auth" / "auth_get_user_token.py"
    if not auth_script.exists():
        print(f"错误: 找不到授权脚本: {auth_script}", file=sys.stderr)
        return False

    cmd = [
        sys.executable,
        str(auth_script),
        "--redirect-uri", redirect_uri,
        "--auto-callback",
    ]

    print()
    print("=" * 50)
    print("启动 OAuth 授权流程")
    print("=" * 50)
    print(f"授权脚本: {auth_script}")
    print(f"重定向地址: {redirect_uri}")
    print()
    print("脚本将自动：")
    print("  1. 生成授权链接并保存到配置目录")
    print("  2. 启动本地回调服务等待浏览器跳转")
    print("  3. 换取 token 并保存")
    print("  4. 自动写入 settings.json（用户信息）")
    print("  5. 自动同步 permissions.json（权限清单）")
    print("  6. 自动生成 risk_policy.json（风险策略）")
    print()

    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode == 0
    except KeyboardInterrupt:
        print("\n授权已取消。", file=sys.stderr)
        return False
    except Exception as e:
        print(f"\n授权脚本执行失败: {e}", file=sys.stderr)
        return False


def _run_check(fix: bool = False) -> dict:
    """运行 setup_check.py 获取最终状态。fix=True 时自动修复可修复项。"""
    check_script = Path(__file__).parent / "setup_check.py"
    cmd = [sys.executable, str(check_script), "--json"]
    if fix:
        cmd.append("--fix")
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
    except Exception:
        pass
    return {}


def _ensure_risk_policy():
    """在 skip-auth 等场景下补写默认风险策略。"""
    if write_default_risk_policy():
        print("  已自动生成默认 risk_policy.json")


def main():
    parser = argparse.ArgumentParser(
        description="飞书 Skills 一键配置向导",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
示例:
  %(prog)s --app-id cli_xxx --app-secret yyy
  %(prog)s                          # 交互式输入
  %(prog)s --check                  # 仅检测环境
  %(prog)s --suggest-scopes         # 输出推荐 scope 列表
""",
    )
    parser.add_argument("--app-id", help="飞书应用 App ID（cli_ 开头）")
    parser.add_argument("--app-secret", help="飞书应用 App Secret")
    parser.add_argument("--redirect-uri", default="http://localhost:8080/callback",
                        help="OAuth 重定向 URL（默认 http://localhost:8080/callback）")
    parser.add_argument("--check", action="store_true", help="仅检测环境状态，不执行配置")
    parser.add_argument("--suggest-scopes", action="store_true", help="输出推荐 scope 列表")
    parser.add_argument("--skip-auth", action="store_true",
                        help="仅写入凭证，不启动 OAuth（用于已授权场景）")
    args = parser.parse_args()

    # --suggest-scopes 委托给 setup_check.py
    if args.suggest_scopes:
        check_script = Path(__file__).parent / "setup_check.py"
        subprocess.run([sys.executable, str(check_script), "--suggest-scopes"])
        return

    # --check 模式
    if args.check:
        check_script = Path(__file__).parent / "setup_check.py"
        subprocess.run([sys.executable, str(check_script)])
        return

    # 获取凭证
    app_id = args.app_id
    app_secret = args.app_secret

    if not app_id:
        app_id = input("请输入 App ID（cli_ 开头）: ").strip()
    if not app_id:
        print("错误: 未提供 App ID", file=sys.stderr)
        sys.exit(1)

    if not _validate_app_id(app_id):
        sys.exit(1)

    if not app_secret:
        app_secret = getpass.getpass("请输入 App Secret（输入不可见）: ").strip()
    if not app_secret:
        print("错误: 未提供 App Secret", file=sys.stderr)
        sys.exit(1)

    # 写入凭证
    print()
    print("步骤 1/3: 写入凭证")
    _write_credentials(app_id, app_secret)

    if args.skip_auth:
        print()
        print("已跳过 OAuth 授权（--skip-auth）。")
        _ensure_risk_policy()
        print("如需授权，请运行: python3 feishu-auth/auth_get_user_token.py")
        return

    # OAuth 授权
    print()
    print("步骤 2/3: OAuth 授权")
    print()
    print("请确保已完成以下操作：")
    print(f"  1. 在飞书开放平台 → 安全设置 → 重定向 URL 中配置: {args.redirect_uri}")
    print("  2. 已开通所需权限（运行 setup_check.py --suggest-scopes 查看推荐列表）")
    print()
    input("准备好了按回车继续...")

    auth_ok = _run_auth(args.redirect_uri)

    # 验证（先尝试自动修复 risk_policy 等可修复项）
    print()
    print("步骤 3/3: 验证配置")
    report = _run_check(fix=True)

    print()
    print("=" * 50)
    if report.get("all_ready"):
        print("配置完成！所有检查通过。")
        scope_count = len(report.get("user_token_scopes", []))
        identity = report.get("default_identity", "user")
        print(f"  用户身份: {identity}")
        print(f"  已授权 scope: {scope_count} 个")
        print()
        print("现在可以正常使用了。例如：")
        print("  python3 feishu-im/im_list_chats.py")
        print("  python3 feishu-doc/doc_create.py --title \"测试文档\"")
        print("  python3 feishu-contact/contact_colleagues.py")
    elif auth_ok:
        print("OAuth 授权完成，但部分检查未通过：")
        for r in report.get("recommendations", []):
            print(f"  - {r}")
        print()
        print("运行以下命令查看详细状态：")
        print("  python3 feishu-setup/setup_check.py")
    else:
        print("配置未完成。")
        print()
        print("如需重新配置，再次运行本脚本即可。")
        print("如遇问题，运行以下命令查看详细状态：")
        print("  python3 feishu-setup/setup_check.py")
    print("=" * 50)


if __name__ == "__main__":
    main()
