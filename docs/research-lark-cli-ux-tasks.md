# 专项调研任务：官方 lark-cli 基础体验优化参考

> 调研日期：2026-06-28  
> 调研对象：本地安装的官方 `lark-cli` v1.0.59  
> 任务目标：**不改项目代码**，仅梳理官方 CLI 中值得当前 `feishu-skills` 项目参考的基础体验优化点，按轻重缓急输出调研报告。  
> 约束：当前已实现的能力域都是高频需求，本次调研**不优先补齐功能域**，只关注基础体验。

## 1. 调研原则

- **不新增功能域为首要目标**：当前覆盖的 `base/doc/drive/im/sheets/calendar/contact/task/wiki/minutes/perm/slides` 都是高频域，调研不把它们排在最高优先级。
- **聚焦基础体验**：命令入口、配置认证、输出格式、分页、帮助发现、稳健性、错误诊断、开发者效率等。
- **先调研，后决策**：本阶段只输出报告，不改动代码。最终是否采纳需根据当前项目的"零 pip 依赖、纯 Python 标准库、独立脚本"定位做取舍。

## 2. 什么是"基础体验"（本次调研范围）

| 维度 | 说明 |
|------|------|
| **CLI 入口与命令结构** | 是否有统一入口、命令层级是否清晰、是否有高阶 shortcut |
| **配置与认证体验** | 多 profile、keychain 存储、配置初始化、身份默认设置 |
| **输出与分页** | JSON/表格/CSV 输出模式、自动分页、分页控制参数 |
| **帮助与发现** | `--help` 信息质量、示例、schema 查看、skill 文档读取 |
| **稳健性** | 幂等键、错误重试、自动回滚、异步任务轮询 |
| **错误诊断** | 健康检查、配置检查、连接性检查、权限检查 |
| **开发者效率** | 本地目录同步、批量操作、媒体上传的 orchestration |

## 3. 从官方 CLI 识别出的重点调研方向

### 3.1 高优先级（建议优先调研）

#### 3.1.1 统一 CLI 入口

官方 CLI：
```bash
lark-cli im messages.send --params '{...}'
lark-cli drive files.list --params '{...}'
```

当前项目：
```bash
python3 feishu-im/im_send_message.py ...
python3 feishu-drive/drive_list.py ...
```

**调研问题**：
- 当前扁平脚本模式在用户体验上的主要痛点是什么？
- 如果引入一个顶层入口（如 `python3 feishu.py im send ...`），是否会破坏"独立脚本可运行"的设计原则？
- 能否用最小成本实现一个可选的顶层入口，同时保留所有脚本独立运行？

#### 3.1.2 帮助信息与示例质量

官方 CLI 的 `--help` 通常包含：
- 明确的命令用途说明
- 使用示例
- 参数说明
- 身份要求提示

当前项目依赖 argparse 默认 help。

**调研问题**：
- 当前各脚本的 `--help` 是否足够让新用户独立使用？
- 是否需要统一在 help 中展示：权限要求、身份要求、使用示例、常见错误？
- 如何在零 pip 依赖前提下提升 help 体验？

#### 3.1.3 身份管理与默认身份

官方 CLI：
```bash
lark-cli config default-as user      # 设置默认 user 身份
lark-cli contact +search-user ... --as user
```

当前项目：
- `settings.json` 中的 `default_identity`
- 部分脚本支持 `--as-user`

**调研问题**：
- 当前身份切换是否足够方便？
- 是否需要在 CLI 层提供 `config default-as` 类似的显式命令？
- 脚本级别的 `--as-user` 是否一致覆盖所有需要 user 身份的脚本？

#### 3.1.4 Token 安全存储

官方 CLI：
- 默认使用系统 keychain（macOS）
- 提供 `keychain-downgrade` 降级到本地文件

当前项目：
- `config/credentials.json` 明文存储

**调研问题**：
- 当前 credentials.json 的安全风险等级如何？
- 在纯 Python 标准库前提下，能否安全地使用 macOS keychain / Windows Credential / Linux secret service？
- 如果引入 keychain，如何保持"零 pip 依赖"？
- 最低成本的改进是什么？（如文件权限 600 提示、不打印 secret 等）

#### 3.1.5 异步任务轮询体验

官方 CLI 的 `drive +export`、`drive +import`、`wiki +node-delete` 等命令内部会异步轮询任务结果。

当前项目：
- 部分脚本直接返回 async task，由用户自行轮询
- `drive_export.py` 可能已有轮询逻辑

**调研问题**：
- 当前哪些脚本会返回 async task？
- 哪些场景下用户需要"同步等待结果"？
- 轮询逻辑是否应该统一封装到 `_client_core.py`？
- 是否应提供 `--wait` / `--no-wait` 参数？

### 3.2 中优先级（值得调研，但不阻塞主线）

#### 3.2.1 高阶 Shortcut 命令

官方 CLI 大量使用 `+xxx` 命令，把多步 API 编排成一步：
- `drive +media-insert`：4 步 orchestration + auto-rollback
- `im +messages-send`：自动处理 user/chat_id 解析
- `sheets +workbook-import`：异步导入 + 轮询

当前项目已有 `shortcuts/` 目录，但数量有限。

**调研问题**：
- 当前 shortcuts 是否覆盖了最高频的组合场景？
- 每个已覆盖域中，哪些多步操作最常被用户手动串联？
- 官方 `+xxx` 命令中哪些最值得在当前项目中以 shortcut 形式实现？

#### 3.2.2 输出格式选择

官方 CLI 可能支持多种输出格式（需验证）。

当前项目：
- 统一 JSON 输出
- 部分脚本可能有 `--human-readable` 或 `--json` 选项

