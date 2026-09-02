# Policies

## 文档与配置的边界

本项目将策略拆成两层：

1. `config/risk_policy.json`
   - 给机器读取
   - 适合白名单、确认规则、手动操作边界
2. `docs/policies.md`
   - 给人阅读
   - 解释规则为什么存在、应该如何维护

## 通用执行原则

### 只读操作

搜索、列出、读取、导出、获取元数据等操作默认无需确认。

### 写操作

创建、修改、删除、发送消息、上传文件等操作默认需要确认，除非命中了 `config/risk_policy.json` 中的受信任范围。

所有写操作 CLI 均支持 `--yes`（或 `-y`）参数显式跳过确认提示。在自动化脚本或流水线中使用时应显式传入该参数，避免交互式输入阻塞执行。

### 不可逆操作

以下操作应视为手动优先，建议不在自动化流程中一键执行：

- 文件删除
- 跨目录移动文件
- 群成员移除
- 批量删除文档/日程

即使传入 `--yes`，上述操作仍会在日志中输出被操作对象的标识，便于事后审计。

## 受信任范围

### 默认工作目录

只有落在受信任文件夹 token 白名单内的创建、上传、复制可以免二次确认。

### 测试联系人与测试群

私聊与群发消息只有命中受信任目标时才允许跳过额外确认。

## Token 使用原则

### tenant_access_token

兼容身份。

主要用于：

- 飞书 API 明确要求应用身份的接口
- user token 不支持或当前环境未授权的回退路径

### user_access_token

当前项目的改造目标是默认优先使用 user 身份。

优先使用场景包括：

- 妙记访问个人资源或 Bot 权限不足时
- 通讯录需要返回完整字段时
- 文档、云盘、任务等更适合按用户资源边界访问的场景

使用要求：

- 不回显完整 token
- `user_access_token` 可缓存在 `credentials.json` 中，但仅为非权威缓存（过期后由 `CloudTokenManager` 自动刷新）
- `refresh_token` **只保存在 Bitable**，不允许写入 `credentials.json`
- 过期后重新获取，不在仓库中长期存放失效 token

**refresh_token 有效期说明**：refresh_token 的有效期由飞书 OAuth 服务端决定，当前为 **604800 秒（7 天）**。每次使用 refresh_token 成功续期后，有效期会重新滚动 7 天。若连续超过 7 天没有触发续期，refresh_token 将失效，需要重新授权。

### 权限体系说明

飞书 OAuth 权限分为两类，对用户引导流程有直接影响：

**免审权限（auto-approved）**：应用创建后无需管理员审核即可生效。包括：
- `bitable:app` — 多维表格的创建、读写、管理
- `im:message` — 发送消息
- `contact:user.base:readonly` — 通讯录基础读取
- `offline_access` — refresh_token
- `auth:user.id:read` — 用户身份
- 其他可在 `feishu_common/_endpoint_registry.py` 中查看完整列表

**非免审权限**：需要企业管理员在飞书开放平台手动审核通过。包括：
- `drive:drive` / `drive:drive:readonly` — 云空间 Drive API
- `docx:document` — 文档读写
- 其他高级权限

**引导原则**：
- 免审权限应通过脚本自动调用 API 开通，无需引导用户操作
- 非免审权限应生成授权链接，用户点击确认即可
- AI 不应引导用户手动去开放平台开通权限，也不应将非免审权限的 API 报错误判为"缺少权限"而建议用户申请

**Bitable 权限**：通过 API 创建的 Bitable 默认为仅应用可访问（私有），无需额外调用 Drive 权限 API 设置。

### 凭证故障处理规则（禁止绕过）

任何与飞书 token 相关的故障——包括但不限于 `user_access_token` 过期、`refresh_token` 刷新失败、接口返回 `401` / `1000001` / `20038` / `99991672` 等错误——**只允许通过 skill 内置工具处理**：

1. 告知用户当前 token 状态及最可能的原因（如 refresh_token 已过期、已被消耗、或应用权限不足）。
2. 优先使用诊断脚本查看当前 token 状态：
   ```bash
   python3 feishu-auth/auth_diagnose_token.py
   python3 feishu-auth/auth_diagnose_token.py --refresh  # 需要手动触发刷新时
   ```
3. 引导用户重新完成授权：`python3 feishu-auth/auth_get_user_token.py`。
4. 在平台/Agent 环境下，使用 `--print-auth-url`、`--callback-url`、`--code`、`--json` 等参数完成非交互授权。

**严禁以下行为：**

- 禁止手写脚本直接调用飞书 token / refresh 接口做调试。
- 禁止手动读取、修改、覆盖 `credentials.json` 中的 `userAccessToken`、`userTokenExpire` 等字段。
- **禁止将 `refresh_token` 写入 `credentials.json` 或任何本地文件**；`refresh_token` 的唯一持久化位置是 Bitable `token_backup` 表。
- 禁止绕过 `feishu_common._client_core.FeishuClientCore` 的自动刷新逻辑，自行实现 token 刷新。
- 禁止用 `authen/v1/oidc/refresh_access_token` 等 v1 接口刷新 OAuth v2 流程获取的 token。

凭证文件的唯一合法写入方是 skill 内置工具（`auth_get_user_token.py`、`_client_core._save_user_token()`、以及 `auth_diagnose_token.py --refresh` 触发的 `_ensure_user_token()`）。`refresh_token` 的唯一合法写入方是 `feishu_common.cloud_token_manager.CloudTokenManager`。违反上述规则会消耗一次性 refresh_token、覆盖有效 token，导致问题循环恶化。

**自动刷新与竞态说明：**

- 业务脚本在需要 user token 时会自动调用 `_ensure_user_token()`，提前 30 分钟触发刷新；刷新由 `CloudTokenManager` 从 Bitable 读取最新 `refresh_token`，调用飞书刷新后，再将新的 `refresh_token` 追加写入 Bitable。
- `CloudTokenManager` 内置竞态重试：若当前 `refresh_token` 已被其他实例消耗，会自动重新读取 Bitable 最新记录并重试。
- `setup_check.py` 不触发 token 刷新，以避免多个入口同时消耗一次性 `refresh_token`。token 刷新唯一合法入口是业务脚本调用 `_ensure_user_token()` 或手动运行 `auth_diagnose_token.py --refresh`。

## 维护建议

### 当团队策略变化时

优先修改：

- `config/risk_policy.json`

必要时再同步更新本文档说明。

### 当项目扩展到新接口能力时

不要先改顶层文档，先判断新能力属于：

- 新配置
- 新规则
- 新说明
- 新 API 封装

按分层放入对应目录，避免再次出现职责混杂。

### 文档职责边界

- `SKILL.md` 只做 skill 元信息与能力入口，不承载执行规则
- 规则解释统一写入本文档，白名单和确认策略统一写入 `config/risk_policy.json`
