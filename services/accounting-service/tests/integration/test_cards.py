from app import schemas
from app.services import billing_service, card_service


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
