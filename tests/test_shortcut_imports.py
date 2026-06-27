#!/usr/bin/env python3
"""Tests that all shortcut scripts are importable and expose a working --help."""

import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path


class TestShortcutImports(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skill_root = Path(__file__).resolve().parent.parent
        cls.shortcut_dir = cls.skill_root / "shortcuts"
        cls.shortcut_files = sorted(cls.shortcut_dir.glob("shortcut_*.py"))
        if not cls.shortcut_files:
            raise AssertionError("No shortcut_*.py files found in shortcuts/")

    def test_all_shortcuts_are_importable(self):
        errors = []
        for path in self.shortcut_files:
            spec = importlib.util.spec_from_file_location(path.stem, str(path))
            try:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
            except Exception as exc:  # pragma: no cover - collect failures
                errors.append(f"{path.name}: {exc}")
        self.assertEqual(errors, [])

    def test_all_shortcuts_help_returns_zero(self):
        failures = []
        for path in self.shortcut_files:
            result = subprocess.run(
                [sys.executable, str(path), "--help"],
                cwd=str(self.skill_root),
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                failures.append(
                    f"{path.name}: exit {result.returncode}\nstdout: {result.stdout}\nstderr: {result.stderr}"
                )
        self.assertEqual(failures, [])


if __name__ == "__main__":
    unittest.main()
