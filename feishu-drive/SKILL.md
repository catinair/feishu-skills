---
name: feishu-drive
version: 1.2.0
description: |
  飞书云空间技能：搜索、列出、复制、下载、上传、移动、删除文件、导出文档。
  纯 Python 标准库（Pillow 可选，用于画板图片裁剪）。
metadata:
  requires:
    bins: ["python3"]
    files: ["feishu-drive/drive_search.py", "feishu-drive/drive_list.py", "feishu-drive/drive_copy.py", "feishu-drive/drive_download.py", "feishu-drive/drive_upload.py", "feishu-drive/drive_move.py", "feishu-drive/drive_delete.py", "feishu-drive/drive_create_folder.py", "feishu-drive/drive_export.py", "config/credentials.json"]
---

# feishu-drive -- 飞书云空间技能

## 权限要求

> **说明**：以下标注的审批要求基于常见企业配置。实际是否需要管理员审批，取决于你所在企业管理员在「飞书开放平台 → 自建应用审核规则」中的设置。

| 脚本 | 所需权限 | 审批说明 |
|------|---------|----------|
| drive_search.py | `drive:drive.search:readonly` | 一般无需管理员审批 |
| drive_list.py | `drive:drive.search:readonly` | 一般无需管理员审批 |
| drive_copy.py | `drive:file` | 通常需管理员审批 |
| drive_download.py | `drive:file` / `docs:document.media:download` | 通常需管理员审批 |
| drive_upload.py | `drive:file` | 通常需管理员审批 |
| drive_move.py | `drive:drive` 或 `space:document:move` | 通常需管理员审批 |
| drive_delete.py | `drive:drive` 或 `space:document:delete` | 通常需管理员审批 |
| drive_export.py | `docs:document.content:read` / `docs:document:export` | 一般无需管理员审批 |

> **注意**：
> - `drive:drive` 是高级权限，包含文件的移动、删除、重命名等管理操作，通常需要飞书管理员审批。如需使用 move/delete，请在飞书开放平台申请该权限并联系管理员审批。
> - `drive_export.py` 需要 `docs:document:export` 权限，如遇 `99991672` 权限错误，请在飞书开放平台检查该权限是否已添加。

## 快捷命令

### 按名称搜索文件

```bash
python3 feishu-drive/drive_search.py --query "周报" --folder-token fldcnxxx
```

**注意**：这是按名称过滤，不是全文搜索。全文搜索需要 `search:docs:read`。

### 列出文件夹文件

```bash
# 根目录
python3 feishu-drive/drive_list.py

# 指定文件夹
python3 feishu-drive/drive_list.py --folder-token fldcnxxx
```

### 复制文件

```bash
python3 feishu-drive/drive_copy.py \
  --file-token doxcnxxx \
  --name "副本" \
  --type docx \
  --folder-token fldcnxxx
```

### 下载文件

```bash
# 下载 drive 文件（pdf/xlsx 等）
python3 feishu-drive/drive_download.py --token boxcnxxx --output ./file.pdf --type file

# 下载文档中的媒体
python3 feishu-drive/drive_download.py --token img_v2_xxx --output ./image.png --type media
```

**注意**：docx 文件不能直接用 drive download（会返回 404），请用 `feishu-doc/doc_fetch.py` 导出为 Markdown。

### 上传文件

```bash
# 上传到云空间（默认）
python3 feishu-drive/drive_upload.py --path ./report.pdf --folder-token fldcnxxx

# 上传到多维表格附件空间（用于 Base 附件字段）
python3 feishu-drive/drive_upload.py \
  --path ./report.pdf \
  --parent-type bitable_file \
  --parent-node YOUR_APP_TOKEN
```

**注意**：
- 仅支持单分片小文件上传（< 20MB）。上传成功后返回 `file_token`。
- 用于 Base 附件字段时，`parent_type` 必须为 `bitable_file`，`parent_node` 为目标多维表格的 `app_token`。
- 普通云空间上传（`parent_type=explorer`）的 `file_token` 不能直接用于 Base 附件字段。

### 移动文件

```bash
python3 feishu-drive/drive_move.py \
  --file-token boxcnxxx \
  --type file \
  --target-folder-token fldcnxxx
```

**注意**：需开通 `drive:drive` 或 `space:document:move` 权限。

### 删除文件

```bash
python3 feishu-drive/drive_delete.py --file-token boxcnxxx --type file
```

**注意**：删除操作不可恢复。需开通 `drive:drive` 或 `space:document:delete` 权限。

### 导出文档

```bash
# 导出 docx 为 PDF
python3 feishu-drive/drive_export.py \
  --token doxcnxxx \
  --doc-type docx \
  --file-extension pdf \
  --output ./doc.pdf

# 导出 sheet 为 CSV（需指定 sub-id 即 sheet_id）
python3 feishu-drive/drive_export.py \
  --token shtcnxxx \
  --doc-type sheet \
  --file-extension csv \
  --sub-id 0edxxx \
  --output ./sheet.csv
```

**注意**：
- 导出是异步任务，脚本会自动轮询（默认最多 30 次，间隔 2 秒）
- sheet/bitable 导出 csv 时必须提供 `--sub-id`
- 需开通 `docs:document:export` 权限
