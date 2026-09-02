---
name: feishu-setup
version: 1.0.0
description: |
  飞书 Skills 配置引导。分步引导用户完成飞书应用创建/绑定、用户授权、本地配置文件生成。
  当主 skill 检测到环境未就绪时路由至此。
metadata:
  status: active
  parent_skill: feishu-skills
  trigger_type: prerequisite
  requires:
    bins: ["python3"]
    files: ["feishu-setup/setup_check.py", "feishu-setup/setup_bitable_infrastructure.py", "feishu-setup/setup_create_app.py", "feishu-setup/setup_verify.py"]
---

# feishu-setup -- 飞书 Skills 配置引导

> **📺 视频配置文档**：更直观的 step-by-step 录屏指引见 [ying-dao.feishu.cn/wiki/...](https://ying-dao.feishu.cn/wiki/Q3DKwDLpHiMFupk7mh3cJV3fnFd?from=from_lark_index_search&ccm_open_type=from_lark_index_search)。
> 下文为文字版 AI 引导流程，可与视频对照使用。

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

**注意**：`setup_check.py` 仅做状态检测，不会自动刷新过期的 `user_access_token`，以避免与业务脚本同时消耗一次性 `refresh_token` 产生竞态。业务脚本自身会在调用需要 user token 的接口时自动刷新。

## 二维码依赖与展示

`--qr` 参数依赖 `qrcode[pil]` 包生成二维码图片。默认环境通常未安装此包，`--qr` 会**静默跳过**二维码生成（不报错、不提示），用户只能看到链接。

**执行 `--begin --qr` 前的处理流程**：

1. 默认先不装依赖，直接运行 `--begin --qr --json`，将 `verification_url` 链接发给用户
2. 告知用户：「如果你需要扫码而非点击链接，我可以生成二维码图片」
3. 用户要求二维码时，安装依赖并重新发起：
   ```bash
   pip install qrcode[pil]
   # 重新运行 --begin --qr --json（会生成新的 device_code）
   ```
4. 输出中出现 `qr_path` 字段时，**用 `deliverfile` 将该图片交付给用户**，同时附上链接作为备选

**关键**：二维码图片生成在服务端临时目录，用户无法直接访问文件路径，必须通过 `deliverfile` 交付。

---

## Step 1: 创建/绑定飞书应用

**前置**：无。

通过 `setup_create_app.py` 自动创建或绑定飞书应用，用户扫码即可完成，无需手动去飞书开放平台后台操作。

**引导对话**：

> 需要创建一个飞书应用来获取 API 凭证。我来发起自动创建流程，你只需扫码确认。

**执行步骤**：

```bash
# 1. 发起应用创建/绑定
python3 feishu-setup/setup_create_app.py --begin --qr --json
```

输出中包含 `verification_url`（验证链接）和可能的 `qr_path`（二维码图片路径，需已安装 `qrcode[pil]`）。
优先将 `qr_path` 指向的二维码图片通过 `deliverfile` 交付给用户，同时附上链接作为备选。
若 `qr_path` 不存在（依赖未安装），则发送链接并告知用户可按需生成二维码（见「二维码依赖与展示」）。
用户打开链接或扫码后，选择「创建新应用」或「关联已有应用」，确认。

```bash
# 2. 用户确认后，轮询获取凭证
python3 feishu-setup/setup_create_app.py --poll --json
```

脚本自动将 `appId`、`appSecret`、`brand` 写入 `credentials.json`（通过 resolver 自动选择路径：平台环境写入 `runtime_assets/feishu-skills/`，本地写入 `config/`）。

**验证**：`poll` 返回 `ok: true` 且 `app_id` 以 `cli_` 开头。

**备选方案（手动创建）**：如自动创建不可用，可引导用户手动操作：

1. 打开 [飞书开发者后台](https://open.feishu.cn/app)
2. 点击「创建企业自建应用」
3. 在「凭证与基础信息」页面找到 **App ID** 和 **App Secret**
4. 用户提供后写入 `credentials.json`

**关于应用权限**：`setup_create_app.py` 使用 `archetype=PersonalAgent`，会自动分配默认权限集，大部分场景够用。如果后续 API 调用报权限错误，系统会自动诊断并生成 scope 申请链接（见「运行时权限错误诊断」一节）。

> **风险提示**：应用注册端点 `POST /oauth/v1/app/registration` 是 lark-cli 内部端点，非飞书公开 API，未来可能变更。

---

## Step 1.5: 开通 Bitable 基础设施所需权限

**前置**：Step 1 完成（需 `appId`/`appSecret`）。

应用创建后、Bitable 基础设施创建前，**只需开通 Bitable 基础设施创建所需的 6 个免审权限**，不要申请全量权限。

**6 个必需免审权限**：
- `bitable:app`
- `base:app:create`
- `base:table:create`
- `base:block:create`
- `base:record:create`
- `base:record:update`

**执行步骤**：

1. 生成这 6 个权限的一键开通链接：
   ```bash
   python3 feishu-setup/setup_scopes.py --minimal
   ```
   脚本输出一个短链接（仅含 6 个 scope），将链接发给用户，告知「点击链接打开飞书开放平台权限申请页，确认即可」。

2. 用户确认后，同步权限清单：
   ```bash
   python3 feishu-auth/auth_sync_permissions.py
   ```

**约束（重要）**：
- **本阶段只申请上述 6 个权限**，不要运行 `setup_scopes.py` 的 `--json` / `--apply` / 无参数模式——那些会生成包含全部（约 160 项）权限的链接，其中大量是后续阶段才需要、且需管理员审批的权限。
- `setup_scopes.py` 的全量模式（`--json` / `--apply`）保留给后续「运行时权限错误诊断」或需要扩展能力域时使用，不在 Step 1.5 使用。

---

## Step 2: 创建 Bitable 基础设施（云模式必需）

**前置**：Step 1、Step 1.5 完成（需 `appId`/`appSecret` + 所需免审权限已开通）。

在云模式下，`refresh_token` **只保存在 Bitable**，不会写入 `credentials.json`。本步骤创建一个归应用所有的多维表格，专门用于存储 `refresh_token`。每次刷新都会在该表中**追加一条新记录**，读取时取最新一条。

运行：

```bash
python3 feishu-setup/setup_bitable_infrastructure.py
```

按提示确认后，脚本会：
1. 检查应用是否已开通所需 tenant Bitable 权限
2. 创建一个名为 `feishu-skills-refreshtoken` 的多维表格（通过 API 创建默认即为仅应用可访问）
3. 在其中创建 `token_backup` 表
4. 将 `app_token` 和 `table_id` 写入 `settings.json`
5. 如果 `credentials.json` 中已有 `refresh_token`，会将其追加到 Bitable 并清理本地字段

> 若已创建的 Bitable 需要手动收紧权限，可在飞书客户端中操作。

如果已经创建过，再次运行会跳过并返回已有配置，同时补录当前本地 `refresh_token`（如有）。如需强制重建：

```bash
python3 feishu-setup/setup_bitable_infrastructure.py --force --yes
```

**注意**：`--force` 会创建新的多维表格，旧表中的备份数据不会自动迁移。

**注意**：云模式下 `credentials.json` 不应包含 `refreshToken`/`refreshTokenExpire`。如果 `setup_check` 提示需要迁移，请再次运行本脚本。

**创建 Bitable 基础设施必需的 tenant scopes（应用身份）**：
- `base:app:create` — 创建多维表格
- `base:table:create` — 创建数据表
- `base:block:create` — 创建字段
- `base:record:create` — 新增记录
- `base:record:update` — 更新记录
- `bitable:app` — 多维表格全部操作（用户身份）

> 注意：`drive:drive` 等云空间权限与创建 Bitable 基础设施无关。如果之前为了清理重复表而开通，可以继续保留；首次创建时不需要。

**reuse-first 行为**：当 `settings.json` 中尚未记录 Bitable 基础设施时，脚本会尝试搜索 Drive，查找名为 `feishu-skills-refreshtoken` 且包含 `token_backup` 表及当前 `app_id` 记录的多维表格。找到后会直接复用并写回 `settings.json`，实现本地与平台环境共享同一套 Bitable。如果应用没有 Drive 搜索类权限，搜索会失败并直接创建新表，不会阻塞 setup。搜索过程和每个候选的跳过原因都会输出到 stderr，方便 AI/用户排查。

**脚本输出字段说明（JSON）**：
- `created`: `true`/`false` 是否新建
- `reason`: 操作原因，如 `infrastructure already exists`、`reused existing Bitable from drive`、`created new Bitable`
- `tenant_scopes_ok`: tenant scope 检查是否通过
- `missing_scopes`: 缺失的必需 scope 列表
- `backup_succeeded`: 是否成功把本地 `refresh_token` 备份到 Bitable
- `local_refresh_token_stripped`: 是否已清理 `credentials.json` 中的本地 RT 字段
- `infrastructure.app_token`: Bitable 应用 token
- `infrastructure.tables.token_backup`: `token_backup` 表 ID
- `error`: 失败时的错误信息

---

## Step 3: 用户授权

**前置**：Step 1、Step 1.5、Step 2 完成。

使用 Device Flow 获取 `user_access_token`，用户扫码/点击链接即可完成授权，无需配置重定向 URL。

**方式一：Device Flow（推荐，适用于所有环境）**

```bash
# 1. 发起授权
python3 feishu-auth/auth_device_flow.py --begin --qr --json
```

输出中包含 `verification_url`（验证链接）、`user_code`（授权码）和可能的 `qr_path`（二维码图片路径，需已安装 `qrcode[pil]`）。
优先将 `qr_path` 指向的二维码图片通过 `deliverfile` 交付给用户，同时附上链接和授权码作为备选。
若 `qr_path` 不存在（依赖未安装），则发送链接和授权码，并告知用户可按需生成二维码（见「二维码依赖与展示」）。
用户点击/扫码确认授权。

```bash
# 2. 用户确认后，轮询获取 token 并持久化
python3 feishu-auth/auth_device_flow.py --poll --json
```

`--poll` 成功后自动完成：
- token 写入 `credentials.json` 和 Bitable（CloudTokenManager）
- settings.json 自动填充（用户信息）
- permissions.json 自动同步（tenant + user scopes）
- risk_policy.json 默认策略生成

**调试模式**：`--poll --no-save` 仅获取 token 不落盘。

**方式二：Authorization Code Flow（本地环境 fallback）**

本地开发环境中 `--auto-callback` 模式更方便，保留 `auth_get_user_token.py` 作为备选：

```bash
python3 feishu-auth/auth_get_user_token.py --print-auth-url --json
```

将 `auth_url` 发给用户，用户在浏览器完成授权后贴回回调 URL：

```bash
python3 feishu-auth/auth_get_user_token.py --callback-url "<完整URL>" --json
```

> 授权码模式需要预先在飞书开发者后台配置重定向 URL（如 `http://localhost:8080/callback`），Device Flow 不需要。

**关键知识（Device Flow）**：

- 设备授权端点：`POST /oauth/v1/device_authorization`（飞书公开 OAuth 标准端点）
- Token 交换：`POST /open-apis/authen/v2/oauth/token`，`grant_type=urn:ietf:params:oauth:grant-type:device_code`
- 默认 scope 包含 `offline_access` 及核心免审权限，可通过 `--scopes` 覆盖
- `qrcode[pil]` 是可选依赖，未安装时 `--qr` 会**静默跳过**（不报错、不提示）。详见「二维码依赖与展示」章节

**常见错误排查**：

| 错误码 | 含义 | 解决方案 |
|--------|------|----------|
| `authorization_pending` | 用户尚未确认 | 正常状态，继续等待 |
| `slow_down` | 轮询过快 | 脚本自动增大间隔 |
| `expired_token` | 授权码过期 | 重新运行 `--begin` |
| `access_denied` | 用户拒绝授权 | 重新运行 `--begin` |
| 99991679 | 缺少用户授权 scope | 重新授权并带上对应 scope |

---

## Step 4: 权限同步

**前置**：Step 3 完成。

> **通常无需手动运行**：`auth_device_flow.py --poll` 成功后会自动同步权限到 `permissions.json`。

如需手动同步：

```bash
python3 feishu-auth/auth_sync_permissions.py
```

这会将飞书开放平台上的 tenant scopes 同步到 `permissions.json`（通过 resolver 自动选择目录），并保留已有的 user scopes。

---

## Step 5: 配置 risk_policy.json（含默认工作区文件夹）

**前置**：Step 3 完成（需要能查询群聊列表）；tenant 侧已开通 `space:folder:create` 或 `drive:drive` 权限。

**说明**：user 模式下此步骤可选（用户自身飞书权限即信任边界）。tenant 模式下必须配置。

> `auth_device_flow.py --poll` 会自动生成默认 `risk_policy.json`（user 模式），如需自定义可继续配置。

### 5.1 创建默认工作区文件夹（推荐）

为减少身份切换，建议用 **tenant 身份**在云空间根目录创建一个固定文件夹，并共享给当前用户 `full_access`。之后 tenant 身份创建的云文档/表格/Base 默认落入该文件夹，用户可直接查看编辑。

```bash
# 1. 用 tenant 身份创建根文件夹
python3 feishu-drive/drive_create_folder.py "feishu-skills 默认工作区" --parent "" --identity tenant --yes

# 2. 用 tenant 身份把文件夹共享给当前用户 full_access
python3 feishu-perm/perm_doc_share.py \
  --token <上一步返回的 folder_token> \
  --type folder \
  --member-id <settings.json 中 user.open_id> \
  --member-type openid \
  --perm full_access \
  --identity tenant \
  --yes
```

> 如果 `drive_create_folder.py` 不支持 `--parent ""`，可直接用 `_request` 调用或后续补充 CLI；当前仓库已验证 tenant 身份调用 `drive/v1/files/create_folder` + `folder_token=""` 可行。

### 5.2 维护 risk_policy.json

将上一步得到的 folder_token 写入 `risk_policy.json`（通过 resolver 自动选择目录）：

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

同时按需配置：

- **信任用户/群聊** — 给这些用户/群发消息不需要确认
- **受限群聊** — 给这些群发消息需要额外确认

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

如需列出当前群聊：

```bash
python3 feishu-im/im_list_chats.py
```

---

## Step 6: 验证测试

**前置**：所有前置 Step 完成。

### 6.1 配置状态检查

```bash
python3 feishu-setup/setup_check.py --json
```

确认 `all_ready: true`、`credentials_valid: true`、`user_token_ready: true`、`bitable_infrastructure_ready: true`。

### 6.2 在线验证（推荐）

使用 `setup_verify.py` 对 token 进行联网验证，确保 token 真的有效（未被吊销、scope 足够）：

```bash
# 验证所有 token + API 端点
python3 feishu-setup/setup_verify.py --json

# 仅验证用户 token
python3 feishu-setup/setup_verify.py --user-only --json

# 仅验证租户 token
python3 feishu-setup/setup_verify.py --tenant-only --json
```

验证内容：

| 检查项 | 方法 |
|--------|------|
| 用户 token | `GET /open-apis/authen/v1/user_info` |
| 租户 token | `POST /oauth/v3/token` → `GET /open-apis/bot/v3/info` |
| Open API 端点 | 无 token 验证可达性 |

确认返回 `ok: true` 且 `user_name` 正确。

### 6.3 token 刷新链路验证

```bash
# 1. token 与 Bitable 状态诊断
python3 feishu-auth/auth_diagnose_token.py

# 2. 触发一次 user_access_token 刷新
python3 feishu-auth/auth_diagnose_token.py --refresh
```

`--refresh` 会确认从 Bitable 读取 refresh_token、刷新、写回新 RT 的整条链路正常。如果都成功，则配置完成。

> 如需额外验证具体业务接口（如发消息、查日程），可以单独运行对应领域的单操作 CLI，但验证测试阶段不建议直接调用 `im_list_chats` 或 `drive_list` 等可能返回成千上万条数据的列表接口。

---

## 运行时权限错误诊断

`feishu_common/_permission_helper.py` 提供运行时权限错误自动诊断能力。当 API 调用因权限不足失败时，系统会：

1. 自动识别权限错误码（`99991672`、`99991679`、`112005`、`1130001`）
2. 从错误响应中提取缺失的 scope
3. 生成飞书开发者控制台的权限申请链接

格式：`https://open.feishu.cn/page/scope-apply?clientID={app_id}&scopes={missing_scopes}`

用户点击链接即可在飞书开放平台直接申请缺失的权限。申请后需重新发布应用并重新授权。

---

## 平台环境

适用于 AI 运行在云端/平台环境，用户与 AI 通过对话交互的场景。

集群环境通常 `config/` 目录不可持久化，凭证和配置文件会自动写入 `runtime_assets/feishu-skills/`。运行任何命令时，注意 stderr 输出的 `CONFIG_ROOT` 和 `CREDENTIALS_PATH`，确认文件写入在正确的位置。

### 快速引导

1. 检查环境：
   ```bash
   python3 feishu-setup/setup_check.py --json
   ```
   根据输出判断缺少哪些配置，按需补充。

2. 如缺少凭证，发起自动创建应用：
   ```bash
   python3 feishu-setup/setup_create_app.py --begin --qr --json
   # 优先用 deliverfile 交付 qr_path 二维码图片给用户，附带链接备用
   # 用户扫码确认后
   python3 feishu-setup/setup_create_app.py --poll --json
   ```
   凭证自动写入 `credentials.json`。

3. 创建 Bitable 基础设施：
   ```bash
   python3 feishu-setup/setup_bitable_infrastructure.py
   ```

4. 用户授权（Device Flow）：
   ```bash
   python3 feishu-auth/auth_device_flow.py --begin --qr --json
   # 优先用 deliverfile 交付 qr_path 二维码图片给用户，附带链接和授权码备用
   # 用户扫码确认后
   python3 feishu-auth/auth_device_flow.py --poll --json
   ```

5. 验证：
   ```bash
   python3 feishu-setup/setup_check.py --json
   python3 feishu-setup/setup_verify.py --json
   ```

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

---

## 脚本清单

| 脚本 | 用途 |
|------|------|
| `setup_check.py` | 配置状态检测（离线） |
| `setup_create_app.py` | 创建/绑定飞书应用（Device Flow） |
| `setup_scopes.py` | 权限缺口检测与批量开通链接生成 |
| `setup_bitable_infrastructure.py` | 创建 Bitable 基础设施 |
| `setup_verify.py` | 在线验证 token 和 API 端点 |
| `setup_verify_structure.py` | 目录结构完整性检查 |
