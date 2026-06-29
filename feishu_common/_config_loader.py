#!/usr/bin/env python3
"""
_config_loader.py -- feishu-skills 配置与策略统一加载入口

支持本地开发与平台运行时两种模式：
- 本地：配置存放在 <skill-root>/config/
- 部分 Agent 平台：skill 目录可能每会话重建，配置优先存放在
  <workspace>/runtime_assets/<skill-name>/，实现跨会话持久化

可通过环境变量 FEISHU_CONFIG_DIR 显式覆盖配置目录。
"""

import json
import os
import sys
import tempfile
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BRAND = "feishu"

# 环境变量名：显式指定配置目录（本地调试或平台注入）
FEISHU_CONFIG_DIR_ENV = "FEISHU_CONFIG_DIR"


def _deep_merge(base, override):
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _compute_default_config_path(filename):
    """计算默认配置路径（不考虑运行时 fallback），仅用于初始化模块常量。"""
    env_dir = os.environ.get(FEISHU_CONFIG_DIR_ENV)
    if env_dir:
        return Path(env_dir) / filename
    return SKILL_ROOT / "config" / filename


# 模块级常量：基于导入时的环境计算，保持向后兼容。
# 内部函数优先使用 resolve_config_path() 做动态解析；这些常量主要供测试 patch 使用。
CONFIG_DIR = _compute_default_config_path("")
SETTINGS_FILE = _compute_default_config_path("settings.json")
CREDENTIALS_FILE = _compute_default_config_path("credentials.json")
PERMISSIONS_FILE = _compute_default_config_path("permissions.json")
RISK_POLICY_FILE = _compute_default_config_path("risk_policy.json")


def skill_root():
    return SKILL_ROOT


def _detect_platform_workspace():
    """探测平台 workspace 根目录。

    判断依据：skill 根目录位于 /home/user/workspace/skills/<skill-name>/ 下，
    且 workspace 可写。限定 /home/user/workspace 是为了避免本地开发目录
    （如 ~/.cc-switch/skills/）因恰好包含 skills 目录而被误判为平台环境。

    其他平台可通过 FEISHU_CONFIG_DIR 环境变量显式指定配置目录。
    """
    try:
        # 环境变量门控：必须有平台标记才继续检测
        if not (os.getenv("OPENCODE") or os.getenv("OPENCODE_CONFIG_DIR")):
            return None
        skill_root_resolved = SKILL_ROOT.resolve()
        parent = skill_root_resolved.parent
        if parent.name != "skills":
            return None
        workspace = parent.parent
        # 限定已知平台 workspace 路径，避免本地目录误触发
        if str(workspace) != "/home/user/workspace":
            return None
        if not workspace.exists() or not workspace.is_dir():
            return None
        if not os.access(str(workspace), os.W_OK):
            return None
        return workspace
    except Exception:
        return None


# 旧目录名（2026-06 之前），迁移后保留常量绑定兼容
_LEGACY_RUNTIME_DIR_NAME = "runtime_credentials"
_RUNTIME_DIR_NAME = "runtime_assets"


def _migrate_legacy_runtime_dir(workspace):
    """自动迁移旧路径 runtime_credentials -> runtime_assets。

    仅当旧目录存在且新目录尚不存在时执行 os.rename() 迁移。
    迁移失败时返回旧路径，确保已有数据不丢失。
    """
    legacy_dir = workspace / _LEGACY_RUNTIME_DIR_NAME / SKILL_ROOT.name
    new_dir = workspace / _RUNTIME_DIR_NAME / SKILL_ROOT.name
    if not legacy_dir.exists():
        return new_dir
    if new_dir.exists():
        return new_dir
    try:
        new_dir.parent.mkdir(parents=True, exist_ok=True)
        os.rename(str(legacy_dir), str(new_dir))
    except OSError:
        # 迁移失败，返回旧路径确保已有数据可读
        return legacy_dir
    return new_dir


def get_runtime_config_dir():
    """返回平台运行时配置目录；非平台环境返回 None。"""
    workspace = _detect_platform_workspace()
    if not workspace:
        return None
    # 自动尝试迁移旧路径
    return _migrate_legacy_runtime_dir(workspace)


def get_config_dir(*, for_write=False):
    """返回当前应使用的配置目录。

    优先级：
    1. FEISHU_CONFIG_DIR 环境变量
    2. 平台运行时目录（平台环境下 for_write=True 时会自动创建）
    3. <skill-root>/config/
    """
    env_dir = os.environ.get(FEISHU_CONFIG_DIR_ENV)
    if env_dir:
        return Path(env_dir)

    runtime_dir = get_runtime_config_dir()
    if runtime_dir:
        if for_write:
            runtime_dir.mkdir(parents=True, exist_ok=True)
            return runtime_dir
        return runtime_dir

    return SKILL_ROOT / "config"


