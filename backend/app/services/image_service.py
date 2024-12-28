# type: ignore[import]
import mimetypes
import os
import uuid
from pathlib import Path
from typing import Optional

from app.config import settings
from app.database.models import Image
from app.models import FileInfo, Image
from app.utils.image_utils import ImageProcessor
from app.utils.logger import logger
from PIL import Image as PILImage
from pillow_heif import register_heif_opener
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

    async def process_image(self, file_info: FileInfo, folder_id: int) -> bool:
        """处理单个图片文件"""
        try:
            # 检查文件是否已存在
            existing = self.db.query(Image).filter(
                Image.file_path == file_info.full_path).first()
            if existing:
                return True

            # 创建图片记录
            image = Image(folder_id=folder_id,
                          file_path=file_info.full_path,
                          mime_type=file_info.mime_type,
                          image_type=self._get_image_type(file_info.full_path),
                          created_at=file_info.created_at,
                          exif_data=self.processor.get_exif_data(
                              file_info.full_path))

            self.db.add(image)
            self.db.flush()

            # 处理图片文件
            if file_info.mime_type and (
                    file_info.mime_type.startswith('image/')
                    or file_info.mime_type.startswith('video/')):
                # 处理HEIF/HEIC文件
                if file_info.full_path.lower().endswith(('.heic', '.heif')):
                    converted_path = await self._handle_heif_conversion(
                        file_info, image)
                    if converted_path:
                        image.converted_path = converted_path

                # 生成缩略图
                thumb_path = await self._handle_thumbnail_creation(
                    file_info, image)
                if thumb_path:
                    image.thumbnail_path = thumb_path

                self.db.refresh(image)
                self.db.commit()

            return True

        except Exception as e:
            logger.error(f"处理图片失败 {file_info.full_path}: {str(e)}")
            self.db.rollback()
            return False

    async def _handle_heif_conversion(self, file_info: FileInfo,
                                      image: Image) -> Optional[str]:
        """处理HEIF/HEIC转换"""
        try:
            # 保持原始目录结构
            rel_dir = os.path.dirname(file_info.rel_path)
            file_name = f"{Path(file_info.full_path).stem}_{uuid.uuid4().hex[:8]}.jpg"
            rel_path = os.path.join(rel_dir, file_name)
            full_path = os.path.join(settings.CONVERTED_DIR, rel_path)

            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            await self.processor.convert_heic(file_info.full_path, full_path)

            # 保存完整路径
            image.converted_path = full_path  # 使用完整路径
            self.db.add(image)
            self.db.flush()

            return full_path
        except Exception as e:
            logger.error(f"HEIF转换失败 {file_info.rel_path}: {str(e)}")
            return None

    async def _handle_thumbnail_creation(self, file_info: FileInfo,
                                         image: Image) -> Optional[str]:
        """处理缩略图生成"""
        try:
            rel_dir = os.path.dirname(file_info.rel_path)
            file_name = f"{Path(file_info.full_path).stem}_{uuid.uuid4().hex[:8]}_thumb.jpg"
            rel_path = os.path.join(rel_dir, file_name)
            full_path = os.path.join(settings.THUMBNAIL_DIR, rel_path)

            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            await self.processor.create_thumbnail(file_info.full_path,
                                                  full_path)

            # 保存完整路径并更新数据库
            image.thumbnail_path = full_path
            self.db.add(image)
            self.db.flush()

            return full_path
        except Exception as e:
            logger.error(f"缩略图生成失败 {file_info.rel_path}: {str(e)}")
            return None

    def _get_image_type(self, file_path: str) -> str:
        """获取图片类型"""
        ext = os.path.splitext(file_path)[1].lower()
        if ext in ('.jpg', '.jpeg'):
            return 'jpeg'
        elif ext == '.png':
            return 'png'
        elif ext == '.gif':
            return 'gif'
        elif ext in ('.heic', '.heif'):
            return 'heif'
        else:
            return 'unknown'
