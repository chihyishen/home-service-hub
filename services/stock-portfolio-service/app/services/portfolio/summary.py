import logging
from datetime import date as date_type
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal

from shared_lib import get_tracer
from sqlalchemy.orm import Session

from ...models import portfolio as models
from ...schemas import portfolio as schemas
from ..twse_service import get_stock_quotes
from .cashflows import _calculate_xirr
from .corp_actions import _apply_corp_action_factors, _load_corp_actions_by_symbol
from .helpers import _env_decimal, sanitize_symbol
from .holdings import _aggregate_active_holdings, _get_quote_status

logger = logging.getLogger(__name__)

tracer = get_tracer("stock-portfolio-service")


def _estimate_sell_costs(gross_market_value: Decimal) -> Decimal:
    """
    估算券商賣出成本（手續費 + 證交稅），預設口徑:
    - 手續費: 0.1425% * 2.8折 = 0.0399%
    - 證交稅: 0.1% (ETF 常見口徑)
    - 成本採整數元無條件捨去
    - 最低手續費: 1 元（國泰證券 2.8 折期間電子下單低消 1 元；
      若實際扣費為 0 元的小額部位，估算仍保留 1 元偏保守）
    可用環境變數覆蓋:
    PORTFOLIO_SELL_FEE_RATE_BASE, PORTFOLIO_SELL_FEE_DISCOUNT,
    PORTFOLIO_SELL_TAX_RATE, PORTFOLIO_SELL_MIN_FEE
    """
    fee_rate_base = _env_decimal("PORTFOLIO_SELL_FEE_RATE_BASE", "0.001425")
    fee_discount = _env_decimal("PORTFOLIO_SELL_FEE_DISCOUNT", "0.28")
    tax_rate = _env_decimal("PORTFOLIO_SELL_TAX_RATE", "0.001")
    min_fee = _env_decimal("PORTFOLIO_SELL_MIN_FEE", "1")
    fee = (gross_market_value * fee_rate_base * fee_discount).quantize(Decimal("1"), rounding=ROUND_DOWN)
    if gross_market_value > 0:
        fee = max(fee, min_fee)
    tax = (gross_market_value * tax_rate).quantize(Decimal("1"), rounding=ROUND_DOWN)
    return fee + tax

