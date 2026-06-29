# 飞书 Skill 集合

纯 Python 标准库的飞书开放平台 CLI 工具集——核心功能零依赖，覆盖文档、电子表格、云空间、IM、多维表格、知识库、日程、通讯录、妙记等能力。

## 为什么选择本项目？

### 起点：一次尴尬的权限审核

我第一次用飞书官方 CLI（[lark-cli](https://github.com/larksuite/cli)）时，走了它的快速配置路径——创建应用、授权、发版全自动完成。我点完确定才发现，它替我申请了一大批高敏权限，直接把发版请求送到了公司管理员那里。

管理员秒拒，批注：**"按照业务需求选择性申请接口权限。"**

我这才意识到问题：官方 CLI 的快速路径是为"管理员配合、走完整开放平台流程"的团队设计的。而我的场景更简单——我只想用最小权限跑几个自动化脚本，不想惊动管理员，更不想申请一堆我用不着的 scope。

### 两种不同的哲学

这不是谁对谁错，是设计重心不同：

- **官方 lark-cli**：一站式全能工具（200+ 命令、26 个 Agent Skills），重心是覆盖飞书尽可能多的能力，适合有管理员支持的正式团队
- **feishu-skills**：权限最小化优先的脚本集，重心是让个人开发者和 AI Agent 用最少的免审 scope 快速跑通常见自动化闭环

### 本项目的做法

**权限最小化 + 脚本自律**：

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
| **产品定位** | 一站式官方 CLI，200+ 命令、26 个 Agent Skills | 权限最小化优先的脚本集，124 个脚本 |
| **语言/依赖** | Go（`npx` / 源码安装） | Python 标准库，脚本直跑 |
| **初始化路径** | 推荐一键配置应用（`config init --new`） | 用户自己提供 appId/appSecret，不替用户创建应用 |
| **权限策略** | 提供 `--recommend`/`--domain`/`--scope` 筛选，快速路径偏向覆盖常用能力 | 默认最小权限（~35 个免审 scope），高敏权限默认不申请 |
| **权限诊断** | `auth check` / scope mismatch 检查 | 调用前预检，缺失时指出具体 scope + 审批指引 |
| **写操作保护** | strict mode / dry-run | `risk_policy.json` 脚本自律 + 信任文件夹/用户/群聊 |
| **AI Agent 友好** | 非设计目标 | 所有输出 JSON，风控决策显式输出到 stderr |
| **覆盖面** | 完整（18 个业务域，官方维护） | 覆盖常用域，但不如官方完整（个人项目） |

> **简单说**：官方 lark-cli 是飞书平台的"全功能瑞士军刀"；feishu-skills 是"最小权限螺丝刀"——不去替代全量能力，而是让免审小闭环场景更快、更透明、更可控。

### 暂未覆盖的领域

作为个人项目，以下飞书能力目前尚未接入（官方 lark-cli 已有对应 Skill）：

| 缺失领域 | 官方 Skill |
|----------|-----------|
| 审批 | `lark-approval` |
| 考勤 | `lark-attendance` |
| 邮箱 | `lark-mail` |
| OKR | `lark-okr` |
| 视频会议 | `lark-vc` |
| 白板/画板 | `lark-whiteboard` |
| 笔记 | `lark-note` |
| 事件订阅 | `lark-event` |
| 应用管理 | `lark-apps` |

已在覆盖域内的接口完整度也不如官方——比如 `feishu-doc/` 能创建、写入、导出、评论，但官方还支持文档模板、协作状态、版本对比等。

如果你需要这些能力，建议直接使用 [lark-cli](https://github.com/larksuite/cli)；如果你的场景是文档、表格、IM、多维表格、日历等常用域的免审小闭环，feishu-skills 会更轻量可控。

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
