import os
import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.config import settings
from app.database.models import Image
from app.utils.image_utils import ImageProcessor
from app.utils.logger import logger


class ImageService:

    def __init__(self, db: Session):
        self.db = db
        self.processor = ImageProcessor()

    async def process_image(self,
                            file_path: str,
                            folder_id: int,
                            image_type: str = 'original',
                            parent_id: int = None) -> Optional[Image]:
        """处理单个图片文件"""
        try:
            logger.info(f"开始处理图片: {file_path}")

            # 生成唯一的文件名
            file_name = os.path.basename(file_path)
            name, ext = os.path.splitext(file_name)
            unique_id = str(uuid.uuid4())[:8]

            # 初始化路径变量
            thumbnail_path = None
            converted_path = None

            # 根据图片类型设置路径 (统一使用 jpg 作为缩略图格式)
            if image_type == 'thumbnail':
                thumbnail_name = f"{name}_{unique_id}_thumb.jpg"  # 强制使用 jpg
                thumbnail_path = os.path.join(settings.THUMBNAIL_DIR,
                                              thumbnail_name)
            elif image_type == 'converted':
                converted_name = f"{name}_{unique_id}_converted.jpg"
                converted_path = os.path.join(settings.CONVERTED_DIR,
                                              converted_name)

            # 检查是否是HEIC文件
            is_heic = file_path.lower().endswith(('.heic', '.heif'))

            if is_heic:
                logger.info(f"转换HEIC文件: {file_path}")
                if not converted_path:
                    converted_name = f"{name}_{unique_id}_converted.jpg"
                    converted_path = os.path.join(settings.CONVERTED_DIR,
                                                  converted_name)
                await self.processor.convert_heic(file_path, converted_path)

            # 生成缩略图（如果还没有设置缩略图路径）
            if not thumbnail_path:
                thumbnail_name = f"{name}_{unique_id}_thumb.jpg"  # 强制使用 jpg
                thumbnail_path = os.path.join(settings.THUMBNAIL_DIR,
                                              thumbnail_name)

            # 创建缩略图
            logger.info(f"生成缩略图: {thumbnail_path}")
            source_path = converted_path if is_heic else file_path
            await self.processor.create_thumbnail(source_path, thumbnail_path)

            # 读取EXIF数据
            logger.info(f"读取EXIF数据: {file_path}")
            exif_data = self.processor.get_exif_data(file_path)

            # 创建数据库记录
            image = Image(file_path=file_path,
                          thumbnail_path=thumbnail_path,
                          exif_data=exif_data,
                          is_heic=is_heic,
                          converted_path=converted_path,
                          folder_id=folder_id,
                          image_type=image_type,
                          parent_id=parent_id)

            self.db.add(image)
            self.db.commit()
            self.db.refresh(image)

            logger.info(f"图片处理完成: {file_path}")
            return image

        except Exception as e:
            logger.error(f"处理图片失败: {file_path}, 错误: {str(e)}")
            self.db.rollback()
            raise e

    async def get_image(self, image_id: int) -> Optional[Image]:
        """获取图片信息"""
        logger.info(f"获���图片信息: ID={image_id}")
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
