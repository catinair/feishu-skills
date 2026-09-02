#!/usr/bin/env python3
"""
_endpoint_registry.py -- API endpoint identity and scope registry

Each method entry declares:
  identity: "app_only" | "user_only" | "both"
  scopes.tenant: list of required tenant scopes (empty if app_only not supported)
  scopes.user: list of required user scopes (empty if user_only not supported)

The resolver in _client_core.py uses this registry together with:
  - config/permissions.json (granted scopes)
  - config/settings.json (default_identity)
to determine which token to use for each API call.
"""

# Identity type constants
APP_ONLY = "app_only"
USER_ONLY = "user_only"
BOTH = "both"

# 已知需要飞书管理员审批才能在平台生效的 scopes。
# permissions.json 中声明了这些 scope 只代表“应用申请了该权限”，
# 不代表“管理员已审批通过”。setup_check 和 API 错误提示会据此给出预警。
ADMIN_APPROVAL_SCOPES = {
    # 云空间高敏感权限
    "drive:drive:readonly",
    "drive:drive",
    "drive:file",
    "drive:file:readonly",
    # 云文档协作者完整管理权限（只读/添加权限通常免审，不纳入预警）
    "docs:permission.member",
    # 通讯录敏感权限
    "contact:user",
    "contact:user:write",
    "contact:department",
    "contact:department:write",
    # 管理员相关
    "admin:admin",
}

