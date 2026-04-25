# Frontend API Client Base Class Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract common HTTP logic from the 4 Angular service files into a thin base class, so each service only declares its endpoints — not error handling, base URL, or boilerplate.

**Architecture:** Create an abstract `BaseApiService<T>` that provides typed CRUD helpers (`getAll`, `getOne`, `create`, `update`, `delete`). Each service extends it with a `baseUrl` and adds any domain-specific methods. The existing `errorLoggingInterceptor` already handles global error → PrimeNG toast, so the base class does NOT duplicate error handling — it only reduces repetitive `this.http.get/post/put/delete` patterns.

**Tech Stack:** Angular 21, TypeScript, Vitest, HttpClient.

**Prerequisites:** Plan 2 (shared-lib error handler) should be merged so backend returns consistent `{code, message, trace_id}`. The interceptor already extracts `error.error?.message` for the toast — no frontend change needed for that.

---

## Design Decision: Why a base class, not a standalone ApiClient service

Option A (standalone `ApiClient` service): Every service injects `ApiClient` and calls `apiClient.get<T>(url)`. Pros: composition over inheritance. Cons: each service still needs to wire URL + every method signature — not much less code.

Option B (abstract base class): Each service extends `BaseApiService`, declares `baseUrl`, and gets free CRUD. Domain-specific methods still call `this.http` directly. Pros: eliminates 60%+ of repetitive lines. Cons: inheritance coupling.

Choosing **Option B** because these services are straightforward REST wrappers and Angular services don't change hierarchy often. The base class is thin (~40 lines) so the coupling risk is low.

---

## File Structure

- Create: `frontend/src/app/services/base-api.service.ts` — abstract base class
- Create: `frontend/src/app/services/base-api.service.spec.ts` — test
- Modify: `frontend/src/app/services/portfolio.service.ts` — extend base class
- Modify: `frontend/src/app/services/portfolio.service.spec.ts` (create if doesn't exist)
- Modify: `frontend/src/app/services/item.service.ts` — extend base class
- Modify: `frontend/src/app/services/shopping-list.service.ts` — extend base class
- Note: `accounting.service.ts` is NOT refactored — it has many non-CRUD methods (reports, card usage, recurring, etc.) and would gain little from inheritance. Leave it as-is.

---

### Task 1: Create `BaseApiService`

**Files:**
- Create: `frontend/src/app/services/base-api.service.ts`
- Create: `frontend/src/app/services/base-api.service.spec.ts`

- [ ] **Step 1: Write failing test**

Create `frontend/src/app/services/base-api.service.spec.ts`:

```typescript
import { describe, it, expect, beforeEach } from 'vitest';
import { TestBed } from '@angular/core/testing';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideHttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { BaseApiService } from './base-api.service';

interface TestItem {
  id: number;
  name: string;
}

@Injectable({ providedIn: 'root' })
class TestService extends BaseApiService<TestItem> {
  protected override baseUrl = '/api/test';
}

describe('BaseApiService', () => {
  let service: TestService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting(), TestService]
    });
    service = TestBed.inject(TestService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  it('getAll sends GET to baseUrl', () => {
    service.getAll().subscribe(items => {
      expect(items).toEqual([{ id: 1, name: 'test' }]);
    });
    const req = httpMock.expectOne('/api/test');
    expect(req.request.method).toBe('GET');
    req.flush([{ id: 1, name: 'test' }]);
  });

  it('getOne sends GET to baseUrl/:id', () => {
    service.getOne(42).subscribe(item => {
      expect(item.name).toBe('hello');
    });
    const req = httpMock.expectOne('/api/test/42');
    expect(req.request.method).toBe('GET');
    req.flush({ id: 42, name: 'hello' });
  });

  it('create sends POST to baseUrl', () => {
    const payload = { name: 'new' };
    service.create(payload).subscribe();
    const req = httpMock.expectOne('/api/test');
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual(payload);
    req.flush({ id: 1, name: 'new' });
  });

  it('update sends PUT to baseUrl/:id', () => {
    service.update(1, { name: 'updated' }).subscribe();
    const req = httpMock.expectOne('/api/test/1');
    expect(req.request.method).toBe('PUT');
    req.flush({ id: 1, name: 'updated' });
  });

  it('remove sends DELETE to baseUrl/:id', () => {
    service.remove(1).subscribe();
    const req = httpMock.expectOne('/api/test/1');
    expect(req.request.method).toBe('DELETE');
    req.flush(null);
  });
});
```

- [ ] **Step 2: Run test — verify fail**

```bash
cd frontend
npx vitest run src/app/services/base-api.service.spec.ts
```

Expected: FAIL (module not found).

- [ ] **Step 3: Implement base class**

Create `frontend/src/app/services/base-api.service.ts`:

```typescript
import { inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

export abstract class BaseApiService<T extends { id?: number }> {
  protected http = inject(HttpClient);
  protected abstract baseUrl: string;

  getAll(params?: HttpParams): Observable<T[]> {
    return this.http.get<T[]>(this.baseUrl, { params });
  }

  getOne(id: number): Observable<T> {
    return this.http.get<T>(`${this.baseUrl}/${id}`);
  }

  create(body: Partial<T>): Observable<T> {
    return this.http.post<T>(this.baseUrl, body);
  }

  update(id: number, body: Partial<T>): Observable<T> {
    return this.http.put<T>(`${this.baseUrl}/${id}`, body);
  }

  remove(id: number): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/${id}`);
  }
}
```

- [ ] **Step 4: Run test — verify pass**

```bash
npx vitest run src/app/services/base-api.service.spec.ts
```

Expected: all 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
cd frontend
git add src/app/services/base-api.service.ts src/app/services/base-api.service.spec.ts
git commit -m "feat(frontend): add BaseApiService abstract class for CRUD"
```

