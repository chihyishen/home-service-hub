# 除權息提醒 (Ex-Dividend Reminder) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fetch upcoming ex-dividend announcements from TWSE Open API, filter to the user's currently-held symbols, expose a new endpoint `GET /api/portfolio/ex-dividends/upcoming`, and display a reminder card on the portfolio dashboard.

**Architecture:** A new `exdividend_service.py` calls the public TWSE OpenAPI (no auth needed), parses the announcement table, and filters results against the user's active holdings. The router exposes a single endpoint. No new DB tables — data is fetched live from TWSE on each request and is not persisted.  The frontend adds one card to the existing portfolio dashboard.

**Tech Stack:** Python 3.13, FastAPI, requests (already installed), Angular 21, PrimeNG

---

## File Map

| Action | File | Purpose |
|--------|------|---------|
| Create | `services/stock-portfolio-service/app/services/exdividend_service.py` | Fetch & parse TWSE ex-dividend table |
| Modify | `services/stock-portfolio-service/app/schemas/portfolio.py` | Add `ExDividendRecord` Pydantic schema |
| Create | `services/stock-portfolio-service/app/routers/exdividend.py` | `GET /api/portfolio/ex-dividends/upcoming` |
| Modify | `services/stock-portfolio-service/app/main.py` | Register new router |
| Create | `services/stock-portfolio-service/tests/unit/test_exdividend_service.py` | Unit tests for parser |
| Modify | `frontend/src/app/models/portfolio.model.ts` | Add `ExDividendRecord` interface |
| Modify | `frontend/src/app/services/portfolio.service.ts` | Add `getUpcomingExDividends()` |
| Modify | `frontend/src/app/components/portfolio/dashboard/dashboard.ts` | Load upcoming ex-dividends |
| Modify | `frontend/src/app/components/portfolio/dashboard/dashboard.html` | Display ex-dividend reminder card |

---

### Task 1: Write failing tests for the ex-dividend parser

**Files:**
- Create: `services/stock-portfolio-service/tests/unit/test_exdividend_service.py`

- [ ] **Step 1: Create the test file**

```python
# services/stock-portfolio-service/tests/unit/test_exdividend_service.py
from app.services.exdividend_service import parse_twse_exdividend_records, roc_to_date
from datetime import date


class TestRocToDate:
    def test_converts_roc_date_string(self):
        # ROC year 114 = Gregorian 2025
        assert roc_to_date("114/06/15") == date(2025, 6, 15)

    def test_returns_none_for_empty(self):
        assert roc_to_date("") is None
        assert roc_to_date("-") is None

    def test_returns_none_for_invalid(self):
        assert roc_to_date("not-a-date") is None


class TestParseTwseExdividendRecords:
    def test_parses_valid_records(self):
        raw = [
            {
                "股票代號": "2330",
                "名稱": "台積電",
                "除息交易日": "114/07/17",
                "除權交易日": "",
                "最近一次配息": "3.00",
            },
            {
                "股票代號": "0050",
                "名稱": "元大台灣50",
                "除息交易日": "114/07/20",
                "除權交易日": "",
                "最近一次配息": "2.50",
            },
        ]
        held_symbols = {"2330", "0050"}
        results = parse_twse_exdividend_records(raw, held_symbols)
        assert len(results) == 2
        assert results[0].symbol == "2330"
        assert results[0].ex_dividend_date == date(2025, 7, 17)
        assert results[0].cash_dividend == "3.00"

    def test_filters_to_held_symbols_only(self):
        raw = [
            {"股票代號": "2330", "名稱": "台積電", "除息交易日": "114/07/17", "除權交易日": "", "最近一次配息": "3.00"},
            {"股票代號": "9999", "名稱": "不持有這檔", "除息交易日": "114/07/20", "除權交易日": "", "最近一次配息": "1.00"},
        ]
        results = parse_twse_exdividend_records(raw, {"2330"})
        assert len(results) == 1
        assert results[0].symbol == "2330"

    def test_returns_empty_for_no_match(self):
        raw = [
            {"股票代號": "9999", "名稱": "不持有", "除息交易日": "114/07/20", "除權交易日": "", "最近一次配息": "1.00"},
        ]
        results = parse_twse_exdividend_records(raw, {"2330"})
        assert results == []

    def test_skips_records_with_no_date(self):
        raw = [
            {"股票代號": "2330", "名稱": "台積電", "除息交易日": "", "除權交易日": "", "最近一次配息": "3.00"},
        ]
        results = parse_twse_exdividend_records(raw, {"2330"})
        # No ex-dividend date → skip
        assert results == []
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd services/stock-portfolio-service
.venv/bin/pytest tests/unit/test_exdividend_service.py -v
```

