import os

import exifread
import pyheif
from PIL import Image

from app.config import settings


class ImageProcessor:

    @staticmethod
    async def create_thumbnail(image_path: str, thumb_path: str):
        """创建缩略图"""
        with Image.open(image_path) as img:
            img.thumbnail(settings.THUMBNAIL_SIZE)
            img.save(thumb_path, "JPEG")

    @staticmethod
    async def convert_heic(heic_path: str, jpg_path: str):
        """转换HEIC为JPEG"""
        heif_file = pyheif.read(heic_path)
        image = Image.frombytes(
            heif_file.mode,
            heif_file.size,
            heif_file.data,
            "raw",
            heif_file.mode,
            heif_file.stride,
        )
        image.save(jpg_path, "JPEG")

    @staticmethod
    def get_exif_data(image_path: str) -> dict:
        """读取EXIF数据"""
        with open(image_path, 'rb') as f:
            tags = exifread.process_file(f)
        return {str(k): str(v) for k, v in tags.items()}
