from sqlalchemy import CheckConstraint, Column, Integer, String, Numeric, DateTime, Enum, Index
from sqlalchemy.sql import func
import enum
from ..database import Base, TimestampMixin

class TransactionType(str, enum.Enum):
    BUY = "BUY"
    SELL = "SELL"

class Transaction(Base, TimestampMixin):
    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint("length(trim(symbol)) > 0", name="ck_transactions_symbol_not_blank"),
        CheckConstraint("quantity > 0", name="ck_transactions_quantity_positive"),
        CheckConstraint("price > 0", name="ck_transactions_price_positive"),
        CheckConstraint("coalesce(fee, 0) >= 0", name="ck_transactions_fee_nonnegative"),
        CheckConstraint("coalesce(tax, 0) >= 0", name="ck_transactions_tax_nonnegative"),
        Index("ix_transactions_symbol_trade_date", "symbol", "trade_date"),
    )

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True, nullable=False)  # 股票代碼, e.g., 2330
    name = Column(String, nullable=True)               # 股票名稱
    type = Column(Enum(TransactionType), nullable=False)
    quantity = Column(Integer, nullable=False)         # 股數
    price = Column(Numeric(12, 2), nullable=False)              # 成交單價
    trade_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    fee = Column(Numeric(12, 2), default=0.0)                   # 手續費 (選填)
    tax = Column(Numeric(12, 2), default=0.0)                   # 交易稅 (選填)

class Dividend(Base, TimestampMixin):
    __tablename__ = "dividends"
    __table_args__ = (
        CheckConstraint("length(trim(symbol)) > 0", name="ck_dividends_symbol_not_blank"),
        CheckConstraint("amount > 0", name="ck_dividends_amount_positive"),
    )

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True, nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)             # 總金額
    ex_dividend_date = Column(DateTime(timezone=True), nullable=False, index=True) # 除息日
    received_date = Column(DateTime(timezone=True), server_default=func.now()) # 入帳日
