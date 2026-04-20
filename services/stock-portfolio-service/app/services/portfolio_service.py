from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict, List, Optional, Tuple
from datetime import date as date_type
from decimal import Decimal, ROUND_HALF_UP, ROUND_DOWN
import math
import os
from ..models import portfolio as models
from ..schemas import portfolio as schemas
from .twse_service import get_stock_quotes
from shared_lib import get_tracer
tracer = get_tracer("stock-portfolio-service")


def _calculate_xirr(cash_flows: List[Tuple[date_type, Decimal]]) -> Optional[Decimal]:
    """
    Compute XIRR from a list of (date, amount) pairs.
    Returns None if calculation is impossible or fails.
    - amounts < 0: outflows (buy)
    - amounts > 0: inflows (sell, dividend, terminal market value)
    """
    if len(cash_flows) < 2:
        return None

    dates = [cf[0] for cf in cash_flows]
    if len(set(dates)) < 2:
        return None

    if cash_flows[-1][1] <= Decimal("0"):
        return None

    try:
        from pyxirr import xirr as _xirr
        result = _xirr(
            [cf[0] for cf in cash_flows],
            [float(cf[1]) for cf in cash_flows],
        )
        if result is None or not isinstance(result, float):
            return None
        if math.isnan(result) or math.isinf(result):
            return None
        return Decimal(str(round(result, 6)))
    except Exception:
        return None

def sanitize_symbol(symbol: str) -> str:
    """
    清理股票代碼：移除 .TW, .TWO (不分大小寫) 並轉為大寫，只保留前面的代碼。
    例如: 0050.TW -> 0050
    """
    if not symbol:
        return ""
    return symbol.split('.')[0].upper().strip()


def _env_decimal(name: str, default: str) -> Decimal:
    val = os.getenv(name)
    if not val:
        return Decimal(default)
    try:
        return Decimal(str(val))
    except Exception:
        return Decimal(default)


def _estimate_sell_costs(gross_market_value: Decimal) -> Decimal:
    """
    估算券商賣出成本（手續費 + 證交稅），預設口徑:
    - 手續費: 0.1425% * 2.8折 = 0.0399%
    - 證交稅: 0.1% (ETF 常見口徑)
    - 成本採整數元無條件捨去
    可用環境變數覆蓋:
    PORTFOLIO_SELL_FEE_RATE_BASE, PORTFOLIO_SELL_FEE_DISCOUNT, PORTFOLIO_SELL_TAX_RATE
    """
    fee_rate_base = _env_decimal("PORTFOLIO_SELL_FEE_RATE_BASE", "0.001425")
    fee_discount = _env_decimal("PORTFOLIO_SELL_FEE_DISCOUNT", "0.28")
    tax_rate = _env_decimal("PORTFOLIO_SELL_TAX_RATE", "0.001")
    fee = (gross_market_value * fee_rate_base * fee_discount).quantize(Decimal("1"), rounding=ROUND_DOWN)
    tax = (gross_market_value * tax_rate).quantize(Decimal("1"), rounding=ROUND_DOWN)
    return fee + tax

