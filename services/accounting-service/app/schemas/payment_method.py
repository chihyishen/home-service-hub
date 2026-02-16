from pydantic import Field
from typing import Optional
from . import BaseSchema, AuditSchema

class PaymentMethodBase(BaseSchema):
    name: str = Field(..., description="支付方式名稱 (例如: 現金, Line Pay, 銀行轉帳)")
    is_active: bool = Field(default=True, description="是否啟用")

class PaymentMethodCreate(PaymentMethodBase):
    pass

class PaymentMethodUpdate(BaseSchema):
    name: Optional[str] = Field(None, description="支付方式名稱")
    is_active: Optional[bool] = Field(None, description="是否啟用")

class PaymentMethod(PaymentMethodBase, AuditSchema):
    id: int
