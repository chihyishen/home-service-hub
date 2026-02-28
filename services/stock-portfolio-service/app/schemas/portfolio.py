from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional
from enum import Enum

class TransactionType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

class TransactionBase(BaseModel):
    symbol: str
    name: Optional[str] = None
    type: TransactionType
    quantity: int
    price: float
    trade_date: Optional[datetime] = None
    fee: float = 0.0
    tax: float = 0.0

class TransactionCreate(TransactionBase):
    pass

class Transaction(TransactionBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class DividendBase(BaseModel):
    symbol: str
    amount: float
    ex_dividend_date: datetime
    received_date: Optional[datetime] = None

class DividendCreate(DividendBase):
    pass

class Dividend(DividendBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# --- 計算後的模型 ---

class StockHolding(BaseModel):
    symbol: str
    name: Optional[str] = None
    total_quantity: int
    avg_cost: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_percent: float
    day_change_amount: float = 0.0      # 單日漲跌金額
    day_change_percent: float = 0.0     # 單日漲跌幅(%)
    day_pnl: float = 0.0                # 單日損益
    total_dividends: float = 0.0
    total_pnl_with_dividend: float # 含息損益

class PortfolioSummary(BaseModel):
    total_market_value: float
    total_cost: float
    total_unrealized_pnl: float
    total_unrealized_pnl_percent: float
    total_day_pnl: float = 0.0          # 投資組合今日總損益
    total_dividends: float
    holdings: List[StockHolding]
