---
name: feishu-doc
version: 1.0.0
description: |
  飞书文档技能：创建、写入、读取、导出飞书文档。
  纯 Python 标准库（Pillow 可选，用于画板图片裁剪）。
metadata:
  requires:
    bins: ["python3"]
    files: ["feishu-doc/doc_token.py", "feishu-doc/doc_create.py", "feishu-doc/doc_write.py", "feishu-doc/doc_read.py", "feishu-doc/doc_fetch.py", "feishu-doc/doc_comments.py", "config/credentials.json"]
---

# feishu-doc -- 飞书文档技能

## 权限要求

| 脚本 | 所需权限 | 状态 |
|------|---------|------|
| doc_token.py | 无 | 已开通 |
| doc_create.py | `docx:document:create` | 已开通 |
| doc_write.py | `docx:document.block:convert` | 已开通 |
| doc_read.py | `docx:document:readonly` | 已开通 |
| doc_fetch.py | `docx:document:readonly` + `docs:document.media:download` | 已开通 |
| doc_comments.py（查看） | `docs:document.comment:read`（或 `docs:doc:readonly` / `drive:drive:readonly`） | 已开通 |
| doc_comments.py（创建） | `docs:document.comment:create`（或 `docs:doc` / `drive:drive`） | 已开通 |
| doc_comments.py（回复） | `docs:document.comment:create`（或 `docs:doc` / `drive:drive`） | 已开通 |

## 输出说明

本模块的写操作类 CLI（如创建、更新、删除等）默认输出精简摘要，便于 AI 消费。如需完整 API 原始响应，请加 `--raw`：

```bash
python3 feishu-doc/doc_create.py --title "测试文档" --raw
```

通用 CLI 约定（`--yes`、`--raw`、`--identity`）详见项目级文档 [`docs/usage.md`](../docs/usage.md)。

## 快捷命令

### 获取 Token

```bash
python3 feishu-doc/doc_token.py
```

输出 tenant_access_token 及其过期时间，用于调试或手动调用 API。注意：当前项目默认身份为 user，此脚本仅用于诊断 tenant token 状态。

### 创建文档

```bash
python3 feishu-doc/doc_create.py --title "会议纪要" --folder-token fldcnxxx
```

### 写入 Markdown（追加模式）

```bash
# 直接写入字符串
python3 feishu-doc/doc_write.py --doc doxcnxxx --markdown "# 标题\n\n正文"

# 从文件写入
python3 feishu-doc/doc_write.py --doc doxcnxxx --markdown-file content.md
```

**注意**：`doc_write.py` 是**追加**内容到文档末尾，不会覆盖已有内容。

### 读取文档 Block 树

```bash
python3 feishu-doc/doc_read.py --doc doxcnxxx
```

### 创建全文评论

```bash
python3 feishu-doc/doc_comments.py --doc doxcnxxx --create-comment "评论内容"
```

### 获取文档评论列表

```bash
# 获取所有评论（人类可读格式）
python3 feishu-doc/doc_comments.py --doc doxcnxxx

# 只获取未解决的评论
python3 feishu-doc/doc_comments.py --doc doxcnxxx --unsolved

# 获取评论（JSON 格式）
python3 feishu-doc/doc_comments.py --doc doxcnxxx --json

# 同时获取表情回复
python3 feishu-doc/doc_comments.py --doc doxcnxxx --reactions
```

输出字段说明：
- `comment_id`：评论 ID
- `user_id`：评论作者用户 ID
- `create_time` / `update_time`：创建/更新时间（秒级时间戳）
- `is_solved`：是否已解决
- `is_whole`：是否为全文评论（false 表示局部划词评论）
- `quote`：局部评论的引用文本
- `reply_list.replies`：回复列表，包含 `content`（富文本内容）、`reply_id`、`user_id` 等
- `reactions`：表情回复（需加 `--reactions`）

### 回复文档评论

```bash
# 回复指定评论
python3 feishu-doc/doc_comments.py --doc doxcnxxx \
  --reply-comment 7639182663504464827 \
  --reply-text "已确认，后续更新到文档中"
```

### 导出文档为 Markdown + 下载媒体

```bash
python3 feishu-doc/doc_fetch.py --doc doxcnxxx --output-dir ./downloads
```

输出：
- `./downloads/document.md` -- 标准 Markdown 内容（图片/文件使用 `![]()` / `[]()` 语法）
- `./downloads/media.json` -- 媒体清单（含下载状态、文档标题）
- `./downloads/media/{filename}.png` -- 下载成功的媒体文件（含画板自动导出为图片）

**支持能力**：
- docx / wiki 链接自动解析（wiki token 失败时自动回退查询 obj_token）
- 画板（board）通过官方 API 导出为 PNG，自动裁剪空白边缘
- 媒体文件名根据 Content-Disposition 自动推断（保留原始文件名和扩展名）
- 标准 Markdown 语法：图片用 `![]()`（URL 填图片路径），文件用 `[]()`（URL 填文件路径）

**媒体下载限制**：
- 可下载：通过 drive 上传后插入文档的媒体（有有效 token）
- 不可下载：通过 convert API 插入的外部 URL 图片（无 token）

## 相关 Shortcut

| 脚本 | 功能 | 场景 |
|------|------|------|
| `shortcuts/shortcut_doc_export.py` | 导出 docx/sheet/bitable 为文件 | 导出为 PDF/Markdown/DOCX |
| `shortcuts/shortcut_doc_download.py` | 下载文档文本+媒体到本地 | 把文档和图片都下载下来 |
| `shortcuts/shortcut_doc_analyze.py` | 获取文档 block 树做结构化分析 | 分析这个文档的结构 |
| `shortcuts/shortcut_doc_upload_md.py` | 上传 Markdown 为飞书文档 | 把这个 md 文件传到飞书 |
| `shortcuts/shortcut_doc_media_insert.py` | 上传媒体并插入文档 | 把这张图片插到文档里 |
| `shortcuts/shortcut_doc_insert_at.py` | 向文档指定 block 插入 Markdown | 在这个单元格/标题下插入内容 |

## 文档类型与 Token

| URL 格式 | Token 类型 | 处理方式 |
|----------|-----------|----------|
| `/docx/doxcnxxx` | document_id | 直接使用 |
| `/doc/doccnxxx` | document_id | 直接使用 |
| `/wiki/wikcnxxx` | wiki_token | `doc_fetch.py` / `shortcut_doc_download.py` 自动回退查询 obj_token |

Wiki 链接在 `doc_fetch.py` 和 `shortcut_doc_download.py` 中已内置自动回退，无需手动查询。
