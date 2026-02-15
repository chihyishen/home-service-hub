from pydantic import BaseModel, ConfigDict
from datetime import date as dt_date

class RecurringBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

class SubscriptionBase(RecurringBase):
    name: str
    amount: float
    category: str
    day_of_month: int
    card_id: int
    active: bool = True

class Subscription(SubscriptionBase):
    id: int

class InstallmentBase(RecurringBase):
    name: str
    total_amount: float
    monthly_amount: float
    total_periods: int
    remaining_periods: int
    start_date: dt_date
    card_id: int

class Installment(InstallmentBase):
    id: int
