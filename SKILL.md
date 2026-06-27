---
name: feishu-skills
version: 1.0.0
description: |
  飞书 Skill 集合：文档(docx)、电子表格(sheet)、云空间(drive)、IM、知识库(wiki)、
  多维表格(base/bitable)、任务(task)、日程(calendar)、通讯录(contact)、妙记(minutes)、
  权限(perm)、幻灯片(slides)。
  纯 Python 标准库（Pillow 可选，用于画板图片裁剪）。提供单操作 CLI 与组合型 Shortcut。
metadata:
  requires:
    bins: ["python3"]
    files:
      [
        "config/credentials.json",
        "config/settings.json",
        "config/permissions.json",
        "config/risk_policy.json",
        "feishu_common/__init__.py",
        "feishu_common/_client.py",
        "feishu_common/_client_core.py",
        "feishu_common/_config_loader.py",
        "feishu-setup/setup_check.py"
      ]
---

# 飞书 Skill 集合

## 定位

这是一个按飞书能力域拆分的 skill 项目：

- `feishu-*`：单操作 CLI
- `shortcuts/`：组合工作流
- `feishu_common/`：共享运行时代码

## 能力概览

| 领域 | 目录 | 核心能力 |
|------|------|---------|
| 多维表格 | `feishu-base` | 表/字段/视图/记录 CRUD、批量操作、CSV 工作流 |
| 云空间 | `feishu-drive` | 搜索、上传下载、复制移动、导出 |
| IM | `feishu-im` | 发消息、建群、群管理、消息检索 |
| 文档 | `feishu-doc` | 创建/读取/写入 docx、导出 Markdown、查看评论 |
| 表格 | `feishu-sheets` | 创建/读取/写入/追加/导出 |
| 知识库 | `feishu-wiki` | 空间与节点操作 |
| 日程 | `feishu-calendar` | 创建/查询/删除日程 |
| 妙记 | `feishu-minutes` | 转写、AI 总结、统计 |
| 通讯录 | `feishu-contact` | 部门查询、人员搜索 |
| 权限 | `feishu-perm` | 协作者管理 |
| 幻灯片 | `feishu-slides` | 媒体上传 |
| 任务 | `feishu-task` | 创建/获取/列取/更新任务、评论读写 |
| 自定义扩展 | `custom` | 用户自定义脚本、子 skill、组合工作流（gitignore，拉取更新不受影响） |

## 意图路由

**执行前必读**：根据用户意图，先读对应子模块的 `SKILL.md`，再执行具体脚本。不要凭记忆猜测脚本用法。

