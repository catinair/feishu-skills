---
name: feishu-setup
version: 1.0.0
description: |
  飞书 Skills 配置引导。分步引导用户完成飞书开放平台应用创建、权限配置、OAuth 授权、本地配置文件生成。
  当主 skill 检测到环境未就绪时路由至此。
metadata:
  status: active
  parent_skill: feishu-skills
  trigger_type: prerequisite
  requires:
    bins: ["python3"]
    files: ["feishu-setup/setup_check.py"]
---

# feishu-setup -- 飞书 Skills 配置引导

## 触发条件

满足以下任一条件时，主 skill 应将控制权交给此引导：

1. `python3 feishu-setup/setup_check.py --json` 中 `"all_ready": false`
2. 首次挂载或首次调用
3. 用户主动要求配置/重新配置

## 配置检测

在开始引导前，先运行检测脚本判断当前状态：

```bash
python3 feishu-setup/setup_check.py
```

根据输出的缺失项，跳转到对应 Step。已完成的步骤直接跳过。

---

## Step 0: 飞书开放平台应用创建

**前置**：此步骤为手动操作，无法自动化。

**引导对话**：

> 需要在飞书开放平台创建一个自建应用。请按以下步骤操作：
>
> 1. 打开 [飞书开发者后台](https://open.feishu.cn/app)
> 2. 点击「创建企业自建应用」
> 3. 填写应用名称（如「我的飞书助手」）和描述
> 4. 创建完成后，在「凭证与基础信息」页面找到 **App ID** 和 **App Secret**
>
> 拿到后请把 App ID 和 App Secret 告诉我。

**收到凭证后**：写入凭证文件（通过 resolver 自动选择路径：平台环境写入 `runtime_credentials/feishu-skills/`，本地写入 `config/`）：

```json
{
  "appId": "<用户提供的 App ID>",
  "appSecret": "<用户提供的 App Secret>",
  "brand": "feishu"
}
```

**验证**：检查 App ID 格式应为 `cli_` 开头。

---

## Step 1: 应用权限开通

**前置**：Step 0 完成。

**引导对话**：

> 接下来需要在飞书开发者后台给应用开通权限。进入应用详情页 → 「权限管理」，搜索并开通以下权限。
> 建议一次性全部开通，OAuth 授权时会自动获取所有已开通的权限。
>
> **IM：**
> - `im:message` — 发送消息（用户身份）
> - `im:chat` — 群聊管理（用户身份）
> - `im:chat:readonly` — 查询群聊（应用身份）
> - `im:message:send_as_bot` — 机器人发消息（应用身份）
>
> **通讯录：**
> - `contact:user.base:readonly` — 通讯录查询
> - `contact:contact.base:readonly` — 通讯录基础查询
> - `contact:user:search` — 搜索用户
> - `contact:department.base:readonly` — 部门查询
>
> **文档：**
> - `docx:document:readonly` — 读取文档
> - `docx:document` — 创建/编辑文档
> - `docx:document.block:convert` — 文档 block 转换
> - `docs:document.comment:read` — 读取评论
> - `docs:document.comment:create` — 创建评论
>
> **云空间：**
> - `drive:drive.search:readonly` — 搜索文件
> - `drive:drive.metadata:readonly` — 文件元数据
> - `drive:drive:version` — 导出文件
> - `drive:file:upload` — 上传文件
>
> **云空间（需管理员审批）：**
> - `drive:drive:readonly` — 下载文件
> - `drive:file` — 文件复制/移动/删除
>
> **表格：**
> - `sheets:spreadsheet` — 读写表格
> - `sheets:spreadsheet:create` — 创建表格
>
> **多维表格：**
> - `bitable:app` — 多维表格全部操作
>
> **知识库：**
> - `wiki:wiki:readonly` — 知识库读取
> - `wiki:wiki` — 知识库写入
>
> **日程：**
> - `calendar:calendar.event:read` — 查询日程
> - `calendar:calendar.event:create` — 创建日程
>
> **任务：**
> - `task:task:read` — 查询任务
> - `task:task:write` — 创建/更新任务
>
> **妙记：**
> - `minutes:minutes.artifacts:read` — 妙记转写
>
> **权限管理：**
> - `docs:permission.member:readonly` — 查询文档协作者
> - `docs:permission.member:create` — 添加文档协作者
>
> **其他：**
> - `offline_access` — 离线访问（获取 refresh_token 必需）
>
> 注意：上面列出的权限大部分可以免审开通。标注「需管理员审批」的权限需要企业管理员在后台审批后才能使用，首次配置时可以跳过。
> 无法开通的权限可以跳过，对应功能会不可用。后续需要时再申请审批。
>
> 开通完成后告诉我。

**重要提示（沉淀自调试经验）**：

飞书的 OAuth scope 名称与权限管理页面显示的名称**可能不同**。已知映射：

| 权限管理页面显示 | OAuth scope 名 |
|---|---|
| im:message.send_as_user | `im:message` |
| im:message.send_as_bot | `im:message:send_as_bot` |

如果授权后 scope 不生效，检查是否使用了正确的 OAuth scope 名。

---

## Step 2: 重定向 URL 配置

**前置**：Step 0 完成。

**引导对话**：

> 需要配置 OAuth 回调地址。进入应用详情页 → 「安全设置」 → 「重定向 URL」，添加：
>
> ```
> http://localhost:8080/callback
> ```
>
> 如果 8080 端口被占用，可以换成其他端口（如 `http://localhost:19876/callback`），但后面授权时需要保持一致。
>
> 配置完成后告诉我。

**注意**：此 URL 必须在发起 OAuth 授权**之前**配置好，否则会报错误码 `20029`（重定向 URL 有误）。

---

## Step 3: 配置 settings.json

**前置**：Step 0 完成。

**引导对话**：

> 请告诉我你的飞书名字（显示名称），我来配置本地用户信息。

**收到名字后**，查询通讯录获取用户 ID 等信息（如可用），写入 `settings.json`（通过 resolver 自动选择目录）：

```json
{
  "default_identity": "user",
  "user": {
    "name": "<用户提供的名字>",
    "user_id": "",
    "open_id": "",
    "department": "",
    "role": ""
  }
}
```

`user_id` 和 `open_id` 可在 OAuth 授权完成后自动填充。`default_identity` 默认为 `"user"`（用户身份优先），如需纯应用身份可改为 `"tenant"`。

---

## Step 4: OAuth 用户授权

**前置**：Step 0、Step 1、Step 2 完成。

这是最关键的步骤。使用 OAuth v2 流程获取 `user_access_token`。

**方式一：脚本引导（推荐）**

运行授权脚本，按提示操作：

```bash
python3 feishu-auth/auth_get_user_token.py
```

如果自定义了重定向端口：

```bash
python3 feishu-auth/auth_get_user_token.py --redirect-uri http://localhost:19876/callback
```

**重要**：脚本会将授权链接保存到 `config/_auth_url.txt`。请直接从该文件复制链接到浏览器，**不要从对话/终端输出中复制**——AI 或终端在复述长 URL 时可能引入不可见的拼写错误（如换行截断、字符替换），导致重定向 URL 不匹配报错 20029。

**方式二：带指定 scope 的授权**

如果需要一次性授权多个 scope，手动构造授权链接：

```python
import json, urllib.parse
from feishu_common._config_loader import load_credentials_data

creds, _ = load_credentials_data()
scopes = "offline_access im:message im:chat contact:user.base:readonly docx:document:readonly"
redirect_uri = "http://localhost:8080/callback"  # 或你配置的端口

auth_url = (
    f"https://accounts.feishu.cn/open-apis/authen/v1/authorize"
    f"?client_id={creds['appId']}"
    f"&redirect_uri={redirect_uri}"
    f"&scope={urllib.parse.quote(scopes, safe='')}"
)
print(auth_url)
```

**授权流程**：

1. 在浏览器中打开授权链接
2. 完成飞书授权
3. 浏览器跳转到 redirect_uri（页面会报错，正常的）
4. 从地址栏复制含 `?code=...` 的完整 URL
5. 脚本自动换取 token 并保存

**关键知识（OAuth v2）**：

- 授权页面：`https://accounts.feishu.cn/open-apis/authen/v1/authorize`
  - 参数用 `client_id`（不是 `app_id`）
- Token 交换：`POST /open-apis/authen/v2/oauth/token`
  - 请求体用 `client_id` + `client_secret`（不是 Authorization header）
- 响应格式：平级 JSON（不是嵌套在 `data` 下）
- 刷新 Token：同一个端点，`grant_type=refresh_token`

**常见错误排查**：

| 错误码 | 含义 | 解决方案 |
|--------|------|----------|
| 20029 | 重定向 URL 有误 | 检查飞书开发者后台是否配置了 redirect_uri。**注意**：如果 redirect_uri 已配置但仍报错，很可能是授权链接在复制过程中被截断或篡改——请从 `config/_auth_url.txt` 文件中直接复制链接，不要从对话或终端输出中复制 |
| 20002 | client_secret 无效 | 检查 credentials.json 中的 appSecret |
| 20026 | refresh_token 无效 | 旧 v1 token 无法用于 v2 接口，需重新授权 |
| 99991695 | 用户授权接口为历史版本 | 使用 v1 token 调用新接口会报此错，需用 v2 token |
| 99991679 | 缺少用户授权 scope | token 中没有所需 scope，重新授权并带上对应 scope |

---

## Step 5: 权限同步

**前置**：Step 4 完成。

同步应用已开通的 tenant 权限到本地：

```bash
python3 feishu-auth/auth_sync_permissions.py
```

这会将飞书开放平台上的 tenant scopes 同步到 `permissions.json`（通过 resolver 自动选择目录），并保留已有的 user scopes。

**注意**：OAuth 授权完成后，tenant scopes 会自动同步，通常无需手动运行此脚本。

---

## Step 6: 配置 risk_policy.json

**前置**：Step 4 完成（需要能查询群聊列表）。

**说明**：user 模式下此步骤可选（用户自身飞书权限即信任边界）。tenant 模式下必须配置。

**引导对话**：

> 需要配置操作风险策略。主要设置：
>
> 1. **信任文件夹** — 在这个文件夹内的创建操作不需要确认
> 2. **信任用户/群聊** — 给这些用户/群发消息不需要确认
> 3. **受限群聊** — 给这些群发消息需要额外确认
>
> 请告诉我：
> - 你的默认工作文件夹 URL 或 token（从飞书云空间链接中获取）
> - 你的测试群名称（用于调试发消息）

**收到信息后**，更新 `risk_policy.json`（通过 resolver 自动选择目录）中对应的字段。

如需列出当前群聊：

```bash
python3 feishu-im/im_list_chats.py
```

---

## Step 7: 验证测试

**前置**：所有前置 Step 完成。

运行环境检测：

```bash
python3 feishu-setup/setup_check.py
```

如果 `all_ready` 为 true，运行功能验证：

```bash
# 1. 通讯录查询（只读，安全）
python3 feishu-contact/contact_colleagues.py

# 2. 群聊列表（只读，安全）
python3 feishu-im/im_list_chats.py

# 3. 云空间文件列表（只读，安全）
python3 feishu-drive/drive_list.py
```

全部成功则配置完成。

---

## 完成交割

配置完成后，向用户确认：

> 飞书 Skills 配置完成！当前状态：
> - 应用凭证：已配置
> - 用户身份：已授权（{scope_count} 个权限）
> - 默认策略：{default_identity}
>
> 现在可以正常使用了。例如：
> - 「查一下我的同事」
> - 「列出我的群聊」
> - 「搜索飞书文档」
>
> 如需重新配置，随时说「重新配置飞书」。

---

## 附录：scope 命名对照表

飞书权限管理页面的名称与 OAuth scope 名称不总是一致。以下是已知的差异：

| 权限管理页面 | OAuth scope | 说明 |
|---|---|---|
| im:message.send_as_user | `im:message` | 用户身份发消息 |
| im:chat.members:read | `im:chat` | 群成员查询（用户身份） |
| im:chat:readonly | `im:chat:readonly` | 群聊查询（应用身份） |

完整的 scope 名称以 `permissions.json`（授权后自动生成，通过 resolver 自动定位）中的列表为准。
