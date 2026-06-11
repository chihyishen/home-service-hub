from sqlalchemy.orm import Session

from ...models import portfolio as models
from ...models.corporate_action import CorporateAction
from .corp_actions import _apply_corp_action_factors, _load_corp_actions_by_symbol
from .helpers import _resolve_sort_trade_date, sanitize_symbol


def _aggregate_active_holdings(
    transactions: list[models.Transaction],
    actions_by_symbol: dict[str, list[CorporateAction]] | None = None,
) -> dict[str, dict[str, object]]:
    holdings: dict[str, dict[str, object]] = {}

    adjusted = _apply_corp_action_factors(transactions, actions_by_symbol)

    for transaction in sorted(
        adjusted,
        key=lambda item: (_resolve_sort_trade_date(item.trade_date), item.id or float("inf")),
    ):
        t_side = getattr(transaction, "position_side", None) or models.PositionSide.LONG
        if not isinstance(t_side, models.PositionSide):
            t_side = models.PositionSide(t_side)
        if t_side is not models.PositionSide.LONG:
            continue

        symbol = sanitize_symbol(transaction.symbol)
        if symbol not in holdings:
            holdings[symbol] = {
                "symbol": symbol,
                "name": transaction.name,
                "total_quantity": 0,
            }

        holdings[symbol]["total_quantity"] += (
            transaction.quantity
            if transaction.type == models.TransactionType.BUY
            else -transaction.quantity
        )
        if transaction.name and not holdings[symbol]["name"]:
            holdings[symbol]["name"] = transaction.name

    return {
        symbol: holding
        for symbol, holding in holdings.items()
        if int(holding["total_quantity"]) > 0
    }


def get_active_holdings(db: Session) -> dict[str, dict[str, object]]:
    transactions = (
        db.query(models.Transaction)
        .order_by(models.Transaction.trade_date, models.Transaction.id)
        .all()
    )
    return _aggregate_active_holdings(transactions, _load_corp_actions_by_symbol(db))


def get_ever_held_symbols(db: Session) -> set:
    """Every symbol the user has ever transacted or received a dividend for.

    This is the allow-list for ``price_history``: a symbol stays in scope
    even after it is fully sold, so its chart history remains available.
    """
    tx_symbols = db.query(models.Transaction.symbol).distinct()
    dv_symbols = db.query(models.Dividend.symbol).distinct()
    return {s for (s,) in tx_symbols} | {s for (s,) in dv_symbols}


def _get_quote_status(active_symbols: list[str], quotes: dict[str, dict]) -> str:
    if not active_symbols:
        return "ok"
    if not quotes:
        return "unavailable"
    if len(quotes) < len(active_symbols):
        return "partial"
    return "ok"
