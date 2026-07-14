#!/usr/bin/env python3
"""Tests for auth_sync_permissions helpers."""

import json
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

MODULE_PATH = Path(__file__).parent.parent / "feishu-auth" / "auth_sync_permissions.py"
SPEC = importlib.util.spec_from_file_location("auth_sync_permissions", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)

build_permissions_payload = MODULE.build_permissions_payload
fetch_tenant_scopes = MODULE.fetch_tenant_scopes
_load_scope_file = MODULE._load_scope_file
_load_user_scopes_from_credentials = MODULE._load_user_scopes_from_credentials


class _FakeClient:
    def _request(self, method, path, use_user_token=False, method_name=None):
        self.last_call = (method, path, use_user_token, method_name)
        return {
            "scopes": [
                {"scope_name": "docx:document", "scope_type": "tenant", "grant_status": 1},
                {"scope_name": "docx:document", "scope_type": "tenant", "grant_status": 1},
                {"scope_name": "wiki:wiki", "scope_type": "tenant", "grant_status": 0},
                {"scope_name": "task:task:read", "scope_type": "tenant", "grant_status": 1},
                {"scope_name": "user:ignored", "scope_type": "user", "grant_status": 1},
            ]
        }


class TestLoadScopeFile(unittest.TestCase):
    def test_missing_file_returns_empty_shape(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "missing.json"
            self.assertEqual(_load_scope_file(path), {"scopes": {"tenant": [], "user": []}})

    def test_existing_file_normalizes_and_sorts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "permissions.json"
            path.write_text(
                json.dumps({"scopes": {"tenant": ["b", "a", "a"], "user": ["u2", "u1"]}}),
                encoding="utf-8",
            )
            self.assertEqual(
                _load_scope_file(path),
                {"scopes": {"tenant": ["a", "b"], "user": ["u1", "u2"]}},
            )

    def test_load_user_scopes_from_credentials(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "credentials.json"
            path.write_text(json.dumps({"userScopes": ["wiki:wiki", "bitable:app", "wiki:wiki"]}), encoding="utf-8")
            self.assertEqual(
                _load_user_scopes_from_credentials(path),
                ["bitable:app", "wiki:wiki"],
            )


class TestFetchTenantScopes(unittest.TestCase):
    def test_filters_authorized_tenant_scopes(self):
        client = _FakeClient()
        result = fetch_tenant_scopes(client)
        self.assertEqual(result, ["docx:document", "task:task:read"])
        self.assertEqual(client.last_call, ("GET", "/open-apis/application/v6/scopes", False, "application_scopes"))


class TestBuildPermissionsPayload(unittest.TestCase):
    def test_builds_stable_sorted_payload(self):
        payload = build_permissions_payload(
            ["task:task:read", "docx:document", "docx:document"],
            ["wiki:wiki", "bitable:app", "wiki:wiki"],
        )
        self.assertEqual(
            payload,
            {
                "scopes": {
                    "tenant": ["docx:document", "task:task:read"],
                    "user": ["bitable:app", "wiki:wiki"],
                },
                "admin_approval_scopes": [],
            },
        )

    def test_flags_admin_approval_scopes(self):
        payload = build_permissions_payload(
            ["drive:file", "docx:document"],
            ["docs:permission.member", "im:message"],
        )
        self.assertEqual(
            sorted(payload["admin_approval_scopes"]),
            ["docs:permission.member", "drive:file"],
        )


if __name__ == "__main__":
    unittest.main()
