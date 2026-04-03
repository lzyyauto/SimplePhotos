"""
FolderService：文件夹内容验证（补偿机制）。

设计说明：
  当用户打开一个文件夹时，后台异步验证该文件夹的 DB 记录
  是否与实际文件系统一致，处理新增/删除的文件和子文件夹。

缓存策略：
  _validation_cache 和 _validation_locks 是类变量（Class Variable），
  所有请求共享同一份缓存，跨实例有效。
  这是关键设计：FolderService 在每次请求中都会 new 一个新实例，
  如果缓存放在实例变量上，每次缓存都是空的，补偿扫描会对每次
  打开文件夹都触发一次文件系统 IO，在几千个文件夹的规模下
  会造成明显的延迟。

适用部署场景：
  NAS + Docker volume 挂载（FileWatcher 在此场景无效）。
  文件变更主要通过：
    1. 启动时全量扫描
    2. 手动触发 /api/scan
    3. 本机制在用户浏览时发现并修复轻微的差异
"""
import asyncio
import os
import threading
from datetime import datetime
from typing import Dict, Set, Tuple

from app.config import settings
from app.database.models import Folder, Image
from app.models import FolderInfo
from app.services.file_service import FileService
from app.services.image_service import ImageService
from app.utils.logger import logger
from cachetools import TTLCache
from sqlalchemy.orm import Session