def resolve_config_path(filename, *, for_write=False):
    """解析单个配置文件路径，读操作支持运行时 -> skill-root 的 fallback。

    Args:
        filename: 配置文件名，如 "credentials.json"
        for_write: 是否为写操作；写操作会优先使用平台运行时目录并自动创建
    """
    env_dir = os.environ.get(FEISHU_CONFIG_DIR_ENV)
    if env_dir:
        return Path(env_dir) / filename

    # 向后兼容：测试代码会 patch 下面这些模块级常量
    constant_map = {
        "credentials.json": CREDENTIALS_FILE,
        "settings.json": SETTINGS_FILE,
        "permissions.json": PERMISSIONS_FILE,
        "risk_policy.json": RISK_POLICY_FILE,
    }
    default_path = constant_map.get(filename, CONFIG_DIR / filename)

    if for_write:
        runtime_dir = get_runtime_config_dir()
        if runtime_dir:
            runtime_dir.mkdir(parents=True, exist_ok=True)
            return runtime_dir / filename
        return default_path

    # 读操作：优先运行时文件，不存在则尝试旧路径，都不存在则回退到模块常量
    runtime_dir = get_runtime_config_dir()
    if runtime_dir:
        runtime_path = runtime_dir / filename
        if runtime_path.exists():
            return runtime_path

        # 迁移失败或旧路径仍有数据时，回退读取
        workspace = _detect_platform_workspace()
        if workspace:
            legacy_dir = workspace / _LEGACY_RUNTIME_DIR_NAME / SKILL_ROOT.name
            legacy_path = legacy_dir / filename
            if legacy_path.exists():
                return legacy_path

    return default_path


