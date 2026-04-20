from pydantic import BaseModel, Field
from datetime import datetime, date
from typing import List, Optional
from enum import Enum
from decimal import Decimal

class TransactionType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

class TransactionBase(BaseModel):
    symbol: str
    name: Optional[str] = None
    type: TransactionType
    quantity: int
    price: Decimal = Field(..., decimal_places=2)
    trade_date: Optional[datetime] = None
    fee: Decimal = Field(default=Decimal("0.0"), decimal_places=2)
    tax: Decimal = Field(default=Decimal("0.0"), decimal_places=2)

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
    amount: Decimal = Field(..., decimal_places=2)
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
    avg_cost: Decimal
    current_price: Decimal
    market_value: Decimal
    unrealized_pnl: Decimal
    unrealized_pnl_percent: Decimal
    day_change_amount: Decimal = Decimal("0.0")      # 單日漲跌金額
    day_change_percent: Decimal = Decimal("0.0")     # 單日漲跌幅(%)
    day_pnl: Decimal = Decimal("0.0")                # 單日損益
    total_dividends: Decimal = Decimal("0.0")
    total_pnl_with_dividend: Decimal # 含息損益
    xirr: Optional[Decimal] = None   # 年化報酬率，如 0.1523 = 15.23%

class PortfolioSummary(BaseModel):
    total_market_value: Decimal
    total_cost: Decimal
    total_unrealized_pnl: Decimal
    total_unrealized_pnl_percent: Decimal
    total_day_pnl: Decimal = Decimal("0.0")          # 投資組合今日總損益
    total_dividends: Decimal
    holdings: List[StockHolding]
    portfolio_xirr: Optional[Decimal] = None          # 整體投資組合年化報酬率


class ExDividendRecord(BaseModel):
    symbol: str
    name: str
    ex_dividend_date: Optional[date] = None     # 除息日
    ex_rights_date: Optional[date] = None       # 除權日
    cash_dividend: Optional[str] = None         # 現金股利（字串保留原始精度）
    stock_dividend: Optional[str] = None        # 股票股利
