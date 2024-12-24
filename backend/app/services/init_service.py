import asyncio
import concurrent.futures
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from queue import Empty, Queue
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
        self.file_queue = Queue()
        self.processed_count = 0
        self.failed_count = 0
        self.total_files = 0
        self._lock = threading.Lock()

    async def initialize_database(self) -> bool:
        """初始化数据库"""
        try:
            # 检查表中是否有数据
            with self.Session() as session:
                folder_count = session.query(Folder).count()
                if folder_count > 0:
                    logger.info(f"数据库已有 {folder_count} 个文件夹记录，跳过初始化")
                    return True

                # 空表，需要执行全盘扫描
                logger.info("数据库为空，开始初始化...")
                await self.full_scan()
                return True

        except Exception as e:
            logger.error(f"数据库初始化失败: {str(e)}")
            return False

    def _get_or_create_folder(self, folder_path: str,
                              session: Session) -> Folder:
        """获取或创建文件夹记录（使用指定会话）"""
        try:
            rel_path = os.path.relpath(folder_path, settings.IMAGES_DIR)

            # 先尝试获取
            folder = session.query(Folder).filter(
                Folder.folder_path == rel_path).first()

            if folder:
                return folder

            # 如果是根目录
            if rel_path == "." or not rel_path:
                return self._get_or_create_root_folder(session)

            # 创建新文件夹
            try:
                name = os.path.basename(folder_path)
                parent_path = os.path.dirname(folder_path)
                parent = self._get_or_create_folder(parent_path, session)

                folder = Folder(folder_path=rel_path,
                                name=name,
                                parent_id=parent.id)
                session.add(folder)
                session.commit()
                return folder

            except Exception as e:
                session.rollback()
                # 再次尝试获取（可能其他线程已创建）
                folder = session.query(Folder).filter(
                    Folder.folder_path == rel_path).first()
                if folder:
                    return folder
                raise

        except Exception as e:
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
        try:
            # 1. 先创建根文件夹
            with self.Session() as session:
                root_folder = self._get_or_create_root_folder(session)
                root_id = root_folder.id

            # 2. 扫描并创建文件夹结构
            folders_map = {'.': root_id}  # 确保根目录存在于映射中
            for root, dirs, _ in os.walk(settings.IMAGES_DIR):
                for dir_name in dirs:
                    full_path = os.path.join(root, dir_name)
                    rel_path = os.path.relpath(full_path, settings.IMAGES_DIR)
                    with self.Session() as session:
                        folder = self._get_or_create_folder(full_path, session)
                        folders_map[rel_path] = folder.id

            # 3. 收集文件
            for root, _, files in os.walk(settings.IMAGES_DIR):
                rel_path = os.path.relpath(root, settings.IMAGES_DIR)
                folder_id = folders_map.get(rel_path, root_id)  # 使用根目录ID作为默认值
                for file in files:
                    if any(file.lower().endswith(ext)
                           for ext in settings.SUPPORTED_FORMATS):
                        self.file_queue.put((os.path.join(root,
                                                          file), folder_id))
                        self.total_files += 1

            logger.info(f"找到 {self.total_files} 个文件待处理")

            # 4. 工作线程函数
            def worker():
                thread_name = threading.current_thread().name
                local_success = 0
                local_failed = 0
                batch_count = 0

                with self.Session() as session:
                    image_service = ImageService(session)
                    while True:
                        # 获取一批文件
                        batch = []
                        for _ in range(self.chunk_size):
                            try:
                                batch.append(self.file_queue.get_nowait())
                            except Empty:
                                break

                        if not batch:
                            break

                        batch_count += 1
                        logger.info(
                            f"[{thread_name}] 开始处理第 {batch_count} 个分片，包含 {len(batch)} 个文件"
                        )

                        # 处理这批文件
                        for file_path, folder_id in batch:
                            try:
                                if asyncio.run(
                                        image_service.process_image(
                                            file_path, folder_id)):
                                    local_success += 1
                                else:
                                    local_failed += 1
                                    logger.warning(
                                        f"[{thread_name}] 处理失败: {file_path}")
                            except Exception as e:
                                local_failed += 1
                                logger.error(
                                    f"[{thread_name}] 处理错误: {file_path}, 错误: {str(e)}"
                                )

                            # 更新进度
                            with self._lock:
                                self.processed_count += 1
                                progress = (self.processed_count *
                                            100) / self.total_files
                                if self.processed_count % 100 == 0:
                                    logger.info(
                                        f"[{thread_name}] 分片 {batch_count} - "
                                        f"总进度: {progress:.1f}% ({self.processed_count}/{self.total_files}) - "
                                        f"成功: {local_success}, 失败: {local_failed}"
                                    )

                        # 每批次提交一次
                        session.commit()
                        logger.info(f"[{thread_name}] 完成第 {batch_count} 个分片处理")

                return local_success, local_failed

            # 5. 启动工作线程
            with ThreadPoolExecutor(
                    max_workers=self.max_workers,
                    thread_name_prefix="ScanWorker") as executor:
                futures = [
                    executor.submit(worker) for _ in range(self.max_workers)
                ]
                total_success = 0
                total_failed = 0

                # 等待所有线程完成
                for future in concurrent.futures.as_completed(futures):
                    success, failed = future.result()
                    total_success += success
                    total_failed += failed

            logger.info(f"扫描完成: 成功 {total_success}, 失败 {total_failed}")
            return len(folders_map), total_success

        except Exception as e:
            logger.error(f"全盘扫描失败: {str(e)}")
            raise
