# Proposal: split-portfolio-service-module

## Why

`app/services/portfolio_service.py` is 1,076 lines — the largest module in the service — and keeps growing because it mixes at least five concerns: corporate-action adjustment, XIRR/cashflow math, holdings aggregation, background history-backfill scheduling, and transaction/dividend CRUD. Ten app modules and 15+ test files import it (several monkeypatch its attributes), so every new feature lands in the same file and every merge conflicts there.

## What Changes

- Split `portfolio_service.py` into cohesive submodules (corporate-action adjustment, XIRR/cashflow, holdings aggregation, history-backfill triggers, transaction/dividend CRUD, shared helpers).
- Keep `portfolio_service.py` as a stable facade that re-exports the public API, so none of the 10 app importers or 15+ test files change their imports, and existing `monkeypatch.setattr(portfolio_service, ...)` patterns keep working.
- No behavior change: identical function signatures, identical results, full suite (548 tests) stays green; ruff stays clean.
- No API, schema, or DB changes.

## Capabilities

### New Capabilities

(none — pure internal restructuring)

### Modified Capabilities

- `stock-portfolio-api-maintainability`: add a requirement that portfolio service logic is organized into cohesive modules behind a stable `portfolio_service` facade, with cross-module calls routed so existing monkeypatch-based tests remain valid.

## Impact

- **Code**: `app/services/portfolio_service.py` shrinks to a facade; new modules under `app/services/portfolio/` (or sibling `portfolio_*.py` files — decided in design.md).
- **Importers (unchanged)**: routers `portfolio`, `exdividend`, `upcoming_events`; services `realized_pnl_service`, `broker_cathay_service`, `portfolio_snapshot_service`, `market_data_service`, `networth_backfill_service`, `scheduler`, `import_service`.
- **Tests**: no test-file changes expected; the suite is the safety net. Tests that monkeypatch facade attributes (e.g. `networth_backfill_service.portfolio_service.get_ever_held_symbols`) constrain how internal calls may be rewired.
- **Risk**: monkeypatched functions called internally by other split-out functions would bypass patched facade attributes if calls are moved to direct submodule imports — design must route these through the facade or document each case.
