from datetime import datetime

from sqlalchemy import (JSON, Boolean, Column, DateTime, ForeignKey, Integer,
                        String, Text)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Image(Base):
    __tablename__ = "images"

    id = Column(Integer, primary_key=True)
    file_path = Column(Text, unique=True)
    folder_id = Column(Integer, ForeignKey('folders.id'), nullable=False)
    thumbnail_path = Column(Text, nullable=True)
    exif_data = Column(JSON, nullable=True)
    is_heic = Column(Boolean, default=False)
    converted_path = Column(Text, nullable=True)
    image_type = Column(String, nullable=False)
    parent_id = Column(Integer, ForeignKey('images.id'), nullable=True)
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
    folder_path = Column(Text, unique=True)
    parent_id = Column(Integer, ForeignKey('folders.id'), nullable=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime,
                        default=datetime.utcnow,
                        onupdate=datetime.utcnow)

    parent = relationship("Folder", remote_side=[id], backref="subfolders")
    images = relationship("Image", back_populates="folder")
