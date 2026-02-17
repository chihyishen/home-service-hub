from pydantic import Field
from typing import Optional
from . import BaseSchema

class PaymentRouteBase(BaseSchema):
    method_name: str = Field(..., description="支付方式名稱 (如: Line Pay)")
    card_id: int = Field(..., description="預設關聯的信用卡 ID")

class PaymentRouteCreate(PaymentRouteBase):
    pass

class PaymentRouteUpdate(BaseSchema):
    method_name: Optional[str] = None
    card_id: Optional[int] = None

class PaymentRoute(PaymentRouteBase):
    id: int