def get_portfolio_summary(db: Session) -> schemas.PortfolioSummary:
    """
    計算投資組合總覽，包含未實現損益與單日損益
    """
    with tracer.start_as_current_span("calculate_portfolio_summary") as span:
        # 1. 取得所有交易紀錄
        transactions = db.query(models.Transaction).order_by(models.Transaction.trade_date).all()
        # 2. 取得所有股利紀錄
        dividends = db.query(models.Dividend).all()

        # 整理每檔股票的狀態
        holdings_map = {}
        cashflows_map: Dict[str, List[Tuple[date_type, Decimal]]] = {}

        # 股利統計
        dividend_map = {}
        for d in dividends:
            symbol = sanitize_symbol(d.symbol)
            dividend_map[symbol] = dividend_map.get(symbol, Decimal("0.0")) + Decimal(str(d.amount))
            # XIRR: dividend inflow
            cf_date = d.ex_dividend_date.date() if hasattr(d.ex_dividend_date, 'date') else d.ex_dividend_date
            cashflows_map.setdefault(symbol, []).append((cf_date, Decimal(str(d.amount))))

        # 交易統計 (計算平均成本與持股數)
        for t in transactions:
            symbol = sanitize_symbol(t.symbol)
            if symbol not in holdings_map:
                holdings_map[symbol] = {
                    "symbol": symbol,
                    "name": t.name,
                    "total_quantity": 0,
                    "total_cost": Decimal("0.0"),
                    "total_cost_ex_fee": Decimal("0.0"),
                }
            
            h = holdings_map[symbol]
            if t.type == models.TransactionType.BUY:
                h["total_quantity"] += t.quantity
                # 買入總成本 = (單價 * 股數) + 手續費
                h["total_cost"] += (Decimal(t.quantity) * Decimal(str(t.price))) + Decimal(str(t.fee or "0.0"))
                # 成交均價口徑(不含手續費)
                h["total_cost_ex_fee"] += (Decimal(t.quantity) * Decimal(str(t.price)))
                # XIRR: buy outflow
                cf_date = t.trade_date.date() if hasattr(t.trade_date, 'date') else t.trade_date
                outflow = -((Decimal(t.quantity) * Decimal(str(t.price))) + Decimal(str(t.fee or "0.0")) + Decimal(str(t.tax or "0.0")))
                cashflows_map.setdefault(symbol, []).append((cf_date, outflow))
            elif t.type == models.TransactionType.SELL:
                if h["total_quantity"] > 0:
                    avg_unit_cost = h["total_cost"] / Decimal(h["total_quantity"])
                    avg_unit_cost_ex_fee = h["total_cost_ex_fee"] / Decimal(h["total_quantity"])
                    h["total_quantity"] -= t.quantity
                    # 賣出時減少庫存成本 (簡易已實現計算方式)
                    h["total_cost"] -= (Decimal(t.quantity) * avg_unit_cost)
                    h["total_cost_ex_fee"] -= (Decimal(t.quantity) * avg_unit_cost_ex_fee)
                    # XIRR: sell inflow
                    cf_date = t.trade_date.date() if hasattr(t.trade_date, 'date') else t.trade_date
                    inflow = (Decimal(t.quantity) * Decimal(str(t.price))) - Decimal(str(t.fee or "0.0")) - Decimal(str(t.tax or "0.0"))
                    cashflows_map.setdefault(symbol, []).append((cf_date, inflow))
                else:
                    pass

        # 只顯示還有持股的股票
        active_symbols = [s for s, h in holdings_map.items() if h["total_quantity"] > 0]
        
        # 3. 取得即時報價
        quotes = get_stock_quotes(active_symbols)

        holdings_list = []
        total_market_value = Decimal("0.0")
        total_cost = Decimal("0.0")
        total_unrealized_pnl = Decimal("0.0")
        total_day_pnl = Decimal("0.0")
        total_dividends = sum(dividend_map.values(), Decimal("0.0"))

        for symbol in active_symbols:
            h = holdings_map[symbol]
            quote = quotes.get(symbol, {})
            # 如果抓不到即時價格，暫以 0 處理，但在計算損益時應避免顯示全賠
            current_price = quote.get("current_price", Decimal("0.0"))
            yesterday_close = quote.get("yesterday_close", Decimal("0.0"))
            
            total_qty_dec = Decimal(h["total_quantity"])
            
            # 平均成本計算（成交均價口徑，不含手續費）
            avg_cost = (h["total_cost_ex_fee"] / total_qty_dec).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            
            # 市值與未實現損益（以券商口徑估算賣出後淨額）
            gross_market_value = (total_qty_dec * current_price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            estimated_sell_costs = _estimate_sell_costs(gross_market_value)
            market_value = (gross_market_value - estimated_sell_costs).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            
            if current_price > 0:
                unrealized_pnl = (market_value - h["total_cost"]).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                pnl_percent = ((unrealized_pnl / h["total_cost"]) * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if h["total_cost"] > 0 else Decimal("0.0")
                
                day_change_amount = (current_price - yesterday_close).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                day_change_percent = ((day_change_amount / yesterday_close) * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if yesterday_close > 0 else Decimal("0.0")
                day_pnl = (day_change_amount * total_qty_dec).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            else:
                # 沒股價時損益先歸零，避免誤導
                unrealized_pnl = Decimal("0.0")
                pnl_percent = Decimal("0.0")
                day_change_amount = Decimal("0.0")
                day_change_percent = Decimal("0.0")
                day_pnl = Decimal("0.0")
            
            stock_div = dividend_map.get(symbol, Decimal("0.0")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

            # Per-stock XIRR: append terminal market value at today
            stock_xirr: Optional[Decimal] = None
            if current_price > 0 and symbol in cashflows_map:
                today = date_type.today()
                stock_flows = sorted(cashflows_map.get(symbol, []), key=lambda x: x[0])
                stock_flows_with_terminal = stock_flows + [(today, market_value)]
                stock_xirr = _calculate_xirr(stock_flows_with_terminal)

            holdings_list.append(schemas.StockHolding(
                symbol=symbol,
                name=quote.get("name") or h["name"] or symbol,
                total_quantity=h["total_quantity"],
                avg_cost=avg_cost,
                current_price=current_price,
                market_value=market_value,
                unrealized_pnl=unrealized_pnl,
                unrealized_pnl_percent=pnl_percent,
                day_change_amount=day_change_amount,
                day_change_percent=day_change_percent,
                day_pnl=day_pnl,
                total_dividends=stock_div,
                total_pnl_with_dividend=(unrealized_pnl + stock_div).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
                xirr=stock_xirr
            ))

            if current_price > 0:
                total_market_value += market_value
                total_unrealized_pnl += unrealized_pnl
                total_day_pnl += day_pnl
            
            total_cost += h["total_cost"]

        total_pnl_percent = ((total_unrealized_pnl / total_cost) * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if total_cost > 0 else Decimal("0.0")

        # Portfolio XIRR: aggregate all cash flows across all held symbols
        all_cashflows: List[Tuple[date_type, Decimal]] = []
        for symbol in active_symbols:
            all_cashflows.extend(cashflows_map.get(symbol, []))
        all_cashflows.sort(key=lambda x: x[0])
        portfolio_xirr: Optional[Decimal] = None
        if total_market_value > 0 and all_cashflows:
            all_cashflows_with_terminal = all_cashflows + [(date_type.today(), total_market_value)]
            portfolio_xirr = _calculate_xirr(all_cashflows_with_terminal)

        return schemas.PortfolioSummary(
            total_market_value=total_market_value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            total_cost=total_cost.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            total_unrealized_pnl=total_unrealized_pnl.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            total_unrealized_pnl_percent=total_pnl_percent,
            total_day_pnl=total_day_pnl.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            total_dividends=total_dividends.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            holdings=holdings_list,
            portfolio_xirr=portfolio_xirr
        )

def create_transaction(db: Session, transaction: schemas.TransactionCreate):
    # Task 2: 清理 symbol
    transaction_data = transaction.model_dump()
    transaction_data["symbol"] = sanitize_symbol(transaction_data["symbol"])
    
    db_transaction = models.Transaction(**transaction_data)
    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)
    return db_transaction

def create_dividend(db: Session, dividend: schemas.DividendCreate):
    # Task 2: 清理 symbol
    dividend_data = dividend.model_dump()
    dividend_data["symbol"] = sanitize_symbol(dividend_data["symbol"])

    db_dividend = models.Dividend(**dividend_data)
    db.add(db_dividend)
    db.commit()
    db.refresh(db_dividend)
    return db_dividend

def update_transaction(db: Session, transaction_id: int, transaction_update: schemas.TransactionCreate):
    db_transaction = db.query(models.Transaction).filter(models.Transaction.id == transaction_id).first()
    if not db_transaction:
        return None
    
    update_data = transaction_update.model_dump()
    update_data["symbol"] = sanitize_symbol(update_data["symbol"])
    
    for key, value in update_data.items():
        setattr(db_transaction, key, value)
    
    db.commit()
    db.refresh(db_transaction)
    return db_transaction

def delete_transaction(db: Session, transaction_id: int):
    db_transaction = db.query(models.Transaction).filter(models.Transaction.id == transaction_id).first()
    if not db_transaction:
        return False
    db.delete(db_transaction)
    db.commit()
    return True

def update_dividend(db: Session, dividend_id: int, dividend_update: schemas.DividendCreate):
    db_dividend = db.query(models.Dividend).filter(models.Dividend.id == dividend_id).first()
    if not db_dividend:
        return None
    
    update_data = dividend_update.model_dump()
    update_data["symbol"] = sanitize_symbol(update_data["symbol"])
    
    for key, value in update_data.items():
        setattr(db_dividend, key, value)
    
    db.commit()
    db.refresh(db_dividend)
    return db_dividend

def delete_dividend(db: Session, dividend_id: int):
    db_dividend = db.query(models.Dividend).filter(models.Dividend.id == dividend_id).first()
    if not db_dividend:
        return False
    db.delete(db_dividend)
    db.commit()
    return True
