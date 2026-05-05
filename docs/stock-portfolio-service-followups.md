# Stock Portfolio Service — Post-Implementation Follow-ups

Date: 2026-05-05
Source: Internal review of `improve-stock-portfolio-service-reliability` after implementation
Status: Items 1–6 and 8 resolved on 2026-05-05; item 7 (frontend `quotes_status`) remains open.

This document captures issues found while reviewing the landed implementation against `docs/stock-portfolio-service-improvement-plan.md`.

## Resolution Summary

| # | Title | Status | Resolved on | Resolution |
|---|---|---|---|---|
| 1 | Production DB schema drift vs ORM model | ✅ Resolved | 2026-05-05 | Added `d1e2f3g4h5i6_migrate_to_numeric_types`; preflight 0 rows on all 4 columns; `alembic check` clean. Removed redundant `Decimal(str(...))` wrappers. |
| 2 | New-transaction `trade_date=None` ordering inconsistency | ✅ Resolved | 2026-05-05 | Adopted Option B (resolve-once-then-persist) in `create_transaction`/`update_transaction`; added `nullable=False` migration `e2f3g4h5i6j7` on top. Tests cover omitted and explicit-null cases. |
| 3 | `truststore.inject_into_ssl()` scope documentation | ✅ Resolved | 2026-05-05 | `SPEC.md` §2 and implementation-notes "Plan Deviations" both state the injection is process-global. |
| 4 | `main.py` imports private `_truststore_bootstrap` | ✅ Resolved | 2026-05-05 | Renamed in place to `bootstrap_truststore` with docstring; the underscore alias is deleted. All call sites and tests updated. |
| 5 | Ex-dividend cache key hardcoded | ✅ Resolved | 2026-05-05 | `fetch_exdividend_json` now uses `cache_key=url`. |
| 6 | Plan deviation: e2e tests deleted, not marked | ✅ Resolved | 2026-05-05 | Documented in `implementation-notes.md` "Plan Deviations". |
| 7 | Frontend has not yet consumed `quotes_status` | ⏳ Open | — | Tracked separately as a frontend follow-up; out of scope for this service. |
| 8 | `TWSE_SSL_VERIFY` legacy unknown-value parsing | ✅ Resolved | 2026-05-05 | `get_tls_mode` now `logger.warning`s on unknown legacy values. |

The remaining sections preserve the original analysis for historical context.

## 1. Production DB schema drift vs ORM model (HIGH) — RESOLVED 2026-05-05

### Observation

Running `alembic check` against the configured stock DB reports four type-change diffs:

```
Detected type change from DOUBLE_PRECISION to Numeric(12, 2) on dividends.amount
Detected type change from DOUBLE_PRECISION to Numeric(12, 2) on transactions.price
Detected type change from DOUBLE_PRECISION to Numeric(12, 2) on transactions.fee
Detected type change from DOUBLE_PRECISION to Numeric(12, 2) on transactions.tax
FAILED: New upgrade operations detected
```

The ORM models (`app/models/portfolio.py`) declare `Numeric(12, 2)`, but the production database stores these columns as `DOUBLE PRECISION`. SQLAlchemy reads them back as `float`, not `Decimal`.

### Impact

- `SPEC.md` claims "全面採用 `decimal.Decimal` 確保金錢運算精確至小數點後兩位." — currently false at the database layer.
- The `Decimal(str(t.price))` / `Decimal(str(t.fee or "0.0"))` wrappers in `app/services/portfolio_service.py` are not "redundant" while the DB returns float — they are required defenses against `TypeError` and float-precision drift.
- Improvement plan Finding 9 ("redundant `Decimal(str(...))` conversions, drop them") is unsafe to apply until column types are aligned.
- New `CheckConstraint`s added by migration `b7a1c9d2e4f6` work correctly on `DOUBLE PRECISION`, but the type contract advertised in code is misleading.

### Recommended change

1. Add an Alembic migration that alters the four columns to `Numeric(12, 2)` with explicit `USING` casts. Sketch:

   ```python
   op.alter_column(
       "transactions", "price",
       existing_type=sa.dialects.postgresql.DOUBLE_PRECISION(),
       type_=sa.Numeric(12, 2),
       postgresql_using="price::numeric(12,2)",
       existing_nullable=False,
   )
   ```

   Repeat for `transactions.fee`, `transactions.tax`, `dividends.amount`.