**调研问题**：
- 当前 JSON 输出是否满足所有场景？
- 是否需要支持 `--format table` / `--format csv` / `--format json`？
- 表格输出在零 pip 依赖下是否容易实现？

#### 3.2.3 分页控制参数

官方 CLI 的 `im +feed-shortcut-list` 支持 `--page-all` 自动拉取全部分页。

当前项目：
- `_paginate()` 自动分页
- 部分脚本可能提供 `--limit` / `--page-size`

**调研问题**：
- 当前自动分页是否对所有场景都合适？
- 是否需要显式分页参数（`--page-all`、`--max-pages`、`--limit`）？
- 大量数据拉取时，默认自动分页是否存在性能/ token 风险？

#### 3.2.4 Schema 查看能力

官方 CLI：
```bash
lark-cli schema calendar.events.list
```

当前项目：
- 无类似能力
- 信息分散在 `SKILL.md` 和 `_endpoint_registry.py`

**调研问题**：
- 是否有必要让脚本/用户快速查看某个 API 的参数和权限要求？
- 能否基于 `_endpoint_registry.py` 生成 schema 查询命令？
- 这是否属于基础体验，还是开发者工具？

### 3.3 低优先级（可记录，暂不深入）

#### 3.3.1 高级功能补齐

以下内容属于新增能力域或高级功能，本次调研不深入，仅记录：
- 邮件（mail）
- OKR（okr）
- 视频会议（vc）
- 审批（approval）
- 考勤（attendance）
- 事件订阅（event）
- 应用开发（apps）
- 高级 sheets 功能（图表、透视表、条件格式等）
- drive 本地目录同步（+pull/+push/+sync）

## 4. 详细调研任务清单

| 优先级 | 任务编号 | 任务名称 | 调研目标 | 预期产出 | 是否可能涉及代码改动（后续） | 备注 |
|--------|----------|----------|----------|----------|---------------------------|------|
| **P0** | T1 | 统一 CLI 入口可行性 | 分析官方 `lark-cli <domain> <action>` 模式，评估当前项目是否需要一个可选顶层入口 | 可行性报告 + 方案对比 | 是（可选） | 需保留脚本独立运行能力 |
| **P0** | T2 | 帮助信息质量审计 | 抽查 5-10 个高频脚本的 `--help`，对比官方 CLI help 质量 | 审计报告 + 改进建议 | 是 | 优先改进高频脚本 |
| **P0** | T3 | 身份管理体验 | 调研官方 `--as` / `config default-as` 设计，评估当前 `default_identity` 和 `--as-user` | 对比报告 + 统一建议 | 是 | 涉及 `_client_core.py` 和脚本参数 |
| **P0** | T4 | Token 安全存储 | 调研官方 keychain 机制，评估当前 credentials.json 风险 | 安全评估报告 + 最小改进方案 | 是 | 需保持零 pip 依赖 |
| **P0** | T5 | 异步任务轮询体验 | 梳理当前返回 async task 的脚本，对比官方同步等待命令 | 脚本清单 + 轮询封装建议 | 是 | 优先 `drive_export`、`wiki` 等 |
| **P1** | T6 | Shortcut 机会盘点 | 分析官方 `+xxx` shortcut，盘点当前项目缺失的高频组合场景 | shortcut 机会清单（按优先级排序） | 是 | 不阻塞主线 |
| **P1** | T7 | 输出格式扩展 | 调研官方输出模式，评估是否增加 table/csv 格式 | 输出格式建议报告 | 是 | 零 pip 依赖约束 |
| **P1** | T8 | 分页控制参数 | 调研官方 `--page-all` 等分页参数，评估当前自动分页策略 | 分页策略建议 | 是 | 涉及 `_client_core.py` |
| **P1** | T9 | Schema/权限查询工具 | 调研官方 `schema` 命令，评估基于 `_endpoint_registry.py` 实现查询工具 | 可行性报告 | 是 | 偏开发者工具 |
| **P2** | T10 | 高级功能域清单 | 记录官方有但当前项目无的能力域，供未来补齐参考 | 功能补齐 backlog | 否（本次） | 仅记录，不调研细节 |

## 5. 调研执行建议

### 5.1 推荐执行顺序

```
第 1 周：T1（统一入口）、T2（help 质量）
第 2 周：T3（身份管理）、T4（token 安全）
第 3 周：T5（异步轮询）、T6（shortcut 机会）
第 4 周：T7-T9（输出格式、分页、schema）
持续：T10（功能补齐 backlog 维护）
```

### 5.2 每个任务的通用产出模板

每个任务完成后，报告应包含：
1. **现状**：当前项目怎么做
2. **官方做法**：lark-cli 怎么做
3. **差距分析**：官方方案解决了什么问题
4. **可行性评估**：在当前项目约束下（零 pip 依赖、纯 Python 标准库、独立脚本）是否可行
5. **推荐方案**：采纳 / 部分采纳 / 不采纳，理由
6. **潜在影响面**：涉及哪些文件、是否破坏现有接口

## 6. 明确约束

- **本阶段不改代码**：所有任务只输出报告和建议。
- **不补齐功能域**：T10 仅记录 backlog，不深入实现。
- **保持项目定位**：任何建议都必须考虑"零 pip 依赖、纯 Python 标准库、脚本可独立运行"三大约束。
- **分优先级落地**：P0 任务如果后续采纳，应优先在分支中验证；P1/P2 任务根据主线进度择机处理。

## 7. 预期总产出

1. 9 份分任务调研报告（T1-T9）
2. 1 份功能补齐 backlog（T10）
3. 1 份综合优先级建议，明确哪些优化应立即在分支中验证、哪些应搁置
