from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from typing import List, Optional
from .. import schemas
from ..database import get_db
from ..services import transaction_service
from ..tracing import tracer
import json
import logging

router = APIRouter(prefix="/transactions", tags=["Transactions"])
logger = logging.getLogger(__name__)

@router.get("/", response_model=List[schemas.Transaction], summary="獲取交易清單")
def list_transactions(
    skip: int = 0, 
    limit: int = 100, 
    category: Optional[str] = None, 
    db: Session = Depends(get_db)
):
    with tracer.start_as_current_span("router.list_transactions") as span:
        logger.info(f"查詢交易清單: category={category}")
        result = transaction_service.get_transactions(db, skip=skip, limit=limit, category=category)
        
        # 記錄回傳清單的大小
        span.set_attribute("http.response.count", len(result))
        
        if len(result) > 0:
            # 使用 jsonable_encoder 安全地將 SQLAlchemy 對象轉換為 JSON 格式
            sample = jsonable_encoder(result[:3])
            span.set_attribute("http.response.body.sample", json.dumps(sample, ensure_ascii=False))
        
        return result

@router.post("/", response_model=schemas.Transaction, summary="新增交易紀錄")
def create_transaction(transaction: schemas.TransactionCreate, db: Session = Depends(get_db)):
    with tracer.start_as_current_span("router.create_transaction") as span:
        logger.info(f"建立交易: {transaction.item}")
        # 記錄 Request Body
        span.set_attribute("http.request.body", transaction.model_dump_json())
        
        result = transaction_service.create_transaction(db, transaction)
        
        # 這裡也要修正，因為 result 此時是 SQLAlchemy 對象
        res_json = json.dumps(jsonable_encoder(result), ensure_ascii=False)
        span.set_attribute("http.response.body", res_json)
        return result

@router.get("/{transaction_id}", response_model=schemas.Transaction, summary="獲取單筆交易詳情")
def get_transaction(transaction_id: int, db: Session = Depends(get_db)):
    with tracer.start_as_current_span("router.get_transaction") as span:
        result = transaction_service.get_transaction(db, transaction_id)
        res_json = json.dumps(jsonable_encoder(result), ensure_ascii=False)
        span.set_attribute("http.response.body", res_json)
        return result

@router.put("/{transaction_id}", response_model=schemas.Transaction, summary="修改交易紀錄")
def update_transaction(
    transaction_id: int, 
    transaction_update: schemas.TransactionUpdate, 
    db: Session = Depends(get_db)
):
    with tracer.start_as_current_span("router.update_transaction") as span:
        span.set_attribute("http.request.body", transaction_update.model_dump_json(exclude_unset=True))
        result = transaction_service.update_transaction(db, transaction_id, transaction_update)
        res_json = json.dumps(jsonable_encoder(result), ensure_ascii=False)
        span.set_attribute("http.response.body", res_json)
        return result

@router.delete("/{transaction_id}", summary="軟刪除交易紀錄")
def delete_transaction(transaction_id: int, db: Session = Depends(get_db)):
    return transaction_service.delete_transaction(db, transaction_id)

@router.post("/{transaction_id}/refund", response_model=schemas.Transaction, summary="建立交易沖銷(退款)")
def refund_transaction(transaction_id: int, refund_amount: float, db: Session = Depends(get_db)):
    return transaction_service.refund_transaction(db, transaction_id, refund_amount)

@router.get("/report/{year}/{month}", 
            response_model=schemas.MonthlyReport, 
            response_model_by_alias=True, 
            summary="獲取月度財務報表")
def get_monthly_report(year: int, month: int, db: Session = Depends(get_db)):
    from ..services import analytics_service
    with tracer.start_as_current_span("router.get_monthly_report") as span:
        result = analytics_service.get_monthly_report(db, year, month)
        # 報表是 Pydantic 模型，可以直接 dump
        span.set_attribute("report.summary", result.summary.model_dump_json())
        return result
