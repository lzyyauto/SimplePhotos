import os
from pathlib import Path
from typing import List, Tuple

from sqlalchemy.orm import Session

from app.config import settings
from app.database.models import Base, Folder, Image
from app.services.file_service import FileService
from app.services.image_service import ImageService
from app.utils.logger import logger


class InitializationService:

    def __init__(self, db: Session, engine):
        self.db = db
        self.engine = engine
        self.file_service = FileService(db)
        self.image_service = ImageService(db)

    async def initialize_database(self) -> bool:
        """初始化数据库"""
        try:
            logger.info("检查数据库状态...")
            # 检查是否有任何记录
            image_count = self.db.query(Image).count()
            folder_count = self.db.query(Folder).count()

            if image_count == 0 and folder_count == 0:
                logger.info("数据库为空,开始初始化扫描")
                # 执行首次扫描
                await self.full_scan()
                return True

            logger.info(f"数据库已存在记录: {folder_count}个文件夹, {image_count}张图片")
            return False

        except Exception as e:
            logger.error(f"初始化数据库失败: {str(e)}")
            raise e

    async def full_scan(self) -> Tuple[int, int]:
        """执行全盘扫描"""
        try:
            logger.info("开始全盘扫描")

            # 清空现有数据
            self.db.query(Image).delete()
            self.db.query(Folder).delete()

            # 扫描所有文件夹
            folders_count = 0
            images_count = 0

            for root, dirs, files in os.walk(settings.IMAGES_DIR):
                # 添加文件夹记录
                folder_path = os.path.relpath(root, settings.IMAGES_DIR)
                if folder_path != '.':  # 跳过根目录
                    folder = Folder(folder_path=folder_path)
                    self.db.add(folder)
                    folders_count += 1

                # 处理图片文件
                for file in files:
                    if any(file.lower().endswith(ext)
                           for ext in settings.SUPPORTED_FORMATS):
                        file_path = os.path.join(root, file)
                        await self.image_service.process_image(file_path)
                        images_count += 1

            self.db.commit()
            logger.info(
                f"全盘扫描完成: 处理了 {folders_count} 个文件夹, {images_count} 张图片")
            return folders_count, images_count

        except Exception as e:
            logger.error(f"全盘扫描失败: {str(e)}")
            self.db.rollback()
            raise e