def safe_write_json(path, data, *, mode=0o644):
    """原子写入 JSON 文件，写完后替换原文件。

    对 credentials.json 默认使用 600 权限，其他文件默认 644。
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # 在同一文件系统上创建临时文件，保证 os.replace 原子
    fd, tmp_path = tempfile.mkstemp(
        suffix=".tmp", prefix=path.name + ".", dir=str(path.parent)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.chmod(tmp_path, mode)
        os.replace(tmp_path, path)
    except Exception:
        if Path(tmp_path).exists():
            Path(tmp_path).unlink()
        raise


def resolve_token_cache_path(*, for_write=False):
    """解析 tenant_access_token 缓存文件路径。

    与 resolve_config_path 同一优先级：
    1. FEISHU_CONFIG_DIR 环境变量
    2. 平台 runtime_assets/ 目录
    3. <skill-root>/config/.token_cache.json（本地 fallback）
    """
    return resolve_config_path(".token_cache.json", for_write=for_write)


def default_credentials_path():
    return resolve_config_path("credentials.json")


def get_permissions_config_path():
    return resolve_config_path("permissions.json")


def get_risk_policy_path():
    return resolve_config_path("risk_policy.json")


def load_settings():
    settings = {"brand": DEFAULT_BRAND}
    path = resolve_config_path("settings.json")
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            settings = _deep_merge(settings, json.load(f))
    return settings


def load_skill_config():
    """Backward-compatible alias for the historical config loader name."""
    return load_settings()


def load_user_config():
    """从 settings.json 加载使用者身份信息。

    返回 settings.user 字段，未配置时返回空 dict。
    """
    settings = load_settings()
    return settings.get("user", {})


def load_default_identity():
    """从 settings.json 获取默认身份类型。

    返回 "tenant" 或 "user"，未配置时返回 "user"。
    """
    settings = load_settings()
    return settings.get("default_identity", "user")


def load_granted_scopes():
    """从 permissions.json 获取已授权的 scopes。

    返回 {"tenant": set([...]), "user": set([...])}。
    文件不存在或缺少字段时返回空 set。
    """
    perms = load_permissions_config()
    scopes = perms.get("scopes", {})
    return {
        "tenant": set(scopes.get("tenant", [])),
        "user": set(scopes.get("user", [])),
    }


def load_permissions_config():
    path = resolve_config_path("permissions.json")
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_risk_policy():
    path = resolve_config_path("risk_policy.json")
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def default_risk_policy():
    """user 模式下的最小默认风险策略。

    当 default_identity 为 user 且未配置 risk_policy.json 时自动生成，
    使用户无需手动维护即可开箱即用。
    """
    return {
        "workspace": {"trusted_folder_tokens": []},
        "messaging": {"trusted_users": [], "trusted_chats": []},
        "writes": {
            "allow_without_confirmation": [
                {"action": "doc_create"},
                {"action": "sheet_create"},
                {"action": "base_create"},
            ],
            "always_confirm_actions": [],
            "manual_only_actions": ["drive_delete", "base_batch_delete"],
        },
    }


def write_default_risk_policy():
    """写入默认 risk_policy.json，仅当文件不存在时创建。"""
    path = resolve_config_path("risk_policy.json", for_write=True)
    if path.exists():
        return False
    safe_write_json(path, default_risk_policy(), mode=0o600)
    return True


def get_default_folder_token():
    """从 risk_policy.json 获取默认文件夹 token。

    优先返回标记为 default 的 trusted_folder_token，
    其次返回列表第一项，都没有则抛出 RuntimeError。
    """
    policy = load_risk_policy()
    workspace = policy.get("workspace", {})
    for item in workspace.get("trusted_folder_tokens", []):
        if item.get("default") and item.get("token"):
            return item["token"]
    tokens = workspace.get("trusted_folder_tokens", [])
    if tokens and tokens[0].get("token"):
        return tokens[0]["token"]
    raise RuntimeError(
        "No default folder token configured. "
        "Set workspace.trusted_folder_tokens in config/risk_policy.json"
    )


def trusted_folder_tokens():
    workspace = load_risk_policy().get("workspace", {})
    return {item.get("token") for item in workspace.get("trusted_folder_tokens", []) if item.get("token")}


def trusted_user_ids():
    messaging = load_risk_policy().get("messaging", {})
    return {item.get("user_id") for item in messaging.get("trusted_users", []) if item.get("user_id")}


def trusted_chat_ids():
    messaging = load_risk_policy().get("messaging", {})
    return {item.get("chat_id") for item in messaging.get("trusted_chats", []) if item.get("chat_id")}


def is_trusted_folder(folder_token):
    return folder_token in trusted_folder_tokens()


def is_trusted_user(user_id):
    return user_id in trusted_user_ids()


def is_trusted_chat(chat_id):
    return chat_id in trusted_chat_ids()


def requires_confirmation_for_action(action_name):
    writes = load_risk_policy().get("writes", {})
    always_confirm = set(writes.get("always_confirm_actions", []))
    return action_name in always_confirm


def is_manual_only_action(action_name):
    writes = load_risk_policy().get("writes", {})
    manual_only = set(writes.get("manual_only_actions", []))
    return action_name in manual_only


def allows_implicit_confirmation(action_name, is_trusted=False):
    writes = load_risk_policy().get("writes", {})
    for item in writes.get("allow_without_confirmation", []):
        if item.get("action") != action_name:
            continue
        if item.get("within_trusted_folder_only"):
            return is_trusted
        return True
    return False


def should_confirm_action(action_name, is_trusted=False, identity=None):
    """判断是否需要用户确认。

    Args:
        action_name: 操作名称
        is_trusted: 目标是否在信任范围内
        identity: 当前身份 "user" 或 "tenant"，None 时从 settings.json 读取
    """
    if identity is None:
        identity = load_default_identity()

    # user 模式下，如果没有 risk_policy.json，用户自身权限即信任边界，不需额外确认
    path = resolve_config_path("risk_policy.json")
    if identity == "user" and not path.exists():
        return False

    if is_manual_only_action(action_name):
        return True
    if requires_confirmation_for_action(action_name):
        return True
    if allows_implicit_confirmation(action_name, is_trusted=is_trusted):
        return False
    return True


def ensure_not_manual_only(action_name):
    if is_manual_only_action(action_name):
        raise RuntimeError(
            f"'{action_name}' 被标记为手动优先操作，当前仓库不建议通过脚本一键执行。\n"
            "请优先引导用户在飞书界面或受控人工流程中完成。"
        )


def prompt_for_confirmation(message):
    print(message, file=sys.stderr)
    resp = input("确认继续? [y/N]: ")
    return resp.strip().lower() in ("y", "yes")


def prompt_for_strong_confirmation(message):
    """强确认：要求用户输入大写 YES 才能继续。

    用于 manual_only 等高风险操作，避免误触普通 y/yes 确认。
    """
    print(message, file=sys.stderr)
    print("此操作被标记为手动优先 / 高风险，如需继续请输入 YES（大写）:", file=sys.stderr)
    resp = input().strip()
    return resp == "YES"


def load_credentials_data(credentials_path=None):
    if credentials_path:
        path = Path(credentials_path)
    else:
        path = resolve_config_path("credentials.json")
    if not path.is_absolute():
        path = SKILL_ROOT / path

    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f), path

    app_id = os.environ.get("FEISHU_APP_ID")
    app_secret = os.environ.get("FEISHU_APP_SECRET")
    if app_id and app_secret:
        return (
            {
                "appId": app_id,
                "appSecret": app_secret,
                "brand": os.environ.get("FEISHU_BRAND", DEFAULT_BRAND),
                "userAccessToken": os.environ.get("FEISHU_USER_ACCESS_TOKEN", ""),
            },
            None,
        )

    raise RuntimeError(
        f"Credentials file not found: {path}\n"
        "请先运行 setup 或设置环境变量 FEISHU_APP_ID / FEISHU_APP_SECRET"
    )


try:
    DEFAULT_FOLDER_TOKEN = get_default_folder_token()
except Exception:
    DEFAULT_FOLDER_TOKEN = ""
