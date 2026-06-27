#!/usr/bin/env python3
"""Tests for identity resolution: _resolve_identity, _detect_caller_method,
load_default_identity, and load_granted_scopes."""

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
from feishu_common._endpoint_registry import ENDPOINT_REGISTRY, APP_ONLY, USER_ONLY, BOTH


class _FakeClient:
    """Minimal fake client exposing only the resolver methods."""

    def __init__(self):
        self.user_access_token = "fake_user_token"

    # Import the real methods from FeishuClientCore
    from feishu_common._client_core import FeishuClientCore
    _detect_caller_method = FeishuClientCore._detect_caller_method
    _resolve_identity = FeishuClientCore._resolve_identity
    _ensure_user_token = FeishuClientCore._ensure_user_token
    _ensure_token = FeishuClientCore._ensure_token


class TestLoadDefaultIdentity(unittest.TestCase):
    def test_returns_user_when_no_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            original = loader.SETTINGS_FILE
            loader.SETTINGS_FILE = Path(tmpdir) / "missing.json"
            try:
                self.assertEqual(loader.load_default_identity(), "user")
            finally:
                loader.SETTINGS_FILE = original

    def test_returns_user_when_key_absent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "settings.json"
            path.write_text(json.dumps({"user": {}}), encoding="utf-8")
            original = loader.SETTINGS_FILE
            loader.SETTINGS_FILE = path
            try:
                self.assertEqual(loader.load_default_identity(), "user")
            finally:
                loader.SETTINGS_FILE = original

    def test_returns_user_when_configured(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "settings.json"
            path.write_text(json.dumps({"default_identity": "user"}), encoding="utf-8")
            original = loader.SETTINGS_FILE
            loader.SETTINGS_FILE = path
            try:
                self.assertEqual(loader.load_default_identity(), "user")
            finally:
                loader.SETTINGS_FILE = original


class TestLoadGrantedScopes(unittest.TestCase):
    def test_returns_sets_from_permissions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "permissions.json"
            path.write_text(json.dumps({
                "scopes": {
                    "tenant": ["a:read", "b:write"],
                    "user": ["c:read"],
                }
            }), encoding="utf-8")
            original = loader.PERMISSIONS_FILE
            loader.PERMISSIONS_FILE = path
            try:
                result = loader.load_granted_scopes()
                self.assertEqual(result["tenant"], {"a:read", "b:write"})
                self.assertEqual(result["user"], {"c:read"})
            finally:
                loader.PERMISSIONS_FILE = original

    def test_returns_empty_sets_when_no_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            original = loader.PERMISSIONS_FILE
            loader.PERMISSIONS_FILE = Path(tmpdir) / "missing.json"
            try:
                result = loader.load_granted_scopes()
                self.assertEqual(result["tenant"], set())
                self.assertEqual(result["user"], set())
            finally:
                loader.PERMISSIONS_FILE = original


class TestResolveIdentity(unittest.TestCase):
    """Test _resolve_identity with various configurations."""

    def _make_client(self, default_identity="tenant", tenant_scopes=None, user_scopes=None):
        """Create a fake client with patched config."""
        client = _FakeClient()
        # Patch config loaders
        self._settings_file = Path(tempfile.mkdtemp()) / "settings.json"
        self._settings_file.write_text(
            json.dumps({"default_identity": default_identity}), encoding="utf-8"
        )
        self._perms_file = Path(tempfile.mkdtemp()) / "permissions.json"
        self._perms_file.write_text(json.dumps({
            "scopes": {
                "tenant": tenant_scopes or [],
                "user": user_scopes or [],
            }
        }), encoding="utf-8")
        self._orig_settings = loader.SETTINGS_FILE
        self._orig_perms = loader.PERMISSIONS_FILE
        loader.SETTINGS_FILE = self._settings_file
        loader.PERMISSIONS_FILE = self._perms_file
        return client

    def _restore(self):
        loader.SETTINGS_FILE = self._orig_settings
        loader.PERMISSIONS_FILE = self._orig_perms

    # --- Priority 1: Explicit overrides ---

    def test_explicit_true_with_both(self):
        client = self._make_client()
        try:
            result = client._resolve_identity("document_create", True)
            self.assertTrue(result)
        finally:
            self._restore()

    def test_explicit_false_with_both(self):
        client = self._make_client()
        try:
            result = client._resolve_identity("document_create", False)
            self.assertFalse(result)
        finally:
            self._restore()

    def test_explicit_true_with_app_only_raises(self):
        client = self._make_client()
        try:
            with self.assertRaises(RuntimeError):
                client._resolve_identity("upload_image", True)
        finally:
            self._restore()

    def test_explicit_false_with_user_only_raises(self):
        client = self._make_client()
        try:
            with self.assertRaises(RuntimeError):
                client._resolve_identity("contact_get_user", False)
        finally:
            self._restore()

    def test_explicit_true_with_user_only(self):
        client = self._make_client()
        try:
            result = client._resolve_identity("contact_get_user", True)
            self.assertTrue(result)
        finally:
            self._restore()

    def test_explicit_false_with_app_only(self):
        client = self._make_client()
        try:
            result = client._resolve_identity("upload_image", False)
            self.assertFalse(result)
        finally:
            self._restore()

    def test_explicit_override_for_unknown_method(self):
        client = self._make_client()
        try:
            result = client._resolve_identity("nonexistent_method", True)
            self.assertTrue(result)
        finally:
            self._restore()

    # --- Priority 2: Registry-driven resolution ---

    def test_app_only_returns_false(self):
        client = self._make_client()
        try:
            result = client._resolve_identity("upload_image", None)
            self.assertFalse(result)
        finally:
            self._restore()

    def test_user_only_returns_true(self):
        client = self._make_client()
        try:
            result = client._resolve_identity("contact_get_user", None)
            self.assertTrue(result)
        finally:
            self._restore()

    def test_both_only_tenant_scopes_granted(self):
        client = self._make_client(
            tenant_scopes=["docx:document:create"],
            user_scopes=[],
        )
        try:
            result = client._resolve_identity("document_create", None)
            self.assertFalse(result)
        finally:
            self._restore()

    def test_both_only_user_scopes_granted(self):
        client = self._make_client(
            tenant_scopes=[],
            user_scopes=["docx:document"],
        )
        try:
            result = client._resolve_identity("document_create", None)
            self.assertTrue(result)
        finally:
            self._restore()

    def test_both_scopes_granted_uses_default_tenant(self):
        client = self._make_client(
            default_identity="tenant",
            tenant_scopes=["docx:document:create"],
            user_scopes=["docx:document"],
        )
        try:
            result = client._resolve_identity("document_create", None)
            self.assertFalse(result)
        finally:
            self._restore()

    def test_both_scopes_granted_uses_default_user(self):
        client = self._make_client(
            default_identity="user",
            tenant_scopes=["docx:document:create"],
            user_scopes=["docx:document"],
        )
        try:
            result = client._resolve_identity("document_create", None)
            self.assertTrue(result)
        finally:
            self._restore()

    def test_neither_scope_granted_uses_default(self):
        client = self._make_client(
            default_identity="tenant",
            tenant_scopes=[],
            user_scopes=[],
        )
        try:
            result = client._resolve_identity("document_create", None)
            self.assertFalse(result)
        finally:
            self._restore()

    # --- Priority 3: Not in registry ---

    def test_unknown_method_uses_default_tenant(self):
        client = self._make_client(default_identity="tenant")
        try:
            result = client._resolve_identity("nonexistent_method", None)
            self.assertFalse(result)
        finally:
            self._restore()

    def test_unknown_method_uses_default_user(self):
        client = self._make_client(default_identity="user")
        try:
            result = client._resolve_identity("nonexistent_method", None)
            self.assertTrue(result)
        finally:
            self._restore()


class TestDetectCallerMethod(unittest.TestCase):
    """Test frame introspection for caller method detection."""

    def test_finds_direct_caller(self):
        """Simulate: public_method -> _request -> _detect_caller_method"""
        client = _FakeClient()

        def _request():
            return client._detect_caller_method()

        def document_create():
            return _request()

        result = document_create()
        self.assertEqual(result, "document_create")

    def test_finds_caller_through_intermediate(self):
        """Simulate: public_method -> _paginate -> _request -> _detect_caller_method"""
        client = _FakeClient()

        def _paginate():
            return client._detect_caller_method()

        def contact_search_users():
            return _paginate()

        result = contact_search_users()
        self.assertEqual(result, "contact_search_users")

    def test_returns_none_for_private_chain(self):
        """When all callers are private, returns None."""
        client = _FakeClient()

        def _private_helper():
            return client._detect_caller_method()

        result = _private_helper()
        self.assertIsNone(result)




class _FakeFeishuClient(FeishuClient):
    """Subclass that bypasses real __init__ and credentials loading."""

    def __init__(self):
        self.creds = {"appId": "app_id", "appSecret": "app_secret"}
        self.brand = "feishu"
        self.base_url = BRAND_DOMAINS["feishu"]
        self.app_id = self.creds["appId"]
        self.app_secret = self.creds["appSecret"]
        self.user_access_token = "USER_TOKEN"
        self._token = "TENANT_TOKEN"
        self._token_expire = time.time() + 7200


class TestMixinTokenSelection(unittest.TestCase):
    """End-to-end token selection through real mixin methods.

    Token ensuring is mocked, but the real _request path runs so that
    _resolve_identity and _detect_caller_method are exercised. Network
    requests are intercepted at urllib.request.urlopen; the Authorization
    header token is recorded and asserted.
    """

    def _make_client(self):
        return _FakeFeishuClient()

    def _patch_config(self, default_identity="user", tenant_scopes=None, user_scopes=None):
        self._settings_file = Path(tempfile.mkdtemp()) / "settings.json"
        self._settings_file.write_text(
            json.dumps({"default_identity": default_identity}), encoding="utf-8"
        )
        self._perms_file = Path(tempfile.mkdtemp()) / "permissions.json"
        self._perms_file.write_text(json.dumps({
            "scopes": {
                "tenant": tenant_scopes or [],
                "user": user_scopes or [],
            }
        }), encoding="utf-8")
        self._orig_settings = loader.SETTINGS_FILE
        self._orig_perms = loader.PERMISSIONS_FILE
        loader.SETTINGS_FILE = self._settings_file
        loader.PERMISSIONS_FILE = self._perms_file

    def _restore_config(self):
        loader.SETTINGS_FILE = self._orig_settings
        loader.PERMISSIONS_FILE = self._orig_perms

    def _urlopen_capture(self, captured):
        """Return a urllib.request.urlopen stand-in that records the Bearer token."""
        def _fake_urlopen(req, timeout=None):
            auth = req.get_header("Authorization") or ""
            captured.append(auth.replace("Bearer ", "") if auth.startswith("Bearer ") else auth)
            resp = MagicMock()
            resp.read.return_value = b'{"code":0,"data":{}}'
            resp.status = 200
            return resp
        return _fake_urlopen

    def test_app_only_uses_tenant_token(self):
        self._patch_config(default_identity="user", tenant_scopes=["im:resource"])
        try:
            client = self._make_client()
            captured = []
            with patch.object(client, "_ensure_user_token", return_value="USER_TOKEN") as mock_user:
                with patch.object(client, "_ensure_token", return_value="TENANT_TOKEN") as mock_tenant:
                    with patch("urllib.request.urlopen", side_effect=self._urlopen_capture(captured)):
                        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                            tmp.write(b"png")
                            tmp_path = tmp.name
                        try:
                            client.upload_image(tmp_path)
                        finally:
                            Path(tmp_path).unlink(missing_ok=True)
            self.assertEqual(captured, ["TENANT_TOKEN"])
            mock_tenant.assert_called_once()
            mock_user.assert_not_called()
        finally:
            self._restore_config()

    def test_user_only_uses_user_token(self):
        self._patch_config(default_identity="tenant", user_scopes=["task:task:write"])
        try:
            client = self._make_client()
            captured = []
            with patch.object(client, "_ensure_user_token", return_value="USER_TOKEN") as mock_user:
                with patch.object(client, "_ensure_token", return_value="TENANT_TOKEN") as mock_tenant:
                    with patch("urllib.request.urlopen", side_effect=self._urlopen_capture(captured)):
                        client.task_create(summary="test")
            self.assertEqual(captured, ["USER_TOKEN"])
            mock_user.assert_called_once()
            mock_tenant.assert_not_called()
        finally:
            self._restore_config()

    def test_both_scopes_granted_uses_default_user(self):
        self._patch_config(
            default_identity="user",
            tenant_scopes=["docx:document:create"],
            user_scopes=["docx:document"],
        )
        try:
            client = self._make_client()
            captured = []
            with patch.object(client, "_ensure_user_token", return_value="USER_TOKEN") as mock_user:
                with patch.object(client, "_ensure_token", return_value="TENANT_TOKEN") as mock_tenant:
                    with patch("urllib.request.urlopen", side_effect=self._urlopen_capture(captured)):
                        client.document_create(title="test")
            self.assertEqual(captured, ["USER_TOKEN"])
            mock_user.assert_called_once()
            mock_tenant.assert_not_called()
        finally:
            self._restore_config()

    def test_both_scopes_granted_uses_default_tenant(self):
        self._patch_config(
            default_identity="tenant",
            tenant_scopes=["docx:document:create"],
            user_scopes=["docx:document"],
        )
        try:
            client = self._make_client()
            captured = []
            with patch.object(client, "_ensure_user_token", return_value="USER_TOKEN") as mock_user:
                with patch.object(client, "_ensure_token", return_value="TENANT_TOKEN") as mock_tenant:
                    with patch("urllib.request.urlopen", side_effect=self._urlopen_capture(captured)):
                        client.document_create(title="test")
            self.assertEqual(captured, ["TENANT_TOKEN"])
            mock_tenant.assert_called_once()
            mock_user.assert_not_called()
        finally:
            self._restore_config()

    def test_both_missing_scopes_raises_preflight_error_user(self):
        """user 默认身份下缺少所需 scope 时，调用前预检应给出明确错误。"""
        self._patch_config(default_identity="user", tenant_scopes=[], user_scopes=[])
        try:
            client = self._make_client()
            with patch.object(client, "_ensure_user_token", return_value="USER_TOKEN"):
                with patch.object(client, "_ensure_token", return_value="TENANT_TOKEN"):
                    with patch("urllib.request.urlopen", side_effect=self._urlopen_capture([])):
                        with self.assertRaises(RuntimeError) as ctx:
                            client.document_create(title="test")
            self.assertIn("docx:document", str(ctx.exception))
            self.assertIn("用户身份", str(ctx.exception))
        finally:
            self._restore_config()

    def test_both_missing_scopes_raises_preflight_error_tenant(self):
        """tenant 默认身份下缺少所需 scope 时，调用前预检应给出明确错误。"""
        self._patch_config(default_identity="tenant", tenant_scopes=[], user_scopes=[])
        try:
            client = self._make_client()
            with patch.object(client, "_ensure_user_token", return_value="USER_TOKEN"):
                with patch.object(client, "_ensure_token", return_value="TENANT_TOKEN"):
                    with patch("urllib.request.urlopen", side_effect=self._urlopen_capture([])):
                        with self.assertRaises(RuntimeError) as ctx:
                            client.document_create(title="test")
            self.assertIn("docx:document:create", str(ctx.exception))
            self.assertIn("应用身份", str(ctx.exception))
        finally:
            self._restore_config()


if __name__ == "__main__":
    unittest.main()
