import re


class BlockToMarkdownConverter:
    """将飞书 docx block 树转换为标准 Markdown"""

    BLOCK_TYPES = {
        1: "page", 2: "text", 3: "heading1", 4: "heading2", 5: "heading3",
        6: "heading4", 7: "heading5", 8: "heading6", 9: "heading7",
        10: "heading8", 11: "heading9", 12: "bullet", 13: "ordered",
        14: "code", 15: "quote", 16: "divider", 17: "todo",
        18: "table_row", 19: "callout", 20: "table_cell",
        22: "table", 23: "file", 24: "grid", 25: "grid_column", 27: "image",
        31: "table", 32: "table_cell", 33: "view", 34: "quote_container",
        36: "okr", 37: "okr_objective", 38: "okr_key_result", 39: "okr_progress",
        43: "board", 50: "reference_synced",
    }

    HEADING_PREFIX = {
        3: "# ", 4: "## ", 5: "### ", 6: "#### ",
        7: "##### ", 8: "###### ", 9: "####### ",
        10: "######## ", 11: "######### ",
    }

    CODE_LANGUAGE_MAP = {
        1: "", 4: "apache", 7: "bash", 8: "csharp", 9: "cpp",
        10: "c", 12: "css", 13: "coffeescript", 14: "d", 15: "dart",
        16: "pascal", 18: "dockerfile", 19: "erlang", 20: "fortran",
        22: "go", 23: "groovy", 24: "html", 27: "haskell", 28: "json",
        29: "java", 30: "javascript", 31: "julia", 32: "kotlin",
        33: "latex", 34: "lisp", 36: "lua", 37: "matlab", 38: "makefile",
        39: "markdown", 40: "nginx", 41: "objectivec", 43: "php",
        44: "perl", 45: "postscript", 46: "powershell", 48: "protobuf",
        49: "python", 50: "r", 52: "ruby", 53: "rust", 54: "sas",
        56: "sql", 57: "scala", 58: "scheme", 60: "shell", 61: "swift",
        63: "typescript", 66: "xml", 67: "yaml",
    }

    BRAND_WEB_DOMAIN = {
        "feishu": "feishu.cn",
        "lark": "larksuite.com",
    }

    def __init__(self, blocks, media_map=None, brand="feishu"):
        self.blocks = blocks
        self.block_map = {b["block_id"]: b for b in blocks}
        self.children_map = {}
        for b in blocks:
            pid = b.get("parent_id", "")
            if pid:
                self.children_map.setdefault(pid, []).append(b)
        self.media_map = media_map or {}  # token -> relative path
        self.web_domain = self.BRAND_WEB_DOMAIN.get(brand, "feishu.cn")

    def convert(self):
        """转换整个 block 树为 Markdown 字符串"""
        lines = []
        root_blocks = [b for b in self.blocks if not b.get("parent_id")]
        for i, root in enumerate(root_blocks):
            root_lines = self._convert_block(root, 0)
            if i > 0 and lines and root_lines:
                lines.append("")
            lines.extend(root_lines)
        lines = self._post_process_lines(lines)
        return "\n".join(lines)

    @staticmethod
    def _post_process_lines(lines):
        """后处理：修复空行、递增有序列表序号"""
        if not lines:
            return lines
        result = []
        ordered_counter = 0
        for i, line in enumerate(lines):
            # 支持缩进的列表项检测
            is_bullet = bool(re.match(r'^(\s*)- ', line)) and not bool(re.match(r'^(\s*)- \[', line))
            is_ordered_raw = bool(re.match(r'^(\s*)\d+\. ', line))
            is_todo = bool(re.match(r'^(\s*)- \[', line))
            is_heading = line.startswith("#")
            is_code_fence = line.startswith("```")
            is_divider = line == "---"
            is_quote = line.startswith("> ")
            is_empty = line == ""
            # 图片、文件链接、表格、画板
            is_image = line.startswith("![") or line.startswith("<image ")
            is_table = line.startswith("|") and "|" in line[1:]
            is_link_only = bool(re.fullmatch(r'\[.*?\]\(.*?\)', line))
            is_board_link = line.startswith("[画板](")
            if is_ordered_raw:
                ordered_counter += 1
                line = f"{ordered_counter}. {line[3:]}"
            elif is_bullet or is_todo or is_heading:
                ordered_counter = 0
            is_ordered = is_ordered_raw
            is_list = is_bullet or is_ordered or is_todo
            is_media = is_image or is_link_only or is_board_link or is_table
            if i == 0 or not result:
                result.append(line)
                continue
            prev_line = result[-1]
            prev_is_empty = prev_line == ""
            if prev_is_empty or is_empty:
                result.append(line)
                continue
            prev_is_heading = prev_line.startswith("#")
            prev_is_code_fence = prev_line.startswith("```")
            prev_is_divider = prev_line == "---"
            prev_is_quote = prev_line.startswith("> ")
            prev_is_ordered = bool(re.match(r'^(\s*)\d+\. ', prev_line))
            prev_is_list = bool(re.match(r'^(\s*)- ', prev_line)) or prev_is_ordered
            prev_is_image = prev_line.startswith("![") or prev_line.startswith("<image ")
            prev_is_table = prev_line.startswith("|") and "|" in prev_line[1:]
            prev_is_link_only = bool(re.fullmatch(r'\[.*?\]\(.*?\)', prev_line))
            prev_is_board_link = prev_line.startswith("[画板](")
            prev_is_media = prev_is_image or prev_is_link_only or prev_is_board_link or prev_is_table
            need_blank = False
            if is_heading and not prev_is_heading:
                need_blank = True
            elif prev_is_heading and not is_heading:
                need_blank = True
            elif is_code_fence and not prev_is_code_fence:
                if line != "```":
                    need_blank = True
            elif prev_is_code_fence and not is_code_fence:
                if prev_line == "```":
                    need_blank = True
            elif is_divider:
                need_blank = True
            elif prev_is_divider:
                need_blank = True
            elif is_quote and not prev_is_quote:
                need_blank = True
            elif prev_is_quote and not is_quote:
                need_blank = True
            elif is_list and not prev_is_list:
                need_blank = True
            elif not is_list and prev_is_list and not is_heading:
                need_blank = True
            elif is_media and not prev_is_media:
                need_blank = True
            elif prev_is_media and not is_media:
                need_blank = True
            if need_blank:
                result.append("")
            result.append(line)
        return result

    def _convert_block(self, block, depth):
        """递归转换单个 block"""
        bt = block.get("block_type", 0)
        lines = []
        skip_children = False
        if bt == 1:
            pass
        elif bt in range(3, 12):
            text = self._extract_text_from_block(block)
            if text:
                prefix = self.HEADING_PREFIX.get(bt, "# ")
                lines.append(prefix + text)
        elif bt == 2:
            text = self._extract_text_from_block(block)
            if text:
                text_lines = text.split("\n")
                for i, ln in enumerate(text_lines):
                    if ln:
                        if i < len(text_lines) - 1:
                            lines.append(ln + "  ")  # Markdown 硬换行
                        else:
                            lines.append(ln)
        elif bt == 12:
            text = self._extract_text_from_block(block)
            if text:
                lines.append("- " + text)
            children = self.children_map.get(block.get("block_id"), [])
            for child in children:
                for cl in self._convert_block(child, depth + 1):
                    if cl:
                        lines.append("  " + cl)
            skip_children = True
        elif bt == 13:
            text = self._extract_text_from_block(block)
            if text:
                lines.append("1. " + text)
            children = self.children_map.get(block.get("block_id"), [])
            for child in children:
                for cl in self._convert_block(child, depth + 1):
                    if cl:
                        lines.append("  " + cl)
            skip_children = True
        elif bt == 14:
            lang = self._extract_code_language(block)
            text = self._extract_text_from_block(block)
            lines.append(f"```{lang}")
            code_lines = text.split("\n")
            if code_lines and code_lines[-1] == "":
                code_lines.pop(-1)
            for ln in code_lines:
                lines.append(ln)
            lines.append("```")
        elif bt == 15:
            text = self._extract_text_from_block(block)
            if text:
                for ln in text.split("\n"):
                    lines.append("> " + ln)
        elif bt == 16:
            lines.append("---")
        elif bt == 17:
            text = self._extract_text_from_block(block)
            checked = self._extract_todo_checked(block)
            marker = "[x]" if checked else "[ ]"
            if text:
                lines.append(f"- {marker} {text}")
            children = self.children_map.get(block.get("block_id"), [])
            for child in children:
                for cl in self._convert_block(child, depth + 1):
                    if cl:
                        lines.append("  " + cl)
            skip_children = True
        elif bt == 19:
            # callout：递归处理 children，每行加 > 前缀，行间插 > 空行
            children = self.children_map.get(block.get("block_id"), [])
            child_lines = []
            for child in children:
                child_lines.extend(self._convert_block(child, depth + 1))
            for i, line in enumerate(child_lines):
                if line:
                    lines.append("> " + line)
                else:
                    lines.append("> ")
                if i < len(child_lines) - 1:
                    lines.append("> ")
            skip_children = True
        elif bt == 22:
            table_lines = self._convert_table(block)
            lines.extend(table_lines)
        elif bt == 23:
            file_data = block.get("file", {})
            token = file_data.get("token", "")
            name = file_data.get("name", "unknown")
            if token in self.media_map:
                path = self.media_map[token]
                lines.append(f"[{name}]({path})")
            else:
                lines.append(f'<file token="{token}" name="{name}"/>')
        elif bt == 24:
            pass
        elif bt == 25:
            pass
        elif bt == 27:
            img_data = block.get("image", {})
            token = img_data.get("token", "")
            width = img_data.get("width")
            height = img_data.get("height")
            attr_str = ""
            if width:
                attr_str += f' width="{width}"'
            if height:
                attr_str += f' height="{height}"'
            if token in self.media_map:
                path = self.media_map[token]
                lines.append(f"![]({path})")
            else:
                lines.append(f'<image token="{token}"{attr_str}/>')
        elif bt == 31:
            # 新版 table（cells 直接内联，无 table_row）
            table_lines = self._convert_table_v2(block)
            lines.extend(table_lines)
            skip_children = True
        elif bt == 32:
            # table_cell（新版），children 已在外层递归处理，此处无需输出
            pass
        elif bt == 33:
            # 嵌入视图容器，children 递归处理，本身不输出额外标记
            pass
        elif bt == 34:
            # quote_container：递归处理 children，每行加 > 前缀
            children = self.children_map.get(block.get("block_id"), [])
            child_lines = []
            for child in children:
                child_lines.extend(self._convert_block(child, depth + 1))
            for line in child_lines:
                if line:
                    lines.append("> " + line)
                else:
                    lines.append("> ")
            skip_children = True
        elif bt == 36:
            # OKR 根容器，children 递归处理
            pass
        elif bt == 37:
            # OKR Objective
            text = self._extract_text_from_block(block)
            if text:
                lines.append(f"**O: {text}**")
        elif bt == 38:
            # OKR Key Result
            text = self._extract_text_from_block(block)
            if text:
                lines.append(f"- KR: {text}")
            children = self.children_map.get(block.get("block_id"), [])
            for child in children:
                for cl in self._convert_block(child, depth + 1):
                    if cl:
                        lines.append("  " + cl)
            skip_children = True
        elif bt == 39:
            # OKR Progress，children 递归处理
            pass
        elif bt == 43:
            board_data = block.get("board", {})
            token = board_data.get("token", "")
            if token in self.media_map:
                path = self.media_map[token]
                lines.append(f"![]({path})")
            elif token:
                lines.append(f'[画板](https://{self.web_domain}/board/{token})')
            else:
                lines.append('[画板]')
        elif bt == 50:
            ref_data = block.get("reference_synced", {})
            src_doc = ref_data.get("source_document_id", "")
            src_block = ref_data.get("source_block_id", "")
            lines.append(f'[跨文档引用](https://{self.web_domain}/docx/{src_doc}#block={src_block})')
        else:
            text = self._extract_text_from_block(block)
            if text:
                lines.append(text)
        child_lines = []
        if not skip_children:
            children = self.children_map.get(block.get("block_id"), [])
            for i, child in enumerate(children):
                child_block_lines = self._convert_block(child, depth + 1)
                if i > 0 and child_lines and child_block_lines:
                    # 连续列表项之间不插入空行
                    prev_is_list = any(
                        bool(re.match(r'^(\s*)- ', l) or re.match(r'^(\s*)\d+\. ', l))
                        for l in child_lines if l
                    )
                    curr_is_list = any(
                        bool(re.match(r'^(\s*)- ', l) or re.match(r'^(\s*)\d+\. ', l))
                        for l in child_block_lines if l
                    )
                    if not (prev_is_list and curr_is_list):
                        child_lines.append("")
                child_lines.extend(child_block_lines)
        if lines and child_lines:
            result = lines + [""] + child_lines
        elif lines:
            result = lines
        elif child_lines:
            result = child_lines
        else:
            result = []
        return result

    def _extract_text_from_block(self, block):
        """从 block 中提取纯文本（带 inline formatting）"""
        content_key = None
        for key in ["text", "heading1", "heading2", "heading3", "heading4",
                    "heading5", "heading6", "heading7", "heading8", "heading9",
                    "bullet", "ordered", "code", "quote", "callout", "todo"]:
            if key in block:
                content_key = key
                break
        if content_key:
            elements = block[content_key].get("elements", [])
            return self._extract_elements_text(elements)
        # OKR 组件的文本在 content.elements 中
        for key in ["okr_objective", "okr_key_result"]:
            if key in block:
                elements = block[key].get("content", {}).get("elements", [])
                return self._extract_elements_text(elements)
        return ""

    def _extract_elements_text(self, elements):
        """从 elements 数组中提取带格式的文本"""
        parts = []
        for elem in elements:
            if "text_run" in elem:
                content = elem["text_run"].get("content", "")
                style = elem["text_run"].get("text_element_style", {})
                content = self._apply_inline_style(content, style)
                parts.append(content)
            elif "mention_user" in elem:
                user_id = elem["mention_user"].get("user_id", "")
                parts.append(f"@user:{user_id}")
            elif "mention_doc" in elem:
                title = elem["mention_doc"].get("title", "")
                token = elem["mention_doc"].get("token", "")
                parts.append(f"[{title}](https://{self.web_domain}/docx/{token})")
            elif "link" in elem:
                text = elem["link"].get("text", "")
                url = elem["link"].get("url", "")
                parts.append(f"[{text}]({url})" if text else url)
            elif "equation" in elem:
                eq = elem["equation"].get("content", "")
                parts.append(f"${eq}$")
        return "".join(parts)

    @staticmethod
    def _apply_inline_style(content, style):
        """应用 inline formatting"""
        if style.get("bold"):
            content = f"**{content}**"
        if style.get("italic"):
            content = f"*{content}*"
        if style.get("inline_code"):
            content = f"`{content}`"
        if style.get("strikethrough"):
            content = f"~~{content}~~"
        if style.get("underline"):
            content = f"<u>{content}</u>"
        link = style.get("link")
        if link and link.get("url"):
            content = f"[{content}]({link['url']})"
        return content

    def _extract_code_language(self, block):
        """提取代码块语言（数字编码转语言名）"""
        code_data = block.get("code", {})
        lang = code_data.get("style", {}).get("language", "")
        if isinstance(lang, int):
            return self.CODE_LANGUAGE_MAP.get(lang, "")
        return str(lang)

    def _extract_todo_checked(self, block):
        """提取 todo 完成状态"""
        todo_data = block.get("todo", {})
        return todo_data.get("style", {}).get("checked", False)

    def _convert_table(self, block):
        """将表格 block 转换为 Markdown 表格"""
        lines = []
        table_data = block.get("table", {})
        prop = table_data.get("property", {})
        row_size = prop.get("row_size", 0)
        col_size = prop.get("column_size", 0)
        header_row = prop.get("header_row", False)
        row_ids = block.get("children", [])
        rows = []
        for row_id in row_ids:
            row_block = self.block_map.get(row_id)
            if not row_block:
                continue
            cell_ids = row_block.get("children", [])
            cells = []
            for cell_id in cell_ids:
                cell_block = self.block_map.get(cell_id)
                if not cell_block:
                    continue
                content_ids = cell_block.get("children", [])
                cell_texts = []
                for cid in content_ids:
                    cblock = self.block_map.get(cid)
                    if cblock:
                        text = self._extract_text_from_block(cblock)
                        if text:
                            cell_texts.append(text)
                cells.append(" ".join(cell_texts))
            rows.append(cells)
        if not rows:
            return lines
        for i, row in enumerate(rows):
            while len(row) < col_size:
                row.append("")
            lines.append("| " + " | ".join(row) + " |")
            if i == 0 and header_row:
                lines.append("| " + " | ".join(["---"] * col_size) + " |")
        return lines

    def _convert_table_v2(self, block):
        """将新版 table（block_type=31）转换为 Markdown 表格

        新版 table 的 children 直接是 table_cell（32），没有 table_row 层。
        cells 按行优先排列在 table.cells 中。
        """
        lines = []
        table_data = block.get("table", {})
        prop = table_data.get("property", {})
        row_size = prop.get("row_size", 0)
        col_size = prop.get("column_size", 0)
        header_row = prop.get("header_row", False)
        cell_ids = table_data.get("cells", block.get("children", []))
        if not cell_ids:
            return lines

        rows = []
        for i in range(row_size):
            row_cells = []
            start = i * col_size
            end = start + col_size
            for cell_id in cell_ids[start:end]:
                cell_block = self.block_map.get(cell_id)
                if not cell_block:
                    row_cells.append("")
                    continue
                content_ids = cell_block.get("children", [])
                cell_texts = []
                for cid in content_ids:
                    cblock = self.block_map.get(cid)
                    if cblock:
                        text = self._extract_text_from_block(cblock)
                        if text:
                            cell_texts.append(text)
                row_cells.append(" ".join(cell_texts))
            rows.append(row_cells)

        if not rows:
            return lines
        for i, row in enumerate(rows):
            while len(row) < col_size:
                row.append("")
            lines.append("| " + " | ".join(row) + " |")
            if i == 0 and header_row:
                lines.append("| " + " | ".join(["---"] * col_size) + " |")
        return lines


class MediaExtractor:
    """从 block 树中提取媒体资源清单"""

    @staticmethod
    def extract(blocks):
        """返回媒体资源列表"""
        media = []
        for block in blocks:
            bt = block.get("block_type", 0)
            if bt == 27:
                img = block.get("image", {})
                token = img.get("token", "")
                if token:
                    media.append({
                        "type": "image", "token": token,
                        "width": img.get("width"), "height": img.get("height"),
                        "block_id": block.get("block_id"),
                    })
            elif bt == 23:
                file_data = block.get("file", {})
                token = file_data.get("token", "")
                if token:
                    media.append({
                        "type": "file", "token": token,
                        "name": file_data.get("name", "unknown"),
                        "block_id": block.get("block_id"),
                    })
            elif bt == 43:
                board_data = block.get("board", {})
                token = board_data.get("token", "")
                if token:
                    media.append({
                        "type": "board", "token": token,
                        "block_id": block.get("block_id"),
                    })
        return media
