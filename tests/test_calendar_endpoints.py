#!/usr/bin/env python3
"""Tests for calendar update and calendar list endpoints."""

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from feishu_common import FeishuClient
import feishu_common._config_loader as loader


def _load_script(name):
    """Load a feishu-*/<name>.py script as a module."""
    skill_root = Path(__file__).resolve().parent.parent
    domain = name.split("_")[0]
    path = skill_root / f"feishu-{domain}" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


calendar_update_event = _load_script("calendar_update_event")
calendar_list_calendars = _load_script("calendar_list_calendars")


class TestCalendarEndpoints(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        creds_path = Path(self._tmpdir) / "credentials.json"
        creds_path.write_text(json.dumps({"appId": "cli_xxx", "appSecret": "yyy"}), encoding="utf-8")
        self.client = FeishuClient(str(creds_path))

        self._orig_settings = loader.SETTINGS_FILE
        loader.SETTINGS_FILE = Path(self._tmpdir) / "settings.json"
        loader.SETTINGS_FILE.write_text(json.dumps({"default_identity": "tenant"}), encoding="utf-8")

    def tearDown(self):
        loader.SETTINGS_FILE = self._orig_settings

    def test_update_event_calls_patch_with_body(self):
        with patch.object(self.client, "_request", return_value={"event": {"event_id": "e1"}}) as mock_req:
            self.client.calendar_update_event(
                event_id="e1",
                calendar_id="primary",
                summary="new title",
                description="new desc",
                start_time="2026-04-25 14:00",
                end_time="2026-04-25 15:00",
                location="Room A",
            )
        mock_req.assert_called_once()
        method, path = mock_req.call_args[0][:2]
        self.assertEqual(method, "PATCH")
        self.assertEqual(path, "/open-apis/calendar/v4/calendars/primary/events/e1")
        body = mock_req.call_args[1]["body"]
        self.assertEqual(body["summary"], "new title")
        self.assertEqual(body["description"], "new desc")
        self.assertEqual(body["location"], {"name": "Room A"})
        self.assertIn("timestamp", body["start_time"])
        self.assertIn("timestamp", body["end_time"])

    def test_update_event_omits_unset_fields(self):
        with patch.object(self.client, "_request", return_value={"event": {}}) as mock_req:
            self.client.calendar_update_event(event_id="e1", summary="only title")
        body = mock_req.call_args[1]["body"]
        self.assertEqual(body, {"summary": "only title"})

    def test_list_calendars_calls_get(self):
        with patch.object(self.client, "_request", return_value={"calendar_list": []}) as mock_req:
            self.client.calendar_list_calendars()
        mock_req.assert_called_once()
        method, path = mock_req.call_args[0][:2]
        self.assertEqual(method, "GET")
        self.assertEqual(path, "/open-apis/calendar/v4/calendars")
        self.assertNotIn("query", mock_req.call_args[1])


class TestCalendarUpdateEventScript(unittest.TestCase):
    def setUp(self):
        self._original_main = calendar_update_event.main

    def tearDown(self):
        calendar_update_event.main = self._original_main

    def _run_main(self, args, patched_create_client):
        old_argv = sys.argv
        sys.argv = ["calendar_update_event.py"] + args
        try:
            with patch.object(calendar_update_event, "create_client", return_value=patched_create_client):
                return calendar_update_event.main()
        finally:
            sys.argv = old_argv

    def test_update_event_script_with_yes(self):
        mock_client = MagicMock()
        mock_client.calendar_update_event.return_value = {"event": {"event_id": "e1"}}
        self._run_main(["e1", "--summary", "Updated", "--yes"], mock_client)
        mock_client.calendar_update_event.assert_called_once()
        kwargs = mock_client.calendar_update_event.call_args[1]
        self.assertEqual(kwargs["event_id"], "e1")
        self.assertEqual(kwargs["summary"], "Updated")


class TestCalendarListCalendarsScript(unittest.TestCase):
    def setUp(self):
        self._original_main = calendar_list_calendars.main

    def tearDown(self):
        calendar_list_calendars.main = self._original_main

    def _run_main(self, args, patched_create_client):
        old_argv = sys.argv
        sys.argv = ["calendar_list_calendars.py"] + args
        try:
            with patch.object(calendar_list_calendars, "create_client", return_value=patched_create_client):
                return calendar_list_calendars.main()
        finally:
            sys.argv = old_argv

    def test_list_calendars_script(self):
        mock_client = MagicMock()
        mock_client.calendar_list_calendars.return_value = {
            "calendar_list": [
                {"calendar_id": "primary", "summary": "主日历"},
                {"calendar_id": "cal2", "summary": "共享日历"},
            ],
        }
        self._run_main(["--limit", "1"], mock_client)
        mock_client.calendar_list_calendars.assert_called_once_with()
        # 校验 --limit 生效
        # 输出只保留第一条


if __name__ == "__main__":
    unittest.main()
