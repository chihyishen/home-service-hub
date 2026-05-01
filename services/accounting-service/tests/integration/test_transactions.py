from datetime import date

from sqlalchemy import event
from app import models, schemas
from app.services import analytics_service, billing_service, recurring_service, transaction_service
from fastapi.testclient import TestClient


def test_transaction_and_refund(db_session):
    db_session.add(models.PaymentMethod(name="Cash", is_active=True))
    db_session.commit()

    tx = transaction_service.create_transaction(
        db_session,
        schemas.TransactionCreate(
            category="測試",
            item="測試支出",
            paid_amount=1000,
            transaction_amount=1000,
            payment_method="Cash",
        ),
    )
    transaction_id = tx.id

    refund = transaction_service.refund_transaction(db_session, transaction_id, 200)
    assert refund.transaction_type == "INCOME"
    assert refund.related_transaction_id == transaction_id
    assert "退款" in refund.item

    original = transaction_service.get_transaction(db_session, transaction_id)
    assert original.refundable_amount == 800
    assert refund.refundable_amount == 0

    today = date.today()
    report = analytics_service.get_monthly_report(db_session, today.year, today.month)
    assert report.summary.total_income >= 200


def test_refund_guards_and_explicit_payment_method_override(db_session):
    db_session.add_all(
        [
            models.PaymentMethod(name="Cash", is_active=True),
            models.PaymentMethod(name="Apple Pay", is_active=True),
            models.CreditCard(
                name="測試卡",
                billing_day=5,
                reward_cycle_type="CALENDAR_MONTH",
                alert_threshold=5000,
                default_payment_method="Apple Pay",
            ),
        ]
    )
    db_session.commit()

    card = db_session.query(models.CreditCard).filter(models.CreditCard.name == "測試卡").first()

    created = transaction_service.create_transaction(
        db_session,
        schemas.TransactionCreate(
            date=date.today(),
            category="餐飲",
            item="午餐",
            paid_amount=1000,
            transaction_amount=1000,
            payment_method="信用卡",
            card_id=card.id,
        ),
    )
    assert created.payment_method == "Apple Pay"

    updated = transaction_service.update_transaction(
        db_session,
        created.id,
        schemas.TransactionUpdate(card_id=card.id),
    )
    assert updated.payment_method == "Apple Pay"

    explicit = transaction_service.update_transaction(
        db_session,
        created.id,
        schemas.TransactionUpdate(card_id=card.id, payment_method="Cash"),
    )
    assert explicit.payment_method == "Cash"

    first_refund = transaction_service.refund_transaction(db_session, created.id, 300)
    assert first_refund.transaction_amount == 300

    refreshed = transaction_service.get_transaction(db_session, created.id)
    assert refreshed.refundable_amount == 700

    for invalid_amount in (0, -1):
        try:
            transaction_service.refund_transaction(db_session, created.id, invalid_amount)
            raise AssertionError("expected refund validation to fail")
        except Exception as exc:
            assert getattr(exc, "status_code", None) == 400

    try:
        transaction_service.refund_transaction(db_session, created.id, 800)
        raise AssertionError("expected over-refund validation to fail")
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 400

    income = transaction_service.create_transaction(
        db_session,
        schemas.TransactionCreate(
            date=date.today(),
            category="薪資",
            item="薪水",
            paid_amount=5000,
            transaction_amount=5000,
            payment_method="Cash",
            transaction_type="INCOME",
        ),
    )
    assert income.refundable_amount == 0

    try:
        transaction_service.refund_transaction(db_session, income.id, 100)
        raise AssertionError("expected income refund validation to fail")
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 400


def test_monthly_report_is_read_only_and_uses_integer_amounts(db_session):
    db_session.add(models.PaymentMethod(name="Cash", is_active=True))
    db_session.commit()

    today = date.today()
    subscription = models.Subscription(
        name="串流月費",
        amount=290,
        category="娛樂",
        sub_type="SUBSCRIPTION",
        payment_method="Cash",
        day_of_month=min(today.day, 28),
        active=True,
    )
    db_session.add(subscription)
    db_session.commit()

    before_count = db_session.query(models.Transaction).count()
    report = analytics_service.get_monthly_report(db_session, today.year, today.month)
    after_count = db_session.query(models.Transaction).count()

    assert before_count == after_count
    assert isinstance(report.summary.total_income, int)
    assert isinstance(report.summary.total_expense, int)
    assert isinstance(report.summary.surplus, int)


def test_monthly_report_keeps_explicitly_generated_recurring_without_extra_writes(db_session):
    today = date.today()
    db_session.add(models.PaymentMethod(name="Cash", is_active=True))
    db_session.commit()

    subscription = models.Subscription(
        name="健身房",
        amount=1299,
        category="健康",
        sub_type="SUBSCRIPTION",
        payment_method="Cash",
        day_of_month=min(today.day, 28),
        active=True,
    )
    db_session.add(subscription)
    db_session.commit()

    recurring_service.generate_recurring_items(db_session)
    after_generation_count = db_session.query(models.Transaction).count()
    report = analytics_service.get_monthly_report(db_session, today.year, today.month)
    after_report_count = db_session.query(models.Transaction).count()

    assert after_generation_count == 1
    assert after_report_count == after_generation_count
    assert report.summary.total_expense == 1299


