#!/usr/bin/env python3
"""Tests for _config_loader helper functions."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import feishu_common._config_loader as loader


class TestGetDefaultFolderToken(unittest.TestCase):
    def test_returns_default_marked_token(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "risk_policy.json"
            path.write_text(json.dumps({
                "workspace": {
                    "trusted_folder_tokens": [
                        {"token": "aaa", "label": "first"},
                        {"token": "bbb", "label": "default", "default": True},
                    ]
                }
            }), encoding="utf-8")
            original = loader.RISK_POLICY_FILE
            loader.RISK_POLICY_FILE = path
            try:
                self.assertEqual(loader.get_default_folder_token(), "bbb")
            finally:
                loader.RISK_POLICY_FILE = original

    def test_returns_first_token_when_no_default_flag(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "risk_policy.json"
            path.write_text(json.dumps({
                "workspace": {
                    "trusted_folder_tokens": [
                        {"token": "first", "label": "a"},
                        {"token": "second", "label": "b"},
                    ]
                }
            }), encoding="utf-8")
            original = loader.RISK_POLICY_FILE
            loader.RISK_POLICY_FILE = path
            try:
                self.assertEqual(loader.get_default_folder_token(), "first")
            finally:
                loader.RISK_POLICY_FILE = original

    def test_raises_when_no_tokens(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "risk_policy.json"
            path.write_text(json.dumps({"workspace": {"trusted_folder_tokens": []}}), encoding="utf-8")
            original = loader.RISK_POLICY_FILE
            loader.RISK_POLICY_FILE = path
            try:
                with self.assertRaises(RuntimeError):
                    loader.get_default_folder_token()
            finally:
                loader.RISK_POLICY_FILE = original

    def test_raises_when_no_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            original = loader.RISK_POLICY_FILE
            loader.RISK_POLICY_FILE = Path(tmpdir) / "missing.json"
            try:
                with self.assertRaises(RuntimeError):
                    loader.get_default_folder_token()
            finally:
                loader.RISK_POLICY_FILE = original


class TestTrustedSets(unittest.TestCase):
    def _with_policy(self, policy):
        tmpdir = tempfile.mkdtemp()
        path = Path(tmpdir) / "risk_policy.json"
        path.write_text(json.dumps(policy), encoding="utf-8")
        self._patch = loader.RISK_POLICY_FILE
        loader.RISK_POLICY_FILE = path

    def _restore(self):
        loader.RISK_POLICY_FILE = self._patch

    def test_trusted_folder_tokens(self):
        self._with_policy({"workspace": {"trusted_folder_tokens": [
            {"token": "a"}, {"token": "b"}, {"token": ""}
        ]}})
        try:
            result = loader.trusted_folder_tokens()
            self.assertEqual(result, {"a", "b"})
        finally:
            self._restore()

    def test_trusted_user_ids(self):
        self._with_policy({"messaging": {"trusted_users": [
            {"user_id": "u1"}, {"user_id": "u2"}
        ]}})
        try:
            result = loader.trusted_user_ids()
            self.assertEqual(result, {"u1", "u2"})
        finally:
            self._restore()

    def test_trusted_chat_ids(self):
        self._with_policy({"messaging": {"trusted_chats": [
            {"chat_id": "c1"}
        ]}})
        try:
            result = loader.trusted_chat_ids()
            self.assertEqual(result, {"c1"})
        finally:
            self._restore()

    def test_is_trusted_folder(self):
        self._with_policy({"workspace": {"trusted_folder_tokens": [{"token": "abc"}]}})
        try:
            self.assertTrue(loader.is_trusted_folder("abc"))
            self.assertFalse(loader.is_trusted_folder("xyz"))
        finally:
            self._restore()

    def test_is_trusted_user(self):
        self._with_policy({"messaging": {"trusted_users": [{"user_id": "u1"}]}})
        try:
            self.assertTrue(loader.is_trusted_user("u1"))
            self.assertFalse(loader.is_trusted_user("u2"))
        finally:
            self._restore()

    def test_is_trusted_chat(self):
        self._with_policy({"messaging": {"trusted_chats": [{"chat_id": "c1"}]}})
        try:
            self.assertTrue(loader.is_trusted_chat("c1"))
            self.assertFalse(loader.is_trusted_chat("c2"))
        finally:
            self._restore()


class TestWritePolicy(unittest.TestCase):
    def _with_policy(self, policy):
        tmpdir = tempfile.mkdtemp()
        path = Path(tmpdir) / "risk_policy.json"
        path.write_text(json.dumps(policy), encoding="utf-8")
        self._patch = loader.RISK_POLICY_FILE
        loader.RISK_POLICY_FILE = path

    def _restore(self):
        loader.RISK_POLICY_FILE = self._patch

    def test_requires_confirmation(self):
        self._with_policy({"writes": {"always_confirm_actions": ["doc_write", "base_delete"]}})
        try:
            self.assertTrue(loader.requires_confirmation_for_action("doc_write"))
            self.assertTrue(loader.requires_confirmation_for_action("base_delete"))
            self.assertFalse(loader.requires_confirmation_for_action("doc_create"))
        finally:
            self._restore()

    def test_is_manual_only(self):
        self._with_policy({"writes": {"manual_only_actions": ["drive_delete"]}})
        try:
            self.assertTrue(loader.is_manual_only_action("drive_delete"))
            self.assertFalse(loader.is_manual_only_action("doc_create"))
        finally:
            self._restore()

    def test_allows_implicit_confirmation_only_when_trusted(self):
        self._with_policy({"writes": {"allow_without_confirmation": [
            {"action": "doc_create", "within_trusted_folder_only": True}
        ]}})
        try:
            self.assertTrue(loader.allows_implicit_confirmation("doc_create", is_trusted=True))
            self.assertFalse(loader.allows_implicit_confirmation("doc_create", is_trusted=False))
        finally:
            self._restore()

    def test_should_confirm_action_obeys_allowlist_and_always_confirm(self):
        self._with_policy({"writes": {
            "allow_without_confirmation": [
                {"action": "doc_create", "within_trusted_folder_only": True}
            ],
            "always_confirm_actions": ["im_send_message"]
        }})
        try:
            self.assertFalse(loader.should_confirm_action("doc_create", is_trusted=True))
            self.assertTrue(loader.should_confirm_action("doc_create", is_trusted=False))
            self.assertTrue(loader.should_confirm_action("im_send_message", is_trusted=True))
        finally:
            self._restore()

    def test_ensure_not_manual_only_raises(self):
        self._with_policy({"writes": {"manual_only_actions": ["drive_delete"]}})
        try:
            with self.assertRaises(RuntimeError):
                loader.ensure_not_manual_only("drive_delete")
        finally:
            self._restore()


class TestLoadCredentialsData(unittest.TestCase):
    def test_from_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "creds.json"
            path.write_text(json.dumps({"appId": "id1", "appSecret": "sec1"}), encoding="utf-8")
            data, resolved = loader.load_credentials_data(str(path))
            self.assertEqual(data["appId"], "id1")
            self.assertEqual(resolved, path)

    def test_from_env_vars(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "missing.json"
            old_env = {}
            for k in ("FEISHU_APP_ID", "FEISHU_APP_SECRET", "FEISHU_BRAND"):
                old_env[k] = os.environ.get(k)
            try:
                os.environ["FEISHU_APP_ID"] = "env_id"
                os.environ["FEISHU_APP_SECRET"] = "env_sec"
                os.environ["FEISHU_BRAND"] = "lark"
                data, resolved = loader.load_credentials_data(str(path))
                self.assertEqual(data["appId"], "env_id")
                self.assertEqual(data["brand"], "lark")
                self.assertIsNone(resolved)
            finally:
                for k, v in old_env.items():
                    if v is None:
                        os.environ.pop(k, None)
                    else:
                        os.environ[k] = v

    def test_raises_when_no_file_no_env(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "missing.json"
            old_env = {}
            for k in ("FEISHU_APP_ID", "FEISHU_APP_SECRET"):
                old_env[k] = os.environ.get(k)
                os.environ.pop(k, None)
            try:
                with self.assertRaises(RuntimeError):
                    loader.load_credentials_data(str(path))
            finally:
                for k, v in old_env.items():
                    if v is not None:
                        os.environ[k] = v


if __name__ == "__main__":
    unittest.main()
