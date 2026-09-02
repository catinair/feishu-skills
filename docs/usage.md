# Usage

## 初始化

### 1. 凭证

在配置目录提供 `credentials.json`（本地开发放在 `config/`，平台环境由 resolver 自动选择 `runtime_assets/`）：

```json
{
  "appId": "cli_xxx",
  "appSecret": "xxx",
  "brand": "feishu"
}
```

> **云模式凭证策略**：当前项目默认使用云模式，`refresh_token` **不会**写入 `credentials.json`，而是保存在名为 `feishu-skills-refreshtoken` 的 Bitable `token_backup` 表中。首次授权前必须先运行 `python3 feishu-setup/setup_bitable_infrastructure.py` 创建该基础设施。`credentials.json` 中只保留 `userAccessToken` 作为非权威本地缓存，过期后由 `CloudTokenManager` 自动从 Bitable 读取 `refresh_token` 并刷新。因此配置示例中不应出现 `refreshToken` 或 `refreshTokenExpire` 字段。

也支持环境变量：

```bash
export FEISHU_APP_ID="cli_xxx"
export FEISHU_APP_SECRET="xxx"
export FEISHU_BRAND="feishu"
```

### 2. 运行配置

编辑 `config/settings.json`（OAuth 授权后会自动填充）：

```json
{
  "default_identity": "user",
  "user": {
    "name": "你的飞书名字"
  }
}
```

默认工作目录与白名单维护在 `config/risk_policy.json`：

```json
{
  "workspace": {
    "trusted_folder_tokens": [
      {
        "token": "fld_xxx",
        "label": "feishu-skills 默认工作区",
        "default": true
      }
    ]
  }
}
```

> **推荐做法**：默认工作区文件夹由 **tenant（应用）身份**创建，再通过 `perm_doc_share.py --identity tenant` 共享给当前用户 `full_access`。这样 tenant 身份创建的云文档/表格/Base 可以落在一个用户有权限的文件夹里，避免切换身份后用户找不到资源。

### 3. 权限

- 权限清单通过 OAuth 授权自动同步到 `config/permissions.json`
- 也可手动运行脚本同步：

```bash
python3 feishu-auth/auth_sync_permissions.py
```

- 若目标文件里没有 user scopes，脚本会尝试从凭证文件中的 `userScopes` 回填

### 4. 权限诊断

当接口报权限不足时，运行诊断工具快速定位缺口：

```bash
# 默认视图：按 config/settings.json 中的 default_identity 判断能力域是否就绪
python3 feishu-auth/auth_scopes.py

# 完整视图：BOTH 身份端点要求 tenant + user 权限同时满足
python3 feishu-auth/auth_scopes.py --full

# 只看某个域
python3 feishu-auth/auth_scopes.py --domain im
python3 feishu-auth/auth_scopes.py --domain calendar --full
```

输出包括：
- 各领域（多维表格、云空间、IM、文档等）权限就绪状态
- 缺失的 scope 及对应的接口
- tenant / user scope 矩阵对比

默认视图按当前 `default_identity` 判断，避免 user 模式下因 tenant scope 缺失而显示大量“未就绪”。如需评估双身份均就绪的完整能力，使用 `--full`。

结合 `reference/error_codes.md` 的排查建议，可以快速判断是需要重新授权还是申请新权限。

## 凭证加载入口

所有 CLI 脚本默认通过 `create_client()` 读取凭证，无需手动指定路径：

```bash
python3 feishu-im/im_list_chats.py
```

`create_client()` 的查找顺序：
1. 环境变量 `FEISHU_CONFIG_DIR` 指定的目录（显式覆盖）
2. 平台运行时目录 `<workspace>/runtime_assets/feishu-skills/`（当 skill 位于 `<workspace>/skills/feishu-skills/` 时，workspace 由 SKILL_ROOT 自动推导）
3. `<skill-root>/config/credentials.json`
4. 环境变量 `FEISHU_APP_ID` / `FEISHU_APP_SECRET`

### 平台运行时持久化

在 OpenCode 等平台上，skill 安装目录可能每会话重建。此时凭证与运行配置会自动写到 workspace 级的持久目录：

```text
<workspace>/runtime_assets/feishu-skills/
```

本地开发或普通部署时，继续沿用 `<skill-root>/config/`。

