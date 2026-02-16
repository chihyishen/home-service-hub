from sqlalchemy import Column, Integer, String, Float, JSON, Boolean
from sqlalchemy.orm import relationship
from ..database import Base, TimestampMixin

class CreditCard(Base, TimestampMixin):
    __tablename__ = "credit_cards"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    billing_day = Column(Integer)
    reward_cycle_type = Column(String, default="BILLING_CYCLE") # BILLING_CYCLE or CALENDAR_MONTH
    reward_rules = Column(JSON, nullable=True)
    alert_threshold = Column(Integer, default=5000)

    transactions = relationship("Transaction", back_populates="card")
    subscriptions = relationship("Subscription", back_populates="card")
    installments = relationship("Installment", back_populates="card")
    payment_routes = relationship("PaymentRoute", back_populates="card")
