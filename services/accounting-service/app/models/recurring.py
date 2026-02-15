from sqlalchemy import Column, Integer, String, Float, ForeignKey, Boolean, Date
from sqlalchemy.orm import relationship
from ..database import Base, TimestampMixin

class Subscription(Base, TimestampMixin):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    amount = Column(Float)
    category = Column(String)
    day_of_month = Column(Integer)
    card_id = Column(Integer, ForeignKey("credit_cards.id"))
    active = Column(Boolean, default=True)
    is_deleted = Column(Boolean, default=False)

    card = relationship("CreditCard", back_populates="subscriptions")

class Installment(Base, TimestampMixin):
    __tablename__ = "installments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    total_amount = Column(Float)
    monthly_amount = Column(Float)
    total_periods = Column(Integer)
    remaining_periods = Column(Integer)
    start_date = Column(Date)
    card_id = Column(Integer, ForeignKey("credit_cards.id"))
    is_deleted = Column(Boolean, default=False)

    card = relationship("CreditCard", back_populates="installments")

class PaymentRoute(Base):
    __tablename__ = "payment_routes"

    id = Column(Integer, primary_key=True, index=True)
    method_name = Column(String, unique=True)
    card_id = Column(Integer, ForeignKey("credit_cards.id"))

    card = relationship("CreditCard", back_populates="payment_routes")
