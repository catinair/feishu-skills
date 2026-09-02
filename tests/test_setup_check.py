#!/usr/bin/env python3
"""Tests for setup_check output."""

import contextlib
import io
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "feishu-setup"))

import feishu_common._config_loader as loader
import setup_check


class TestSetupCheckReport(unittest.TestCase):
    def test_report_has_config_context(self):
        report = setup_check.run_all_checks()
        self.assertIn("config_dir", report)
        self.assertIn("config_dir_source", report)
        self.assertIn("is_platform", report)

    def test_local_config_dir_source_is_skill_root(self):
        """模拟本地环境，验证 config_dir_source 为 skill_root。"""
        with patch.object(setup_check, "get_config_context") as mock_ctx:
            mock_ctx.return_value = {
                "config_dir": loader.SKILL_ROOT / "config",
                "source": "skill_root",
                "is_platform": False,
            }
            report = setup_check.run_all_checks()
            self.assertEqual(report["config_dir_source"], "skill_root")
            self.assertFalse(report["is_platform"])

    def test_missing_file_detail_uses_canonical_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            old = os.environ.pop(loader.FEISHU_CONFIG_DIR_ENV, None)
            try:
                os.environ[loader.FEISHU_CONFIG_DIR_ENV] = tmpdir
                report = setup_check.run_all_checks()
                creds_detail = report.get("credentials_detail", "")
                self.assertIn(tmpdir, creds_detail)
            finally:
                if old is None:
                    os.environ.pop(loader.FEISHU_CONFIG_DIR_ENV, None)
                else:
                    os.environ[loader.FEISHU_CONFIG_DIR_ENV] = old


class TestSetupCheckTokenRefresh(unittest.TestCase):
    def _write_creds(self, tmpdir, **kwargs):
        creds = {
            "appId": "cli_test",
            "appSecret": "test_secret",
            "brand": "feishu",
        }
        creds.update(kwargs)
        path = Path(tmpdir) / "credentials.json"
        path.write_text(json.dumps(creds), encoding="utf-8")
        return path

    def test_token_expired_with_valid_refresh_no_auto_refresh(self):
        """setup_check 不再自动刷新 token，过期时只给出刷新命令。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            old = os.environ.pop(loader.FEISHU_CONFIG_DIR_ENV, None)
            try:
                os.environ[loader.FEISHU_CONFIG_DIR_ENV] = tmpdir
                self._write_creds(
                    tmpdir,
                    userAccessToken="OLD_TOKEN",
                    userTokenExpire=time.time() - 100,
                )

                result = setup_check.check_user_token()

                self.assertFalse(result["user_token_ready"])
                self.assertIsNotNone(result["next_command"])
                self.assertIn("auth_diagnose_token.py --refresh", result["next_command"])
                self.assertIn("由业务脚本自动刷新", result["user_token_detail"])
            finally:
                if old is None:
                    os.environ.pop(loader.FEISHU_CONFIG_DIR_ENV, None)
                else:
                    os.environ[loader.FEISHU_CONFIG_DIR_ENV] = old

    def test_token_expired_with_local_refresh_token_requires_migration(self):
        """云模式下 credentials.json 中仍有 refresh_token 时，提示迁移。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            old = os.environ.pop(loader.FEISHU_CONFIG_DIR_ENV, None)
            try:
                os.environ[loader.FEISHU_CONFIG_DIR_ENV] = tmpdir
                self._write_creds(
                    tmpdir,
                    userAccessToken="OLD_TOKEN",
                    userTokenExpire=time.time() - 100,
                    refreshToken="REFRESH_TOKEN",
                    refreshTokenExpire=time.time() + 86400,
                )

                with patch.object(setup_check, "_bitable_configured", return_value=True):
                    result = setup_check.check_user_token()

                self.assertFalse(result["user_token_ready"])
                self.assertIn("cloud mode", result["user_token_detail"])
                self.assertIn("setup_bitable_infrastructure.py", result["next_command"])
            finally:
                if old is None:
                    os.environ.pop(loader.FEISHU_CONFIG_DIR_ENV, None)
                else:
                    os.environ[loader.FEISHU_CONFIG_DIR_ENV] = old

    def test_missing_user_token_has_next_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            old = os.environ.pop(loader.FEISHU_CONFIG_DIR_ENV, None)
            try:
                os.environ[loader.FEISHU_CONFIG_DIR_ENV] = tmpdir
                self._write_creds(tmpdir)

                result = setup_check.check_user_token()

                self.assertFalse(result["user_token_ready"])
                self.assertIsNotNone(result["next_command"])
                self.assertIn("auth_get_user_token.py", result["next_command"])
                self.assertEqual(result["user_token_detail"], "user_access_token 未配置")
            finally:
                if old is None:
                    os.environ.pop(loader.FEISHU_CONFIG_DIR_ENV, None)
                else:
                    os.environ[loader.FEISHU_CONFIG_DIR_ENV] = old

    def test_run_all_checks_recommendation_includes_next_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            old = os.environ.pop(loader.FEISHU_CONFIG_DIR_ENV, None)
            try:
                os.environ[loader.FEISHU_CONFIG_DIR_ENV] = tmpdir
                self._write_creds(tmpdir)

                report = setup_check.run_all_checks()

                self.assertIn("user_token", report.get("missing", []))
                recommendations = report.get("recommendations", [])
                self.assertTrue(
                    any("auth_get_user_token.py" in r for r in recommendations),
                    f"recommendations 应包含授权命令: {recommendations}",
                )
            finally:
                if old is None:
                    os.environ.pop(loader.FEISHU_CONFIG_DIR_ENV, None)
                else:
                    os.environ[loader.FEISHU_CONFIG_DIR_ENV] = old


class TestSetupCheckStderrOutput(unittest.TestCase):
    def test_prints_config_root_and_credentials_path(self):
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            setup_check.main()
        output = buf.getvalue()
        self.assertIn("CONFIG_ROOT:", output)
        self.assertIn("CREDENTIALS_PATH:", output)


if __name__ == "__main__":
    unittest.main()