---

### Task 2: Refactor `PortfolioService` to extend base class

**Files:**
- Modify: `frontend/src/app/services/portfolio.service.ts`

- [ ] **Step 1: Rewrite portfolio.service.ts**

Replace the **entire** content of `frontend/src/app/services/portfolio.service.ts` with:

```typescript
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { BaseApiService } from './base-api.service';
import { PortfolioSummary, Transaction, Dividend } from '../models/portfolio.model';

@Injectable({
  providedIn: 'root'
})
export class PortfolioService extends BaseApiService<Transaction> {
  protected override baseUrl = '/api/portfolio/transactions';

  getSummary(): Observable<PortfolioSummary> {
    return this.http.get<PortfolioSummary>('/api/portfolio/summary');
  }

  getTransactions(): Observable<Transaction[]> {
    return this.getAll();
  }

  createTransaction(transaction: Partial<Transaction>): Observable<Transaction> {
    return this.create(transaction);
  }

  updateTransaction(id: number, transaction: Partial<Transaction>): Observable<Transaction> {
    return this.update(id, transaction);
  }

  deleteTransaction(id: number): Observable<void> {
    return this.remove(id);
  }

  // Dividends — different resource, so use http directly
  getDividends(): Observable<Dividend[]> {
    return this.http.get<Dividend[]>('/api/portfolio/dividends');
  }

  createDividend(dividend: Partial<Dividend>): Observable<Dividend> {
    return this.http.post<Dividend>('/api/portfolio/dividends', dividend);
  }

  updateDividend(id: number, dividend: Partial<Dividend>): Observable<Dividend> {
    return this.http.put<Dividend>(`/api/portfolio/dividends/${id}`, dividend);
  }

  deleteDividend(id: number): Observable<void> {
    return this.http.delete<void>(`/api/portfolio/dividends/${id}`);
  }
}
```

Note: We keep the old method names (`getTransactions`, `createTransaction`, etc.) as thin wrappers so callers don't need any changes. Over time these can be cleaned up.

- [ ] **Step 2: Run full frontend tests**

```bash
cd frontend
npm test
```

Expected: all tests pass. Components call the same public methods — only the internals changed.

- [ ] **Step 3: Commit**

```bash
git add src/app/services/portfolio.service.ts
git commit -m "refactor(frontend): PortfolioService extends BaseApiService"
```

---

### Task 3: Refactor `ItemService` to extend base class

**Files:**
- Modify: `frontend/src/app/services/item.service.ts`

- [ ] **Step 1: Rewrite item.service.ts**

Replace the **entire** content of `frontend/src/app/services/item.service.ts` with:

```typescript
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { HttpParams } from '@angular/common/http';
import { BaseApiService } from './base-api.service';
import {
  ItemRequest,
  ItemResponse,
  InventoryTransactionRequest,
  InventoryTransactionResponse,
  ItemTransactionResultResponse
} from '../models/item.model';
import { environment } from '../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class ItemService extends BaseApiService<ItemResponse> {
  protected override baseUrl = `${environment.apiUrl}/items`;

  getAll(params?: HttpParams): Observable<ItemResponse[]> {
    return this.http.get<ItemResponse[]>(this.baseUrl, { params });
  }

  getAllFiltered(keyword?: string, lowStockOnly?: boolean, category?: string, location?: string): Observable<ItemResponse[]> {
    let params = new HttpParams();
    if (keyword) params = params.set('keyword', keyword);
    if (lowStockOnly) params = params.set('lowStockOnly', String(lowStockOnly));
    if (category) params = params.set('category', category);
    if (location) params = params.set('location', location);
    return this.getAll(params);
  }

  getCategories(): Observable<string[]> {
    return this.http.get<string[]>(`${this.baseUrl}/categories`);
  }

  getLocations(): Observable<string[]> {
    return this.http.get<string[]>(`${this.baseUrl}/locations`);
  }

  getById(id: number): Observable<ItemResponse> {
    return this.getOne(id);
  }

  createItem(item: ItemRequest): Observable<ItemResponse> {
    return this.http.post<ItemResponse>(this.baseUrl, item);
  }

  updateItem(id: number, item: ItemRequest): Observable<ItemResponse> {
    return this.http.put<ItemResponse>(`${this.baseUrl}/${id}`, item);
  }

  uploadImage(id: number, file: File): Observable<ItemResponse> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<ItemResponse>(`${this.baseUrl}/${id}/image`, formData);
  }

  deleteItem(id: number): Observable<void> {
    return this.remove(id);
  }

  createTransaction(id: number, payload: InventoryTransactionRequest): Observable<ItemTransactionResultResponse> {
    return this.http.post<ItemTransactionResultResponse>(`${this.baseUrl}/${id}/transactions`, payload);
  }

  getTransactions(id: number, limit: number = 50): Observable<InventoryTransactionResponse[]> {
    return this.http.get<InventoryTransactionResponse[]>(`${this.baseUrl}/${id}/transactions`, { params: { limit } });
  }
}
```