| 用户意图 | 模块 | 脚本 |
|---------|------|------|
| 读取/查看文档内容 | `feishu-doc` | `doc_read.py` / `doc_fetch.py` |
| 查看文档评论 | `feishu-doc` | `doc_comments.py` |
| 创建文档评论 | `feishu-doc` | `doc_comments.py --create-comment` |
| 回复文档评论 | `feishu-doc` | `doc_comments.py --reply-comment` |
| 写入/编辑文档 | `feishu-doc` | `doc_write.py` |
| 创建文档 | `feishu-doc` | `doc_create.py` |
| **导出文档为文件**（PDF/Markdown/DOCX） | **`shortcuts`** | **`shortcut_doc_export.py`** |
| **下载文档到本地**（文本+媒体附件） | **`shortcuts`** | **`shortcut_doc_download.py`** |
| **分析文档结构**（block 树） | **`shortcuts`** | **`shortcut_doc_analyze.py`** |
| **上传 Markdown 为飞书文档** | **`shortcuts`** | **`shortcut_doc_upload_md.py`** |
| **插入图片/文件到文档** | **`shortcuts`** | **`shortcut_doc_media_insert.py`** |
| **向文档指定位置插入内容** | **`shortcuts`** | **`shortcut_doc_insert_at.py`** |
| 读取表格 | `feishu-sheets` | `sheet_read.py` |
| 写入/追加表格 | `feishu-sheets` | `sheet_write.py` / `sheet_append.py` |
| **导出表格为 CSV** | `feishu-sheets` | `sheet_export_csv.py` |
| 查询多维表格记录 | `feishu-base` | `base_query.py` / `base_get.py` |
| 新增/更新/删除多维表格记录 | `feishu-base` | `base_append.py` / `base_update.py` / `base_delete.py` |
| **多维表格导出 CSV** | **`shortcuts`** | **`shortcut_base_export_csv.py`** |
| **CSV 导入多维表格** | **`shortcuts`** | **`shortcut_base_import_csv.py`** |
| **CSV 增量同步到多维表格** | **`shortcuts`** | **`shortcut_base_sync_csv.py`** |
| **克隆多维表格表结构** | **`shortcuts`** | **`shortcut_base_clone_table.py`** |
| 发消息 | `feishu-im` | `im_send_message.py` |
| 建群/群管理 | `feishu-im` | `im_create_chat.py` / `im_chat_*.py` |
| **群富文本通知** | **`shortcuts`** | **`shortcut_notify_group.py`** |
| **上传文件并发送** | **`shortcuts`** | **`shortcut_upload_and_send.py`** |
| 搜索云空间文件 | `feishu-drive` | `drive_search.py` |
| 上传/下载/复制/移动文件 | `feishu-drive` | `drive_upload.py` / `drive_download.py` / `drive_copy.py` / `drive_move.py` |
| **复制文件/文件夹** | **`shortcuts`** | **`shortcut_drive_clone.py`** |
| 创建/查询/删除日程 | `feishu-calendar` | `calendar_create_event.py` / `calendar_list_events.py` |
| **创建日程并通知群** | **`shortcuts`** | **`shortcut_meeting_notify.py`** |
| 知识库节点查询/遍历 | `feishu-wiki` | `wiki_list_nodes.py` / `wiki_list_all_nodes.py` / `wiki_get_node.py` |
| 文档权限管理 | `feishu-perm` | `perm_doc_share.py` / `perm_doc_remove.py` |
| **创建文档并分享到群** | **`shortcuts`** | **`shortcut_share_doc.py`** |
| 妙记转写/总结 | `feishu-minutes` | `minutes_get.py` / `minutes_transcript.py` |
| 通讯录查询 | `feishu-contact` | `contact_search.py` / `contact_get.py` |
| 创建飞书任务 | `feishu-task` | `task_create.py` |
| 获取飞书任务详情 | `feishu-task` | `task_get.py` |
| 列取飞书任务列表 | `feishu-task` | `task_list.py` |
| 更新/完成飞书任务 | `feishu-task` | `task_patch.py` |
| 创建任务评论 | `feishu-task` | `task_comment_create.py` |
| 获取任务评论列表 | `feishu-task` | `task_comment_list.py` |

## 快捷方式一览

`shortcuts/` 下的组合工作流，串联多个单操作完成端到端任务：

| 脚本 | 功能 | 典型场景 |
|------|------|---------|
| `shortcut_doc_export.py` | 导出 docx/sheet/bitable 为文件 | "把这个文档导出为 PDF" |
| `shortcut_doc_download.py` | 下载文档文本+媒体到本地 | "把文档和图片都下载下来" |
| `shortcut_doc_analyze.py` | 获取文档 block 树做结构化分析 | "分析这个文档的结构" |
| `shortcut_doc_upload_md.py` | 上传 Markdown 为飞书文档 | "把这个 md 文件传到飞书" |
| `shortcut_doc_media_insert.py` | 上传媒体并插入文档 | "把这张图片插到文档里" |
| `shortcut_doc_insert_at.py` | 向文档指定 block 插入 Markdown | "在这个单元格/标题下插入内容" |
| `shortcut_share_doc.py` | 创建文档并分享到群/个人 | "建个文档分享到群里" |
| `shortcut_base_export_csv.py` | 多维表格导出 CSV | "把这个表导出成 CSV" |
| `shortcut_base_import_csv.py` | CSV 导入多维表格 | "把这个 CSV 导入到表里" |
| `shortcut_base_sync_csv.py` | CSV 增量同步到多维表格 | "把本地 CSV 同步到飞书表" |
| `shortcut_base_clone_table.py` | 克隆多维表格表结构 | "复制一张表的结构到新表" |
| `shortcut_drive_clone.py` | 复制文件/文件夹 | "把这个文件复制一份" |
| `shortcut_notify_group.py` | 群富文本通知 | "发个通知到群里" |
| `shortcut_upload_and_send.py` | 上传文件并发送 | "把这个文件发给某人" |
| `shortcut_meeting_notify.py` | 创建日程并通知群 | "建个会议通知大家" |

## 子模块文档

