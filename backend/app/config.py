import os
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 基础配置
    APP_NAME: str = "SimplePhotos Backend"
    DEBUG: bool = True

    # 基础路径配置 - 通过环境变量或默认值设置
    BASE_DIR: Path = Path(__file__).parent.parent.parent
    DATA_ROOT: Path = Path(os.getenv('DATA_ROOT',
                                     str(BASE_DIR / 'data')))  # 转换为字符串

    # 数据目录配置
    DATA_DIR: Path = DATA_ROOT
    IMAGES_DIR: Path = DATA_DIR / "images"
    CACHE_DIR: Path = DATA_DIR / "cache"
    THUMBNAIL_DIR: Path = CACHE_DIR / "thumbnails"
    CONVERTED_DIR: Path = CACHE_DIR / "converted"
    LOGS_DIR: Path = DATA_DIR / "logs"

    # 数据库配置
    DATABASE_URL: str = f"sqlite:///{DATA_DIR}/images.db"

    # 图片相关配置
    SUPPORTED_FORMATS: List[str] = [
        ".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic", ".heif", ".mp4"
    ]
    THUMBNAIL_SIZE: tuple = (200, 200)

    # 多语言支持
    SUPPORTED_LANGUAGES: List[str] = ["en", "zh"]
    DEFAULT_LANGUAGE: str = "zh"

    # 分页配置
    PAGE_SIZE: int = 50

    # API 路径配置
    API_IMAGES_PATH: str = "/data/images"
    API_THUMBNAILS_PATH: str = "/data/thumbnails"
    API_CONVERTED_PATH: str = "/data/converted"

    # 扫描处理配置 - 使用简单的环境变量覆盖
    SCAN_WORKERS: int = int(os.getenv('SCAN_WORKERS', os.cpu_count() or 4))
    SCAN_CHUNK_SIZE: int = int(os.getenv('SCAN_CHUNK_SIZE', 10))

    def __init__(self):
        super().__init__()
        print(f"BASE_DIR: {self.BASE_DIR}")
        print(f"DATA_ROOT: {self.DATA_ROOT}")

    def setup_directories(self) -> None:
        """确保所有必要的目录存在，不存在则创建"""
        for path in [
                self.DATA_DIR, self.IMAGES_DIR, self.CACHE_DIR,
                self.THUMBNAIL_DIR, self.CONVERTED_DIR, self.LOGS_DIR
        ]:
            path.mkdir(parents=True, exist_ok=True)

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
settings.setup_directories()
