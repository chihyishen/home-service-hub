from pydantic import BaseModel, Field
from typing import List, Optional
from . import BaseSchema, AuditSchema

class CardBase(BaseSchema):
    name: str = Field(..., description="卡片名稱", examples=["台新 FlyGo"])
    billing_day: int = Field(..., description="結帳日 (1-31)", examples=[10])
    reward_rules: Optional[List[dict]] = Field(default=None, description="回饋規則")
    alert_threshold: float = Field(default=5000.0, description="消費提醒閾值")

class CreditCardCreate(CardBase):
    pass

class CreditCardUpdate(BaseModel): # 修改模型通常不強制繼承 BaseSchema 的轉化，或維持簡單
    name: Optional[str] = None
    billing_day: Optional[int] = None
    reward_rules: Optional[List[dict]] = None
    alert_threshold: Optional[float] = None

class CreditCard(CardBase, AuditSchema):
    id: int
    is_deleted: bool

class CardStatus(BaseSchema):
    card_name: str
    current_cycle_total: float
    remaining_for_max_reward: Optional[float] = None
    next_billing_date: str
    status_message: str
