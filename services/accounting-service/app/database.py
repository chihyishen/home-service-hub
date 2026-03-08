import os
from sqlalchemy import create_engine, Column, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.sql import func
from dotenv import load_dotenv

# 載入環境變數
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.env"))
load_dotenv(env_path, override=True)

def get_database_url() -> str:
    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    host = os.getenv("DB_HOST")
    port = os.getenv("POSTGRES_PORT")
    db_name = os.getenv("ACCOUNTING_DB")

    missing_vars = [
        var for var, val in {
            "POSTGRES_USER": user,
            "POSTGRES_PASSWORD": password,
            "DB_HOST": host,
            "POSTGRES_PORT": port,
            "ACCOUNTING_DB": db_name
        }.items() if not val
    ]

    if missing_vars:
        raise ValueError(f"❌ 缺少必要的資料庫環境變數: {', '.join(missing_vars)}")

    return f"postgresql://{user}:{password}@{host}:{port}/{db_name}"

SQLALCHEMY_DATABASE_URL = get_database_url()
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,      # 自動檢測失效連線
    pool_recycle=1800,       # 30 分鐘回收一次連線，降低 stale connection 風險
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_use_lifo=True,
    connect_args={
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 5,
    }
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 審計欄位 Mixin
class TimestampMixin:
    # 建立時間 (Java: createdAt)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    # 最後更新時間 (Java: updatedAt)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