2. Verify `alembic check` reports clean (no operations detected) after the migration.

3. After the type migration is deployed, execute the deferred Finding 9 cleanup: replace `Decimal(str(t.price))`, `Decimal(str(t.fee or "0.0"))`, and `Decimal(str(t.tax or "0.0"))` with direct attribute access. Do this in a separate commit so behavior diff is reviewable.

4. Update `SPEC.md` only after both steps land.

### Risks

- `DOUBLE PRECISION → NUMERIC(12, 2)` truncates values that exceed the scale. Run a preflight: `select count(*) from transactions where price <> round(price::numeric, 2);` (and equivalents for `fee`, `tax`, `dividends.amount`). If any rows exist, decide whether to round or block migration.
- Migration takes a table lock on PostgreSQL when changing column types; acceptable on personal-scale data but worth noting.

## 2. New-transaction `trade_date=None` ordering inconsistency (MEDIUM) — RESOLVED 2026-05-05

### Observation

In `app/services/portfolio_service.py`:

```python
def _resolve_sort_trade_date(trade_date, fallback_trade_date=None):
    resolved = trade_date or fallback_trade_date or datetime.now(timezone.utc)
```

`schemas.TransactionCreate.trade_date` is `Optional[datetime] = None`. When a client omits `trade_date`:

