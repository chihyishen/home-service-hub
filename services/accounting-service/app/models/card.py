from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from ..database import Base, TimestampMixin


class CreditCard(Base, TimestampMixin):
    __tablename__ = "credit_cards"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    billing_day = Column(Integer)
    reward_cycle_type = Column(String, default="BILLING_CYCLE") # BILLING_CYCLE or CALENDAR_MONTH
    alert_threshold = Column(Integer, default=5000)
    default_payment_method = Column(String, default="Apple Pay")
    alert_payment_method = Column(String, nullable=True)  # 若設定，預警門檻僅計算此支付工具的消費

    transactions = relationship("Transaction", back_populates="card")
    subscriptions = relationship("Subscription", back_populates="card")
    installments = relationship("Installment", back_populates="card")
