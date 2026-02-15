from pydantic import BaseModel, Field
from typing import List, Optional, Any
from datetime import date

class PaymentRouteBase(BaseModel):
    method_name: str
    card_id: int

class PaymentRoute(PaymentRouteBase):
    id: int
    class Config:
        from_attributes = True

class CreditCardBase(BaseModel):
    name: str
    billing_day: int
    reward_rules: Optional[List[dict]] = None
    alert_threshold: float = 5000.0

class CreditCard(CreditCardBase):
    id: int
    class Config:
        from_attributes = True

class TransactionBase(BaseModel):
    date: Optional[date] = None
    category: str
    item: str
    personal_amount: float
    actual_swipe: float
    payment_method: str
    card_id: Optional[int] = None
    note: Optional[str] = None
    tags: Optional[List[str]] = None
    status: str = "COMPLETED"

class TransactionCreate(TransactionBase):
    pass

class Transaction(TransactionBase):
    id: int
    subscription_id: Optional[int] = None
    installment_id: Optional[int] = None
    class Config:
        from_attributes = True

class SubscriptionBase(BaseModel):
    name: str
    amount: float
    category: str
    day_of_month: int
    card_id: int
    active: bool = True

class Subscription(SubscriptionBase):
    id: int
    class Config:
        from_attributes = True

class InstallmentBase(BaseModel):
    name: str
    total_amount: float
    monthly_amount: float
    total_periods: int
    remaining_periods: int
    start_date: date
    card_id: int

class Installment(InstallmentBase):
    id: int
    class Config:
        from_attributes = True

# 用於回報信用卡狀態的 Schema
class CardStatus(BaseModel):
    card_name: str
    current_cycle_total: float
    remaining_for_max_reward: Optional[float] = None
    next_billing_date: date
    status_message: str
