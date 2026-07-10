from datetime import date, timedelta

import pytest
from app import models, schemas
from app.services import analytics_service, billing_service, card_service
from pydantic import ValidationError


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
        models.Transaction(
            card_id=None,
            category_id=category.id,
            transaction_amount=3000,
            transaction_type="EXPENSE",
            payment_method=card.name,
        ),
    ])
    other_card = card_service.create_card(
        db_session,
        schemas.CreditCardCreate(name="另一張卡", billing_day=10),
    )
    db_session.add(
        models.Transaction(
            card_id=other_card.id,
            category_id=category.id,
            transaction_amount=90000,
            transaction_type="EXPENSE",
            payment_method="LP",
        )
    )
    db_session.commit()

    status = billing_service.get_card_status(db_session, card.id)
    assert status.current_cycle_total == 73000
    assert status.filtered_usage == 20000
    assert status.remaining_for_max_reward == 13334
    assert "LP" in status.status_message


def test_alert_cycle_can_be_calendar_month_while_usage_stays_on_billing_cycle(db_session):
    today = date(2026, 7, 10)
    card = card_service.create_card(
        db_session,
        schemas.CreditCardCreate(
            name="獨立預警卡",
            billing_day=7,
            reward_cycle_type="BILLING_CYCLE",
            alert_threshold=33334,
            alert_payment_method="Line Pay",
            alert_cycle_type="CALENDAR_MONTH",
        ),
    )
    other_card = card_service.create_card(
        db_session,
        schemas.CreditCardCreate(name="其他卡", billing_day=7),
    )
    category = models.Category(name="預警測試", color="#64748b")
    db_session.add(category)
    db_session.commit()

    # Today is in the billing period after day 7. The first transaction is
    # outside that period but inside the current calendar month.
    db_session.add_all([
        models.Transaction(card_id=card.id, category_id=category.id, date=today.replace(day=5),
                           transaction_amount=33334, transaction_type="EXPENSE", payment_method="Line Pay"),
        models.Transaction(card_id=card.id, category_id=category.id, date=today.replace(day=9),
                           transaction_amount=20000, transaction_type="EXPENSE", payment_method="Apple Pay"),
        models.Transaction(card_id=card.id, category_id=category.id, date=today.replace(day=6) - timedelta(days=30),
                           transaction_amount=10000, transaction_type="EXPENSE", payment_method="Line Pay"),
        models.Transaction(card_id=other_card.id, category_id=category.id, date=today.replace(day=5),
                           transaction_amount=90000, transaction_type="EXPENSE", payment_method="Line Pay"),
    ])
    db_session.commit()

    status = billing_service.get_card_status(db_session, card.id, target_date=today)
    assert status.current_cycle_total == 20000
    assert status.filtered_usage == 33334
    assert status.remaining_for_max_reward == 0
    assert status.alert_period_start == today.replace(day=1).strftime("%Y-%m-%d")

    summary = analytics_service.get_card_usage_summary(db_session, target_date=today)
    card_summary = next(item for item in summary if item.card_name == card.name)
    assert card_summary.current_usage == 20000
    assert card_summary.alert_usage == 33334
    assert card_summary.alert_payment_method == "Line Pay"
    assert card_summary.alert_cycle_type == "CALENDAR_MONTH"
    assert card_summary.alert_cycle_start == today.replace(day=1)
    assert card_summary.remaining_to_threshold == 0


def test_alert_cycle_type_validation():
    with pytest.raises(ValidationError):
        schemas.CreditCardCreate(name="無效預警週期", billing_day=7, alert_cycle_type="WEEK")
    with pytest.raises(ValidationError):
        schemas.CreditCardUpdate(alert_cycle_type="WEEK")


def test_zero_alert_threshold_remains_disabled(db_session):
    card = card_service.create_card(
        db_session,
        schemas.CreditCardCreate(name="停用預警卡", billing_day=7, alert_threshold=0),
    )

    summary = analytics_service.get_card_usage_summary(
        db_session,
        target_date=date(2026, 7, 10),
    )
    card_summary = next(item for item in summary if item.card_name == card.name)
    assert card_summary.alert_threshold == 0
    assert card_summary.remaining_to_threshold == 0
    assert card_summary.is_near_limit is False
    assert card_summary.is_over_limit is False


def test_billing_cycle_handles_short_months_and_year_rollover():
    assert billing_service.get_billing_cycle_range(31, date(2026, 2, 15)) == (
        date(2026, 2, 1), date(2026, 2, 28)
    )
    assert billing_service.get_billing_cycle_range(31, date(2024, 2, 29)) == (
        date(2024, 2, 1), date(2024, 2, 29)
    )
    assert billing_service.get_billing_cycle_range(30, date(2026, 3, 15)) == (
        date(2026, 3, 1), date(2026, 3, 30)
    )
    assert billing_service.get_billing_cycle_range(10, date(2026, 1, 5)) == (
        date(2025, 12, 11), date(2026, 1, 10)
    )


@pytest.mark.parametrize("billing_day", [0, 32])
def test_billing_day_validation_on_create_and_update(billing_day):
    with pytest.raises(ValidationError):
        schemas.CreditCardCreate(name="無效卡", billing_day=billing_day)
    with pytest.raises(ValidationError):
        schemas.CreditCardUpdate(billing_day=billing_day)


def test_billing_day_update_remains_partial():
    update = schemas.CreditCardUpdate(name="只更新名稱")
    assert update.model_dump(exclude_unset=True) == {"name": "只更新名稱"}


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
