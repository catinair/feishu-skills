#!/usr/bin/env python3
"""Tests for cloud-only token management via CloudTokenManager."""

import json
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from feishu_common._client_core import BRAND_DOMAINS, FeishuClientCore
from feishu_common.cloud_token_manager import CloudTokenManager


class _FakeClient(FeishuClientCore):
    """Client subclass that never loads real credentials."""

    def __init__(self, creds, creds_path=None, bitable_infra=None):
        self.creds = dict(creds)
        self.creds["_source_path"] = creds_path
        self.brand = self.creds.get("brand", "feishu")
        self.base_url = BRAND_DOMAINS.get(self.brand, BRAND_DOMAINS["feishu"])
        self.app_id = self.creds["appId"]
        self.app_secret = self.creds["appSecret"]
        self.user_access_token = self.creds.get("userAccessToken")
        self._token = "fake_tenant_token"
        self._token_expire = time.time() + 7200
        if bitable_infra:
            self._cloud_token_manager = CloudTokenManager(
                app_id=self.app_id,
                app_secret=self.app_secret,
                bitable_infra=bitable_infra,
            )
        else:
            self._cloud_token_manager = None


def _make_json_response(payload, status=200):
    data = json.dumps(payload).encode("utf-8")
    resp = MagicMock()
    resp.read.return_value = data
    resp.code = status
    return resp


class TestCloudTokenManager(unittest.TestCase):
    def _make_manager(self):
        return CloudTokenManager(
            app_id="app_id",
            app_secret="app_secret",
            bitable_infra={"app_token": "app_token", "table_id": "table_id"},
        )

    def _make_tenant_token_response(self):
        return _make_json_response({
            "code": 0,
            "tenant_access_token": "TENANT_TOKEN",
            "expire": 7200,
        })

    def _make_bitable_search_response(self, refresh_token="RT_FROM_BITABLE"):
        return _make_json_response({
            "code": 0,
            "data": {
                "items": [
                    {
                        "record_id": "rec_1",
                        "fields": {
                            "app_id": "app_id",
                            "refresh_token": refresh_token,
                            "refresh_token_expire": int(time.time() + 86400),
                            "updated_at": int(time.time() * 1000),
                        },
                    }
                ]
            },
        })

    def _make_refresh_response(self, access_token="NEW_AT", refresh_token="NEW_RT"):
        return _make_json_response({
            "code": 0,
            "data": {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expires_in": 7200,
                "refresh_token_expires_in": 2592000,
            },
        })

    def test_get_user_access_token_reads_bitable_and_refreshes(self):
        manager = self._make_manager()

        def urlopen_side_effect(req, **kwargs):
            url = req.full_url
            if "tenant_access_token" in url:
                return self._make_tenant_token_response()
            if "records/search" in url:
                return self._make_bitable_search_response("OLD_RT")
            if "authen/v2/oauth/token" in url:
                return self._make_refresh_response("NEW_AT", "NEW_RT")
            if "records" in url and req.method == "POST":
                return _make_json_response({"code": 0, "data": {"record": {"record_id": "rec_new"}}})
            raise RuntimeError(f"unexpected URL: {url}")

        with patch("urllib.request.urlopen", side_effect=urlopen_side_effect):
            token = manager.get_user_access_token()

        self.assertEqual(token, "NEW_AT")
        self.assertEqual(manager._user_access_token, "NEW_AT")

    def test_get_user_access_token_uses_memory_cache(self):
        manager = self._make_manager()
        manager._user_access_token = "CACHED_AT"
        manager._user_token_expire = time.time() + 7200

        with patch("urllib.request.urlopen") as mock_urlopen:
            token = manager.get_user_access_token()
            mock_urlopen.assert_not_called()

        self.assertEqual(token, "CACHED_AT")

    def test_race_condition_retries_with_latest_bitable_record(self):
        manager = self._make_manager()
        call_count = {"search": 0, "refresh": 0}

        def urlopen_side_effect(req, **kwargs):
            url = req.full_url
            if "tenant_access_token" in url:
                return self._make_tenant_token_response()
            if "records/search" in url:
                call_count["search"] += 1
                # First search returns OLD_RT; subsequent searches return NEW_RT
                rt = "OLD_RT" if call_count["search"] == 1 else "NEW_RT"
                return self._make_bitable_search_response(rt)
            if "authen/v2/oauth/token" in url:
                call_count["refresh"] += 1
                if call_count["refresh"] == 1:
                    # Simulate stale RT error
                    raise urllib.error.HTTPError(
                        url, 400, "Bad Request", {},
                        io.BytesIO(b'{"code": 999, "msg": "invalid refresh_token"}')
                    )
                return self._make_refresh_response("NEW_AT", "NEWER_RT")
            if "records" in url and req.method == "POST":
                return _make_json_response({"code": 0, "data": {"record": {"record_id": "rec_new"}}})
            raise RuntimeError(f"unexpected URL: {url}")

        import urllib.error
        import io

        with patch("time.sleep"):
            with patch("urllib.request.urlopen", side_effect=urlopen_side_effect):
                token = manager.get_user_access_token()

        self.assertEqual(token, "NEW_AT")
        self.assertGreaterEqual(call_count["search"], 2)

    def test_save_refresh_token_appends_record(self):
        manager = self._make_manager()
        appended = {"called": False}

        def urlopen_side_effect(req, **kwargs):
            url = req.full_url
            if "tenant_access_token" in url:
                return self._make_tenant_token_response()
            if "records" in url and req.method == "POST":
                appended["called"] = True
                body = json.loads(req.data.decode("utf-8"))
                self.assertEqual(body["fields"]["refresh_token"], "INITIAL_RT")
                self.assertEqual(body["fields"]["app_id"], "app_id")
                return _make_json_response({"code": 0, "data": {"record": {"record_id": "rec_new"}}})
            raise RuntimeError(f"unexpected URL: {url}")

        with patch("urllib.request.urlopen", side_effect=urlopen_side_effect):
            manager.save_refresh_token("INITIAL_RT", time.time() + 86400)

        self.assertTrue(appended["called"])


