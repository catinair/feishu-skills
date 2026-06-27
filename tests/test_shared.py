#!/usr/bin/env python3
"""Tests for feishu_common pure-logic utilities."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from feishu_common._shared import extract_doc_id, extract_base_info
from feishu_common._config_loader import _deep_merge, load_settings, load_risk_policy


class TestExtractDocId(unittest.TestCase):
    def test_plain_token(self):
        self.assertEqual(extract_doc_id("doxcn123abc"), "doxcn123abc")

    def test_docx_url(self):
        self.assertEqual(
            extract_doc_id("https://example.feishu.cn/docx/doxcn123abc"),
            "doxcn123abc",
        )

    def test_doc_url(self):
        self.assertEqual(
            extract_doc_id("https://example.feishu.cn/doc/doxcn123abc?from=sidebar"),
            "doxcn123abc",
        )

    def test_wiki_url(self):
        self.assertEqual(
            extract_doc_id("https://example.feishu.cn/wiki/wikcn456def"),
            "wikcn456def",
        )

    def test_url_with_query_and_fragment(self):
        self.assertEqual(
            extract_doc_id("https://example.feishu.cn/docx/doxcnABC123?q=1#section"),
            "doxcnABC123",
        )


class TestExtractBaseInfo(unittest.TestCase):
    def test_plain_token(self):
        self.assertEqual(extract_base_info("XqA3bAtGpaWjflsryxfcadp7nmf"), ("XqA3bAtGpaWjflsryxfcadp7nmf", ""))

    def test_token_with_table(self):
        self.assertEqual(
            extract_base_info("XqA3bAtGpaWjflsryxfcadp7nmf/tblOflmn3KGcgUsn"),
            ("XqA3bAtGpaWjflsryxfcadp7nmf", "tblOflmn3KGcgUsn"),
        )

    def test_full_url(self):
        self.assertEqual(
            extract_base_info(
                "https://example.feishu.cn/base/XqA3bAtGpaWjflsryxfcadp7nmf?table=tblOflmn3KGcgUsn"
            ),
            ("XqA3bAtGpaWjflsryxfcadp7nmf", "tblOflmn3KGcgUsn"),
        )

    def test_url_without_table(self):
        self.assertEqual(
            extract_base_info("https://example.feishu.cn/base/XqA3bAtGpaWjflsryxfcadp7nmf"),
            ("XqA3bAtGpaWjflsryxfcadp7nmf", ""),
        )

    def test_url_with_extra_params(self):
        self.assertEqual(
            extract_base_info(
                "https://example.feishu.cn/base/XqA3bAtGpaWjflsryxfcadp7nmf?table=tblOflmn3KGcgUsn&view=vew123"
            ),
            ("XqA3bAtGpaWjflsryxfcadp7nmf", "tblOflmn3KGcgUsn"),
        )


class TestDeepMerge(unittest.TestCase):
    def test_simple_override(self):
        base = {"a": 1, "b": 2}
        override = {"b": 3}
        self.assertEqual(_deep_merge(base, override), {"a": 1, "b": 3})

    def test_nested_merge(self):
        base = {"a": {"x": 1, "y": 2}, "b": 3}
        override = {"a": {"y": 99}}
        self.assertEqual(_deep_merge(base, override), {"a": {"x": 1, "y": 99}, "b": 3})

    def test_nested_replace_with_primitive(self):
        base = {"a": {"x": 1}}
        override = {"a": 42}
        self.assertEqual(_deep_merge(base, override), {"a": 42})

    def test_add_new_keys(self):
        base = {"a": 1}
        override = {"b": 2}
        self.assertEqual(_deep_merge(base, override), {"a": 1, "b": 2})

    def test_empty_override(self):
        base = {"a": 1}
        self.assertEqual(_deep_merge(base, {}), {"a": 1})


class TestLoadSettings(unittest.TestCase):
    def test_missing_file_returns_defaults(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Point to a non-existent file by monkey-patching
            import feishu_common._config_loader as loader
            original = loader.SETTINGS_FILE
            loader.SETTINGS_FILE = Path(tmpdir) / "settings.json"
            try:
                result = load_settings()
                self.assertEqual(result, {"brand": "feishu"})
            finally:
                loader.SETTINGS_FILE = original

    def test_file_loaded_and_merged(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            import feishu_common._config_loader as loader
            original = loader.SETTINGS_FILE
            path = Path(tmpdir) / "settings.json"
            path.write_text(json.dumps({"brand": "lark", "custom": 42}), encoding="utf-8")
            loader.SETTINGS_FILE = path
            try:
                result = load_settings()
                self.assertEqual(result["brand"], "lark")
                self.assertEqual(result["custom"], 42)
            finally:
                loader.SETTINGS_FILE = original


class TestLoadRiskPolicy(unittest.TestCase):
    def test_missing_file_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            import feishu_common._config_loader as loader
            original = loader.RISK_POLICY_FILE
            loader.RISK_POLICY_FILE = Path(tmpdir) / "risk_policy.json"
            try:
                result = load_risk_policy()
                self.assertEqual(result, {})
            finally:
                loader.RISK_POLICY_FILE = original

    def test_file_loaded(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            import feishu_common._config_loader as loader
            original = loader.RISK_POLICY_FILE
            path = Path(tmpdir) / "risk_policy.json"
            payload = {"version": 1, "workspace": {"trusted_folder_tokens": []}}
            path.write_text(json.dumps(payload), encoding="utf-8")
            loader.RISK_POLICY_FILE = path
            try:
                result = load_risk_policy()
                self.assertEqual(result["version"], 1)
            finally:
                loader.RISK_POLICY_FILE = original


class TestLookupContact(unittest.TestCase):
    """Tests for lookup_contact API-only mode."""

    def test_no_client_raises(self):
        from feishu_common._shared import lookup_contact
        with self.assertRaises(RuntimeError):
            lookup_contact(name="test")

    def test_no_args_raises(self):
        from feishu_common._shared import lookup_contact
        with self.assertRaises(RuntimeError):
            lookup_contact(client=object())

    def test_leader_raises(self):
        from feishu_common._shared import lookup_contact
        with self.assertRaises(RuntimeError):
            lookup_contact(leader="test", client=object())


class TestCliRun(unittest.TestCase):
    def test_runtime_error_exits_1(self):
        from feishu_common._shared import cli_run
        with self.assertRaises(SystemExit) as ctx:
            cli_run(lambda: (_ for _ in ()).throw(RuntimeError("bad")))
        self.assertEqual(ctx.exception.code, 1)

    def test_keyboard_interrupt_exits_130(self):
        from feishu_common._shared import cli_run
        with self.assertRaises(SystemExit) as ctx:
            cli_run(lambda: (_ for _ in ()).throw(KeyboardInterrupt()))
        self.assertEqual(ctx.exception.code, 130)

    def test_file_not_found_exits_1(self):
        from feishu_common._shared import cli_run
        with self.assertRaises(SystemExit) as ctx:
            cli_run(lambda: (_ for _ in ()).throw(FileNotFoundError("nope")))
        self.assertEqual(ctx.exception.code, 1)

    def test_success_no_exit(self):
        from feishu_common._shared import cli_run
        # Should not raise
        cli_run(lambda: None)


class TestConfirmActionOrExit(unittest.TestCase):
    def test_yes_skips_confirmation(self):
        import feishu_common._shared as shared
        original_prompt = shared.prompt_for_confirmation
        try:
            shared.prompt_for_confirmation = lambda message: (_ for _ in ()).throw(AssertionError("should not prompt"))
            shared.confirm_action_or_exit("doc_write", "confirm", yes=True)
        finally:
            shared.prompt_for_confirmation = original_prompt

    def test_trusted_create_can_skip_confirmation(self):
        import feishu_common._shared as shared
        original_prompt = shared.prompt_for_confirmation
        try:
            shared.prompt_for_confirmation = lambda message: (_ for _ in ()).throw(AssertionError("should not prompt"))
            shared.confirm_action_or_exit("doc_create", "confirm", is_trusted=True)
        finally:
            shared.prompt_for_confirmation = original_prompt

    def test_reject_exits_zero(self):
        import feishu_common._shared as shared
        original_prompt = shared.prompt_for_confirmation
        original_should = shared.should_confirm_action
        try:
            # Force confirmation prompt regardless of identity/risk_policy state
            shared.should_confirm_action = lambda *a, **kw: True
            shared.prompt_for_confirmation = lambda message: False
            with self.assertRaises(SystemExit) as ctx:
                shared.confirm_action_or_exit("doc_write", "confirm")
            self.assertEqual(ctx.exception.code, 0)
        finally:
            shared.prompt_for_confirmation = original_prompt
            shared.should_confirm_action = original_should


if __name__ == "__main__":
    unittest.main()
