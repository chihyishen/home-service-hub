## ADDED Requirements

### Requirement: 退款不得灌入收入報表

Accounting analytics aggregations SHALL classify any transaction with `transaction_type = "INCOME" AND related_transaction_id IS NOT NULL` as a refund offset rather than income. Refund transactions MUST be excluded from any `total_income`, monthly income series, and income-based ratios such as `savings_rate`. Refund amounts SHALL be netted from the original EXPENSE transaction's month and category.

#### Scenario: 同月部分退款

- **WHEN** an EXPENSE of 1000 in 2026-05 is partially refunded by 300 (also dated 2026-05)
- **AND** the caller requests the 2026-05 monthly report
- **THEN** `total_income` does not include the 300 refund
- **AND** `total_expense` equals the original total minus 300
- **AND** the EXPENSE category's amount in `expense_breakdown` is reduced by 300
- **AND** `savings_rate` is recomputed using the netted income and expense

#### Scenario: 跨月退款

- **WHEN** an EXPENSE of 1000 in 2026-04 is refunded by 1000 in 2026-05
- **AND** the caller requests the annual report for 2026
- **THEN** `monthly_income[2026-05]` does not include the 1000 refund
- **AND** `monthly_expense[2026-04]` is reduced by 1000
- **AND** `monthly_expense[2026-05]` is unchanged

#### Scenario: 全額退款後 category 趨勢

- **WHEN** an EXPENSE of 500 in category "餐飲" in 2026-03 has a refund of 500
- **AND** no other "餐飲" EXPENSE exists in 2026-03
- **THEN** the annual report's `category_trend` entry for "餐飲" has `monthly_amounts[2026-03] = 0`

#### Scenario: 孤兒退款

- **WHEN** a refund INCOME exists with `related_transaction_id` pointing to a deleted EXPENSE
- **THEN** the refund SHALL NOT be added to any income total
- **AND** the refund SHALL NOT modify any expense total or category breakdown

### Requirement: refund 累積查詢只實作一次

The function that aggregates refunded amounts per source transaction SHALL be defined once in a shared module under `app/services/` and SHALL be reused by both `transaction_service` and `analytics_service`. Behavior, signature, and return type MUST be preserved.

#### Scenario: 跨服務一致

- **WHEN** both `transaction_service` and `analytics_service` need cumulative refunded amounts for a set of transaction ids
- **THEN** they call the same shared helper
- **AND** the function returns `dict[int, int]` mapping `source_transaction_id` to total refunded amount in TWD integer

### Requirement: 校驗與付款方式同步集中於共用 helper

Accounting service category, payment method, and card validation SHALL be implemented in a single shared helper module. `transaction_service.create_transaction`, `transaction_service.update_transaction`, `recurring_service.create_subscription`, `recurring_service.update_subscription`, `recurring_service.create_installment`, and `recurring_service.update_installment` SHALL all delegate validation and default payment method resolution to that helper. HTTP error status codes and existing detail strings MUST be preserved so frontend behavior is unchanged.

#### Scenario: 卡片預設付款方式同步在四條路徑一致

- **WHEN** a card has `default_payment_method = "Apple Pay"`
- **AND** any of create_transaction / update_transaction / create_subscription / update_subscription / create_installment / update_installment is invoked with that card_id and no explicit `payment_method`
- **THEN** the resulting record has `payment_method = "Apple Pay"`

#### Scenario: 付款方式不存在

- **WHEN** any of the six paths is invoked with `payment_method = "NotARealMethod"`
- **THEN** the response is HTTP 400
- **AND** the error detail begins with `Invalid payment_method:`

#### Scenario: 分類不存在

- **WHEN** any of the six paths is invoked with a `category_id` that does not exist
- **THEN** the response is HTTP 400
- **AND** the error detail begins with `Invalid category_id:`

### Requirement: recurring 生成日期使用真實月底

`recurring_service.generate_recurring_items` SHALL determine the day-of-month for generated subscription and installment transactions using `billing_service.safe_date_replace(year, month, day)` semantics. It MUST NOT cap the day at 28.

#### Scenario: day_of_month 為 31 的訂閱在 2 月

- **WHEN** an active subscription has `day_of_month = 31`
- **AND** `generate_recurring_items` runs in February of a non-leap year
- **THEN** the generated transaction has `date.day = 28`

#### Scenario: day_of_month 為 30 的訂閱在 4 月

- **WHEN** an active subscription has `day_of_month = 30`
- **AND** `generate_recurring_items` runs in April
- **THEN** the generated transaction has `date.day = 30`

#### Scenario: day_of_month 為 31 的分期在 3 月

- **WHEN** an installment has `start_date.day = 31` and `remaining_periods > 0`
- **AND** `generate_recurring_items` runs in March
- **THEN** the generated transaction has `date.day = 31`
