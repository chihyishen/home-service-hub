from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session


def create_health_router(get_db) -> APIRouter:
    """Create a health router. Pass the service's get_db dependency."""
    router = APIRouter(tags=["health"])

    @router.get("/health")
    def liveness():
        return {"status": "ok"}

    @router.get("/health/ready")
    def readiness(db: Session = Depends(get_db)):
        try:
            db.execute(text("SELECT 1"))
            return {"status": "ok", "database": "ok"}
        except Exception as exc:
            return {"status": "degraded", "database": f"error: {exc.__class__.__name__}"}

    return router
