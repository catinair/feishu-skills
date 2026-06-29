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
        "label": "默认工作文件夹",
        "default": true
      }
    ]
  }
}
```

### 3. 权限

- 权限清单通过 OAuth 授权自动同步到 `config/permissions.json`
- 也可手动运行脚本同步：

```bash
python3 feishu-auth/auth_sync_permissions.py
```

- 若目标文件里没有 user scopes，脚本会尝试从凭证文件中的 `userScopes` 回填

## 凭证加载入口

所有 CLI 脚本默认通过 `create_client()` 读取凭证，无需手动指定路径：

```bash
python3 feishu-im/im_list_chats.py
```

`create_client()` 的查找顺序：
1. 环境变量 `FEISHU_CONFIG_DIR` 指定的目录（显式覆盖）
2. 平台运行时目录 `/home/user/workspace/runtime_assets/feishu-skills/`（当 skill 位于 `/home/user/workspace/skills/feishu-skills/` 时）
3. `<skill-root>/config/credentials.json`
4. 环境变量 `FEISHU_APP_ID` / `FEISHU_APP_SECRET`

### 平台运行时持久化

在部分 Agent 平台上，skill 安装目录可能每会话重建。此时凭证与运行配置会自动写到 workspace 级的持久目录：

```text
/home/user/workspace/runtime_assets/feishu-skills/
```

本地开发或普通部署时，继续沿用 `<skill-root>/config/`。

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

## 文档入口

- 架构说明：`docs/architecture.md`
- 规则说明：`docs/policies.md`
- 飞书 API 备查：`reference/`
