import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.config import settings

# 创建日志目录
log_dir = settings.BASE_DIR / "logs"
log_dir.mkdir(exist_ok=True)

# 配置日志格式
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# 创建文件处理器
file_handler = RotatingFileHandler(
    filename=log_dir / "app.log",
    maxBytes=10 * 1024 * 1024,  # 10MB
    backupCount=5,
    encoding='utf-8')
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.INFO)

# 创建控制台处理器
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
console_handler.setLevel(logging.INFO)

# 获取logger实例
logger = logging.getLogger('SimplePhotos')
logger.setLevel(logging.INFO)

# 确保处理器只被添加一次
if not logger.handlers:
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

# 设置日志传播
logger.propagate = False
