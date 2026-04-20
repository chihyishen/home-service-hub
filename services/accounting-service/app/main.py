from shared_lib import create_app

from .database import engine, Base, get_db
from .routers import transactions, cards, recurring, categories, payment_methods

# Create tables (will be replaced by Alembic in Plan 3)
Base.metadata.create_all(bind=engine)

app = create_app(
    title="Home Service Hub - Accounting API",
    description="記帳與財務管理微服務。",
    version="1.2.0",
    routers=[
        transactions.router,
        cards.router,
        recurring.router,
        categories.router,
        payment_methods.router,
    ],
    get_db=get_db,
    engine=engine,
    otel_service_name_env="OTEL_SERVICE_NAME_ACCOUNTING",
    otel_strict=True,
)
