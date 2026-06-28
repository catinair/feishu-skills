---
name: feishu-calendar
version: 1.0.0
description: |
  飞书日程管理技能：创建、查询、更新、删除日程，查询日历列表和用户忙闲状态。
  纯 Python 标准库（Pillow 可选，用于画板图片裁剪）。
metadata:
  requires:
    bins: ["python3"]
    files: ["feishu-calendar/calendar_create_event.py", "feishu-calendar/calendar_delete_event.py", "feishu-calendar/calendar_freebusy.py", "feishu-calendar/calendar_get_event.py", "feishu-calendar/calendar_list_calendars.py", "feishu-calendar/calendar_list_events.py", "feishu-calendar/calendar_update_event.py", "config/credentials.json"]
---

# feishu-calendar -- 飞书日程技能

飞书日程管理。创建、查询、更新、删除日程，查询日历列表和用户忙闲状态。

## 权限要求

> **说明**：以下标注的审批要求基于常见企业配置。实际是否需要管理员审批，取决于你所在企业管理员在「飞书开放平台 → 自建应用审核规则」中的设置。

| 脚本 | 所需权限 | 审批说明 |
|------|---------|----------|
| calendar_list_events.py | `calendar:calendar` / `calendar:calendar:readonly` | 一般无需管理员审批 |
| calendar_get_event.py | `calendar:calendar` / `calendar:calendar:readonly` | 一般无需管理员审批 |
| calendar_create_event.py | `calendar:calendar` | 一般无需管理员审批 |
| calendar_delete_event.py | `calendar:calendar` | 一般无需管理员审批 |
| calendar_freebusy.py | `calendar:calendar.freebusy:readonly` + `contact:user.base:readonly` | 一般无需管理员审批 |
| calendar_update_event.py | `calendar:calendar.event:update` | 一般无需管理员审批 |
| calendar_list_calendars.py | `calendar:calendar:read` | 一般无需管理员审批 |

## 快捷命令

### 查询日程列表

```bash
python3 feishu-calendar/calendar_list_events.py
python3 feishu-calendar/calendar_list_events.py --calendar-id primary --limit 10
```

### 查询单个日程

```bash
python3 feishu-calendar/calendar_get_event.py <event_id>
```

### 创建日程

```bash
python3 feishu-calendar/calendar_create_event.py "周会" --start "2026-04-25 14:00" --end "2026-04-25 15:00"
python3 feishu-calendar/calendar_create_event.py "项目复盘" --start "2026-04-25 10:00" --end "2026-04-25 11:30" --location "会议室 A" --desc "季度复盘"
```

时间格式支持：
- ISO 格式：`2026-04-25T14:00:00+08:00`
- 简单格式：`2026-04-25 14:00`（自动补 `+08:00`）
- 时间戳：`1774442400`（秒级）

### 删除日程

```bash
python3 feishu-calendar/calendar_delete_event.py <event_id>
python3 feishu-calendar/calendar_delete_event.py <event_id> --yes
```

### 更新日程

```bash
python3 feishu-calendar/calendar_update_event.py <event_id> --summary "改期到下周"
python3 feishu-calendar/calendar_update_event.py <event_id> --start "2026-04-26 14:00" --end "2026-04-26 15:00" --location "会议室 B" --yes
```

### 查询日历列表

```bash
python3 feishu-calendar/calendar_list_calendars.py
python3 feishu-calendar/calendar_list_calendars.py --limit 20 --raw
```

### 查询用户忙闲

```bash
python3 feishu-calendar/calendar_freebusy.py --user-id your_user_id --date 2026-04-25
python3 feishu-calendar/calendar_freebusy.py --openid ou_xxx --start "2026-04-25T09:00:00+08:00" --end "2026-04-25T18:00:00+08:00"
```

**注意**：忙闲 API 仅支持 `open_id`。如传 `--user-id`，会先通过 contact API 获取 `open_id`。

## 脚本列表

| 脚本 | 功能 | 关键参数 |
|------|------|----------|
| `calendar_list_events.py` | 查询日程列表 | `--calendar-id`, `--limit` |
| `calendar_get_event.py` | 查询单个日程 | `<event_id>`, `--raw` |
| `calendar_create_event.py` | 创建日程 | `<title>`, `--start`, `--end`, `--location`, `--desc` |
| `calendar_delete_event.py` | 删除日程 | `<event_id>`, `--yes` |
| `calendar_freebusy.py` | 查询用户忙闲 | `--user-id` / `--openid`, `--date` |
| `calendar_update_event.py` | 更新日程 | `<event_id>`, `--summary`, `--start`, `--end`, `--yes` |
| `calendar_list_calendars.py` | 查询日历列表 | `--limit`, `--raw` |

## 注意事项

1. **时区处理**：简单时间格式会自动补 `+08:00`，跨时区场景建议使用 ISO 格式或时间戳。
2. **删除确认**：`calendar_delete_event.py` 默认会提示确认，可传 `--yes` 跳过。
3. **依赖**：纯 Python 标准库（Pillow 可选），共用 `../feishu_common`。
