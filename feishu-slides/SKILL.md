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

| 脚本 | 所需权限 | 状态 |
|------|---------|------|
| slides_upload_media.py | `docs:document.media:upload` | **需申请** |

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
- 需开通 `docs:document.media:upload` 权限
