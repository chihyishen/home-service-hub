from sqlalchemy import Column, Integer, String, Float, DateTime, Enum
from sqlalchemy.sql import func
import enum
from ..database import Base, TimestampMixin

class TransactionType(str, enum.Enum):
    BUY = "BUY"
    SELL = "SELL"

class Transaction(Base, TimestampMixin):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True, nullable=False)  # 股票代碼, e.g., 2330
    name = Column(String, nullable=True)               # 股票名稱
    type = Column(Enum(TransactionType), nullable=False)
    quantity = Column(Integer, nullable=False)         # 股數
    price = Column(Float, nullable=False)              # 成交單價
    trade_date = Column(DateTime(timezone=True), server_default=func.now())
    fee = Column(Float, default=0.0)                   # 手續費 (選填)
    tax = Column(Float, default=0.0)                   # 交易稅 (選填)

class Dividend(Base, TimestampMixin):
    __tablename__ = "dividends"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True, nullable=False)
    amount = Column(Float, nullable=False)             # 總金額
    ex_dividend_date = Column(DateTime(timezone=True), nullable=False) # 除息日
    received_date = Column(DateTime(timezone=True), server_default=func.now()) # 入帳日
