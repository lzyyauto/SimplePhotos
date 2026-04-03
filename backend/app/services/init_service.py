import asyncio
import os
import threading
from typing import Any, Dict, List, Tuple

from app.config import settings
from app.database.database import engine
from app.database.models import Base, FailedImage, Folder, Image
from app.models import FileInfo, FolderInfo
from app.services.file_service import FileService
from app.services.image_service import ImageService
from app.utils.logger import logger
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker


class InitializationService:

    def __init__(self, db: Session):
        self.db = db
        self.Session = sessionmaker(bind=engine)
        self.max_workers = settings.SCAN_WORKERS
        self.file_service = FileService(db)
        self.image_service = ImageService(db)
        self.folders_map: Dict[str, int] = {}
        self.folder_lock = threading.Lock()

    async def initialize_database(self) -> bool:
        """数据库初始化入口：若已有数据则跳过扫描"""
        try:
            logger.info("开始检查数据库初始化状态...")

            try:
                Base.metadata.create_all(bind=engine)
                logger.info("数据库表创建完成")

                folder_count = self.db.query(Folder).count()
                logger.info(f"当前文件夹数量: {folder_count}")

                if folder_count > 0:
                    logger.info("数据库已初始化，跳过扫描")
                    return True

            except Exception as e:
                logger.error(f"数据库查询失败: {str(e)}", exc_info=True)
                raise RuntimeError(f"数据库连接异常: {str(e)}")

            if not os.path.exists(settings.IMAGES_DIR):
                logger.error(f"图片目录不存在: {settings.IMAGES_DIR}")
                return False

            logger.info(f"开始扫描图片目录: {settings.IMAGES_DIR}")

            if not await self.process_folders():
                logger.error("文件夹处理失败")
                return False

            if not await self.process_files():
                logger.error("文件处理失败")
                return False

            logger.info("数据库初始化完成")
            return True

        except Exception as e:
            logger.error(f"数据库初始化失败: {str(e)}", exc_info=True)
            return False

    async def full_scan(self) -> Tuple[bool, str]:
        """执行全盘扫描，强制重新扫描所有文件夹和文件
        Returns:
            Tuple[bool, str]: (是否成功, 结果信息)
        """
        try:
            logger.info("开始执行全盘扫描...")
            Base.metadata.create_all(bind=engine)

            if not os.path.exists(settings.IMAGES_DIR):
                error_msg = f"图片目录不存在: {settings.IMAGES_DIR}"
                logger.error(error_msg)
                return False, error_msg

            logger.info(f"开始全盘扫描图片目录: {settings.IMAGES_DIR}")
            self.folders_map = {}

            if not await self.process_folders(force_rescan=True):
                return False, "文件夹处理失败"

            if not await self.process_files(force_rescan=True):
                return False, "文件处理失败"

            logger.info("全盘扫描完成")
            return True, "扫描完成"

        except Exception as e:
            error_msg = f"全盘扫描失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg

    async def process_folders(self, force_rescan: bool = False) -> bool:
        """处理文件夹"""
        try:
            logger.info("开始处理文件夹...")

            if force_rescan:
                with self.Session() as session:
                    try:
                        if settings.DB_TYPE == "postgresql":
                            # PostgreSQL：一条语句完成，RESTART IDENTITY 重置自增序列
                            # CASCADE 自动处理外键依赖（images, failed_images）
                            session.execute(text(
                                "TRUNCATE TABLE images, failed_images, folders "
                                "RESTART IDENTITY CASCADE"
                            ))
                        else:
                            # SQLite：临时关闭外键约束，逐表清空
                            session.execute(text("PRAGMA foreign_keys=OFF"))
                            session.execute(text("DELETE FROM images"))
                            session.execute(text("DELETE FROM failed_images"))
                            session.execute(text("DELETE FROM folders"))
                            session.execute(text("PRAGMA foreign_keys=ON"))

                        session.commit()
                        logger.info("已清空相关表，准备重新扫描")
                    except Exception as e:
                        session.rollback()
                        logger.error(f"清空表失败: {str(e)}")
                        return False

            with self.Session() as session:
                root = session.query(Folder).filter(
                    Folder.folder_path == ".").first()
                if not root:
                    root_info = FolderInfo(
                        full_path=str(settings.IMAGES_DIR),
                        rel_path=".",
                        name="root",
                        parent_path=None,
                    )
                    root = self.file_service.save_folder(root_info, session)
                    session.commit()
                    logger.info("创建根目录成功")

                # 映射表：使用相对路径 "." 和绝对路径两种 key，方便后续文件查找
                self.folders_map["."] = root.id
                self.folders_map[str(settings.IMAGES_DIR)] = root.id

                all_folders, _ = self.file_service.collect_paths()
                for folder_path in all_folders:
                    folder_info = self.file_service.get_folder_info(folder_path)
                    folder = self.file_service.save_folder(folder_info, session)
                    if folder:
                        self.folders_map[os.path.abspath(folder_path)] = folder.id

                session.commit()
                logger.info(f"文件夹处理完成，共处理 {len(self.folders_map)} 个文件夹")

            return True

        except Exception as e:
            logger.error(f"处理文件夹失败: {str(e)}", exc_info=True)
            return False

    async def process_files(self, force_rescan: bool = False) -> bool:
        """处理文件（分片 + 并发）"""
        try:
            logger.info("开始处理文件...")
            _, all_files = self.file_service.collect_paths()

            chunk_size = settings.SCAN_CHUNK_SIZE
            file_chunks = [
                all_files[i: i + chunk_size]
                for i in range(0, len(all_files), chunk_size)
            ]

            tasks = [
                self._process_files_chunk(i, chunk)
                for i, chunk in enumerate(file_chunks)
            ]
            results = await asyncio.gather(*tasks)

            completed = sum(s for s, f in results)
            failed = sum(f for s, f in results)
            logger.info(f"文件处理完成: 成功 {completed}, 失败 {failed}")
            return True

        except Exception as e:
            logger.error(f"处理文件失败: {str(e)}", exc_info=True)
            return False

    async def _process_files_chunk(
        self, chunk_id: int, files: List[Tuple[str, str]]
    ) -> Tuple[int, int]:
        """处理一组文件，每个 chunk 使用独立 Session，避免长事务"""
        success_count = 0
        failed_count = 0
        session = self.Session()

        try:
            for idx, (file_path, folder_path) in enumerate(files, 1):
                if await self._process_one_file_in_chunk(session, file_path, folder_path):
                    success_count += 1
                    if success_count % 10 == 0:
                        session.commit()
                        logger.info(f"分片 {chunk_id}: 已处理 {success_count}/{len(files)} 个文件")
                else:
                    failed_count += 1

                if idx % 10 == 0:
                    session.commit()

            session.commit()
            return success_count, failed_count

        except Exception as e:
            logger.error(f"分片 {chunk_id} 处理失败: {str(e)}", exc_info=True)
            session.rollback()
            return success_count, failed_count
        finally:
            session.close()

    async def _process_one_file_in_chunk(
        self, session: Session, file_path: str, folder_path: str
    ) -> bool:
        """抽取单个文件的处理逻辑，避免大段嵌套"""
        try:
            file_info = self.file_service.get_file_info(file_path)
            abs_folder_path = os.path.abspath(folder_path)

            with self.folder_lock:
                folder_id = self.folders_map.get(abs_folder_path)

            if not folder_id:
                error_msg = f"找不到文件夹ID: {abs_folder_path}"
                logger.warning(f"{error_msg} / {file_info.rel_path}")
                self._record_failed_image(session, file_info.rel_path, folder_path, error_msg)
                return False

            image_service = ImageService(session)
            if await image_service.process_image(file_info, folder_id):
                return True
            else:
                self._record_failed_image(session, file_info.rel_path, folder_path, "图片处理失败")
                return False

        except Exception as e:
            error_msg = f"处理文件异常: {str(e)}"
            logger.error(f"{error_msg} - {file_path}")
            rel_file_path = os.path.relpath(file_path, settings.IMAGES_DIR)
            self._record_failed_image(session, rel_file_path, folder_path, error_msg)
            return False

    def _record_failed_image(self, session: Session, rel_file_path: str, folder_path: str, error_msg: str):
        """记录失败图片"""
        session.add(FailedImage(
            file_path=rel_file_path,
            folder_path=os.path.relpath(folder_path, settings.IMAGES_DIR),
            error_message=error_msg,
        ))

    async def process_single_file(
        self, file_info: FileInfo, folder_id: int, session: Session
    ) -> bool:
        """处理单个文件"""
        try:
            image_service = ImageService(session)
            return await image_service.process_image(file_info, folder_id)
        except Exception as e:
            logger.error(f"处理文件失败 {file_info.rel_path}: {str(e)}")
            session.rollback()
            return False
