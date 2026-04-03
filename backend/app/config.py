import os
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 基础配置
    APP_NAME: str = "SimplePhotos"
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
    DB_TYPE: str = os.getenv('DB_TYPE', 'sqlite')  # sqlite / postgresql

    # PostgreSQL 配置
    PG_HOST: str = os.getenv('PG_HOST', 'localhost')
    PG_PORT: int = int(os.getenv('PG_PORT', 5432))
    PG_USER: str = os.getenv('PG_USER', 'postgres')
    PG_PASSWORD: str = os.getenv('PG_PASSWORD', '')
    PG_DATABASE: str = os.getenv('PG_DATABASE', 'simplephotos')

    @property
    def DATABASE_URL(self) -> str:
        if self.DB_TYPE == 'postgresql':
            return (
                f"postgresql+psycopg2://"
                f"{self.PG_USER}:{self.PG_PASSWORD}"
                f"@{self.PG_HOST}:{self.PG_PORT}/{self.PG_DATABASE}"
            )
        return f"sqlite:///{self.DATA_DIR}/images.db"

    # 图片相关配置
    SUPPORTED_FORMATS: List[str] = [
        ".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic", ".heif", ".mp4", ".mov"
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
        print(f"数据库配置:")
        print(f"  DB_TYPE: {self.DB_TYPE}")
        if self.DB_TYPE == 'postgresql':
            print(f"  PG_HOST: {self.PG_HOST}")
            print(f"  PG_PORT: {self.PG_PORT}")
            print(f"  PG_USER: {self.PG_USER}")
            print(f"  PG_DATABASE: {self.PG_DATABASE}")
            # 密码不输出，只显示是否已设置
            print(f"  PG_PASSWORD: {'***' if self.PG_PASSWORD else '(empty)'}")
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
        extra = "ignore"


settings = Settings()
settings.setup_directories()
