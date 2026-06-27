#!/usr/bin/env python3
"""
_client_task.py -- 飞书任务 API v2 mixin
"""

class TaskMixin:

    def task_create(self, summary, description=None, due=None, members=None,
                    extra=None, origin=None, mode=None, reminders=None,
                    tasklists=None, client_token=None, user_id_type="open_id"):
        """创建飞书任务

        Args:
            summary: 任务标题（必填，最长 3000 字符）
            description: 任务描述（最长 3000 字符）
            due: 截止时间 dict {"timestamp": "ms", "is_all_day": bool}
            members: 成员列表 [{"id": "ou_xxx", "type": "user", "role": "assignee"}]
            extra: 自定义附带数据（最长 65536 字符）
            origin: 来源信息 dict
            mode: 完成模式 1=会签 2=或签
            reminders: 提醒配置列表
            tasklists: 清单列表
            client_token: 幂等 token（10-100 字符）
            user_id_type: 用户 ID 类型

        Returns:
            dict: 创建的任务对象
        """
        body = {"summary": summary}
        if description is not None:
            body["description"] = description
        if due is not None:
            body["due"] = due
        if members is not None:
            body["members"] = members
        if extra is not None:
            body["extra"] = extra
        if origin is not None:
            body["origin"] = origin
        if mode is not None:
            body["mode"] = mode
        if reminders is not None:
            body["reminders"] = reminders
        if tasklists is not None:
            body["tasklists"] = tasklists
        if client_token is not None:
            body["client_token"] = client_token
        query = {"user_id_type": user_id_type}
        data = self._request("POST", "/open-apis/task/v2/tasks", body=body, query=query)
        return data.get("task", data)

    def task_get(self, task_guid, user_id_type="open_id"):
        """获取任务详情

        Args:
            task_guid: 任务 GUID
            user_id_type: 用户 ID 类型

        Returns:
            dict: 任务对象（含 guid, summary, status, members, comments 等）
        """
        query = {"user_id_type": user_id_type}
        data = self._request("GET", f"/open-apis/task/v2/tasks/{task_guid}", query=query)
        return data.get("task", data)

    def task_list(self, completed=None, page_size=50, max_results=None,
                  user_id_type="open_id"):
        """列取当前用户负责的任务（仅支持 user_access_token）

        Args:
            completed: 过滤条件 True=已完成 False=未完成 None=不过滤
            page_size: 每页数量（1-100）
            max_results: 最大返回条数
            user_id_type: 用户 ID 类型

        Returns:
            dict: {"total": int, "items": [...], "has_more": bool}
        """
        extra_query = {"type": "my_tasks", "user_id_type": user_id_type}
        if completed is not None:
            extra_query["completed"] = "true" if completed else "false"
        items = self._paginate(
            "GET", "/open-apis/task/v2/tasks",
            page_size=page_size, max_results=max_results,
            extra_query=extra_query,
        )
        return {"total": len(items), "items": items, "has_more": False}

    def task_patch(self, task_guid, update_fields, task_data=None,
                   user_id_type="open_id"):
        """更新任务（标题、描述、截止时间、完成状态等）

        Args:
            task_guid: 任务 GUID
            update_fields: 要修改的字段名列表，如 ["summary", "completed_at"]
            task_data: 要修改的字段新值 dict
            user_id_type: 用户 ID 类型

        Returns:
            dict: 更新后的任务对象

        完成任务: update_fields=["completed_at"], task_data={"completed_at": "<ms>"}
        恢复未完成: update_fields=["completed_at"], task_data={"completed_at": "0"}
        """
        body = {"update_fields": update_fields}
        if task_data is not None:
            body["task"] = task_data
        query = {"user_id_type": user_id_type}
        data = self._request("PATCH", f"/open-apis/task/v2/tasks/{task_guid}",
                             body=body, query=query)
        return data.get("task", data)

    def task_comment_create(self, resource_id, content,
                            reply_to_comment_id=None,
                            resource_type="task",
                            user_id_type="open_id"):
        """为任务创建评论

        Args:
            resource_id: 任务 GUID
            content: 评论内容（最长 3000 字符）
            reply_to_comment_id: 回复的评论 ID（不填=顶层评论）
            resource_type: 资源类型，默认 "task"
            user_id_type: 用户 ID 类型

        Returns:
            dict: 创建的评论对象
        """
        body = {
            "content": content,
            "resource_type": resource_type,
            "resource_id": resource_id,
        }
        if reply_to_comment_id is not None:
            body["reply_to_comment_id"] = reply_to_comment_id
        query = {"user_id_type": user_id_type}
        data = self._request("POST", "/open-apis/task/v2/comments",
                             body=body, query=query)
        return data.get("comment", data)

    def task_comment_list(self, resource_id, resource_type="task",
                          direction="asc", page_size=50, max_results=None,
                          user_id_type="open_id"):
        """获取任务的评论列表

        Args:
            resource_id: 任务 GUID
            resource_type: 资源类型，默认 "task"
            direction: 排序 "asc"=从旧到新 "desc"=从新到旧
            page_size: 每页数量（1-100）
            max_results: 最大返回条数
            user_id_type: 用户 ID 类型

        Returns:
            dict: {"total": int, "items": [...], "has_more": bool}
        """
        extra_query = {
            "resource_type": resource_type,
            "resource_id": resource_id,
            "direction": direction,
            "user_id_type": user_id_type,
        }
        items = self._paginate(
            "GET", "/open-apis/task/v2/comments",
            page_size=page_size, max_results=max_results,
            extra_query=extra_query,
        )
        return {"total": len(items), "items": items, "has_more": False}
