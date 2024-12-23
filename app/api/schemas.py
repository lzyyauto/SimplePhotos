from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, computed_field


class ImageBase(BaseModel):
    file_path: str
    thumbnail_path: str
    is_heic: bool
    exif_data: Dict
    converted_path: Optional[str] = None


class ImageCreate(ImageBase):
    pass


class Image(BaseModel):
    id: int
    folder_id: int
    is_heic: bool
    is_thumbnail: bool
    image_type: str

    @computed_field
    def preview_url(self) -> str:
        """返回预览图URL"""
        return f"/api/images/{self.id}/preview"

    @computed_field
    def full_url(self) -> str:
        """返回完整图片URL"""
        return f"/api/images/{self.id}/full"

    class Config:
        from_attributes = True


class FolderBase(BaseModel):
    folder_path: str


class FolderCreate(FolderBase):
    pass


class Folder(BaseModel):
    id: int
    name: str
    folder_path: str
    parent_id: Optional[int] = None

    @computed_field
    def has_subfolders(self) -> bool:
        """是否有子文件夹（用于前端显示展开图标）"""
        return True  # 这里可以优化，通过查询实际确定

    class Config:
        from_attributes = True


class FolderStructure(BaseModel):
    path: str
    name: str
    files: List[str]


class PaginatedImageResponse(BaseModel):
    items: List[Image]
    total: int
    page: int
    total_pages: int
    page_size: int
