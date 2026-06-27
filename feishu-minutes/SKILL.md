---
name: feishu-minutes
version: 1.0.0
description: |
  飞书妙记信息查询与 AI 产物导出。将会议录音/视频转写为结构化总结、章节纪要、待办事项。
  纯 Python 标准库（Pillow 可选，用于画板图片裁剪）。
metadata:
  requires:
    bins: ["python3"]
    files: ["feishu-minutes/minutes_artifacts.py", "feishu-minutes/minutes_get.py", "feishu-minutes/minutes_statistics.py", "feishu-minutes/minutes_transcript.py", "config/credentials.json"]
---

# feishu-minutes -- 飞书妙记技能

飞书妙记（Minutes）信息查询与 AI 产物导出。将会议录音/视频转写为结构化总结、章节纪要、待办事项。

## 使用场景

- 获取妙记 AI 总结（会议核心内容提炼）
- 获取章节纪要（按讨论模块分段摘要）
- 获取待办事项（自动提取的 action items）
- 获取妙记基本信息、访问统计（需额外权限）

## 权限要求

飞书 minutes 接口的权限分为**应用身份**（tenant_access_token）和**用户身份**（OAuth / user_access_token），两者是独立的。

当前项目已切到 `user-first` 方向，minutes 模块默认按 `config/settings.json` 中的 `default_identity=user` 运行，通常不再需要为单个命令显式传 `--user-token`。

| 功能 | API | 所需权限 | 推荐调用方式 |
|------|-----|---------|-------------|
| AI 产物（总结/章节/待办） | `GET /minutes/{token}/artifacts` | `minutes:minutes.artifacts:read` | ✅ 默认 user 路径 |
| 基本信息 | `GET /minutes/{token}` | `minutes:minutes.basic:read` | 默认 user 路径 |
| 转写导出 | `GET /minutes/{token}/transcript` | `minutes:minutes.artifacts:read` 或相应用户权限 | 默认 user 路径 |
| 访问统计 | `GET /minutes/{token}/statistics` | 当前实现为 app-only | tenant 兼容路径 |

> 如果当前环境缺少有效 `user_access_token`，请先执行 `python3 feishu-auth/auth_get_user_token.py` 完成授权。

## 工作流

### 1. 获取妙记 AI 产物（最常用）

```bash
python3 feishu-minutes/minutes_artifacts.py --token obcnxxx
```

**token 获取方式**：从妙记 URL 中提取，例如 `https://xxx.feishu.cn/minutes/obcnq3b9jl72l83w4f14xxxx` 中的 `obcnq3b9jl72l83w4f14xxxx`。

**user_access_token 获取方式**：
1. 在飞书开放平台 → 你的应用 → 权限管理 → **User Token Scopes** 标签页，勾选 `minutes:minutes.artifacts:read`
2. 运行 `python3 feishu-auth/auth_get_user_token.py`
3. 令牌会写入凭证文件（通过 resolver 自动选择目录），后续命令自动读取

格式化输出示例：
```
=== 妙记总结 ===
视频围绕客户价值判断及系统规划展开讨论，确定了客户价值判断的相关标准...

=== 章节纪要 ===

【项目进度回顾与风险评估】(31000ms - 33000ms)
1. 确认Q3项目交付节点为9月30日...

=== 待办事项 ===
- [ ] 提交资源保障方案 (@张三)
```

其他选项：
```bash
# 保存到文件
python3 feishu-minutes/minutes_artifacts.py --token obcnxxx --output ./summary.md

# 输出原始 JSON
python3 feishu-minutes/minutes_artifacts.py --token obcnxxx --raw
```

### 2. 获取妙记基本信息（需额外权限）

```bash
python3 feishu-minutes/minutes_get.py --token obcnxxx
```

返回：token、owner_id、create_time、title、cover、duration、url

### 3. 导出转写内容（需额外权限）

```bash
python3 feishu-minutes/minutes_transcript.py --token obcnxxx --output ./transcript.txt
```

### 4. 获取访问统计（需额外权限）

```bash
python3 feishu-minutes/minutes_statistics.py --token obcnxxx
```

## 脚本列表

| 脚本 | 功能 | 关键参数 |
|------|------|----------|
| `minutes_artifacts.py` | 获取 AI 总结/章节/待办 | `--token`, `--output`, `--raw` |
| `minutes_get.py` | 获取妙记基本信息 | `--token` |
| `minutes_transcript.py` | 导出转写内容 | `--token`, `--output`, `--raw` |
| `minutes_statistics.py` | 获取访问统计 | `--token` |

## 注意事项

1. **没有列表 API**：飞书暂未提供"列出所有妙记"的 API，token 需从妙记 URL 中手动获取。
2. **权限分层**：tenant_access_token 和 user_access_token 的权限互相独立；当前 minutes 体验默认优先走 user 路径。
3. **转写完成状态**：若妙记仍在转写中，API 会返回 2091003 "minute not ready, try later"。
4. **user_access_token 安全**：token 具有用户数据访问权限，**切勿硬编码到脚本或提交到版本控制**。
5. **依赖**：纯 Python 标准库（Pillow 可选），共用 `../feishu_common`。
