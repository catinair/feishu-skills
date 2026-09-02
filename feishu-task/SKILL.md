---
name: feishu-task
version: 1.0.0
description: |
  飞书任务技能：创建任务、获取详情、列取列表、更新任务、创建评论、获取评论列表。
  纯 Python 标准库。
metadata:
  requires:
    bins: ["python3"]
    files:
      [
        "feishu-task/task_create.py",
        "feishu-task/task_get.py",
        "feishu-task/task_list.py",
        "feishu-task/task_patch.py",
        "feishu-task/task_comment_create.py",
        "feishu-task/task_comment_list.py",
        "config/credentials.json",
      ]
---

# feishu-task -- 飞书任务技能

## 权限要求

| 脚本 | 所需权限 | 身份要求 |
|------|---------|---------|
| task_create.py | `task:task:write` | **仅 user** |
| task_get.py | `task:task:read` | **仅 user** |
| task_list.py | `task:task:read` | **仅 user** |
| task_patch.py | `task:task:write` | **仅 user** |
| task_comment_create.py | `task:comment:write` | **仅 user** |
| task_comment_list.py | `task:comment:read` | **仅 user** |

> **注意**：当前 `feishu-task` 模块已按 `user_access_token` 实现。若未来飞书开放平台确认部分 task 接口支持稳定的应用身份，再评估是否补 tenant 兼容路径。

## 输出说明

本模块的写操作类 CLI（如创建、更新、删除等）默认输出精简摘要，便于 AI 消费。如需完整 API 原始响应，请加 `--raw`：

```bash
python3 feishu-task/task_create.py --summary "测试任务" --raw
```

通用 CLI 约定（`--yes`、`--raw`、`--identity`）详见项目级文档 [`docs/usage.md`](../docs/usage.md)。

## 快捷命令

### 创建任务

```bash
python3 feishu-task/task_create.py --summary "补齐本月商机盘点" --member ou_xxx
```

带截止时间和描述：

```bash
python3 feishu-task/task_create.py \
  --summary "补齐本月商机盘点" \
  --description "请在下班前补齐商机阶段、预计回款时间和主管预测金额" \
  --due-timestamp 1718121600000 \
  --member ou_xxx
```

### 获取任务详情

```bash
python3 feishu-task/task_get.py --guid e297ddff-06ca-4166-b917-4ce57cd3a7a0
```

返回字段包括：`guid`, `summary`, `description`, `status`(todo/done), `completed_at`, `created_at`, `due`, `members`, `creator` 等。

### 列取任务列表

```bash
# 列取所有任务（需 user_access_token）
python3 feishu-task/task_list.py

# 只列未完成任务
python3 feishu-task/task_list.py --completed false

# 只列已完成任务
python3 feishu-task/task_list.py --completed true
```

### 更新任务

```bash
# 完成任务
python3 feishu-task/task_patch.py --guid <task_guid> --complete

# 恢复未完成
python3 feishu-task/task_patch.py --guid <task_guid> --uncomplete

# 更新标题
python3 feishu-task/task_patch.py --guid <task_guid> --summary "新标题"

# 更新截止时间
python3 feishu-task/task_patch.py --guid <task_guid> --due-timestamp 1718121600000
```

### 创建评论

```bash
# 发表评论
python3 feishu-task/task_comment_create.py --resource-id <task_guid> --content "已完成3个宣讲"

# 回复某条评论
python3 feishu-task/task_comment_create.py --resource-id <task_guid> --content "收到" --reply-to <comment_id>
```

### 获取评论列表

```bash
# 按时间正序
python3 feishu-task/task_comment_list.py --resource-id <task_guid>

# 按时间倒序，最多10条
python3 feishu-task/task_comment_list.py --resource-id <task_guid> --direction desc --max 10
```

## Member 格式

任务成员表示方式：

```json
{
  "id": "ou_xxx",
  "type": "user",
  "role": "assignee"
}
```

角色：`assignee`=负责人，`follower`=关注人，`creator`=创建者

## 时间格式

截止时间/开始时间使用毫秒时间戳：

```json
{
  "timestamp": "1675742789470",
  "is_all_day": true
}
```

- `is_all_day=true`：截止日期，精确到天
- `is_all_day=false`：截止时间，精确到秒

## 任务状态

API 返回的 `status` 字段只有两种值：
- `todo` — 未完成
- `done` — 已完成

完成时间通过 `completed_at` 字段获取（毫秒时间戳，"0"=未完成）。
