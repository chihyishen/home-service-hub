from datetime import date as dt_date

from pydantic import AliasChoices, ConfigDict, Field

from . import AuditSchema, BaseSchema


class TransactionBase(BaseSchema):
    date: dt_date | None = Field(default=None, description="交易日期", examples=["2026-02-15"])
    category_id: int = Field(..., description="結構化分類 ID")
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
    card_id: int | None = Field(default=None, description="關聯的信用卡 ID")
    transaction_type: str = Field(default="EXPENSE", description="交易類型 (INCOME, EXPENSE)", examples=["EXPENSE"])
    note: str | None = Field(default=None, description="備註")
    tags: list[str] | None = Field(default=None, description="標籤")
    related_transaction_id: int | None = Field(default=None, description="關聯的原始交易 ID (沖銷用)")

class TransactionCreate(TransactionBase):
    model_config = ConfigDict(extra="forbid")

class TransactionUpdate(BaseSchema):
    model_config = ConfigDict(extra="forbid")
    date: dt_date | None = None
    category_id: int | None = None
    item: str | None = None
    paid_amount: int | None = Field(
        default=None,
        validation_alias=AliasChoices("paid_amount", "paidAmount", "personal_amount", "personalAmount")
    )
    transaction_amount: int | None = Field(
        default=None,
        validation_alias=AliasChoices("transaction_amount", "transactionAmount", "actual_swipe", "actualSwipe")
    )
    payment_method: str | None = None
    card_id: int | None = None
    transaction_type: str | None = None
    note: str | None = None
    tags: list[str] | None = None

class Transaction(TransactionBase, AuditSchema):
    id: int
    category_name: str
    subscription_id: int | None = None
    installment_id: int | None = None
    card_name: str | None = None
    refundable_amount: int = 0
