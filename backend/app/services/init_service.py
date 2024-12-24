import os
from pathlib import Path
from typing import List, Tuple

from app.config import settings
from app.database.models import Folder
from app.services.image_service import ImageService
from app.utils.logger import logger
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session


class InitializationService:

    def __init__(self, db: Session):
        self.db = db
        self.image_service = ImageService(db)
        self.batch_size = 100  # 每批处理的图片数
        self.processed_count = 0
        self.failed_count = 0

    async def initialize_database(self) -> bool:
        """初始化数据库，如果数据库已存在则跳过全盘扫描"""
        try:
            db_path = Path(settings.DATABASE_URL.replace('sqlite:///', ''))

            # 检查数据库文件是否存在
            if db_path.exists():
                # 验证数据库是否有效（简单检查是否有数据）
                folder_count = self.db.query(Folder).count()
                if folder_count > 0:
                    logger.info("数据库已存在且包含数据，跳过全盘扫描")
                    return True
                else:
                    logger.info("数据库存在但为空，执行全盘扫描")
            else:
                logger.info("数据库不存在，执行全盘扫描")

            # 执行全盘扫描
            folders_count, images_count = await self.full_scan()
            logger.info(f"初始化完成: {folders_count} 个文件夹, {images_count} 张图片")
            return True

        except Exception as e:
            logger.error(f"初始化数据库失败: {str(e)}")
            return False

    def _get_or_create_folder(self, folder_path: str) -> Folder:
        """获取或创建文件夹记录"""
        try:
            # 获取相对路径
            rel_path = os.path.relpath(folder_path, settings.IMAGES_DIR)

            # 查找现有文件夹
            folder = self.db.query(Folder).filter(
                Folder.folder_path == rel_path).first()

            if not folder:
                # 获取文件夹名称
                name = os.path.basename(folder_path)

                # 处理根目录
                if rel_path == "." or not rel_path:
                    return self._get_or_create_root_folder()

                # 获取父文件夹
                parent_path = os.path.dirname(folder_path)
                parent = self._get_or_create_folder(parent_path)

                # 创建新文件夹记录
                folder = Folder(
                    folder_path=rel_path,
                    name=name,
                    parent_id=parent.id  # 设置父文件夹ID
                )
                self.db.add(folder)
                self.db.commit()
                logger.debug(f"创建文件夹: {rel_path}")

            return folder

        except Exception as e:
            self.db.rollback()
            logger.error(f"创建文件夹失败 {folder_path}: {str(e)}")
            raise

    def _get_or_create_root_folder(self) -> Folder:
        """获取或创建根文件夹"""
        root = self.db.query(Folder).filter(Folder.folder_path == ".").first()

        if not root:
            root = Folder(
                folder_path=".",
                name="root",
                parent_id=None  # 根目录没有父目录
            )
            self.db.add(root)
            self.db.commit()
            logger.debug("创建根文件夹")

        return root

    async def _process_batch(self, files: List[str]):
        """批量处理图片文件"""
        for file_path in files:
            try:
                folder_path = os.path.dirname(file_path)
                folder = self._get_or_create_folder(folder_path)

                if await self.image_service.process_image(
                        file_path, folder.id):
                    self.processed_count += 1
                else:
                    self.failed_count += 1

            except Exception as e:
                self.failed_count += 1
                self.image_service.failed_images.append((file_path, str(e)))

    def _log_failed_images(self):
        """记录处理失败的图片"""
        log_file = settings.LOGS_DIR / "failed_images.log"
        with open(log_file, 'w', encoding='utf-8') as f:
            for path, error in self.image_service.failed_images:
                f.write(f"{path}: {error}\n")
        logger.warning(f"失败的图片已记录到 {log_file}")

    async def full_scan(self) -> Tuple[int, int]:
        """执行全盘扫描"""
        try:
            image_files = []
            folders_count = 0

            logger.info("开始扫描文件夹...")
            # 收集所有图片文件
            for root, dirs, files in os.walk(settings.IMAGES_DIR):
                folders_count += len(dirs)
                for file in files:
                    if any(file.lower().endswith(ext)
                           for ext in settings.SUPPORTED_FORMATS):
                        image_files.append(os.path.join(root, file))

            # 批量处理图片
            total_images = len(image_files)
            logger.info(f"找到 {total_images} 张图片，开始处理...")

            for i in range(0, total_images, self.batch_size):
                batch = image_files[i:i + self.batch_size]
                await self._process_batch(batch)
                self.db.commit()  # 每批提交一次

                # 计算进度百分比
                progress = min(100,
                               round((i + len(batch)) / total_images * 100, 1))
                processed = i + len(batch)
                logger.info(
                    f"进度: {progress}% ({processed}/{total_images}) - "
                    f"成功: {self.processed_count}, 失败: {self.failed_count}")

            # 处理完成后的汇总
            logger.info(f"扫描完成:")
            logger.info(f"- 文件夹数量: {folders_count}")
            logger.info(f"- 总图片数量: {total_images}")
            logger.info(f"- 处理成功: {self.processed_count}")
            logger.info(f"- 处理失败: {self.failed_count}")

            # 如果有失败的图片，记录到日志
            if self.image_service.failed_images:
                self._log_failed_images()

            return folders_count, self.processed_count

        except Exception as e:
            logger.error(f"全盘扫描失败: {str(e)}")
            raise
