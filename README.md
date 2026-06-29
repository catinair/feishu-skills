# 飞书 Skill 集合

纯 Python 标准库的飞书开放平台 CLI 工具集——核心功能零依赖，覆盖文档、电子表格、云空间、IM、多维表格、知识库、日程、通讯录、妙记等能力。

## 为什么选择本项目？

飞书官方 CLI（[lark-cli](https://github.com/larksuite/cli)，Go 实现）功能完整，但在权限管理上有一个长期未修的痛点：

- 创建应用时**默认申请所有常用权限**，管理员看到大列表直接驳回
- 即使按业务域指定授权范围，实际 OAuth 请求仍可能带上全量 scope
- 权限不足时只返回通用 403，**不告诉你缺哪个 scope**

这些问题截至 v1.0.59 仍未修复。

本项目的解法是**权限最小化 + 脚本自律**：

| 特性 | 说明 |
|------|------|
| **最小权限申请** | OAuth 默认只请求 ~35 个精选免审 scope，高敏权限（如 `drive:file`）默认不申请 |
| **精确 scope 控制** | 支持 `--minimal`（仅 `offline_access`）和 `--scope`（手动指定） |
| **预检诊断** | 调用前检查权限，缺失时给出**具体 scope 名称**和审批指引，而非通用 403 |
| **脚本自律** | `risk_policy.json` 控制写操作确认策略，可配置信任文件夹/用户/群聊，防止 AI Agent 误操作 |
| **零依赖** | 纯 Python 标准库（≥3.9），Pillow 仅作为画板图片裁剪的可选依赖 |

## 快速开始

**前置要求**：Python ≥ 3.9，核心功能无 pip 依赖。

```bash
git clone https://github.com/catinair/feishu-skills.git
cd feishu-skills
python3 feishu-setup/setup_check.py
```

你只需提供 **appId + appSecret**，后续 OAuth 授权、用户信息写入、权限清单同步全部自动完成。

运行一个脚本试试：

```bash
python3 feishu-im/im_list_chats.py
python3 feishu-doc/doc_create.py --title "测试文档"
python3 shortcuts/shortcut_base_export_csv.py --app base_token --table table_id --output data.csv
```

## 功能概览

| 领域 | 能力 |
|------|------|
| **云文档** (`feishu-doc/`) | 创建、写入、导出、评论、插入媒体/内容块 |
| **电子表格** (`feishu-sheets/`) | 创建、写入、追加数据 |
| **云空间** (`feishu-drive/`) | 上传、下载、复制、移动、删除、新建文件夹 |
| **多维表格** (`feishu-base/`) | CRUD、字段/视图管理、CSV 导入导出、批量同步 |
| **IM 消息** (`feishu-im/`) | 发送消息、回复、创建/更新群聊、添加成员、上传图片 |
| **知识库** (`feishu-wiki/`) | 创建节点、管理空间 |
| **日程** (`feishu-calendar/`) | 创建/更新/删除日程、查询空闲时间、列表 |
| **通讯录** (`feishu-contact/`) | 搜索用户、查询部门、获取同事 |
| **妙记** (`feishu-minutes/`) | 导出妙记内容、上传媒体 |
| **权限** (`feishu-perm/`) | 分享文档、移除协作者 |
| **幻灯片** (`feishu-slides/`) | 上传图片媒体 |
| **任务** (`feishu-task/`) | 创建、更新、评论 |
| **跨域组合** (`shortcuts/`) | 一键分享文档、上传并发送、会议通知、群组通知、CSV 直写多维表格 |

每个脚本独立运行，通过 `--help` 查看参数。输出均为 JSON，方便 AI Agent 和脚本管道消费。

## 安装

### Git Clone

```bash
git clone https://github.com/catinair/feishu-skills.git
cd feishu-skills
```

后续更新：`git pull`。`custom/` 目录中的自定义内容不会被覆盖。

### 手动下载 ZIP

打开 [仓库页面](https://github.com/catinair/feishu-skills)，点击 **Code → Download ZIP** 下载源码包。

> ZIP 包不含 Git 历史，后续更新需重新下载。

## 配置入口

配置文件默认存放在 `<skill-root>/config/`，可通过 `FEISHU_CONFIG_DIR` 环境变量覆盖：

```bash
export FEISHU_CONFIG_DIR=/path/to/custom/config
```

| 文件 | 说明 |
|------|------|
| `credentials.json` | 应用凭证与 token（OAuth 自动写入） |
| `settings.json` | 默认身份、用户信息 |
| `permissions.json` | 已授权权限快照（授权时自动同步） |
| `risk_policy.json` | 信任文件夹/用户/群聊、写操作确认策略 |

详见 [docs/usage.md](docs/usage.md)。

## 与官方 lark-cli 的对比

| 维度 | lark-cli（官方） | feishu-skills（本项目） |
|------|-----------------|----------------------|
| **语言** | Go（需编译） | Python 标准库（脚本直跑） |
| **依赖** | 自我包含的二进制 | 核心零依赖，Pillow 可选 |
| **权限策略** | 默认申请全部常用 scope | 默认最小权限（~35 个免审 scope） |
| **权限错误** | 通用 403 | 指出缺失的 scope + 审批指引 |
| **写操作保护** | 无 | `risk_policy.json` 脚本自律 |
| **AI Agent 友好** | 非设计目标 | 所有输出 JSON、风控决策显式输出 |
| **安装方式** | `brew` / 编译 | `git clone` / ZIP |

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

`custom/` 用于存放你的自定义脚本或子 skill，已加入 `.gitignore`。详见 [custom/README.md](custom/README.md)。

## 参考文档

- 配置引导：[feishu-setup/SKILL.md](feishu-setup/SKILL.md)（新用户从这里开始）
- 项目架构：[docs/architecture.md](docs/architecture.md)
- 使用方式：[docs/usage.md](docs/usage.md)
- 执行规则：[docs/policies.md](docs/policies.md)
- 飞书 API 备查：`reference/`

## 免责声明

本项目为社区开源项目，**非飞书官方项目**，与飞书开放平台（Feishu Open Platform）无任何隶属、关联或合作关系。本项目的维护者不隶属于飞书或其母公司。使用本项目所产生的任何风险由使用者自行承担。飞书相关商标及服务名称归其各自所有者所有。
