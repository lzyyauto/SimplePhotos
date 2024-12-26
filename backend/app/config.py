import os
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 基础配置
    APP_NAME: str = "SimplePhotos Backend"
    DEBUG: bool = True

    # 基础路径配置
    BASE_DIR: Path = Path(__file__).parent.parent.parent
    DATA_ROOT: Path = Path(os.getenv('DATA_ROOT', str(BASE_DIR / 'data')))

    # 数据目录配置
    DATA_DIR: Path = DATA_ROOT
    IMAGES_DIR: Path = Path(os.getenv('IMAGES_DIR', str(DATA_DIR / "images")))
    CACHE_DIR: Path = DATA_DIR / "cache"
    THUMBNAIL_DIR: Path = CACHE_DIR / "thumbnails"
    CONVERTED_DIR: Path = CACHE_DIR / "converted"
    LOGS_DIR: Path = DATA_DIR / "logs"

    # 数据库配置
    DB_TYPE: str = os.getenv('DB_TYPE', 'sqlite')  # 默认使用 sqlite

    # MySQL 配置
    MYSQL_HOST: str = os.getenv('MYSQL_HOST', 'localhost')
    MYSQL_PORT: int = int(os.getenv('MYSQL_PORT', 3306))
    MYSQL_USER: str = os.getenv('MYSQL_USER', 'root')
    MYSQL_PASSWORD: str = os.getenv('MYSQL_PASSWORD', '')
    MYSQL_DATABASE: str = os.getenv('MYSQL_DATABASE', 'photos')

    @property
    def DATABASE_URL(self) -> str:
        if self.DB_TYPE == 'mysql':
            return f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
        return f"sqlite:///{self.DATA_DIR}/images.db"

    # 图片相关配置
    SUPPORTED_FORMATS: List[str] = [
        ".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic", ".heif", ".mp4"
    ]
    THUMBNAIL_SIZE: tuple = (200, 200)

    # 多语言支持
    SUPPORTED_LANGUAGES: List[str] = ["en", "zh"]
    DEFAULT_LANGUAGE: str = "zh"

    # 分页配置
    PAGE_SIZE: int = 20

    # API 路径配置
    API_IMAGES_PATH: str = "/data/images"
    API_THUMBNAILS_PATH: str = "/data/thumbnails"
    API_CONVERTED_PATH: str = "/data/converted"

    # 扫描处理配置 - 使用简单的环境变量覆盖
    SCAN_WORKERS: int = int(os.getenv('SCAN_WORKERS', os.cpu_count() or 4))
    SCAN_CHUNK_SIZE: int = int(os.getenv('SCAN_CHUNK_SIZE', 20))

    def __init__(self):
        super().__init__()
        # 打印关键配置信息
        print(f"数据库配置:")
        print(f"  DB_TYPE: {self.DB_TYPE}")
        if self.DB_TYPE == 'mysql':
            print(f"  MYSQL_HOST: {self.MYSQL_HOST}")
            print(f"  MYSQL_PORT: {self.MYSQL_PORT}")
            print(f"  MYSQL_USER: {self.MYSQL_USER}")
            print(f"  MYSQL_DATABASE: {self.MYSQL_DATABASE}")
            print(f"  DATABASE_URL: {self.DATABASE_URL}")

        print(f"\n路径配置:")
        print(f"  BASE_DIR: {self.BASE_DIR}")
        print(f"  DATA_ROOT: {self.DATA_ROOT}")
        print(f"  DATA_DIR: {self.DATA_DIR}")
        print(f"  IMAGES_DIR: {self.IMAGES_DIR}")
        print(f"  CACHE_DIR: {self.CACHE_DIR}")

        print(f"\n扫描配置:")
        print(f"  SCAN_WORKERS: {self.SCAN_WORKERS}")
        print(f"  SCAN_CHUNK_SIZE: {self.SCAN_CHUNK_SIZE}")

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
