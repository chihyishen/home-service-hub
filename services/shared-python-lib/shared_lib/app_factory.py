from __future__ import annotations

from typing import Callable, Sequence

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.engine import Engine

from .config import SharedSettings
from .errors import register_error_handlers
from .health import create_health_router
from .tracing import setup_tracing


def create_app(
    *,
    title: str,
    version: str,
    routers: Sequence[APIRouter],
    get_db: Callable,
    description: str = "",
    engine: Engine | None = None,
    otel_service_name_env: str | None = None,
    otel_strict: bool = False,
    settings: SharedSettings | None = None,
) -> FastAPI:
    """Bootstrap a FastAPI app with CORS, error handling, tracing, and health routes."""
    if settings is None:
        settings = SharedSettings()

    app = FastAPI(title=title, description=description, version=version)

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.get_allowed_origins_list(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Error handling (before routers so it catches all)
    register_error_handlers(app)

    # Business routers
    for router in routers:
        app.include_router(router)

    # Health
    app.include_router(create_health_router(get_db))

    # Root
    @app.get("/")
    async def root():
        return {"message": f"Welcome to {title}", "docs": "/docs"}

    # Tracing (after all routers registered so FastAPIInstrumentor picks them up)
    if otel_service_name_env and engine:
        setup_tracing(
            service_name_env=otel_service_name_env,
            strict=otel_strict,
            app=app,
            engine=engine,
        )

    return app
