import asyncio
import os
from typing import Generator, List

from sqlalchemy.orm import Session
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from app.config import settings
from app.database.models import Folder, Image
from app.services.image_service import ImageService
from app.utils.logger import logger


class FileWatcher(FileSystemEventHandler):

    def __init__(self, db: Session, image_service: ImageService):
        self.db = db
        self.image_service = image_service
        self.loop = asyncio.get_event_loop()
        logger.info("初始化文件监控服务")

    def on_created(self, event):
        if not event.is_directory and self._is_valid_image(event.src_path):
            logger.info(f"检测到新文件: {event.src_path}")
            try:
                # 获取文件所在文件夹
                rel_path = os.path.relpath(os.path.dirname(event.src_path),
                                           settings.IMAGES_DIR)
                folder = self.db.query(Folder).filter(
                    Folder.folder_path == rel_path).first()

                if folder:
                    # 使用事件循环运行异步任务
                    self.loop.create_task(
                        self.image_service.process_image(event.src_path,
                                                         folder_id=folder.id))
            except Exception as e:
                logger.error(f"处理新文件失败: {str(e)}")

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
        logger.info("创建缓存���录")
        os.makedirs(settings.CACHE_DIR, exist_ok=True)
        os.makedirs(settings.THUMBNAIL_DIR, exist_ok=True)
        os.makedirs(settings.CONVERTED_DIR, exist_ok=True)

    def scan_directory(self, path: str) -> Generator[str, None, None]:
        """扫描目录下的所有图片文件"""
        logger.info(f"开始扫描目录: {path}")
        for root, _, files in os.walk(path):
            for file in files:
                if any(file.lower().endswith(ext)
                       for ext in settings.SUPPORTED_FORMATS):
                    full_path = os.path.join(root, file)
                    logger.debug(f"发现图片文件: {full_path}")
                    yield full_path

    def start_watching(self, path: str):
        """开始监控文件夹变化"""
        if self.observer:
            logger.warning("文件监控服务已在运行")
            return

        logger.info(f"开始监控目录: {path}")
        event_handler = FileWatcher(self.db, self.image_service)
        self.observer = Observer()
        self.observer.schedule(event_handler, path, recursive=True)
        self.observer.start()
        logger.info("文件监控服务已启动")

    def stop_watching(self):
        """停止文件监控"""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None
            logger.info("文件监控服务已停止")

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
