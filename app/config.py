import os
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 基础配置
    APP_NAME: str = "SimplePhotos Backend"
    DEBUG: bool = True

    # 基础路径配置
    BASE_DIR: Path = Path(__file__).parent.parent
    DATA_DIR: Path = BASE_DIR / "data"

    # 数据库配置
    DATABASE_URL: str = f"sqlite:///{DATA_DIR}/images.db"

    # 图片相关配置
    IMAGES_DIR: Path = DATA_DIR / "images"
    SUPPORTED_FORMATS: List[str] = [
        ".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic", ".heif", ".mp4"
    ]
    THUMBNAIL_SIZE: tuple = (200, 200)

    # 缓存配置
    CACHE_DIR: Path = DATA_DIR / "cache"
    THUMBNAIL_DIR: Path = CACHE_DIR / "thumbnails"
    CONVERTED_DIR: Path = CACHE_DIR / "converted"

    # 多语言支持
    SUPPORTED_LANGUAGES: List[str] = ["en", "zh"]
    DEFAULT_LANGUAGE: str = "zh"

    # 分页配置
    PAGE_SIZE: int = 50

    def setup_directories(self):
        """创建必要的目录结构"""
        for path in [
                self.DATA_DIR, self.IMAGES_DIR, self.CACHE_DIR,
                self.THUMBNAIL_DIR, self.CONVERTED_DIR
        ]:
            path.mkdir(parents=True, exist_ok=True)

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
settings.setup_directories()
