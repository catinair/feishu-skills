#!/usr/bin/env python3
"""Tests for admin-approval scope hints on permission errors."""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from feishu_common._client_core import FeishuClientCore, ADMIN_APPROVAL_SCOPES
from feishu_common._endpoint_registry import BOTH
import feishu_common._config_loader as loader


class _FakeClient(FeishuClientCore):
    def __init__(self, creds=None, perms_path=None):
        self.creds = creds or {"appId": "cli_test", "appSecret": "secret", "brand": "feishu"}
        self.brand = "feishu"
        self.base_url = "https://open.feishu.cn"
        self.app_id = self.creds["appId"]
        self.app_secret = self.creds["appSecret"]
        self.user_access_token = "USER_TOKEN"
        self._token = "TENANT_TOKEN"
        self._token_expire = 9999999999


class TestAdminApprovalHint(unittest.TestCase):
    def setUp(self):
        self._orig_perms = loader.PERMISSIONS_FILE
        self._tmpdir = Path(tempfile.mkdtemp())
        loader.PERMISSIONS_FILE = self._tmpdir / "permissions.json"

    def tearDown(self):
        loader.PERMISSIONS_FILE = self._orig_perms

    def _patch_registry(self):
        """Temporarily inject a registry entry for delete_file requiring drive:file."""
        from feishu_common import _client_core
        orig_registry = dict(_client_core.ENDPOINT_REGISTRY)
        _client_core.ENDPOINT_REGISTRY["delete_file"] = {
            "identity": BOTH,
            "scopes": {
                "tenant": ["drive:file"],
                "user": ["drive:file"],
            },
        }
        return orig_registry

    def _restore_registry(self, orig):
        from feishu_common import _client_core
        _client_core.ENDPOINT_REGISTRY = orig

    def test_admin_approval_scope_known(self):
        self.assertIn("drive:file", ADMIN_APPROVAL_SCOPES)

    def test_hint_includes_admin_approval_message(self):
        orig_registry = self._patch_registry()
        try:
            client = _FakeClient()
            loader.PERMISSIONS_FILE.write_text(
                json.dumps({"scopes": {"tenant": ["drive:file"], "user": []}}),
                encoding="utf-8",
            )

            def fake_urlopen(req, timeout=None):
                resp = MagicMock()
                resp.read.return_value = b'{"code":99991672,"msg":"permission denied"}'
                resp.status = 200
                return resp

            with patch("urllib.request.urlopen", side_effect=fake_urlopen):
                with self.assertRaises(RuntimeError) as ctx:
                    client._request("DELETE", "/fake/path", method_name="delete_file")

            err = str(ctx.exception)
            self.assertIn("drive:file", err)
            self.assertIn("管理员审批", err)
        finally:
            self._restore_registry(orig_registry)


if __name__ == "__main__":
    unittest.main()
