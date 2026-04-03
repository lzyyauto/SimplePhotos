import mimetypes
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from app.config import settings
from app.database.models import Folder, Image
from app.models import FileInfo, FolderInfo
from app.services.image_service import ImageService
from app.utils.logger import logger
from sqlalchemy.orm import Session



class FileService:

    def __init__(self, db: Session):
        self.db = db
        self.image_service = ImageService(db)
        self._setup_cache_dirs()
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

