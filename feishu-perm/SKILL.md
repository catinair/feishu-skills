---
name: feishu-perm
version: 1.0.0
description: |
  飞书文档/云空间权限管理。给文档、表格、多维表格添加/移除协作者，查询现有权限。
  纯 Python 标准库（Pillow 可选，用于画板图片裁剪）。
metadata:
  requires:
    bins: ["python3"]
    files: ["feishu-perm/perm_doc_list.py", "feishu-perm/perm_doc_share.py", "feishu-perm/perm_doc_remove.py", "config/credentials.json"]
---

# feishu-perm -- 飞书权限管理技能

飞书文档/云空间权限管理。给文档、表格、多维表格添加/移除协作者，查询现有权限。

## 使用场景

- 创建了文档/表格后，需要给其他用户开通管理权限
- 查询某个文档当前的分享范围和协作者列表
- 移除不再需要的协作者

## 权限要求

> **说明**：以下标注的审批要求基于常见企业配置。实际是否需要管理员审批，取决于你所在企业管理员在「飞书开放平台 → 自建应用审核规则」中的设置。

| 脚本 | 所需权限 | 审批说明 |
|------|---------|----------|
| perm_doc_list.py | `drive:drive` 或 `docs:document` 相关权限 | 通常需管理员审批 |
| perm_doc_share.py | `drive:drive` 或 `docs:document` 相关权限 | 通常需管理员审批 |
| perm_doc_remove.py | `drive:drive` 或 `docs:document` 相关权限 | 通常需管理员审批 |

## 快捷命令

### 列出协作者

```bash
python3 feishu-perm/perm_doc_list.py --token doxcnxxx --type docx
```

返回当前文档的所有协作者及其权限级别（view/edit/full_access）。

### 添加协作者

```bash
# 给用户查看权限
python3 feishu-perm/perm_doc_share.py --token doxcnxxx --type docx --member-id ou_xxx --member-type openid --perm view

# 给用户编辑权限
python3 feishu-perm/perm_doc_share.py --token doxcnxxx --type docx --member-id ou_xxx --member-type openid --perm edit

# 给群聊编辑权限
python3 feishu-perm/perm_doc_share.py --token doxcnxxx --type docx --member-id oc_xxx --member-type openchat --perm edit
```

**参数说明：**
- `--type`: docx / sheet / bitable / file / mindnote / slides
- `--member-type`: openid / union_id / user_id / openchat / department_id
- `--perm`: view（可阅读）/ edit（可编辑）/ full_access（可管理）

### 移除协作者

```bash
python3 feishu-perm/perm_doc_remove.py --token doxcnxxx --type docx --member-id ou_xxx
```

## 脚本列表

| 脚本 | 功能 | 关键参数 |
|------|------|----------|
| `perm_doc_list.py` | 列出协作者 | `--token`, `--type` |
| `perm_doc_share.py` | 添加协作者 | `--token`, `--type`, `--member-id`, `--member-type`, `--perm` |
| `perm_doc_remove.py` | 移除协作者 | `--token`, `--type`, `--member-id` |

## 注意事项

1. **folder 类型暂不支持**：当前 drive v1 权限 API 对 folder 类型返回 400，可能是参数或路径差异，待后续验证。
2. **权限生效延迟**：添加协作者后，对方可能需要刷新页面才能看到文档。
3. **依赖**：纯 Python 标准库（Pillow 可选），共用 `../feishu_common`。
