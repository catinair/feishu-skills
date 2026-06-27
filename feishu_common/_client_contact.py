#!/usr/bin/env python3
"""_client_contact.py -- 通讯录相关 API mixin。"""

class ContactMixin:
    def contact_search_users(self, query_text, limit=20, user_id_type="open_id"):
        """通过 Search API 搜索用户（结果按相关性排序）

        使用 /open-apis/search/v1/user，需要 user_access_token + contact:user:search scope。
        """
        return self._paginate(
            "GET", "/open-apis/search/v1/user",
            items_key="users", max_results=limit,
            extra_query={"user_id_type": user_id_type, "query": query_text},
        )

    def contact_list_departments(self, page_size=50, parent_department_id=None, fetch_child=False, department_id_type="open_department_id", max_results=None):
        """列出部门列表

        Args:
            page_size: 分页大小
            parent_department_id: 父部门 ID（不传则获取所有有权限的部门）
            fetch_child: 是否递归获取子部门
            department_id_type: department_id / open_department_id
            max_results: 最大返回条数，None 表示不限制
        """
        extra_query = {
            "fetch_child": "true" if fetch_child else "false",
            "department_id_type": department_id_type,
        }
        if parent_department_id is not None:
            extra_query["parent_department_id"] = parent_department_id
        return self._paginate(
            "GET", "/open-apis/contact/v3/departments",
            page_size=page_size, max_results=max_results,
            extra_query=extra_query,
        )

    def contact_get_department(self, department_id, department_id_type="open_department_id"):
        """获取单个部门详情"""
        return self._request(
            "GET", f"/open-apis/contact/v3/departments/{department_id}",
            query={"department_id_type": department_id_type}
        )

    def contact_list_department_members(self, department_id, page_size=50, department_id_type="open_department_id", user_id_type="open_id", fetch_child=False, max_results=None):
        """查询部门成员列表（需要 user_access_token）

        注意：此 API 返回完整字段（姓名、邮箱等）需要 user_access_token。
        请先在凭证文件中配置 userAccessToken，或运行 auth_get_user_token.py 授权。
        """
        extra_query = {
            "department_id": department_id,
            "department_id_type": department_id_type,
            "user_id_type": user_id_type,
        }
        if fetch_child:
            extra_query["fetch_child"] = "true"
        return self._paginate(
            "GET", "/open-apis/contact/v3/users",
            page_size=page_size, max_results=max_results,
            extra_query=extra_query,
        )

    def contact_find_by_department(self, department_id, page_size=50,
                                   department_id_type="department_id",
                                   user_id_type="open_id",
                                   use_user_token=None, max_results=None):
        """通过 find_by_department 接口查询部门直属用户

        相比 contact_list_department_members，此接口用 tenant_access_token
        也能返回姓名等基础字段（需应用有 contact:user.base:readonly 权限）。
        默认由 registry 决定身份；调用方可显式传入 use_user_token 做降级重试。
        """
        extra_query = {
            "department_id": department_id,
            "department_id_type": department_id_type,
            "user_id_type": user_id_type,
        }
        return self._paginate(
            "GET", "/open-apis/contact/v3/users/find_by_department",
            page_size=page_size, max_results=max_results,
            extra_query=extra_query, use_user_token=use_user_token,
        )

    def contact_get_user(self, user_id, user_id_type="user_id"):
        """获取用户详情（需要 user_access_token 才能返回姓名、邮箱等完整字段）

        Args:
            user_id: 用户 ID（根据 user_id_type 类型）
            user_id_type: user_id / open_id / union_id
        """
        return self._request(
            "GET", f"/open-apis/contact/v3/users/{user_id}",
            query={"user_id_type": user_id_type}
        )

    def contact_get_self(self):
        """获取当前登录用户信息（通过 user_access_token）"""
        return self._request("GET", "/open-apis/authen/v1/user_info")

    def contact_colleagues(self, user_id_type="open_id"):
        """查询当前用户同部门的所有人员

        流程：获取当前用户信息 → 获取完整 profile（含部门）→ 查询部门成员

        若用户部门不可见（通讯录权限范围不足），返回 {"me": user, "members": [],
        "warning": "..."} 而非抛异常，方便调用方做 fallback。
        """
        me = self.contact_get_self()
        me_open_id = me.get("open_id")
        if not me_open_id:
            raise RuntimeError("无法获取当前用户 open_id")
        me_full = self.contact_get_user(me_open_id, user_id_type="open_id")
        user = me_full.get("user", me_full)
        dept_path = user.get("department_path", [])
        if not dept_path:
            return {
                "me": user,
                "department_id": None,
                "department_name": "",
                "members": [],
                "warning": "当前用户未关联部门或部门不可见。"
                            "请在飞书管理后台 → 通讯录权限范围中扩大应用的可见范围。",
            }
        dept_id = dept_path[0].get("department_id")
        dept_name = dept_path[0].get("department_name", {}).get("name", "")
        members = self.contact_find_by_department(
            dept_id, department_id_type="open_department_id", user_id_type=user_id_type,
        )
        return {"department_id": dept_id, "department_name": dept_name, "me": user, "members": members}

    def lookup_contact(self, name=None, openid=None, user_id=None, leader=None):
        """查询部门人员信息（纯 API）。"""
        from feishu_common._shared import lookup_contact as _lookup
        return _lookup(name=name, openid=openid, user_id=user_id, leader=leader, client=self)
