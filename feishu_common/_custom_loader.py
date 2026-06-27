#!/usr/bin/env python3
"""
_custom_loader.py -- 扫描并加载 custom/ 目录下的用户自定义脚本和子 skill。

custom/ 目录用于存放用户自定义扩展，已加入 .gitignore，上游更新时不会被覆盖。
本模块只负责发现与索引，不执行自定义脚本。
"""

import json
import re
from pathlib import Path

try:
    from ._config_loader import SKILL_ROOT
except ImportError:
    # 支持被单独 importlib 加载时的回退
    SKILL_ROOT = Path(__file__).resolve().parent.parent

CUSTOM_DIR = SKILL_ROOT / "custom"


def _parse_skill_md(path):
    """解析 SKILL.md 头部的 YAML-like 元数据。

    只处理前后三个破折号包裹的元数据块，返回 dict。
    解析失败时返回 {"name": 目录名/文件名}。
    """
    metadata = {}
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return metadata

    # 简单解析 metadata 块中的 key: value
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            meta_text = parts[1]
            for line in meta_text.splitlines():
                if ":" in line and not line.strip().startswith("-"):
                    key, _, value = line.partition(":")
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if key and value:
                        metadata[key] = value
    return metadata


def load_custom_skills(custom_dir=None):
    """扫描 custom/ 目录，返回自定义脚本和子 skill 的清单。

    Args:
        custom_dir: 自定义扫描目录，默认使用项目根目录下的 custom/

    Returns:
        dict: {
            "scripts": [
                {"name": "my_script", "path": "custom/my_script.py", "description": "..."}
            ],
            "skills": [
                {"name": "my-workflow", "path": "custom/my-workflow", "description": "..."}
            ]
        }
    """
    result = {"scripts": [], "skills": []}
    scan_dir = Path(custom_dir) if custom_dir else CUSTOM_DIR
    skill_root = scan_dir.parent
    if not scan_dir.exists():
        return result

    for entry in sorted(scan_dir.iterdir()):
        if entry.name.startswith("."):
            continue

        if entry.is_file() and entry.suffix == ".py":
            name = entry.stem
            description = ""
            try:
                # 读取模块级 docstring 第一行作为描述
                text = entry.read_text(encoding="utf-8")
                match = re.search(r'"""(.*?)"""', text, re.DOTALL)
                if match:
                    doc = match.group(1).strip().splitlines()
                    if doc:
                        description = doc[0].strip()
            except Exception:
                pass
            result["scripts"].append({
                "name": name,
                "path": str(entry.relative_to(skill_root)),
                "description": description,
            })

        elif entry.is_dir():
            skill_md = entry / "SKILL.md"
            if skill_md.exists():
                metadata = _parse_skill_md(skill_md)
                result["skills"].append({
                    "name": metadata.get("name", entry.name),
                    "path": str(entry.relative_to(skill_root)),
                    "description": metadata.get("description", ""),
                    "version": metadata.get("version", "0.0.0"),
                })
            else:
                # 没有 SKILL.md 的目录也记录，但只作为普通目录
                py_files = sorted([f for f in entry.iterdir() if f.suffix == ".py"])
                if py_files:
                    result["scripts"].append({
                        "name": entry.name,
                        "path": str(entry.relative_to(skill_root)),
                        "description": f"目录，包含 {len(py_files)} 个脚本",
                    })

    return result


def list_custom_scripts():
    """返回 custom/ 下可直接运行的 Python 脚本路径列表。"""
    return [s["path"] for s in load_custom_skills()["scripts"]]


def list_custom_skills():
    """返回 custom/ 下子 skill 目录路径列表。"""
    return [s["path"] for s in load_custom_skills()["skills"]]
