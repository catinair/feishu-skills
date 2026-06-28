# 竞品调研：alextangson/feishu_skills

> 调研日期：2026-06-28  
> 调研对象：[https://github.com/alextangson/feishu_skills](https://github.com/alextangson/feishu_skills)  
> 调研目的：了解同类开源项目，判断与本项目的差异，提取可借鉴经验。

## 1. 对方项目速览

| 维度 | 内容 |
|------|------|
| 定位 | 为 OpenClaw AI Agent 框架设计的飞书 API Skill 库 |
| 形态 | **不是 SDK，也不是可执行脚本**，而是 10 个 `SKILL.md` Prompt 模板 |
| 覆盖域 | im（25+ API）、bitable（30+）、doc-writer（15+）、drive、task、calendar、approval、contact、wiki、card |
| Star / Fork | 63 / 8 |
| License | MIT |
| 运行方式 | 把 markdown 复制到 OpenClaw 的 skills 目录，Agent 读取后自己生成 curl 调用 |
| 认证 | 仅 `tenant_access_token`（企业内部应用），一个 bash 脚本负责 token 获取与缓存 |

对方的核心 slogan 是：**"120+ 项飞书 API 实测经验，让你的 AI Agent 成为飞书自动化专家"**。

## 2. 与本项目的核心差异

| 维度 | alextangson/feishu_skills | 当前 feishu-skills |
|------|---------------------------|--------------------|
| 交付物 | Prompt 模板（markdown） | Python CLI 脚本 |
| 使用者 | AI Agent（OpenClaw） | 终端用户 / 脚本 |
| 调用链路 | Agent 读 SKILL.md → 生成 curl | 用户执行 `python3 xxx.py` |
| 认证能力 | 仅 tenant token | tenant + user token + OAuth v2 |
| 工程化 | 轻量：一个 bash 脚本 + markdown | 完整运行时：client、mixin、端点注册、配置系统、分页、权限预检、风险策略 |
| 输出 | 无固定输出格式，依赖 Agent | 统一 JSON 输出 |
| 可测试性 | 基本无测试 | 144 个 pytest 用例 |

**一句话结论**：对方卖的是"知识"，我们卖的是"工具"。方向相似，形态不同，不构成直接竞争。

## 3. 值得借鉴的具体经验

### 3.1 Prompt 精简与 token 优化

对方在 2026-03-07 做了一次大优化，把所有 skills 从 **2229 行压缩到 790 行**，**token 消耗减少 65%**。这说明 SKILL.md 作为 AI 主要文档，有很大的压缩空间。

可借鉴做法：
- 删除冗余说明，保留"这个 skill 能做什么、需要什么权限、关键坑点"
- 用表格替代大段文字
- 把示例和心法前置

### 3.2 "实测心法"——官方文档不会告诉你的坑

对方每个 skill 里都记录了真实调用踩出来的经验，例如：

| Skill | 心法 |
|-------|------|
| feishu-im | `content` 字段必须是字符串化 JSON，不能直接传对象 |
| feishu-doc-writer | **严禁并发写入，必须串行执行，否则 Block 顺序会错乱** |
| feishu-bitable | 日期字段必须转为 13 位毫秒级时间戳 |

当前项目 `_client_core.py` 已有中文错误码映射，但 `SKILL.md` 对"踩坑点"的强调可以更强。

### 3.3 权限清单前置

对方每个 `SKILL.md` 顶部就是 `required_permissions` 列表，例如：

```markdown
name	feishu-im
description	飞书消息与群管理。发送消息、建群、置顶、加急、撤回、群菜单/Tab/公告。
required_permissions
im:message
im:chat:create
im:chat.members:write_only
```

一目了然。当前项目虽然也有权限表，但可以学习这种"顶部一句话 + 权限清单"的格式。

### 3.4 Token 缓存脚本设计

对方的 `scripts/get_feishu_token.sh` 虽然只是一个 bash 脚本，但做得比较严谨：
- 文件锁（`mkdir` 实现锁目录）
- 提前 5 分钟刷新
- 环境变量可配置缓存路径和刷新窗口
- 强制刷新参数 `--force-refresh`
- 缓存文件 `chmod 600`

当前项目靠 `config/credentials.json` 缓存 token，可考虑增强：
- 更明确的 token 刷新窗口配置
- 对缓存文件的权限敏感提示

### 3.5 文档与 Mermaid 插件块细节

`feishu-doc-writer` 里有几个当前项目没有明确记录的知识点：
- 飞书官方提供 `POST /documents/{document_id}/convert` 做 Markdown → Blocks 转换
- Mermaid 绘图块是插件块（`block_type=40`），需要特定 `component_type_id`
- 建议先读取文档中已有的 Mermaid 块，复用其 `component_type_id/theme/view`

当前项目 `_docx_converter.py` 已实现 Markdown ↔ docx block 转换，但 SKILL.md 里没有这么多实战经验式的指引。

## 4. 建议行动项（按优先级）

| 优先级 | 行动项 | 说明 |
|--------|--------|------|
| **低/不做** | 重构 SKILL.md 结构 | 当前 SKILL.md 已足够精简，按对方结构重构后 token 不降反升，性价比低 |
| **低/顺手做** | 补充"实测心法"小节 | 如果未来维护某个 SKILL.md，可顺手把踩坑点聚合成一个"实测心法"小节，但不必单独立项 |
| **中** | 增强 token 刷新策略 | 参考对方的锁、提前刷新窗口、强制刷新设计，但涉及核心运行时，需充分测试 |
| **低** | 功能补齐 | 对方有 `approval`、`card` 两个领域当前项目没有，应基于真实需求，而非"对方有" |

## 5. 推荐的分支测试方向

**本次专项不推荐开分支验证。**

对方项目的核心价值（Prompt 模板、AI Agent 适配）与当前项目的 CLI 工具定位差异过大，格式上的微借鉴（权限清单前置、实测心法小节）不值得单独立项测试。

## 6. 最终结论

**alextangson/feishu_skills 对当前项目没有强行借鉴的价值，性价比不高。**

判断依据：

1. **形态不匹配**：对方是 OpenClaw 的 Prompt 模板集合，当前项目是 CLI 工具集合，要解决的不是同一个问题。
2. **压缩红利不存在**：对方能压缩 65% 是因为原始文档冗长；当前项目的 SKILL.md 本来就很精简，按它的结构重构后 `feishu-im` token 反而可能上涨。
3. **核心优势已具备**：双 token + OAuth 刷新、端点注册、权限预检、风险策略等工程化能力远超对方。
4. **可借鉴的皮毛价值有限**：顶部权限清单、实测心法小节确实有格式上的好处，但单独为这两点重构 15 个 SKILL.md 不划算。

建议：

- 保留当前 SKILL.md 模板，不做大规模重构。
- 如果未来偶尔维护某个 SKILL.md，可以顺手把它的踩坑点聚合成一个"实测心法"小节。
- 把精力放回真正的工程改进（如 token 刷新并发安全、新增 API 覆盖），而不是文档形态的模仿。

**这个专项到此为止。**
