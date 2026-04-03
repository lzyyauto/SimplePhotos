"""
数据库连接与 Session 管理。

支持两种数据库后端：
  - postgresql: 使用 psycopg2 驱动（需安装 psycopg2-binary）
  - sqlite: 开发/测试用（默认值）

通过环境变量 DB_TYPE 切换。
"""
from app.config import settings
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker

# -----------------------------------------------------------------------
# 构建 Engine
# -----------------------------------------------------------------------
if settings.DB_TYPE == "postgresql":
    engine = create_engine(
        settings.DATABASE_URL,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=1800,  # 30分钟回收连接，防止 PG 踢掉空闲连接
        pool_pre_ping=True,  # 每次从连接池取连接前 ping 一下，自动重连
    )
else:
    # SQLite 需要允许跨线程访问（开发用）
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False},
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# -----------------------------------------------------------------------
# FastAPI 依赖注入：获取数据库 Session
# -----------------------------------------------------------------------
def get_db():
    """
    FastAPI 路由依赖。每个请求获得独立 Session，请求结束后关闭。
    用法：db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