ENDPOINT_REGISTRY = {
    # ── Internal / Admin ─────────────────────────────────────────────
    "application_scopes": {
        "identity": APP_ONLY,
        "scopes": {"tenant": [], "user": []},
    },
    # ── Doc ──────────────────────────────────────────────────────────
    "document_info": {
        "identity": BOTH,
        "scopes": {
            "tenant": ["docx:document:readonly"],
            "user": ["docx:document:readonly"],
        },
    },
    "document_block_info": {
        "identity": BOTH,
        "scopes": {
            "tenant": ["docx:document:readonly"],
            "user": ["docx:document:readonly"],
        },
    },
    "document_create_child_blocks": {
        "identity": BOTH,
        "scopes": {"tenant": ["docx:document"], "user": ["docx:document"]},
    },
    "document_update_block": {
        "identity": BOTH,
        "scopes": {"tenant": ["docx:document"], "user": ["docx:document"]},
    },
    "document_create": {
        "identity": BOTH,
        "scopes": {"tenant": ["docx:document:create"], "user": ["docx:document"]},
    },
    "document_blocks": {
        "identity": BOTH,
        "scopes": {
            "tenant": ["docx:document:readonly"],
            "user": ["docx:document:readonly"],
        },
    },
    "document_blocks_all": {
        "identity": BOTH,
        "scopes": {
            "tenant": ["docx:document:readonly"],
            "user": ["docx:document:readonly"],
        },
    },
    "document_raw_content": {
        "identity": BOTH,
        "scopes": {
            "tenant": ["docx:document:readonly"],
            "user": ["docx:document:readonly"],
        },
    },
    "markdown_to_blocks": {
        "identity": BOTH,
        "scopes": {
            "tenant": ["docx:document.block:convert"],
            "user": ["docx:document.block:convert"],
        },
    },
    "insert_blocks": {
        "identity": BOTH,
        "scopes": {"tenant": ["docx:document"], "user": ["docx:document"]},
    },
    "write_markdown": {
        "identity": BOTH,
        "scopes": {"tenant": ["docx:document"], "user": ["docx:document"]},
    },
    "document_comments": {
        "identity": BOTH,
        "scopes": {
            "tenant": ["docs:document.comment:read"],
            "user": ["docs:document.comment:read"],
        },
    },
    "document_comments_all": {
        "identity": BOTH,
        "scopes": {
            "tenant": ["docs:document.comment:read"],
            "user": ["docs:document.comment:read"],
        },
    },
    "document_comment_reply": {
        "identity": BOTH,
        "scopes": {
            "tenant": ["docs:document.comment:create"],
            "user": ["docs:document.comment:create"],
        },
    },
    "document_comment_create": {
        "identity": BOTH,
        "scopes": {
            "tenant": ["docs:document.comment:create"],
            "user": ["docs:document.comment:create"],
        },
    },
    # ── Drive ────────────────────────────────────────────────────────
    "list_files": {
        "identity": BOTH,
        "scopes": {
            "tenant": ["drive:drive:readonly"],
            "user": ["drive:drive:readonly"],
        },
    },
    "search_files": {
        "identity": BOTH,
        "scopes": {
            "tenant": ["drive:drive:readonly"],
            "user": ["drive:drive:readonly"],
        },
    },
    "copy_file": {
        "identity": BOTH,
        "scopes": {"tenant": ["drive:file"], "user": ["drive:file"]},
    },
    "upload_file": {
        "identity": BOTH,
        "scopes": {"tenant": ["drive:file:upload"], "user": ["drive:file:upload"]},
    },
    "move_file": {
        "identity": BOTH,
        "scopes": {"tenant": ["drive:file"], "user": ["drive:file"]},
    },
    "delete_file": {
        "identity": BOTH,
        "scopes": {"tenant": ["drive:file"], "user": ["drive:file"]},
    },
    "create_folder": {
        "identity": BOTH,
        # 官方文档：tenant 侧满足 drive:drive 或 space:folder:create 任一即可；
        # space:folder:create 为免审权限，作为 tenant 默认要求。
        "scopes": {"tenant": ["space:folder:create"], "user": ["space:folder:create"]},
    },
    # download_file, download_media, download_board use _resolve_and_get_token()
    # for identity resolution (binary streaming, can't go through _request)
    "download_file": {
        "identity": BOTH,
        "scopes": {
            "tenant": ["drive:drive:readonly"],
            "user": ["drive:drive:readonly"],
        },
    },
    "download_media": {
        "identity": BOTH,
        "scopes": {
            "tenant": ["drive:drive:readonly"],
            "user": ["drive:drive:readonly"],
        },
    },
    "batch_get_tmp_download_url": {
        "identity": BOTH,
        "scopes": {
            "tenant": ["drive:drive:readonly"],
            "user": ["drive:drive:readonly"],
        },
    },
    "download_board": {
        "identity": BOTH,
        "scopes": {
            "tenant": ["board:whiteboard:node:read"],
            "user": ["board:whiteboard:node:read"],
        },
    },
    "drive_create_export_task": {
        "identity": BOTH,
        "scopes": {"tenant": ["drive:drive:version"], "user": ["drive:drive:version"]},
    },
    "drive_get_export_task": {
        "identity": BOTH,
        "scopes": {
            "tenant": ["drive:drive:version:readonly"],
            "user": ["drive:drive:version:readonly"],
        },
    },
    "drive_export_download": {
        "identity": BOTH,
        "scopes": {
            "tenant": ["drive:drive:version:readonly"],
            "user": ["drive:drive:version:readonly"],
        },
    },
    "drive_export": {
        "identity": BOTH,
        "scopes": {"tenant": ["drive:drive:version"], "user": ["drive:drive:version"]},
    },
    # ── Sheets ───────────────────────────────────────────────────────
    "sheet_create": {
        "identity": BOTH,
        "scopes": {
            "tenant": ["sheets:spreadsheet:create"],
            "user": ["sheets:spreadsheet:create"],
        },
    },
    "sheet_get_info": {
        "identity": BOTH,
        "scopes": {
            "tenant": ["sheets:spreadsheet"],
            "user": ["sheets:spreadsheet.meta:read"],
        },
    },
    "sheet_read": {
        "identity": BOTH,
        "scopes": {"tenant": ["sheets:spreadsheet"], "user": ["sheets:spreadsheet"]},
    },
    "sheet_write": {
        "identity": BOTH,
        "scopes": {"tenant": ["sheets:spreadsheet"], "user": ["sheets:spreadsheet"]},
    },
    "sheet_append": {
        "identity": BOTH,
        "scopes": {"tenant": ["sheets:spreadsheet"], "user": ["sheets:spreadsheet"]},
    },
    # ── Wiki ─────────────────────────────────────────────────────────
    "wiki_get_node": {
        "identity": BOTH,
        "scopes": {"tenant": ["wiki:wiki:readonly"], "user": ["wiki:wiki:readonly"]},
    },
    "wiki_list_spaces": {
        "identity": BOTH,
        "scopes": {"tenant": ["wiki:wiki:readonly"], "user": ["wiki:wiki:readonly"]},
    },
    "wiki_create_node": {
        "identity": BOTH,
        "scopes": {"tenant": ["wiki:wiki"], "user": ["wiki:wiki"]},
    },
    "wiki_list_nodes": {
        "identity": BOTH,
        "scopes": {"tenant": ["wiki:wiki:readonly"], "user": ["wiki:wiki:readonly"]},
    },
    # ── Calendar ─────────────────────────────────────────────────────
    "calendar_list_events": {
        "identity": BOTH,
        "scopes": {
            "tenant": ["calendar:calendar.event:read"],
            "user": ["calendar:calendar.event:read"],
        },
    },
    "calendar_get_event": {
        "identity": BOTH,
        "scopes": {
            "tenant": ["calendar:calendar.event:read"],
            "user": ["calendar:calendar.event:read"],
        },
    },
    "calendar_create_event": {
        "identity": BOTH,
        "scopes": {
            "tenant": ["calendar:calendar.event:create"],
            "user": ["calendar:calendar.event:create"],
        },
    },
    "calendar_delete_event": {
        "identity": BOTH,
        "scopes": {
            "tenant": ["calendar:calendar.event:read"],
            "user": ["calendar:calendar.event:delete"],
        },
    },
    "calendar_freebusy": {
        "identity": BOTH,
        "scopes": {
            "tenant": ["calendar:timeoff"],
            "user": ["calendar:calendar.free_busy:read"],
        },
    },
    "calendar_update_event": {
        "identity": BOTH,
        "scopes": {
            "tenant": ["calendar:calendar.event:update"],
            "user": ["calendar:calendar.event:update"],
        },
    },
    "calendar_list_calendars": {
        "identity": BOTH,
        "scopes": {"tenant": ["calendar:calendar"], "user": ["calendar:calendar:read"]},
    },
    "calendar_subscribe": {
        "identity": BOTH,
        "scopes": {
            "tenant": ["calendar:calendar:subscribe"],
            "user": ["calendar:calendar:subscribe"],
        },
    },
    # ── IM ───────────────────────────────────────────────────────────
    "im_create_chat": {
        "identity": APP_ONLY,
        "scopes": {"tenant": ["im:chat"], "user": []},
    },
    "im_send_text": {
        "identity": BOTH,
        "scopes": {"tenant": ["im:message:send_as_bot"], "user": ["im:message"]},
    },
    "im_send_post": {
        "identity": BOTH,
        "scopes": {"tenant": ["im:message:send_as_bot"], "user": ["im:message"]},
    },
    "im_messages_list": {
        "identity": BOTH,
        "scopes": {"tenant": ["im:message:readonly"], "user": ["im:message"]},
    },
    "im_reply_message": {
        "identity": BOTH,
        "scopes": {"tenant": ["im:message:send_as_bot"], "user": ["im:message"]},
    },
    "im_send_file": {
        "identity": BOTH,
        "scopes": {"tenant": ["im:message:send_as_bot"], "user": ["im:message"]},
    },
    "im_send_image": {
        "identity": BOTH,
        "scopes": {"tenant": ["im:message:send_as_bot"], "user": ["im:message"]},
    },
    "upload_image": {
        "identity": APP_ONLY,
        "scopes": {"tenant": ["im:resource"], "user": []},
    },
    "im_chat_info": {
        "identity": BOTH,
        "scopes": {"tenant": ["im:chat:readonly"], "user": ["im:chat"]},
    },
    "im_chat_members": {
        "identity": BOTH,
        "scopes": {"tenant": ["im:chat.members:read"], "user": ["im:chat"]},
    },
    "im_chat_add_members": {
        "identity": BOTH,
        "scopes": {"tenant": ["im:chat.members:bot_access"], "user": ["im:chat"]},
    },
    "im_chat_update": {
        "identity": BOTH,
        "scopes": {"tenant": ["im:chat"], "user": ["im:chat"]},
    },
    "im_search_messages": {
        "identity": USER_ONLY,
        "scopes": {"tenant": [], "user": ["search:message"]},
    },
    "im_list_chats": {
        "identity": BOTH,
        "scopes": {"tenant": ["im:chat:readonly"], "user": ["im:chat"]},
    },
    "im_search_chats": {
        "identity": BOTH,
        "scopes": {"tenant": ["im:chat:readonly"], "user": ["im:chat"]},
    },
    # ── Minutes ──────────────────────────────────────────────────────
    "minutes_get": {
        "identity": BOTH,
        "scopes": {
            "tenant": ["minutes:minutes:readonly"],
            "user": ["minutes:minutes.basic:read"],
        },
    },
    "minutes_transcript": {
        "identity": BOTH,
        "scopes": {
            "tenant": ["minutes:minutes.transcript:export"],
            "user": ["minutes:minutes.artifacts:read"],
        },
    },
    "minutes_statistics": {
        "identity": APP_ONLY,
        "scopes": {"tenant": ["minutes:minutes:readonly"], "user": []},
    },
    "minutes_artifacts": {
        "identity": BOTH,
        "scopes": {
            "tenant": ["minutes:minutes:readonly"],
            "user": ["minutes:minutes.artifacts:read"],
        },
    },
    # ── Contact ──────────────────────────────────────────────────────
    "contact_search_users": {
        "identity": USER_ONLY,
        "scopes": {"tenant": [], "user": ["contact:user:search"]},
    },
    "contact_list_departments": {
        "identity": BOTH,
        "scopes": {
            "tenant": ["contact:department.base:readonly"],
            "user": ["contact:department.base:readonly"],
        },
    },
    "contact_get_department": {
        "identity": BOTH,
        "scopes": {
            "tenant": ["contact:department.base:readonly"],
            "user": ["contact:department.base:readonly"],
        },
    },
    "contact_list_department_members": {
        "identity": USER_ONLY,
        "scopes": {"tenant": [], "user": ["contact:user.base:readonly"]},
    },
    "contact_find_by_department": {
        "identity": BOTH,
        "scopes": {
            "tenant": ["contact:user.base:readonly"],
            "user": ["contact:user.base:readonly"],
        },
    },
    "contact_get_user": {
        "identity": BOTH,
        "scopes": {
            "tenant": ["contact:contact.base:readonly"],
            "user": ["contact:contact.base:readonly"],
        },
    },
    "contact_get_self": {
        "identity": USER_ONLY,
        "scopes": {"tenant": [], "user": ["auth:user.id:read"]},
    },
    "contact_colleagues": {
        "identity": USER_ONLY,
        "scopes": {"tenant": [], "user": ["contact:contact.base:readonly"]},
    },
    # ── Perm ─────────────────────────────────────────────────────────
    "perm_list_members": {
        "identity": BOTH,
        "scopes": {
            "tenant": ["docs:permission.member:readonly"],
            "user": ["docs:permission.member:readonly"],
        },
    },
    "perm_add_member": {
        "identity": BOTH,
        "scopes": {
            "tenant": ["docs:permission.member:create"],
            "user": ["docs:permission.member:create"],
        },
    },
    "perm_remove_member": {
        "identity": BOTH,
        "scopes": {
            "tenant": ["docs:permission.member"],
            "user": ["docs:permission.member"],
        },
    },
    # ── Base ─────────────────────────────────────────────────────────
    "base_create": {
        "identity": BOTH,
        "scopes": {"tenant": ["base:app:create"], "user": ["bitable:app"]},
    },
    "base_list_tables": {
        "identity": BOTH,
        "scopes": {"tenant": ["bitable:app"], "user": ["bitable:app"]},
    },
    "base_query_records": {
        "identity": BOTH,
        "scopes": {"tenant": ["bitable:app"], "user": ["bitable:app"]},
    },
    "base_create_record": {
        "identity": BOTH,
        "scopes": {"tenant": ["base:record:create"], "user": ["bitable:app"]},
    },
    "base_update_record": {
        "identity": BOTH,
        "scopes": {"tenant": ["base:record:update"], "user": ["bitable:app"]},
    },
    "base_delete_record": {
        "identity": BOTH,
        "scopes": {"tenant": ["bitable:app"], "user": ["bitable:app"]},
    },
    "base_get": {
        "identity": BOTH,
        "scopes": {"tenant": ["bitable:app"], "user": ["bitable:app"]},
    },
    "base_copy": {
        "identity": BOTH,
        "scopes": {"tenant": ["bitable:app"], "user": ["bitable:app"]},
    },
    "base_list_fields": {
        "identity": BOTH,
        "scopes": {"tenant": ["base:field:read"], "user": ["bitable:app"]},
    },
    "base_create_table": {
        "identity": BOTH,
        "scopes": {"tenant": ["base:table:create"], "user": ["bitable:app"]},
    },
    "base_delete_table": {
        "identity": BOTH,
        "scopes": {"tenant": ["bitable:app"], "user": ["bitable:app"]},
    },
    "base_batch_update_records": {
        "identity": BOTH,
        "scopes": {"tenant": ["base:record:update"], "user": ["bitable:app"]},
    },
    "base_batch_delete_records": {
        "identity": BOTH,
        "scopes": {"tenant": ["bitable:app"], "user": ["bitable:app"]},
    },
    "base_list_views": {
        "identity": BOTH,
        "scopes": {"tenant": ["bitable:app"], "user": ["bitable:app"]},
    },
    "base_get_record": {
        "identity": BOTH,
        "scopes": {"tenant": ["bitable:app"], "user": ["bitable:app"]},
    },
    "base_get_table": {
        "identity": BOTH,
        "scopes": {"tenant": ["bitable:app"], "user": ["bitable:app"]},
    },
    "base_get_field": {
        "identity": BOTH,
        "scopes": {"tenant": ["base:field:read"], "user": ["bitable:app"]},
    },
    "base_batch_create_records": {
        "identity": BOTH,
        "scopes": {"tenant": ["base:record:create"], "user": ["bitable:app"]},
    },
    "base_update_table": {
        "identity": BOTH,
        "scopes": {"tenant": ["bitable:app"], "user": ["bitable:app"]},
    },
    "base_create_field": {
        "identity": BOTH,
        "scopes": {"tenant": ["base:block:create"], "user": ["base:block:create"]},
    },
    "base_update_field": {
        "identity": BOTH,
        "scopes": {"tenant": ["base:block:update"], "user": ["base:block:update"]},
    },
    "base_delete_field": {
        "identity": BOTH,
        "scopes": {"tenant": ["base:block:delete"], "user": ["base:block:delete"]},
    },
    "base_create_view": {
        "identity": BOTH,
        "scopes": {"tenant": ["bitable:app"], "user": ["bitable:app"]},
    },
    "base_delete_view": {
        "identity": BOTH,
        "scopes": {"tenant": ["bitable:app"], "user": ["bitable:app"]},
    },
    "base_rename_view": {
        "identity": BOTH,
        "scopes": {"tenant": ["bitable:app"], "user": ["bitable:app"]},
    },
    "base_get_view": {
        "identity": BOTH,
        "scopes": {"tenant": ["bitable:app"], "user": ["bitable:app"]},
    },
    "base_get_view_filter": {
        "identity": BOTH,
        "scopes": {"tenant": ["bitable:app"], "user": ["bitable:app"]},
    },
    "base_set_view_filter": {
        "identity": BOTH,
        "scopes": {"tenant": ["bitable:app"], "user": ["bitable:app"]},
    },
    "base_get_view_sort": {
        "identity": BOTH,
        "scopes": {"tenant": ["bitable:app"], "user": ["bitable:app"]},
    },
    "base_set_view_sort": {
        "identity": BOTH,
        "scopes": {"tenant": ["bitable:app"], "user": ["bitable:app"]},
    },
    "base_get_view_group": {
        "identity": BOTH,
        "scopes": {"tenant": ["bitable:app"], "user": ["bitable:app"]},
    },
    "base_set_view_group": {
        "identity": BOTH,
        "scopes": {"tenant": ["bitable:app"], "user": ["bitable:app"]},
    },
    "base_get_view_visible_fields": {
        "identity": BOTH,
        "scopes": {"tenant": ["bitable:app"], "user": ["bitable:app"]},
    },
    "base_set_view_visible_fields": {
        "identity": BOTH,
        "scopes": {"tenant": ["bitable:app"], "user": ["bitable:app"]},
    },
    "base_query_data": {
        "identity": BOTH,
        "scopes": {"tenant": ["bitable:app"], "user": ["bitable:app"]},
    },
    "base_list_record_history": {
        "identity": BOTH,
        "scopes": {"tenant": ["bitable:app"], "user": ["bitable:app"]},
    },
    "base_search_field_options": {
        "identity": BOTH,
        "scopes": {"tenant": ["bitable:app"], "user": ["bitable:app"]},
    },
    "base_search_records": {
        "identity": BOTH,
        "scopes": {"tenant": ["bitable:app"], "user": ["bitable:app"]},
    },
    "base_upsert_record": {
        "identity": BOTH,
        "scopes": {"tenant": ["bitable:app"], "user": ["bitable:app"]},
    },
    "base_upload_attachment": {
        "identity": BOTH,
        "scopes": {
            "tenant": ["bitable:app", "drive:file:upload"],
            "user": ["bitable:app"],
        },
    },
    "base_download_attachments": {
        "identity": BOTH,
        "scopes": {
            "tenant": ["bitable:app", "drive:drive:readonly"],
            "user": ["bitable:app"],
        },
    },
    # ── Task ─────────────────────────────────────────────────────────
    "task_create": {
        "identity": USER_ONLY,
        "scopes": {"tenant": [], "user": ["task:task:write"]},
    },
    "task_get": {
        "identity": USER_ONLY,
        "scopes": {"tenant": [], "user": ["task:task:read"]},
    },
    "task_list": {
        "identity": USER_ONLY,
        "scopes": {"tenant": [], "user": ["task:task:read"]},
    },
    "task_patch": {
        "identity": USER_ONLY,
        "scopes": {"tenant": [], "user": ["task:task:write"]},
    },
    "task_comment_create": {
        "identity": USER_ONLY,
        "scopes": {"tenant": [], "user": ["task:comment:write"]},
    },
    "task_comment_list": {
        "identity": USER_ONLY,
        "scopes": {"tenant": [], "user": ["task:comment:read"]},
    },
    # ── Slides ───────────────────────────────────────────────────────
    "slides_upload_media": {
        "identity": BOTH,
        "scopes": {"tenant": ["drive:file:upload"], "user": ["drive:file:upload"]},
    },
}
