from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel


class ImageBase(BaseModel):
    file_path: str
    thumbnail_path: str
    is_heic: bool
    exif_data: Dict
    converted_path: Optional[str] = None


class ImageCreate(ImageBase):
    pass


class Image(ImageBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FolderBase(BaseModel):
    folder_path: str


class FolderCreate(FolderBase):
    pass


class Folder(FolderBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FolderStructure(BaseModel):
    path: str
    name: str
    files: List[str]
