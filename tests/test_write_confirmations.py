#!/usr/bin/env python3
"""Tests for write-action confirmation layer in CLI scripts."""

import builtins
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
    domain = name.split("_")[0]
    path = skill_root / f"feishu-{domain}" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


doc_create = _load_script("doc_create")
drive_upload = _load_script("drive_upload")
task_create = _load_script("task_create")


class TestWriteConfirmations(unittest.TestCase):
    def setUp(self):
        self._original_mains = {
            "doc_create": doc_create.main,
            "drive_upload": drive_upload.main,
            "task_create": task_create.main,
        }
        self._patch_config(default_identity="tenant")

    def tearDown(self):
        doc_create.main = self._original_mains["doc_create"]
        drive_upload.main = self._original_mains["drive_upload"]
        task_create.main = self._original_mains["task_create"]
        self._restore_config()

    def _patch_config(self, default_identity="tenant"):
        self._tmpdir = tempfile.mkdtemp()
        settings_path = Path(self._tmpdir) / "settings.json"
        settings_path.write_text(json.dumps({"default_identity": default_identity}), encoding="utf-8")
        risk_path = Path(self._tmpdir) / "risk_policy.json"
        risk_path.write_text(json.dumps({"writes": {}}), encoding="utf-8")
        self._orig_settings = loader.SETTINGS_FILE
        self._orig_risk = loader.RISK_POLICY_FILE
        loader.SETTINGS_FILE = settings_path
        loader.RISK_POLICY_FILE = risk_path

    def _restore_config(self):
        loader.SETTINGS_FILE = self._orig_settings
        loader.RISK_POLICY_FILE = self._orig_risk

    def _run_main(self, module, args, mock_client):
        """Run a script's main() with replaced sys.argv and patched create_client."""
        old_argv = sys.argv
        sys.argv = [module.__name__.split(".")[-1] + ".py"] + args
        try:
            with patch.object(module, "create_client", return_value=mock_client):
                return module.main()
        finally:
            sys.argv = old_argv

    # --- doc_create ---

    def test_doc_create_without_yes_prompts_and_exits(self):
        mock_client = MagicMock()
        mock_input = MagicMock(return_value="n")
        with patch.object(builtins, "input", mock_input):
            with self.assertRaises(SystemExit) as ctx:
                self._run_main(doc_create, ["--title", "Test Doc"], mock_client)
        self.assertEqual(ctx.exception.code, 0)
        mock_input.assert_called()
        mock_client.document_create.assert_not_called()

    def test_doc_create_with_yes_skips_prompt(self):
        mock_client = MagicMock()
        mock_client.document_create.return_value = {"document_id": "doxcnxxx"}
        with patch.object(builtins, "input") as mock_input:
            mock_input.side_effect = AssertionError("input should not be called")
            self._run_main(doc_create, ["--title", "Test Doc", "--yes"], mock_client)
        mock_client.document_create.assert_called_once()

    # --- drive_upload ---

    def test_drive_upload_without_yes_prompts_and_exits(self):
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
            tmp.write(b"upload me")
            tmp_path = tmp.name
        try:
            mock_client = MagicMock()
            mock_input = MagicMock(return_value="n")
            with patch.object(builtins, "input", mock_input):
                with self.assertRaises(SystemExit) as ctx:
                    self._run_main(drive_upload, ["--path", tmp_path], mock_client)
            self.assertEqual(ctx.exception.code, 0)
            mock_input.assert_called()
            mock_client.upload_file.assert_not_called()
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_drive_upload_with_yes_skips_prompt(self):
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
            tmp.write(b"upload me")
            tmp_path = tmp.name
        try:
            mock_client = MagicMock()
            mock_client.upload_file.return_value = {"file_token": "boxcnxxx"}
            with patch.object(builtins, "input") as mock_input:
                mock_input.side_effect = AssertionError("input should not be called")
                self._run_main(drive_upload, ["--path", tmp_path, "--yes"], mock_client)
            mock_client.upload_file.assert_called_once()
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    # --- task_create ---

    def test_task_create_without_yes_prompts_and_exits(self):
        mock_client = MagicMock()
        mock_input = MagicMock(return_value="n")
        with patch.object(builtins, "input", mock_input):
            with self.assertRaises(SystemExit) as ctx:
                self._run_main(task_create, ["--summary", "Test Task"], mock_client)
        self.assertEqual(ctx.exception.code, 0)
        mock_input.assert_called()
        mock_client.task_create.assert_not_called()

    def test_task_create_with_yes_skips_prompt(self):
        mock_client = MagicMock()
        mock_client.task_create.return_value = {"guid": "task_xxx"}
        with patch.object(builtins, "input") as mock_input:
            mock_input.side_effect = AssertionError("input should not be called")
            self._run_main(task_create, ["--summary", "Test Task", "--yes"], mock_client)
        mock_client.task_create.assert_called_once()


if __name__ == "__main__":
    unittest.main()
