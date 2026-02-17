from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel
from datetime import datetime
from typing import Optional

# 基礎 Schema：實作與 Java 對標的 CamelCase 輸出
class BaseSchema(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel,
        populate_by_name=True
    )

# 審計欄位 Mixin
class AuditSchema(BaseModel):
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

from .card import CreditCard, CreditCardCreate, CreditCardUpdate, CardStatus
from .transaction import Transaction, TransactionCreate, TransactionUpdate
from .recurring import (
    Subscription, SubscriptionCreate, SubscriptionUpdate,
    Installment, InstallmentCreate, InstallmentUpdate
)
from .analytics import MonthlyReport
from .category import Category, CategoryCreate, CategoryUpdate
from .payment_method import PaymentMethod, PaymentMethodCreate, PaymentMethodUpdate
