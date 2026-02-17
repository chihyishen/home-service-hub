from pydantic import Field, AliasChoices
from typing import List, Optional
from datetime import date as dt_date
from . import BaseSchema, AuditSchema

class TransactionBase(BaseSchema):
    date: Optional[dt_date] = Field(default=None, description="交易日期", examples=["2026-02-15"])
    category: Optional[str] = Field(default=None, description="分類名稱 (若提供 category_id 可自動同步)", examples=["餐飲"])
    category_id: Optional[int] = Field(default=None, description="結構化分類 ID")
    item: str = Field(..., description="品項名稱", examples=["午餐"])
    paid_amount: int = Field(
        ...,
        description="實付金額",
        validation_alias=AliasChoices("paid_amount", "paidAmount", "personal_amount", "personalAmount")
    )
    transaction_amount: int = Field(
        ...,
        description="交易金額",
        validation_alias=AliasChoices("transaction_amount", "transactionAmount", "actual_swipe", "actualSwipe")
    )
    payment_method: str = Field(..., description="支付方式", examples=["信用卡"])
    card_id: Optional[int] = Field(default=None, description="關聯的信用卡 ID")
    transaction_type: str = Field(default="EXPENSE", description="交易類型 (INCOME, EXPENSE)", examples=["EXPENSE"])
    note: Optional[str] = Field(default=None, description="備註")
    tags: Optional[List[str]] = Field(default=None, description="標籤")
    related_transaction_id: Optional[int] = Field(default=None, description="關聯的原始交易 ID (沖銷用)")

class TransactionCreate(TransactionBase):
    pass

class TransactionUpdate(BaseSchema):
    date: Optional[dt_date] = None
    category: Optional[str] = None
    category_id: Optional[int] = None
    item: Optional[str] = None
    paid_amount: Optional[int] = Field(
        default=None,
        validation_alias=AliasChoices("paid_amount", "paidAmount", "personal_amount", "personalAmount")
    )
    transaction_amount: Optional[int] = Field(
        default=None,
        validation_alias=AliasChoices("transaction_amount", "transactionAmount", "actual_swipe", "actualSwipe")
    )
    payment_method: Optional[str] = None
    card_id: Optional[int] = None
    transaction_type: Optional[str] = None
    note: Optional[str] = None
    tags: Optional[List[str]] = None

class Transaction(TransactionBase, AuditSchema):
    id: int
    subscription_id: Optional[int] = None
    installment_id: Optional[int] = None
    card_name: Optional[str] = None
