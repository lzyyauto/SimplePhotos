import mimetypes
import os
import uuid
from pathlib import Path
from typing import Optional

from app.config import settings
from app.database.models import Image
from app.models import FileInfo
from app.utils.image_utils import ImageProcessor
from app.utils.logger import logger
from sqlalchemy.orm import Session


class ImageService:

    def __init__(self, db: Session):
        self.db = db
        self.processor = ImageProcessor()
        self._setup_cache_dirs()

    def _setup_cache_dirs(self):
        """确保缓存目录存在"""
        os.makedirs(settings.THUMBNAIL_DIR, exist_ok=True)
        os.makedirs(settings.CONVERTED_DIR, exist_ok=True)

    async def get_image(self, image_id: int) -> Optional[Image]:
        """根据 ID 获取图片记录"""
        return self.db.query(Image).filter(Image.id == image_id).first()

    async def process_image(self, file_info: FileInfo, folder_id: int) -> bool:
        """处理单个图片/视频文件，生成缩略图和 HEIC 转换文件"""
        try:
            # 幂等：文件已存在则跳过（使用相对路径去重）
            existing = self.db.query(Image).filter(
                Image.file_path == file_info.rel_path
            ).first()
            if existing:
                return True

            is_heic = file_info.full_path.lower().endswith((".heic", ".heif"))

            image = Image(
                folder_id=folder_id,
                file_path=file_info.rel_path,  # 存相对路径，跨部署可移植
                mime_type=file_info.mime_type,
                image_type=self._get_image_type(file_info.full_path),
                is_heic=is_heic,  # 正确设置 is_heic 字段
                created_at=file_info.created_at,
                exif_data=self.processor.get_exif_data(file_info.full_path),
            )

            self.db.add(image)
            self.db.flush()  # 获取 image.id，不提交事务

            is_media = file_info.mime_type and (
                file_info.mime_type.startswith("image/")
                or file_info.mime_type.startswith("video/")
            )

            if is_media:
                # HEIC 转换为 JPEG
                if is_heic:
                    converted_path = await self._handle_heif_conversion(file_info)
                    if converted_path:
                        # 存相对于 CONVERTED_DIR 的路径
                        image.converted_path = os.path.relpath(
                            converted_path, settings.CONVERTED_DIR
                        )

                # 生成缩略图
                thumb_path = await self._handle_thumbnail_creation(file_info)
                if thumb_path:
                    # 存相对于 THUMBNAIL_DIR 的路径
                    image.thumbnail_path = os.path.relpath(
                        thumb_path, settings.THUMBNAIL_DIR
                    )

            # flush 更新缩略图路径，由外层 chunk 来 commit，避免双重提交
            self.db.flush()
            return True

        except Exception as e:
            logger.error(f"处理图片失败 {file_info.full_path}: {str(e)}")
            self.db.rollback()
            return False

    def _get_cache_path(self, file_info: FileInfo, base_dir: Path | str, suffix: str) -> str:
        rel_dir = os.path.dirname(file_info.rel_path)
        file_name = f"{Path(file_info.full_path).stem}_{uuid.uuid4().hex[:8]}{suffix}"
        full_path = os.path.join(base_dir, rel_dir, file_name)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        return full_path

    async def _handle_heif_conversion(self, file_info: FileInfo) -> Optional[str]:
        """HEIC/HEIF → JPEG 转换，保持目录结构"""
        try:
            full_path = self._get_cache_path(file_info, settings.CONVERTED_DIR, ".jpg")
            await self.processor.convert_heic(file_info.full_path, full_path)
            return full_path
        except Exception as e:
            logger.error(f"HEIF转换失败 {file_info.rel_path}: {str(e)}")
            return None

    async def _handle_thumbnail_creation(self, file_info: FileInfo) -> Optional[str]:
        """生成缩略图，保持目录结构"""
        try:
            full_path = self._get_cache_path(file_info, settings.THUMBNAIL_DIR, "_thumb.jpg")
            await self.processor.create_thumbnail(file_info.full_path, full_path)
            return full_path
        except Exception as e:
            logger.error(f"缩略图生成失败 {file_info.rel_path}: {str(e)}")
            return None

    def _get_image_type(self, file_path: str) -> str:
        """根据扩展名判断文件类型"""
        ext = os.path.splitext(file_path)[1].lower()
        type_map = {
            ".jpg": "jpeg", ".jpeg": "jpeg",
            ".png": "png",
            ".gif": "gif",
            ".webp": "webp",
            ".heic": "heif", ".heif": "heif",
            ".mp4": "video", ".mov": "video",
        }
        return type_map.get(ext, "unknown")
