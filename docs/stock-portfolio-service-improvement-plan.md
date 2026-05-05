# Stock Portfolio Service Improvement Plan

Date: 2026-05-04
Target: `services/stock-portfolio-service`
Status: Proposal for review

## Goal

Improve correctness, resilience, and maintainability of the stock portfolio service without changing the public API shape unless explicitly called out below.

The current service is already functional and covered by unit tests. Baseline verification on 2026-05-04:

```bash
cd services/stock-portfolio-service
.venv/bin/python -m pytest -q
```

Result: `21 passed`, with two Pydantic v2 deprecation warnings from class-based `Config`.

## Current Findings

### 1. External TWSE calls are fragile and default to disabled SSL verification

Files:

- `services/stock-portfolio-service/app/services/twse_service.py`
- `services/stock-portfolio-service/app/services/exdividend_service.py`

Observed behavior:

- `twse_service.fetch_raw_quotes()` defaults `TWSE_SSL_VERIFY` to `False`.
- `exdividend_service.fetch_upcoming_exdividends()` always calls `requests.get(..., verify=False)`.
- Both services issue live network calls synchronously from API request paths.
- Failures are swallowed and returned as empty data, which is user-friendly but makes operational diagnosis harder.

Risk:

- Disabling TLS verification by default weakens transport safety.
- A temporary TWSE slowdown can directly slow portfolio endpoints.
- Empty results can be indistinguishable from "no relevant data".

Operational context (2026-05-04 from owner):

- `verify=False` was originally set because real-world TWSE calls fail TLS verification intermittently. Simply flipping the default to `True` will regress availability.
- Decision: adopt `truststore` (OS native trust store) plus automatic fallback to `verify=False` on TLS error, with a kill-switch env var.

Recommended change:

- Add `truststore` to `requirements.txt`. Call `truststore.inject_into_ssl()` once at process startup (e.g. inside `shared_lib.create_app` or a small bootstrap in the TWSE client module) so `requests` uses macOS Keychain / Windows cert store / Linux `ca-certificates`. This typically fixes certifi-staleness issues without weakening security.
- Two-stage verification on each TWSE call:
  1. Attempt with `verify=True`.
  2. On `requests.exceptions.SSLError`, log `WARNING` with the cert error detail, set tracing attributes `tls.verified=false` and `tls.fallback=true`, increment a counter, then retry once with `verify=False`.
  3. Other exceptions are not subject to fallback and behave as before.
- Provide an explicit kill-switch env var (replace existing `TWSE_SSL_VERIFY`):
  - `TWSE_TLS_MODE` with values `verify` (default), `fallback` (current proposal), `insecure` (always `verify=False`, emergency only). Document `insecure` as emergency-only.
- Apply the same client to `exdividend_service.py` (currently hardcodes `verify=False`).
- Add a small shared request helper for TWSE calls with:
  - timeout
  - limited retry/backoff (separate from TLS fallback retry)
  - structured logging
  - tracing metadata: `tls.verified`, `tls.fallback`, `cache.hit`, `http.status`
- Add a short TTL cache:
  - quotes: 15-60 seconds
  - ex-dividend table: 15-60 minutes

Operational follow-ups:

- After deploy, watch the `tls.fallback=true` counter for a week. If fallback rate is near zero, consider removing `fallback` mode in a later change. If non-trivial, capture cert chain details and decide whether to bundle a specific intermediate CA.
- Consider an alert if fallback rate exceeds a threshold (e.g. >10% over 1 hour).

Review questions:

- Is `truststore` acceptable as a new runtime dependency in this service? (Pure-Python, MIT, maintained.)
- Is `TWSE_TLS_MODE` naming acceptable, or prefer keeping `TWSE_SSL_VERIFY` and adding a separate `TWSE_TLS_FALLBACK_ON_ERROR` flag?
- Is in-process caching enough, or should this use Redis later if multiple instances are expected?

### 2. Create/update input validation is too permissive

Files:

- `services/stock-portfolio-service/app/schemas/portfolio.py`
- `services/stock-portfolio-service/app/models/portfolio.py`
- new Alembic migration under `services/stock-portfolio-service/alembic/versions/`

Observed behavior:

- `symbol` can be empty or whitespace.
- `quantity` can be zero or negative.
- `price`, `fee`, `tax`, and dividend `amount` can be negative.
- The database layer does not enforce these constraints.

Risk:

- Bad data can enter the database via API or direct DB writes.
- Negative quantity/price breaks portfolio math and can hide in summary output.

