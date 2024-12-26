from datetime import datetime

from sqlalchemy import (JSON, Boolean, Column, DateTime, ForeignKey, Integer,
                        String, Text)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Image(Base):
    __tablename__ = "images"

    id = Column(Integer, primary_key=True, index=True)
    file_path = Column(String(512), unique=True, nullable=False)
    folder_id = Column(Integer, ForeignKey("folders.id"), nullable=False)
    thumbnail_path = Column(String(512))
    exif_data = Column(JSON)
    is_heic = Column(Boolean, default=False)
    converted_path = Column(String(512))
    image_type = Column(String(32), nullable=False, default='original')
    mime_type = Column(String(64))
    parent_id = Column(Integer, ForeignKey("images.id"))
    is_thumbnail = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime,
                        default=datetime.utcnow,
                        onupdate=datetime.utcnow)

    folder = relationship("Folder", back_populates="images")
    parent = relationship("Image", remote_side=[id], backref="derivatives")


class Folder(Base):
    __tablename__ = "folders"

    id = Column(Integer, primary_key=True)
    folder_path = Column(String(512), unique=True)
    parent_id = Column(Integer, ForeignKey('folders.id'), nullable=True)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime,
                        default=datetime.utcnow,
                        onupdate=datetime.utcnow)

    parent = relationship("Folder", remote_side=[id], backref="subfolders")
    images = relationship("Image", back_populates="folder")


class FailedImage(Base):
    __tablename__ = "failed_images"

    id = Column(Integer, primary_key=True)
    file_path = Column(String(512), nullable=False)
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