def test_card_usage_supports_negative_net_refunds(db_session):
    today = date.today()
    db_session.add_all(
        [
            models.PaymentMethod(name="Apple Pay", is_active=True),
            models.CreditCard(
                name="測試卡",
                billing_day=5,
                reward_cycle_type="CALENDAR_MONTH",
                alert_threshold=5000,
                default_payment_method="Apple Pay",
            ),
        ]
    )
    db_session.commit()

    card = db_session.query(models.CreditCard).filter(models.CreditCard.name == "測試卡").first()

    transaction_service.create_transaction(
        db_session,
        schemas.TransactionCreate(
            date=today,
            category="測試",
            item="一般消費",
            paid_amount=1000,
            transaction_amount=1000,
            payment_method="Apple Pay",
            card_id=card.id,
        ),
    )
    transaction_service.create_transaction(
        db_session,
        schemas.TransactionCreate(
            date=today,
            category="測試",
            item="退刷入帳",
            paid_amount=1500,
            transaction_amount=1500,
            payment_method="Apple Pay",
            card_id=card.id,
            transaction_type="INCOME",
        ),
    )

    summary = analytics_service.get_card_usage_summary(db_session)
    card_summary = next(item for item in summary if item.card_name == card.name)
    assert card_summary.current_usage == -500
    assert card_summary.is_near_limit is False
    assert card_summary.is_over_limit is False

    status = billing_service.get_card_status(db_session, card.id)
    assert status.current_cycle_total == -500
    assert "淨退款" in status.status_message


def test_card_usage_summary_and_status_reduce_refunds(db_session):
    today = date.today()
    db_session.add_all(
        [
            models.PaymentMethod(name="Apple Pay", is_active=True),
            models.CreditCard(
                name="測試卡",
                billing_day=5,
                reward_cycle_type="CALENDAR_MONTH",
                alert_threshold=5000,
                default_payment_method="Apple Pay",
            ),
        ]
    )
    db_session.commit()

    card = db_session.query(models.CreditCard).filter(models.CreditCard.name == "測試卡").first()

    expense = transaction_service.create_transaction(
        db_session,
        schemas.TransactionCreate(
            date=today,
            category="測試",
            item="測試刷卡",
            paid_amount=1000,
            transaction_amount=1000,
            payment_method="Apple Pay",
            card_id=card.id,
        ),
    )

    transaction_service.refund_transaction(db_session, expense.id, 400)

    summary = analytics_service.get_card_usage_summary(db_session)
    card_summary = next(item for item in summary if item.card_name == card.name)
    assert card_summary.current_usage == 600
    assert card_summary.remaining_to_threshold == 4400

    status = billing_service.get_card_status(db_session, card.id)
    assert status.current_cycle_total == 600


def test_get_transactions_supports_agent_filters(db_session):
    db_session.add(models.PaymentMethod(name="Cash", is_active=True))
    db_session.commit()

    today = date.today()

    manual_tx = transaction_service.create_transaction(
        db_session,
        schemas.TransactionCreate(
            date=today,
            category="餐飲",
            item="午餐",
            paid_amount=180,
            transaction_amount=180,
            payment_method="Cash",
        ),
    )

    subscription_tx = transaction_service.create_transaction(
        db_session,
        schemas.TransactionCreate(
            date=today,
            category="娛樂",
            item="影音訂閱",
            paid_amount=300,
            transaction_amount=300,
            payment_method="Cash",
        ),
    )
    subscription_tx.subscription_id = 1

    installment_tx = transaction_service.create_transaction(
        db_session,
        schemas.TransactionCreate(
            date=today,
            category="3C",
            item="手機分期",
            paid_amount=1200,
            transaction_amount=1200,
            payment_method="Cash",
        ),
    )
    installment_tx.installment_id = 1

    income_tx = transaction_service.create_transaction(
        db_session,
        schemas.TransactionCreate(
            date=today,
            category="薪資",
            item="薪水",
            paid_amount=50000,
            transaction_amount=50000,
            payment_method="Cash",
            transaction_type="INCOME",
        ),
    )

    db_session.commit()

    filtered = transaction_service.get_transactions(
        db_session,
        date_preset="today",
        transaction_type="expense",
        exclude_subscription=True,
        exclude_installment=True,
    )

    assert [tx.id for tx in filtered] == [manual_tx.id]

    keyword_filtered = transaction_service.get_transactions(
        db_session,
        date_from=today,
        date_to=today,
        keyword="午餐",
    )

    assert [tx.id for tx in keyword_filtered] == [manual_tx.id]
    assert income_tx.id not in [tx.id for tx in filtered]
    assert filtered[0].refundable_amount == 180


