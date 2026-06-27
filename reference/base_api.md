# 多维表格 API 参考（兜底文档）

当预置脚本无法解决问题时，可直接调用以下接口。

## 记录 CRUD（Bitable v1）

### 查询记录

```
GET /open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records?page_size=500
Query: filter, page_token
```

### 创建记录

```
POST /open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records
Body: {"fields": {"姓名": "张三", "状态": "进行中"}}
```

### 更新记录

```
PUT /open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id}
Body: {"fields": {"状态": "已完成"}}
```

### 删除记录

```
DELETE /open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id}
```

### 批量创建

```
POST /open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_create
Body: {"records": [{"fields": {...}}, ...]}
```

单次上限 500 条。

### 批量更新

```
POST /open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_update
Body: {"records": [{"record_id": "rec_xxx", "fields": {...}}, ...]}
```

### 批量删除

```
POST /open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_delete
Body: {"records": ["rec_xxx", "rec_yyy"]}
```

### 搜索记录

```
POST /open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/search
Body: {"keyword": "张三", "search_fields": ["姓名", "状态"]}
```

## 数据表管理（Bitable v1）

### 列出数据表

```
GET /open-apis/bitable/v1/apps/{app_token}/tables
```

### 创建数据表

```
POST /open-apis/bitable/v1/apps/{app_token}/tables
Body: {"table": {"name": "新表名"}}
```

### 删除数据表

```
DELETE /open-apis/bitable/v1/apps/{app_token}/tables/{table_id}
```

## 字段管理（Bitable v1）

### 列出字段

```
GET /open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/fields
```

### 创建字段

```
POST /open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/fields
Body: {"field_name": "新字段", "type": 1}
```

### 更新字段

```
PUT /open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/fields/{field_id}
Body: {"field_name": "新名称", "type": 1, "property": {...}}
```

注意：必须传 `type`，不传会报错。

### 删除字段

```
DELETE /open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/fields/{field_id}
```

## 视图管理（Bitable v1）

### 列出视图

```
GET /open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/views
```

### 创建视图

```
POST /open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/views
Body: {"view_name": "新视图", "view_type": "grid"}
```

视图类型：`grid`(表格) / `kanban`(看板) / `gallery`(画册) / `gantt`(甘特图)

## Base v3 API（需 `base:base` 权限）

### 数据查询（聚合分析）

```
POST /open-apis/base/v3/bases/{app_token}/data/query
Body: {"dimensions": [{"field_id": "fldStatus"}], "measures": [{"field_id": "fldAmount", "aggregator": "SUM"}]}
```

### 视图筛选

```
GET /open-apis/base/v3/bases/{app_token}/tables/{table_id}/views/{view_id}/filter
PUT /open-apis/base/v3/bases/{app_token}/tables/{table_id}/views/{view_id}/filter
Body: {"logic": "and", "conditions": [["fldStatus", "==", "进行中"]]}
```

### 视图排序

```
GET /open-apis/base/v3/bases/{app_token}/tables/{table_id}/views/{view_id}/sort
PUT /open-apis/base/v3/bases/{app_token}/tables/{table_id}/views/{view_id}/sort
Body: {"sort_config": [{"field_id": "fldDate", "desc": true}]}
```

### 视图分组

```
GET /open-apis/base/v3/bases/{app_token}/tables/{table_id}/views/{view_id}/group
PUT /open-apis/base/v3/bases/{app_token}/tables/{table_id}/views/{view_id}/group
Body: {"group_config": [{"field_id": "fldStatus"}]}
```

### 记录变更历史

```
GET /open-apis/base/v3/bases/{app_token}/record_history?table_id=xxx&record_id=xxx
```

## 官方文档

- https://open.feishu.cn/document/server-docs/docs/bitable-v1/app-overview
- https://open.feishu.cn/document/server-docs/docs/base-v3/overview
- 飞书开放平台 AI 助手：https://open.feishu.cn/app/ai/playground?from=nav
