#!/usr/bin/env python3
"""Tests for auth_get_user_token scope strategy and agent-friendly CLI."""

import json
import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

MODULE_PATH = Path(__file__).parent.parent / "feishu-auth" / "auth_get_user_token.py"
SPEC = importlib.util.spec_from_file_location("auth_get_user_token", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)

_load_user_scopes = MODULE._load_user_scopes
CORE_USER_SCOPES = MODULE.CORE_USER_SCOPES


class TestLoadUserScopes(unittest.TestCase):
    def test_no_permissions_returns_core_scopes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            old = os.environ.pop("FEISHU_CONFIG_DIR", None)
            try:
                os.environ["FEISHU_CONFIG_DIR"] = tmpdir
                scopes, source = _load_user_scopes()
                self.assertEqual(set(scopes), set(CORE_USER_SCOPES))
                self.assertEqual(source, "core_fallback")
            finally:
                if old is None:
                    os.environ.pop("FEISHU_CONFIG_DIR", None)
                else:
                    os.environ["FEISHU_CONFIG_DIR"] = old

    def test_tenant_scopes_derive_user_scopes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            old = os.environ.pop("FEISHU_CONFIG_DIR", None)
            try:
                os.environ["FEISHU_CONFIG_DIR"] = tmpdir
                perms = {
                    "scopes": {
                        "tenant": ["contact:contact.base:readonly"],
                        "user": ["offline_access"],
                    }
                }
                (Path(tmpdir) / "permissions.json").write_text(
                    json.dumps(perms), encoding="utf-8"
                )
                scopes, source = _load_user_scopes()
                self.assertIn("offline_access", scopes)
                self.assertIn("auth:user.id:read", scopes)
                # Verify derivation produced scopes beyond CORE_USER_SCOPES
                self.assertIn("contact:contact.base:readonly", scopes)
                self.assertEqual(source, "tenant_derived")
            finally:
                if old is None:
                    os.environ.pop("FEISHU_CONFIG_DIR", None)
                else:
                    os.environ["FEISHU_CONFIG_DIR"] = old


class TestBuildAuthUrl(unittest.TestCase):
    def test_build_auth_url_contains_required_params(self):
        client = MagicMock()
        client.app_id = "test_app_id"
        url = MODULE._build_auth_url(
            client,
            ["offline_access", "im:message"],
            "http://localhost:8080/callback",
        )
        self.assertIn("client_id=test_app_id", url)
        self.assertIn("response_type=code", url)
        self.assertIn("redirect_uri=http%3A%2F%2Flocalhost%3A8080%2Fcallback", url)
        self.assertIn("scope=offline_access%20im%3Amessage", url)
        self.assertTrue(url.startswith("https://accounts.feishu.cn/open-apis/authen/v1/authorize"))


class TestAgentFriendlyCLI(unittest.TestCase):
    @patch.object(MODULE, "_auto_sync_permissions")
    @patch.object(MODULE, "_auto_populate_settings")
    @patch.object(MODULE, "write_default_risk_policy")
    @patch.object(MODULE, "exchange_code_for_token")
    @patch.object(MODULE, "_load_user_scopes")
    @patch.object(MODULE, "FeishuClient")
    @patch.object(MODULE, "resolve_config_path")
    @patch.object(MODULE, "get_config_dir")
    @patch.object(MODULE, "log_config_paths")
    @patch.object(MODULE, "get_config_context")
    @patch.object(MODULE, "load_credentials_data")
    @patch.object(MODULE, "print_json")
    def test_print_auth_url_json_output(
        self, mock_print_json, mock_load_creds, mock_get_context, mock_log,
        mock_get_dir, mock_resolve, mock_client_cls, mock_load_scopes,
        mock_exchange, mock_write_risk, mock_populate, mock_sync,
    ):
        mock_get_context.return_value = {
            "config_dir": Path("/tmp"),
            "source": "env",
            "is_platform": False,
        }
        mock_load_creds.return_value = (
            {"appId": "test_app", "appSecret": "test_secret"},
            Path("/tmp/credentials.json"),
        )
        mock_get_dir.return_value = Path("/tmp")
        mock_resolve.return_value = Path("/tmp/credentials.json")
        mock_client = MagicMock()
        mock_client.app_id = "test_app"
        mock_client_cls.return_value = mock_client
        mock_load_scopes.return_value = (["offline_access", "im:message"], "core_fallback")

        with patch.object(sys, "argv", ["auth_get_user_token.py", "--print-auth-url", "--json"]):
            MODULE.main()

        mock_print_json.assert_called_once()
        args = mock_print_json.call_args[0][0]
        self.assertIn("auth_url", args)
        self.assertIn("scopes", args)
        self.assertIn("scope_source", args)


if __name__ == "__main__":
    unittest.main()
