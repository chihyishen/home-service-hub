from shared_lib import create_app

from .database import engine, Base, get_db
from .routers import portfolio

# Create tables (will be replaced by Alembic in Plan 3)
Base.metadata.create_all(bind=engine)

app = create_app(
    title="Home Service Hub - Stock Portfolio API",
    description="投資組合管理微服務。",
    version="1.0.0",
    routers=[portfolio.router],
    get_db=get_db,
    engine=engine,
    otel_service_name_env="OTEL_SERVICE_NAME_STOCK",
    otel_strict=False,
)
