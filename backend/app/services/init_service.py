import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List, Tuple

from app.config import settings
from app.database.database import engine  # 确保导入 engine
from app.database.models import Folder
from app.services.image_service import ImageService
from app.utils.logger import logger
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


class InitializationService:

    def __init__(self, db: Session):
        self.db = db
        self.Session = sessionmaker(
            bind=engine)  # 使用实际的 engine 实例，而不是 Engine 类
        self.max_workers = settings.SCAN_WORKERS
        self.chunk_size = settings.SCAN_CHUNK_SIZE
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

    def _get_or_create_folder(self, folder_path: str,
                              session: Session) -> Folder:
        """获取或创建文件夹记录（使用指定会话）"""
        try:
            rel_path = os.path.relpath(folder_path, settings.IMAGES_DIR)
            folder = session.query(Folder).filter(
                Folder.folder_path == rel_path).first()

            if not folder:
                name = os.path.basename(folder_path)
                if rel_path == "." or not rel_path:
                    return self._get_or_create_root_folder(session)

                parent_path = os.path.dirname(folder_path)
                parent = self._get_or_create_folder(parent_path, session)

                folder = Folder(folder_path=rel_path,
                                name=name,
                                parent_id=parent.id)
                session.add(folder)
                session.commit()  # 立即提交文件夹创建

            return folder

        except Exception as e:
            session.rollback()
            logger.error(f"创建文件夹失败 {folder_path}: {str(e)}")
            raise

    def _get_or_create_root_folder(self, session: Session) -> Folder:
        """获取或创建根文件夹"""
        root = session.query(Folder).filter(Folder.folder_path == ".").first()

        if not root:
            root = Folder(
                folder_path=".",
                name="root",
                parent_id=None  # 根目录没有父目录
            )
            session.add(root)
            session.commit()
            logger.debug("创建根文件夹")

        return root

    async def full_scan(self) -> Tuple[int, int]:
        """执行全盘扫描"""
        try:
            image_files = []
            folders_count = 0

            # 扫描文件
            logger.info("开始扫描文件夹...")
            for root, dirs, files in os.walk(settings.IMAGES_DIR):
                folders_count += len(dirs)
                for file in files:
                    if any(file.lower().endswith(ext)
                           for ext in settings.SUPPORTED_FORMATS):
                        image_files.append(os.path.join(root, file))

            total_images = len(image_files)
            logger.info(f"找到 {total_images} 张图片，开始处理...")

            # 分片处理
            chunks = [
                image_files[i:i + self.chunk_size]
                for i in range(0, len(image_files), self.chunk_size)
            ]

            async def process_chunk(chunk: List[str]) -> Tuple[int, int]:
                success = 0
                failed = 0
                # 为每个线程创建新的会话
                with self.Session() as session:
                    for file_path in chunk:
                        try:
                            folder_path = os.path.dirname(file_path)
                            folder = self._get_or_create_folder(
                                folder_path, session)

                            image_service = ImageService(session)
                            if await image_service.process_image(
                                    file_path, folder.id):
                                success += 1
                            else:
                                failed += 1

                        except Exception as e:
                            failed += 1
                            logger.error(f"处理失败: {file_path}, 错误: {str(e)}")

                    # 每个分片完成后立即提交
                    session.commit()
                return success, failed

            # 使用线程池处理分片
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = []
                for chunk in chunks:
                    future = asyncio.create_task(process_chunk(chunk))
                    futures.append(future)

                # 处理结果
                for i, future in enumerate(asyncio.as_completed(futures)):
                    chunk_success, chunk_failed = await future
                    self.processed_count += chunk_success
                    self.failed_count += chunk_failed

                    # 更新进度
                    progress = ((i + 1) * self.chunk_size * 100) / total_images
                    processed = min((i + 1) * self.chunk_size, total_images)
                    logger.info(
                        f"进度: {progress:.1f}% ({processed}/{total_images}) - "
                        f"成功: {self.processed_count}, 失败: {self.failed_count}")

            # 处理完成后的汇总
            logger.info("扫描完成:")
            logger.info(f"- 文件夹数量: {folders_count}")
            logger.info(f"- 总图片数量: {total_images}")
            logger.info(f"- 处理成功: {self.processed_count}")
            logger.info(f"- 处理失败: {self.failed_count}")

            return folders_count, self.processed_count

        except Exception as e:
            logger.error(f"全盘扫描失败: {str(e)}")
            raise