class FolderService:

    # ----------------------------------------------------------------
    # 类变量：所有请求/实例共享，进程生命周期内持续有效
    # - maxsize=10000: 覆盖几千个文件夹绰绰有余
    # - ttl=3600: 1小时内访问过的文件夹不重复扫描
    #   （NAS 场景下文件不会频繁变动，1小时足够）
    # ----------------------------------------------------------------
    _validation_cache: TTLCache = TTLCache(maxsize=10000, ttl=3600)
    _validation_locks: Dict[int, asyncio.Lock] = {}

    # 保护 _validation_locks 字典本身的线程安全
    # （asyncio.Lock 只保护协程并发，字典操作需要 threading.Lock）
    _lock_registry_mutex = threading.Lock()

    def __init__(self, db: Session):
        self.db = db
        self.file_service = FileService(db)

    # ----------------------------------------------------------------
    # 公开接口
    # ----------------------------------------------------------------

    async def validate_folder_content(self, folder_id: int) -> None:
        """
        异步验证文件夹内容（幂等、带缓存）。

        流程：
          命中缓存 → 直接返回
          未命中   → 获取锁 → 再次检查缓存（防止并发重复扫描）
                   → 扫描文件系统 → 与 DB 对比 → 处理差异 → 写入缓存
        """
        # 快速路径：缓存命中，跳过扫描
        if folder_id in self._validation_cache:
            return

        lock = self._get_or_create_lock(folder_id)

        # 如果已经有协程在验证这个文件夹，直接返回，避免重复工作
        if lock.locked():
            return

        async with lock:
            # Double-check：可能在等锁期间缓存已被写入
            if folder_id in self._validation_cache:
                return

            try:
                folder = self.db.query(Folder).filter(
                    Folder.id == folder_id
                ).first()
                if not folder:
                    return

                # folder_path 是相对路径，拼接 IMAGES_DIR 得到绝对路径
                abs_folder_path = os.path.join(
                    str(settings.IMAGES_DIR), folder.folder_path
                )

                if not os.path.exists(abs_folder_path):
                    logger.warning(f"文件夹不存在于文件系统: {abs_folder_path}")
                    return

                real_files, real_folders = self._scan_folder_content(abs_folder_path)
                db_files = self._get_db_files(folder_id)
                db_folders = self._get_db_folders(folder_id)

                new_files = real_files - db_files
                deleted_files = db_files - real_files
                new_folders = real_folders - db_folders
                deleted_folders = db_folders - real_folders

                has_changes = new_files or deleted_files or new_folders or deleted_folders

                if has_changes:
                    logger.info(
                        f"文件夹 {folder.folder_path} 发现变更: "
                        f"+{len(new_files)}文件 -{len(deleted_files)}文件 "
                        f"+{len(new_folders)}文件夹 -{len(deleted_folders)}文件夹"
                    )

                    for file_path in new_files:
                        await self._process_new_file(file_path, folder_id)

                    for subfolder_path in new_folders:
                        await self._process_new_folder(subfolder_path, folder_id)

                    for file_path in deleted_files:
                        self._process_deleted_file(file_path)

                    for subfolder_path in deleted_folders:
                        self._process_deleted_folder(subfolder_path)
                else:
                    logger.debug(f"文件夹验证通过（无变更）: {folder.folder_path}")

                # 写入缓存（无论有无变更都写，避免频繁扫描）
                self._validation_cache[folder_id] = datetime.now()

            except Exception as e:
                logger.error(f"验证文件夹内容失败 folder_id={folder_id}: {str(e)}", exc_info=True)
            finally:
                # 验证完成后清理锁，释放内存
                self._remove_lock(folder_id)

    @classmethod
    def invalidate_cache(cls, folder_id: int) -> None:
        """
        手动使某个文件夹的缓存失效。
        在 /api/scan 全量扫描后应调用此方法清空所有缓存。
        """
        cls._validation_cache.pop(folder_id, None)

    @classmethod
    def clear_all_cache(cls) -> None:
        """清空所有文件夹的验证缓存（全量扫描后调用）"""
        cls._validation_cache.clear()
        logger.info("已清空所有文件夹验证缓存")

    # ----------------------------------------------------------------
    # 内部工具方法
    # ----------------------------------------------------------------

    def _get_or_create_lock(self, folder_id: int) -> asyncio.Lock:
        """线程安全地获取或创建 folder_id 对应的 asyncio.Lock"""
        with self._lock_registry_mutex:
            if folder_id not in self._validation_locks:
                self._validation_locks[folder_id] = asyncio.Lock()
            return self._validation_locks[folder_id]

    def _remove_lock(self, folder_id: int) -> None:
        """验证完成后移除锁，控制内存占用"""
        with self._lock_registry_mutex:
            self._validation_locks.pop(folder_id, None)

    def _scan_folder_content(self, abs_folder_path: str) -> Tuple[Set[str], Set[str]]:
        """
        扫描实际文件系统（只扫一层，不递归）。
        返回的路径均为相对于 IMAGES_DIR 的相对路径，与 DB 存储格式一致。
        """
        real_files: Set[str] = set()
        real_folders: Set[str] = set()

        try:
            for entry in os.scandir(abs_folder_path):
                rel = os.path.relpath(entry.path, settings.IMAGES_DIR)
                if entry.is_file(follow_symlinks=False) and self._is_supported_file(entry.name):
                    real_files.add(rel)
                elif entry.is_dir(follow_symlinks=False) and not entry.name.startswith((".", "@", "$")):
                    real_folders.add(rel)
        except PermissionError:
            logger.warning(f"无读取权限: {abs_folder_path}")
        except Exception as e:
            logger.error(f"扫描文件夹失败 {abs_folder_path}: {str(e)}")

        return real_files, real_folders

    def _get_db_files(self, folder_id: int) -> Set[str]:
        """获取 DB 中记录的文件相对路径集合"""
        return {
            image.file_path
            for image in self.db.query(Image.file_path).filter(
                Image.folder_id == folder_id
            )
        }

    def _get_db_folders(self, folder_id: int) -> Set[str]:
        """获取 DB 中记录的子文件夹相对路径集合"""
        return {
            f.folder_path
            for f in self.db.query(Folder.folder_path).filter(
                Folder.parent_id == folder_id
            )
        }

    async def _process_new_file(self, rel_path: str, folder_id: int) -> None:
        """处理新增文件（相对路径）"""
        try:
            full_path = os.path.join(str(settings.IMAGES_DIR), rel_path)
            file_info = self.file_service.get_file_info(full_path)
            image_service = ImageService(self.db)
            await image_service.process_image(file_info, folder_id)
            self.db.commit()
            logger.info(f"补偿：新增文件 {rel_path}")
        except Exception as e:
            self.db.rollback()
            logger.error(f"处理新文件失败 {rel_path}: {str(e)}")

    async def _process_new_folder(self, rel_path: str, parent_id: int) -> None:
        """处理新增文件夹（相对路径）"""
        try:
            full_path = os.path.join(str(settings.IMAGES_DIR), rel_path)
            folder_info = self.file_service.get_folder_info(full_path)
            folder = self.file_service.save_folder(folder_info, self.db, root_id=parent_id)
            if folder:
                self.db.commit()
                logger.info(f"补偿：新增文件夹 {rel_path}")
        except Exception as e:
            self.db.rollback()
            logger.error(f"处理新文件夹失败 {rel_path}: {str(e)}")

    def _process_deleted_file(self, rel_path: str) -> None:
        """处理已删除文件"""
        try:
            deleted = self.db.query(Image).filter(
                Image.file_path == rel_path
            ).delete()
            if deleted:
                self.db.commit()
                logger.info(f"补偿：删除文件记录 {rel_path}")
        except Exception as e:
            self.db.rollback()
            logger.error(f"删除文件记录失败 {rel_path}: {str(e)}")

    def _process_deleted_folder(self, rel_path: str) -> None:
        """
        处理已删除文件夹。
        删除该文件夹及其所有子文件夹记录（依赖 DB 外键 CASCADE）。
        """
        try:
            folder = self.db.query(Folder).filter(
                Folder.folder_path == rel_path
            ).first()
            if not folder:
                return

            # 递归删除子文件夹缓存（让它们下次会重新验证）
            subfolders = self.db.query(Folder).filter(
                Folder.parent_id == folder.id
            ).all()
            for subfolder in subfolders:
                self._process_deleted_folder(subfolder.folder_path)

            # 删除图片记录（Folder 上有 cascade='all, delete-orphan'，
            # 删 Folder 时 SQLAlchemy 会自动级联删 Image，
            # 但显式操作更清晰且避免 N+1 问题）
            self.db.query(Image).filter(Image.folder_id == folder.id).delete()
            self.db.delete(folder)
            self.db.commit()
            logger.info(f"补偿：删除文件夹记录 {rel_path}")
        except Exception as e:
            self.db.rollback()
            logger.error(f"删除文件夹记录失败 {rel_path}: {str(e)}")

    @staticmethod
    def _is_supported_file(filename: str) -> bool:
        return any(filename.lower().endswith(ext) for ext in settings.SUPPORTED_FORMATS)
