"""数据传输对象（Data Transfer Objects）
只包含纯 Python dataclass，不含任何 SQLAlchemy 声明。
SQLAlchemy ORM Model 统一在 app/database/models.py 中定义。
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional


@dataclass
class FileInfo:
    """文件信息数据类，用于在服务层之间传递文件元数据"""
    full_path: str       # 文件的绝对路径
    rel_path: str        # 相对于 IMAGES_DIR 的路径
    folder_path: str     # 所在文件夹的绝对路径
    mime_type: Optional[str]
    size: int
    created_at: datetime
    exif_data: Optional[Dict] = None


@dataclass
class FolderInfo:
    """文件夹信息数据类，用于在服务层之间传递文件夹元数据"""
    full_path: str       # 文件夹的绝对路径
    rel_path: str        # 相对于 IMAGES_DIR 的路径
    name: str            # 文件夹名称
    parent_path: Optional[str]  # 父文件夹的绝对路径
