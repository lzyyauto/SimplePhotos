from app.config import settings
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# 根据数据库类型设置不同的连接参数
if settings.DB_TYPE == 'mysql':
    engine = create_engine(
        settings.DATABASE_URL,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=1800,  # 自动回收连接
    )
else:
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False}  # sqlite 需要
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        if settings.DB_TYPE == 'mysql':
            # 测试连接是否有效
            db.execute(text('SELECT 1'))
        yield db
    finally:
        db.close()