Recommended change:

- Add Pydantic validation:
  - `symbol`: trim input, require non-empty, reasonable max length
  - `quantity`: `gt=0`
  - `price`: `gt=0`
  - `fee`, `tax`: `ge=0`
  - dividend `amount`: `gt=0`
- Add matching SQLAlchemy `CheckConstraint`s and Alembic migration.
- Add API tests for invalid create/update payloads.

Compatibility note:

- This may reject existing invalid rows when adding DB constraints. Before migration, run a read-only data quality query against production DB.

Suggested pre-migration checks:

```sql
select * from transactions
where trim(symbol) = ''
   or quantity <= 0
   or price <= 0
   or coalesce(fee, 0) < 0
   or coalesce(tax, 0) < 0;

select * from dividends
where trim(symbol) = ''
   or amount <= 0;
```

Review questions:

- Should existing invalid data be blocked by migration failure, or should migration include a cleanup step?
- Should symbol validation allow non-TWSE symbols for future markets, or restrict to numeric Taiwan stock/ETF codes?

### 3. SELL transactions can exceed current holdings

File:

- `services/stock-portfolio-service/app/services/portfolio_service.py`

Observed behavior:

- The summary calculation subtracts SELL quantity if the current quantity is positive.
- It does not reject or flag a SELL quantity greater than current holdings.
- Create/update paths do not validate available quantity.

Risk:

- Overselling can produce negative holdings and distorted rolling average cost.
- Since the summary only displays active symbols with quantity greater than zero, invalid data may be hidden instead of visible.

Recommended change:

- Add service-level validation on transaction create/update:
  - Compute current holdings for the target symbol up to the relevant transaction ordering.
  - Reject SELL when available quantity would go below zero.
  - On update, exclude the transaction being updated from the availability calculation.
- Return HTTP 400 with a clear message from router/service.
- Add tests for:
  - SELL without holdings
  - SELL greater than holdings
  - update BUY to SELL causing oversell
  - valid partial SELL still works

Review questions:

- Should validation use trade date ordering only, or `(trade_date, id)` for deterministic same-day ordering?
- Should short selling ever be supported? Current product language implies no.

### 4. Portfolio summary loads all rows and calls TWSE synchronously

Files:

- `services/stock-portfolio-service/app/services/portfolio_service.py`
- `services/stock-portfolio-service/app/routers/exdividend.py`

Observed behavior:

- Summary loads all transactions and all dividends into memory.
- Upcoming ex-dividend route also loads all transactions and calculates holdings in Python.
- This is acceptable for small personal data sets but will degrade as history grows.

Risk:

- API latency grows with full transaction history.
- Repeated dashboard polling causes repeated TWSE calls.

Recommended change:

Phase 1:

- Extract a reusable holdings aggregation helper so summary and ex-dividend use the same logic.
- Add tracing attributes for transaction count, dividend count, active symbol count, quote count, and cache hit/miss.
- Add quote/ex-dividend TTL cache as described in finding 1.

Phase 2:

- Consider a materialized holdings table or snapshot table if data volume grows.
- Consider DB-side aggregation only if rolling average and XIRR rules remain manageable.

Review questions:

- Is this service expected to stay single-user/personal, or become multi-user?
- What dashboard refresh interval does frontend currently use?

### 5. Dividend totals have ambiguous semantics

File:

- `services/stock-portfolio-service/app/services/portfolio_service.py`

Observed behavior:

- `total_dividends` sums every dividend record across all symbols.
- Portfolio XIRR aggregates cash flows only for currently active symbols.
- Holdings list only shows currently active symbols.

Risk:

- A user may interpret `total_dividends` as dividends for currently held positions, while it currently behaves like lifetime dividends across all records.
- Closed positions can affect total dividend display but not active holdings display.

Recommended change:

Option A, no API shape change:

- Keep `total_dividends` as lifetime dividends.
- Document this explicitly in `SPEC.md`.
- Add `active_total_dividends` later if frontend needs it.

Option B, clearer API:

- Add `lifetime_dividends` and `active_holdings_dividends`.
- Keep `total_dividends` temporarily for backward compatibility and mark the intended meaning.

Review questions:

- Which number does the frontend currently display as portfolio dividend performance?
- Should closed positions be included in portfolio-level performance?

### 6. Local health router is unused

Files:

- `services/stock-portfolio-service/app/main.py`
- `services/stock-portfolio-service/app/routers/health.py`
- `services/shared-python-lib/shared_lib/app_factory.py`