| 模块 | 文档 |
|------|------|
| `feishu-base` | `feishu-base/SKILL.md` |
| `feishu-drive` | `feishu-drive/SKILL.md` |
| `feishu-im` | `feishu-im/SKILL.md` |
| `feishu-doc` | `feishu-doc/SKILL.md` |
| `feishu-wiki` | `feishu-wiki/SKILL.md` |
| `feishu-sheets` | `feishu-sheets/SKILL.md` |
| `feishu-minutes` | `feishu-minutes/SKILL.md` |
| `feishu-task` | `feishu-task/SKILL.md` |
| `custom` | `custom/SKILL.md` |

## Skill 目录结构完整性检查

在触发任何飞书操作前，先确认本 skill 的目录结构已完整加载。某些 Agent 平台会异步解压或延迟加载 skill 文件，若关键目录缺失就继续执行，会导致 `ModuleNotFoundError` 或找不到脚本。

### 预期目录结构

```text
feishu-skills/
├── SKILL.md
├── README.md
├── feishu_common/
│   ├── __init__.py
│   ├── _client.py
│   ├── _client_core.py
│   └── _config_loader.py
├── feishu-setup/
│   └── setup_check.py
├── feishu-auth/
├── feishu-base/
├── feishu-calendar/
├── feishu-contact/
├── feishu-doc/
├── feishu-drive/
├── feishu-im/
├── feishu-minutes/
├── feishu-perm/
├── feishu-sheets/
├── feishu-slides/
├── feishu-task/
├── feishu-wiki/
├── shortcuts/
├── config/
│   └── credentials.example.json
├── docs/
└── reference/
```

### 检查行为

执行任何具体脚本前，先检查以下关键路径是否存在：

- `feishu_common/__init__.py`
- `feishu_common/_client.py`
- `feishu_common/_client_core.py`
- `feishu_common/_config_loader.py`
- `feishu-setup/setup_check.py`

**若上述任一文件缺失**，说明 skill 尚未加载完成，必须：

1. **停止执行当前请求**；
2. 明确告知用户："检测到 feishu-skills 目录结构不完整，可能存在 skill 加载延迟或加载失败，请等待 skill 完全加载后再试。"
3. 不要尝试用残缺文件继续运行脚本，也不要让用户反复重试同一命令。

可通过以下命令快速验证：

```bash
python3 feishu-setup/setup_verify_structure.py
```

## 首次配置检查

本 skill 被触发时，**先检查配置是否就绪，仅在缺失时引导用户完成配置**。已配置好的环境不要重复提示。

### 快速检测

运行环境检测脚本获取完整状态：

```bash
python3 feishu-setup/setup_check.py
```

输出中 `all_ready: true` 表示配置就绪，否则 `missing` 字段列出缺失项。

### 完整引导

新用户或配置不完整时，参考 `feishu-setup/SKILL.md` 进行分步引导，覆盖：

0. 飞书开放平台应用创建
1. 应用权限开通
2. 重定向 URL 配置
3. 凭证填写
4. OAuth 用户授权（v2 流程）
5. 权限同步
6. 风险策略配置
7. 验证测试

### 检查顺序（快速版）

1. **凭证 + 用户授权**（必须）：运行 `python3 feishu-setup/setup_check.py`，检查 `credentials_valid` 和 `user_token_ready`
   - 缺失时：引导用户提供 appId + appSecret，通过 resolver 写入凭证文件（平台环境自动写入 `runtime_credentials/feishu-skills/`，本地写入 `config/`），然后运行 `python3 feishu-auth/auth_get_user_token.py` 完成 OAuth 授权
   - OAuth 成功后自动创建 settings.json（用户信息）和 permissions.json（权限清单），无需手动维护
   - 已存在：跳过

2. **信任文件夹**（user 模式可选，tenant 模式必须）：检查 `risk_policy.json` 中 `workspace.trusted_folder_tokens` 是否有至少一项
   - 缺失时：提示用户在飞书云空间中找到目标文件夹，从 URL 中提取 token 填入
   - 已存在：跳过

### 行为规则

- 三项全部就绪 → **直接执行用户请求，不提配置**
- 任一缺失 → **仅提示缺失项，就地引导补全，补全后继续执行请求**
- 不要一次性列出所有配置要求，按缺失项逐个引导
- 配置写入后立即生效，无需重启

## 说明

本文件只负责 skill 元数据、能力边界与入口索引。
执行规则与风险策略不再在这里重复维护，统一见 `docs/policies.md`。
