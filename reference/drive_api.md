# 云空间 API 参考（兜底文档）

当预置脚本无法解决问题时，可直接调用以下接口。

## 列出文件

```
GET /open-apis/drive/v1/files?page_size=200&folder_token=fldcnxxx
```

## 复制文件

```
POST /open-apis/drive/v1/files/{file_token}/copy
Body: {"name": "副本", "type": "docx", "folder_token": "fldcnxxx"}
```

## 移动文件

```
PUT /open-apis/drive/v1/files/{file_token}/move
Body: {"type": "docx", "folder_token": "fldcnxxx"}
```

## 删除文件

```
DELETE /open-apis/drive/v1/files/{file_token}?type=docx
```

## 创建文件夹

```
POST /open-apis/drive/v1/files/create_folder
Body: {"name": "新文件夹", "folder_token": "fldcnxxx"}
```

## 上传文件

```
POST /open-apis/drive/v1/files/upload_all
Content-Type: multipart/form-data
Form: file_name, parent_type, parent_node, size, file
```

## 下载文件

```
GET /open-apis/drive/v1/files/{file_token}/download
```

注意：docx 文件不支持直接下载，会返回 404。需使用导出任务 API。

## 下载媒体

```
GET /open-apis/drive/v1/medias/{media_token}/download
```

## 导出任务

创建导出任务（docx/sheet/bitable 转 pdf/xlsx/csv/markdown）：

```
POST /open-apis/drive/v1/export_tasks
Body: {"token": "doccnxxx", "type": "docx", "file_extension": "pdf"}
```

查询导出状态：

```
GET /open-apis/drive/v1/export_tasks/{ticket}?token=doccnxxx
```

下载导出结果：

```
GET /open-apis/drive/v1/export_tasks/file/{file_token}/download
```

注意：sheet/bitable 导出 csv 时必须传 `sub_id`（子表 ID）。

## 官方文档

- https://open.feishu.cn/document/server-docs/docs/drive-v1/file/list
- https://open.feishu.cn/document/server-docs/docs/drive-v1/file/copy
- https://open.feishu.cn/document/server-docs/docs/drive-v1/export_task/create
- 飞书开放平台 AI 助手：https://open.feishu.cn/app/ai/playground?from=nav