Expected: `ModuleNotFoundError` because `exdividend_service.py` doesn't exist yet.

---

### Task 2: Implement exdividend_service.py

**Files:**
- Create: `services/stock-portfolio-service/app/services/exdividend_service.py`
- Modify: `services/stock-portfolio-service/app/schemas/portfolio.py` (add schema first)

- [ ] **Step 1: Add ExDividendRecord schema to portfolio.py**

At the bottom of `app/schemas/portfolio.py`, add:

```python
class ExDividendRecord(BaseModel):
    symbol: str
    name: str
    ex_dividend_date: Optional[date] = None     # 除息日
    ex_rights_date: Optional[date] = None       # 除權日
    cash_dividend: Optional[str] = None         # 現金股利（字串保留原始精度）
    stock_dividend: Optional[str] = None        # 股票股利
```

Also add `from datetime import date` at the top if not already present.

- [ ] **Step 2: Create exdividend_service.py**

```python
# services/stock-portfolio-service/app/services/exdividend_service.py
import logging
import requests
from datetime import date
from typing import List, Optional, Set

from ..schemas.portfolio import ExDividendRecord

logger = logging.getLogger(__name__)

TWSE_EXDIVIDEND_URL = "https://openapi.twse.com.tw/v1/exchangeReport/TWT48U"


def roc_to_date(roc_str: str) -> Optional[date]:
    """
    Convert ROC date string "114/06/15" to Python date(2025, 6, 15).
    ROC year + 1911 = Gregorian year.
    Returns None for empty or invalid strings.
    """
    if not roc_str or roc_str.strip() in ("", "-"):
        return None
    try:
        parts = roc_str.strip().split("/")
        if len(parts) != 3:
            return None
        year = int(parts[0]) + 1911
        month = int(parts[1])
        day = int(parts[2])
        return date(year, month, day)
    except (ValueError, IndexError):
        return None


def parse_twse_exdividend_records(
    raw_records: list, held_symbols: Set[str]
) -> List[ExDividendRecord]:
    """
    Parse a list of raw TWSE API dicts into ExDividendRecord objects,
    keeping only records for symbols in held_symbols.
    Skips records with no valid ex-dividend or ex-rights date.
    """
    results = []
    for item in raw_records:
        symbol = item.get("股票代號", "").strip()
        if symbol not in held_symbols:
            continue

        ex_div_date = roc_to_date(item.get("除息交易日", ""))
        ex_rights_date = roc_to_date(item.get("除權交易日", ""))

        # Skip if neither date is present
        if ex_div_date is None and ex_rights_date is None:
            continue

        results.append(
            ExDividendRecord(
                symbol=symbol,
                name=item.get("名稱", symbol),
                ex_dividend_date=ex_div_date,
                ex_rights_date=ex_rights_date,
                cash_dividend=item.get("最近一次配息") or None,
                stock_dividend=item.get("最近一次配股") or None,
            )
        )

    # Sort by earliest date (ex-dividend or ex-rights)
    def _sort_key(r: ExDividendRecord):
        d = r.ex_dividend_date or r.ex_rights_date
        return d if d else date(9999, 12, 31)

    results.sort(key=_sort_key)
    return results


def fetch_upcoming_exdividends(held_symbols: Set[str]) -> List[ExDividendRecord]:
    """
    Fetch the TWSE upcoming ex-dividend table and return records for held_symbols only.
    Returns an empty list on any network or parse error.
    """
    if not held_symbols:
        return []
    try:
        resp = requests.get(TWSE_EXDIVIDEND_URL, timeout=10, verify=False)
        resp.raise_for_status()
        raw = resp.json()
        if not isinstance(raw, list):
            logger.warning("TWSE ex-dividend API returned unexpected format")
            return []
        return parse_twse_exdividend_records(raw, held_symbols)
    except Exception as e:
        logger.error(f"Failed to fetch TWSE ex-dividend data: {e}")
        return []
```

