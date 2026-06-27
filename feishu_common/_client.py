#!/usr/bin/env python3
"""
_client.py -- 飞书 Skill HTTP 客户端组合入口
从各子模块导入 mixin，组合为 FeishuClient 类。
所有 CLI 脚本继续通过 `from _shared import FeishuClient` 使用，无需修改。
"""

from ._client_core import FeishuClientCore
from ._config_loader import DEFAULT_FOLDER_TOKEN
from ._client_doc import DocMixin
from ._client_drive import DriveMixin
from ._client_sheets import SheetsMixin
from ._client_wiki import WikiMixin
from ._client_base import BaseMixin
from ._client_minutes import MinutesMixin
from ._client_contact import ContactMixin
from ._client_calendar import CalendarMixin
from ._client_im import IMMixin
from ._client_perm import PermMixin
from ._client_slides import SlidesMixin
from ._client_task import TaskMixin


class FeishuClient(
    FeishuClientCore,
    DocMixin,
    DriveMixin,
    SheetsMixin,
    WikiMixin,
    BaseMixin,
    MinutesMixin,
    ContactMixin,
    CalendarMixin,
    IMMixin,
    PermMixin,
    SlidesMixin,
    TaskMixin,
):
    """飞书 HTTP API 客户端（组合所有领域能力）"""
    pass


__all__ = ["FeishuClient", "DEFAULT_FOLDER_TOKEN"]