Observed behavior:

- `shared_lib.create_app()` already registers `/health` and `/health/ready`.
- `app/routers/health.py` exists but is not included by `app/main.py`.
- Current tests assert health routes are registered once.

Risk:

- The unused file can mislead future edits.

Recommended change:

- Delete `services/stock-portfolio-service/app/routers/health.py`.
- Keep `tests/unit/test_health.py` as coverage for shared-lib health registration.

Review questions:

- None, unless there is a plan to make service-specific health behavior different from shared health.

### 7. Pydantic v2 deprecation warning

File:

- `services/stock-portfolio-service/app/schemas/portfolio.py`

Observed behavior:

- Tests emit `PydanticDeprecatedSince20` for class-based `Config`.

Risk:

- Future Pydantic v3 upgrade will break these models.

Recommended change:

- Replace:

```python
class Config:
    from_attributes = True
```

with:

```python
from pydantic import ConfigDict

model_config = ConfigDict(from_attributes=True)
```

Tests:

- Full service tests should pass without Pydantic deprecation warnings.

### 8. `update_*` overwrites optional fields with `None`

File:

- `services/stock-portfolio-service/app/services/portfolio_service.py`

Observed behavior:

- `update_transaction()` and `update_dividend()` call `transaction_update.model_dump()` and then loop `setattr()` over every key.
- `TransactionCreate.trade_date` and `DividendCreate.received_date` are `Optional` with default `None`. If a PUT request omits them, the dump still emits `None`, which overwrites the previously stored value with `None`.

Risk:

- Silent data loss when the frontend (or any client) issues a partial-feeling PUT.
- XIRR and ordering depend on `trade_date`, so wiping it skews calculations.

Recommended change:

- Use `model_dump(exclude_unset=True)` in update paths, or introduce dedicated `TransactionUpdate` / `DividendUpdate` schemas.
- Add tests asserting that omitting a previously-set field on PUT preserves the original value.

### 9. Redundant `Decimal(str(...))` conversions

File:

- `services/stock-portfolio-service/app/services/portfolio_service.py`

Observed behavior:

- SQLAlchemy `Numeric` columns already return `Decimal`. The summary loop wraps `t.price`, `t.fee`, `t.tax`, `d.amount` in `Decimal(str(...))` defensively.

Risk:

- Pure noise; harmless but obscures intent.

Recommended change:

- Drop the conversions and use `t.price`, `t.fee or Decimal("0")`, etc. directly.
- Keep this change atomic so review can verify no behavior drift.

### 10. List endpoints bypass the service layer and lack pagination

File:

- `services/stock-portfolio-service/app/routers/portfolio.py`

Observed behavior:

- `GET /transactions` and `GET /dividends` query `db.query(...)` directly inside the router.
- Other endpoints route through `portfolio_service`.
- No `limit` / `offset` or cursor support.

Risk:

- Inconsistent layering makes future filters/sorting harder to share.
- Response size grows unbounded as history accumulates.

Recommended change:

- Move the query into `portfolio_service.list_transactions()` / `list_dividends()`.
- Add `limit` (default e.g. 200, max 1000) and `offset` query parameters.
- Optionally accept `symbol` filter on both endpoints.

### 11. TWSE failure returns empty data without UX signal

File:

- `services/stock-portfolio-service/app/services/twse_service.py`

Observed behavior:

- Network or parse failures return `{}`.
- Summary then renders all holdings with `current_price=0`, looking like a total wipeout.

Risk:

- Indistinguishable from "no data" vs "external API down".
- Hard to diagnose without inspecting traces.

Recommended change:

- Tag the summary span with `quotes.unavailable=true` and an error reason.
- Add a top-level boolean (e.g. `quotes_stale: bool` or `quotes_status: "ok" | "unavailable"`) to `PortfolioSummary` so the frontend can show a banner.
- Keep the safe fallback (current behavior) so the dashboard still renders.

### 12. `parse_twse_msg_array` logs INFO per symbol

File:

- `services/stock-portfolio-service/app/services/twse_service.py`

Observed behavior:

- `logger.info(f"解析股票 [{symbol}]: ...")` runs for every quoted symbol on every poll.

Risk:

- Log volume scales with portfolio size × dashboard refresh rate.

Recommended change:

- Demote per-symbol log to `DEBUG`.
- Keep an aggregate `INFO` line per fetch (`"TWSE quotes parsed: 12 symbols"`).

