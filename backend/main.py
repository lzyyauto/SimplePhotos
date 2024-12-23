import contextlib

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.config import settings
from app.database import models
from app.database.database import engine, get_db
from app.services.init_service import InitializationService
from app.utils.logger import logger

# 创建数据库表
logger.info("正在创建数据库表...")
models.Base.metadata.create_all(bind=engine)
logger.info("数据库表创建完成")


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    print("lifespan start")
    """应用生命周期事件处理"""
    try:
        logger.info("开始应用初始化...")
        db = next(get_db())
        init_service = InitializationService(db, engine)
        result = await init_service.initialize_database()
        if result:
            logger.info("数据库初始化完成")
        else:
            logger.info("数据库已存在，跳过初始化")
        logger.info("应用初始化完成")
        yield
    except Exception as e:
        print(f"初始化错误: {e}")
        logger.error(f"启动初始化失败: {str(e)}")
        raise e
    finally:
        print("lifespan finally")


# 先定义 lifespan 函数，再创建 FastAPI 实例
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
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
