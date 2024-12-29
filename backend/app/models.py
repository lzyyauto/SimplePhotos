from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


# 数据类模型
@dataclass
class FileInfo:
    full_path: str
    rel_path: str
    folder_path: str
    mime_type: Optional[str]
    size: int
    created_at: datetime
    exif_data: Optional[Dict] = None


@dataclass
class FolderInfo:
    full_path: str
    rel_path: str
    name: str
    parent_path: Optional[str]


# 数据库模型
class Folder(Base):
    __tablename__ = "folders"

    id = Column(Integer, primary_key=True, index=True)
    folder_path = Column(String, unique=True, index=True)
    name = Column(String)
    parent_id = Column(Integer,
                       ForeignKey('folders.id', ondelete='SET NULL'),
                       nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class Image(Base):
    __tablename__ = "images"

    id = Column(Integer, primary_key=True, index=True)
    folder_id = Column(Integer, ForeignKey("folders.id"))
    file_path = Column(String, unique=True, index=True)
    mime_type = Column(String(64))
    image_type = Column(String(32), nullable=False, default='original')
    thumbnail_path = Column(String, nullable=True)
    converted_path = Column(String, nullable=True)
    exif_data = Column(JSON, nullable=True)
    created_at = Column(DateTime)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class FailedImage(Base):
    __tablename__ = "failed_images"

    id = Column(Integer, primary_key=True, index=True)
    file_path = Column(String, unique=True, index=True)
    folder_path = Column(String)
    error_message = Column(String)
    created_at = Column(DateTime, default=datetime.now)
    retry_count = Column(Integer, default=0)
