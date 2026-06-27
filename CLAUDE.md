# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 在本仓库中工作时提供指引。

## 项目概述

飞书 Skill 集合 — 纯 Python 标准库实现（零 pip 依赖），封装飞书开放平台 API 的独立 CLI 脚本集合。每个脚本均可通过 `python3 <script>.py` 独立运行。要求 Python >= 3.9。Pillow 为可选依赖（仅用于画板图片裁剪）。

## 常用命令

```bash
# 运行全部测试
python3 -m pytest tests/ -q

# 运行单个测试文件
python3 -m pytest tests/test_config_loader.py -q

# 运行单个脚本
python3 feishu-im/im_list_chats.py
python3 feishu-doc/doc_create.py --title "测试" --folder-token fldcnxxx

# 环境/配置检查
python3 feishu-setup/setup_check.py          # 人类可读输出
python3 feishu-setup/setup_check.py --json   # JSON 输出
python3 feishu-setup/setup_check.py --fix    # 自动修复缺失的 risk_policy.json

# 验证目录结构完整性
python3 feishu-setup/setup_verify_structure.py
```

无构建步骤、无 linter 配置、无 `requirements.txt`。本项目不是 Python 包，而是扁平的脚本集合。

## 架构

### 脚本模式

每个 CLI 脚本（`feishu-*/*.py`、`shortcuts/*.py`）遵循统一模板：

1. `sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))` 以找到 `feishu_common`
2. 从 `feishu_common` 导入 `create_client`、`print_json`、`cli_run`
3. 定义 `main()` 函数，使用 argparse 解析参数，调用 client 方法，`print_json(result)` 输出
4. 用 `cli_run(main)` 包装，统一错误处理

### 核心运行时 (`feishu_common/`)

- **`_client.py`** — `FeishuClient` 类，通过多重继承组合：`FeishuClientCore` + 12 个领域 mixin（`_client_doc.py`、`_client_drive.py`、`_client_sheets.py`、`_client_wiki.py`、`_client_base.py`、`_client_minutes.py`、`_client_contact.py`、`_client_calendar.py`、`_client_im.py`、`_client_perm.py`、`_client_slides.py`、`_client_task.py`）
- **`_client_core.py`** — HTTP 引擎：Token 管理（tenant + user token 自动刷新）、按端点的身份解析、预检权限检查、分页（`_paginate()`）、中文错误码映射
- **`_endpoint_registry.py`** — ~90 个 API 方法的注册表，声明身份要求（`APP_ONLY`/`USER_ONLY`/`BOTH`）及 tenant/user 所需权限
- **`_config_loader.py`** — 三级配置解析：`FEISHU_CONFIG_DIR` 环境变量 → 平台运行时目录 → `<skill-root>/config/`。处理风险策略、信任验证、确认提示、原子写入
- **`_shared.py`** — CLI 工具函数：`create_client()`、`print_json()`、`extract_doc_id()`、`extract_base_info()`、`cli_run()`、`confirm_action_or_exit()`、`lookup_contact()`
- **`_docx_converter.py`** — Markdown ↔ docx block 转换器
- **`_custom_loader.py`** — 从 `custom/` 目录动态加载自定义 skill
- **`__init__.py`** — 公共 API 表面（重导出脚本所需的一切）

### 目录结构

| 目录 | 用途 |
|------|------|
| `feishu-*/` | 按领域拆分的单操作 CLI（每个目录包含 `SKILL.md` + 操作脚本） |
| `shortcuts/` | 跨领域组合工作流，串联多个操作 |
| `feishu_common/` | 共享运行时库（所有脚本从此导入） |
| `feishu-setup/` | 配置向导与环境检测 |
| `feishu-auth/` | OAuth v2 授权流程与权限同步 |
| `config/` | 机器可读配置（gitignore，仅 `.example.json` 文件入库） |
| `docs/` | 人类可读文档（`architecture.md`、`usage.md`、`policies.md`） |
| `reference/` | 飞书 API 备查资料（非运行时配置） |
| `custom/` | 用户扩展目录（gitignore，上游更新不受影响） |
| `tests/` | 单元测试（16 个文件，基于 pytest） |

### 凭证流程

1. 用户提供 `appId` + `appSecret` → 写入 `config/credentials.json`
2. `feishu-auth/auth_get_user_token.py` 执行 OAuth v2（localhost 回调服务器）→ token + refresh_token 保存到 `credentials.json`
3. `feishu-auth/auth_sync_permissions.py` 同步 tenant 权限到 `config/permissions.json`
4. 运行时，`_client_core.py._resolve_identity()` 根据端点注册表 + 已授权权限 + `settings.json` 的 default_identity 决定每次调用使用 user 还是 app token

### 配置文件（均 gitignore，示例见 `config/*.example.json`）

- `credentials.json` — appId、appSecret、tokens
- `settings.json` — default_identity、用户信息
- `permissions.json` — 已授权权限快照
- `risk_policy.json` — 信任文件夹/用户/群聊、写入确认规则

## 新增 API 方法

1. 新增 API mixin → 加到 `feishu_common/_client_xxx.py`
2. 新增单操作 CLI → 加到对应的 `feishu-*` 目录
3. 新增跨域工作流 → 加到 `shortcuts/`
4. 在 `feishu_common/_endpoint_registry.py` 注册新端点，声明身份和权限要求

## 关键约定

- 所有脚本通过 `print_json()` 输出 JSON — 设计上为机器可读
- 风险策略控制确认提示：信任的文件夹/用户/群聊跳过确认；对非信任目标的写入操作需显式传 `--yes` / `-y` 参数
- 中文错误信息是有意为之（面向目标用户）
- `SKILL.md` 文件是 AI Agent 的主要文档 — 执行脚本前先读对应子模块的 `SKILL.md`
- `custom/` 是用户脚本的扩展入口 — 已 gitignore，`git pull` 更新不会冲突
