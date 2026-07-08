from app import models, schemas
from app.services import billing_service, card_service


def test_card_alert_payment_method_filters_threshold(db_session):
    card = card_service.create_card(
        db_session,
        schemas.CreditCardCreate(name="台新 Richart", billing_day=10, alert_threshold=33334),
    )
    card_service.update_card(
        db_session,
        card.id,
        schemas.CreditCardUpdate(alert_payment_method="LP"),
    )

    category = models.Category(name="購物", color="#64748b")
    db_session.add(category)
    db_session.commit()

    db_session.add_all([
        models.Transaction(
            card_id=card.id,
            category_id=category.id,
            transaction_amount=20000,
            transaction_type="EXPENSE",
            payment_method="LP",
        ),
        models.Transaction(
            card_id=card.id,
            category_id=category.id,
            transaction_amount=50000,
            transaction_type="EXPENSE",
            payment_method="Apple Pay",
        ),
    ])
    db_session.commit()

    status = billing_service.get_card_status(db_session, card.id)
    assert status.current_cycle_total == 70000
    assert status.filtered_usage == 20000
    assert status.remaining_for_max_reward == 13334
    assert "LP" in status.status_message


def test_card_crud(db_session):
    card = card_service.create_card(
        db_session,
        schemas.CreditCardCreate(name="測試卡", billing_day=10),
    )
    assert card.name == "測試卡"

    updated = card_service.update_card(
        db_session,
        card.id,
        schemas.CreditCardUpdate(name="更新卡"),
    )
    assert updated.name == "更新卡"

    fetched = card_service.get_card(db_session, card.id)
    assert fetched.name == "更新卡"

    status = billing_service.get_card_status(db_session, card.id)
    assert status is not None
    assert status.current_cycle_total == 0

    card_service.delete_card(db_session, card.id)
