from datetime import date

from app import models, schemas
from app.services import analytics_service, billing_service, transaction_service


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

    today = date.today()
    report = analytics_service.get_monthly_report(db_session, today.year, today.month)
    assert report.summary.total_income >= 200


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
