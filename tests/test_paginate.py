#!/usr/bin/env python3
"""Tests for FeishuClientCore._paginate helper."""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, call

sys.path.insert(0, str(Path(__file__).parent.parent))

from feishu_common._client_core import FeishuClientCore
from feishu_common._client_doc import DocMixin


def _make_client():
    """Create a minimal client with mocked credentials."""
    client = object.__new__(FeishuClientCore)
    client.base_url = "https://open.feishu.cn"
    client._token = "fake"
    client._token_expire = 9999999999
    client.user_access_token = None
    return client


class TestPaginate(unittest.TestCase):
    def test_single_page(self):
        client = _make_client()
        client._request = MagicMock(return_value={"items": [1, 2, 3], "has_more": False})
        result = client._paginate("GET", "/api/test")
        self.assertEqual(result, [1, 2, 3])
        client._request.assert_called_once()

    def test_multi_page(self):
        client = _make_client()
        client._request = MagicMock(side_effect=[
            {"items": [1, 2], "has_more": True, "page_token": "tok1"},
            {"items": [3, 4], "has_more": True, "page_token": "tok2"},
            {"items": [5], "has_more": False},
        ])
        result = client._paginate("GET", "/api/test", page_size=2)
        self.assertEqual(result, [1, 2, 3, 4, 5])
        self.assertEqual(client._request.call_count, 3)

    def test_max_results_truncates(self):
        client = _make_client()
        client._request = MagicMock(side_effect=[
            {"items": [1, 2, 3], "has_more": True, "page_token": "tok1"},
            {"items": [4, 5], "has_more": False},
        ])
        result = client._paginate("GET", "/api/test", page_size=3, max_results=4)
        self.assertEqual(result, [1, 2, 3, 4])
        # Only needed 2 pages to get 4 items
        self.assertEqual(client._request.call_count, 2)

    def test_max_results_within_single_page(self):
        client = _make_client()
        client._request = MagicMock(return_value={"items": [1, 2, 3, 4, 5], "has_more": True, "page_token": "tok1"})
        result = client._paginate("GET", "/api/test", page_size=5, max_results=3)
        self.assertEqual(result, [1, 2, 3])
        client._request.assert_called_once()

    def test_empty_response(self):
        client = _make_client()
        client._request = MagicMock(return_value={"items": [], "has_more": False})
        result = client._paginate("GET", "/api/test")
        self.assertEqual(result, [])

    def test_custom_keys(self):
        client = _make_client()
        client._request = MagicMock(side_effect=[
            {"files": ["a.txt"], "has_more": True, "next_page_token": "n1"},
            {"files": ["b.txt"], "has_more": False},
        ])
        result = client._paginate(
            "GET", "/api/files",
            items_key="files", page_token_key="next_page_token",
        )
        self.assertEqual(result, ["a.txt", "b.txt"])

    def test_body_page_token(self):
        client = _make_client()
        mock_req = MagicMock(return_value={"items": [1], "has_more": False})
        client._request = mock_req
        client._paginate("POST", "/api/search", page_token_in="body", page_size=50, extra_body={"filter": "x"})
        args, kwargs = mock_req.call_args
        self.assertEqual(kwargs["body"]["filter"], "x")
        self.assertEqual(kwargs["body"]["page_size"], 50)

    def test_body_page_token_multi_page(self):
        client = _make_client()
        client._request = MagicMock(side_effect=[
            {"items": [1], "has_more": True, "page_token": "t1"},
            {"items": [2], "has_more": False},
        ])
        result = client._paginate("POST", "/api/search", page_token_in="body", page_size=1)
        self.assertEqual(result, [1, 2])
        # Verify second call includes page_token in body
        second_call = client._request.call_args_list[1]
        self.assertEqual(second_call[1]["body"]["page_token"], "t1")

    def test_extra_query_passed(self):
        client = _make_client()
        mock_req = MagicMock(return_value={"items": [1], "has_more": False})
        client._request = mock_req
        client._paginate("GET", "/api/test", extra_query={"folder": "abc"})
        _, kwargs = mock_req.call_args
        self.assertEqual(kwargs["query"]["folder"], "abc")

    def test_has_more_true_but_no_page_token_stops(self):
        client = _make_client()
        client._request = MagicMock(return_value={"items": [1], "has_more": True, "page_token": ""})
        result = client._paginate("GET", "/api/test")
        self.assertEqual(result, [1])
        client._request.assert_called_once()


class TestSanitizeBlocks(unittest.TestCase):
    def test_removes_readonly_keys(self):
        blocks = [{"block_id": "b1", "block_type": 2, "parent_id": "p", "index": 0, "children_id": []}]
        result = DocMixin._sanitize_blocks(blocks)
        self.assertNotIn("parent_id", result[0])
        self.assertNotIn("index", result[0])
        self.assertNotIn("children_id", result[0])
        self.assertEqual(result[0]["block_id"], "b1")

    def test_cleans_table_property(self):
        blocks = [{
            "block_id": "t1",
            "block_type": 22,
            "table": {
                "property": {
                    "row_size": 2, "column_size": 3,
                    "merge_info": {"some": "data"},
                    "unknown_field": "bad",
                }
            }
        }]
        result = DocMixin._sanitize_blocks(blocks)
        prop = result[0]["table"]["property"]
        self.assertNotIn("merge_info", prop)
        self.assertNotIn("unknown_field", prop)
        self.assertEqual(prop["row_size"], 2)

    def test_recursive_children(self):
        blocks = [{
            "block_id": "parent",
            "children": [
                {"block_id": "child", "parent_id": "parent", "block_type": 2}
            ]
        }]
        result = DocMixin._sanitize_blocks(blocks)
        self.assertNotIn("parent_id", result[0]["children"][0])


if __name__ == "__main__":
    unittest.main()
