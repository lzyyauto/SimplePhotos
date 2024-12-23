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
                result = True
            else:
                logger.info(f"数据库已存在记录: {folder_count}个文件夹, {image_count}张图片")
                result = False

            # 启动文件监控
            self.file_service.start_watching(settings.IMAGES_DIR)
            return result

        except Exception as e:
            logger.error(f"初始化数据库失败: {str(e)}")
            raise e

    async def full_scan(self) -> Tuple[int, int]:
        """执行全盘扫描"""
        try:
            logger.info("开始全盘扫描")
            self.db.query(Image).delete()
            self.db.query(Folder).delete()

            folders_count = 0
            images_count = 0
            folder_cache = {}  # 缓存文件夹对象

            # 先创建根目录
            root_folder = Folder(folder_path=".",
                                 name=os.path.basename(settings.IMAGES_DIR),
                                 parent_id=None)
            self.db.add(root_folder)
            self.db.flush()
            folder_cache["."] = root_folder
            folders_count += 1

            for root, dirs, files in os.walk(settings.IMAGES_DIR):
                rel_path = os.path.relpath(root, settings.IMAGES_DIR)
                current_folder = None

                if rel_path != ".":
                    # 获取父文件夹路径
                    parent_path = os.path.dirname(rel_path) or "."
                    parent_folder = folder_cache[parent_path]

                    # 创建当前文件夹
                    current_folder = Folder(folder_path=rel_path,
                                            name=os.path.basename(rel_path),
                                            parent_id=parent_folder.id)
                    self.db.add(current_folder)
                    self.db.flush()
                    folder_cache[rel_path] = current_folder
                    folders_count += 1
                else:
                    current_folder = root_folder

                # 处理图片文件
                for file in files:
                    if any(file.lower().endswith(ext)
                           for ext in settings.SUPPORTED_FORMATS):
                        file_path = os.path.join(root, file)
                        await self.image_service.process_image(
                            file_path,
                            folder_id=current_folder.id  # 传入所属文件夹ID
                        )
                        images_count += 1

            self.db.commit()
            logger.info(
                f"全盘扫描完成: 处理了 {folders_count} 个文件夹, {images_count} 张图片")
            return folders_count, images_count

        except Exception as e:
            logger.error(f"全盘扫描失败: {str(e)}")
            self.db.rollback()
            raise e
