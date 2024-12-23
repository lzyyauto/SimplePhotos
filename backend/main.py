import contextlib

import uvicorn
from app.api.routes import router
from app.config import settings
from app.database import models
from app.database.database import engine, get_db
from app.services.file_service import FileService
from app.services.init_service import InitializationService
from app.utils.logger import logger
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

# 创建数据库表
logger.info("正在创建数据库表...")
models.Base.metadata.create_all(bind=engine)
logger.info("数据库表创建完成")


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    print("lifespan start")
    """应用生命周期事件处理"""
    file_service = None  # 在外部定义，以便finally中可以访问
    try:
        logger.info("开始应用初始化...")
        db = next(get_db())

        # 初始化服务
        init_service = InitializationService(db)
        if await init_service.initialize_database():
            logger.info("数据库初始化完成")

            # 启动文件监控
            file_service = FileService(db)
            file_service.start_watching(str(settings.IMAGES_DIR))
            logger.info("文件监控服务已启动")
        else:
            raise RuntimeError("数据库初始化失败")

        yield

    except Exception as e:
        print(f"初始化错误: {e}")
        logger.error(f"启动初始化失败: {str(e)}")
        raise e
    finally:
        print("lifespan finally")
        # 停止文件监控
        if file_service:
            file_service.stop_watching()
            logger.info("文件监控服务已停止")


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

# 先定义 lifespan 函数，再创��� FastAPI 实例
app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    lifespan=lifespan  # 现在 lifespan 函数已经定义，可以直接使用
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载所有静态文件目录
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
