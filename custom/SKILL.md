---
name: feishu-custom
version: 0.0.0
description: |
  用户自定义扩展目录。可在此创建自定义脚本、子 skill 或组合工作流。
  此目录已加入 .gitignore，拉取上游更新时不会被覆盖。
metadata:
  status: active
  parent_skill: feishu-skills
  requires:
    bins: ["python3"]
---

# custom/ -- 用户自定义扩展

此目录用于存放自定义脚本或子 skill，拉取上游更新时不会被覆盖。

## 使用方式

### 自定义脚本

在此目录下创建 Python 脚本，可引用 `feishu_common`：

```python
#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from feishu_common import create_client, cli_run

def main():
    client = create_client()
    # 你的逻辑 ...

if __name__ == "__main__":
    cli_run(main)
```

### 自定义子 skill

创建子目录（如 `custom/my-workflow/`），包含脚本即可。

## 注意

- 此目录已加入 `.gitignore`，你的改动不会被 git 追踪
- 上游仓库更新时，直接 `git pull` 即可，不会影响此目录
- 如果需要贡献回上游，请将代码移到对应的正式 `feishu-*/` 目录
