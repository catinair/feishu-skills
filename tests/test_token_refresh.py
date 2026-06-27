#!/usr/bin/env python3
"""Tests for FeishuClient user_access_token refresh and ensure logic."""

import json
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from feishu_common._client_core import BRAND_DOMAINS, FeishuClientCore


class _FakeClient(FeishuClientCore):
    """Client subclass that never loads real credentials."""

    def __init__(self, creds, creds_path=None):
        # Bypass FeishuClientCore.__init__ to avoid file/network access
        self.creds = dict(creds)
        self.creds["_source_path"] = creds_path
        self.brand = self.creds.get("brand", "feishu")
        self.base_url = BRAND_DOMAINS.get(self.brand, BRAND_DOMAINS["feishu"])
        self.app_id = self.creds["appId"]
        self.app_secret = self.creds["appSecret"]
        self.user_access_token = self.creds.get("userAccessToken") or self.creds.get("user_access_token")
        self._token = "fake_tenant_token"
        self._token_expire = time.time() + 7200


class TestRefreshUserToken(unittest.TestCase):
    def _make_client(self, creds, creds_path=None):
        return _FakeClient(creds, creds_path=creds_path)

    def _make_success_response(self, access_token="NEW_TOKEN", refresh_token="NEW_REFRESH"):
        payload = json.dumps({
            "code": 0,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": 7200,
            "refresh_token_expires_in": 2592000,
            "scope": "scope1 scope2",
        }).encode("utf-8")
        resp = MagicMock()
        resp.read.return_value = payload
        return resp

    def _make_error_response(self, code=999):
        payload = json.dumps({"code": code, "msg": "bad request"}).encode("utf-8")
        resp = MagicMock()
        resp.read.return_value = payload
        return resp

    def test_success_writes_token_and_updates_client(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            creds_path = Path(tmpdir) / "credentials.json"
            creds = {
                "appId": "app_id",
                "appSecret": "app_secret",
                "userAccessToken": "OLD_TOKEN",
                "userTokenExpire": time.time() - 100,
                "refreshToken": "REFRESH_TOKEN",
            }
            creds_path.write_text(json.dumps(creds), encoding="utf-8")
            client = self._make_client(creds, creds_path=str(creds_path))

            with patch("urllib.request.urlopen", return_value=self._make_success_response()):
                result = client._refresh_user_token()

            self.assertEqual(result, "NEW_TOKEN")
            self.assertEqual(client.user_access_token, "NEW_TOKEN")
            self.assertEqual(client.creds["userAccessToken"], "NEW_TOKEN")

            saved = json.loads(creds_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["userAccessToken"], "NEW_TOKEN")
            self.assertEqual(saved["refreshToken"], "NEW_REFRESH")
            self.assertIn("userTokenExpire", saved)
            self.assertIn("refreshTokenExpire", saved)
            self.assertEqual(set(saved["userScopes"]), {"scope1", "scope2"})

    def test_refresh_token_expired_returns_none(self):
        client = self._make_client({
            "appId": "app_id",
            "appSecret": "app_secret",
            "refreshToken": "REFRESH_TOKEN",
            "refreshTokenExpire": time.time() - 100,
        })
        with patch("urllib.request.urlopen") as mock_urlopen:
            result = client._refresh_user_token()
            mock_urlopen.assert_not_called()
        self.assertIsNone(result)

    def test_missing_refresh_token_returns_none(self):
        client = self._make_client({
            "appId": "app_id",
            "appSecret": "app_secret",
        })
        with patch("urllib.request.urlopen") as mock_urlopen:
            result = client._refresh_user_token()
            mock_urlopen.assert_not_called()
        self.assertIsNone(result)

    def test_api_error_returns_none(self):
        client = self._make_client({
            "appId": "app_id",
            "appSecret": "app_secret",
            "refreshToken": "REFRESH_TOKEN",
        })
        with patch("urllib.request.urlopen", return_value=self._make_error_response()):
            result = client._refresh_user_token()
        self.assertIsNone(result)

    def test_network_exception_returns_none(self):
        client = self._make_client({
            "appId": "app_id",
            "appSecret": "app_secret",
            "refreshToken": "REFRESH_TOKEN",
        })
        with patch("urllib.request.urlopen", side_effect=IOError("network down")):
            result = client._refresh_user_token()
        self.assertIsNone(result)


class TestEnsureUserToken(unittest.TestCase):
    def _make_client(self, creds, creds_path=None):
        return _FakeClient(creds, creds_path=creds_path)

    def test_not_expired_returns_existing_token(self):
        client = self._make_client({
            "appId": "app_id",
            "appSecret": "app_secret",
            "userAccessToken": "EXISTING_TOKEN",
            "userTokenExpire": time.time() + 7200,
        })
        with patch.object(client, "_refresh_user_token") as mock_refresh:
            result = client._ensure_user_token()
            mock_refresh.assert_not_called()
        self.assertEqual(result, "EXISTING_TOKEN")

    def test_expired_refreshes_and_returns_new_token(self):
        client = self._make_client({
            "appId": "app_id",
            "appSecret": "app_secret",
            "userAccessToken": "OLD_TOKEN",
            "userTokenExpire": time.time() - 100,
            "refreshToken": "REFRESH_TOKEN",
        })
        with patch.object(client, "_refresh_user_token", return_value="REFRESHED_TOKEN") as mock_refresh:
            result = client._ensure_user_token()
            mock_refresh.assert_called_once()
        self.assertEqual(result, "REFRESHED_TOKEN")

    def test_expired_and_refresh_fails_raises(self):
        client = self._make_client({
            "appId": "app_id",
            "appSecret": "app_secret",
            "userAccessToken": "OLD_TOKEN",
            "userTokenExpire": time.time() - 100,
            "refreshToken": "REFRESH_TOKEN",
        })
        with patch.object(client, "_refresh_user_token", return_value=None):
            with self.assertRaises(RuntimeError) as ctx:
                client._ensure_user_token()
            self.assertIn("已过期", str(ctx.exception))

    def test_no_user_token_raises(self):
        client = self._make_client({
            "appId": "app_id",
            "appSecret": "app_secret",
        })
        with patch.object(client, "_refresh_user_token", return_value=None):
            with self.assertRaises(RuntimeError) as ctx:
                client._ensure_user_token()
            self.assertIn("未配置", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
