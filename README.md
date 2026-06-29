# 飞书 Skill 集合

纯 Python 标准库实现的飞书 Skill 集合，覆盖文档、云空间、IM、多维表格、日程、通讯录、妙记等能力。

---

## 安装

提供两种安装方式。

### 方式一：Git Clone

适用于可访问飞书开放平台的网络环境，且本地有 Git 工具。

```bash
git clone https://github.com/catinair/feishu-skills.git
cd feishu-skills
```

后续更新：

```bash
cd feishu-skills && git pull
```

`custom/` 目录中的自定义内容不会被更新覆盖。

### 方式二：手动下载 ZIP

适用于无法使用 Git 的场景。

1. 打开仓库页面：https://github.com/catinair/feishu-skills
2. 点击 **Code** → **Download ZIP**，下载源码包
3. 解压到本地目录

> ZIP 包不含 Git 历史，后续更新需重新下载。

---

## 快速开始

安装后，AI 会自动检测配置状态并引导完成。也可以手动检测：

```bash
python3 feishu-setup/setup_check.py
```

用户只需提供 **appId + appSecret**，其余全部自动完成：

1. OAuth 授权 -> 获取 user_access_token
2. 自动写入 settings.json（用户信息）和 permissions.json（权限清单）
3. 完成后即可使用所有功能

完整引导见 [feishu-setup/SKILL.md](feishu-setup/SKILL.md)。

### 运行一个脚本

```bash
python3 feishu-im/im_list_chats.py
python3 feishu-doc/doc_create.py --title "测试文档"
python3 shortcuts/shortcut_base_export_csv.py --app base_token --table table_id --output data.csv
```

---

## 配置入口

- `config/settings.json`：轻量运行配置
- `config/permissions.json`：应用权限快照（授权时自动同步）
- `config/risk_policy.json`：默认工作目录、白名单与可执行风险策略

### 配置目录优先级

配置文件默认存放在 `<skill-root>/config/`。可通过 `FEISHU_CONFIG_DIR` 环境变量显式覆盖：

```bash
export FEISHU_CONFIG_DIR=/path/to/custom/config
```

详见 [docs/usage.md](docs/usage.md)。

---

## 身份与权限

- 默认身份为 `user`，兼容 `tenant`
- 默认身份由 `config/settings.json` 的 `default_identity` 控制
- OAuth 授权后自动同步 tenant scopes 到 `config/permissions.json`，也可手动运行 `python3 feishu-auth/auth_sync_permissions.py`
- OAuth 授权与续期响应中的实际 user scopes 会写入凭证文件的 `userScopes` 字段（通过 resolver 自动定位），供权限同步脚本回填

---

## 可选依赖

核心功能仅依赖 Python 标准库，无需 `pip install`。以下功能在安装对应库后体验更佳：

| 功能 | 可选库 | 说明 |
|------|--------|------|
| 画板下载自动裁剪边缘空白 | `Pillow` | 未安装时保留原图，不影响下载 |

---

## 项目结构

```text
feishu-skills/
├── config/         # 机器读取配置
├── custom/         # 用户自定义扩展（gitignore，拉取更新不受影响）
├── docs/           # 人类阅读文档
├── reference/      # 飞书 API 备查资料
├── feishu_common/  # 共享运行时代码
├── feishu-setup/   # 配置引导与环境检测
├── feishu-*/       # 各领域单操作 CLI
└── shortcuts/      # 跨领域组合工作流
```

## 自定义扩展

`custom/` 目录用于存放你的自定义脚本或子 skill。此目录已加入 `.gitignore`，上游仓库更新时直接 `git pull` 不会影响你的自定义内容。详见 [custom/README.md](custom/README.md)。

## 参考文档

- 配置引导：[feishu-setup/SKILL.md](feishu-setup/SKILL.md)（新用户从这里开始）
- 项目架构：[docs/architecture.md](docs/architecture.md)
- 使用方式：[docs/usage.md](docs/usage.md)
- 执行规则：[docs/policies.md](docs/policies.md)
- 飞书接口备查：`reference/`

---

## 免责声明

本项目为社区开源项目，**非飞书官方项目**，与飞书开放平台（Feishu Open Platform）无任何隶属、关联或合作关系。本项目的维护者不隶属于飞书或其母公司。使用本项目所产生的任何风险由使用者自行承担。飞书相关商标及服务名称归其各自所有者所有。
