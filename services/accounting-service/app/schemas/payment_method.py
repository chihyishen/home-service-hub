
from pydantic import Field

from . import AuditSchema, BaseSchema


class PaymentMethodBase(BaseSchema):
    name: str = Field(..., description="支付方式名稱 (例如: 現金, Line Pay, 銀行轉帳)")
    is_active: bool = Field(default=True, description="是否啟用")

class PaymentMethodCreate(PaymentMethodBase):
    pass

class PaymentMethodUpdate(BaseSchema):
    name: str | None = Field(None, description="支付方式名稱")
    is_active: bool | None = Field(None, description="是否啟用")

class PaymentMethod(PaymentMethodBase, AuditSchema):
    id: int
