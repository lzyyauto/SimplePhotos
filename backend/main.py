import contextlib
import os
import signal
import sys
from pathlib import Path
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
from fastapi.responses import FileResponse
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
    db = SessionLocal()
    file_service_instance: Optional[FileService] = None

    try:
        # 初始化数据库（首次启动时触发全盘扫描）
        init_service = InitializationService(db)
        if not await init_service.initialize_database():
            db.close()
            logger.error("数据库初始化失败，应用无法启动")
            raise RuntimeError("数据库初始化失败")

        # 初始化成功后，按配置决定是否启动文件监控
        if settings.ENABLE_FILE_WATCHER:
            file_service_instance = FileService(db)
            file_service_instance.start_watching(str(settings.IMAGES_DIR))
            logger.info("文件监控服务已启动")
        else:
            logger.info("文件监控服务已禁用（ENABLE_FILE_WATCHER=false）")

        yield

    except Exception as e:
        logger.error(f"应用启动失败: {str(e)}")
        raise
    finally:
        # 应用关闭时，停止监控并关闭 DB Session
        if file_service_instance:
            file_service_instance.stop_watching()
        db.close()
        logger.info("应用已停止")


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

# 注册 API 路由（必须在静态文件挂载之前，否则 catch-all 会拦截 API 请求）
app.include_router(router, prefix="/api")

# 挂载媒体静态文件目录
app.mount("/data/images",
          StaticFiles(directory=str(settings.IMAGES_DIR)),
          name="images")
app.mount("/data/thumbnails",
          StaticFiles(directory=str(settings.THUMBNAIL_DIR)),
          name="thumbnails")
app.mount("/data/converted",
          StaticFiles(directory=str(settings.CONVERTED_DIR)),
          name="converted")

# -------------------------------------------------------------------
# 前端静态文件托管（生产环境）
# 优先查找 Vite build 产物（dist/），找不到则认为是开发模式，跳过
# -------------------------------------------------------------------
_FRONTEND_DIST = Path(__file__).parent / "frontend" / "dist"

if _FRONTEND_DIST.exists():
    # 挂载前端 assets（JS/CSS/图片等）
    app.mount("/assets",
              StaticFiles(directory=str(_FRONTEND_DIST / "assets")),
              name="frontend-assets")

    # SPA catch-all：所有非 API、非静态资源的路径都返回 index.html
    # 让前端 React Router 处理路由
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend(full_path: str):
        index = _FRONTEND_DIST / "index.html"
        return FileResponse(str(index))

    logger.info(f"前端静态文件已挂载: {_FRONTEND_DIST}")
else:
    logger.info("未找到前端 dist 目录，跳过静态文件挂载（开发模式）")

if __name__ == "__main__":
    logger.info("正在启动应用服务器...")
    uvicorn.run("main:app",
                host="0.0.0.0",
                port=8000,
                reload=True,
                log_config=logging_config)