### 13. Missing indexes on date-ordered columns

File:

- `services/stock-portfolio-service/app/models/portfolio.py`
- new Alembic migration

Observed behavior:

- `Transaction.trade_date` is sorted in summary and ex-dividend paths; not indexed.
- `Dividend.ex_dividend_date` is ordered in `GET /dividends`; not indexed.

Risk:

- Acceptable today (small personal data). Will degrade if data volume grows or if multi-user is introduced.

Recommended change:

- Add indexes via Alembic migration:
  - `transactions(trade_date)`
  - `dividends(ex_dividend_date)`
- Optional composite `transactions(symbol, trade_date)` if symbol-filtered queries are added.

### 14. DELETE endpoints return JSON body instead of 204

File:

- `services/stock-portfolio-service/app/routers/portfolio.py`

Observed behavior:

- `DELETE /transactions/{id}` and `DELETE /dividends/{id}` return `{"message": "...deleted"}` with HTTP 200.

Risk:

- Minor; not REST-conventional. Frontend already only checks status code.

Recommended change:

- Return `Response(status_code=204)` (or set `status_code=204` on the route decorator) and drop the body.
- Update any frontend code that asserts on `message`.

### 15. e2e tests hit live TWSE

File:

- `services/stock-portfolio-service/tests/unit/test_twse_service_e2e.py`

Observed behavior:

- The test makes real HTTP calls to TWSE during default `pytest` runs.

Risk:

- Flaky in CI; couples test pass/fail to TWSE uptime.

Recommended change:

- Mark the test class with `@pytest.mark.e2e`.
- Configure `pytest.ini` / `pyproject.toml` to deselect `e2e` by default (`addopts = -m "not e2e"`).
- Run e2e tests on demand: `pytest -m e2e`.

## Proposed Work Breakdown

### Task 1: Validation and DB constraints

Scope:

- Update Pydantic schemas.
- Add SQLAlchemy constraints.
- Add Alembic migration.
- Add invalid payload tests.

Primary files:

- `app/schemas/portfolio.py`
- `app/models/portfolio.py`
- `alembic/versions/<new_revision>_add_portfolio_data_constraints.py`
- `tests/unit/test_portfolio_validation.py` or extend existing tests

Acceptance criteria:

- Invalid create/update payloads return 422 or 400 consistently.
- Existing valid tests pass.
- Alembic migration is reversible.

### Task 2: Oversell protection

Scope:

- Add holdings availability validation in transaction create/update.
- Return clear HTTP 400 errors.
- Add tests for invalid SELL cases.

Primary files:

- `app/services/portfolio_service.py`
- `app/routers/portfolio.py`
- `tests/unit/test_portfolio_service.py`

Acceptance criteria:

- Cannot create SELL that exceeds available shares.
- Cannot update an existing transaction into an invalid state.
- Valid BUY and partial SELL flows still pass.

### Task 3: TWSE resilience and cache

Scope:

- Enable SSL verification by default.
- Add configurable timeout/retry/backoff.
- Add short TTL cache for quote and ex-dividend fetches.
- Improve logging/tracing around external API failures.

Primary files:

- `app/services/twse_service.py`
- `app/services/exdividend_service.py`
- possible new helper: `app/services/twse_client.py`
- tests for cache and request behavior

Acceptance criteria:

- Unit tests verify `verify=True` by default.
- Repeated calls within TTL do not perform repeated network requests.
- Network failure still returns safe empty data but logs useful context.

### Task 4: Shared holdings aggregation

Scope:

- Extract holdings calculation used by summary and ex-dividend route.
- Keep output behavior unchanged.

Primary files:

- `app/services/portfolio_service.py`
- `app/routers/exdividend.py`

Acceptance criteria:

- Summary and ex-dividend route use the same active symbol logic.
- Tests cover active holdings after BUY/SELL sequences.

### Task 5: Cleanup and warning removal

Scope:

- Remove unused local health router.
- Convert Pydantic class `Config` to `ConfigDict`.

Primary files:

- delete `app/routers/health.py`
- update `app/schemas/portfolio.py`

Acceptance criteria:

- Health tests still pass.
- Full tests pass without Pydantic deprecation warnings.

### Task 6: Update path partial-update fix

Scope:

- Switch `update_transaction` / `update_dividend` to `model_dump(exclude_unset=True)` (or split `*Update` schemas).
- Add tests that PUT without optional fields preserves stored values.

Primary files:

