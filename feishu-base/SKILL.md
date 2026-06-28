---
name: feishu-base
version: 1.3.0
description: |
  飞书多维表格技能：创建表格、查询记录、追加记录、更新记录、删除记录、
  批量操作、字段/视图/表管理、Base 复制、字段 CRUD、视图管理、单条记录获取。
  纯 Python 标准库（Pillow 可选，用于画板图片裁剪）。
metadata:
  requires:
    bins: ["python3"]
    files:
      [
        "feishu-base/base_create.py",
        "feishu-base/base_get.py",
        "feishu-base/base_copy.py",
        "feishu-base/base_tables.py",
        "feishu-base/base_table_create.py",
        "feishu-base/base_table_delete.py",
        "feishu-base/base_fields.py",
        "feishu-base/base_views.py",
        "feishu-base/base_query.py",
        "feishu-base/base_append.py",
        "feishu-base/base_update.py",
        "feishu-base/base_delete.py",
        "feishu-base/base_batch_update.py",
        "feishu-base/base_batch_delete.py",
        "feishu-base/base_record_get.py",
        "feishu-base/base_batch_create.py",
        "feishu-base/base_table_get.py",
        "feishu-base/base_table_update.py",
        "feishu-base/base_field_create.py",
        "feishu-base/base_field_delete.py",
        "feishu-base/base_field_update.py",
        "feishu-base/base_field_get.py",
        "feishu-base/base_view_create.py",
        "feishu-base/base_view_delete.py",
        "feishu-base/base_view_rename.py",
        "feishu-base/base_record_search.py",
        "feishu-base/base_record_upsert.py",
        "feishu-base/base_record_upload_attachment.py",
        "feishu-base/base_view_get.py",
        "feishu-base/base_view_filter_get.py",
        "feishu-base/base_view_filter_set.py",
        "feishu-base/base_view_sort_get.py",
        "feishu-base/base_view_sort_set.py",
        "feishu-base/base_view_group_get.py",
        "feishu-base/base_view_group_set.py",
        "feishu-base/base_view_visible_fields_get.py",
        "feishu-base/base_view_visible_fields_set.py",
        "feishu-base/base_data_query.py",
        "feishu-base/base_record_history_list.py",
        "feishu-base/base_field_search_options.py",
        "config/credentials.json",
      ]
---

# feishu-base -- 飞书多维表格技能

## 权限要求

> **说明**：以下标注的审批要求基于常见企业配置。实际是否通常需管理员审批，取决于你所在企业管理员在「飞书开放平台 → 自建应用审核规则」中的设置。

| 脚本 | 所需权限 | 审批说明 |
|------|---------|------|
| base_create.py | `base:app:create` | 一般无需管理员审批 |
| base_get.py | `base:app:read` | 一般无需管理员审批 |
| base_copy.py | `base:app:create` | 一般无需管理员审批 |
| base_tables.py | `base:field:read` | 一般无需管理员审批 |
| base_table_create.py | `base:table:create` | 一般无需管理员审批 |
| base_table_delete.py | `base:table:delete` | 一般无需管理员审批 |
| base_fields.py | `base:field:read` | 一般无需管理员审批 |
| base_views.py | `base:view:read` | 一般无需管理员审批 |
| base_query.py | `base:record:read` | 一般无需管理员审批 |
| base_append.py | `base:record:create` | 一般无需管理员审批 |
| base_update.py | `base:record:update` | 一般无需管理员审批 |
| base_delete.py | `base:record:delete` | 一般无需管理员审批 |
| base_batch_update.py | `base:record:update` | 一般无需管理员审批 |
| base_batch_delete.py | `base:record:delete` | 一般无需管理员审批 |
| base_record_get.py | `base:record:read` | 一般无需管理员审批 |
| base_batch_create.py | `base:record:create` | 一般无需管理员审批 |
| base_table_get.py | `base:table:read` | 一般无需管理员审批 |
| base_table_update.py | `base:table:write_only` | **通常需管理员审批** |
| base_field_create.py | `base:field:create` | **通常需管理员审批** |
| base_field_delete.py | `base:field:delete` | **通常需管理员审批** |
| base_field_update.py | `base:field:update` | **通常需管理员审批** |
| base_field_get.py | `base:field:read` | 一般无需管理员审批 |
| base_view_create.py | `base:view:write_only` | **通常需管理员审批** |
| base_view_delete.py | `base:view:write_only` | **通常需管理员审批** |
| base_view_rename.py | `base:view:write_only` | **通常需管理员审批** |
| base_record_search.py | `base:record:read` | 一般无需管理员审批 |
| base_record_upsert.py | `base:record:create` / `base:record:update` | 一般无需管理员审批 |
| base_record_upload_attachment.py | `base:record:update` / `drive:file` | 一般无需管理员审批 |
| base_view_get.py | `base:view:read` | 一般无需管理员审批 |
| base_view_filter_get.py | `base:view:read` | **通常需管理员审批** |
| base_view_filter_set.py | `base:view:write_only` | **通常需管理员审批** |
| base_view_sort_get.py | `base:view:read` | **通常需管理员审批** |
| base_view_sort_set.py | `base:view:write_only` | **通常需管理员审批** |
| base_view_group_get.py | `base:view:read` | **通常需管理员审批** |
| base_view_group_set.py | `base:view:write_only` | **通常需管理员审批** |
| base_view_visible_fields_get.py | `base:view:read` | **通常需管理员审批** |
| base_view_visible_fields_set.py | `base:view:write_only` | **通常需管理员审批** |
| base_data_query.py | `base:table:read` | **通常需管理员审批** |
| base_record_history_list.py | `base:history:read` | **通常需管理员审批** |
| base_field_search_options.py | `base:field:read` | **通常需管理员审批** |

