# Tasks: split-portfolio-service-module

## 1. Scaffold the package

- [ ] 1.1 Create `app/services/portfolio/__init__.py` (empty or docstring only — the facade stays `portfolio_service.py`)
- [ ] 1.2 Add `portfolio/helpers.py` with `sanitize_symbol`, `_escape_like_prefix`, `_resolve_sort_trade_date`, `_trade_calendar_date`, `_is_odd_lot`, `_env_decimal` moved verbatim; re-export them from the facade; run full suite

## 2. Move leaf modules (no intra-package dependants yet)

- [ ] 2.1 Move `_calculate_xirr` to `portfolio/cashflows.py`; facade re-export; run `tests/unit/test_xirr.py` + full suite
- [ ] 2.2 Move `_AdjustedTransaction`, `_factor_for_trade`, `_apply_corp_action_factors`, `_load_corp_actions_by_symbol`, `_load_adjusted_transactions` to `portfolio/corp_actions.py`; facade re-export; run full suite
- [ ] 2.3 Move `_recompute_day_trade_flags`, `_validate_symbol_ledger`, `_validate_transaction_ledger` to `portfolio/day_trade.py`; facade re-export; run day-trade tests + full suite

## 3. Move holdings and summary

- [ ] 3.1 Move `_aggregate_active_holdings`, `get_active_holdings`, `get_ever_held_symbols`, `_get_quote_status` to `portfolio/holdings.py` (imports from `corp_actions`); facade re-export; verify scheduler/networth tests still pass unchanged (cross-module patch contract)
- [ ] 3.2 Move `_estimate_sell_costs` and `get_portfolio_summary` to `portfolio/summary.py`, importing `get_stock_quotes` there
- [ ] 3.3 Re-point the ~11 `get_stock_quotes` patch targets in `tests/unit/test_portfolio_service.py`, `test_realized_pnl_invariant.py`, `test_active_holdings.py` to `app.services.portfolio.summary.get_stock_quotes`; run full suite

## 4. Move backfill triggers and CRUD

- [ ] 4.1 Move `_schedule_symbol_history_backfill`, `_schedule_tpex_symbol_history_backfill`, `_is_tpex_marker`, `_symbol_uses_tpex_history` to `portfolio/history_backfill.py`; facade re-export; run backfill-trigger tests
- [ ] 4.2 Move transaction/dividend CRUD (`create/list/update/delete_*`, `_parse_sort`, `_TRANSACTION_SORT_FIELDS`, `_DIVIDEND_SORT_FIELDS`) to `portfolio/crud.py`; facade re-export; run full suite

## 5. Finalize

- [ ] 5.1 Reduce `portfolio_service.py` to imports/re-exports only (explicit `as` aliases); confirm no business logic remains and no submodule imports the facade
- [ ] 5.2 Run `uvx ruff check services scripts` and the full 548-test suite; confirm both clean
- [ ] 5.3 Update `SPEC.md` / `README.md` module references if they mention `portfolio_service.py` internals
