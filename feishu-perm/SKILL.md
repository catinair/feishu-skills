---
name: feishu-perm
version: 1.0.0
description: |
  飞书文档/云空间权限管理。给文档、表格、多维表格添加/移除协作者，查询现有权限。
  纯 Python 标准库（Pillow 可选，用于画板图片裁剪）。
metadata:
  requires:
    bins: ["python3"]
    files: ["feishu-perm/perm_doc_list.py", "feishu-perm/perm_doc_share.py", "feishu-perm/perm_doc_remove.py", "feishu-perm/perm_bitable_private.py", "config/credentials.json"]
---

# feishu-perm -- 飞书权限管理技能

飞书文档/云空间/多维表格权限管理。给文档、表格、多维表格添加/移除协作者，查询现有权限，或将多维表格设为私有。

## 使用场景

- 创建了文档/表格/多维表格后，需要给其他用户开通管理权限
- 查询某个文档当前的分享范围和协作者列表
- 移除不再需要的协作者
- 把存储敏感数据（如 refresh_token）的多维表格设为私有

## 权限要求

| 脚本 | 所需权限 | 状态 |
|------|---------|------|
| perm_doc_list.py | `drive:drive` 或 `docs:document` 相关权限 | 需确认 |
| perm_doc_share.py | `drive:drive` 或 `docs:document` 相关权限 | 需确认 |
| perm_doc_remove.py | `drive:drive` 或 `docs:document` 相关权限 | 需确认 |

## 输出说明

本模块的写操作类 CLI（如创建、更新、删除等）默认输出精简摘要，便于 AI 消费。如需完整 API 原始响应，请加 `--raw`：

```bash
python3 feishu-perm/perm_doc_share.py --token doxcnxxx --type docx --member-id ou_xxx --raw
```

通用 CLI 约定（`--yes`、`--raw`、`--identity`）详见项目级文档 [`docs/usage.md`](../docs/usage.md)。

## 快捷命令

### 列出协作者

```bash
python3 feishu-perm/perm_doc_list.py --token doxcnxxx --type docx

# 多维表格
python3 feishu-perm/perm_doc_list.py --token VuvbXxxxxx --type bitable
```

返回当前文档/多维表格的所有协作者及其权限级别（view/edit/full_access）。

### 添加协作者

```bash
# 给用户查看权限
python3 feishu-perm/perm_doc_share.py --token doxcnxxx --type docx --member-id ou_xxx --member-type openid --perm view

# 给用户编辑权限
python3 feishu-perm/perm_doc_share.py --token doxcnxxx --type docx --member-id ou_xxx --member-type openid --perm edit

# 给群聊编辑权限
python3 feishu-perm/perm_doc_share.py --token doxcnxxx --type docx --member-id oc_xxx --member-type openchat --perm edit

# 给多维表格添加协作者
python3 feishu-perm/perm_doc_share.py --token VuvbXxxxxx --type bitable --member-id ou_xxx --member-type openid --perm view

# 给文件夹添加协作者（需用 tenant 身份）
python3 feishu-perm/perm_doc_share.py --token fldxxxxx --type folder --member-id ou_xxx --member-type openid --perm full_access --identity tenant
```

**参数说明：**
- `--type`: docx / sheet / bitable / file / folder / mindnote / slides
- `--member-type`: openid / union_id / user_id / openchat / department_id
- `--perm`: view（可阅读）/ edit（可编辑）/ full_access（可管理）
- `--identity`: user / tenant，folder 等由应用身份创建的资源需用 tenant 身份授权

### 移除协作者

```bash
python3 feishu-perm/perm_doc_remove.py --token doxcnxxx --type docx --member-id ou_xxx

# 多维表格
python3 feishu-perm/perm_doc_remove.py --token VuvbXxxxxx --type bitable --member-id ou_xxx
```

### 将多维表格设为私有

```bash
python3 feishu-perm/perm_bitable_private.py --app-token VuvbXxxxxx
```

该命令会关闭多维表格的外部访问、链接分享，并将安全相关可见范围限制为仅可管理者访问。
推荐用于存储 `refresh_token` 等敏感数据的 `token_backup` 表。

## 脚本列表

| 脚本 | 功能 | 关键参数 |
|------|------|----------|
| `perm_doc_list.py` | 列出协作者 | `--token`, `--type` |
| `perm_doc_share.py` | 添加协作者 | `--token`, `--type`, `--member-id`, `--member-type`, `--perm`, `--identity` |
| `perm_doc_remove.py` | 移除协作者 | `--token`, `--type`, `--member-id` |
| `perm_bitable_private.py` | 多维表格设为私有 | `--app-token` |

## 注意事项

1. **folder 类型需用 tenant 身份**：folder 由 tenant（应用）创建时，给用户授权需加 `--identity tenant`；默认 user 身份无法给不属于自己的 folder 授权。
2. **权限生效延迟**：添加协作者后，对方可能需要刷新页面才能看到文档。
3. **依赖**：纯 Python 标准库（Pillow 可选），共用 `../feishu_common`。
