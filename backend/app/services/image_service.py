import mimetypes
import os
import uuid
from pathlib import Path
from typing import Optional

from app.config import settings
from app.database.models import Image
from app.utils.image_utils import ImageProcessor
from app.utils.logger import logger
from PIL import Image as PILImage
from PIL.ExifTags import TAGS
from sqlalchemy.orm import Session


class ImageService:

    def __init__(self, db: Session):
        self.db = db
        self.processor = ImageProcessor()
        self.failed_images = []  # 记录处理失败的图片

    async def process_image(self, file_path: str, folder_id: int) -> bool:
        try:
            # 检查文件是否存在且可读
            if not os.path.exists(file_path) or os.path.getsize(
                    file_path) == 0:
                raise ValueError(f"文件不存在或为空: {file_path}")

            # 检查是否已存在
            existing_image = self.db.query(Image).filter(
                Image.file_path == file_path).first()
            if existing_image:
                return True

            # 获取 MIME 类型
            mime_type = self._get_image_type(file_path)
            if not mime_type:
                raise ValueError(f"不支持的图片类型: {file_path}")

            # 处理 HEIC 图片
            is_heic = file_path.lower().endswith(('.heic', '.heif'))
            converted_path = None
            if is_heic:
                converted_path = await self._convert_heic(file_path)

            # 生成缩略图
            thumbnail_path = await self._create_thumbnail(file_path)

            # 读取 EXIF 数据
            exif_data = self._get_exif_data(file_path)
            logger.debug(f"读取到 EXIF 数据: {len(exif_data)} 个字段")

            # 创建图片记录
            image = Image(file_path=file_path,
                          folder_id=folder_id,
                          image_type='original',
                          mime_type=mime_type,
                          is_heic=is_heic,
                          converted_path=converted_path,
                          thumbnail_path=thumbnail_path,
                          exif_data=exif_data,
                          is_thumbnail=False)
            self.db.add(image)
            self.db.commit()
            return True

        except Exception as e:
            self.db.rollback()
            self.failed_images.append((file_path, str(e)))
            logger.error(f"处理图片失败: {file_path}, 错误: {str(e)}")
            return False

    async def _create_thumbnail(self, file_path: str) -> str:
        """创建缩略图"""
        try:
            # 生成缩略图文件名
            file_name = Path(file_path).stem
            thumb_name = f"{file_name}_{os.urandom(4).hex()}_thumb.jpg"
            thumb_path = os.path.join(settings.THUMBNAIL_DIR, thumb_name)

            # 创建缩略图
            with PILImage.open(file_path) as img:
                # 转换为 RGB 模式（处理 RGBA 图片）
                if img.mode in ('RGBA', 'LA'):
                    background = PILImage.new('RGB', img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[-1])
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')

                # 生成缩略图
                img.thumbnail(settings.THUMBNAIL_SIZE)
                img.save(thumb_path, 'JPEG', quality=85)

            return thumb_path

        except Exception as e:
            logger.error(f"创建缩略图失败: {file_path}, 错误: {str(e)}")
            return None

    async def _convert_heic(self, file_path: str) -> str:
        """转换 HEIC 图片"""
        try:
            from pillow_heif import register_heif_opener
            register_heif_opener()

            # 生成转换后的文件名
            file_name = Path(file_path).stem
            converted_name = f"{file_name}_{os.urandom(4).hex()}_converted.jpg"
            converted_path = os.path.join(settings.CONVERTED_DIR,
                                          converted_name)

            # 转换图片
            with PILImage.open(file_path) as img:
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                img.save(converted_path, 'JPEG', quality=95)

            return converted_path

        except Exception as e:
            logger.error(f"转换 HEIC 失败: {file_path}, 错误: {str(e)}")
            return None

    def _get_image_type(self, file_path: str) -> str:
        """获取图片的 MIME 类型"""
        try:
            mime_type, _ = mimetypes.guess_type(file_path)
            if mime_type and mime_type.startswith('image/'):
                return mime_type

            with PILImage.open(file_path) as img:
                if img.format:
                    return f"image/{img.format.lower()}"

            return "image/unknown"
        except Exception:
            return "image/unknown"

    async def get_image(self, image_id: int) -> Optional[Image]:
        """获取图片信息"""
        logger.info(f"获取图片信息: ID={image_id}")
        return self.db.query(Image).filter(Image.id == image_id).first()

    async def delete_image(self, image_id: int) -> bool:
        """删除图片记录及相关文件"""
        logger.info(f"删除图片: ID={image_id}")
        image = await self.get_image(image_id)
        if not image:
            logger.warning(f"图片不存在: ID={image_id}")
            return False

        # 删除缓存文件
        if os.path.exists(image.thumbnail_path):
            os.remove(image.thumbnail_path)
        if image.converted_path and os.path.exists(image.converted_path):
            os.remove(image.converted_path)

        # 删除数据库记录
        self.db.delete(image)
        self.db.commit()

        logger.info(f"图片删除完成: ID={image_id}")
        return True

    def _get_exif_data(self, file_path: str) -> dict:
        """读取图片的 EXIF 数据"""
        try:
            with PILImage.open(file_path) as img:
                exif = img.getexif()
                if not exif:
                    return {}

                exif_data = {}
                for tag_id in exif:
                    try:
                        tag = TAGS.get(tag_id, tag_id)
                        value = exif.get(tag_id)
                        # 确保值是可序列化的
                        if isinstance(value, bytes):
                            value = value.decode(errors='ignore')
                        elif hasattr(value, '_asdict'):
                            value = value._asdict()
                        exif_data[str(tag)] = str(value)
                    except Exception as e:
                        logger.warning(f"处理 EXIF 标签 {tag_id} 失败: {str(e)}")
                        continue

                logger.debug(f"成功读取 EXIF 数据: {file_path}")
                return exif_data

        except Exception as e:
            logger.error(f"读取 EXIF 失败: {file_path}, 错误: {str(e)}")
            return {}
