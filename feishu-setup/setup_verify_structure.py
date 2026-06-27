#!/usr/bin/env python3
"""
setup_verify_structure.py -- 检查 feishu-skills 目录结构是否完整

某些 Agent 平台会异步加载 skill，关键文件缺失时继续执行会导致报错。
本脚本用于在执行具体操作前确认 skill 已加载完成。

用法：
    python3 feishu-setup/setup_verify_structure.py
    python3 feishu-setup/setup_verify_structure.py --json
"""

import json
import os
import sys
from pathlib import Path


# 关键文件/目录清单：缺失任一都视为 skill 加载不完整
REQUIRED_PATHS = [
    "SKILL.md",
    "README.md",
    "feishu_common/__init__.py",
    "feishu_common/_client.py",
    "feishu_common/_client_core.py",
    "feishu_common/_config_loader.py",
    "feishu-setup/setup_check.py",
    "feishu-auth",
    "feishu-base",
    "feishu-calendar",
    "feishu-contact",
    "feishu-doc",
    "feishu-drive",
    "feishu-im",
    "feishu-minutes",
    "feishu-perm",
    "feishu-sheets",
    "feishu-slides",
    "feishu-task",
    "feishu-wiki",
    "shortcuts",
    "config/credentials.example.json",
]


def check_structure(skill_root="."):
    root = Path(skill_root)
    missing = []
    for rel in REQUIRED_PATHS:
        path = root / rel
        if not path.exists():
            missing.append(rel)

    return {
        "skill_root": str(root.resolve()),
        "complete": len(missing) == 0,
        "required_count": len(REQUIRED_PATHS),
        "missing_count": len(missing),
        "missing": missing,
    }


def main():
    json_only = "--json" in sys.argv
    report = check_structure()

    if json_only:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0 if report["complete"] else 1

    if report["complete"]:
        print("✅ feishu-skills 目录结构完整，可以继续执行。")
        return 0

    print("❌ 检测到 feishu-skills 目录结构不完整，可能存在 skill 加载延迟或加载失败。", file=sys.stderr)
    print("请等待 skill 完全加载后再试。", file=sys.stderr)
    print(file=sys.stderr)
    print(f"缺失项（共 {report['missing_count']} 个）：", file=sys.stderr)
    for item in report["missing"]:
        print(f"  - {item}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
