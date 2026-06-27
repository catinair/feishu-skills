# 权限清单

本文档是权限说明快照，不再代表唯一真实来源。

当前项目正在从 tenant-first 迁移到 user-first / tenant-compatible 模式：

- 当前环境已开通权限请查看 `config/permissions.json`（OAuth 授权后自动同步）
- 可通过 `python3 feishu-auth/auth_sync_permissions.py` 手动刷新 tenant scopes

> **说明**：
> - 带 `*` 的 scope 表示 Python 项目当前已实际使用（对应 `feishu-*` 目录下的脚本）。
> - 未标注的 scope 表示应用已开通但 Python 项目尚未封装对应 CLI。

---

## Tenant Scopes（Bot 可用，共 114 项）

### 管理类
- admin:app.admin:check
- admin:app.admin_id:readonly

### 应用类
- application:application:self_manage
- application:bot.menu:readonly
- application:bot.menu:write

### 多维表格 Base
- base:app:create `*`
- base:app:update `*`
- base:collaborator:create `*`
- base:collaborator:read `*`
- base:field:read `*`
- base:form:update
- base:record:create `*`
- base:record:update `*`
- base:table:create `*`

### Bitable
- bitable:app `*`

### 画板
- board:whiteboard:node:create
- board:whiteboard:node:delete
- board:whiteboard:node:read
- board:whiteboard:node:update

### 日历
- calendar:calendar `*`
- calendar:calendar.event:create `*`
- calendar:calendar.event:read `*`
- calendar:calendar:readonly `*`
- calendar:timeoff

### 卡片
- cardkit:card:read
- cardkit:card:write
- cardkit:template:read

### 通讯录
- contact:contact.base:readonly `*`
- contact:department.base:readonly `*`
- contact:department.organize:readonly `*`
- contact:user.employee_id:readonly `*`

### 目录
- directory:employee:search

### 文档 Docs
- docs:doc `*`
- docs:document.comment:read
- docs:document.comment:write_only
- docs:document.content:read `*`
- docs:document.media:download `*`
- docs:document.media:upload `*`
- docs:document.subscription
- docs:document.subscription:read
- docs:document:copy `*`
- docs:document:import
- docs:permission.member `*`
- docs:permission.member:create `*`
- docs:permission.member:readonly `*`
- docs:permission.member:retrieve `*`
- docs:permission.member:update `*`
- docs:permission.setting
- docs:permission.setting:read
- docs:permission.setting:readonly

### 文档 Docx
- docx:document `*`
- docx:document.block:convert `*`
- docx:document:create `*`
- docx:document:readonly `*`

### 云空间 Drive
- drive:drive.metadata:readonly `*`
- drive:drive.search:readonly `*`
- drive:drive:version `*`
- drive:drive:version:readonly `*`
- drive:file `*`
- drive:file.meta.sec_label.read_only
- drive:file:upload `*`
- drive:file:view_record:readonly `*`

### 事件
- event:ip_list

### IM
- im:chat `*`
- im:chat.access_event.bot_p2p_chat:read
- im:chat.members:bot_access `*`
- im:chat.members:read `*`
- im:chat:read `*`
- im:chat:readonly `*`
- im:message `*`
- im:message.group_at_msg:readonly
- im:message.group_msg
- im:message.p2p_msg:readonly
- im:message.pins:read
- im:message.pins:write_only
- im:message.reactions:read
- im:message.reactions:write_only
- im:message:readonly
- im:message:recall
- im:message:send_as_bot `*`
- im:message:send_multi_users
- im:message:update
- im:resource `*`

### 妙记
- minutes:minutes.transcript:export `*`
- minutes:minutes:readonly `*`

### OKR
- okr:okr:readonly

### 电子表格
- sheets:spreadsheet `*`
- sheets:spreadsheet:create `*`
- sheets:spreadsheet:write_only `*`

### 云文档空间
- space:document.event:read
- space:document:retrieve `*`
- space:document:shortcut
- space:folder:create `*`

### 任务
- task:attachment:read
- task:attachment:write
- task:comment
- task:comment:read
- task:comment:readonly
- task:comment:write
- task:custom_field:read
- task:custom_field:write
- task:section:read
- task:section:write
- task:task
- task:task:read
- task:task:readonly
- task:task:write
- task:tasklist:read
- task:tasklist:write

### 视频会议
- vc:meeting.meetingevent:read
- vc:meeting:readonly

### 身份验证
- verification:verification_information:readonly

### 知识库
- wiki:wiki `*`
- wiki:wiki:readonly `*`

---

## User Scopes（需用户身份授权，共 68 项）

> 以下 scope 需通过 `user_access_token` 调用，Bot 身份不可用。
> Python 项目中，`contact_get.py` 和 `contact_departments.py` 在需要完整字段时会要求配置 user_access_token。

- bitable:app
- board:whiteboard:node:create
- board:whiteboard:node:read
- board:whiteboard:node:update
- calendar:calendar
- calendar:calendar:readonly
- contact:contact.base:readonly `*`
- contact:department.base:readonly `*`
- contact:user.base:readonly `*`
- contact:user.basic_profile:readonly `*`
- contact:user.email:readonly `*`
- contact:user.employee_id:readonly `*`
- contact:user.employee_number:read
- docs:doc
- docs:document.comment:read
- docs:document.media:upload
- docs:document.subscription
- docs:document.subscription:read
- docs:document:import
- docs:permission.member
- docs:permission.member:auth
- docs:permission.member:create
- docs:permission.member:readonly
- docs:permission.member:retrieve
- docs:permission.member:update
- docs:permission.setting
- docs:permission.setting:read
- docs:permission.setting:readonly
- docx:document
- docx:document.block:convert
- docx:document:readonly
- drive:drive.metadata:readonly
- drive:drive.search:readonly
- drive:drive:version
- drive:drive:version:readonly
- drive:file.meta.sec_label.read_only
- drive:file:view_record:readonly
- event:ip_list
- im:chat
- im:message
- mail:user_mailbox:readonly
- minutes:minutes.artifacts:read
- search:docs:read
- sheets:spreadsheet
- space:document.event:read
- space:document:retrieve
- space:document:shortcut
- space:folder:create
- task:attachment:read
- task:attachment:write
- task:comment
- task:comment:read
- task:comment:readonly
- task:comment:write
- task:custom_field:read
- task:custom_field:write
- task:section:read
- task:section:write
- task:task
- task:task:read
- task:task:readonly
- task:task:write
- task:tasklist:read
- task:tasklist:write
- vc:meeting.search:read
- vc:note:read
- wiki:wiki
- wiki:wiki:readonly

---

## 未开通但相关的 Scopes

以下 scope 应用当前未开通，但 Python 项目已通过替代方案实现对应功能：

- `drive:export:readonly` — 应用未开通此权限。Python 项目通过 `POST /open-apis/drive/v1/export_tasks` 导出任务 API 实现 docx/sheet 导出，该接口走 `drive:drive:version` 等已有权限，无需额外申请 `drive:export:readonly`。
