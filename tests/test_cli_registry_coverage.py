#!/usr/bin/env python3
"""Tests that CLI scripts only call client methods registered in ENDPOINT_REGISTRY."""

import ast
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from feishu_common._endpoint_registry import ENDPOINT_REGISTRY


def _find_client_calls(source_path):
    """Return a set of client.<method> names used in a script."""
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    calls = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
                if func.value.id == "client":
                    calls.add(func.attr)
    return calls


class TestCliRegistryCoverage(unittest.TestCase):
    def test_all_cli_client_calls_are_registered(self):
        """所有 CLI 脚本里 client.xxx() 调用的方法都必须在 registry 中注册。"""
        skill_root = Path(__file__).resolve().parent.parent
        missing = []
        for script_dir in skill_root.glob("feishu-*"):
            for script_path in script_dir.glob("*.py"):
                calls = _find_client_calls(script_path)
                for method in calls:
                    if method.startswith("_"):
                        continue
                    if method not in ENDPOINT_REGISTRY:
                        missing.append(f"{script_path.name}: client.{method}()")
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