> **注意**：
> - `base:table:write_only`、`base:field:create/delete/update`、`base:view:write_only` 是高级权限，通常需要飞书管理员审批。如遇 403 权限错误，请在飞书开放平台申请对应权限并联系管理员审批。
> - **Base v3 API**（`base_view_filter_get/set`、`base_view_sort_get/set`、`base_view_group_get/set`、`base_view_visible_fields_get/set`、`base_data_query`、`base_record_history_list`、`base_field_search_options`）需要 `base:base` 或更细粒度的 v3 权限，通常需要管理员审批。如遇 `99991672` 权限错误，请在飞书开放平台申请对应权限并联系管理员审批。

## 快捷命令

### 创建多维表格

```bash
python3 feishu-base/base_create.py --name "客户信息表"
```

默认创建到指定文件夹，可通过 `--folder-token` 自定义位置。

### 获取 Base 信息

```bash
python3 feishu-base/base_get.py --app base_token_or_url
```

### 复制 Base

```bash
python3 feishu-base/base_copy.py --app base_token_or_url --name "新表格名称"
```

### 列出数据表

```bash
python3 feishu-base/base_tables.py --app base_token_or_url
```

### 创建数据表

```bash
python3 feishu-base/base_table_create.py --app base_token_or_url --name "新表名"
```

可通过 `--fields-file` 指定初始字段定义（JSON 数组）。

### 删除数据表

```bash
python3 feishu-base/base_table_delete.py --app base_token_or_url --table table_id
```

### 获取数据表

```bash
python3 feishu-base/base_table_get.py --app base_token_or_url --table table_id
```

### 更新数据表（重命名）

```bash
python3 feishu-base/base_table_update.py --app base_token_or_url --table table_id --name "新表名"
```

**注意**：此接口调用 Base v3 API，应用需开通 `base:base` 相关权限。如遇 `99991672` 权限错误，请在飞书开放平台申请权限。

### 列出字段

```bash
python3 feishu-base/base_fields.py --app base_token_or_url --table table_id
```

写记录前先查看字段结构，了解字段名和类型。

### 列出视图

```bash
python3 feishu-base/base_views.py --app base_token_or_url --table table_id
```

### 获取单条记录

```bash
python3 feishu-base/base_record_get.py --app base_token_or_url --table table_id --record rec_xxx
```

### 查询记录

```bash
# 查询所有记录
python3 feishu-base/base_query.py --app XqA3bAtGpaWjflsryxfcadp7nmf --table tblOflmn3KGcgUsn

# 从 URL 自动提取 app_token 和 table_id
python3 feishu-base/base_query.py --app "https://example.feishu.cn/base/XqA3bAtGpaWjflsryxfcadp7nmf?table=tblOflmn3KGcgUsn"

# 带筛选条件（飞书 filter 语法）
python3 feishu-base/base_query.py --app base_token --table table_id --filter "CurrentValue.[姓名] = \"张三\""
```

### 追加记录

