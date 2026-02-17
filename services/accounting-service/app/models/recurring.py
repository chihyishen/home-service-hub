from sqlalchemy import Column, Integer, String, Float, ForeignKey, Boolean, Date
from sqlalchemy.orm import relationship
from ..database import Base, TimestampMixin

class Subscription(Base, TimestampMixin):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    amount = Column(Integer)
    category = Column(String)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    sub_type = Column(String, default="SUBSCRIPTION") # FIXED_EXPENSE or SUBSCRIPTION
    payment_method = Column(String, default="信用卡")
    day_of_month = Column(Integer)
    card_id = Column(Integer, ForeignKey("credit_cards.id"))
    active = Column(Boolean, default=True)

    card = relationship("CreditCard", back_populates="subscriptions")
    category_info = relationship("Category")

class Installment(Base, TimestampMixin):
    __tablename__ = "installments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    total_amount = Column(Integer)
    monthly_amount = Column(Integer)
    payment_method = Column(String, default="信用卡")
    total_periods = Column(Integer)
    remaining_periods = Column(Integer)
    start_date = Column(Date)
    card_id = Column(Integer, ForeignKey("credit_cards.id"))

    card = relationship("CreditCard", back_populates="installments")