class TestClientCoreCloudMode(unittest.TestCase):
    def _make_client(self, creds, creds_path=None, bitable_infra=None):
        return _FakeClient(creds, creds_path=creds_path, bitable_infra=bitable_infra)

    def test_ensure_user_token_delegates_to_cloud_token_manager(self):
        bitable_infra = {"app_token": "app_token", "table_id": "table_id"}
        with tempfile.TemporaryDirectory() as tmpdir:
            creds_path = Path(tmpdir) / "credentials.json"
            creds = {"appId": "app_id", "appSecret": "app_secret"}
            creds_path.write_text(json.dumps(creds), encoding="utf-8")
            client = self._make_client(
                creds,
                creds_path=str(creds_path),
                bitable_infra=bitable_infra,
            )

            with patch.object(
                client._cloud_token_manager, "get_user_access_token", return_value="DELEGATED_AT"
            ):
                token = client._ensure_user_token()

            self.assertEqual(token, "DELEGATED_AT")
            self.assertEqual(client.user_access_token, "DELEGATED_AT")
            saved = json.loads(creds_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["userAccessToken"], "DELEGATED_AT")

    def test_ensure_user_token_raises_without_bitable(self):
        """非云模式（无 Bitable 且无 refresh_token）下应提示重新授权，而非要求 Bitable 基础设施。"""
        client = self._make_client({"appId": "app_id", "appSecret": "app_secret"})
        with self.assertRaises(RuntimeError) as ctx:
            client._ensure_user_token()
        self.assertIn("user_access_token", str(ctx.exception))
        self.assertNotIn("Bitable infrastructure", str(ctx.exception))

    def test_save_user_token_does_not_write_refresh_token_locally(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            creds_path = Path(tmpdir) / "credentials.json"
            creds = {
                "appId": "app_id",
                "appSecret": "app_secret",
                "userAccessToken": "OLD_AT",
            }
            creds_path.write_text(json.dumps(creds), encoding="utf-8")
            bitable_infra = {"app_token": "app_token", "table_id": "table_id"}
            client = self._make_client(creds, creds_path=str(creds_path), bitable_infra=bitable_infra)

            appended = {"called": False}

            def urlopen_side_effect(req, **kwargs):
                url = req.full_url
                if "tenant_access_token" in url:
                    return _make_json_response({"code": 0, "tenant_access_token": "TT", "expire": 7200})
                if "records" in url and req.method == "POST":
                    appended["called"] = True
                    return _make_json_response({"code": 0, "data": {"record": {"record_id": "rec"}}})
                raise RuntimeError(f"unexpected URL: {url}")

            with patch("urllib.request.urlopen", side_effect=urlopen_side_effect):
                client._save_user_token("NEW_AT", "NEW_RT", 7200, 2592000, scopes=["scope1"])

            saved = json.loads(creds_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["userAccessToken"], "NEW_AT")
            self.assertNotIn("refreshToken", saved)
            self.assertNotIn("refreshTokenExpire", saved)
            self.assertTrue(appended["called"])


if __name__ == "__main__":
    unittest.main()
