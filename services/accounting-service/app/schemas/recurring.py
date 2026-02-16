from pydantic import Field
from datetime import date as dt_date
from typing import Optional
from . import BaseSchema, AuditSchema

class SubscriptionBase(BaseSchema):
    name: str = Field(..., description="項目名稱", examples=["Netflix"])
    amount: int = Field(..., description="每月金額")
    category: str = Field(..., description="分類名稱", examples=["娛樂"])
    category_id: Optional[int] = Field(default=None, description="分類 ID")
    sub_type: str = Field(default="SUBSCRIPTION", description="類型: FIXED_EXPENSE (固定支出) 或 SUBSCRIPTION (訂閱)")
    payment_method: str = Field(default="信用卡", description="支付方式", examples=["信用卡", "Apple Pay"])
    day_of_month: int = Field(..., description="每月扣款日 (1-31)", examples=[15])
    card_id: int = Field(..., description="扣款信用卡 ID")
    active: bool = Field(default=True, description="是否啟用中")

class SubscriptionCreate(SubscriptionBase):
    pass

class SubscriptionUpdate(BaseSchema): # 修正：繼承 BaseSchema
    name: Optional[str] = None
    amount: Optional[int] = None
    category: Optional[str] = None
    category_id: Optional[int] = None
    sub_type: Optional[str] = None
    payment_method: Optional[str] = None
    day_of_month: Optional[int] = None
    card_id: Optional[int] = None
    active: Optional[bool] = None

class Subscription(SubscriptionBase, AuditSchema):
    id: int

class InstallmentBase(BaseSchema):
    name: str = Field(..., description="分期名稱", examples=["iPhone 15"])
    total_amount: int = Field(..., description="總金額")
    monthly_amount: int = Field(..., description="每期金額")
    payment_method: str = Field(default="信用卡", description="支付方式", examples=["信用卡"])
    total_periods: int = Field(..., description="總期數")
    remaining_periods: int = Field(..., description="剩餘期數")
    start_date: dt_date = Field(..., description="開始日期")
    card_id: int = Field(..., description="扣款信用卡 ID")

class InstallmentCreate(InstallmentBase):
    pass

class InstallmentUpdate(BaseSchema): # 修正：繼承 BaseSchema
    name: Optional[str] = None
    total_amount: Optional[int] = None
    monthly_amount: Optional[int] = None
    payment_method: Optional[str] = None
    total_periods: Optional[int] = None
    remaining_periods: Optional[int] = None
    card_id: Optional[int] = None

class Installment(InstallmentBase, AuditSchema):
    id: int
