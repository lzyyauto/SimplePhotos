import mimetypes
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from app.config import settings
from app.database.models import Folder, Image
from app.models import FileInfo, Folder, FolderInfo
from app.services.image_service import ImageService
from app.utils.logger import logger
from sqlalchemy.orm import Session
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserver


class FileWatcher(FileSystemEventHandler):

    def __init__(self, db: Session, image_service: ImageService):
        # self.db = db
        # self.image_service = image_service
        # self.loop = asyncio.get_event_loop()
        logger.info("初始化文件监控服务2")

    def on_created(self, event):
        if not event.is_directory and self._is_valid_image(event.src_path):
            # 使用 call_later 调用同步方法，该方法内部创建异步任务
            self.loop.call_later(10, self._schedule_process_file,
                                 event.src_path)

    def _schedule_process_file(self, file_path: str):
        """创建异步任务来处理文件"""
        asyncio.create_task(self._process_new_file(file_path))

    async def _process_new_file(self, file_path: str):
        try:
            # 检查文件是否存在且可读
            if not os.path.exists(file_path):
                logger.warning(f"文件不存在: {file_path}")
                return

            # 检查文件大小是否为0
            if os.path.getsize(file_path) == 0:
                logger.warning(f"文件大小为0: {file_path}")
                return

            # 获取文件所在文件夹
            rel_path = os.path.relpath(os.path.dirname(file_path),
                                       settings.IMAGES_DIR)
            folder = self.db.query(Folder).filter(
                Folder.folder_path == rel_path).first()

            if folder:
                await self.image_service.process_image(file_path,
                                                       folder_id=folder.id)
                logger.info(f"成功处理新文件: {file_path}")
        except Exception as e:
            logger.error(f"处理新文件失败: {file_path}, 错误: {str(e)}")

    def on_deleted(self, event):
        if not event.is_directory and self._is_valid_image(event.src_path):
            logger.info(f"检测到文件删除: {event.src_path}")
            try:
                # 删除数据库中的记录
                image = self.db.query(Image).filter(
                    Image.file_path == event.src_path).first()
                if image:
                    self.db.delete(image)
                    self.db.commit()
            except Exception as e:
                logger.error(f"处理文件删除失败: {str(e)}")

    def _is_valid_image(self, path: str) -> bool:
        return any(path.lower().endswith(ext)
                   for ext in settings.SUPPORTED_FORMATS)


