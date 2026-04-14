import os
from sqlalchemy.orm import sessionmaker

from shared_lib.database import Base, TimestampMixin, get_database_url, create_db_engine, get_db as _get_db

# 載入環境變數並建立連線
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.env"))

SQLALCHEMY_DATABASE_URL = get_database_url(
    db_env_var="STOCK_DB",
    required_vars=["POSTGRES_USER", "POSTGRES_PASSWORD"],
    env_path=env_path,
)

engine = create_db_engine(SQLALCHEMY_DATABASE_URL, pool_config={
    "pool_recycle": 3600,
})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    yield from _get_db(SessionLocal)
