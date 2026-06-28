#!/usr/bin/env python3
"""Tests for feishu-setup/setup_wizard.py."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import importlib.util

sys.path.insert(0, str(Path(__file__).parent.parent))

import feishu_common._config_loader as loader

# setup_wizard.py lives in feishu-setup/ which is not a valid package name;
# load it dynamically so tests can run without renaming the directory.
_wizard_path = Path(__file__).parent.parent / "feishu-setup" / "setup_wizard.py"
_spec = importlib.util.spec_from_file_location("setup_wizard", _wizard_path)
_wizard_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_wizard_module)
wizard = _wizard_module


class TestSetupWizard(unittest.TestCase):
    def setUp(self):
        self._tmpdir = Path(tempfile.mkdtemp())
        self._orig_config_dir_env = "FEISHU_CONFIG_DIR"
        self._prev_env = os.environ.get(self._orig_config_dir_env)
        os.environ[self._orig_config_dir_env] = str(self._tmpdir)

    def tearDown(self):
        if self._prev_env is None:
            os.environ.pop(self._orig_config_dir_env, None)
        else:
            os.environ[self._orig_config_dir_env] = self._prev_env

    def test_validate_app_id_rejects_short_and_bad_prefix(self):
        self.assertFalse(wizard._validate_app_id("not_cli_"))
        self.assertFalse(wizard._validate_app_id("cli_"))
        self.assertFalse(wizard._validate_app_id("cli_123"))
        self.assertTrue(wizard._validate_app_id("cli_1234567890"))

    def test_write_credentials_creates_file(self):
        path = wizard._write_credentials("cli_1234567890", "secret")
        self.assertTrue(path.exists())
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(data["appId"], "cli_1234567890")
        self.assertEqual(data["appSecret"], "secret")
        self.assertEqual(data["brand"], "feishu")

    def test_run_check_returns_dict(self):
        report = wizard._run_check()
        self.assertIsInstance(report, dict)

    def test_ensure_risk_policy_creates_default(self):
        policy_path = self._tmpdir / "risk_policy.json"
        self.assertFalse(policy_path.exists())
        wizard._ensure_risk_policy()
        self.assertTrue(policy_path.exists())
        data = json.loads(policy_path.read_text(encoding="utf-8"))
        self.assertIn("workspace", data)
        self.assertIn("messaging", data)
        self.assertIn("writes", data)
        # Second call is a no-op
        wizard._ensure_risk_policy()


if __name__ == "__main__":
    unittest.main()