def get_portfolio_summary(db: Session) -> schemas.PortfolioSummary:
    """
    計算投資組合總覽，包含未實現損益與單日損益
    """
    with tracer.start_as_current_span("calculate_portfolio_summary") as span:
        # 1. 取得所有交易紀錄
        # Within the same trade_date, force BUY before SELL so a day-trade
        # whose SELL row has a lower id than its BUY cannot drop the SELL
        # silently against qty=0 and leave phantom holdings.
        transactions = (
            db.query(models.Transaction)
            .order_by(
                models.Transaction.trade_date,
                models.Transaction.type.asc(),  # BUY < SELL alphabetically
                models.Transaction.id,
            )
            .all()
        )
        # 2. 取得所有股利紀錄
        dividends = db.query(models.Dividend).all()
        actions_by_symbol = _load_corp_actions_by_symbol(db)
        adjusted_transactions = _apply_corp_action_factors(transactions, actions_by_symbol)
        from ..realized_pnl_service import iter_realized_events
        realized_events = list(iter_realized_events(adjusted_transactions))
        realized_pnl_by_symbol: dict[str, Decimal] = {}
        for event in realized_events:
            realized_pnl_by_symbol[event.symbol] = (
                realized_pnl_by_symbol.get(event.symbol, Decimal("0.0"))
                + event.realized_pnl
            )
        active_holdings = _aggregate_active_holdings(transactions, actions_by_symbol)
        active_symbols = list(active_holdings.keys())

        span.set_attribute("portfolio.transaction_count", len(transactions))
        span.set_attribute("portfolio.dividend_count", len(dividends))
        span.set_attribute("portfolio.active_symbol_count", len(active_symbols))
        span.set_attribute("portfolio.corporate_action_symbol_count", len(actions_by_symbol))

        # 整理每檔股票的狀態
        holdings_map = {}
        cashflows_map: dict[str, list[tuple[date_type, Decimal]]] = {}

        # 股利統計
        dividend_map = {}
        for d in dividends:
            symbol = sanitize_symbol(d.symbol)
            dividend_map[symbol] = dividend_map.get(symbol, Decimal("0.0")) + d.amount
            # XIRR: dividend inflow
            cf_date = d.ex_dividend_date.date() if hasattr(d.ex_dividend_date, 'date') else d.ex_dividend_date
            cashflows_map.setdefault(symbol, []).append((cf_date, d.amount))

        # 交易統計 (計算平均成本與持股數，採用 corporate-action 調整後的視圖)
        # SHORT rows are intentionally skipped here — long-side holdings_map only
        # tracks long inventory. Realized P&L for short closes is aggregated via
        # `realized_pnl_by_symbol` above (sourced from iter_realized_events).
        for t in adjusted_transactions:
            t_side = getattr(t, "position_side", None) or models.PositionSide.LONG
            if not isinstance(t_side, models.PositionSide):
                t_side = models.PositionSide(t_side)
            if t_side is not models.PositionSide.LONG:
                continue

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
                h["total_cost"] += (Decimal(t.quantity) * t.price) + (t.fee or Decimal("0.0"))
                # 成交均價口徑(不含手續費)
                h["total_cost_ex_fee"] += (Decimal(t.quantity) * t.price)
                # XIRR: buy outflow
                cf_date = t.trade_date.date() if hasattr(t.trade_date, 'date') else t.trade_date
                outflow = -((Decimal(t.quantity) * t.price) + (t.fee or Decimal("0.0")) + (t.tax or Decimal("0.0")))
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
                    inflow = (Decimal(t.quantity) * t.price) - (t.fee or Decimal("0.0")) - (t.tax or Decimal("0.0"))
                    cashflows_map.setdefault(symbol, []).append((cf_date, inflow))
                else:
                    pass

        # 3. 取得即時報價
        quotes = get_stock_quotes(active_symbols)
        quote_status = _get_quote_status(active_symbols, quotes)
        span.set_attribute("portfolio.quote_count", len(quotes))
        span.set_attribute("portfolio.quote_status", quote_status)

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
            
            # 平均成本計算（含手續費 / 交易稅口徑，與損益計算一致）
            avg_cost = (h["total_cost"] / total_qty_dec).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            
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
            stock_xirr: Decimal | None = None
            if current_price > 0 and symbol in cashflows_map:
                today = date_type.today()
                stock_flows = sorted(cashflows_map.get(symbol, []), key=lambda x: x[0])
                stock_flows_with_terminal = [*stock_flows, (today, market_value)]
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
        all_cashflows: list[tuple[date_type, Decimal]] = []
        for symbol in active_symbols:
            all_cashflows.extend(cashflows_map.get(symbol, []))
        all_cashflows.sort(key=lambda x: x[0])
        portfolio_xirr: Decimal | None = None
        if total_market_value > 0 and all_cashflows:
            all_cashflows_with_terminal = [*all_cashflows, (date_type.today(), total_market_value)]
            portfolio_xirr = _calculate_xirr(all_cashflows_with_terminal)

        # Sum realised P&L across every symbol with realized events (long close +
        # short cover + no-inventory anomalies). Sourced from iter_realized_events
        # so the per-event sum invariant holds vs the realized-pnl endpoint.
        total_realized_pnl = sum(
            realized_pnl_by_symbol.values(),
            Decimal("0.0"),
        )

        return schemas.PortfolioSummary(
            total_market_value=total_market_value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            total_cost=total_cost.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            total_unrealized_pnl=total_unrealized_pnl.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            total_unrealized_pnl_percent=total_pnl_percent,
            total_day_pnl=total_day_pnl.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            total_dividends=total_dividends.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            total_realized_pnl=total_realized_pnl.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            holdings=holdings_list,
            portfolio_xirr=portfolio_xirr,
            quotes_status=quote_status,
        )
