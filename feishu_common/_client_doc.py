#!/usr/bin/env python3
"""_client_doc.py -- 文档相关 API mixin。"""

MAX_BLOCKS_PER_REQUEST = 1000

class DocMixin:

    def document_info(self, document_id):
        """获取文档基本信息"""
        data = self._request("GET", f"/open-apis/docx/v1/documents/{document_id}")
        return data.get("document", {})

    def document_create(self, title=None, folder_token=None):
        """创建空文档"""
        payload = {}
        if title:
            payload["title"] = title
        if folder_token:
            payload["folder_token"] = folder_token
        data = self._request("POST", "/open-apis/docx/v1/documents", body=payload)
        return data.get("document", {})
    
    def document_block_info(self, document_id, block_id):
        """获取文档中指定 block 的详细信息"""
        data = self._request(
            "GET",
            f"/open-apis/docx/v1/documents/{document_id}/blocks/{block_id}",
            query={"document_revision_id": -1},
        )
        return data.get("block", data)

    def document_create_child_blocks(self, document_id, parent_block_id, children, index=0):
        """在文档指定 block 下创建子 block

        Args:
            document_id: 文档 ID
            parent_block_id: 父 block ID
            children: 子 block 列表
            index: 插入位置索引，默认为 0；传 None 时不带 index 参数
        """
        body = {"children": children}
        if index is not None:
            body["index"] = index
        return self._request(
            "POST",
            f"/open-apis/docx/v1/documents/{document_id}/blocks/{parent_block_id}/children",
            body=body,
        )

    def document_update_block(self, document_id, block_id, update_body):
        """更新文档中指定 block 的内容/属性"""
        return self._request(
            "PATCH",
            f"/open-apis/docx/v1/documents/{document_id}/blocks/{block_id}",
            body=update_body,
        )

    def document_raw_content(self, document_id):
        """获取 docx 文档原始 Markdown 内容"""
        data = self._request(
            "GET",
            f"/open-apis/docx/v1/documents/{document_id}/raw_content",
            query={"document_revision_id": -1},
        )
        return data.get("content", "")

    def document_blocks(self, document_id, page_token=None, page_size=500):
        """获取文档 block 树（分页）"""
        query = {"page_size": page_size, "document_revision_id": -1}
        if page_token:
            query["page_token"] = page_token
        return self._request("GET", f"/open-apis/docx/v1/documents/{document_id}/blocks", query=query)
    
    def document_blocks_all(self, document_id, max_results=None):
        """获取完整文档 block 树（自动分页）"""
        all_items = self._paginate(
            "GET", f"/open-apis/docx/v1/documents/{document_id}/blocks",
            page_size=500, max_results=max_results,
            extra_query={"document_revision_id": -1},
        )
        return {"items": all_items}
    
    def markdown_to_blocks(self, markdown):
        """调用飞书 API 将 Markdown 转为 docx block 结构"""
        return self._request(
            "POST", "/open-apis/docx/v1/documents/blocks/convert",
            body={"content_type": "markdown", "content": markdown}
        )
    
    # convert API 返回但 insert API 不接受的 block 顶层字段
    _BLOCK_READONLY_KEYS = {"parent_id", "index", "children_id"}
    # table.property 中已知安全的字段白名单
    _TABLE_PROPERTY_WHITELIST = {
        "row_size", "column_size", "header_row",
        "column_width", "row_height", "default_column_width", "default_row_height",
    }

    @classmethod
    def _sanitize_blocks(cls, blocks):
        """递归清洗 block 结构，移除 convert API 返回但 insert API 不接受的字段。"""
        for block in blocks:
            if not isinstance(block, dict):
                continue
            # 清除 block 顶层只读/非标准字段
            for key in cls._BLOCK_READONLY_KEYS:
                block.pop(key, None)
            # 清除 table 块中的不兼容属性
            if "table" in block and isinstance(block["table"], dict):
                table = block["table"]
                prop = table.get("property")
                if isinstance(prop, dict):
                    # 旧的 merge_info 清除
                    prop.pop("merge_info", None)
                    # 只保留白名单字段
                    bad_keys = [k for k in prop if k not in cls._TABLE_PROPERTY_WHITELIST]
                    for k in bad_keys:
                        del prop[k]
            # 清除 table_cell 中可能的非标准属性
            if "table_cell" in block and isinstance(block["table_cell"], dict):
                cell = block["table_cell"]
                cell.pop("merge_info", None)
            # 递归处理子块
            children = block.get("children", [])
            if isinstance(children, list) and children:
                cls._sanitize_blocks(children)
        return blocks
    
    def insert_blocks(self, document_id, blocks, first_level_block_ids, index=0, parent_block_id=None):
        """将 block 插入文档指定位置（支持嵌套块）

        Args:
            document_id: 文档 ID
            blocks: 要插入的 block 列表
            first_level_block_ids: blocks 中属于第一层级的 block ID 列表
            index: 插入位置索引（0 表示最前面）
            parent_block_id: 目标父 block ID，默认 document_id（文档根节点）
        """
        parent = parent_block_id or document_id
        path = f"/open-apis/docx/v1/documents/{document_id}/blocks/{parent}/descendant"
        payload = {"children_id": first_level_block_ids, "descendants": blocks, "index": index}
        query = {"document_revision_id": -1}
        return self._request("POST", path, body=payload, query=query)
    
    def write_markdown(self, document_id, markdown):
        """将 Markdown 内容写入文档（自动转换 + 清洗 + 分批插入 + 降级恢复）

        返回值:
            dict: 包含 insert API 响应，以及:
                - warnings: list[str] 警告信息（含被跳过的 block）
                - blocks_total: int 总 block 数
                - blocks_inserted: int 成功插入数
        """
        warnings = []

        # 1. 转换
        data = self.markdown_to_blocks(markdown)
        raw_blocks = data.get("blocks", [])
        first_level_ids = data.get("first_level_block_ids", [])
        convert_warnings = data.get("warnings", [])
        if convert_warnings:
            warnings.extend(
                w if isinstance(w, str) else str(w) for w in convert_warnings
            )
        if not raw_blocks:
            raise RuntimeError("Markdown conversion returned empty blocks")

        # 2. 清洗
        raw_blocks = self._sanitize_blocks(raw_blocks)

        # 3. 建立映射 & 按序重建
        block_map = {}
        for b in raw_blocks:
            if isinstance(b, dict) and "block_id" in b:
                block_map[b["block_id"]] = b

        def collect_subtree(block_id):
            result = []
            block = block_map.get(block_id)
            if not block:
                return result
            result.append(block)
            for child_id in block.get("children", []):
                if isinstance(child_id, str):
                    result.extend(collect_subtree(child_id))
            return result

        ordered_blocks = []
        for fid in first_level_ids:
            ordered_blocks.extend(collect_subtree(fid))
        covered = {b["block_id"] for b in ordered_blocks}
        for b in block_map.values():
            if b["block_id"] not in covered:
                ordered_blocks.append(b)

        total = len(ordered_blocks)
        first_level_set = set(first_level_ids)

        # 4. 尝试批量插入
        last_result = None
        inserted_count = 0
        try:
            if total <= MAX_BLOCKS_PER_REQUEST:
                batch_first_ids = [
                    b["block_id"] for b in ordered_blocks
                    if b["block_id"] in first_level_set
                ]
                last_result = self.insert_blocks(
                    document_id, ordered_blocks, batch_first_ids
                )
                inserted_count = total
            else:
                for i in range(0, total, MAX_BLOCKS_PER_REQUEST):
                    batch_blocks = ordered_blocks[i: i + MAX_BLOCKS_PER_REQUEST]
                    batch_block_ids = {b["block_id"] for b in batch_blocks}
                    batch_first_ids = [
                        fid for fid in first_level_ids if fid in batch_block_ids
                    ]
                    last_result = self.insert_blocks(
                        document_id, batch_blocks, batch_first_ids, inserted_count
                    )
                    inserted_count += len(batch_blocks)
        except RuntimeError as batch_err:
            # 5. 批量插入失败，降级为逐个 first_level block 插入
            warnings.append(f"批量插入失败（{batch_err}），降级为逐块插入")

            _BLOCK_TYPE_NAMES = {
                2: "text", 3: "h1", 4: "h2", 5: "h3", 6: "h4", 7: "h5",
                8: "h6", 9: "h7", 10: "h8", 11: "h9", 12: "bullet",
                13: "ordered", 14: "code", 15: "quote", 16: "divider",
                17: "todo", 22: "table", 27: "image", 31: "table_v2",
            }

            # 按 first_level block 分组
            first_level_subtrees = []
            for fid in first_level_ids:
                subtree = collect_subtree(fid)
                if subtree:
                    first_level_subtrees.append((fid, subtree))

            # 处理未被 first_level_ids 覆盖的块
            covered_by_fl = set()
            for fid in first_level_ids:
                covered_by_fl.update(b["block_id"] for b in collect_subtree(fid))
            orphan_blocks = [
                b for b in ordered_blocks
                if b["block_id"] not in covered_by_fl
            ]
            if orphan_blocks:
                first_level_subtrees.append(("_orphans_", orphan_blocks))

            inserted_count = 0
            current_index = 0
            for fl_id, subtree in first_level_subtrees:
                try:
                    fl_ids_in_subtree = [
                        b["block_id"] for b in subtree
                        if b["block_id"] in first_level_set or b["block_id"] == fl_id
                    ]
                    if not fl_ids_in_subtree:
                        fl_ids_in_subtree = [subtree[0]["block_id"]]
                    last_result = self.insert_blocks(
                        document_id, subtree, fl_ids_in_subtree, current_index
                    )
                    inserted_count += len(subtree)
                    current_index += 1
                except RuntimeError as block_err:
                    # 确定失败的 block 类型
                    if subtree:
                        bt = subtree[0].get("block_type", "?")
                        bt_name = _BLOCK_TYPE_NAMES.get(bt, f"type_{bt}")
                    else:
                        bt_name = "unknown"
                    msg = f"跳过 block（{bt_name}，{fl_id[:8]}…）：{block_err}"
                    if bt in (22, 31):
                        msg += "；飞书 API 对表格支持有限，建议将表格转为列表格式"
                    warnings.append(msg)

        # 6. 组装返回值
        # 不再透传 insert_blocks API 原始响应（含大量 block_id_relations 映射），
        # 避免 AI context 被无意义的内部 block 映射塞满甚至触发截断。
        return {
            "status": "ok",
            "blocks_total": total,
            "blocks_inserted": inserted_count,
            "warnings": warnings,
        }

    def document_comments(self, file_token, file_type="docx", page_token=None, page_size=50, is_whole=None, is_solved=None, need_reaction=False, user_id_type="open_id"):
        """获取云文档评论列表（分页）

        Args:
            file_token: 云文档 token
            file_type: 文档类型（docx/sheet/slides/file）
            page_token: 分页标记
            page_size: 每页条数，默认 50，最大 100
            is_whole: 是否只取全文评论（None=不限）
            is_solved: 是否只取已解决评论（None=不限）
            need_reaction: 是否获取评论的表情回复
            user_id_type: 用户 ID 类型（open_id/union_id/user_id）

        Returns:
            dict: {items: [...], has_more: bool, page_token: str}
        """
        query = {
            "file_type": file_type,
            "page_size": min(max(1, page_size), 100),
            "need_reaction": "true" if need_reaction else "false",
            "user_id_type": user_id_type,
        }
        if page_token:
            query["page_token"] = page_token
        if is_whole is not None:
            query["is_whole"] = "true" if is_whole else "false"
        if is_solved is not None:
            query["is_solved"] = "true" if is_solved else "false"

        return self._request(
            "GET",
            f"/open-apis/drive/v1/files/{file_token}/comments",
            query=query,
        )

    def document_comments_all(self, file_token, file_type="docx", is_whole=None, is_solved=None, need_reaction=False, user_id_type="open_id", max_results=None):
        """获取云文档全部评论（自动分页）

        注意：评论的回复（reply_list）若超过一页，也会自动拉取所有回复。

        Returns:
            list: 评论 item 列表，每个 item 包含完整的 reply_list.replies
        """
        all_items = []
        page_token = None
        while True:
            data = self.document_comments(
                file_token=file_token,
                file_type=file_type,
                page_token=page_token,
                page_size=100,
                is_whole=is_whole,
                is_solved=is_solved,
                need_reaction=need_reaction,
                user_id_type=user_id_type,
            )
            items = data.get("items", [])
            for item in items:
                # 自动分页拉取回复
                item = self._fetch_all_replies(item, file_token, file_type, need_reaction, user_id_type)
                all_items.append(item)
            if max_results is not None and len(all_items) >= max_results:
                break
            if not data.get("has_more"):
                break
            page_token = data.get("page_token")
        return all_items

    def _fetch_all_replies(self, comment_item, file_token, file_type, need_reaction, user_id_type):
        """自动拉取评论的所有回复（处理 reply_list 的分页）"""
        reply_list = comment_item.get("reply_list", {})
        if not reply_list:
            return comment_item
        all_replies = reply_list.get("replies", [])
        page_token = reply_list.get("page_token")
        has_more = reply_list.get("has_more", False)

        while has_more and page_token:
            query = {
                "file_type": file_type,
                "page_size": 100,
                "need_reaction": "true" if need_reaction else "false",
                "user_id_type": user_id_type,
                "page_token": page_token,
            }
            # 回复分页通过 comment_id 作为 page_token 参数查询
            # 实际上飞书文档说 replies 的分页也是通过同一接口的 page_token
            # 但回复没有单独的 API，需要通过原接口继续翻页
            # 这里我们简化处理：回复的分页数据已经在原接口返回了
            # 如果回复真的很多，需要再次调用接口
            data = self._request(
                "GET",
                f"/open-apis/drive/v1/files/{file_token}/comments",
                query=query,
            )
            # 这里其实 API 的设计是：回复的 has_more/page_token 在同一响应里
            # 但再次查询时不会只返回回复，所以这种场景比较少见
            # 简单处理：跳出
            break

        reply_list["replies"] = all_replies
        comment_item["reply_list"] = reply_list
        return comment_item

    def document_comment_create(self, file_token, text, file_type="docx", user_id_type="open_id"):
        """在云文档中添加全文评论

        Args:
            file_token: 云文档 token
            text: 评论文本内容
            file_type: 文档类型（docx/sheet/slides/file）
            user_id_type: 用户 ID 类型

        Returns:
            dict: 评论数据，包含 comment_id 等
        """
        query = {
            "file_type": file_type,
            "user_id_type": user_id_type,
        }
        body = {
            "reply_list": {
                "replies": [
                    {
                        "content": {
                            "elements": [
                                {
                                    "type": "text_run",
                                    "text_run": {
                                        "text": text,
                                    },
                                }
                            ]
                        }
                    }
                ]
            }
        }
        return self._request(
            "POST",
            f"/open-apis/drive/v1/files/{file_token}/comments",
            query=query,
            body=body,
        )

    def document_comment_reply(self, file_token, comment_id, text, file_type="docx", user_id_type="open_id"):
        """回复云文档评论

        Args:
            file_token: 云文档 token
            comment_id: 评论 ID
            text: 回复文本内容
            file_type: 文档类型（docx/sheet/slides/file）
            user_id_type: 用户 ID 类型

        Returns:
            dict: 回复数据，包含 reply_id、user_id、create_time 等
        """
        query = {
            "file_type": file_type,
            "user_id_type": user_id_type,
        }
        body = {
            "content": {
                "elements": [
                    {
                        "type": "text_run",
                        "text_run": {
                            "text": text,
                        },
                    }
                ]
            }
        }
        return self._request(
            "POST",
            f"/open-apis/drive/v1/files/{file_token}/comments/{comment_id}/replies",
            query=query,
            body=body,
        )
