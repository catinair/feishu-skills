#!/usr/bin/env python3
"""_client_calendar.py -- 日程相关 API mixin。"""

import re


class CalendarMixin:
    def calendar_list_events(
        self,
        calendar_id="primary",
        page_size=50,
        page_token=None,
        start_time=None,
        end_time=None,
        anchor_time=None,
        sync_token=None,
        show_deleted=None,
    ):
        """查询日程列表

        Args:
            calendar_id: 日历 ID，默认 primary（主日历）
            page_size: 分页大小（最小 50）
            page_token: 分页 token
            start_time: 开始时间（秒级时间戳或 ISO 字符串）
            end_time: 结束时间（秒级时间戳或 ISO 字符串）
            anchor_time: 锚点时间（秒级时间戳或 ISO 字符串）
            sync_token: 增量同步 token
            show_deleted: 是否返回已删除日程
        """
        query = {"page_size": page_size}
        if page_token:
            query["page_token"] = page_token
        if start_time is not None:
            query["start_time"] = self._to_query_timestamp(start_time)
        if end_time is not None:
            query["end_time"] = self._to_query_timestamp(end_time)
        if anchor_time is not None:
            query["anchor_time"] = self._to_query_timestamp(anchor_time)
        if sync_token is not None:
            query["sync_token"] = sync_token
        if show_deleted is not None:
            query["show_deleted"] = "true" if show_deleted else "false"
        return self._request(
            "GET", f"/open-apis/calendar/v4/calendars/{calendar_id}/events", query=query
        )

    def calendar_get_event(self, event_id, calendar_id="primary"):
        """获取单个日程详情"""
        return self._request(
            "GET", f"/open-apis/calendar/v4/calendars/{calendar_id}/events/{event_id}"
        )

    def calendar_create_event(
        self,
        calendar_id="primary",
        summary=None,
        description=None,
        start_time=None,
        end_time=None,
        location=None,
        attendees=None,
        use_user_token=None,
        **kwargs,
    ):
        """创建日程

        Args:
            calendar_id: 日历 ID
            summary: 日程标题
            description: 日程描述
            start_time: 开始时间戳（秒）或 ISO 格式字符串
            end_time: 结束时间戳（秒）或 ISO 格式字符串
            location: 地点名称或 dict（含 name/address）
            attendees: 参与者列表，每项为 dict（含 id/type）
            use_user_token: 是否强制使用 user_access_token，None 表示由 registry 决定
            **kwargs: 其他字段透传
        """
        body = {}
        if summary:
            body["summary"] = summary
        if description:
            body["description"] = description
        if start_time is not None:
            body["start_time"] = self._build_time_field(start_time)
        if end_time is not None:
            body["end_time"] = self._build_time_field(end_time)
        if location:
            if isinstance(location, str):
                body["location"] = {"name": location}
            else:
                body["location"] = location
        if attendees:
            body["attendees"] = (
                attendees if isinstance(attendees, list) else [attendees]
            )
        body.update(kwargs)
        return self._request(
            "POST",
            f"/open-apis/calendar/v4/calendars/{calendar_id}/events",
            body=body,
            use_user_token=use_user_token,
        )

    def calendar_delete_event(self, event_id, calendar_id="primary"):
        """删除日程"""
        return self._request(
            "DELETE",
            f"/open-apis/calendar/v4/calendars/{calendar_id}/events/{event_id}",
        )

    def calendar_freebusy(self, user_id, time_min, time_max, user_id_type="open_id"):
        """查询用户忙闲状态

        Args:
            user_id: 用户 ID
            time_min: 开始时间（ISO 格式，如 2026-04-24T00:00:00+08:00）
            time_max: 结束时间（ISO 格式）
            user_id_type: open_id（默认，calendar API 仅支持 open_id）
        """
        body = {
            "user_id": user_id,
            "time_min": time_min,
            "time_max": time_max,
        }
        return self._request("POST", "/open-apis/calendar/v4/freebusy/list", body=body)

    def calendar_update_event(
        self,
        event_id,
        calendar_id="primary",
        summary=None,
        description=None,
        start_time=None,
        end_time=None,
        location=None,
        attendees=None,
        **kwargs,
    ):
        """更新日程信息

        Args:
            event_id: 日程 ID
            calendar_id: 日历 ID，默认 primary
            summary: 日程标题
            description: 日程描述
            start_time: 开始时间戳（秒）或 ISO 格式字符串
            end_time: 结束时间戳（秒）或 ISO 格式字符串
            location: 地点名称或 dict
            attendees: 参与者列表
            **kwargs: 其他字段透传
        """
        body = {}
        if summary is not None:
            body["summary"] = summary
        if description is not None:
            body["description"] = description
        if start_time is not None:
            body["start_time"] = self._build_time_field(start_time)
        if end_time is not None:
            body["end_time"] = self._build_time_field(end_time)
        if location is not None:
            if isinstance(location, str):
                body["location"] = {"name": location}
            else:
                body["location"] = location
        if attendees is not None:
            body["attendees"] = (
                attendees if isinstance(attendees, list) else [attendees]
            )
        body.update(kwargs)
        return self._request(
            "PATCH",
            f"/open-apis/calendar/v4/calendars/{calendar_id}/events/{event_id}",
            body=body,
        )

    def calendar_list_calendars(self):
        """查询日历列表（如主日历、共享日历）

        飞书该接口不支持分页参数，直接返回全部日历。
        """
        return self._request("GET", "/open-apis/calendar/v4/calendars")

    def calendar_subscribe(self, calendar_id):
        """订阅日历（或取消订阅，同一端点 toggle）。

        订阅后默认为「游客」权限，只能查看忙闲。
        需要对方升级为「订阅者」才能查看日程详情。

        Args:
            calendar_id: 日历 ID，如 feishu.cn_xxx@group.calendar.feishu.cn

        Returns:
            API 响应 dict，code=0 表示成功
        """
        return self._request(
            "POST",
            "/open-apis/calendar/v4/calendars/subscription",
            body={"calendar_id": calendar_id},
        )

    @staticmethod
    def _to_query_timestamp(value):
        """将秒级时间戳或 ISO 字符串转换为查询参数所需的秒级时间戳字符串。"""
        import datetime

        if isinstance(value, int) or isinstance(value, float):
            return str(int(value))
        if isinstance(value, str) and value.isdigit():
            return str(int(value))
        if isinstance(value, str):
            ts = value
            if ts.endswith("Z"):
                ts = ts[:-1] + "+00:00"
            try:
                return str(int(datetime.datetime.fromisoformat(ts).timestamp()))
            except ValueError:
                return value
        return str(value)

    @staticmethod
    def _build_time_field(value):
        """将时间值构建为日历 API 所需格式

        飞书 Calendar API 仅支持 timestamp 或 date 格式，不支持 date_time。
        """
        import datetime

        if isinstance(value, int) or (isinstance(value, str) and value.isdigit()):
            return {"timestamp": str(int(value))}
        if isinstance(value, str) and re.match(r"^\d{4}-\d{2}-\d{2}$", value):
            return {"date": value}
        # ISO 格式含时间 → 解析为 datetime 再转 timestamp
        if isinstance(value, str) and (
            "T" in value or value.endswith("Z") or "+" in value
        ):
            # 处理 +08:00 时区
            ts = value
            if ts.endswith("Z"):
                ts = ts[:-1] + "+00:00"
            try:
                dt = datetime.datetime.fromisoformat(ts)
                return {"timestamp": str(int(dt.timestamp()))}
            except ValueError:
                pass
        return {"timestamp": str(value)}