- [ ] **Step 3: Run the tests to verify they pass**

```bash
cd services/stock-portfolio-service
.venv/bin/pytest tests/unit/test_exdividend_service.py -v
```

Expected: all 7 tests pass.

- [ ] **Step 4: Commit**

```bash
git add services/stock-portfolio-service/app/services/exdividend_service.py \
        services/stock-portfolio-service/app/schemas/portfolio.py \
        services/stock-portfolio-service/tests/unit/test_exdividend_service.py
git commit -m "feat(stock): add ex-dividend service with TWSE parser"
```

---

### Task 3: Create the router and register it

**Files:**
- Create: `services/stock-portfolio-service/app/routers/exdividend.py`
- Modify: `services/stock-portfolio-service/app/main.py`

- [ ] **Step 1: Create exdividend.py router**

```python
# services/stock-portfolio-service/app/routers/exdividend.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models import portfolio as models
from ..schemas.portfolio import ExDividendRecord
from ..services.exdividend_service import fetch_upcoming_exdividends
from ..services.portfolio_service import sanitize_symbol

router = APIRouter(
    prefix="/api/portfolio",
    tags=["Portfolio"]
)


@router.get("/ex-dividends/upcoming", response_model=List[ExDividendRecord])
def get_upcoming_exdividends(db: Session = Depends(get_db)):
    """
    Return upcoming ex-dividend announcements from TWSE for stocks
    currently held in the portfolio (quantity > 0).
    """
    transactions = db.query(models.Transaction).order_by(models.Transaction.trade_date).all()

    # Compute held symbols (same logic as portfolio_service)
    holdings_qty: dict = {}
    for t in transactions:
        symbol = sanitize_symbol(t.symbol)
        if t.type == models.TransactionType.BUY:
            holdings_qty[symbol] = holdings_qty.get(symbol, 0) + t.quantity
        elif t.type == models.TransactionType.SELL:
            holdings_qty[symbol] = holdings_qty.get(symbol, 0) - t.quantity

    held_symbols = {s for s, qty in holdings_qty.items() if qty > 0}
    return fetch_upcoming_exdividends(held_symbols)
```

- [ ] **Step 2: Register router in main.py**

Edit `services/stock-portfolio-service/app/main.py`:

```python
from shared_lib import create_app

from .database import engine, get_db
from .routers import portfolio, exdividend

app = create_app(
    title="Home Service Hub - Stock Portfolio API",
    description="投資組合管理微服務。",
    version="1.1.0",
    routers=[portfolio.router, exdividend.router],
    get_db=get_db,
    engine=engine,
    otel_service_name_env="OTEL_SERVICE_NAME_STOCK",
    otel_strict=False,
)
```

- [ ] **Step 3: Verify service starts and endpoint exists**

```bash
pm2 restart stock-portfolio-service
sleep 5
curl -s http://localhost:8001/api/portfolio/ex-dividends/upcoming | python3 -m json.tool
```

Expected: a JSON array (possibly empty if no holdings or outside trading hours).

- [ ] **Step 4: Commit**

```bash
git add services/stock-portfolio-service/app/routers/exdividend.py \
        services/stock-portfolio-service/app/main.py
git commit -m "feat(stock): add /api/portfolio/ex-dividends/upcoming endpoint"
```

---

### Task 4: Update Angular model and service

**Files:**
- Modify: `frontend/src/app/models/portfolio.model.ts`
- Modify: `frontend/src/app/services/portfolio.service.ts`

- [ ] **Step 1: Add ExDividendRecord to portfolio.model.ts**

At the bottom of `frontend/src/app/models/portfolio.model.ts`, add:

```typescript
export interface ExDividendRecord {
  symbol: string;
  name: string;
  ex_dividend_date?: string;   // ISO date string
  ex_rights_date?: string;
  cash_dividend?: string;
  stock_dividend?: string;
}
```

- [ ] **Step 2: Add getUpcomingExDividends() to portfolio.service.ts**

In `frontend/src/app/services/portfolio.service.ts`, add the import and method:

At the top, update the import from portfolio.model:
```typescript
import { PortfolioSummary, Transaction, Dividend, ExDividendRecord } from '../models/portfolio.model';
```

