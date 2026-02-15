from pydantic import Field
from typing import List, Optional
from datetime import date as dt_date
from . import BaseSchema, AuditSchema

class TransactionBase(BaseSchema):
    date: Optional[dt_date] = Field(default=None, description="交易日期", examples=["2026-02-15"])
    category: str = Field(..., description="分類", examples=["餐飲"])
    item: str = Field(..., description="品項名稱", examples=["午餐"])
    personal_amount: float = Field(..., description="個人負擔金額")
    actual_swipe: float = Field(..., description="實際刷卡金額")
    payment_method: str = Field(..., description="支付方式", examples=["信用卡"])
    card_id: Optional[int] = Field(default=None, description="關聯的信用卡 ID")
    transaction_type: str = Field(default="EXPENSE", description="交易類型 (INCOME, EXPENSE)", examples=["EXPENSE"])
    note: Optional[str] = Field(default=None, description="備註")
    tags: Optional[List[str]] = Field(default=None, description="標籤")
    status: str = Field(default="COMPLETED", description="狀態")

class TransactionCreate(TransactionBase):
    pass

class TransactionUpdate(BaseSchema):
    date: Optional[dt_date] = None
    category: Optional[str] = None
    item: Optional[str] = None
    personal_amount: Optional[float] = None
    actual_swipe: Optional[float] = None
    payment_method: Optional[str] = None
    card_id: Optional[int] = None
    transaction_type: Optional[str] = None
    note: Optional[str] = None
    tags: Optional[List[str]] = None
    status: Optional[str] = None

class Transaction(TransactionBase, AuditSchema):
    id: int
    subscription_id: Optional[int] = None
    installment_id: Optional[int] = None
    is_deleted: bool
