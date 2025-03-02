import os

import cv2
import numpy as np
from app.config import settings
from app.utils.logger import logger
from PIL import Image
from PIL.ExifTags import TAGS
from pillow_heif import register_heif_opener

# 注册 HEIF 打开器
register_heif_opener()


class ImageProcessor:

    @staticmethod
    async def create_thumbnail(image_path: str, thumb_path: str):
        """创建缩略图"""
        try:
            # 修正 endswith 方法的使用，使用元组作为参数
            if image_path.lower().endswith(('.mp4', '.mov')):
                # 处理视频文件
                await ImageProcessor._create_video_thumbnail(
                    image_path, thumb_path)
            elif image_path.lower().endswith('.gif'):
                # 处理 GIF 文件
                await ImageProcessor._create_gif_thumbnail(
                    image_path, thumb_path)
            elif image_path.lower().endswith(('.heic', '.heif')):
                # 处理 HEIC/HEIF 文件 - 注意这里不需要转换，因为转换已经在 image_service 中完成
                await ImageProcessor._create_image_thumbnail(
                    image_path, thumb_path)
            else:
                # 处理普通图片
                await ImageProcessor._create_image_thumbnail(
                    image_path, thumb_path)
        except Exception as e:
            logger.error(f"创建缩略图失败 {image_path}: {str(e)}")
            raise

    @staticmethod
    async def _create_video_thumbnail(video_path: str, thumb_path: str):
        """从视频创建缩略图"""
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise Exception("无法打开视频文件")

            ret, frame = cap.read()
            if not ret:
                raise Exception("无法读取视频帧")

            # 转换 BGR 到 RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            # 转换为PIL图像
            img = Image.fromarray(frame_rgb)
            img.thumbnail(settings.THUMBNAIL_SIZE)

            # 确保目标目录存在
            os.makedirs(os.path.dirname(thumb_path), exist_ok=True)
            img.save(thumb_path, "JPEG", quality=95)
            cap.release()

        except Exception as e:
            logger.error(f"创建视频缩略图失败: {str(e)}")
            raise

    @staticmethod
    async def _create_gif_thumbnail(gif_path: str, thumb_path: str):
        """从GIF创建缩略图"""
        try:
            with Image.open(gif_path) as img:
                # 获取第一帧
                img.seek(0)
                # 转换为RGB模式
                if img.mode in ('RGBA', 'P'):
                    first_frame = img.convert('RGB')
                else:
                    first_frame = img.copy()

                first_frame.thumbnail(settings.THUMBNAIL_SIZE)

                # 确保目标目录存在
                os.makedirs(os.path.dirname(thumb_path), exist_ok=True)
                first_frame.save(thumb_path, "JPEG", quality=95)
        except Exception as e:
            logger.error(f"创建GIF缩略图失败: {str(e)}")
            raise

    @staticmethod
    async def _create_image_thumbnail(image_path: str, thumb_path: str):
        """创建普通图片缩略图"""
        try:
            with Image.open(image_path) as img:
                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')
                img.thumbnail(settings.THUMBNAIL_SIZE)

                # 确保目标目录存在
                os.makedirs(os.path.dirname(thumb_path), exist_ok=True)
                img.save(thumb_path, "JPEG", quality=95)
        except Exception as e:
            logger.error(f"创建图片缩略图失败: {str(e)}")
            raise

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
