#!/usr/bin/env python3
"""Tests for download/export methods identity resolution and token selection."""

import json
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

import feishu_common._config_loader as loader
from feishu_common._client import FeishuClient
from feishu_common._client_core import BRAND_DOMAINS


class _FakeClient(FeishuClient):
    """Client subclass with minimal credentials for testing."""

    def __init__(self, creds):
        self.creds = dict(creds)
        self.brand = self.creds.get("brand", "feishu")
        self.base_url = BRAND_DOMAINS.get(self.brand, BRAND_DOMAINS["feishu"])
        self.app_id = self.creds["appId"]
        self.app_secret = self.creds["appSecret"]
        self.user_access_token = self.creds.get("userAccessToken")
        self._token = "TENANT_TOKEN"
        self._token_expire = time.time() + 7200


class TestDownloadIdentity(unittest.TestCase):
    def _make_client(self):
        return _FakeClient({
            "appId": "app_id",
            "appSecret": "app_secret",
            "userAccessToken": "USER_TOKEN",
        })

    def _patch_settings(self, default_identity="user"):
        tmpdir = tempfile.mkdtemp()
        path = Path(tmpdir) / "settings.json"
        path.write_text(json.dumps({"default_identity": default_identity}), encoding="utf-8")
        self._orig_settings = loader.SETTINGS_FILE
        loader.SETTINGS_FILE = path

    def _restore_settings(self):
        loader.SETTINGS_FILE = self._orig_settings

    def _capture_request_raw(self, client, captured):
        """Return a mock for _request_raw that records the resolved token.

        The mock mirrors the real _request_raw token resolution path so the
        captured token is the one that would have been sent in the
        Authorization header.
        """
        def _fake_request_raw(method, path_or_url, query=None, method_name=None):
            use_user = client._resolve_identity(method_name or client._detect_caller_method(), None)
            token = client._ensure_user_token() if use_user else client._ensure_token()
            captured.append((path_or_url, token))
            resp = MagicMock()
            resp.read.return_value = b"file content"
            resp.headers = {}
            return resp
        return _fake_request_raw

    def test_download_file_default_identity_user(self):
        self._patch_settings(default_identity="user")
        try:
            client = self._make_client()
            captured = []
            with tempfile.TemporaryDirectory() as tmpdir:
                save_path = Path(tmpdir) / "downloaded.bin"
                with patch.object(client, "_request_raw", side_effect=self._capture_request_raw(client, captured)):
                    client.download_file("file_token_123", str(save_path))
            self.assertEqual(len(captured), 1)
            url, token = captured[0]
            self.assertIn("file_token_123", url)
            self.assertEqual(token, "USER_TOKEN")
        finally:
            self._restore_settings()

    def test_drive_export_download_default_identity_user(self):
        self._patch_settings(default_identity="user")
        try:
            client = self._make_client()
            captured = []
            with tempfile.TemporaryDirectory() as tmpdir:
                save_path = Path(tmpdir) / "exported.bin"
                with patch.object(client, "_request_raw", side_effect=self._capture_request_raw(client, captured)):
                    client.drive_export_download("export_token_456", str(save_path))
            self.assertEqual(len(captured), 1)
            url, token = captured[0]
            self.assertIn("export_token_456", url)
            self.assertEqual(token, "USER_TOKEN")
        finally:
            self._restore_settings()

    def test_download_file_default_identity_tenant(self):
        self._patch_settings(default_identity="tenant")
        try:
            client = self._make_client()
            captured = []
            with tempfile.TemporaryDirectory() as tmpdir:
                save_path = Path(tmpdir) / "downloaded.bin"
                with patch.object(client, "_request_raw", side_effect=self._capture_request_raw(client, captured)):
                    client.download_file("file_token_123", str(save_path))
            self.assertEqual(len(captured), 1)
            _, token = captured[0]
            self.assertEqual(token, "TENANT_TOKEN")
        finally:
            self._restore_settings()

    def test_drive_export_download_default_identity_tenant(self):
        self._patch_settings(default_identity="tenant")
        try:
            client = self._make_client()
            captured = []
            with tempfile.TemporaryDirectory() as tmpdir:
                save_path = Path(tmpdir) / "exported.bin"
                with patch.object(client, "_request_raw", side_effect=self._capture_request_raw(client, captured)):
                    client.drive_export_download("export_token_456", str(save_path))
            self.assertEqual(len(captured), 1)
            _, token = captured[0]
            self.assertEqual(token, "TENANT_TOKEN")
        finally:
            self._restore_settings()


if __name__ == "__main__":
    unittest.main()
