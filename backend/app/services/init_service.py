import asyncio
import concurrent.futures
import os
import threading
import time
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
            # 检查表中是否有数���
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

            # 收集所有文件并预先分片
            all_files = []
            for root, _, files in os.walk(settings.IMAGES_DIR):
                rel_path = os.path.relpath(root, settings.IMAGES_DIR)
                folder_id = folders_map.get(rel_path, folders_map.get('.'))
                for file in files:
                    if any(file.lower().endswith(ext)
                           for ext in settings.SUPPORTED_FORMATS):
                        all_files.append((os.path.join(root, file), folder_id))

            self.total_files = len(all_files)
            logger.info(f"找到 {self.total_files} 个文件待处理")

            # 确保分片大小符合配置
            chunk_size = self.chunk_size
            chunks = [
                all_files[i:i + chunk_size]
                for i in range(0, len(all_files), chunk_size)
            ]
            logger.info(f"分成 {len(chunks)} 个分片")

            def process_chunk(chunk_id: int,
                              files: List[Tuple[str, int]]) -> Tuple[int, int]:
                thread_name = threading.current_thread().name
                success = 0
                failed = 0
                chunk_size = len(files)

                logger.info(
                    f"[{thread_name}] 开始处理分片 {chunk_id+1}/{len(chunks)}, 大小: {chunk_size}"
                )

                with self.Session() as session:
                    image_service = ImageService(session)
                    batch = []

                    for idx, (file_path, folder_id) in enumerate(files, 1):
                        try:
                            if asyncio.run(
                                    image_service.process_image(
                                        file_path, folder_id)):
                                success += 1
                                batch.append(True)
                            else:
                                failed += 1
                                batch.append(False)
                                logger.warning(
                                    f"[{thread_name}] 处理��败: {file_path}")
                        except Exception as e:
                            failed += 1
                            logger.error(
                                f"[{thread_name}] 处理错误: {file_path}, 错误: {str(e)}"
                            )
                            continue

                        if len(batch) >= self.chunk_size:
                            try:
                                session.commit()
                                batch = []
                            except Exception as e:
                                logger.error(
                                    f"[{thread_name}] 提交失败，继续处理: {str(e)}")

                        # 进度日志
                        chunk_progress = (idx * 100) // chunk_size
                        if chunk_progress in [0, 50, 100]:
                            logger.info(
                                f"[{thread_name}] 分片 {chunk_id+1} 进度: {chunk_progress}% - "
                                f"成功: {success}, 失败: {failed}")

                        with self._lock:
                            self.processed_count += 1
                            if self.processed_count in [
                                    1, self.total_files // 2, self.total_files
                            ]:
                                total_progress = (self.processed_count *
                                                  100) // self.total_files
                                logger.info(
                                    f"总进度: {total_progress}% ({self.processed_count}/{self.total_files}) - "
                                    f"成功: {self.processed_count}, 失败: {self.failed_count}"
                                )

                    # 提交剩余的文件
                    if batch:
                        try:
                            session.commit()
                        except Exception as e:
                            logger.error(f"[{thread_name}] 最终提交失败: {str(e)}")

                return success, failed

            # 使用线程池处理分片
            with ThreadPoolExecutor(
                    max_workers=self.max_workers,
                    thread_name_prefix="ScanWorker") as executor:
                futures = [
                    executor.submit(process_chunk, i, chunk)
                    for i, chunk in enumerate(chunks)
                ]

                total_success = 0
                total_failed = 0
                for future in concurrent.futures.as_completed(futures):
                    success, failed = future.result()
                    total_success += success
                    total_failed += failed

            logger.info(f"扫描完成: 成功 {total_success}, 失败 {total_failed}")
            return len(folders_map), total_success

        except Exception as e:
            logger.error(f"全盘扫描失败: {str(e)}")
            raise
