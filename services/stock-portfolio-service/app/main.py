import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from shared_lib import create_app

from .database import SessionLocal, engine, get_db
from .models import (  # noqa: F401  (register tables with Base.metadata)
    corporate_action,
    portfolio_snapshot,
    price_history,
    symbol_map,
)
from .routers import dividends_backfill, exdividend, history, imports, portfolio, realized_pnl, upcoming_events
from .routers import symbol_map as symbol_map_router
from .services import scheduler as scheduler_module
from .services.twse_client import bootstrap_truststore

bootstrap_truststore()

logger = logging.getLogger(__name__)


def _start_scheduler():
    if not scheduler_module.is_enabled():
        logger.info("scheduler.disabled")
        return None
    try:
        scheduler = scheduler_module.build_scheduler(SessionLocal)
        scheduler.start()
    except Exception as exc:
        logger.exception("scheduler.bootstrap.failed", extra={"error": str(exc)})
        return None
    job_ids = [job.id for job in scheduler.get_jobs()]
    logger.info("scheduler.started", extra={"jobs": job_ids})
    return scheduler


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    scheduler = _start_scheduler()
    try:
        yield
    finally:
        if scheduler is not None:
            scheduler.shutdown(wait=False)
            logger.info("scheduler.stopped")


app = create_app(
    title="Home Service Hub - Stock Portfolio API",
    description="投資組合管理微服務。",
    version="1.1.0",
    routers=[
        portfolio.router,
        realized_pnl.router,
        exdividend.router,
        imports.router,
        history.router,
        history.snapshot_router,
        history.corp_router,
        symbol_map_router.router,
        dividends_backfill.router,
        upcoming_events.router,
    ],
    get_db=get_db,
    engine=engine,
    otel_service_name_env="OTEL_SERVICE_NAME_STOCK",
    otel_strict=False,
    lifespan=_lifespan,
    auth_service="portfolio",
)
