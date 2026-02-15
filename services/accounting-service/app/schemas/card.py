from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional

class CardBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str = Field(..., description="卡片名稱", examples=["台新 FlyGo"])
    billing_day: int = Field(..., description="結帳日 (1-31)", examples=[10])
    reward_rules: Optional[List[dict]] = Field(default=None, description="回饋規則")
    alert_threshold: float = Field(default=5000.0, description="消費提醒閾值")

class CreditCardCreate(CardBase):
    pass

class CreditCardUpdate(BaseModel):
    name: Optional[str] = None
    billing_day: Optional[int] = None
    reward_rules: Optional[List[dict]] = None
    alert_threshold: Optional[float] = None

class CreditCard(CardBase):
    id: int
    is_deleted: bool

class CardStatus(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    card_name: str
    current_cycle_total: float
    remaining_for_max_reward: Optional[float] = None
    next_billing_date: str # 這裡改用字串或 date 均可
    status_message: str
