#!/usr/bin/env python3
"""_client_wiki.py -- 知识库相关 API mixin。"""

class WikiMixin:
    def wiki_get_node(self, wiki_token):
        """获取 wiki 节点信息（无需 space_id）

        返回 node 的 obj_type、obj_token、title 等关键信息
        """
        return self._request("GET", "/open-apis/wiki/v2/spaces/get_node", query={"token": wiki_token})

    def wiki_list_spaces(self, page_size=50, max_results=None):
        """列出知识空间"""
        return self._paginate("GET", "/open-apis/wiki/v2/spaces", page_size=page_size, max_results=max_results)

    def wiki_create_node(self, space_id, obj_type, title, node_type="origin", parent_node_token=None):
        """在 Wiki 知识空间下创建节点

        Args:
            space_id: 知识空间 ID
            obj_type: 节点类型，如 docx / sheet / bitable / mindnote / slides
            title: 节点标题
            node_type: 节点类型，默认 origin
            parent_node_token: 父节点 token（不传则创建在根目录）
        """
        body = {
            "obj_type": obj_type,
            "node_type": node_type,
            "title": title,
        }
        if parent_node_token:
            body["parent_node_token"] = parent_node_token
        return self._request(
            "POST", f"/open-apis/wiki/v2/spaces/{space_id}/nodes", body=body
        )

    def wiki_list_nodes(self, space_id, parent_node_token=None, page_size=50, max_results=None):
        """列出知识空间下的节点

        Args:
            space_id: 知识空间 ID
            parent_node_token: 父节点 token（不传则列出根节点）
            page_size: 每页数量
            max_results: 最大返回数量
        """
        extra_query = {}
        if parent_node_token:
            extra_query["parent_node_token"] = parent_node_token
        return self._paginate(
            "GET", f"/open-apis/wiki/v2/spaces/{space_id}/nodes",
            page_size=page_size, max_results=max_results,
            extra_query=extra_query or None,
        )
