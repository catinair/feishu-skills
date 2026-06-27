#!/usr/bin/env python3
"""_client_sheets.py -- 电子表格相关 API mixin。"""

class SheetsMixin:
    def sheet_create(self, title=None, folder_token=None):
        """创建电子表格"""
        body = {}
        if title:
            body["title"] = title
        if folder_token:
            body["folder_token"] = folder_token
        data = self._request("POST", "/open-apis/sheets/v3/spreadsheets", body=body or None)
        return data.get("spreadsheet", {})
    
    def sheet_get_info(self, spreadsheet_token):
        """获取电子表格元数据（含 sheet_id 列表）"""
        return self._request("GET", f"/open-apis/sheets/v2/spreadsheets/{spreadsheet_token}/metainfo")
    
    def sheet_read(self, spreadsheet_token, sheet_id, range_str):
        """读取单元格数据
    
        range_str 格式: "A1:B10" 或 "A1"
        """
        return self._request(
            "GET", f"/open-apis/sheets/v2/spreadsheets/{spreadsheet_token}/values/{sheet_id}!{range_str}"
        )
    
    def sheet_write(self, spreadsheet_token, sheet_id, range_str, values):
        """写入单元格数据
    
        values: 二维数组，如 [["姓名", "年龄"], ["张三", 25]]
        """
        return self._request(
            "PUT", f"/open-apis/sheets/v2/spreadsheets/{spreadsheet_token}/values",
            body={
                "valueRange": {
                    "range": f"{sheet_id}!{range_str}",
                    "values": values,
                }
            }
        )
    
    def sheet_append(self, spreadsheet_token, sheet_id, values):
        """追加行数据到表格末尾"""
        return self._request(
            "POST", f"/open-apis/sheets/v2/spreadsheets/{spreadsheet_token}/values_append",
            body={
                "valueRange": {
                    "range": sheet_id,
                    "values": values,
                }
            },
            query={"insertDataOption": "INSERT_ROWS", "valueInputOption": "USER_ENTERED"}
        )
    
