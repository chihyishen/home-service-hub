from sqlalchemy import Column, Integer, String, Boolean
from ..database import Base, TimestampMixin

class PaymentMethod(Base, TimestampMixin):
    __tablename__ = "payment_methods"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    is_active = Column(Boolean, default=True)
