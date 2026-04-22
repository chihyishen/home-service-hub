from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..database import get_db

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
