from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.dca_plan import DcaPlan
from ..schemas import portfolio as schemas
from ..services import dca_service
from ..services.portfolio.helpers import sanitize_symbol

router = APIRouter(prefix="/api/portfolio/dca-plans", tags=["DCA"])


class DcaPlanIn(BaseModel):
    symbol: str
    amount: int = Field(..., gt=0)
    day_of_month: int = Field(..., ge=1, le=31)
    fee: Decimal = Field(default=Decimal("1"), ge=0, decimal_places=2)
    active: bool = True

    @field_validator("symbol")
    @classmethod
    def _symbol(cls, value: str) -> str:
        value = sanitize_symbol(value)
        if not value:
            raise ValueError("symbol is required")
        return value


class DcaPlanOut(DcaPlanIn):
    id: int
    last_executed_on: date | None = None
    model_config = ConfigDict(from_attributes=True)


def _get(db: Session, plan_id: int) -> DcaPlan:
    plan = db.get(DcaPlan, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="DCA plan not found")
    return plan


@router.get("", response_model=list[DcaPlanOut])
def list_plans(db: Session = Depends(get_db)):
    return db.query(DcaPlan).order_by(DcaPlan.id).all()


@router.post("", response_model=DcaPlanOut)
def create_plan(body: DcaPlanIn, db: Session = Depends(get_db)):
    plan = DcaPlan(**body.model_dump())
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


@router.put("/{plan_id}", response_model=DcaPlanOut)
def update_plan(plan_id: int, body: DcaPlanIn, db: Session = Depends(get_db)):
    plan = _get(db, plan_id)
    for key, value in body.model_dump().items():
        setattr(plan, key, value)
    db.commit()
    db.refresh(plan)
    return plan


@router.delete("/{plan_id}")
def delete_plan(plan_id: int, db: Session = Depends(get_db)):
    db.delete(_get(db, plan_id))
    db.commit()
    return {"message": "DCA plan deleted"}


@router.post("/run", response_model=list[schemas.Transaction])
def run_now(db: Session = Depends(get_db)):
    """手動補跑（排程每個交易日 17:30 也會自動跑）。"""
    return dca_service.run_due(db, dca_service.today_tw())
