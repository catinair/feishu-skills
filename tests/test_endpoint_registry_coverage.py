#!/usr/bin/env python3
"""Tests that public API methods remain covered by ENDPOINT_REGISTRY."""

import inspect
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from feishu_common._client_base import BaseMixin
from feishu_common._client_calendar import CalendarMixin
from feishu_common._client_contact import ContactMixin
from feishu_common._client_doc import DocMixin
from feishu_common._client_drive import DriveMixin
from feishu_common._client_im import IMMixin
from feishu_common._client_minutes import MinutesMixin
from feishu_common._client_perm import PermMixin
from feishu_common._client_sheets import SheetsMixin
from feishu_common._client_slides import SlidesMixin
from feishu_common._client_task import TaskMixin
from feishu_common._client_wiki import WikiMixin
from feishu_common._endpoint_registry import ENDPOINT_REGISTRY


ALLOWLIST = {
    "lookup_contact",      # local CSV/API convenience wrapper, not a direct endpoint contract
}

MIXINS = [
    BaseMixin,
    CalendarMixin,
    ContactMixin,
    DocMixin,
    DriveMixin,
    IMMixin,
    MinutesMixin,
    PermMixin,
    SheetsMixin,
    SlidesMixin,
    TaskMixin,
    WikiMixin,
]


class TestEndpointRegistryCoverage(unittest.TestCase):
    def test_public_mixin_methods_are_registered(self):
        missing = []
        for mixin in MIXINS:
            for name, value in mixin.__dict__.items():
                if name.startswith("_") or name in ALLOWLIST:
                    continue
                if not inspect.isfunction(value):
                    continue
                if name not in ENDPOINT_REGISTRY:
                    missing.append(f"{mixin.__name__}.{name}")
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
