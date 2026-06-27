# 开发检查清单

本清单用于规范新功能、修复或 CLI 脚本提交前的自检流程，降低权限、字段、端点等回归风险。

## 一、通用检查（所有改动）

- [ ] `python3 -m pytest tests/ -q` 全部通过
- [ ] 新增/修改的 mixin 方法已注册到 `feishu_common/_endpoint_registry.py`
- [ ] 新增/修改的 CLI 脚本调用的是已注册 mixin 方法（由 `tests/test_cli_registry_coverage.py` 自动检查）
- [ ] 新增/修改的 CLI 脚本能被直接 import 且不报语法错误
- [ ] 相关 `SKILL.md` 已同步更新（脚本列表、权限要求、用法示例）

## 二、真实凭证测试（按操作类型区分）

### 只读类操作（可自行测试）

例如：查询、列表、获取详情、导出等。**必须**用真实凭证至少跑一次：

```bash
python3 feishu-calendar/calendar_list_calendars.py
python3 feishu-doc/doc_fetch.py --token xxx
```

### 写入/修改/删除/发送类操作（必须人工二次确认后逐项测试）

例如：创建日程、发送消息、删除文件、修改权限、更新任务等。**禁止批量自动测试**，必须：

1. 先由开发者/测试人员明确确认测试对象（哪个群、哪条消息、哪个文件、谁的日程）。
2. 逐条手动执行，验证行为符合预期。
3. 涉及敏感 scope（如 `drive:file`、`docs:permission.member`）的，需先确认管理员已审批并重新发布应用。

```bash
# 示例：发送消息前必须人工确认接收方
python3 feishu-im/im_send_message.py --chat-id xxx --text "测试消息"
```

## 三、权限与授权相关

- [ ] 新增端点所需 scope 已加入 `feishu-auth/auth_get_user_token.py` 的 `_DEFAULT_SCOPES`
- [ ] 新增 scope 属于免审权限还是管理员审批权限已确认（参考 `ADMIN_APPROVAL_SCOPES`）
- [ ] 需要管理员审批的 scope 已在 `SKILL.md` 或文档中标注
- [ ] 若修改了默认 scope，建议重新运行 `python3 feishu-auth/auth_get_user_token.py` 刷新 token

## 四、提交前

- [ ] `git status` 确认无意外文件
- [ ] commit 信息使用中文，简要说明改动与原因
