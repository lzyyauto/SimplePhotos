import asyncio
import os
from datetime import datetime, timedelta
from typing import Dict, Set, Tuple

from app.config import settings
from app.models import Base, FailedImage, FileInfo, Folder, FolderInfo, Image
from app.services.file_service import FileService
from app.services.image_service import ImageService
from app.utils.logger import logger
from cachetools import TTLCache
from sqlalchemy.orm import Session, sessionmaker


class FolderService:

    def __init__(self, db: Session):
        self.db = db
        self.file_service = FileService(db)
        # 创建TTL缓存，设置1小时过期时间
        self.validation_cache = TTLCache(maxsize=100, ttl=3600)
        self.validation_locks: Dict[int, asyncio.Lock] = {}

    async def validate_folder_content(self, folder_id: int) -> None:
        """异步验证文件夹内容"""
        # 如果已经在缓存中且未过期，直接返回
        if folder_id in self.validation_cache:
            return

        # 获取或创建该文件夹的锁
        if folder_id not in self.validation_locks:
            self.validation_locks[folder_id] = asyncio.Lock()

        # 如果已经在验证中，直接返回
        if self.validation_locks[folder_id].locked():
            return

        async with self.validation_locks[folder_id]:
            try:
                # 获取文件夹信息
                folder = self.db.query(Folder).filter(
                    Folder.id == folder_id).first()
                if not folder:
                    return

                # 获取实际文件系统中的内容
                real_files, real_folders = await self._scan_folder_content(
                    folder.folder_path)

                # 获取数据库中记录的内容
                db_files = set(self._get_db_files(folder_id))
                db_folders = set(self._get_db_folders(folder_id))

                # 计算差异
                new_files = real_files - db_files
                deleted_files = db_files - real_files
                new_folders = real_folders - db_folders
                deleted_folders = db_folders - real_folders

                # 处理新增文件
                for file_path in new_files:
                    await self._process_new_file(file_path, folder_id)

                # 处理新增文件夹
                for folder_path in new_folders:
                    await self._process_new_folder(folder_path, folder_id)

                # 处理删除的文件
                for file_path in deleted_files:
                    self._process_deleted_file(file_path)

                # 处理删除的文件夹
                for folder_path in deleted_folders:
                    self._process_deleted_folder(folder_path)

                # 更新缓存
                self.validation_cache[folder_id] = datetime.now()

            except Exception as e:
                logger.error(f"验证文件夹内容失败 {folder_id}: {str(e)}")
            finally:
                # 清理锁
                if not self.validation_locks[folder_id].locked():
                    self.validation_locks.pop(folder_id, None)

    async def _scan_folder_content(
            self, folder_path: str) -> Tuple[Set[str], Set[str]]:
        """扫描文件夹内容"""
        real_files = set()
        real_folders = set()

        full_path = os.path.join(settings.IMAGES_DIR, folder_path)
        try:
            for entry in os.scandir(full_path):
                if entry.is_file() and self._is_supported_file(entry.name):
                    real_files.add(entry.path)
                elif entry.is_dir():
                    real_folders.add(entry.path)
        except Exception as e:
            logger.error(f"扫描文件夹失败 {folder_path}: {str(e)}")

        return real_files, real_folders

    def _get_db_files(self, folder_id: int) -> Set[str]:
        """获取数据库中记录的文件"""
        return {
            image.file_path
            for image in self.db.query(Image).filter(
                Image.folder_id == folder_id)
        }

    def _get_db_folders(self, folder_id: int) -> Set[str]:
        """获取数据库中记录的文件夹"""
        return {
            folder.folder_path
            for folder in self.db.query(Folder).filter(
                Folder.parent_id == folder_id)
        }

    async def _process_new_file(self, file_path: str, folder_id: int) -> None:
        """处理新文件"""
        try:
            file_info = self.file_service.get_file_info(file_path)
            image_service = ImageService(self.db)
            await image_service.process_image(file_info, folder_id)
            logger.info(f"补偿处理新文件: {file_path}")
        except Exception as e:
            logger.error(f"处理新文件失败 {file_path}: {str(e)}")

    async def _process_new_folder(self, folder_path: str,
                                  parent_id: int) -> None:
        """处理新文件夹"""
        try:
            folder_info = self.file_service.get_folder_info(folder_path)
            folder = self.file_service.save_folder(folder_info, self.db)
            if folder:
                self.db.commit()
                logger.info(f"补偿处理新文件夹成功: {folder_path}")
            else:
                logger.warning(f"补偿处理新文件夹失败，未能保存: {folder_path}")
        except Exception as e:
            logger.error(f"处理新文件夹失败 {folder_path}: {str(e)}")
            self.db.rollback()

    def _process_deleted_file(self, file_path: str) -> None:
        """处理已删除的文件"""
        try:
            image = self.db.query(Image).filter(
                Image.file_path == file_path).first()
            if image:
                self.db.delete(image)
                self.db.commit()
                logger.info(f"删除不存在的文件记录: {file_path}")
        except Exception as e:
            logger.error(f"删除文件记录失败 {file_path}: {str(e)}")

    def _process_deleted_folder(self, folder_path: str) -> None:
        """处理已删除的文件夹"""
        try:
            # 获取文件夹
            folder = self.db.query(Folder).filter(
                Folder.folder_path == folder_path).first()
            if folder:
                # 删除与该文件夹相关的所有图像
                images = self.db.query(Image).filter(
                    Image.folder_id == folder.id).all()
                for image in images:
                    self.db.delete(image)
                # 删除文件夹
                self.db.delete(folder)
                self.db.commit()
                logger.info(f"删除不存在的文件夹记录: {folder_path}")
        except Exception as e:
            logger.error(f"删除文件夹记录失败 {folder_path}: {str(e)}")
            self.db.rollback()  # 确保在出错时回滚事务

    def _is_supported_file(self, filename: str) -> bool:
        """检查是否为支持的文件类型"""
        return any(filename.lower().endswith(ext)
                   for ext in settings.SUPPORTED_FORMATS)
