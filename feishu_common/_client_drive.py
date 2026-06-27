#!/usr/bin/env python3
"""_client_drive.py -- 云空间相关 API mixin。"""

import mimetypes
import os
import re
import sys
import time
import urllib.parse
from pathlib import Path

from ._client_core import DEFAULT_TIMEOUT
from ._config_loader import DEFAULT_FOLDER_TOKEN

class DriveMixin:
    def list_files(self, folder_token=None, page_size=200, max_results=None):
        """列出文件夹文件（自动分页）"""
        extra_query = {"folder_token": folder_token} if folder_token else None
        return self._paginate(
            "GET", "/open-apis/drive/v1/files",
            items_key="files", page_token_key="next_page_token",
            page_size=page_size, max_results=max_results,
            extra_query=extra_query,
        )
    
    def search_files(self, query, folder_token=None, page_size=200):
        """搜索 drive 文件（客户端按名称过滤）"""
        files = self.list_files(folder_token=folder_token, page_size=page_size)
        if query:
            query_lower = query.lower()
            files = [
                f for f in files
                if query_lower in f.get("name", "").lower()
                or query_lower in f.get("type", "").lower()
                or query_lower in f.get("token", "").lower()
            ]
        return {"files": files, "total": len(files), "query": query or ""}
    
    def copy_file(self, file_token, name, file_type, folder_token):
        """复制文件到目标文件夹"""
        body = {"name": name, "type": file_type, "folder_token": folder_token}
        data = self._request("POST", f"/open-apis/drive/v1/files/{file_token}/copy", body=body)
        return data.get("file", {})
    
    def upload_file(self, file_path, folder_token=None, parent_type=None, parent_node=None):
        """上传文件到云空间（小文件，单分片上传）
    
        Args:
            file_path: 本地文件路径
            folder_token: 目标文件夹 token（parent_type=explorer 时生效）
            parent_type: 上传目标类型，如 "explorer"（云空间）或 "bitable_file"（多维表格）
            parent_node: 上传目标节点，如文件夹 token 或多维表格 app_token
        """
        path = Path(file_path)
        if not path.exists():
            raise RuntimeError(f"File not found: {file_path}")
        file_data = path.read_bytes()
        filename = path.name
        content_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        boundary = "----LarkDriveBoundary" + os.urandom(8).hex()
        pt = parent_type or "explorer"
        pn = parent_node or (folder_token or DEFAULT_FOLDER_TOKEN)
        size_str = str(len(file_data))
    
        parts = [
            f"--{boundary}".encode(),
            b'Content-Disposition: form-data; name="file_name"',
            b"",
            filename.encode("utf-8"),
            f"--{boundary}".encode(),
            b'Content-Disposition: form-data; name="parent_type"',
            b"",
            pt.encode(),
            f"--{boundary}".encode(),
            b'Content-Disposition: form-data; name="parent_node"',
            b"",
            pn.encode("utf-8"),
            f"--{boundary}".encode(),
            b'Content-Disposition: form-data; name="size"',
            b"",
            size_str.encode("utf-8"),
            f"--{boundary}".encode(),
            f'Content-Disposition: form-data; name="file"; filename="{filename}"'.encode("utf-8"),
            f"Content-Type: {content_type}".encode(),
            b"",
            file_data,
            f"--{boundary}--".encode(),
        ]
        body = b"\r\n".join(parts)
        headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
        data = self._request("POST", "/open-apis/drive/v1/files/upload_all", body=body, headers=headers)
        return data
    
    def move_file(self, file_token, file_type, target_folder_token):
        """移动文件到目标文件夹"""
        body = {"type": file_type, "folder_token": target_folder_token}
        data = self._request("PUT", f"/open-apis/drive/v1/files/{file_token}/move", body=body)
        return data.get("file", {})
    
    def delete_file(self, file_token, file_type):
        """删除文件或文件夹"""
        self._request("DELETE", f"/open-apis/drive/v1/files/{file_token}", query={"type": file_type})
        return {"deleted": True, "file_token": file_token}
    
    def create_folder(self, name, folder_token=None):
        """创建云文档文件夹
    
        Args:
            name: 文件夹名称
            folder_token: 父文件夹 token，不传则使用默认文件夹
        """
        body = {"name": name}
        if folder_token:
            body["folder_token"] = folder_token
        data = self._request("POST", "/open-apis/drive/v1/files/create_folder", body=body)
        return data
    
    @staticmethod
    def _parse_filename_from_content_disposition(content_disp):
        """解析 Content-Disposition header 中的文件名
    
        优先 RFC 5987 的 filename*=UTF-8''...，回退到 filename="..."
        """
        if not content_disp:
            return None
        # 1. 尝试 filename*=UTF-8''...（RFC 5987）
        for prefix in ("filename*=UTF-8''", "filename*=utf-8''"):
            if prefix in content_disp:
                encoded = content_disp.split(prefix, 1)[1].split(";")[0].strip()
                try:
                    return urllib.parse.unquote(encoded)
                except Exception:
                    pass
        # 2. 尝试 filename="..."
        import re
        m = re.search(r'filename\s*=\s*"([^"]*)"', content_disp)
        if m:
            return m.group(1)
        # 3. 尝试 filename=...（无引号）
        m = re.search(r'filename\s*=\s*([^;\s]+)', content_disp)
        if m:
            return m.group(1).strip('"')
        return None
    
    def download_file(self, file_token, save_path):
        """下载普通文件（file 类型，如 pdf/xlsx）"""
        path = f"/open-apis/drive/v1/files/{file_token}/download"
        try:
            resp = self._request_raw("GET", path)
        except RuntimeError as e:
            if "HTTP 404" in str(e):
                raise RuntimeError(
                    "HTTP 404: File not found or file type not supported for direct download. "
                    "Docx/doc files cannot be downloaded directly. Use doc_fetch.py for docx export."
                ) from e
            raise
        content_disp = resp.headers.get("Content-Disposition", "")
        filename = self._parse_filename_from_content_disposition(content_disp)
        save = Path(save_path)
        if save.is_dir():
            save = save / (filename or file_token)
        save.parent.mkdir(parents=True, exist_ok=True)
        with open(save, "wb") as f:
            f.write(resp.read())
        return str(save)
    
    def download_media(self, media_token, save_path, progress=True):
        """下载文档媒体文件（图片、文件块等）

        优先尝试 /medias/ 路径，403 时回退到 /files/ 路径。
        大文件自动延长超时，支持流式下载进度打印。
        """
        paths = [
            f"/open-apis/drive/v1/medias/{media_token}/download",
            f"/open-apis/drive/v1/files/{media_token}/download",
        ]

        # 先 HEAD 预检文件大小，用于计算动态超时
        total_size = 0
        for path in paths:
            try:
                head_resp = self._request_raw("HEAD", path)
                total_size = int(head_resp.headers.get("Content-Length", 0))
                break
            except RuntimeError as e:
                err_msg = str(e)
                if "HTTP 404" in err_msg or "HTTP 405" in err_msg:
                    continue
                raise
            except Exception:
                break

        # 动态超时：按文件大小估算（每 MB 5 秒，最少 30 秒）
        timeout = max(DEFAULT_TIMEOUT, total_size // (1024 * 1024) * 5)

        last_error = None
        resp = None
        for path in paths:
            try:
                resp = self._request_raw("GET", path)
                break
            except RuntimeError as e:
                last_error = e
                if "HTTP 404" in str(e):
                    continue
                raise
        else:
            if last_error and "HTTP 404" in str(last_error):
                raise RuntimeError(
                    "HTTP 404: Media not found. The media token may be invalid, "
                    "or the media was inserted via external URL (no token)."
                ) from last_error
            raise last_error

        content_disp = resp.headers.get("Content-Disposition", "")
        filename = self._parse_filename_from_content_disposition(content_disp)
        if not filename:
            ct = resp.headers.get("Content-Type", "")
            if "image" in ct:
                ext = ct.split("/")[-1] if "/" in ct else "png"
                filename = f"{media_token}.{ext}"
            else:
                filename = media_token
        save = Path(save_path)
        if save.is_dir():
            save = save / filename
        save.parent.mkdir(parents=True, exist_ok=True)

        # 如果 HEAD 没拿到大小，从 GET 响应再补一次
        if total_size == 0:
            total_size = int(resp.headers.get("Content-Length", 0))

        chunk_size = 64 * 1024
        downloaded = 0
        last_pct = -1
        with open(save, "wb") as f:
            while True:
                chunk = resp.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if progress and total_size > 0:
                    pct = int(downloaded * 100 / total_size)
                    if pct != last_pct and pct % 10 == 0:
                        print(f"  {pct}%", file=sys.stderr)
                        last_pct = pct
                elif progress and total_size == 0:
                    # 无 Content-Length 时按每 10 MB 打印
                    if downloaded % (10 * 1024 * 1024) < chunk_size:
                        mb = downloaded / (1024 * 1024)
                        print(f"  {mb:.1f} MB", file=sys.stderr)
        if progress:
            print("  done", file=sys.stderr)
        return str(save)
    
    def download_board(self, board_token, save_path, progress=True):
        """下载画板（board/whiteboard）为图片

        调用飞书官方画板下载接口 /board/v1/whiteboards/{token}/download_as_image
        返回二进制图片流，根据 Content-Type 推断格式（jpeg/png）。
        下载后会自动裁剪掉边缘空白，适配内容实际尺寸。
        """
        path = f"/open-apis/board/v1/whiteboards/{board_token}/download_as_image"
        try:
            resp = self._request_raw("GET", path)
        except RuntimeError as e:
            err_msg = str(e)
            if "HTTP 403" in err_msg:
                raise RuntimeError(
                    "HTTP 403: Permission denied to download board image. "
                    "Ensure the app has 'board:whiteboard:node:read' scope."
                ) from e
            if "HTTP 404" in err_msg:
                raise RuntimeError("HTTP 404: Board not found or export not supported.") from e
            raise

        ct = resp.headers.get("Content-Type", "image/jpeg")
        ext = "jpg"
        if "png" in ct:
            ext = "png"
        elif "jpeg" in ct or "jpg" in ct:
            ext = "jpg"
    
        save = Path(save_path)
        if save.is_dir():
            save = save / f"{board_token}.{ext}"
        save.parent.mkdir(parents=True, exist_ok=True)
    
        # 流式读取并打印进度
        total_size = int(resp.headers.get("Content-Length", 0))
        chunk_size = 64 * 1024
        downloaded = 0
        chunks = []
        last_pct = -1
        while True:
            chunk = resp.read(chunk_size)
            if not chunk:
                break
            chunks.append(chunk)
            downloaded += len(chunk)
            if progress and total_size > 0:
                pct = int(downloaded * 100 / total_size)
                if pct != last_pct and pct % 10 == 0:
                    print(f"  {pct}%", file=sys.stderr)
                    last_pct = pct
            elif progress and total_size == 0:
                if downloaded % (10 * 1024 * 1024) < chunk_size:
                    mb = downloaded / (1024 * 1024)
                    print(f"  {mb:.1f} MB", file=sys.stderr)
        raw_data = b"".join(chunks)
        if progress:
            print("  done", file=sys.stderr)
    
        # 自动裁剪边缘空白（仅依赖 Pillow，无 numpy）
        try:
            from PIL import Image
            import io
    
            img = Image.open(io.BytesIO(raw_data))
            gray = img.convert("L")
            bg = gray.getpixel((0, 0))
    
            # 二值化：接近背景色的像素置黑，其他置白，再取内容边界
            threshold = 20
            binary = gray.point(lambda p: 0 if abs(p - bg) < threshold else 255)
            bbox = binary.getbbox()
            if not bbox:
                with open(save, "wb") as f:
                    f.write(raw_data)
                return str(save)
    
            # 加 padding 裁剪
            padding = 20
            w, h = img.size
            left = max(0, bbox[0] - padding)
            top = max(0, bbox[1] - padding)
            right = min(w, bbox[2] + padding)
            bottom = min(h, bbox[3] + padding)
    
            img.crop((left, top, right, bottom)).save(save, quality=95)
            return str(save)
        except Exception:
            # Pillow 未安装或裁剪失败时保留原图
            with open(save, "wb") as f:
                f.write(raw_data)
            return str(save)
    
    
    def drive_create_export_task(self, token, doc_type, file_extension, sub_id=None):
        """创建导出任务，返回 ticket"""
        body = {"token": token, "type": doc_type, "file_extension": file_extension}
        if sub_id:
            body["sub_id"] = sub_id
        data = self._request("POST", "/open-apis/drive/v1/export_tasks", body=body)
        return data.get("ticket")
    
    def drive_get_export_task(self, ticket, token):
        """查询导出任务状态"""
        data = self._request("GET", f"/open-apis/drive/v1/export_tasks/{ticket}", query={"token": token})
        return data.get("result", {})
    
    def drive_export_download(self, file_token, save_path):
        """下载导出完成的文件"""
        url = f"{self.base_url}/open-apis/drive/v1/export_tasks/file/{file_token}/download"
        return self._download_url(url, save_path, method_name="drive_export_download")
    
    def drive_export(self, token, doc_type, file_extension, sub_id=None, output_path=None, max_attempts=30, poll_interval=2):
        """导出文件并下载到本地（含轮询）
    
        Args:
            token: 文档 token
            doc_type: 文档类型 (doc/docx/sheet/bitable)
            file_extension: 导出格式 (docx/pdf/xlsx/csv/markdown)
            sub_id: sheet/bitable 导出 csv 时需要的子表 ID
            output_path: 本地保存路径（默认使用导出文件名）
            max_attempts: 最大轮询次数（默认 30）
            poll_interval: 轮询间隔秒数（默认 2）
        """
        import time, os
    
        ticket = self.drive_create_export_task(token, doc_type, file_extension, sub_id)
    
        for attempt in range(1, max_attempts + 1):
            result = self.drive_get_export_task(ticket, token)
            status = result.get("job_status", 0)
    
            if status == 0 and result.get("file_token"):
                file_token = result["file_token"]
                file_name = result.get("file_name", f"{token}.{file_extension}")
                save_path = output_path or file_name
                self.drive_export_download(file_token, save_path)
                return {
                    "saved_path": save_path,
                    "file_name": os.path.basename(save_path),
                    "file_token": file_token,
                    "ticket": ticket,
                    "file_size": result.get("file_size", 0),
                }
            elif status in (1, 2):
                time.sleep(poll_interval)
            else:
                error_msg = result.get("job_error_msg", f"export failed with status {status}")
                raise RuntimeError(f"Export failed: {error_msg} (ticket={ticket})")
    
        raise RuntimeError(f"Export timed out after {max_attempts} attempts (ticket={ticket})")
    
