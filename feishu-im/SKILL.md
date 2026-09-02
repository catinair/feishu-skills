---
name: feishu-im
version: 1.3.0
description: |
  飞书 IM 技能：发送消息、创建群聊、列出群聊、上传图片、群成员管理、群信息查询、搜索消息。
  纯 Python 标准库（Pillow 可选，用于画板图片裁剪）。
metadata:
  requires:
    bins: ["python3"]
    files: ["feishu-im/im_send_message.py", "feishu-im/im_list_chats.py", "feishu-im/im_search_chats.py", "feishu-im/im_create_chat.py", "feishu-im/im_upload_image.py", "feishu-im/im_chat_info.py", "feishu-im/im_chat_members.py", "feishu-im/im_chat_add_members.py", "feishu-im/im_chat_update.py", "feishu-im/im_messages_search.py", "feishu-im/im_messages_list.py", "feishu-im/im_messages_reply.py", "config/credentials.json"]
---

# feishu-im -- 飞书 IM 技能

## 权限要求

| 脚本 | 所需权限 | 身份支持 | 状态 |
|------|---------|----------|------|
| im_send_message.py | `im:message`（user）或 `im:message:send_as_bot`（tenant/app） | `user` / `tenant` | 已开通 |
| im_list_chats.py | `im:chat:readonly` | `both` | 已开通 |
| im_search_chats.py | `im:chat`（user）或 `im:chat:readonly`（tenant） | `both` | 已开通 |
| im_create_chat.py | `im:chat` | `app_only` | 已开通 |
| im_upload_image.py | `im:resource` | `app_only` | 已开通 |
| im_chat_info.py | `im:chat:readonly` | `both` | 已开通 |
| im_chat_members.py | `im:chat:readonly` 或 `im:chat.members:read` | `both` | 已开通 |
| im_chat_add_members.py | `im:chat:member:operate` 或 `im:chat` | `both` | 需确认 |
| im_chat_update.py | `im:chat` | `both` | 已开通 |
| im_messages_search.py | `search:message` / `contact:user.basic_profile:readonly` | `user_only` | **需申请** |
| im_messages_list.py | `im:message`（user）或 `im:message:readonly`（tenant） | `both` | 已开通 |
| im_messages_reply.py | `im:message`（user）或 `im:message:send_as_bot`（tenant） | `both` | 已开通 |

## 身份说明

IM 发送/回复类脚本支持两种调用身份：

- **user 身份（默认）**：消息以当前授权用户个人身份发出，`sender.sender_type = "user"`。需要 user scope `im:message`。
- **tenant/app 身份**：消息以应用机器人身份发出，`sender.sender_type = "app"`。需要 tenant scope `im:message:send_as_bot`。

默认身份由 `config/settings.json` 中的 `default_identity` 控制。也可以在调用时显式指定：

```bash
# 默认按 settings.json 的 default_identity
python3 feishu-im/im_send_message.py --receive-id oc_xxx --type chat_id --text "你好"

# 强制以用户身份发送
python3 feishu-im/im_send_message.py --receive-id oc_xxx --type chat_id --text "你好" --identity user

# 强制以应用机器人身份发送
python3 feishu-im/im_send_message.py --receive-id oc_xxx --type chat_id --text "你好" --identity tenant
```

**注意**：`im_create_chat.py` 仅支持 tenant/app 身份（飞书 API 限制），不受 `--identity user` 影响。

## 输出说明

写操作类 CLI（如 `im_send_message.py`、`im_chat_update.py`）默认输出精简摘要，便于 AI 消费。如需完整 API 原始响应，请加 `--raw`：

```bash
python3 feishu-im/im_send_message.py --receive-id oc_xxx --type chat_id --text "你好" --raw
```

## 快捷命令

### 列出群聊

```bash
python3 feishu-im/im_list_chats.py
```

### 搜索群组

```bash
# 按关键字搜索（含未加入的公开群）
python3 feishu-im/im_search_chats.py --query "全员MVP"

# 仅搜索未加入的公开群
python3 feishu-im/im_search_chats.py --query "项目" --search-types public_not_joined

# 指定身份
python3 feishu-im/im_search_chats.py --query "项目" --identity user
```

### 创建群聊

```bash
python3 feishu-im/im_create_chat.py --name "项目群" --description "项目沟通群"
```

### 发送文本消息

```bash
python3 feishu-im/im_send_message.py \
  --receive-id oc_xxx \
  --type chat_id \
  --text "大家好，这是测试消息"
```

### 发送富文本消息

```bash
python3 feishu-im/im_send_message.py \
  --receive-id oc_xxx \
  --type chat_id \
  --title "通知" \
  --post-lines '[[{"tag":"text","text":"项目已上线"}],[{"tag":"a","text":"查看详情","href":"https://feishu.cn"}]]'
```

### 上传图片

```bash
python3 feishu-im/im_upload_image.py --path ./screenshot.png
```

### 获取群详情

```bash
python3 feishu-im/im_chat_info.py --chat-id oc_xxx
```

### 查询群成员

```bash
python3 feishu-im/im_chat_members.py --chat-id oc_xxx --user-id-type user_id
```

### 拉人进群

```bash
python3 feishu-im/im_chat_add_members.py --chat-id oc_xxx --members your_user_id --user-id-type user_id
```

### 转让群主

```bash
python3 feishu-im/im_chat_update.py --chat-id oc_xxx --owner-id ou_xxx
```

### 修改群名

```bash
python3 feishu-im/im_chat_update.py --chat-id oc_xxx --name "新群名"
```

### 搜索消息

```bash
# 按关键词搜索
python3 feishu-im/im_messages_search.py --query "项目进展"

# 限定群组和发送者
python3 feishu-im/im_messages_search.py \
  --query "周报" \
  --chat-ids "oc_xxx,oc_yyy" \
  --senders "ou_xxx"

# 限定时间范围
python3 feishu-im/im_messages_search.py \
  --query "会议" \
  --start "2026-01-01T00:00:00+08:00" \
  --end "2026-01-31T23:59:59+08:00"
```

**注意**：消息搜索需要 `search:message` 权限，默认走 user 身份。

## 接收者类型

| type | 说明 | 获取方式 |
|------|------|---------|
| `chat_id` | 群聊 ID | 通过 `im_list_chats.py` 获取 |
| `open_id` | 用户 ID | 通过通讯录接口获取 |
