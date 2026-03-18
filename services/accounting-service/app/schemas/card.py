from pydantic import Field
from typing import List, Optional
from . import BaseSchema, AuditSchema

class CardBase(BaseSchema):
    name: str = Field(..., description="卡片名稱", examples=["台新 FlyGo"])
    billing_day: int = Field(..., description="結帳日 (1-31)", examples=[10])
    reward_cycle_type: str = Field(default="BILLING_CYCLE", description="回饋計算週期")
    alert_threshold: int = Field(default=5000, description="消費提醒閾值")
    default_payment_method: str = Field(default="Apple Pay", description="預設支付工具")

class CreditCardCreate(CardBase):
    pass

class CreditCardUpdate(BaseSchema): # 修正：改為繼承 BaseSchema
    name: Optional[str] = None
    billing_day: Optional[int] = None
    reward_cycle_type: Optional[str] = None
    alert_threshold: Optional[int] = None
    default_payment_method: Optional[str] = None

class CreditCard(CardBase, AuditSchema):
    id: int

class CardStatus(BaseSchema):
    card_name: str
    current_cycle_total: int
    remaining_for_max_reward: Optional[int] = None
    next_billing_date: str
    status_message: str
