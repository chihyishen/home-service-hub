from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


# 基礎 Schema：實作與 Java 對標的 CamelCase 輸出
class BaseSchema(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel,
        populate_by_name=True
    )

# 審計欄位 Mixin
class AuditSchema(BaseModel):
    created_at: datetime | None = None
    updated_at: datetime | None = None

from .analytics import (
    AnnualReport,
    AnnualSummary,
    CategoryTrend,
    MonthlyCompareReport,
    MonthlyReport,
    MonthlyTrendPoint,
)
from .card import CardStatus, CreditCard, CreditCardCreate, CreditCardUpdate
from .category import (
    Category,
    CategoryCreate,
    CategoryMergePreview,
    CategoryMergeRequest,
    CategoryMergeResult,
    CategoryUpdate,
)
from .payment_method import PaymentMethod, PaymentMethodCreate, PaymentMethodUpdate
from .recurring import (
    Installment,
    InstallmentCreate,
    InstallmentUpdate,
    Subscription,
    SubscriptionCreate,
    SubscriptionUpdate,
)
from .transaction import Transaction, TransactionCreate, TransactionUpdate