```bash
# 直接指定字段值
python3 feishu-base/base_append.py \
  --app base_token \
  --table table_id \
  --fields '{"姓名": "张三", "电话": "13800138000"}'

# 从文件读取字段值
python3 feishu-base/base_append.py \
  --app base_token \
  --table table_id \
  --fields-file record.json
```

### 批量创建记录

```bash
python3 feishu-base/base_batch_create.py \
  --app base_token \
  --table table_id \
  --records-file records.json
```

`records.json` 格式：
```json
[
  {"fields": {"姓名": "张三", "电话": "13800138000"}},
  {"fields": {"姓名": "李四", "电话": "13900139000"}}
]
```

**注意**：单次最多 500 条。

### 更新记录

```bash
python3 feishu-base/base_update.py \
  --app base_token \
  --table table_id \
  --record rec_xxx \
  --fields '{"姓名": "李四"}'
```

### 删除记录

```bash
python3 feishu-base/base_delete.py \
  --app base_token \
  --table table_id \
  --record rec_xxx
```

### 批量更新记录

```bash
python3 feishu-base/base_batch_update.py \
  --app base_token \
  --table table_id \
  --records-file updates.json
```

`updates.json` 格式：
```json
[
  {"record_id": "rec_xxx", "fields": {"姓名": "张三"}},
  {"record_id": "rec_yyy", "fields": {"姓名": "李四"}}
]
```

### 批量删除记录

```bash
# 逗号分隔 record_id
python3 feishu-base/base_batch_delete.py \
  --app base_token \
  --table table_id \
  --records "rec_xxx,rec_yyy"

# 从文件读取
python3 feishu-base/base_batch_delete.py \
  --app base_token \
  --table table_id \
  --records-file ids.json
```

`ids.json` 格式：`["rec_xxx", "rec_yyy"]`

### 高级搜索记录

```bash
# 基础搜索
python3 feishu-base/base_record_search.py --app base_token --table table_id

# 带复杂筛选条件
python3 feishu-base/base_record_search.py \
  --app base_token \
  --table table_id \
  --filter '{"conjunction": "and", "conditions": [{"field_name": "状态", "operator": "is", "value": ["进行中"]}]}'

# 带筛选+排序+指定返回字段
python3 feishu-base/base_record_search.py \
  --app base_token \
  --table table_id \
  --filter-file filter.json \
  --sort '[{"field_name": "日期", "desc": false}]' \
  --fields '["姓名", "电话", "日期"]'
```

### 更新或插入记录（Upsert）

```bash
# 更新已有记录
python3 feishu-base/base_record_upsert.py \
  --app base_token \
  --table table_id \
  --record rec_xxx \
  --fields '{"姓名": "李四"}'

# 创建新记录（不提供 --record）
python3 feishu-base/base_record_upsert.py \
  --app base_token \
  --table table_id \
  --fields '{"姓名": "张三", "电话": "13800138000"}'
```

### 上传附件到记录字段

```bash
python3 feishu-base/base_record_upload_attachment.py \
  --app base_token \
  --table table_id \
  --record rec_xxx \
  --field "附件" \
  --path ./document.pdf
```

**注意**：此脚本会自动将新附件合并到该字段已有的附件列表中，无需手动处理。

### 获取字段

```bash
python3 feishu-base/base_field_get.py --app base_token_or_url --table table_id --field fld_xxx
```

### 创建字段

```bash
# 简单文本字段
python3 feishu-base/base_field_create.py --app base_token --table table_id --name "新字段" --type 1

# 邮箱字段（通过 ui_type 指定子类型）
python3 feishu-base/base_field_create.py --app base_token --table table_id --name "邮箱" --type 1 --ui-type Email

# 带选项的单选字段
python3 feishu-base/base_field_create.py \
  --app base_token \
  --table table_id \
  --name "状态" \
  --type 3 \
  --property '{"options": [{"name": "选项A", "color": 0}, {"name": "选项B", "color": 1}]}'
```

**常用 ui_type**：`Text`, `Email`, `Phone`, `Url`, `Rating`, `Number`, `SingleSelect`, `MultiSelect`, `DateTime`, `Checkbox`, `User`, `Attachment`。

### 更新字段

```bash
python3 feishu-base/base_field_update.py \
  --app base_token \
  --table table_id \
  --field fld_xxx \
  --name "新字段名" \
  --type 1 \
  --property '{"options": [{"name": "新选项", "color": 2}]}'
```

**注意**：Bitable v1 API 更新字段时必须传入 `type`，CLI 已自动兜底（不传时自动获取当前字段类型），但显式传入更稳妥。

