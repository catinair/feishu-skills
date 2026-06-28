---
name: feishu-slides
version: 1.0.0
description: |
  飞书幻灯片技能：上传媒体到幻灯片。
  纯 Python 标准库（Pillow 可选，用于画板图片裁剪）。
metadata:
  requires:
    bins: ["python3"]
    files: ["feishu-slides/slides_upload_media.py", "config/credentials.json"]
---

# feishu-slides -- 飞书幻灯片技能

## 权限要求

> **说明**：以下标注的审批要求基于常见企业配置。实际是否需要管理员审批，取决于你所在企业管理员在「飞书开放平台 → 自建应用审核规则」中的设置。

| 脚本 | 所需权限 | 审批说明 |
|------|---------|----------|
| slides_upload_media.py | `docs:document.media:upload` | 一般无需管理员审批 |

## 快捷命令

### 上传图片到幻灯片

```bash
python3 feishu-slides/slides_upload_media.py \
  --path ./image.png \
  --presentation doxcnxxx

# 从 Wiki URL 自动解析
python3 feishu-slides/slides_upload_media.py \
  --path ./image.png \
  --presentation "https://xxx.feishu.cn/wiki/xxx"
```

**注意**：
- 仅支持单分片小文件上传（< 20MB）
- 上传成功后返回 `file_token`，可用于 `<img src="...">`
- 需开通 `docs:document.media:upload` 权限。标注为「一般无需管理员审批」的 scope 仍需在飞书开放平台 → 权限管理中开通；若你的企业启用了严格审核策略，也可能需要管理员审批。