def test_get_transactions_manual_only_defaults_to_today_manual_expense(db_session):
    db_session.add(models.PaymentMethod(name="Cash", is_active=True))
    db_session.commit()

    today = date.today()

    manual_tx = transaction_service.create_transaction(
        db_session,
        schemas.TransactionCreate(
            date=today,
            category="餐飲",
            item="晚餐",
            paid_amount=220,
            transaction_amount=220,
            payment_method="Cash",
        ),
    )

    subscription_tx = transaction_service.create_transaction(
        db_session,
        schemas.TransactionCreate(
            date=today,
            category="娛樂",
            item="串流月費",
            paid_amount=290,
            transaction_amount=290,
            payment_method="Cash",
        ),
    )
    subscription_tx.subscription_id = 1

    income_tx = transaction_service.create_transaction(
        db_session,
        schemas.TransactionCreate(
            date=today,
            category="薪資",
            item="獎金",
            paid_amount=3000,
            transaction_amount=3000,
            payment_method="Cash",
            transaction_type="INCOME",
        ),
    )

    db_session.commit()

    filtered = transaction_service.get_transactions(
        db_session,
        manual_only=True,
    )

    assert [tx.id for tx in filtered] == [manual_tx.id]
    assert subscription_tx.id not in [tx.id for tx in filtered]
    assert income_tx.id not in [tx.id for tx in filtered]


def test_get_transactions_uses_constant_queries_for_card_and_category(db_session):
    db_session.add_all(
        [
            models.PaymentMethod(name="Apple Pay", is_active=True),
            models.Category(name="交通", color="#123456"),
            models.CreditCard(
                name="通勤卡",
                billing_day=5,
                reward_cycle_type="CALENDAR_MONTH",
                alert_threshold=5000,
                default_payment_method="Apple Pay",
            ),
        ]
    )
    db_session.commit()

    category = db_session.query(models.Category).filter(models.Category.name == "交通").first()
    card = db_session.query(models.CreditCard).filter(models.CreditCard.name == "通勤卡").first()

    for index in range(3):
        transaction_service.create_transaction(
            db_session,
            schemas.TransactionCreate(
                date=date.today(),
                category="交通",
                category_id=category.id,
                item=f"通勤 {index + 1}",
                paid_amount=100 + index,
                transaction_amount=100 + index,
                payment_method="Apple Pay",
                card_id=card.id,
            ),
        )

    statements: list[str] = []
    engine = db_session.get_bind()

    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        normalized = " ".join(statement.lower().split())
        if normalized.startswith("select"):
            statements.append(normalized)

    event.listen(engine, "before_cursor_execute", before_cursor_execute)
    try:
        transactions = transaction_service.get_transactions(db_session, skip=0, limit=100)
    finally:
        event.remove(engine, "before_cursor_execute", before_cursor_execute)

    assert len(transactions) == 3
    assert all(tx.card_name == "通勤卡" for tx in transactions)
    assert all(tx.refundable_amount == tx.transaction_amount for tx in transactions)
    assert len([statement for statement in statements if "from transactions" in statement]) == 2
    assert not any("from credit_cards" in statement and "join" not in statement for statement in statements)
    assert not any("from categories" in statement and "join" not in statement for statement in statements)


def test_annual_report_endpoint_is_read_only_and_returns_camel_case(client: TestClient, db_session):
    today = date.today()
    db_session.add_all(
        [
            models.PaymentMethod(name="Cash", is_active=True),
            models.Category(name="餐飲", color="#f97316"),
        ]
    )
    db_session.commit()

    category = db_session.query(models.Category).filter(models.Category.name == "餐飲").first()
    db_session.add(
        models.Transaction(
            date=date(today.year, 1, 10),
            category="舊餐飲",
            category_id=category.id,
            item="午餐",
            paid_amount=320,
            transaction_amount=320,
            payment_method="Cash",
            transaction_type="EXPENSE",
        )
    )
    db_session.add(
        models.Subscription(
            name="尚未產生的訂閱",
            amount=199,
            category="娛樂",
            sub_type="SUBSCRIPTION",
            payment_method="Cash",
            day_of_month=min(today.day, 28),
            active=True,
        )
    )
    db_session.commit()

    before_count = db_session.query(models.Transaction).count()
    response = client.get(f"/transactions/report/annual/{today.year}")
    after_count = db_session.query(models.Transaction).count()

    assert response.status_code == 200
    assert before_count == after_count

    body = response.json()
    assert body["year"] == today.year
    assert len(body["monthlyTrend"]) == today.month
    assert body["categoryTrend"][0]["category"] == "餐飲"
    assert isinstance(body["monthlyTrend"][0]["totalExpense"], int)
    assert isinstance(body["summary"]["totalExpense"], int)
    assert body["summary"]["highestExpenseMonth"] == f"{today.year}-01"


def test_openapi_delete_summaries_do_not_mention_soft_delete(client: TestClient):
    response = client.get("/openapi.json")
    assert response.status_code == 200
    spec = response.json()
    assert "軟刪除" not in str(spec)
    assert "soft delete" not in str(spec).lower()
    assert "/transactions/report/annual/{year}" in spec["paths"]
    annual_report_schema = spec["paths"]["/transactions/report/annual/{year}"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]
    assert annual_report_schema["$ref"] == "#/components/schemas/AnnualReport"
