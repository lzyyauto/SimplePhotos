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
from app.database.models import FailedImage, Folder
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
        """创建或获取根文件夹"""
        try:
            root = session.query(Folder).filter(
                Folder.folder_path == '.').first()
            if not root:
                root = Folder(folder_path='.', name='root', parent_id=None)
                session.add(root)
                session.commit()
            return root
        except Exception as e:
            logger.error(f"创建根文件夹失败: {str(e)}")
            raise

    async def full_scan(self) -> bool:
        try:
            # 1. 先创建根文件夹
            logger.info("创建根文件夹...")
            with self.Session() as session:
                root_folder = self._get_or_create_root_folder(session)
                session.commit()
                folders_map = {'.': root_folder.id}

            # 2. 收集所有路径（文件夹和文件）
            logger.info("开始收集文件系统结构...")
            all_folders = []
            all_files = []

            for root, dirs, files in os.walk(settings.IMAGES_DIR):
                # 过滤文件夹
                dirs[:] = [
                    d for d in dirs if not d.startswith('.')
                    and not d.startswith('@') and not d.startswith('$')
                    and os.path.isdir(os.path.join(root, d))
                ]

                # 收集文件夹
                for dir_name in dirs:
                    full_path = os.path.join(root, dir_name)
                    rel_path = os.path.relpath(full_path, settings.IMAGES_DIR)
                    if rel_path != '.':
                        all_folders.append(full_path)

                # 收集文件
                for file in files:
                    if file.lower().endswith(
                        ('.jpg', '.jpeg', '.png', '.gif', '.heic', '.mp4')):
                        full_path = os.path.join(root, file)
                        all_files.append(
                            (full_path, os.path.dirname(full_path)))

            total_folders = len(all_folders)
            total_files = len(all_files)
            logger.info(f"发现 {total_folders} 个文件夹, {total_files} 个文件待处理")

            # 3. 按层级排序文件夹并分片处理
            all_folders.sort(key=lambda x: len(Path(x).parts))
            folder_chunks = [
                all_folders[i:i + self.chunk_size]
                for i in range(0, len(all_folders), self.chunk_size)
            ]

            # 4. 多线程处理文件夹
            logger.info("开始处理文件夹...")
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                folder_futures = []
                for i, chunk in enumerate(folder_chunks):
                    folder_futures.append(
                        executor.submit(self._process_folder_chunk, i, chunk))

                folder_count = 0
                for future in concurrent.futures.as_completed(folder_futures):
                    chunk_folders = future.result()
                    folders_map.update(chunk_folders)
                    folder_count += len(chunk_folders)
                    progress = (folder_count * 100) // total_folders
                    logger.info(
                        f"文件夹处理进度: {progress}% ({folder_count}/{total_folders})"
                    )

            # 5. 分片处理文件
            logger.info("开始处理文件...")
            file_chunks = [
                all_files[i:i + self.chunk_size]
                for i in range(0, len(all_files), self.chunk_size)
            ]

            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                file_futures = []
                for i, chunk in enumerate(file_chunks):
                    file_futures.append(
                        executor.submit(self._process_file_chunk, i, chunk,
                                        folders_map))

                file_count = 0
                for future in concurrent.futures.as_completed(file_futures):
                    success, failed = future.result()
                    file_count += success
                    progress = (file_count * 100) // total_files
                    logger.info(
                        f"文件处理进度: {progress}% ({file_count}/{total_files})")

            logger.info(f"初始化完成: 处理了 {folder_count} 个文件夹, {file_count} 个文件")
            return True

        except Exception as e:
            logger.error(f"全盘扫描失败: {str(e)}")
            return False

    def _process_folder_chunk(self, start_idx: int,
                              folders: List[str]) -> dict:
        thread_name = threading.current_thread().name
        result = {}
        with self.Session() as session:
            for folder_path in folders:
                try:
                    rel_path = os.path.relpath(folder_path,
                                               settings.IMAGES_DIR)
                    folder = self._get_or_create_folder(folder_path, session)
                    result[rel_path] = folder.id
                except Exception as e:
                    logger.error(
                        f"[{thread_name}] 处理文件夹失败 {folder_path}: {str(e)}")
            session.commit()
        return result
