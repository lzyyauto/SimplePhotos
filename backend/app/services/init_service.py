import asyncio
import os
import threading
from typing import Any, Dict, List, Tuple

from app.config import settings
from app.database.database import engine  # 确保导入 engine
from app.models import Base, FileInfo, Folder, FolderInfo  # 从 app.models 导入
from app.services.file_service import FileService
from app.services.image_service import ImageService
from app.utils.logger import logger
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
        """数据库初始化入口"""
        try:
            logger.info("开始检查数据库初始化状态...")

            # 确保数据库连接正常
            try:
                # 检查数据库表是否存在
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

            # 检查图片目录是否存在
            if not os.path.exists(settings.IMAGES_DIR):
                logger.error(f"图片目录不存在: {settings.IMAGES_DIR}")
                return False

            logger.info(f"开始扫描图片目录: {settings.IMAGES_DIR}")

            # 第一阶段：处理文件夹
            try:
                if not await self.process_folders():
                    logger.error("文件夹处理失败")
                    return False
            except Exception as e:
                logger.error(f"文件夹处理异常: {str(e)}", exc_info=True)
                return False

            # 第二阶段：处理文件
            try:
                if not await self.process_files():
                    logger.error("文件处理失败")
                    return False
            except Exception as e:
                logger.error(f"文件处理异常: {str(e)}", exc_info=True)
                return False

            logger.info("数据库初始化完成")
            return True

        except Exception as e:
            logger.error(f"数据库初始化失败: {str(e)}", exc_info=True)
            return False

    async def process_folders(self) -> bool:
        """处理文件夹"""
        try:
            logger.info("开始处理文件夹...")

            # 先创建根目录
            with self.Session() as session:
                root = session.query(Folder).filter(
                    Folder.folder_path == settings.IMAGES_DIR).first()
                if not root:
                    root_info = FolderInfo(full_path=settings.IMAGES_DIR,
                                           rel_path=".",
                                           name="root",
                                           parent_path=None)
                    root = self.file_service.save_folder(root_info, session)
                    session.commit()
                    logger.info("创建根目录成功")

                # 保存根目录ID到映射表
                self.folders_map[settings.IMAGES_DIR] = root.id

                # 处理其他文件夹
                all_folders, _ = self.file_service.collect_paths()
                for folder_path in all_folders:
                    folder_info = self.file_service.get_folder_info(
                        folder_path)
                    folder = self.file_service.save_folder(
                        folder_info, session, root.id)
                    if folder:
                        self.folders_map[folder_info.full_path] = folder.id

                session.commit()
                logger.info("文件夹处理完成")

            return True

        except Exception as e:
            logger.error(f"处理文件夹失败: {str(e)}")
            return False

    async def process_files(self) -> bool:
        """处理文件"""
        try:
            logger.info("开始处理文件...")
            _, all_files = self.file_service.collect_paths()

            # 分片处理
            chunk_size = 100
            file_chunks = [
                all_files[i:i + chunk_size]
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
            logger.error(f"处理文件失败: {str(e)}")
            return False

    async def _process_files_chunk(
            self, chunk_id: int, files: List[Tuple[str,
                                                   str]]) -> Tuple[int, int]:
        """处理一组文件"""
        success_count = 0
        failed_count = 0
        session = self.Session()

        try:
            for idx, (file_path, folder_path) in enumerate(files, 1):
                try:
                    file_info = self.file_service.get_file_info(file_path)
                    abs_folder_path = os.path.abspath(folder_path)

                    with self.folder_lock:
                        folder_id = self.folders_map.get(abs_folder_path)

                    if not folder_id:
                        logger.warning(f"找不到文件夹ID: {abs_folder_path}")
                        failed_count += 1
                        continue

                    # 创建新的 ImageService 实例并处理图片
                    image_service = ImageService(session)
                    if await image_service.process_image(file_info, folder_id):
                        success_count += 1
                        if success_count % 10 == 0:
                            session.commit()
                            logger.info(
                                f"分片 {chunk_id}: 已处理 {success_count}/{len(files)} 个文件"
                            )
                    else:
                        failed_count += 1

                except Exception as e:
                    logger.error(f"处理文件失败 {file_path}: {str(e)}")
                    failed_count += 1

            session.commit()
            return success_count, failed_count

        finally:
            session.close()

    async def process_single_file(self, file_info: FileInfo, folder_id: int,
                                  session: Session) -> bool:
        """处理单个文件"""
        try:
            image_service = ImageService(session)
            return await image_service.process_image(file_info, folder_id)
        except Exception as e:
            logger.error(f"处理文件失败 {file_info.rel_path}: {str(e)}")
            session.rollback()
            return False
