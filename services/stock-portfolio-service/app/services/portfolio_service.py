from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict
from decimal import Decimal, ROUND_HALF_UP
from ..models import portfolio as models
from ..schemas import portfolio as schemas
from .twse_service import get_stock_quotes
from ..tracing import tracer

def sanitize_symbol(symbol: str) -> str:
    """
    清理股票代碼：移除 .TW, .TWO (不分大小寫) 並轉為大寫，只保留前面的代碼。
    例如: 0050.TW -> 0050
    """
    if not symbol:
        return ""
    return symbol.split('.')[0].upper().strip()

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
        
        # 股利統計
        dividend_map = {}
        for d in dividends:
            symbol = sanitize_symbol(d.symbol)
            dividend_map[symbol] = dividend_map.get(symbol, Decimal("0.0")) + Decimal(str(d.amount))

        # 交易統計 (計算平均成本與持股數)
        for t in transactions:
            symbol = sanitize_symbol(t.symbol)
            if symbol not in holdings_map:
                holdings_map[symbol] = {
                    "symbol": symbol,
                    "name": t.name,
                    "total_quantity": 0,
                    "total_cost": Decimal("0.0"),
                }
            
            h = holdings_map[symbol]
            if t.type == models.TransactionType.BUY:
                h["total_quantity"] += t.quantity
                # 買入總成本 = (單價 * 股數) + 手續費
                h["total_cost"] += (Decimal(t.quantity) * Decimal(str(t.price))) + Decimal(str(t.fee or "0.0"))
            elif t.type == models.TransactionType.SELL:
                if h["total_quantity"] > 0:
                    avg_unit_cost = h["total_cost"] / Decimal(h["total_quantity"])
                    h["total_quantity"] -= t.quantity
                    # 賣出時減少庫存成本 (簡易已實現計算方式)
                    h["total_cost"] -= (Decimal(t.quantity) * avg_unit_cost)
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
            current_price = quote.get("current_price", Decimal("0.0"))
            yesterday_close = quote.get("yesterday_close", Decimal("0.0"))
            
            total_qty_dec = Decimal(h["total_quantity"])
            
            # 平均成本計算
            avg_cost = (h["total_cost"] / total_qty_dec).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            
            # 市值與未實現損益
            market_value = (total_qty_dec * current_price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            unrealized_pnl = (market_value - h["total_cost"]).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            pnl_percent = ((unrealized_pnl / h["total_cost"]) * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if h["total_cost"] > 0 else Decimal("0.0")
            
            # 單日損益計算
            day_change_amount = (current_price - yesterday_close).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            day_change_percent = ((day_change_amount / yesterday_close) * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if yesterday_close > 0 else Decimal("0.0")
            day_pnl = (day_change_amount * total_qty_dec).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            
            stock_div = dividend_map.get(symbol, Decimal("0.0")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

            holdings_list.append(schemas.StockHolding(
                symbol=symbol,
                name=quote.get("name") or h["name"],
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
                total_pnl_with_dividend=(unrealized_pnl + stock_div).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            ))

            total_market_value += market_value
            total_cost += h["total_cost"]
            total_unrealized_pnl += unrealized_pnl
            total_day_pnl += day_pnl

        total_pnl_percent = ((total_unrealized_pnl / total_cost) * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if total_cost > 0 else Decimal("0.0")

        return schemas.PortfolioSummary(
            total_market_value=total_market_value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            total_cost=total_cost.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            total_unrealized_pnl=total_unrealized_pnl.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            total_unrealized_pnl_percent=total_pnl_percent,
            total_day_pnl=total_day_pnl.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            total_dividends=total_dividends.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            holdings=holdings_list
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
