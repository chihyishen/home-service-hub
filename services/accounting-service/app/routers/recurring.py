from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..services import recurring_service

router = APIRouter(prefix="/recurring", tags=["Recurring"])

@router.post("/generate", summary="手動觸發定期項目生成")
def trigger_recurring_generation(db: Session = Depends(get_db)):
    recurring_service.generate_recurring_items(db)
    return {"message": "Recurring items generated"}
