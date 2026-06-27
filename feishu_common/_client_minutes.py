#!/usr/bin/env python3
"""_client_minutes.py -- 妙记相关 API mixin。"""

class MinutesMixin:
    def minutes_get(self, minute_token, use_user_token=None):
        """获取妙记基本信息（标题、时长、URL 等）"""
        return self._request("GET", f"/open-apis/minutes/v1/minutes/{minute_token}", use_user_token=use_user_token)
    
    def minutes_transcript(self, minute_token, use_user_token=None):
        """导出妙记转写内容（含时间戳、发言人）"""
        return self._request(
            "GET",
            f"/open-apis/minutes/v1/minutes/{minute_token}/transcript",
            use_user_token=use_user_token,
        )
    
    def minutes_statistics(self, minute_token, use_user_token=None):
        """获取妙记访问统计数据（PV、UV 等）"""
        return self._request(
            "GET",
            f"/open-apis/minutes/v1/minutes/{minute_token}/statistics",
            use_user_token=use_user_token,
        )
    
    def minutes_artifacts(self, minute_token, use_user_token=None):
        """获取妙记 AI 产物（总结、章节、待办）"""
        return self._request(
            "GET",
            f"/open-apis/minutes/v1/minutes/{minute_token}/artifacts",
            use_user_token=use_user_token,
        )
    
