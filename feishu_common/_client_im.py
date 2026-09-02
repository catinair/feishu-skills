#!/usr/bin/env python3
"""_client_im.py -- IM 相关 API mixin。"""

import json
import mimetypes
import os
from pathlib import Path


class IMMixin:
    def im_messages_list(
        self,
        container_id,
        container_id_type="chat",
        page_size=50,
        page_token=None,
        start_time=None,
        end_time=None,
    ):
        """获取群聊/会话消息列表（单页）"""
        query = {
            "container_id_type": container_id_type,
            "container_id": container_id,
            "page_size": page_size,
        }
        if page_token:
            query["page_token"] = page_token
        if start_time is not None:
            query["start_time"] = start_time
        if end_time is not None:
            query["end_time"] = end_time
        return self._request("GET", "/open-apis/im/v1/messages", query=query)

    def im_send_file(self, receive_id, receive_id_type, file_token, uuid=None):
        """发送文件消息"""
        body = {
            "receive_id": receive_id,
            "msg_type": "file",
            "content": json.dumps({"file_key": file_token}),
        }
        if uuid:
            body["uuid"] = uuid
        return self._request(
            "POST",
            "/open-apis/im/v1/messages",
            body=body,
            query={"receive_id_type": receive_id_type},
        )

    def im_send_image(self, receive_id, receive_id_type, image_key, uuid=None):
        """发送图片消息"""
        body = {
            "receive_id": receive_id,
            "msg_type": "image",
            "content": json.dumps({"image_key": image_key}),
        }
        if uuid:
            body["uuid"] = uuid
        return self._request(
            "POST",
            "/open-apis/im/v1/messages",
            body=body,
            query={"receive_id_type": receive_id_type},
        )

    def im_reply_message(self, message_id, msg_type, content, uuid=None):
        """回复指定消息"""
        body = {
            "content": json.dumps(content),
            "msg_type": msg_type,
        }
        if uuid:
            body["uuid"] = uuid
        data = self._request(
            "POST", f"/open-apis/im/v1/messages/{message_id}/reply", body=body
        )
        return data.get("message", data)

    def im_create_chat(self, name, description=""):
        """创建群聊"""
        body = {"name": name}
        if description:
            body["description"] = description
        data = self._request("POST", "/open-apis/im/v1/chats", body=body)
        return data

    def im_send_text(self, receive_id, receive_id_type, text, use_user_token=None):
        """发送文本消息"""
        body = {
            "receive_id": receive_id,
            "msg_type": "text",
            "content": json.dumps({"text": text}),
        }
        data = self._request(
            "POST",
            "/open-apis/im/v1/messages",
            body=body,
            query={"receive_id_type": receive_id_type},
            use_user_token=use_user_token,
        )
        return data

    def im_send_post(
        self, receive_id, receive_id_type, title, content_lines, use_user_token=None
    ):
        """发送富文本消息（post 类型）

        content_lines: 二维数组，每行是一个 tag 列表
        例如：[[{"tag": "text", "text": "Hello"}], [{"tag": "a", "text": "Link", "href": "https://..."}]]
        """
        body = {
            "receive_id": receive_id,
            "msg_type": "post",
            "content": json.dumps(
                {
                    "zh_cn": {
                        "title": title,
                        "content": content_lines,
                    }
                }
            ),
        }
        data = self._request(
            "POST",
            "/open-apis/im/v1/messages",
            body=body,
            query={"receive_id_type": receive_id_type},
            use_user_token=use_user_token,
        )
        return data

    def upload_image(self, image_path):
        """上传图片到飞书，返回 image_key"""
        path = Path(image_path)
        if not path.exists():
            raise RuntimeError(f"Image not found: {image_path}")
        image_data = path.read_bytes()
        filename = path.name
        content_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        boundary = "----LarkDocBoundary" + os.urandom(8).hex()
        parts = [
            f"--{boundary}".encode(),
            b'Content-Disposition: form-data; name="image_type"',
            b"",
            b"message",
            f"--{boundary}".encode(),
            f'Content-Disposition: form-data; name="image"; filename="{filename}"'.encode(),
            f"Content-Type: {content_type}".encode(),
            b"",
            image_data,
            f"--{boundary}--".encode(),
        ]
        body = b"\r\n".join(parts)
        headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
        data = self._request(
            "POST", "/open-apis/im/v1/images", body=body, headers=headers
        )
        return data.get("image_key", "")

    def im_chat_info(self, chat_id):
        """获取群聊详情"""
        return self._request("GET", f"/open-apis/im/v1/chats/{chat_id}")

    def im_chat_members(
        self,
        chat_id,
        member_id_type="open_id",
        page_size=100,
        page_token=None,
        max_results=None,
    ):
        """获取群聊成员列表（自动分页，也支持 page_token 单页模式）"""
        extra_query = {"member_id_type": member_id_type}
        if page_token:
            query = dict(extra_query)
            query["page_size"] = page_size
            query["page_token"] = page_token
            return self._request(
                "GET", f"/open-apis/im/v1/chats/{chat_id}/members", query=query
            )

        items = self._paginate(
            "GET",
            f"/open-apis/im/v1/chats/{chat_id}/members",
            page_size=page_size,
            max_results=max_results,
            extra_query=extra_query,
        )
        return {"total": len(items), "items": items, "has_more": False}

    def im_chat_add_members(self, chat_id, member_ids, member_id_type="user_id"):
        """向群聊添加成员

        member_ids: 用户 ID 列表
        member_id_type: user_id / open_id / union_id
        """
        return self._request(
            "POST",
            f"/open-apis/im/v1/chats/{chat_id}/members",
            query={"member_id_type": member_id_type},
            body={
                "id_list": member_ids if isinstance(member_ids, list) else [member_ids]
            },
        )

    def im_chat_update(self, chat_id, **kwargs):
        """修改群聊信息（转让群主、修改名称/描述等）"""
        return self._request("PUT", f"/open-apis/im/v1/chats/{chat_id}", body=kwargs)

    def im_search_messages(
        self,
        query=None,
        chat_ids=None,
        senders=None,
        start_time=None,
        end_time=None,
        page_size=20,
        page_token=None,
        max_results=None,
    ):
        """搜索消息（支持自动分页，也可通过 page_token 手动分页）

        Args:
            query: 搜索关键词
            chat_ids: 限定会话 ID 列表
            senders: 发送者 open_id 列表
            start_time: 开始时间（ISO 8601 格式）
            end_time: 结束时间（ISO 8601 格式）
            page_size: 每页条数（1-50，默认 20）
            page_token: 分页 token。为 None 时自动分页获取全部结果；传入具体值时仅返回单页。
            max_results: 最大返回条数，None 表示不限制。
        """
        # 手动分页模式：直接返回单页
        if page_token is not None:
            body = {}
            if query is not None:
                body["query"] = query
            if chat_ids is not None:
                body["chat_ids"] = chat_ids
            if senders is not None:
                body["senders"] = senders
            if start_time is not None:
                body["start_time"] = start_time
            if end_time is not None:
                body["end_time"] = end_time
            query_params = {"page_size": page_size, "page_token": page_token}
            return self._request(
                "POST",
                "/open-apis/im/v1/messages/search",
                query=query_params,
                body=body,
            )

        # 自动分页模式
        body = {}
        if query is not None:
            body["query"] = query
        if chat_ids is not None:
            body["chat_ids"] = chat_ids
        if senders is not None:
            body["senders"] = senders
        if start_time is not None:
            body["start_time"] = start_time
        if end_time is not None:
            body["end_time"] = end_time
        messages = self._paginate(
            "POST",
            "/open-apis/im/v1/messages/search",
            page_size=page_size,
            max_results=max_results,
            extra_body=body,
        )
        return {"total": len(messages), "items": messages, "has_more": False}

    def im_list_chats(
        self,
        page_size=50,
        max_results=None,
        user_id_type=None,
        sort_type=None,
        page_token=None,
        use_user_token=None,
    ):
        """列出当前身份有权限的群聊（自动分页，也支持 page_token 单页模式）

        use_user_token: True=user 身份, False=tenant 身份, None=按 registry 决定
        """
        extra_query = {}
        if user_id_type:
            extra_query["user_id_type"] = user_id_type
        if sort_type:
            extra_query["sort_type"] = sort_type
        if page_token:
            query = dict(extra_query)
            query["page_size"] = page_size
            query["page_token"] = page_token
            return self._request(
                "GET",
                "/open-apis/im/v1/chats",
                query=query,
                use_user_token=use_user_token,
            )
        return self._paginate(
            "GET",
            "/open-apis/im/v1/chats",
            page_size=page_size,
            max_results=max_results,
            extra_query=extra_query or None,
            use_user_token=use_user_token,
        )

    def im_search_chats(
        self,
        query,
        page_size=50,
        max_results=None,
        page_token=None,
        search_types=None,
        member_ids=None,
        is_manager=None,
        disable_search_by_user=None,
        chat_modes=None,
        sorter=None,
        user_id_type=None,
        use_user_token=None,
    ):
        """按关键字搜索群组（含未加入的公开群）

        调用 POST /open-apis/im/v2/chats/search

        Args:
            query: 搜索关键字（0-50 字符）
            page_size: 每页数量
            max_results: 最大返回条数
            page_token: 分页 token；提供后仅返回单页
            search_types: 群组类型过滤，如 ["private", "public_not_joined"]
            member_ids: 群成员 ID 列表
            is_manager: 是否自己创建/管理的群
            disable_search_by_user: 关闭以人搜群
            chat_modes: 群模式过滤，如 ["default", "thread"]
            sorter: 排序，如 "create_time_desc"
            user_id_type: 用户 ID 类型
            use_user_token: True=user 身份, False=tenant 身份
        """
        body = {"query": query}
        if (
            search_types
            or member_ids
            or is_manager is not None
            or disable_search_by_user is not None
            or chat_modes
        ):
            filter_body = {}
            if search_types:
                filter_body["search_types"] = search_types
            if member_ids:
                filter_body["member_ids"] = member_ids
            if is_manager is not None:
                filter_body["is_manager"] = is_manager
            if disable_search_by_user is not None:
                filter_body["disable_search_by_user"] = disable_search_by_user
            if chat_modes:
                filter_body["chat_modes"] = chat_modes
            body["filter"] = filter_body
        if sorter:
            body["sorter"] = sorter

        extra_query = {}
        if user_id_type:
            extra_query["user_id_type"] = user_id_type

        if page_token:
            q = dict(extra_query)
            q["page_size"] = page_size
            q["page_token"] = page_token
            return self._request(
                "POST",
                "/open-apis/im/v2/chats/search",
                body=body,
                query=q,
                use_user_token=use_user_token,
            )
        return self._paginate(
            "POST",
            "/open-apis/im/v2/chats/search",
            items_key="items",
            page_size=page_size,
            max_results=max_results,
            extra_query=extra_query or None,
            extra_body=body,
            use_user_token=use_user_token,
        )
