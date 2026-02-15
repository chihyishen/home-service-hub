from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Date, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

class CreditCard(Base):
    __tablename__ = "credit_cards"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    billing_day = Column(Integer)  # 結帳日 (1-31)
    # 優惠規則, e.g., [{"threshold": 5000, "rate": 0.07}, {"threshold": 10000, "rate": 0.01}]
    reward_rules = Column(JSON, nullable=True)
    alert_threshold = Column(Float, default=5000.0)

    transactions = relationship("Transaction", back_populates="card")
    subscriptions = relationship("Subscription", back_populates="card")
    installments = relationship("Installment", back_populates="card")
    payment_routes = relationship("PaymentRoute", back_populates="card")

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, server_default=func.current_date())
    category = Column(String, index=True)
    item = Column(String)
    
    # 金額拆分
    personal_amount = Column(Float)  # 個人支出
    actual_swipe = Column(Float)     # 實際刷卡 (含代墊/分期)
    
    payment_method = Column(String)  # Line Pay, Apple Pay, 現金
    card_id = Column(Integer, ForeignKey("credit_cards.id"), nullable=True)
    
    note = Column(String, nullable=True)
    tags = Column(JSON, nullable=True)  # ["#UberEats", "#晚餐"]
    
    # 狀態: 'COMPLETED', 'PENDING_SUB', 'PENDING_INSTALLMENT', 'REIMBURSEMENT_REQUIRED'
    status = Column(String, default="COMPLETED")
    
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=True)
    installment_id = Column(Integer, ForeignKey("installments.id"), nullable=True)

    card = relationship("CreditCard", back_populates="transactions")

class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    amount = Column(Float)
    category = Column(String)
    day_of_month = Column(Integer)
    card_id = Column(Integer, ForeignKey("credit_cards.id"))
    active = Column(Boolean, default=True)

    card = relationship("CreditCard", back_populates="subscriptions")

class Installment(Base):
    __tablename__ = "installments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    total_amount = Column(Float)
    monthly_amount = Column(Float)
    total_periods = Column(Integer)
    remaining_periods = Column(Integer)
    start_date = Column(Date)
    card_id = Column(Integer, ForeignKey("credit_cards.id"))

    card = relationship("CreditCard", back_populates="installments")

class PaymentRoute(Base):
    __tablename__ = "payment_routes"

    id = Column(Integer, primary_key=True, index=True)
    method_name = Column(String, unique=True)  # 如: Line Pay
    card_id = Column(Integer, ForeignKey("credit_cards.id"))

    card = relationship("CreditCard", back_populates="payment_routes")
