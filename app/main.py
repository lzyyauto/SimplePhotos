import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import settings
from app.database import models
from app.database.database import engine, get_db
from app.services.init_service import InitializationService
from app.utils.logger import logger

# 创建数据库表
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(router, prefix="/api")


@app.on_event("startup")
async def startup_event():
    """应用启动时执行初始化"""
    try:
        logger.info("开始应用初始化...")
        db = next(get_db())
        init_service = InitializationService(db, engine)
        await init_service.initialize_database()
        logger.info("应用初始化完成")
    except Exception as e:
        logger.error(f"启动初始化失败: {str(e)}")
        raise e


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
