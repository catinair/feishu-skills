---
name: feishu-setup
version: 2.0.0
description: |
  飞书 Skills 配置引导。两阶段完成配置：飞书控制台操作 + 一条命令自动配置。
  当主 skill 检测到环境未就绪时路由至此。
metadata:
  status: active
  parent_skill: feishu-skills
  trigger_type: prerequisite
  requires:
    bins: ["python3"]
    files: ["feishu-setup/setup_check.py", "feishu-setup/setup_wizard.py"]
---

# feishu-setup -- 飞书 Skills 配置引导

## 快速检测

先运行检测脚本判断当前状态：

```bash
python3 feishu-setup/setup_check.py
```

`all_ready: true` 表示配置完成，无需操作。否则按下方引导补全缺失项。

---

## 阶段一：飞书控制台操作（手动，一次性）

> 以下操作在 [飞书开放平台](https://open.feishu.cn/app) 完成，每个应用只需做一次。

### 1. 创建自建应用

打开 [飞书开发者后台](https://open.feishu.cn/app) → 点击「创建企业自建应用」→ 填写名称和描述。

### 2. 开通权限

进入应用详情页 → 「权限管理」→ 搜索并开通以下 scope。

查看推荐 scope 列表（可复制粘贴批量搜索）：

```bash
python3 feishu-setup/setup_check.py --suggest-scopes
```

**最低可用**（建议一次性全开）：

| 类别 | scope | 说明 |
|------|-------|------|
| 基础 | `offline_access` | 刷新 token 必需 |
| 基础 | `auth:user.id:read` | 用户身份 |
| IM | `im:message` | 发送消息 |
| 通讯录 | `contact:user.base:readonly` | 通讯录查询 |

**完整推荐**：运行 `--suggest-scopes` 查看全部约 35 个免审 scope。

> 标注「需管理员审批」的 scope 可跳过，对应功能暂不可用，后续按需申请。

### 3. 配置重定向 URL

进入应用详情页 → 「安全设置」→ 「重定向 URL」，添加：

```
http://localhost:8080/callback
```

> 如果 8080 端口被占用，可换成其他端口（如 `http://localhost:19876/callback`），后续授权时需保持一致。

### 完成

记下 **App ID** 和 **App Secret**（在「凭证与基础信息」页面），进入阶段二。

---

## 阶段二：一条命令完成配置（自动）

```bash
python3 feishu-setup/setup_wizard.py --app-id <你的App_ID> --app-secret <你的App_Secret>
```

或交互式输入（Secret 不会显示在终端）：

```bash
python3 feishu-setup/setup_wizard.py
```

向导会自动完成：

1. 写入凭证 → `config/credentials.json`
2. 启动 OAuth 授权 → 浏览器完成授权后自动回调
3. 写入用户信息 → `config/settings.json`
4. 同步权限清单 → `config/permissions.json`
5. 生成风险策略 → `config/risk_policy.json`
6. 验证配置完整性

### 自定义重定向端口

如果阶段一配置了非 8080 端口：

```bash
python3 feishu-setup/setup_wizard.py --app-id cli_xxx --app-secret yyy \
  --redirect-uri http://localhost:19876/callback
```

### 仅写入凭证（已授权场景）

如果已有 token，只需写入凭证：

```bash
python3 feishu-setup/setup_wizard.py --app-id cli_xxx --app-secret yyy --skip-auth
```

---

## 常见问题

| 错误码 | 含义 | 解决方案 |
|--------|------|----------|
| 20029 | 重定向 URL 有误 | 检查飞书后台是否配置了 redirect_uri |
| 20002 | client_secret 无效 | 检查 App Secret 是否正确 |
| 20026 | refresh_token 无效 | 重新运行向导 |
| 99991679 | 缺少用户授权 scope | 重新运行向导（会自动请求新 scope） |

## 进阶用法

| 场景 | 命令 |
|------|------|
| 检查环境状态 | `python3 feishu-setup/setup_check.py` |
| 查看推荐 scope | `python3 feishu-setup/setup_check.py --suggest-scopes` |
| JSON 格式输出 | `python3 feishu-setup/setup_check.py --json` |
| 自动修复 risk_policy | `python3 feishu-setup/setup_check.py --fix` |
| 重新授权 | `python3 feishu-auth/auth_get_user_token.py` |
| 同步权限 | `python3 feishu-auth/auth_sync_permissions.py` |
