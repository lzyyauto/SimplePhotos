"""
SQLAlchemy ORM Model 唯一定义文件。
所有数据库表结构在此定义，其他模块统一从此处导入。
"""
import os
from datetime import datetime

from sqlalchemy import (BigInteger, Boolean, Column, DateTime, ForeignKey, Integer,
                        JSON, String, Text)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

# 根据数据库类型选择 JSON 字段实现：
#   - PostgreSQL：使用 JSONB（原生支持，可建索引，性能更好）
#   - 其他（SQLite 等）：使用标准 JSON
if os.getenv("DB_TYPE", "sqlite") == "postgresql":
    from sqlalchemy.dialects.postgresql import JSONB as JsonType
else:
    JsonType = JSON  # type: ignore[assignment]


class Folder(Base):
    __tablename__ = "folders"

    id = Column(Integer, primary_key=True, index=True)
    # 存储相对于 IMAGES_DIR 的路径（跨部署可移植）
    folder_path = Column(String(512), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    parent_id = Column(
        Integer,
        ForeignKey("folders.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_scanned_at = Column(DateTime, nullable=True)
    missing_since = Column(DateTime, nullable=True)

    parent = relationship("Folder", remote_side=[id], backref="subfolders")
    images = relationship("Image", back_populates="folder", cascade="all, delete-orphan")


class Image(Base):
    __tablename__ = "images"

    id = Column(Integer, primary_key=True, index=True)
    folder_id = Column(
        Integer,
        ForeignKey("folders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # 存储相对于 IMAGES_DIR 的路径（跨部署可移植）
    file_path = Column(String(512), unique=True, nullable=False, index=True)
    # 缓存路径：相对于各自缓存目录（THUMBNAIL_DIR / CONVERTED_DIR）
    thumbnail_path = Column(String(512), nullable=True)
    converted_path = Column(String(512), nullable=True)

    mime_type = Column(String(64), nullable=True)
    image_type = Column(String(32), nullable=False, default="original")  # original / heif / video / etc.
    is_heic = Column(Boolean, default=False)

    # 使用 JsonType：PG 下为 JSONB（可索引、性能好），其他数据库为标准 JSON
    exif_data = Column(JsonType, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    size_bytes = Column(BigInteger, nullable=True)
    mtime_ns = Column(BigInteger, nullable=True)
    missing_since = Column(DateTime, nullable=True)
    thumbnail_status = Column(String(16), nullable=False, default="pending", server_default="pending")
    thumbnail_version = Column(String(64), nullable=True)
    thumbnail_priority = Column(Integer, nullable=False, default=0, server_default="0")
    thumbnail_attempts = Column(Integer, nullable=False, default=0, server_default="0")
    thumbnail_error = Column(Text, nullable=True)
    thumbnail_started_at = Column(DateTime, nullable=True)
    thumbnail_retry_at = Column(DateTime, nullable=True)

    folder = relationship("Folder", back_populates="images")


class FailedImage(Base):
    __tablename__ = "failed_images"

    id = Column(Integer, primary_key=True, index=True)
    file_path = Column(String(512), nullable=False, index=True)
    folder_path = Column(String(512), nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class ScanRun(Base):
    __tablename__ = "scan_runs"

    id = Column(Integer, primary_key=True)
    status = Column(String(16), nullable=False, default="pending")
    folders_scanned = Column(Integer, nullable=False, default=0)
    images_discovered = Column(Integer, nullable=False, default=0)
    images_updated = Column(Integer, nullable=False, default=0)
    error = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
