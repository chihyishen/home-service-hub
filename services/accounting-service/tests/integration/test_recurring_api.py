from datetime import date

from app import models, schemas
from app.services import recurring_service
import pytest


def test_subscription_and_auto_gen(db_session):
    card = models.CreditCard(name="訂閱卡", billing_day=5, default_payment_method="Apple Pay")
    db_session.add(card)
    db_session.add(models.PaymentMethod(name="Apple Pay", is_active=True))
    db_session.commit()
    db_session.refresh(card)

    subscription = recurring_service.create_subscription(
        db_session,
        schemas.SubscriptionCreate(
            name="AutoTestSub",
            amount=100,
            category="T",
            day_of_month=1,
            card_id=card.id,
            payment_method="Apple Pay",
        ),
    )
    assert subscription.id is not None

    toggled = recurring_service.toggle_subscription_active(db_session, subscription.id)
    assert toggled.active is False

    reenabled = recurring_service.toggle_subscription_active(db_session, subscription.id)
    assert reenabled.active is True

    recurring_service.generate_recurring_items(db_session)
    generated = db_session.query(models.Transaction).filter(models.Transaction.subscription_id == subscription.id).all()
    assert len(generated) == 1


def test_completed_installment_can_be_deleted_and_detaches_history(db_session):
    db_session.add(models.PaymentMethod(name="信用卡", is_active=True))
    db_session.commit()

    installment = recurring_service.create_installment(
        db_session,
        schemas.InstallmentCreate(
            name="已完成分期",
            total_amount=12000,
            monthly_amount=1000,
            total_periods=12,
            remaining_periods=0,
            start_date=date(2026, 1, 1),
        ),
    )

    transaction = models.Transaction(
        date=date.today(),
        category="分期付款",
        item="已完成分期 (第 12/12 期)",
        paid_amount=1000,
        transaction_amount=1000,
        payment_method="Cash",
        installment_id=installment.id,
        transaction_type="EXPENSE",
    )
    db_session.add(transaction)
    db_session.commit()

    result = recurring_service.delete_installment(db_session, installment.id)

    db_session.expire_all()
    assert result["message"] == "Installment deleted"
    assert db_session.get(models.Installment, installment.id) is None
    assert db_session.get(models.Transaction, transaction.id).installment_id is None


def test_active_installment_cannot_be_deleted(db_session):
    db_session.add(models.PaymentMethod(name="信用卡", is_active=True))
    db_session.commit()

    installment = recurring_service.create_installment(
        db_session,
        schemas.InstallmentCreate(
            name="進行中分期",
            total_amount=6000,
            monthly_amount=500,
            total_periods=12,
            remaining_periods=3,
            start_date=date(2026, 1, 1),
        ),
    )

    with pytest.raises(Exception) as exc_info:
        recurring_service.delete_installment(db_session, installment.id)

    assert getattr(exc_info.value, "status_code", None) == 400
    assert getattr(exc_info.value, "detail", None) == "Only completed installments can be deleted"
