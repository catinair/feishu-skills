---
name: feishu-contact
version: 1.0.0
description: |
  飞书通讯录查询技能：搜索用户、查询用户详情、查询部门架构。
  纯 Python 标准库（Pillow 可选，用于画板图片裁剪）。
metadata:
  requires:
    bins: ["python3"]
    files: ["feishu-contact/contact_lookup.py", "feishu-contact/contact_colleagues.py", "feishu-contact/contact_departments.py", "feishu-contact/contact_get.py", "feishu-contact/contact_search.py", "config/credentials.json"]
---

# feishu-contact -- 飞书通讯录技能

飞书通讯录查询。搜索用户、查询用户详情、查询部门架构。

## 权限要求

> **说明**：以下标注的审批要求基于常见企业配置。实际是否需要管理员审批，取决于你所在企业管理员在「飞书开放平台 → 自建应用审核规则」中的设置。

| 脚本 | 所需权限 | 审批说明 |
|------|---------|----------|
| contact_search.py | `contact:user:search` | 一般无需管理员审批 |
| contact_get.py | `contact:contact.base:readonly` | 一般无需管理员审批 |
| contact_colleagues.py | `contact:contact.base:readonly` + `auth:user.id:read` | 一般无需管理员审批 |
| contact_departments.py | `contact:department.base:readonly` + `contact:user.base:readonly`（--members） | 一般无需管理员审批 |

> 当前项目已切到 `user-first`，通讯录接口默认通过 `user_access_token` 调用。若 token 过期，请执行 `python3 feishu-auth/auth_get_user_token.py` 刷新。

## 快捷命令

### 统一查询（推荐）

```bash
python3 feishu-contact/contact_lookup.py --name 夏草
python3 feishu-contact/contact_lookup.py --openid ou_xxx
python3 feishu-contact/contact_lookup.py --user-id your_user_id
```

### 搜索用户

```bash
python3 feishu-contact/contact_search.py 万青
python3 feishu-contact/contact_search.py 张三 --limit 10
```

### 查询用户详情

```bash
python3 feishu-contact/contact_get.py --user-id your_user_id
python3 feishu-contact/contact_get.py --openid ou_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 查询同部门人员

```bash
python3 feishu-contact/contact_colleagues.py
```

### 查询部门架构

```bash
# 列出所有部门
python3 feishu-contact/contact_departments.py --list

# 查询单个部门信息
python3 feishu-contact/contact_departments.py --get 8a612b6c9184b118

# 查询部门成员（默认 user 身份）
python3 feishu-contact/contact_departments.py --members 8a612b6c9184b118

# 输出完整部门树
python3 feishu-contact/contact_departments.py --tree

# 拉取全部门成员（去重），输出 JSON
python3 feishu-contact/contact_departments.py --all-members

# 拉取全部门成员，输出 CSV
python3 feishu-contact/contact_departments.py --all-members --output csv > members.csv
```

## 脚本列表

| 脚本 | 功能 | 关键参数 |
|------|------|----------|
| `contact_lookup.py` | 统一查询入口 | `--name` / `--openid` / `--user-id` |
| `contact_search.py` | 搜索用户 | `<keyword>`, `--limit` |
| `contact_get.py` | 查询用户详情 | `--user-id` / `--openid`, `--raw` |
| `contact_colleagues.py` | 查询同部门人员 | 无参数（基于当前用户身份） |
| `contact_departments.py` | 查询部门架构 | `--list`, `--get`, `--members`, `--tree`, `--all-members` |

## 注意事项

1. **contact_lookup.py**：统一查询入口（`--name` 搜索 / `--openid` / `--user-id` 精确查询），纯 API。
2. **身份策略**：通讯录接口默认使用 `user_access_token`（由 `config/settings.json` 的 `default_identity` 控制）。
3. **部门成员权限**：`--members` 使用 `find_by_department` 接口，需要应用开通 `contact:user.base:readonly` 或 `contact:contact.base:readonly` 权限。
4. **依赖**：纯 Python 标准库（Pillow 可选），共用 `../feishu_common`。

## 问题排查

### 接口调用成功，但返回空数据或字段不全

如果脚本没有报权限错误（HTTP 200 或正常 JSON 输出），但出现以下现象：

- `contact_departments.py --list` 返回 `{"departments": [], "total": 0}`
- `contact_get.py` 返回的 `department_ids`、`job_title` 等字段为空
- `contact_colleagues.py` 只返回自己一个人，或返回 `"department_id": None`

很可能是飞书后台的**通讯录权限范围**（又称"数据访问范围"）限制导致的，而不是 registry 或 scope 错误。

飞书应用后台可以设置通讯录可见范围：

> 飞书开放平台 → 应用详情 → 权限管理 → 通讯录权限范围

常见选项：

- **全部成员**：应用可见整个通讯录
- **与应用的可用范围一致**：应用只能看到授权用户自己所在范围
- **部分成员**：管理员手动指定可见范围

如果应用仅对你个人可用，或权限范围被设为"与应用的可用范围一致"，那么机器人/应用身份就只能看到你自己（或你所在的小范围部门），从而出现"接口通但数据空/不全"的情况。

**排查建议**：

1. 先确认脚本本身没有报权限错误（如 `权限预检失败`、`HTTP 403` 等）。
2. 用 `contact_search.py 你的姓名`（user 身份）测试：如果能搜到自己，说明 API 权限是正常的。
3. 去飞书开放平台检查"通讯录权限范围"设置，必要时扩大可见范围后重新测试。
4. 如果无法扩大权限范围，这是预期行为：接口已正确工作，只是返回的数据受限于应用可见范围。
