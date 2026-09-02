#!/usr/bin/env python3
"""
feishu_common -- 飞书 Skill 公共模块包
纯 Python 标准库（Pillow 可选，用于画板图片裁剪）。
提供 HTTP 客户端、Token 管理、Markdown 转换器等共享能力。
"""

from ._client import FeishuClient, DEFAULT_FOLDER_TOKEN
from ._config_loader import (
    allows_implicit_confirmation,
    default_credentials_path,
    ensure_not_manual_only,
    get_default_folder_token,
    get_permissions_config_path,
    get_risk_policy_path,
    is_manual_only_action,
    is_trusted_chat,
    is_trusted_folder,
    is_trusted_user,
    load_default_identity,
    load_granted_scopes,
    load_permissions_config,
    load_risk_policy,
    load_skill_config,
    load_settings,
    load_user_config,
    prompt_for_confirmation,
    prompt_for_strong_confirmation,
    requires_confirmation_for_action,
    should_confirm_action,
    default_risk_policy,
    write_default_risk_policy,
)
from ._custom_loader import load_custom_skills, list_custom_scripts, list_custom_skills
from ._docx_converter import BlockToMarkdownConverter, MediaExtractor
from ._shared import (
    print_json,
    extract_doc_id,
    extract_base_info,
    cli_run,
    confirm_action_or_exit,
    create_client,
    lookup_contact,
    log_config_paths,
)
