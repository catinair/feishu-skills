# Architecture

## 目标

本项目是一个可扩展的飞书 skill 集合，核心目标有三个：

1. 保持单脚本可直接运行
2. 保持配置、策略、说明与运行时代码解耦
3. 在新增接口能力时，不需要重新调整整体目录

## 分层

### 1. 运行时代码

- `feishu_common/`
  - `_client_core.py` — HTTP 请求、Token 获取与缓存
  - `_client.py` — 组合所有领域 mixin 的 `FeishuClient` 入口
  - `_client_xxx.py` — 各领域 API 封装（doc/drive/im/base 等）
  - `_config_loader.py` — 统一加载配置；支持本地 `<skill-root>/config/` 与平台运行时 `/home/user/workspace/runtime_assets/<skill-name>/` 双路径，可通过 `FEISHU_CONFIG_DIR` 显式覆盖
  - `_shared.py` — CLI 共享工具：`create_client()`、`print_json()`、`extract_doc_id()`、`extract_base_info()`、联系人查询等
  - `_docx_converter.py` — Markdown 到 docx block 的转换器
- `feishu-*`
  - 按飞书能力域拆分的单操作 CLI
- `shortcuts/`
  - 跨能力组合工作流

所有 CLI 脚本通过 `from feishu_common import create_client, cli_run` 使用统一入口，不再各自硬编码凭证路径。

### 2. 机器配置

- `config/settings.json`
  - 轻量运行配置，不承载安全白名单
- `config/permissions.json`
  - 飞书开放平台后台导出的原始权限 JSON
- `config/risk_policy.json`
  - 默认工作目录、可执行风险策略与白名单

### 3. 人类文档

- `README.md`
  - 项目入口、最小启动路径
- `docs/usage.md`
  - 常见工作流与配置方法
- `docs/policies.md`
  - 策略解释与规则边界
- `docs/architecture.md`
  - 当前文档，解释目录与职责

### 4. 外部参考

- `reference/`
  - 飞书 API 备查资料，不作为运行配置

## 顶层文件职责

### README.md

只做入口，不承载完整规则手册。

### SKILL.md

只做 skill 元数据、能力概览、依赖文件与入口说明。

## 扩展规则

未来新增接口能力时：

1. 如果是新的 API 封装，优先加到 `feishu_common/_client_xxx.py`
2. 如果是新的单一动作入口，优先加到对应 `feishu-*` 目录
3. 如果是跨域组合流程，放到 `shortcuts/`
4. 如果需要新增团队规则，优先改 `config/risk_policy.json`
5. 如果需要新增使用说明，优先改 `docs/`

## 不建议的做法

- 不要把团队规则继续堆进 `README.md`
- 不要把机器需要读取的配置只写在 Markdown
- 不要让 `reference/` 承担项目自身配置职责
- 不要让 `SKILL.md` 与 `docs/policies.md` 互相复制大段内容