class FileService:

    def __init__(self, db: Session):
        self.db = db
        self.image_service = ImageService(db)
        self._setup_cache_dirs()
        self.observer = None
        logger.info("初始化文件服务")

    def _setup_cache_dirs(self):
        """创建必要的缓存目录"""
        logger.info("创建缓存目录")
        os.makedirs(settings.CACHE_DIR, exist_ok=True)
        os.makedirs(settings.THUMBNAIL_DIR, exist_ok=True)
        os.makedirs(settings.CONVERTED_DIR, exist_ok=True)

    def collect_paths(self) -> Tuple[List[str], List[Tuple[str, str]]]:
        """收集所有文件夹和文件路径"""
        all_folders = []
        all_files = []

        for root, dirs, files in os.walk(settings.IMAGES_DIR):
            # 过滤文件夹
            dirs[:] = [
                d for d in dirs if not d.startswith(('.', '@', '$'))
                and os.path.isdir(os.path.join(root, d))
            ]

            # 收集文件夹
            for dir_name in dirs:
                full_path = os.path.join(root, dir_name)
                if os.path.relpath(full_path, settings.IMAGES_DIR) != '.':
                    all_folders.append(full_path)

            # 收集文件
            for file in files:
                # 将支持的格式转换为元组
                supported_formats = tuple(settings.SUPPORTED_FORMATS)
                if file.lower().endswith(supported_formats):
                    full_path = os.path.join(root, file)
                    all_files.append((full_path, os.path.dirname(full_path)))

        return all_folders, all_files

    def get_folder_info(self, folder_path: str) -> FolderInfo:
        """获取文件夹信息"""
        abs_path = os.path.abspath(folder_path)
        rel_path = os.path.relpath(folder_path, settings.IMAGES_DIR)
        name = os.path.basename(folder_path)
        parent_path = os.path.dirname(abs_path)  # 使用绝对路径获取父目录

        # 如果是根目录的直接子文件夹，parent_path 就是 IMAGES_DIR
        if parent_path == os.path.dirname(settings.IMAGES_DIR):
            parent_path = settings.IMAGES_DIR

        return FolderInfo(full_path=abs_path,
                          rel_path=rel_path,
                          name=name,
                          parent_path=parent_path)

    def get_file_info(self, file_path: str) -> FileInfo:
        """获取文件信息"""
        try:
            abs_path = os.path.abspath(file_path)
            rel_path = os.path.relpath(file_path, settings.IMAGES_DIR)
            folder_path = os.path.dirname(abs_path)
            mime_type = mimetypes.guess_type(file_path)[0]
            file_stat = os.stat(file_path)

            return FileInfo(full_path=abs_path,
                            rel_path=rel_path,
                            folder_path=folder_path,
                            mime_type=mime_type,
                            size=file_stat.st_size,
                            created_at=datetime.fromtimestamp(
                                file_stat.st_ctime))
        except Exception as e:
            logger.error(f"获取文件信息失败 {file_path}: {str(e)}")
            raise

    def save_folder(self,
                    folder_info: FolderInfo,
                    session: Session,
                    root_id: Optional[int] = None) -> Optional[Folder]:
        """保存文件夹信息到数据库"""
        try:
            # 检查文件夹是否已存在
            folder = session.query(Folder).filter(
                Folder.folder_path == folder_info.full_path).first()
            if folder:
                return folder

            # 处理根目录
            if folder_info.rel_path == ".":
                folder = Folder(folder_path=folder_info.full_path,
                                name="root",
                                parent_id=None)
            else:
                # 查找父文件夹ID
                parent = session.query(Folder).filter(
                    Folder.folder_path == folder_info.parent_path).first()
                parent_id = parent.id if parent else root_id

                folder = Folder(folder_path=folder_info.full_path,
                                name=folder_info.name,
                                parent_id=parent_id)

            session.add(folder)
            session.flush()
            return folder

        except Exception as e:
            logger.error(f"保存文件夹失败 {folder_info.rel_path}: {str(e)}")
            session.rollback()
            return None

    def _get_parent_id(self, parent_path: str, session: Session) -> int:
        """获取父文件夹ID"""
        if not parent_path or parent_path == '.':
            return 0  # 如果是根目录的直接子文件夹，返回0

        parent = session.query(Folder).filter(
            Folder.folder_path == os.path.relpath(
                parent_path, settings.IMAGES_DIR)).first()
        return parent.id if parent else 0  # 如果找不到父文件夹，也返回0

    def start_watching(self, path: str):
        """开始监控文件夹化"""
        if self.observer:
            logger.warning("文件监控服务已在运行")
            return

        logger.info(f"开始监控目录: {path}")
        event_handler = FileWatcher(self.db, self.image_service)

        # 修改监控服务的配置
        self.observer = PollingObserver(timeout=1)  # 减少超时时间
        self.observer.daemon = True  # 设置为守护线程
        self.observer.schedule(event_handler, path, recursive=True)
        self.observer.start()
        logger.info("使用轮询模式监控服务")

    def stop_watching(self):
        """停止文件监控"""
        if self.observer:
            try:
                self.observer.stop()
                # 添加时机制
                self.observer.join(timeout=2)
                if self.observer.is_alive():
                    logger.warning("文件监控服务未能正常停止")
                self.observer = None
                logger.info("文件监控服务已停止")
            except Exception as e:
                logger.error(f"停止文件监控服务失败: {str(e)}")

    def get_folder_structure(self, base_path: str) -> List[dict]:
        """获取文件夹结构"""
        logger.info(f"获取目录结构: {base_path}")
        structure = []
        for root, dirs, files in os.walk(base_path):
            folder = {
                'path':
                os.path.relpath(root, base_path),
                'name':
                os.path.basename(root),
                'files': [
                    f for f in files
                    if any(f.lower().endswith(ext)
                           for ext in settings.SUPPORTED_FORMATS)
                ]
            }
            structure.append(folder)
        return structure