- `app/services/portfolio_service.py`
- `app/schemas/portfolio.py` (if introducing `*Update`)
- `tests/unit/test_portfolio_service.py`

Acceptance criteria:

- PUT without `trade_date` does not overwrite the stored `trade_date`.
- All existing update tests still pass.

### Task 7: Router consistency, pagination, DELETE 204

Scope:

- Move `GET /transactions` and `GET /dividends` into service layer.
- Add `limit` / `offset` (and optional `symbol` filter).
- Convert DELETE responses to 204 No Content.

Primary files:

- `app/routers/portfolio.py`
- `app/services/portfolio_service.py`
- frontend code that consumes DELETE message body (if any)

Acceptance criteria:

- List endpoints accept pagination params and return paginated data.
- DELETE returns 204; integration tests updated.

### Task 8: Quote UX signal and observability

Scope:

- Add a `quotes_status` (or equivalent) field to `PortfolioSummary` indicating quote freshness.
- Tag spans on TWSE failure.
- Demote per-symbol parse log to DEBUG; add aggregate INFO.

Primary files:

- `app/services/twse_service.py`
- `app/services/portfolio_service.py`
- `app/schemas/portfolio.py`
- `tests/unit/test_portfolio_service.py`

Acceptance criteria:

- When TWSE returns no data, summary clearly indicates unavailable quotes.
- Per-symbol log volume is removed at INFO.

### Task 9: Cleanup follow-ups

Scope:

- Remove redundant `Decimal(str(...))` wrapping in summary calculation.
- Add Alembic migration for indexes on `transactions.trade_date` and `dividends.ex_dividend_date`.
- Mark e2e TWSE tests with `@pytest.mark.e2e` and exclude from default run.

Primary files:

- `app/services/portfolio_service.py`
- `alembic/versions/<new_revision>_add_portfolio_indexes.py`
- `tests/unit/test_twse_service_e2e.py`
- `pytest.ini` or `pyproject.toml`

Acceptance criteria:

- Default `pytest` run excludes e2e tests.
- `alembic upgrade head` / `downgrade -1` succeed.
- No behavior change to summary output.

### Task 10: Dividend semantics documentation

Scope:

- Decide on lifetime vs active dividends.
- Update `SPEC.md`.
- Optionally add new response fields if frontend needs both meanings.

Primary files:

- `SPEC.md`
- `app/schemas/portfolio.py`
- `app/services/portfolio_service.py`

Acceptance criteria:

- API field semantics are documented.
- Tests cover dividends from closed positions.

## Suggested Implementation Order

1. Task 5: cleanup and warning removal.
2. Task 6: update path partial-update fix (correctness, tiny diff).
3. Task 1: validation and constraints.
4. Task 2: oversell protection.
5. Task 4: shared holdings aggregation.
6. Task 7: router consistency, pagination, DELETE 204.
7. Task 9: cleanup follow-ups (Decimal wrapping, indexes, e2e marker).
8. Task 3: TWSE resilience and cache (depends on TLS decision).
9. Task 8: quote UX signal and observability.
10. Task 10: dividend semantics.

Rationale:

- Start with low-risk cleanup and silent-data-loss fix.
- Then protect data at API and DB boundaries.
- Then fix business correctness around SELL.
- Then reduce duplication and tighten API surface.
- External API caching is useful but blocked on TLS decision and has more behavioral choices.
- UX signal benefits from the cache work landing first.
- Dividend semantics needs product decision before changing response shape.

## Verification Plan

Run service tests:

```bash
cd services/stock-portfolio-service
.venv/bin/python -m pytest -q
```

Run Alembic migration checks:

```bash
cd services/stock-portfolio-service
.venv/bin/alembic upgrade head
.venv/bin/alembic downgrade -1
.venv/bin/alembic upgrade head
```

Optional live smoke tests after deploy:

```bash
curl -sS http://localhost:8080/health
curl -sS http://localhost:8080/health/ready
curl -sS http://localhost:8080/api/portfolio/summary
curl -sS http://localhost:8080/api/portfolio/ex-dividends/upcoming
```

## Reviewer Checklist

- Are the proposed DB constraints compatible with current production data?
- Should invalid transaction business rules return 400 or 422?
- Should SSL verification be mandatory or configurable?
- Is in-memory TTL cache acceptable for deployment topology?
- Should closed positions contribute to portfolio-level dividend and XIRR metrics?
- Is same-day transaction ordering sufficiently deterministic?
