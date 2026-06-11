"""Stable facade for portfolio service — re-exports the public API.

All business logic lives in the ``app.services.portfolio`` subpackage.
This module exists so that the 10+ app modules and 15+ test files that do
``from ..services import portfolio_service`` (or access its attributes
dynamically via monkeypatch) continue to work unchanged.

Re-exports use explicit ``as`` aliases (``from .x import name as name``)
so ruff's F401 rule treats them as intentional public re-exports.
"""

from .portfolio.cashflows import _calculate_xirr as _calculate_xirr
from .portfolio.corp_actions import _AdjustedTransaction as _AdjustedTransaction
from .portfolio.corp_actions import _apply_corp_action_factors as _apply_corp_action_factors
from .portfolio.corp_actions import _factor_for_trade as _factor_for_trade
from .portfolio.corp_actions import _load_adjusted_transactions as _load_adjusted_transactions
from .portfolio.corp_actions import _load_corp_actions_by_symbol as _load_corp_actions_by_symbol
from .portfolio.crud import _DIVIDEND_SORT_FIELDS as _DIVIDEND_SORT_FIELDS
from .portfolio.crud import _TRANSACTION_SORT_FIELDS as _TRANSACTION_SORT_FIELDS
from .portfolio.crud import _parse_sort as _parse_sort
from .portfolio.crud import create_dividend as create_dividend
from .portfolio.crud import create_transaction as create_transaction
from .portfolio.crud import delete_dividend as delete_dividend
from .portfolio.crud import delete_transaction as delete_transaction
from .portfolio.crud import list_dividends as list_dividends
from .portfolio.crud import list_transactions as list_transactions
from .portfolio.crud import update_dividend as update_dividend
from .portfolio.crud import update_transaction as update_transaction
from .portfolio.day_trade import _recompute_day_trade_flags as _recompute_day_trade_flags
from .portfolio.day_trade import _validate_symbol_ledger as _validate_symbol_ledger
from .portfolio.day_trade import _validate_transaction_ledger as _validate_transaction_ledger
from .portfolio.helpers import _env_decimal as _env_decimal
from .portfolio.helpers import _escape_like_prefix as _escape_like_prefix
from .portfolio.helpers import _is_odd_lot as _is_odd_lot
from .portfolio.helpers import _resolve_sort_trade_date as _resolve_sort_trade_date
from .portfolio.helpers import _trade_calendar_date as _trade_calendar_date
from .portfolio.helpers import sanitize_symbol as sanitize_symbol
from .portfolio.history_backfill import _is_tpex_marker as _is_tpex_marker
from .portfolio.history_backfill import _schedule_symbol_history_backfill as _schedule_symbol_history_backfill
from .portfolio.history_backfill import (
    _schedule_tpex_symbol_history_backfill as _schedule_tpex_symbol_history_backfill,
)
from .portfolio.history_backfill import _symbol_uses_tpex_history as _symbol_uses_tpex_history
from .portfolio.holdings import _aggregate_active_holdings as _aggregate_active_holdings
from .portfolio.holdings import _get_quote_status as _get_quote_status
from .portfolio.holdings import get_active_holdings as get_active_holdings
from .portfolio.holdings import get_ever_held_symbols as get_ever_held_symbols
from .portfolio.summary import _estimate_sell_costs as _estimate_sell_costs
from .portfolio.summary import get_portfolio_summary as get_portfolio_summary