### 删除字段

```bash
python3 feishu-base/base_field_delete.py --app base_token --table table_id --field fld_xxx --yes
```

### 创建视图

```bash
python3 feishu-base/base_view_create.py --app base_token --table table_id --name "新视图" --type grid
```

视图类型：`grid`(表格)、`kanban`(看板)、`gallery`(画册)、`gantt`(甘特图)。

### 删除视图

```bash
python3 feishu-base/base_view_delete.py --app base_token --table table_id --view vew_xxx --yes
```

### 重命名视图

```bash
python3 feishu-base/base_view_rename.py --app base_token --table table_id --view vew_xxx --name "新名称"
```

### 获取视图详情

```bash
python3 feishu-base/base_view_get.py --app base_token --table table_id --view vew_xxx
```

### 获取/设置视图筛选条件

```bash
# 获取当前筛选
python3 feishu-base/base_view_filter_get.py --app base_token --table table_id --view vew_xxx

# 设置筛选
python3 feishu-base/base_view_filter_set.py \
  --app base_token --table table_id --view vew_xxx \
  --json '{"logic":"and","conditions":[["fldStatus","==","进行中"]]}'
```

### 获取/设置视图排序

```bash
# 获取当前排序
python3 feishu-base/base_view_sort_get.py --app base_token --table table_id --view vew_xxx

# 设置排序
python3 feishu-base/base_view_sort_set.py \
  --app base_token --table table_id --view vew_xxx \
  --json '[{"field_id":"fldDate","desc":true}]'
```

### 获取/设置视图分组

```bash
# 获取当前分组
python3 feishu-base/base_view_group_get.py --app base_token --table table_id --view vew_xxx

# 设置分组
python3 feishu-base/base_view_group_set.py \
  --app base_token --table table_id --view vew_xxx \
  --json '[{"field_id":"fldStatus"}]'
```

### 获取/设置视图可见字段

```bash
# 获取当前可见字段配置
python3 feishu-base/base_view_visible_fields_get.py --app base_token --table table_id --view vew_xxx

# 设置可见字段
python3 feishu-base/base_view_visible_fields_set.py \
  --app base_token --table table_id --view vew_xxx \
  --json '{"field_order":["fldName","fldStatus"],"hidden_fields":["fldInternal"]}'
```

### 数据查询（JSON DSL 聚合）

```bash
# 按状态分组统计金额
python3 feishu-base/base_data_query.py \
  --app base_token \
  --dsl '{"dimensions":[{"field_id":"fldStatus"}],"measures":[{"field_id":"fldAmount","aggregator":"SUM"}]}'

# 从文件读取 DSL
python3 feishu-base/base_data_query.py --app base_token --dsl-file query.json
```

### 查询记录变更历史

```bash
python3 feishu-base/base_record_history_list.py \
  --app base_token --table table_id --record rec_xxx --page-size 50
```

### 搜索字段选项

```bash
# 列出单选/多选字段的所有选项
python3 feishu-base/base_field_search_options.py --app base_token --table table_id --field fld_xxx

# 按关键词搜索选项
python3 feishu-base/base_field_search_options.py --app base_token --table table_id --field fld_xxx --keyword "选项A"
```

## 字段类型注意事项

不同字段类型传入的格式不同。建议先通过 `base_fields.py` 查看字段结构，再通过 `base_query.py` 查询一条现有记录观察字段格式，然后再写入。

### 基础字段

| 字段类型 | API type | 写入格式 | 示例 |
|---------|---------|---------|------|
| 多行文本 | 1 | 字符串 | `"张三"` |
| 数字 | 2 | 数字 | `100` |
| 单选 | 3 | 字符串或对象 | `"选项A"` 或 `{"text": "选项A"}` |
| 多选 | 4 | 字符串数组或对象数组 | `["选项A", "选项B"]` |
| 日期 | 5 | 毫秒时间戳 | `1704067200000` |
| 复选框 | 7 | 布尔值 | `true` / `false` |
| 人员 | 11 | 对象数组 | `[{"id": "ou_xxx"}]` |
| 电话 | 13 | 字符串 | `"13800138000"` |
| 超链接 | 15 | 对象 | `{"text": "显示文本", "link": "https://example.com"}` |
| 附件 | 17 | 对象数组 | `[{"file_token": "boxcnxxx"}]`（见下方附件说明） |
| 关联记录 | 18 | 对象数组 | `[{"id": "rec_xxx"}]` |
| 双向关联 | 22 | 对象数组 | `[{"id": "rec_xxx"}]` |
| 地理位置 | 23 | 对象 | `{"location": "地址", "location_type": "text"}` |
| 群组 | 24 | 对象数组 | `[{"id": "oc_xxx"}]` |

