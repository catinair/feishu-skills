# IM API 参考（兜底文档）

当预置脚本无法解决问题时，可直接调用以下接口。

## 发送文本消息

```
POST /open-apis/im/v1/messages?receive_id_type=chat_id
Body: {
  "receive_id": "oc_xxx",
  "msg_type": "text",
  "content": "{\"text\":\"Hello\"}"
}
```

## 发送富文本消息（post）

```
POST /open-apis/im/v1/messages?receive_id_type=chat_id
Body: {
  "receive_id": "oc_xxx",
  "msg_type": "post",
  "content": "{\"zh_cn\":{\"title\":\"标题\",\"content\":[[{\"tag\":\"text\",\"text\":\"正文\"}]]}}"
}
```

## 上传图片

```
POST /open-apis/im/v1/images
Content-Type: multipart/form-data
Form: image_type=message, image=<文件>
```

## 获取群聊列表

```
GET /open-apis/im/v1/chats?page_size=50
```

## 获取群聊信息

```
GET /open-apis/im/v1/chats/{chat_id}
```

## 获取群成员

```
GET /open-apis/im/v1/chats/{chat_id}/members?member_id_type=user_id
```

## 添加群成员

```
POST /open-apis/im/v1/chats/{chat_id}/members
Body: {"member_id_type": "user_id", "member_ids": ["ou_xxx"]}
```

## 搜索消息

```
POST /open-apis/im/v1/messages/search
Body: {"query": "关键词", "page_size": 20}
```

## 获取会话消息列表

```
GET /open-apis/im/v1/messages?container_id_type=chat&container_id=oc_xxx&page_size=50
```

## 官方文档

- https://open.feishu.cn/document/server-docs/docs/im-v1/message/create
- https://open.feishu.cn/document/server-docs/docs/im-v1/image/create
- https://open.feishu.cn/document/server-docs/docs/im-v1/chat/list
- 飞书开放平台 AI 助手：https://open.feishu.cn/app/ai/playground?from=nav
