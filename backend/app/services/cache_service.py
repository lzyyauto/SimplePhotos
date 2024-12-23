import os
from datetime import datetime, timedelta
from typing import Optional

from app.config import settings


class CacheService:

    def __init__(self):
        self._setup_cache_dirs()
        self.cache = {}

    def _setup_cache_dirs(self):
        """确保缓存目录存在"""
        os.makedirs(settings.CACHE_DIR, exist_ok=True)
        os.makedirs(settings.THUMBNAIL_DIR, exist_ok=True)
        os.makedirs(settings.CONVERTED_DIR, exist_ok=True)

    def get_cache(self, key: str) -> Optional[str]:
        """获取缓存内容"""
        if key in self.cache:
            value, expiry = self.cache[key]
            if expiry > datetime.now():
                return value
            else:
                del self.cache[key]
        return None

    def set_cache(self,
                  key: str,
                  value: str,
                  expires_in: timedelta = timedelta(hours=1)):
        """设置缓存内容"""
        self.cache[key] = (value, datetime.now() + expires_in)

    def clear_cache(self):
        """清除所有缓存"""
        self.cache.clear()

        # 清除缓存目录
        for dir_path in [settings.THUMBNAIL_DIR, settings.CONVERTED_DIR]:
            for file in os.listdir(dir_path):
                file_path = os.path.join(dir_path, file)
                try:
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                except Exception as e:
                    print(f"Error deleting {file_path}: {e}")
