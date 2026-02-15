from sqlalchemy import Column, Integer, String, Float, JSON, Boolean
from sqlalchemy.orm import relationship
from ..database import Base

class CreditCard(Base):
    __tablename__ = "credit_cards"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    billing_day = Column(Integer)
    reward_rules = Column(JSON, nullable=True)
    alert_threshold = Column(Float, default=5000.0)
    is_deleted = Column(Boolean, default=False)

    # 使用字串 "Transaction" 而非類別對象，避免循環引用
    transactions = relationship("Transaction", back_populates="card")
    subscriptions = relationship("Subscription", back_populates="card")
    installments = relationship("Installment", back_populates="card")
    payment_routes = relationship("PaymentRoute", back_populates="card")
