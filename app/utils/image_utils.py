import os

from PIL import Image
from PIL.ExifTags import TAGS
from pillow_heif import register_heif_opener

from app.config import settings

# 注册 HEIF 打开器
register_heif_opener()


class ImageProcessor:

    @staticmethod
    async def create_thumbnail(image_path: str, thumb_path: str):
        """创建缩略图"""
        with Image.open(image_path) as img:
            # 处理所有可能的颜色模式
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            img.thumbnail(settings.THUMBNAIL_SIZE)
            img.save(thumb_path, "JPEG")

    @staticmethod
    async def convert_heic(heic_path: str, jpg_path: str):
        """转换HEIC为JPEG"""
        with Image.open(heic_path) as img:
            if img.mode == 'RGBA':
                img = img.convert('RGB')
            img.save(jpg_path, "JPEG")

    @staticmethod
    def get_exif_data(image_path: str) -> dict:
        """读取EXIF数据"""
        try:
            with Image.open(image_path) as img:
                exif = img.getexif()
                if not exif:
                    return {}

                # 将数字标签转换为可读的标签名
                exif_data = {}
                for tag_id in exif:
                    tag = TAGS.get(tag_id, tag_id)
                    data = exif.get(tag_id)
                    # 确保数据是字符串格式
                    if isinstance(data, bytes):
                        data = data.decode(errors='replace')
                    exif_data[str(tag)] = str(data)
                return exif_data
        except Exception:
            return {}  # 如果读取失败，返回空字典
