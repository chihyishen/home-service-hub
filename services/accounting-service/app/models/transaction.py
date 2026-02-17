from sqlalchemy import Column, Integer, String, Float, ForeignKey, Date, JSON, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base, TimestampMixin

class Transaction(Base, TimestampMixin):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, server_default=func.current_date())
    category = Column(String, index=True) # 舊的字串分類
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True) # 結構化分類
    item = Column(String)
    personal_amount = Column(Integer)
    actual_swipe = Column(Integer)
    payment_method = Column(String)
    card_id = Column(Integer, ForeignKey("credit_cards.id"), nullable=True)
    transaction_type = Column(String, default="EXPENSE")
    note = Column(String, nullable=True)
    tags = Column(JSON, nullable=True)
    
    # 沖銷與連結
    related_transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=True)
    
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=True)
    installment_id = Column(Integer, ForeignKey("installments.id"), nullable=True)

    card = relationship("CreditCard", back_populates="transactions")
    # 分類關聯
    category_info = relationship("Category", back_populates="transactions")
    # 自我關聯
    related_transaction = relationship("Transaction", remote_side=[id])
