## MODIFIED Requirements

### Requirement: 分類改名同步 legacy category 字串

When a category name is updated, the system SHALL NOT need to synchronize any legacy string column on transactions or subscriptions, because the legacy `category` string column has been removed. Reports and listings SHALL derive category display name solely from the `category_info` relationship.

#### Scenario: 分類改名後查詢報表

- **WHEN** category "餐飲" is renamed to "外食"
- **AND** existing transactions reference that category id
- **THEN** monthly reports show "外食" without any background data migration
- **AND** the legacy `category` column does not exist on `transactions` or `subscriptions`

### Requirement: 分類合併

The category merge workflow SHALL move source category references to the target category by updating only `category_id` foreign keys. Applying a merge MUST NOT update any string column representing the category name on `transactions` or `subscriptions`. The source category SHALL be deleted only after all references are migrated.

#### Scenario: 合併 apply

- **WHEN** the caller applies merging source category A into target category B
- **THEN** all transactions previously referencing A reference B via `category_id`
- **AND** all subscriptions previously referencing A reference B via `category_id`
- **AND** there is no string column synchronization step
- **AND** source category A is deleted after references are migrated

## ADDED Requirements

### Requirement: Transaction 與 Subscription 不再儲存 category 字串

The `transactions.category` and `subscriptions.category` string columns SHALL NOT exist in the database schema. Category for any transaction or subscription is represented exclusively by `category_id` referencing `categories.id`. The Alembic migration history MUST include a step that backfills `category_id` from existing string values, creates `categories` rows for distinct orphan strings, enforces `category_id NOT NULL`, and drops the legacy string column.

#### Scenario: Schema 檢查

- **WHEN** `\d transactions` is run on the production database
- **THEN** there is no column named `category`
- **AND** `category_id` is `NOT NULL`

#### Scenario: Schema 檢查 subscriptions

- **WHEN** `\d subscriptions` is run on the production database
- **THEN** there is no column named `category`
- **AND** `category_id` is `NOT NULL`

#### Scenario: Backfill 處理孤兒字串

- **WHEN** the Alembic migration runs against a database that contains a transaction with `category = "投資"` and no matching `categories.name`
- **THEN** the migration creates a `categories` row with `name = "投資"`
- **AND** the transaction's `category_id` is set to that new id
- **AND** the migration completes successfully

### Requirement: API 強制以 category_id 表達分類

`POST /api/accounting/transactions`, `PUT /api/accounting/transactions/{id}`, `POST /api/accounting/recurring/subscriptions`, and `PUT /api/accounting/recurring/subscriptions/{id}` SHALL require `category_id` and MUST NOT accept a `category` string field. Missing or invalid `category_id` SHALL result in HTTP 422 (missing) or HTTP 400 (invalid id).

#### Scenario: 建立交易缺少 category_id

- **WHEN** the caller submits a transaction create payload without `category_id`
- **THEN** the response is HTTP 422

#### Scenario: 建立交易帶不存在的 category_id

- **WHEN** the caller submits a transaction create payload with `category_id` that does not exist
- **THEN** the response is HTTP 400
- **AND** the error detail begins with `Invalid category_id:`

#### Scenario: 建立訂閱缺少 category_id

- **WHEN** the caller submits a subscription create payload without `category_id`
- **THEN** the response is HTTP 422

### Requirement: API 響應使用 category_name 暴露顯示名稱

Transaction and subscription API responses SHALL expose `category_id: int` and `category_name: str`. They MUST NOT expose a `category` string field. `category_name` SHALL be derived from the `categories.name` joined via `category_id`.

#### Scenario: 取得交易詳情

- **WHEN** the caller fetches a transaction whose `category_id` references category "外食"
- **THEN** the response contains `category_id` and `category_name = "外食"`
- **AND** the response does not contain a top-level `category` string field
