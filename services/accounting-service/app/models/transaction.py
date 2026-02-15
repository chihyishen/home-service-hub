from sqlalchemy import Column, Integer, String, Float, ForeignKey, Date, JSON, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, server_default=func.current_date())
    category = Column(String, index=True)
    item = Column(String)
    personal_amount = Column(Float)
    actual_swipe = Column(Float)
    payment_method = Column(String)
    card_id = Column(Integer, ForeignKey("credit_cards.id"), nullable=True)
    transaction_type = Column(String, default="EXPENSE")  # INCOME, EXPENSE
    note = Column(String, nullable=True)
    tags = Column(JSON, nullable=True)
    status = Column(String, default="COMPLETED")
    is_deleted = Column(Boolean, default=False)
    
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=True)
    installment_id = Column(Integer, ForeignKey("installments.id"), nullable=True)

    # 這裡同樣使用字串參考
    card = relationship("CreditCard", back_populates="transactions")
