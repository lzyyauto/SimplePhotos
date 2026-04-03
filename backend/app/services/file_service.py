import asyncio
import mimetypes
import os
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from app.config import settings
from app.database.database import SessionLocal
from app.database.models import Folder, Image
from app.models import FileInfo, FolderInfo
from app.services.image_service import ImageService
from app.utils.logger import logger
from sqlalchemy.orm import Session
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserver


class FileWatcher(FileSystemEventHandler):
    """
    文件系统事件监听器（基于 watchdog）。

    ⚠️  DEPRECATED / 不推荐使用 ⚠️
    -------------------------------------------------------
    当前部署方式：Unraid NAS + Docker volume 挂载
    在此场景下，该监控机制存在根本性限制：

    1. Docker bind mount 的文件变更事件（inotify/FSEvents）
       不会从宿主机透传到容器内部。
       => PollingObserver 是唯一能工作的模式。

    2. PollingObserver 每秒遍历一次整棵目录树（O(N)）。
       对于 3-5万张图 + 几千个文件夹的规模，
       NAS 磁盘 IO 会持续被占用，得不偿失。

    推荐替代方案：
      - 手动触发：POST /api/scan（导入新图后手动扫描）
      - 补偿机制：FolderService.validate_folder_content()
                  （用户浏览时后台自动修复轻微不一致）

    ENABLE_FILE_WATCHER 默认应保持 false。
    -------------------------------------------------------

    线程安全：每次事件处理都创建独立的数据库 Session，
    避免跨线程共享同一个 Session（SQLAlchemy Session 非线程安全）。
    """

    def __init__(self):
        self.pending_files: Dict[str, float] = {}
        self.processing_lock = threading.Lock()
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self.thread.start()
        logger.info("初始化文件监控服务")

    def _run_event_loop(self):
        """在独立线程中运行事件循环"""
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def _get_session(self) -> Session:
        """每次操作获取独立 Session（线程安全）"""
        return SessionLocal()

    def on_created(self, event):
        """文件创建事件处理（延迟 10s，等待文件写入完成）"""
        try:
            if not event.is_directory and self._is_valid_image(event.src_path):
                logger.info(f"检测到新文件: {event.src_path}")
                with self.processing_lock:
                    self.pending_files[event.src_path] = time.time()
                self.loop.call_later(
                    10,
                    lambda: self.loop.create_task(self._process_pending_files()),
                )
        except Exception as e:
            logger.error(f"处理文件创建事件失败: {str(e)}")

    async def _process_pending_files(self):
        """处理待处理文件队列"""
        with self.processing_lock:
            current_time = time.time()
            files_to_process = {
                path: ts
                for path, ts in self.pending_files.items()
                if current_time - ts >= 10
            }
            if not files_to_process:
                return
            for path in files_to_process:
                self.pending_files.pop(path)

        # 按文件夹分组处理
        files_by_folder: Dict[str, List[str]] = {}
        for file_path in files_to_process:
            folder_path = os.path.dirname(file_path)
            files_by_folder.setdefault(folder_path, []).append(file_path)

        for folder_path, files in files_by_folder.items():
            # 每个文件夹批次使用独立 Session
            db = self._get_session()
            try:
                rel_path = os.path.relpath(folder_path, settings.IMAGES_DIR)
                folder = db.query(Folder).filter(
                    Folder.folder_path == rel_path
                ).first()

                if not folder:
                    logger.warning(f"找不到文件夹记录: {folder_path}")
                    continue

                image_service = ImageService(db)
                for file_path in files:
                    try:
                        file_info = FileInfo(
                            full_path=file_path,
                            rel_path=os.path.relpath(file_path, settings.IMAGES_DIR),
                            folder_path=folder_path,
                            mime_type=mimetypes.guess_type(file_path)[0],
                            size=os.path.getsize(file_path),
                            created_at=datetime.fromtimestamp(os.path.getctime(file_path)),
                        )
                        await image_service.process_image(file_info, folder.id)
                        logger.info(f"成功处理新文件: {file_path}")
                    except Exception as e:
                        logger.error(f"处理文件失败: {file_path}, 错误: {str(e)}")

                db.commit()
            except Exception as e:
                logger.error(f"处理文件夹失败: {folder_path}, 错误: {str(e)}")
                db.rollback()
            finally:
                db.close()

    def on_deleted(self, event):
        """文件删除事件处理"""
        if not event.is_directory and self._is_valid_image(event.src_path):
            logger.info(f"检测到文件删除: {event.src_path}")
            db = self._get_session()
            try:
                rel_path = os.path.relpath(event.src_path, settings.IMAGES_DIR)
                image = db.query(Image).filter(Image.file_path == rel_path).first()
                if image:
                    db.delete(image)
                    db.commit()
                    logger.info(f"已删除文件记录: {rel_path}")
            except Exception as e:
                logger.error(f"处理文件删除失败: {str(e)}")
                db.rollback()
            finally:
                db.close()

    def _is_valid_image(self, file_path: str) -> bool:
        """检查是否为支持的文件类型"""
        return any(
            file_path.lower().endswith(ext) for ext in settings.SUPPORTED_FORMATS
        )


