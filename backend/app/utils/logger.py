import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.config import settings


def setup_logger():
    """配置日志系统"""

    # 创建日志目录
    log_dir = settings.DATA_DIR / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "app.log"

    # 配置根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # 日志格式
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',  # 简化格式，移除了 name
        datefmt='%Y-%m-%d %H:%M:%S')

    # 文件处理器
    file_handler = RotatingFileHandler(
        filename=log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)

    # 创建应用日志器
    logger = logging.getLogger('SimplePhotos')
    logger.setLevel(logging.INFO)
    # 清除可能存在的旧处理器
    logger.handlers.clear()

    # 添加处理器
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    # 确保日志不会传播到父日志器
    logger.propagate = False

    return logger


# 创建 logger 实例
logger = setup_logger()
