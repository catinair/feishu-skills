#!/usr/bin/env python3
"""_client_base.py -- 多维表格相关 API mixin。"""
import os

class BaseMixin:
    def base_create(self, name, folder_token=None):
        """创建多维表格"""
        body = {"name": name}
        if folder_token:
            body["folder_token"] = folder_token
        data = self._request("POST", "/open-apis/bitable/v1/apps", body=body)
        return data.get("app", {})

    def base_list_tables(self, app_token, max_results=None):
        """列出多维表格中的所有数据表"""
        tables = self._paginate("GET", f"/open-apis/bitable/v1/apps/{app_token}/tables", max_results=max_results)
        return {"total": len(tables), "items": tables, "has_more": False}

    def base_query_records(self, app_token, table_id, page_size=500, filter_expr=None, max_results=None):
        """查询数据表记录（自动分页）"""
        extra_query = {"filter": filter_expr} if filter_expr else None
        records = self._paginate(
            "GET", f"/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records",
            page_size=page_size, max_results=max_results, extra_query=extra_query,
        )
        return {"total": len(records), "records": records}

    def base_create_record(self, app_token, table_id, fields):
        """创建单条记录"""
        data = self._request(
            "POST", f"/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records",
            body={"fields": fields}
        )
        return data.get("record", {})

    def base_update_record(self, app_token, table_id, record_id, fields):
        """更新单条记录"""
        data = self._request(
            "PUT", f"/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id}",
            body={"fields": fields}
        )
        return data.get("record", {})

    def base_delete_record(self, app_token, table_id, record_id):
        """删除单条记录"""
        self._request("DELETE", f"/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id}")
        return {"deleted": True, "record_id": record_id}

    def base_get(self, app_token):
        """获取多维表格信息"""
        return self._request("GET", f"/open-apis/bitable/v1/apps/{app_token}")

    def base_copy(self, app_token, name, folder_token=None):
        """复制多维表格"""
        body = {"name": name}
        if folder_token:
            body["folder_token"] = folder_token
        data = self._request("POST", f"/open-apis/bitable/v1/apps/{app_token}/copy", body=body)
        return data.get("app", {})

    def base_list_fields(self, app_token, table_id, max_results=None):
        """列出数据表的所有字段"""
        fields = self._paginate(
            "GET", f"/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/fields",
            max_results=max_results,
        )
        return {"total": len(fields), "items": fields, "has_more": False}

    def base_create_table(self, app_token, name, fields=None):
        """在多维表格中创建数据表

        fields 格式示例：
        [
            {"field_name": "姓名", "type": 1},
            {"field_name": "年龄", "type": 2},
        ]
        """
        body = {"table": {"name": name}}
        if fields:
            body["table"]["fields"] = fields
        data = self._request("POST", f"/open-apis/bitable/v1/apps/{app_token}/tables", body=body)
        return data

    def base_delete_table(self, app_token, table_id):
        """删除数据表"""
        self._request("DELETE", f"/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}")
        return {"deleted": True, "table_id": table_id}

    def base_batch_update_records(self, app_token, table_id, records):
        """批量更新记录

        records 格式：
        [
            {"record_id": "rec_xxx", "fields": {"字段名": "新值"}},
            ...
        ]
        """
        data = self._request(
            "POST", f"/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_update",
            body={"records": records}
        )
        return data.get("records", [])

    def base_batch_delete_records(self, app_token, table_id, record_ids):
        """批量删除记录"""
        data = self._request(
            "POST", f"/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_delete",
            body={"records": record_ids}
        )
        return {"deleted": len(record_ids), "record_ids": record_ids}

    def base_list_views(self, app_token, table_id, max_results=None):
        """列出数据表的所有视图"""
        views = self._paginate(
            "GET", f"/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/views",
            max_results=max_results,
        )
        return {"total": len(views), "items": views, "has_more": False}

    def base_get_record(self, app_token, table_id, record_id):
        """获取单条记录详情"""
        return self._request("GET", f"/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id}")

    def base_batch_create_records(self, app_token, table_id, records):
        """批量创建记录

        Args:
            records: [{'fields': {...}}, ...] 格式数组
        """
        body = {"records": records}
        return self._request("POST", f"/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_create", body=body)

    def base_get_table(self, app_token, table_id):
        """获取单个数据表信息（Bitable v1 无单表接口，通过列表过滤）"""
        data = self.base_list_tables(app_token)
        for t in data.get("items", []):
            if t.get("table_id") == table_id:
                return {"table": t}
        raise RuntimeError(f"Table not found: {table_id}")

    def base_update_table(self, app_token, table_id, name):
        """更新数据表（重命名）

        Bitable v1 无此接口，使用 Base v3 API。
        如需使用，应用需开通 base:base 相关权限。
        """
        body = {"name": name}
        return self._request("PATCH", f"/open-apis/base/v3/bases/{app_token}/tables/{table_id}", body=body)

    def base_get_field(self, app_token, table_id, field_id):
        """获取单个字段详情（Bitable v1 无单字段接口，通过列表过滤）"""
        data = self.base_list_fields(app_token, table_id)
        for f in data.get("items", []):
            if f.get("field_id") == field_id:
                return {"field": f}
        raise RuntimeError(f"Field not found: {field_id}")

    def base_create_field(self, app_token, table_id, field_name, field_type, property=None, ui_type=None):
        """创建字段

        Args:
            field_name: 字段名称
            field_type: 字段类型，如 1(文本), 2(数字), 3(单选), 4(多选), 5(日期) 等
            property: 字段属性，如单选的 options、数字的 formatter 等
            ui_type: UI 类型，如 "Text", "Email", "Phone", "Url", "Rating" 等
        """
        body = {"field_name": field_name, "type": field_type}
        if ui_type is not None:
            body["ui_type"] = ui_type
        if property is not None:
            body["property"] = property
        return self._request("POST", f"/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/fields", body=body)

    def base_update_field(self, app_token, table_id, field_id, field_name=None, field_type=None, property=None):
        """更新字段

        Bitable v1 的 field update 必须同时传入 type，若未提供则自动获取当前字段 type。
        """
        body = {}
        if field_name is not None:
            body["field_name"] = field_name
        if property is not None:
            body["property"] = property
        if field_type is not None:
            body["type"] = field_type
        else:
            # Bitable v1 必须传 type，自动获取
            field_info = self.base_get_field(app_token, table_id, field_id)
            body["type"] = field_info["field"]["type"]
        return self._request("PUT", f"/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/fields/{field_id}", body=body)

    def base_delete_field(self, app_token, table_id, field_id):
        """删除字段"""
        self._request("DELETE", f"/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/fields/{field_id}")
        return {"deleted": True, "field_id": field_id}

    def base_create_view(self, app_token, table_id, view_name, view_type="grid"):
        """创建视图

        Args:
            view_name: 视图名称
            view_type: 视图类型，grid(表格)/kanban(看板)/gallery(画册)/gantt(甘特图)
        """
        body = {"view_name": view_name, "view_type": view_type}
        return self._request("POST", f"/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/views", body=body)

    def base_delete_view(self, app_token, table_id, view_id):
        """删除视图"""
        self._request("DELETE", f"/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/views/{view_id}")
        return {"deleted": True, "view_id": view_id}

    def base_rename_view(self, app_token, table_id, view_id, view_name):
        """重命名视图"""
        body = {"view_name": view_name}
        return self._request("PATCH", f"/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/views/{view_id}", body=body)

    def base_get_view(self, app_token, table_id, view_id):
        """获取单个视图详情（Bitable v1 无单视图接口，通过列表过滤）"""
        data = self.base_list_views(app_token, table_id)
        for v in data.get("items", []):
            if v.get("view_id") == view_id:
                return {"view": v}
        raise RuntimeError(f"View not found: {view_id}")

    # ── Base v3 API（需开通 base:base 相关权限）──

    def _base_v3_get(self, app_token, path_segment):
        """Base v3 GET 请求辅助方法"""
        return self._request("GET", f"/open-apis/base/v3/bases/{app_token}/{path_segment}")

    def _base_v3_put(self, app_token, path_segment, body):
        """Base v3 PUT 请求辅助方法"""
        return self._request("PUT", f"/open-apis/base/v3/bases/{app_token}/{path_segment}", body=body)

    def base_get_view_filter(self, app_token, table_id, view_id):
        """获取视图筛选条件（Base v3）"""
        return self._base_v3_get(app_token, f"tables/{table_id}/views/{view_id}/filter")

    def base_set_view_filter(self, app_token, table_id, view_id, filter_config):
        """设置视图筛选条件（Base v3）

        filter_config 示例:
            {"logic": "and", "conditions": [["fldStatus", "==", "Todo"]]}
        """
        return self._base_v3_put(app_token, f"tables/{table_id}/views/{view_id}/filter", filter_config)

    def base_get_view_sort(self, app_token, table_id, view_id):
        """获取视图排序配置（Base v3）"""
        return self._base_v3_get(app_token, f"tables/{table_id}/views/{view_id}/sort")

    def base_set_view_sort(self, app_token, table_id, view_id, sort_config):
        """设置视图排序配置（Base v3）

        sort_config 示例:
            [{"field_id": "fldName", "desc": false}]
            或包装格式: {"sort_config": [{"field_id": "fldName", "desc": false}]}
        """
        if isinstance(sort_config, list):
            sort_config = {"sort_config": sort_config}
        return self._base_v3_put(app_token, f"tables/{table_id}/views/{view_id}/sort", sort_config)

    def base_get_view_group(self, app_token, table_id, view_id):
        """获取视图分组配置（Base v3）"""
        return self._base_v3_get(app_token, f"tables/{table_id}/views/{view_id}/group")

    def base_set_view_group(self, app_token, table_id, view_id, group_config):
        """设置视图分组配置（Base v3）

        group_config 示例:
            [{"field_id": "fldStatus"}]
            或包装格式: {"group_config": [{"field_id": "fldStatus"}]}
        """
        if isinstance(group_config, list):
            group_config = {"group_config": group_config}
        return self._base_v3_put(app_token, f"tables/{table_id}/views/{view_id}/group", group_config)

    def base_get_view_visible_fields(self, app_token, table_id, view_id):
        """获取视图可见字段配置（Base v3）"""
        return self._base_v3_get(app_token, f"tables/{table_id}/views/{view_id}/visible_fields")

    def base_set_view_visible_fields(self, app_token, table_id, view_id, visible_fields_config):
        """设置视图可见字段配置（Base v3）"""
        return self._base_v3_put(app_token, f"tables/{table_id}/views/{view_id}/visible_fields", visible_fields_config)

    def base_query_data(self, app_token, dsl):
        """Base 数据查询（Base v3 JSON DSL 聚合查询）

        Args:
            dsl: 查询 DSL 对象，必须包含 dimensions 或 measures 之一
                示例: {"dimensions": [{"field_id": "fldStatus"}], "measures": [{"field_id": "fldAmount", "aggregator": "SUM"}]}
        """
        return self._request("POST", f"/open-apis/base/v3/bases/{app_token}/data/query", body=dsl)

    def base_list_record_history(self, app_token, table_id, record_id, page_size=30, max_version=None):
        """查询记录变更历史（Base v3）

        Args:
            max_version: 分页参数，传入上一页最后一条的 version 值
        """
        query = {"table_id": table_id, "record_id": record_id, "page_size": page_size}
        if max_version is not None:
            query["max_version"] = max_version
        return self._request("GET", f"/open-apis/base/v3/bases/{app_token}/record_history", query=query)

    def base_search_field_options(self, app_token, table_id, field_id, keyword=None, offset=0, limit=30):
        """搜索字段的选项列表（Base v3，适用于单选/多选字段）

        Args:
            keyword: 搜索关键词
            offset: 分页偏移
            limit: 分页大小
        """
        query = {"offset": offset, "limit": limit}
        if keyword:
            query["query"] = keyword
        return self._request("GET", f"/open-apis/base/v3/bases/{app_token}/tables/{table_id}/fields/{field_id}/options", query=query)

    def base_search_records(self, app_token, table_id, filter=None, sort=None, field_names=None, page_size=500, max_results=None):
        """高级搜索记录（支持复杂 filter/sort，自动分页）

        Args:
            filter: 筛选条件对象，如 {"conjunction": "and", "conditions": [...]}
            sort: 排序数组，如 [{"field_name": "日期", "desc": false}]
            field_names: 指定返回的字段名数组
            page_size: 每页条数（最大 500）
            max_results: 最大返回条数，None 表示不限制
        """
        extra_body = {}
        if filter is not None:
            extra_body["filter"] = filter
        if sort is not None:
            extra_body["sort"] = sort
        if field_names is not None:
            extra_body["field_names"] = field_names
        records = self._paginate(
            "POST", f"/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/search",
            page_size=page_size, max_results=max_results,
            page_token_in="body", extra_body=extra_body or None,
        )
        return {"total": len(records), "items": records, "has_more": False}

    def base_upsert_record(self, app_token, table_id, fields, record_id=None):
        """更新或插入记录

        提供 record_id 时更新，否则创建新记录。
        """
        if record_id:
            return self.base_update_record(app_token, table_id, record_id, fields)
        return self.base_create_record(app_token, table_id, fields)

    def base_upload_attachment(self, app_token, table_id, record_id, field_name, file_path):
        """上传附件到记录的指定字段

        会自动合并到该字段已有的附件列表中。
        """
        import os
        upload_result = self.upload_file(file_path, parent_type="bitable_file", parent_node=app_token)
        file_token = upload_result.get("file_token")
        file_name = os.path.basename(file_path)

        # 获取当前记录
        record = self.base_get_record(app_token, table_id, record_id)
        existing = record.get("fields", {}).get(field_name, [])
        if not isinstance(existing, list):
            existing = []

        # 合并附件
        attachments = existing + [{"file_token": file_token, "name": file_name}]

        # 更新记录
        return self.base_update_record(app_token, table_id, record_id, {field_name: attachments})