class FileService:

    def __init__(self, db: Session):
        self.db = db
        self.image_service = ImageService(db)
        self._setup_cache_dirs()
        self.observer = None
        logger.info("初始化文件服务")

    def _setup_cache_dirs(self):
        """创建必要的缓存目录"""
        os.makedirs(settings.CACHE_DIR, exist_ok=True)
        os.makedirs(settings.THUMBNAIL_DIR, exist_ok=True)
        os.makedirs(settings.CONVERTED_DIR, exist_ok=True)

    def collect_paths(self) -> Tuple[List[str], List[Tuple[str, str]]]:
        """
        遍历 IMAGES_DIR，收集所有文件夹和支持格式的文件路径。
        Returns:
            (all_folders, all_files)
            all_folders: List[str] - 文件夹的绝对路径列表
            all_files: List[Tuple[str, str]] - (文件绝对路径, 所在文件夹绝对路径)
        """
        all_folders = []
        all_files = []
        supported_formats = tuple(settings.SUPPORTED_FORMATS)

        for root, dirs, files in os.walk(settings.IMAGES_DIR):
            # 过滤系统/隐藏文件夹
            dirs[:] = [
                d for d in dirs
                if not d.startswith((".", "@", "$"))
                and os.path.isdir(os.path.join(root, d))
            ]

            for dir_name in dirs:
                full_path = os.path.join(root, dir_name)
                all_folders.append(full_path)

            for file in files:
                if file.lower().endswith(supported_formats):
                    full_path = os.path.join(root, file)
                    all_files.append((full_path, root))

        return all_folders, all_files

    def get_folder_info(self, folder_path: str) -> FolderInfo:
        """获取文件夹信息（相对路径 + 父路径）"""
        abs_path = os.path.abspath(folder_path)
        rel_path = os.path.relpath(folder_path, settings.IMAGES_DIR)
        name = os.path.basename(folder_path)
        parent_abs_path = os.path.dirname(abs_path)

        return FolderInfo(
            full_path=abs_path,
            rel_path=rel_path,
            name=name,
            parent_path=parent_abs_path,
        )

    def get_file_info(self, file_path: str) -> FileInfo:
        """获取文件信息"""
        try:
            abs_path = os.path.abspath(file_path)
            rel_path = os.path.relpath(file_path, settings.IMAGES_DIR)
            folder_path = os.path.dirname(abs_path)
            mime_type = mimetypes.guess_type(file_path)[0]
            file_stat = os.stat(file_path)

            return FileInfo(
                full_path=abs_path,
                rel_path=rel_path,
                folder_path=folder_path,
                mime_type=mime_type,
                size=file_stat.st_size,
                created_at=datetime.fromtimestamp(file_stat.st_ctime),
            )
        except Exception as e:
            logger.error(f"获取文件信息失败 {file_path}: {str(e)}")
            raise

    def save_folder(
        self,
        folder_info: FolderInfo,
        session: Session,
        root_id: Optional[int] = None,
    ) -> Optional[Folder]:
        """保存文件夹信息到数据库（使用相对路径作为唯一键）"""
        try:
            # 统一用相对路径作为 folder_path（跨部署可移植）
            rel_path = folder_info.rel_path

            folder = session.query(Folder).filter(
                Folder.folder_path == rel_path
            ).first()
            if folder:
                return folder

            if rel_path == ".":
                folder = Folder(folder_path=rel_path, name="root", parent_id=None)
            else:
                # 查找父文件夹（父文件夹也用相对路径存储）
                parent_rel_path = os.path.relpath(
                    folder_info.parent_path, settings.IMAGES_DIR
                ) if folder_info.parent_path else "."

                parent = session.query(Folder).filter(
                    Folder.folder_path == parent_rel_path
                ).first()
                parent_id = parent.id if parent else root_id

                folder = Folder(
                    folder_path=rel_path,
                    name=folder_info.name,
                    parent_id=parent_id,
                )

            session.add(folder)
            session.flush()
            return folder

        except Exception as e:
            logger.error(f"保存文件夹失败 {folder_info.rel_path}: {str(e)}")
            session.rollback()
            return None

    def start_watching(self, path: str):
        """开始监控文件夹"""
        if self.observer:
            logger.warning("文件监控服务已在运行")
            return

        logger.info(f"开始监控目录: {path}")
        event_handler = FileWatcher()
        self.observer = PollingObserver(timeout=1)
        self.observer.daemon = True
        self.observer.schedule(event_handler, path, recursive=True)
        self.observer.start()
        logger.info("文件监控服务已启动（轮询模式）")

    def stop_watching(self):
        """停止文件监控"""
        if self.observer:
            try:
                self.observer.stop()
                self.observer.join(timeout=2)
                if self.observer.is_alive():
                    logger.warning("文件监控服务未能正常停止")
                self.observer = None
                logger.info("文件监控服务已停止")
            except Exception as e:
                logger.error(f"停止文件监控服务失败: {str(e)}")
