from __future__ import annotations

import inspect
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import Column, DateTime, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class TimestampMixin:
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


def _default_env_path() -> str:
    frame = inspect.currentframe()
    caller = frame.f_back.f_back if frame and frame.f_back else None
    caller_file = caller.f_code.co_filename if caller else __file__
    return str((Path(caller_file).resolve().parent / "../../../.env").resolve())


def get_database_url(
    db_env_var: str,
    required_vars: list[str] | None = None,
    env_path: str | None = None,
) -> str:
    if required_vars is None:
        required_vars = ["POSTGRES_USER", "POSTGRES_PASSWORD"]

    load_dotenv(env_path or _default_env_path(), override=True)

    env_values = {name: os.getenv(name) for name in required_vars}
    missing_vars = [name for name, value in env_values.items() if not value]
    if missing_vars:
        raise ValueError(f"Missing required database environment variables: {', '.join(missing_vars)}")

    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db_name = os.getenv(db_env_var)
    return f"postgresql://{user}:{password}@{host}:{port}/{db_name}"


def create_db_engine(database_url: str, pool_config: dict | None = None) -> Engine:
    engine_kwargs = {"pool_pre_ping": True}
    if pool_config:
        engine_kwargs.update(pool_config)
    return create_engine(database_url, **engine_kwargs)


def get_db(SessionLocal):
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
