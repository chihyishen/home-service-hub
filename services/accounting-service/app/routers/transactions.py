import logging
from datetime import date

from fastapi import APIRouter, Depends
from shared_lib import get_tracer
from sqlalchemy.orm import Session

from .. import schemas
from ..database import get_db
from ..services import transaction_service

tracer = get_tracer("accounting-service")

router = APIRouter(prefix="/transactions", tags=["Transactions"])
logger = logging.getLogger(__name__)

@router.get("/", response_model=list[schemas.Transaction], summary="獲取交易清單")
def list_transactions(
    skip: int = 0,
    limit: int = 100,
    category: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    date_preset: str | None = None,
    transaction_type: str | None = None,
    exclude_subscription: bool = False,
    exclude_installment: bool = False,
    manual_only: bool = False,
    keyword: str | None = None,
    db: Session = Depends(get_db),
):
    with tracer.start_as_current_span("router.list_transactions") as span:
        logger.info(
            "查詢交易清單: category=%s, date_from=%s, date_to=%s, date_preset=%s, transaction_type=%s, "
            "exclude_subscription=%s, exclude_installment=%s, manual_only=%s, keyword=%s",
            category,
            date_from,
            date_to,
            date_preset,
            transaction_type,
            exclude_subscription,
            exclude_installment,
            manual_only,
            keyword,
        )
        result = transaction_service.get_transactions(
            db,
            skip=skip,
            limit=limit,
            category=category,
            date_from=date_from,
            date_to=date_to,
            date_preset=date_preset,
            transaction_type=transaction_type,
            exclude_subscription=exclude_subscription,
            exclude_installment=exclude_installment,
            manual_only=manual_only,
            keyword=keyword,
        )
        
        # 記錄回傳清單的大小
        span.set_attribute("http.response.count", len(result))
        
        return result

@router.post("/", response_model=schemas.Transaction, summary="新增交易紀錄")
def create_transaction(transaction: schemas.TransactionCreate, db: Session = Depends(get_db)):
    with tracer.start_as_current_span("router.create_transaction") as span:
        span.set_attribute("transaction.type", transaction.transaction_type)
        span.set_attribute("transaction.category_id", transaction.category_id)
        if transaction.card_id is not None:
            span.set_attribute("transaction.card_id", transaction.card_id)
        
        result = transaction_service.create_transaction(db, transaction)
        span.set_attribute("transaction.id", result.id)
        return result

@router.get("/report/annual/{year}",
            response_model=schemas.AnnualReport,
            response_model_by_alias=True,
            summary="獲取年度趨勢報表")
def get_annual_report(year: int, db: Session = Depends(get_db)):
    from ..services import analytics_service
    with tracer.start_as_current_span("router.get_annual_report") as span:
        result = analytics_service.get_annual_report(db, year)
        span.set_attribute("report.annual.year", result.year)
        span.set_attribute("report.annual.categories", len(result.category_trend))
        return result


@router.get("/report/{year}/{month}", 
            response_model=schemas.MonthlyReport, 
            response_model_by_alias=True, 
            summary="獲取月度財務報表")
def get_monthly_report(year: int, month: int, db: Session = Depends(get_db)):
    from ..services import analytics_service
    with tracer.start_as_current_span("router.get_monthly_report"):
        result = analytics_service.get_monthly_report(db, year, month)
        return result


@router.get("/report/compare/{year}/{month}",
            response_model=schemas.analytics.MonthlyCompareReport,
            response_model_by_alias=True,
            summary="獲取本月與上月分類差異")
def get_monthly_compare_report(year: int, month: int, db: Session = Depends(get_db)):
    from ..services import analytics_service
    with tracer.start_as_current_span("router.get_monthly_compare_report") as span:
        result = analytics_service.get_monthly_compare_report(db, year, month)
        span.set_attribute("report.compare.period", result.period)
        span.set_attribute("report.compare.baseline_period", result.baseline_period)
        return result


@router.get("/{transaction_id}", response_model=schemas.Transaction, summary="獲取單筆交易詳情")
def get_transaction(transaction_id: int, db: Session = Depends(get_db)):
    with tracer.start_as_current_span("router.get_transaction") as span:
        result = transaction_service.get_transaction(db, transaction_id)
        span.set_attribute("transaction.id", transaction_id)
        return result


@router.put("/{transaction_id}", response_model=schemas.Transaction, summary="修改交易紀錄")
def update_transaction(
    transaction_id: int,
    transaction_update: schemas.TransactionUpdate,
    db: Session = Depends(get_db)
):
    with tracer.start_as_current_span("router.update_transaction") as span:
        span.set_attribute("transaction.id", transaction_id)
        if transaction_update.transaction_type is not None:
            span.set_attribute("transaction.type", transaction_update.transaction_type)
        if transaction_update.category_id is not None:
            span.set_attribute("transaction.category_id", transaction_update.category_id)
        if transaction_update.card_id is not None:
            span.set_attribute("transaction.card_id", transaction_update.card_id)
        result = transaction_service.update_transaction(db, transaction_id, transaction_update)
        return result


@router.delete("/{transaction_id}", summary="刪除交易紀錄")
def delete_transaction(transaction_id: int, db: Session = Depends(get_db)):
    return transaction_service.delete_transaction(db, transaction_id)


@router.post("/{transaction_id}/refund", response_model=schemas.Transaction, summary="建立交易沖銷(退款)")
def refund_transaction(transaction_id: int, refund_amount: int, db: Session = Depends(get_db)):
    return transaction_service.refund_transaction(db, transaction_id, refund_amount)