Important: The original service uses method names `create`, `update`, `delete` directly — but `BaseApiService` also defines `create` and `update`. Check the callers:

```bash
cd frontend
grep -rn "itemService\.\(create\|update\|delete\)\b" src/app/components/
```

If callers use `.create(item)`, `.update(id, item)`, `.delete(id)` — the base class signatures differ slightly (e.g., `create` takes `Partial<T>` while the old one takes `ItemRequest`). The wrapper methods above (`createItem`, `updateItem`, `deleteItem`) preserve the old interface. **Update callers only if they call the exact old method names.** Check and fix any mismatches.

- [ ] **Step 2: Run tests**

```bash
npm test
```

Expected: pass.

- [ ] **Step 3: Commit**

```bash
git add src/app/services/item.service.ts
git commit -m "refactor(frontend): ItemService extends BaseApiService"
```

---

### Task 4: Refactor `ShoppingListService` to extend base class

**Files:**
- Modify: `frontend/src/app/services/shopping-list.service.ts`

- [ ] **Step 1: Rewrite shopping-list.service.ts**

Replace the **entire** content of `frontend/src/app/services/shopping-list.service.ts` with:

```typescript
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { HttpParams } from '@angular/common/http';
import { BaseApiService } from './base-api.service';
import { ShoppingListItemRequest, ShoppingListItemResponse } from '../models/item.model';
import { environment } from '../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class ShoppingListService extends BaseApiService<ShoppingListItemResponse> {
  protected override baseUrl = `${environment.apiUrl}/shopping-list`;

  getList(status?: 'PENDING' | 'PURCHASED' | 'SKIPPED'): Observable<ShoppingListItemResponse[]> {
    let params = new HttpParams();
    if (status) params = params.set('status', status);
    return this.getAll(params);
  }

  generateFromLowStock(): Observable<ShoppingListItemResponse[]> {
    return this.http.post<ShoppingListItemResponse[]>(`${this.baseUrl}/generate-from-low-stock`, {});
  }

  createItem(payload: ShoppingListItemRequest): Observable<ShoppingListItemResponse> {
    return this.http.post<ShoppingListItemResponse>(this.baseUrl, payload);
  }

  updateItem(id: number, payload: ShoppingListItemRequest): Observable<ShoppingListItemResponse> {
    return this.http.patch<ShoppingListItemResponse>(`${this.baseUrl}/${id}`, payload);
  }

  deleteItem(id: number): Observable<void> {
    return this.remove(id);
  }
}
```

Note: The original `update` uses `PATCH`, not `PUT`. The base class `update` uses `PUT`. So we keep a custom `updateItem` method instead of using the inherited `update`.

- [ ] **Step 2: Check callers**

```bash
grep -rn "shoppingListService\.\(create\|update\|delete\|getList\)\b" src/app/components/
```

If callers use the original method names (`create`, `update`, `delete`), update them to `createItem`, `updateItem`, `deleteItem`. Or if no callers exist (service unused), skip.

- [ ] **Step 3: Run tests**

```bash
npm test
```

Expected: pass.

- [ ] **Step 4: Commit**

```bash
git add src/app/services/shopping-list.service.ts
git commit -m "refactor(frontend): ShoppingListService extends BaseApiService"
```

---

### Task 5: Verify no regression — full build

**Files:** None (verification only).

- [ ] **Step 1: Run full test suite**

```bash
cd frontend
npm test
```

- [ ] **Step 2: Run production build**

```bash
npm run build
```

Expected: both pass with zero errors.

- [ ] **Step 3: Smoke test in browser (manual)**

```bash
npm start
```

Open `http://localhost:4200`. Navigate to:
- Portfolio dashboard → transactions load?
- Accounting transactions → list loads?
- Inventory list → items load?

If any page fails, check browser devtools console for errors.

---

## Self-Review Checklist

- [ ] `BaseApiService` uses `inject(HttpClient)` — no constructor injection (matches Angular 21 inject function pattern used in existing services)
- [ ] `accounting.service.ts` is NOT refactored (too many domain-specific methods, inheritance adds no value)
- [ ] All refactored services preserve their original public method signatures — callers need zero changes
- [ ] The `remove` method name was chosen to avoid collision with `delete` keyword (TypeScript reserved word concern in some contexts)
- [ ] The `errorLoggingInterceptor` still handles all errors globally — base class does not add its own error handling

## Out of Scope

- Refactoring `accounting.service.ts` (too many unique methods to benefit from inheritance)
- Adding retry logic or caching to the base class (interceptor already handles retry)
- Changing error response display (interceptor already shows PrimeNG toast)
