#!/usr/bin/env python3
"""_client_perm.py -- 权限相关 API mixin。"""

class PermMixin:
    def perm_list_members(self, token, type, use_user_token=None):
        """列出文档/云空间对象的协作者
    
        type: docx / sheet / bitable / file / folder / mindnote / slides
        """
        return self._request(
            "GET",
            f"/open-apis/drive/v1/permissions/{token}/members",
            query={"type": type},
            use_user_token=use_user_token,
        )
    
    def perm_add_member(self, token, type, member_id, member_type, perm, use_user_token=None):
        """添加协作者
    
        member_type: openid / union_id / user_id / openchat / department_id
        perm: view / edit / full_access
        """
        return self._request(
            "POST",
            f"/open-apis/drive/v1/permissions/{token}/members",
            query={"type": type},
            body={"member_id": member_id, "member_type": member_type, "perm": perm},
            use_user_token=use_user_token,
        )
    
    def perm_remove_member(self, token, type, member_id, use_user_token=None):
        """移除协作者"""
        return self._request(
            "DELETE",
            f"/open-apis/drive/v1/permissions/{token}/members/{member_id}",
            query={"type": type},
            use_user_token=use_user_token,
        )