- The validator orders the proposed transaction at `datetime.now()`.
- The actual stored row receives `server_default=func.now()`, set at COMMIT, by the database clock.
- A user inserting a backdated transaction (e.g. forgot to record yesterday's BUY) without supplying `trade_date` will be ordered as "today" by the validator, but the DB row will also be "today" — so SELL availability checks read correctly, but the user's mental model of "this BUY happened earlier" is silently wrong.

### Impact

- SELL availability still rejects oversells correctly in the common case, because validator and DB both treat the omitted `trade_date` as "now."
- However, the validator's "now" and the DB's "now" can differ when many writes are concurrent or when validation precedes commit by seconds. Over time this will surface as same-day ordering anomalies that are very hard to debug.
- Frontend already supplies `trade_date`, so risk is currently low. But the contract is brittle.

### Recommended change

Pick one of:

**Option A — Make `trade_date` required on input.**

- Change `TransactionCreate.trade_date` to `datetime` (non-optional).
- Remove `server_default=func.now()` from `Transaction.trade_date` (or keep as defense-in-depth).
- Frontend currently sends `trade_date`; verify before flipping the schema.

**Option B — Resolve `trade_date` once, before validation, and persist that value.**

- In `create_transaction` / `update_transaction`, compute `transaction_data["trade_date"] = transaction_data.get("trade_date") or datetime.now(timezone.utc)` before calling `_validate_transaction_ledger`, and pass the same value through to the SQLAlchemy model.
- Drop the `or datetime.now(...)` branch inside `_resolve_sort_trade_date` so the helper becomes a pure normalizer.

Option A is cleaner; Option B is more backward-compatible.

## 3. `truststore.inject_into_ssl()` scope documentation (MEDIUM) — RESOLVED 2026-05-05

### Observation

`openspec/changes/improve-stock-portfolio-service-reliability/proposal.md` says:

> `truststore.inject_into_ssl()` should be scoped to stock service / TWSE client, not shared app factory.

The actual implementation calls `_truststore_bootstrap()` from `app/main.py` at module import. `truststore.inject_into_ssl()` replaces the standard library `ssl` module's default context for the entire Python process. Once invoked, it affects every subsequent HTTPS call in the stock-portfolio-service process — including OpenTelemetry OTLP exporters, psycopg2 SSL connections, and any future client.

### Impact

- Behavior is correct and arguably desirable (consistent trust store everywhere in this service).
- But the documented "scope" is misleading. A reviewer comparing proposal language to code will reasonably flag it as a discrepancy.

### Recommended change

- Update `SPEC.md` and `openspec/changes/.../proposal.md` (or its archive copy after the change is archived) to state: "`truststore` is injected at stock-portfolio-service process startup. The injection is process-global by design — it affects all HTTPS clients in this service, not just TWSE."
- Add an `implementation-notes.md` line clarifying the same point.

No code change required.

## 4. `main.py` imports private symbol `_truststore_bootstrap` (LOW) — RESOLVED 2026-05-05

### Observation

```python
# app/main.py
from .services.twse_client import _truststore_bootstrap
_truststore_bootstrap()
```

The leading underscore signals module-private. Cross-module use of a private name is a code-smell.

### Recommended change

In `app/services/twse_client.py`:

```python
def bootstrap_truststore() -> None:
    _truststore_bootstrap()
```

Update `app/main.py` to import and call `bootstrap_truststore()`. Keep `_truststore_bootstrap` as the internal implementation if desired, or rename outright.

## 5. Ex-dividend cache key is hardcoded (LOW) — RESOLVED 2026-05-05

### Observation

In `app/services/twse_client.py`:

```python
def fetch_exdividend_json(self, url: str) -> list:
    result = self._fetch(
        ...
        cache_key="exdividend-table",
        ...
    )
```

The cache key is the literal string `"exdividend-table"` regardless of `url`. Today only one ex-dividend URL exists, so this works. Adding a second ex-dividend endpoint would collide on the same cache slot.

### Recommended change

Use the URL itself (or a tuple of `(span_name, url)`) as the cache key. Trivial change, removes a future foot-gun.

## 6. Implementation deviated from plan: e2e tests deleted, not marked (LOW) — RESOLVED 2026-05-05

### Observation

`docs/stock-portfolio-service-improvement-plan.md` Finding 15 recommends marking `tests/unit/test_twse_service_e2e.py` with `@pytest.mark.e2e` and excluding from default `pytest`. The implementation deleted that file and added `tests/unit/test_twse_service_mocked.py` instead.

### Impact

- Deletion is arguably the better choice (no flaky CI dependency on TWSE uptime).
- But the deviation from the written plan is undocumented. A reviewer reading both will notice.

### Recommended change

- Add a line in `openspec/changes/improve-stock-portfolio-service-reliability/implementation-notes.md` under "Deferred Decisions" or a new "Plan Deviations" section: "Replaced live e2e TWSE tests with mocked unit tests (`tests/unit/test_twse_service_mocked.py`) instead of marking them with `@pytest.mark.e2e`. Live verification is now only done via the post-deploy smoke checks."

No code change.

## 7. Frontend has not yet consumed `PortfolioSummary.quotes_status` (LOW)

### Observation

The summary response now exposes `quotes_status: "ok" | "partial" | "unavailable"`, but the Angular dashboard does not yet read it. When TWSE is unreachable, the user still sees zero-priced holdings without an explanation banner.

### Recommended change

- Add a thin status banner in the portfolio dashboard component when `quotes_status` is `partial` or `unavailable`.
- Track in frontend backlog rather than this service's plan.

## 8. `TWSE_SSL_VERIFY` legacy parsing of unknown values (LOW) — RESOLVED 2026-05-05

### Observation

In `get_tls_mode()`, if `TWSE_SSL_VERIFY` is set to anything outside `{1, true, yes, on, 0, false, no, off}`, the function silently returns `TLSMode.FALLBACK` without warning. `TWSE_TLS_MODE` does warn on unknown values; the legacy variable does not.

### Recommended change

Add a `logger.warning("Unknown TWSE_SSL_VERIFY=%s; defaulting to fallback", legacy_verify)` branch. Trivial, helps operations.

## Suggested execution order for the follow-up change

1. **#1** schema migration + Finding 9 cleanup (largest correctness win, blocks SPEC accuracy).
2. **#2** `trade_date` semantics decision and fix (correctness, requires product decision A vs B).
3. **#3** + **#6** documentation cleanup (no code risk; align proposal/SPEC with reality).
4. **#4** + **#5** + **#8** small code hygiene.
5. **#7** frontend follow-up (separate frontend PR).

## Verification expectations for the follow-up change

- `alembic check` is clean after #1.
- `pytest -q` remains green; new tests cover the chosen `trade_date` behavior in #2.
- Manual smoke: omit `trade_date` from a POST `/api/portfolio/transactions` and confirm the stored value matches the documented contract.
- Manual smoke: confirm `quotes_status` banner appears when TWSE is unreachable (after #7).