Inside the class, add:
```typescript
getUpcomingExDividends(): Observable<ExDividendRecord[]> {
  return this.http.get<ExDividendRecord[]>('/api/portfolio/ex-dividends/upcoming');
}
```

---

### Task 5: Display ex-dividend reminder in the dashboard

**Files:**
- Modify: `frontend/src/app/components/portfolio/dashboard/dashboard.ts`
- Modify: `frontend/src/app/components/portfolio/dashboard/dashboard.html`

- [ ] **Step 1: Load ex-dividends in dashboard.ts**

In `dashboard.ts`, add the import:
```typescript
import { PortfolioSummary, ExDividendRecord } from '../../../models/portfolio.model';
```

Add a signal inside the class:
```typescript
upcomingExDividends = signal<ExDividendRecord[]>([]);
```

In `ngOnInit()`, add the load call:
```typescript
ngOnInit() {
  this.loadSummary();
  this.loadExDividends();
}
```

Add the method:
```typescript
loadExDividends() {
  this.portfolioService.getUpcomingExDividends().subscribe({
    next: (data) => this.upcomingExDividends.set(data),
    error: () => this.upcomingExDividends.set([])  // fail silently
  });
}
```

- [ ] **Step 2: Add ex-dividend card in dashboard.html**

Inside the `hub-bento-grid`, add a new full-width card after the holdings card. If `upcomingExDividends().length > 0`, show the table:

```html
<!-- 即將除權息提醒 -->
@if (upcomingExDividends().length > 0) {
  <div class="bento-item bento-full exdiv-card">
    <h3 class="card-title">
      <i class="pi pi-bell"></i> 即將除權息提醒
    </h3>
    <p-table [value]="upcomingExDividends()" [tableStyle]="{'min-width': '40rem'}" styleClass="p-datatable-sm">
      <ng-template pTemplate="header">
        <tr>
          <th>代號</th>
          <th>名稱</th>
          <th>除息日</th>
          <th>除權日</th>
          <th>現金股利</th>
        </tr>
      </ng-template>
      <ng-template pTemplate="body" let-row>
        <tr>
          <td><strong>{{ row.symbol }}</strong></td>
          <td>{{ row.name }}</td>
          <td>{{ row.ex_dividend_date ?? '-' }}</td>
          <td>{{ row.ex_rights_date ?? '-' }}</td>
          <td>{{ row.cash_dividend ?? '-' }}</td>
        </tr>
      </ng-template>
    </p-table>
  </div>
}
```

- [ ] **Step 3: Add TableModule import in dashboard.ts**

`TableModule` is already imported via `imports: [CommonModule, CardModule, TableModule, ...]` — confirm it's in the `imports` array. If it is, no change needed.

- [ ] **Step 4: Run frontend tests**

```bash
cd frontend
npm test
```

Expected: all tests pass.

- [ ] **Step 5: Restart frontend and verify in browser**

```bash
pm2 restart frontend
```

Open the portfolio dashboard. If any held stocks have upcoming ex-dividend announcements in the TWSE table, a card "即將除權息提醒" will appear at the bottom of the page.

Note: The TWSE TWT48U endpoint only contains announcements for the current period (usually 1–3 months ahead). Outside of announcement periods, the card will simply not appear.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/app/models/portfolio.model.ts \
        frontend/src/app/services/portfolio.service.ts \
        frontend/src/app/components/portfolio/dashboard/dashboard.ts \
        frontend/src/app/components/portfolio/dashboard/dashboard.html
git commit -m "feat(frontend): add ex-dividend reminder card to portfolio dashboard"
```

---

## Self-Review

### Spec coverage
- ✅ Fetch TWSE ex-dividend table
- ✅ Filter to user's current holdings
- ✅ New API endpoint
- ✅ Frontend reminder card
- ✅ Fail gracefully (network errors return empty list, card hidden)

### Placeholder scan
- No TBD or placeholder steps found.

### Type consistency
- `ExDividendRecord` schema uses `Optional[date]` (Python) → serialised as ISO string by FastAPI ✅
- Frontend `ExDividendRecord.ex_dividend_date?: string` matches ✅
- `getUpcomingExDividends(): Observable<ExDividendRecord[]>` ✅
