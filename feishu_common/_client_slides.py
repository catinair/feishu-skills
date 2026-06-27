#!/usr/bin/env python3
"""_client_slides.py -- 幻灯片相关 API mixin。"""

class SlidesMixin:
    
    def slides_upload_media(self, file_path, presentation_token):
        """上传媒体文件到幻灯片
    
        Args:
            file_path: 本地文件路径（最大 20MB）
            presentation_token: 幻灯片 token
        """
        upload_result = self.upload_file(file_path, parent_type="slide_file", parent_node=presentation_token)
        return upload_result
