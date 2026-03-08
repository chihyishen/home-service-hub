from app import models, schemas
from app.services import recurring_service


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
