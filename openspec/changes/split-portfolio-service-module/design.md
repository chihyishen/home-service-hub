# Design: split-portfolio-service-module

## Context

`portfolio_service.py` (1,076 lines) hosts six distinguishable concerns. Ten app modules import it as `from . import portfolio_service` (or `from ..services import portfolio_service`) and access attributes dynamically; 15+ test files import it, some calling helpers directly, some patching attributes.

Two monkeypatch patterns exist with different survival characteristics:

1. **Cross-module patches** — e.g. `patch.object(sched.portfolio_service, "get_active_holdings")`, `patch.object(snap_svc.portfolio_service, "get_portfolio_summary")`, `monkeypatch.setattr(nbs.portfolio_service, "get_ever_held_symbols", ...)`. The consumer (scheduler / portfolio_snapshot_service / networth_backfill_service) resolves the attribute through the facade at call time, so these keep working as long as the facade re-exports the names and consumers keep dynamic `portfolio_service.X(...)` access.
2. **Intra-module patches** — e.g. `@patch("app.services.portfolio_service.get_stock_quotes")` (11 sites in test_portfolio_service / test_realized_pnl_invariant / test_active_holdings). Today `get_portfolio_summary` resolves `get_stock_quotes` from its own module globals. After the split it resolves from the new owning submodule, so these patch targets must be re-pointed (string change only).

## Goals / Non-Goals

**Goals:**
- No app-code import changes outside `app/services/` internals; facade keeps the public surface.
- Each new module under ~300 lines with one concern.
- Zero behavior change; 548 tests green after each task (only patch-target strings may change in tests).

**Non-Goals:**
- No renaming of public functions, no signature changes, no router changes.
- No StrEnum migration, no performance work, no new features.
- Not splitting other large files (networth_backfill_service etc.) — separate change if wanted.

## Decisions

**D1 — Package + facade layout.** New package `app/services/portfolio/` holds the implementation; `app/services/portfolio_service.py` stays as the facade re-exporting the public API plus the private helpers tests exercise directly (`_estimate_sell_costs`, `_resolve_sort_trade_date`, `_trade_calendar_date`, `_recompute_day_trade_flags`, `_parse_sort`, `_TRANSACTION_SORT_FIELDS`, `_DIVIDEND_SORT_FIELDS`). Re-exports use explicit `as` aliases so ruff's F401 treatment matches the `database.py` precedent. (Alternative rejected: turning `portfolio_service` itself into a package — keeps old patch strings resolving but still breaks intra-module patches, and `__init__`-as-facade makes the import graph murkier.)

**D2 — Module split** (line ranges from current file):

| Module | Contents | ~Lines |
|---|---|---|
| `portfolio/corp_actions.py` | `_AdjustedTransaction`, `_factor_for_trade`, `_apply_corp_action_factors`, `_load_corp_actions_by_symbol`, `_load_adjusted_transactions` | 26–148 |
| `portfolio/cashflows.py` | `_calculate_xirr` | 149–185 |
| `portfolio/helpers.py` | `sanitize_symbol`, `_escape_like_prefix`, `_resolve_sort_trade_date`, `_trade_calendar_date`, `_is_odd_lot`, `_env_decimal` | scattered |
| `portfolio/day_trade.py` | `_recompute_day_trade_flags`, `_validate_symbol_ledger`, `_validate_transaction_ledger` | 228–389 |
| `portfolio/holdings.py` | `_aggregate_active_holdings`, `get_active_holdings`, `get_ever_held_symbols`, `_get_quote_status` | 390–460 |
| `portfolio/summary.py` | `_estimate_sell_costs`, `get_portfolio_summary` (imports `get_stock_quotes`) | 461–702 |
| `portfolio/history_backfill.py` | `_schedule_symbol_history_backfill`, `_schedule_tpex_symbol_history_backfill`, `_is_tpex_marker`, `_symbol_uses_tpex_history` | 703–808 |
| `portfolio/crud.py` | transaction + dividend create/list/update/delete, `_parse_sort`, sort-field maps | 809–1076 |

**D3 — Patch-target migration.** The ~11 `get_stock_quotes` patch sites change their target string to `app.services.portfolio.summary.get_stock_quotes` (and `patch.object(portfolio_service, ...)` forms switch to importing `summary`). No other test edits. Cross-module patch sites (scheduler/snapshot/networth tests) are explicitly left untouched and serve as regression proof that the facade contract holds.

**D4 — Internal call direction.** Submodules import each other directly (e.g. `summary` imports from `holdings`, `corp_actions`, `cashflows`); only code *outside* the package goes through the facade. The facade imports from submodules, never the reverse — no cycles by construction.

**D5 — Mechanical movement.** Functions move verbatim (cut/paste plus import fix-ups). Any cleanup beyond imports is out of scope to keep the diff reviewable as pure movement.

## Risks / Trade-offs

- **Silent patch bypass**: a missed intra-module patch site would stub nothing and hit the network-mocked path differently — mitigated by running the full suite after each move task; the affected tests assert on stubbed quote values, so a bypass fails loudly, not silently.
- **Hidden module-global coupling** (e.g. `tracer`, `logger`, env reads at import time): each submodule gets its own `logger`/`tracer` line; `_env_decimal` reads env at call time so movement is safe.
- Two extra indirection hops when reading code (facade → submodule). Accepted: importers keep one import, and the facade file doubles as a public-API inventory.
