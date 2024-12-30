import contextlib
import signal
import sys
from typing import Optional

import uvicorn
from app.api.routes import router
from app.config import settings
from app.database import models
from app.database.database import SessionLocal, engine, get_db
from app.services.file_service import FileService
from app.services.init_service import InitializationService
from app.utils.logger import logger
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# 全局服务实例
file_service: Optional[FileService] = None

# 创建数据库表
logger.info("正在创建数据库表...")
models.Base.metadata.create_all(bind=engine)
logger.info("数据库表创建完成")


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    try:
        # 创建数据库会话
        db = SessionLocal()

        try:
            # 初始化服务
            init_service = InitializationService(db)
            if not await init_service.initialize_database():
                logger.error("数据库初始化失败")
                raise RuntimeError("数据库初始化失败")

        except Exception as e:
            logger.error(f"初始化服务失败: {str(e)}")
            raise

        finally:
            # 无论初始化是否成功，都启动文件监控
            file_service = FileService(db)
            file_service.start_watching(settings.IMAGES_DIR)
            logger.info("文件监控服务已启动")
            db.close()

        yield

    except Exception as e:
        logger.error(f"应用启动失败: {str(e)}")
        raise e


# 配置 uvicorn 访问日志
logging_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(levelname)s - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
    },
    "loggers": {
        "uvicorn.access": {
            "handlers": ["default"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}

# 创建 FastAPI 实例
app = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG, lifespan=lifespan)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件目录
app.mount("/data/images",
          StaticFiles(directory=str(settings.IMAGES_DIR)),
          name="images")
app.mount("/data/thumbnails",
          StaticFiles(directory=str(settings.THUMBNAIL_DIR)),
          name="thumbnails")
app.mount("/data/converted",
          StaticFiles(directory=str(settings.CONVERTED_DIR)),
          name="converted")

# 注册路由
app.include_router(router, prefix="/api")

if __name__ == "__main__":
    logger.info("正在启动应用服务器...")
    uvicorn.run("main:app",
                host="0.0.0.0",
                port=8000,
                reload=True,
                log_config=logging_config)
