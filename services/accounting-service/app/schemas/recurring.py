from datetime import date as dt_date

from pydantic import ConfigDict, Field

from . import AuditSchema, BaseSchema


class SubscriptionBase(BaseSchema):
    name: str = Field(..., description="項目名稱", examples=["Netflix"])
    amount: int = Field(..., description="每月金額")
    category_id: int = Field(..., description="分類 ID")
    sub_type: str = Field(default="SUBSCRIPTION", description="類型: FIXED_EXPENSE (固定支出) 或 SUBSCRIPTION (訂閱)")
    payment_method: str = Field(default="信用卡", description="支付方式", examples=["信用卡", "Apple Pay"])
    day_of_month: int = Field(..., description="每月扣款日 (1-31)", examples=[15])
    card_id: int | None = Field(default=None, description="扣款信用卡 ID")
    active: bool = Field(default=True, description="是否啟用中")

class SubscriptionCreate(SubscriptionBase):
    model_config = ConfigDict(extra="forbid")

class SubscriptionUpdate(BaseSchema): # 修正：繼承 BaseSchema
    model_config = ConfigDict(extra="forbid")
    name: str | None = None
    amount: int | None = None
    category_id: int | None = None
    sub_type: str | None = None
    payment_method: str | None = None
    day_of_month: int | None = None
    card_id: int | None = None
    active: bool | None = None

class Subscription(SubscriptionBase, AuditSchema):
    id: int
    category_name: str
    card_name: str | None = None

class InstallmentBase(BaseSchema):
    name: str = Field(..., description="分期名稱", examples=["iPhone 15"])
    total_amount: int = Field(..., description="總金額")
    monthly_amount: int = Field(..., description="每期金額")
    payment_method: str = Field(default="信用卡", description="支付方式", examples=["信用卡"])
    total_periods: int = Field(..., description="總期數")
    remaining_periods: int = Field(..., description="剩餘期數")
    start_date: dt_date = Field(..., description="開始日期")
    card_id: int | None = Field(default=None, description="扣款信用卡 ID")

class InstallmentCreate(InstallmentBase):
    pass

class InstallmentUpdate(BaseSchema): # 修正：繼承 BaseSchema
    name: str | None = None
    total_amount: int | None = None
    monthly_amount: int | None = None
    payment_method: str | None = None
    total_periods: int | None = None
    remaining_periods: int | None = None
    start_date: dt_date | None = None
    card_id: int | None = None

class Installment(InstallmentBase, AuditSchema):
    id: int
    card_name: str | None = None
