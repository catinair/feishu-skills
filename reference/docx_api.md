# 文档 API 参考（兜底文档）

当预置脚本无法解决问题时，可直接调用以下接口。

## 创建文档

```
POST /open-apis/docx/v1/documents
Body: {"folder_token": "fldcnxxx"}
```

## 读取 Block 树

```
GET /open-apis/docx/v1/documents/{document_id}/blocks?page_size=500&document_revision_id=-1
```

## Markdown 转 Block

```
POST /open-apis/docx/v1/documents/blocks/convert
Body: {"content_type": "markdown", "content": "# 标题\n\n正文"}
```

## 插入 Block

```
POST /open-apis/docx/v1/documents/{document_id}/blocks/{document_id}/descendant?document_revision_id=-1
Body: {"children_id": [...], "descendants": [...], "index": 0}
```

## 下载文档媒体

```
GET /open-apis/drive/v1/medias/{media_token}/download
```

## 官方文档

- https://open.feishu.cn/document/server-docs/docs/docs/docx-v1/document-create
- https://open.feishu.cn/document/server-docs/docs/docs/docx-v1/document-blockget
- 飞书开放平台 AI 助手：https://open.feishu.cn/app/ai/playground?from=nav
