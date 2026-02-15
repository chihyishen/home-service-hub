import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# 修正路徑：database.py 在 app/ 內，所以要往上跳三層到根目錄
# 層次：app -> accounting-service -> services -> root
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.env"))
load_dotenv(env_path, override=True)

def get_database_url() -> str:
    # 優先嘗試讀取完整的 URL
    url = os.getenv("DATABASE_URL")
    if url:
        return url

    # 若無完整 URL，則由組件拼湊
    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    host = os.getenv("DB_HOST")
    port = os.getenv("POSTGRES_PORT")
    db_name = os.getenv("POSTGRES_DB_ACCOUNTING")

    # 檢查必要欄位是否缺失
    missing_vars = [
        var for var, val in {
            "POSTGRES_USER": user,
            "POSTGRES_PASSWORD": password,
            "DB_HOST": host,
            "POSTGRES_PORT": port,
            "POSTGRES_DB_ACCOUNTING": db_name
        }.items() if not val
    ]

    if missing_vars:
        raise ValueError(
            f"❌ 缺少必要的環境變數設定: {', '.join(missing_vars)}。 "
            f"嘗試載入的路徑為: {env_path}"
        )

    return f"postgresql://{user}:{password}@{host}:{port}/{db_name}"

SQLALCHEMY_DATABASE_URL = get_database_url()

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
