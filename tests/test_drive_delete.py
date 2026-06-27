#!/usr/bin/env python3
"""Tests for drive_delete.py main function behavior."""

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

import feishu_common._config_loader as loader


def _load_script(name):
    """Load a feishu-*/<name>.py script as a module (directories contain hyphens)."""
    skill_root = Path(__file__).resolve().parent.parent
    # Directory prefix is feishu-<domain>, e.g., feishu-drive/drive_delete.py
    domain = name.split("_")[0]
    path = skill_root / f"feishu-{domain}" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


drive_delete = _load_script("drive_delete")


class TestDriveDelete(unittest.TestCase):
    def setUp(self):
        self._original_main = drive_delete.main

    def tearDown(self):
        drive_delete.main = self._original_main

    def _run_main(self, args, patched_create_client):
        """Run drive_delete.main with replaced sys.argv and patched create_client."""
        old_argv = sys.argv
        sys.argv = ["drive_delete.py"] + args
        try:
            with patch.object(drive_delete, "create_client", return_value=patched_create_client):
                return drive_delete.main()
        finally:
            sys.argv = old_argv

    def _patch_risk_policy(self, policy):
        tmpdir = tempfile.mkdtemp()
        path = Path(tmpdir) / "risk_policy.json"
        path.write_text(json.dumps(policy), encoding="utf-8")
        self._orig_policy = loader.RISK_POLICY_FILE
        loader.RISK_POLICY_FILE = path

    def _restore_risk_policy(self):
        loader.RISK_POLICY_FILE = self._orig_policy

    def test_normal_delete_calls_client_once(self):
        self._patch_risk_policy({"writes": {"manual_only_actions": []}})
        try:
            mock_client = MagicMock()
            mock_client.delete_file.return_value = {"deleted": True}
            self._run_main(["--file-token", "xxx", "--type", "file", "--yes"], mock_client)
            mock_client.delete_file.assert_called_once_with("xxx", "file")
        finally:
            self._restore_risk_policy()

    def test_manual_only_yes_bypasses_and_deletes(self):
        """manual_only 操作在 --yes 显式确认下应执行，并打印风险警告。"""
        self._patch_risk_policy({
            "writes": {"manual_only_actions": ["drive_delete"]}
        })
        try:
            mock_client = MagicMock()
            mock_client.delete_file.return_value = {"deleted": True}
            self._run_main(["--file-token", "xxx", "--type", "file", "--yes"], mock_client)
            mock_client.delete_file.assert_called_once_with("xxx", "file")
        finally:
            self._restore_risk_policy()

    def test_manual_only_strong_confirmation_decline_does_not_delete(self):
        """manual_only 操作在强确认被拒绝时不执行删除。"""
        self._patch_risk_policy({
            "writes": {"manual_only_actions": ["drive_delete"]}
        })
        try:
            mock_client = MagicMock()
            with patch("builtins.input", return_value="no"):
                with self.assertRaises(SystemExit) as ctx:
                    self._run_main(["--file-token", "xxx", "--type", "file"], mock_client)
            self.assertEqual(ctx.exception.code, 0)
            mock_client.delete_file.assert_not_called()
        finally:
            self._restore_risk_policy()


if __name__ == "__main__":
    unittest.main()