### 文本子类型

创建字段时可通过 `property.text_type` 指定：

| 子类型 | 说明 |
|--------|------|
| `plain` | 纯文本（默认） |
| `phone` | 电话 |
| `url` | URL |
| `email` | 邮箱 |
| `barcode` | 条码 |

### 数字子类型

创建字段时可通过 `property.formatter` 指定：

| 子类型 | 说明 |
|--------|------|
| `plain` | 普通数字（默认） |
| `currency` | 货币 |
| `progress` | 进度 |
| `rating` | 评分 |

### 系统字段（只读）

| 字段类型 | API type | 说明 |
|---------|---------|------|
| 创建时间 | 1001 | 自动记录，不可写入 |
| 最后修改时间 | 1002 | 自动记录，不可写入 |
| 创建人 | 1003 | 自动记录，不可写入 |
| 最后修改人 | 1004 | 自动记录，不可写入 |
| 自动编号 | 1005 | 自动生成，不可写入 |

### 附件字段写入说明

附件字段必须先**上传到当前多维表格的存储空间**，获取 `file_token` 后才能写入记录。

```bash
# 1. 上传文件到多维表格空间（parent_type 必须为 bitable_file）
python3 feishu-drive/drive_upload.py \
  --path ./document.pdf \
  --parent-type bitable_file \
  --parent-node YOUR_APP_TOKEN

# 2. 用返回的 file_token 写入记录
python3 feishu-base/base_append.py \
  --app YOUR_APP_TOKEN \
  --table YOUR_TABLE_ID \
  --fields '{"附件": [{"file_token": "boxcnxxx"}]}'
```

**注意**：通过普通云空间上传（`parent_type=explorer`）获取的 `file_token` 不能用于 Base 附件字段，会报错 `1254303 AttachPermNotAllow`。

### 高级字段

| 字段类型 | API type | 说明 |
|---------|---------|------|
| 公式 | 20 | 只读，由公式表达式计算 |
| 查找引用 | 21 | 只读，引用关联表的字段 |

## 批量操作限制

- **单次上限**：批量创建/更新/删除最多 500 条记录，超过需分批
- **原子性**：批量操作是原子性的，只要有一条失败，整批都会回滚
- **并发限制**：同一数据表不支持并发写，需串行调用并加 0.5~1 秒延迟，否则会报 `1254291 Write conflict`

## 常见错误码速查

| 错误码 | 错误信息 | 原因 | 解决 |
|--------|---------|------|------|
| 1254015 | Field types do not match | 字段值格式与类型不匹配 | 先 `base_fields.py` 查看类型，按上表构造正确格式 |
| 1254045 | FieldNameNotFound | 字段名不存在 | 检查字段名（含空格、大小写），或用 `base_fields.py` 确认 |
| 1254064 | DatetimeFieldConvFail | 日期格式错误 | 必须用毫秒时间戳（13 位），不能用字符串或秒级时间戳 |
| 1254066 | UserFieldConvFail | 人员字段格式错误 | 必须传 `[{"id": "ou_xxx"}]`，确认 user_id_type |
| 1254068 | URLFieldConvFail | 超链接格式错误 | 必须用对象 `{"text": "...", "link": "..."}`，不能传字符串 URL |
| 1254104 | RecordAddOnceExceedLimit | 批量超过上限 | 分批，每批 ≤ 500 条 |
| 1254291 | Write conflict | 并发写冲突 | 串行调用 + 延迟 0.5~1 秒 |
| 1254303 | AttachPermNotAllow | 附件未属于当前表格 | 附件需通过 `parent_type=bitable_file` 上传到当前多维表格 |
| 99991672 | 权限不足 | 应用缺少 Base v3 权限 | `base_table_update` 等接口需开通 `base:base` 权限 |
| 99992402 | field validation failed | 字段更新参数不完整 | 必须同时传入 `type`（CLI 已自动处理） |

## base URL 格式

```
https://xxx.feishu.cn/base/{app_token}?table={table_id}
```

脚本支持直接从完整 URL 提取 `app_token` 和 `table_id`。