## 通用 CLI 约定

所有单操作 CLI 和大部分 Shortcut 遵循统一的参数约定：

| 参数 | 说明 | 适用场景 |
|------|------|----------|
| `--yes` / `-y` | 跳过交互式确认 | 写操作、删除操作等默认需要确认的脚本 |
| `--raw` | 输出完整 API 原始响应 | 默认摘要输出不满足调试需求时 |
| `--identity user\|tenant` | 强制使用 user 或 tenant 身份调用 | 支持双身份的脚本（如 IM 发送、日程创建、权限授权） |

### 默认摘要输出

为减少 AI context 噪音，**写操作类 CLI 默认输出精简摘要**，例如：

```json
{
  "status": "ok",
  "document_id": "doxcnxxx",
  "title": "测试文档"
}
```

如需完整响应，加 `--raw`：

```bash
python3 feishu-doc/doc_create.py --title "测试" --raw
python3 feishu-im/im_send_message.py --receive-id oc_xxx --type chat_id --text "hi" --raw
```

### 身份选择：user vs tenant

项目默认身份为 `user`（由 `config/settings.json` 的 `default_identity` 控制）。两种身份的区别：

- **user 身份**：使用 `user_access_token`，代表当前授权用户操作。适合：
  - 发送个人身份消息
  - 在用户主日历创建日程
  - 操作用户个人资源

- **tenant 身份**：使用 `tenant_access_token`，代表应用/机器人操作。适合：
  - 以机器人身份发消息
  - 创建群聊（`im_create_chat.py` 仅支持 tenant）
  - 操作应用公共资源

显式切换身份：

```bash
# 强制以用户身份发送消息
python3 feishu-im/im_send_message.py --receive-id oc_xxx --type chat_id --text "hi" --identity user

# 强制以应用身份发送消息
python3 feishu-im/im_send_message.py --receive-id oc_xxx --type chat_id --text "hi" --identity tenant

# 在用户主日历创建日程
python3 feishu-calendar/calendar_create_event.py "周会" --start "2026-04-25 14:00" --end "2026-04-25 15:00" --identity user

# 给 tenant 创建的文件夹授权给用户
python3 feishu-perm/perm_doc_share.py \
  --token fld_xxx \
  --type folder \
  --member-id ou_xxx \
  --member-type openid \
  --perm full_access \
  --identity tenant
```

**注意**：
- 若脚本不支持 `--identity`，说明该 API 仅支持单一身份（如 `im_create_chat.py` 仅 tenant）；
- 身份切换受权限约束，若对应 scope 未开通会报权限预检错误；
- 调用时可在 stderr 看到 `_resolve_identity()` 打印的身份决策日志，便于排查。

---

## 常见运行方式

### 单操作 CLI

```bash
# 只读操作
python3 feishu-im/im_list_chats.py
python3 feishu-doc/doc_create.py --title "测试文档"

# Base 操作支持从 URL 自动提取 token
python3 feishu-base/base_query.py --app base_token --table table_id
python3 feishu-base/base_query.py \
  --app "https://xxx.feishu.cn/base/APP_TOKEN?table=TABLE_ID"

# 写操作默认会提示确认，加 --yes 可跳过
python3 feishu-base/base_delete.py --app base_token --table tblxxx --record recxxx --yes
```

### 组合型 Shortcut

```bash
# 导出多维表格到 CSV
python3 shortcuts/shortcut_base_export_csv.py \
  --app base_token --table table_id --output data.csv

# 从 CSV 导入到多维表格
python3 shortcuts/shortcut_base_import_csv.py \
  --app base_token --table table_id --input data.csv

# 创建文档并分享到群
python3 shortcuts/shortcut_share_doc.py --title "会议纪要" --chat-id oc_xxx
```

## 配置修改入口

- 默认工作目录与白名单：`config/risk_policy.json`
- 轻量运行配置：`config/settings.json`
- 应用权限：`config/permissions.json`
- 权限同步脚本：`feishu-auth/auth_sync_permissions.py`
- 权限诊断脚本：`feishu-auth/auth_scopes.py`

## 文档入口

- 架构说明：`docs/architecture.md`
- 规则说明：`docs/policies.md`
- 飞书 API 备查：`reference/`
