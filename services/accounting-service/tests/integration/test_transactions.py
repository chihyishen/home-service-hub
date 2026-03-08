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
