from decimal import ROUND_DOWN, Decimal

from sqlalchemy.orm import Session

from ...models import portfolio as models
from ...models.corporate_action import CorporateAction
from .helpers import sanitize_symbol


class _AdjustedTransaction:
    """Read-only view of a Transaction with a corporate-action factor applied.

    The view duck-types ``models.Transaction`` over the fields the
    aggregation logic touches. ``quantity`` is multiplied by ``factor`` and
    ``price`` is divided by it; cost basis (qty * price) is preserved.
    Fees and taxes stay nominal.
    """

    __slots__ = ("_base", "_factor")

    def __init__(self, base: models.Transaction, factor: Decimal):
        self._base = base
        self._factor = factor

    @property
    def id(self):
        return self._base.id

    @property
    def symbol(self):
        return self._base.symbol

    @property
    def name(self):
        return self._base.name

    @property
    def type(self):
        return self._base.type

    @property
    def trade_date(self):
        return self._base.trade_date

    @property
    def quantity(self):
        if self._factor == 1:
            return self._base.quantity
        return int(
            (Decimal(self._base.quantity) * self._factor).to_integral_value(rounding=ROUND_DOWN)
        )

    @property
    def price(self):
        if self._factor == 1:
            return self._base.price
        return self._base.price / self._factor

    @property
    def fee(self):
        return self._base.fee

    @property
    def tax(self):
        return self._base.tax

    @property
    def position_side(self):
        return getattr(self._base, "position_side", models.PositionSide.LONG)

    @property
    def is_day_trade(self):
        return getattr(self._base, "is_day_trade", False)


def _factor_for_trade(actions: list[CorporateAction], trade_date) -> Decimal:
    """Cumulative product of every action strictly AFTER trade_date."""
    target = trade_date.date() if hasattr(trade_date, "date") else trade_date
    factor = Decimal(1)
    for action in actions:
        if action.effective_date > target:
            factor *= action.ratio
    return factor


def _apply_corp_action_factors(
    transactions: list[models.Transaction],
    actions_by_symbol: dict[str, list[CorporateAction]] | None,
) -> list:
    """Return transactions (or adjusted views) with factor applied."""
    if not actions_by_symbol:
        return list(transactions)
    adjusted: list = []
    for txn in transactions:
        sym_actions = actions_by_symbol.get(sanitize_symbol(txn.symbol), None)
        if not sym_actions:
            adjusted.append(txn)
            continue
        factor = _factor_for_trade(sym_actions, txn.trade_date)
        if factor == 1:
            adjusted.append(txn)
        else:
            adjusted.append(_AdjustedTransaction(txn, factor))
    return adjusted


def _load_corp_actions_by_symbol(db: Session) -> dict[str, list[CorporateAction]]:
    rows = (
        db.query(CorporateAction)
        .order_by(CorporateAction.effective_date.asc(), CorporateAction.id.asc())
        .all()
    )
    grouped: dict[str, list[CorporateAction]] = {}
    for row in rows:
        grouped.setdefault(sanitize_symbol(row.symbol), []).append(row)
    return grouped


def _load_adjusted_transactions(db: Session) -> list:
    """Load transactions in the portfolio-summary order with split factors applied."""
    transactions = (
        db.query(models.Transaction)
        .order_by(
            models.Transaction.trade_date,
            models.Transaction.type.asc(),
            models.Transaction.id,
        )
        .all()
    )
    return _apply_corp_action_factors(transactions, _load_corp_actions_by_symbol(db))
