---
name: feishu-wiki
version: 1.0.0
description: |
  飞书知识库技能：列出空间、查询节点、创建节点。
  纯 Python 标准库（Pillow 可选，用于画板图片裁剪）。
metadata:
  requires:
    bins: ["python3"]
    files: ["feishu-wiki/wiki_list_spaces.py", "feishu-wiki/wiki_list_nodes.py", "feishu-wiki/wiki_get_node.py", "feishu-wiki/wiki_create_node.py", "config/credentials.json"]
---

# feishu-wiki -- 飞书知识库技能

飞书知识库（Wiki）节点查询与元信息获取。将 `/wiki/xxx` 链接解析为可操作的真实文档 token。

## 使用场景

- 将知识库链接（如 `https://xxx.feishu.cn/wiki/abc123`）解析为 `obj_token` + `obj_type`
- 列出知识空间及其目录树，确定需要操作的文档/表格/多维表格
- 在知识库中搜索特定标题的节点

## 输出说明

本模块的写操作类 CLI（如 `wiki_create_node.py`）默认输出精简摘要，便于 AI 消费。如需完整 API 原始响应，请加 `--raw`：

```bash
python3 feishu-wiki/wiki_create_node.py "测试节点" --space xxx --raw
```

通用 CLI 约定（`--yes`、`--raw`、`--identity`）详见项目级文档 [`docs/usage.md`](../docs/usage.md)。

## 工作流

### 1. 列出知识空间

```bash
python3 feishu-wiki/wiki_list_spaces.py
```

返回所有可访问的 wiki space，每个包含 `space_id`、`name`、`description`。

### 2. 列出空间下的节点

```bash
# 列出指定空间的根节点（无 parent_node_token）
python3 feishu-wiki/wiki_list_nodes.py --space-id 7307181174114517020

# 列出子节点
python3 feishu-wiki/wiki_list_nodes.py --space-id 7307181174114517020 --parent-node-token MV0qwHubqiloBmkoGS3cFYo8nNc

# 限制数量（默认 50，分页自动拉取）
python3 feishu-wiki/wiki_list_nodes.py --space-id 7307181174114517020 --page-size 50
```

### 2.1 递归遍历整个知识空间

```bash
# 递归遍历所有节点
python3 feishu-wiki/wiki_list_all_nodes.py --space-id 7310041255240073220

# 拼接节点链接（需要传入知识库域名）
python3 feishu-wiki/wiki_list_all_nodes.py --space-id 7310041255240073220 --wiki-base-url https://ying-dao.feishu.cn

# 限制遍历深度
python3 feishu-wiki/wiki_list_all_nodes.py --space-id 7310041255240073220 --max-depth 2

# 按标题过滤（仅顶层）
python3 feishu-wiki/wiki_list_all_nodes.py --space-id 7310041255240073220 --filter "医药"
```

**输出结构：**
- `stats` — 统计信息（总数、按类型分布、最大深度）
- `nodes` — 扁平节点列表，每项包含：
  - `depth` — 层级深度（根节点为 0）
  - `title` — 节点标题
  - `node_token` — wiki 链接用 token
  - `obj_token` — 真实文档 token（调接口用）
  - `obj_type` — 真实类型：`docx` | `sheet` | `bitable` | `file` | `mindnote`
  - `node_type` — `origin`（原始）或 `shortcut`（快捷方式）
  - `has_child` — 是否有子节点
  - `parent_node_token` — 父节点 token
  - `url` — wiki 链接（仅传 `--wiki-base-url` 时有值）

**节点数据结构：**
- `node_token` — wiki 节点 token，用于 URL 和子节点查询
- `obj_token` — 真实文档/表格 token，传给 doc/sheet/base skill 使用
- `obj_type` — 真实类型：`docx` | `sheet` | `bitable` | `file` | `mindnote`
- `node_type` — `origin`（原始节点）或 `shortcut`（快捷方式）
- `has_child` — 是否有子节点
- `parent_node_token` — 父节点 token（根节点为空）

### 3. 解析 wiki token（单节点查询）

```bash
python3 feishu-wiki/wiki_get_node.py --token OiahwckAfiDIwlkg2fhcwJb7n2b
```

从 wiki URL 中提取 token（`wiki/` 后面的部分），返回对应的 `obj_token` 和 `obj_type`。

**典型用法：** 将 wiki 链接转成可操作 token 后，根据 `obj_type` 分发给对应的 skill：
- `docx` → `feishu-doc`（doc_read.py / doc_write.py）
- `sheet` → `feishu-sheets`（sheet_read.py / sheet_write.py）
- `bitable` → `feishu-base`（base_query.py / base_append.py）

## 脚本列表

| 脚本 | 功能 | 关键参数 |
|------|------|----------|
| `wiki_list_spaces.py` | 列出所有知识空间 | — |
| `wiki_list_nodes.py` | 列出空间节点（单层） | `--space-id`, `--parent-node-token`, `--page-size` |
| `wiki_list_all_nodes.py` | 递归遍历整个知识空间 | `--space-id`, `--wiki-base-url`, `--max-depth`, `--filter` |
| `wiki_get_node.py` | 单节点解析 | `--token` |
| `wiki_create_node.py` | 在知识空间创建节点 | `--space`, `--type`, `--parent`, `--yes` |

### 4. 创建 Wiki 节点

```bash
# 在知识空间根目录创建文档
python3 feishu-wiki/wiki_create_node.py "会议纪要" --space 7310041255240073220

# 创建表格节点
python3 feishu-wiki/wiki_create_node.py "数据表" --space 7310041255240073220 --type sheet

# 在指定父节点下创建子文档
python3 feishu-wiki/wiki_create_node.py "子文档" --space 7310041255240073220 --parent OUxxxxx --type docx
```

支持的 `--type`：`docx`（默认）、`sheet`、`bitable`、`mindnote`、`slides`。

## 注意事项

1. **wiki token vs obj_token**：知识库链接里的 token 是 `node_token`（wiki 专用），不能直接传给文档/表格 API。必须先通过 `wiki_get_node.py` 解析出 `obj_token` 和 `obj_type`。
2. **快捷方式节点**：`node_type=shortcut` 的节点指向其他空间的真实节点，其 `origin_node_token` 和 `origin_space_id` 可能为空。对文档做接口调用时必须用 `obj_token` 而非 `node_token`。
3. **分页**：`wiki_list_nodes.py` 默认自动拉取全部节点（通过 `page_token` 分页），可用 `--page-size` 限制单次返回数量。
4. **依赖**：纯 Python 标准库（Pillow 可选），共用 `../feishu_common`。
