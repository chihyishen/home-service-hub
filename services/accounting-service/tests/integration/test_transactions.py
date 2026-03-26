from datetime import date

from app import models, schemas
from app.services import analytics_service, transaction_service


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
