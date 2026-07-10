
from typing import Literal

from pydantic import Field

from . import AuditSchema, BaseSchema


class CardBase(BaseSchema):
    name: str = Field(..., description="卡片名稱", examples=["台新 FlyGo"])
    billing_day: int = Field(..., ge=1, le=31, description="結帳日 (1-31)", examples=[10])
    reward_cycle_type: str = Field(default="BILLING_CYCLE", description="回饋計算週期")
    alert_threshold: int = Field(default=5000, description="消費提醒閾值")
    default_payment_method: str = Field(default="Apple Pay", description="預設支付工具")
    alert_payment_method: str | None = Field(default=None, description="若設定，預警門檻僅計算此支付工具的消費")
    alert_cycle_type: Literal["BILLING_CYCLE", "CALENDAR_MONTH"] | None = Field(
        default=None, description="預警計算週期；未設定時跟隨回饋週期"
    )

class CreditCardCreate(CardBase):
    pass

class CreditCardUpdate(BaseSchema): # 修正：改為繼承 BaseSchema
    name: str | None = None
    billing_day: int | None = Field(default=None, ge=1, le=31)
    reward_cycle_type: str | None = None
    alert_threshold: int | None = None
    default_payment_method: str | None = None
    alert_payment_method: str | None = None
    alert_cycle_type: Literal["BILLING_CYCLE", "CALENDAR_MONTH"] | None = None

class CreditCard(CardBase, AuditSchema):
    id: int

class CardStatus(BaseSchema):
    card_name: str
    current_cycle_total: int
    remaining_for_max_reward: int | None = None
    next_billing_date: str
    status_message: str
    filtered_usage: int | None = None
    alert_payment_method: str | None = None
    alert_cycle_type: Literal["BILLING_CYCLE", "CALENDAR_MONTH"] | None = None
    alert_period_start: str | None = None
    alert_period_end: str | None = None
