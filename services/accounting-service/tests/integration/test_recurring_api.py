from datetime import date

import pytest
from app import models, schemas
from app.services import recurring_service
from fastapi.testclient import TestClient
from sqlalchemy import text


def _get_or_create_category(db_session, name: str, color: str = "#64748b") -> models.Category:
    category = db_session.query(models.Category).filter(models.Category.name == name).first()
    if category:
        return category

    category = models.Category(name=name, color=color)
    db_session.add(category)
    db_session.flush()
    return category


def _subscription_create(db_session, *, category_name: str, **kwargs) -> schemas.SubscriptionCreate:
    category = _get_or_create_category(db_session, category_name)
    return schemas.SubscriptionCreate(category_id=category.id, **kwargs)


def test_subscription_and_auto_gen(db_session):
    card = models.CreditCard(name="訂閱卡", billing_day=5, default_payment_method="Apple Pay")
    db_session.add(card)
    db_session.add(models.PaymentMethod(name="Apple Pay", is_active=True))
    db_session.commit()
    db_session.refresh(card)

    subscription = recurring_service.create_subscription(
        db_session,
        _subscription_create(
            db_session,
            category_name="T",
            name="AutoTestSub",
            amount=100,
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


def test_create_subscription_requires_category_id(client: TestClient, db_session):
    db_session.add(models.PaymentMethod(name="Cash", is_active=True))
    db_session.commit()

    response = client.post(
        "/api/accounting/recurring/subscriptions",
        json={
            "name": "串流",
            "amount": 290,
            "subType": "SUBSCRIPTION",
            "paymentMethod": "Cash",
            "dayOfMonth": 5,
            "active": True,
        },
    )

    assert response.status_code == 422


def test_update_subscription_rejects_null_category_id(client: TestClient, db_session):
    db_session.add(models.PaymentMethod(name="Cash", is_active=True))
    db_session.commit()

    subscription = recurring_service.create_subscription(
        db_session,
        _subscription_create(
            db_session,
            category_name="娛樂",
            name="串流",
            amount=290,
            sub_type="SUBSCRIPTION",
            payment_method="Cash",
            day_of_month=5,
            active=True,
        ),
    )

    response = client.put(
        f"/api/accounting/recurring/subscriptions/{subscription.id}",
        json={"categoryId": None},
    )

    assert response.status_code == 400
    assert response.json()["message"] == "category_id cannot be null"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("amount", 0),
        ("dayOfMonth", 0),
        ("dayOfMonth", 32),
        ("subType", "INVALID"),
    ],
)
def test_create_subscription_rejects_invalid_values(client: TestClient, db_session, field, value):
    db_session.add(models.PaymentMethod(name="Cash", is_active=True))
    category = _get_or_create_category(db_session, "訂閱驗證")
    db_session.commit()
    payload = {
        "name": "串流",
        "amount": 290,
        "categoryId": category.id,
        "subType": "SUBSCRIPTION",
        "paymentMethod": "Cash",
        "dayOfMonth": 5,
        "active": True,
    }
    payload[field] = value

    response = client.post("/api/accounting/recurring/subscriptions", json=payload)

    assert response.status_code == 400


def test_update_subscription_rejects_null_required_values(client: TestClient, db_session):
    db_session.add(models.PaymentMethod(name="Cash", is_active=True))
    db_session.commit()
    subscription = recurring_service.create_subscription(
        db_session,
        _subscription_create(
            db_session,
            category_name="訂閱驗證",
            name="串流",
            amount=290,
            day_of_month=5,
            payment_method="Cash",
        ),
    )

    for payload in ({"amount": None}, {"dayOfMonth": None}, {"active": None}):
        response = client.put(
            f"/api/accounting/recurring/subscriptions/{subscription.id}",
            json=payload,
        )
        assert response.status_code == 400


@pytest.mark.parametrize("sub_type", ["SUBSCRIPTION", "FIXED_EXPENSE"])
@pytest.mark.parametrize("operation", ["delete", "toggle"])
def test_stopping_subscription_preserves_existing_transactions(client, db_session, monkeypatch, sub_type, operation):
    db_session.execute(text("PRAGMA foreign_keys=ON"))
    category = _get_or_create_category(db_session, "訂閱")
    subscription = models.Subscription(
        name="claude", amount=600, day_of_month=13, category_id=category.id, sub_type=sub_type, active=True,
    )
    unrelated = models.Subscription(name="其他訂閱", category_id=category.id, active=False)
    db_session.add_all([subscription, unrelated])
    db_session.flush()
    transactions = [
        models.Transaction(
            date=transaction_date, category_id=category.id, item="claude", paid_amount=600,
            transaction_amount=600, payment_method="Cash", subscription_id=subscription.id,
            transaction_type="EXPENSE", note="保留原始帳目",
        )
        for transaction_date in (date(2026, 9, 13), date(2026, 10, 31))
    ]
    unrelated_transaction = models.Transaction(category_id=category.id, subscription_id=unrelated.id)
    db_session.add_all([*transactions, unrelated_transaction])
    db_session.commit()
    subscription_id = subscription.id
    fields = [column.name for column in models.Transaction.__table__.columns
              if column.name not in ("subscription_id", "updated_at")]
    snapshots = {transaction.id: {field: getattr(transaction, field) for field in fields}
                 for transaction in transactions}

    if operation == "delete":
        response = client.delete(f"/api/accounting/recurring/subscriptions/{subscription_id}")
    else:
        response = client.patch(f"/api/accounting/recurring/subscriptions/{subscription_id}/toggle")
    assert response.status_code == 200

    class FrozenDate(date):
        @classmethod
        def today(cls):
            return date(2026, 11, 1)

    monkeypatch.setattr(recurring_service, "date", FrozenDate)
    recurring_service.generate_recurring_items(db_session)
    db_session.expire_all()
    assert db_session.query(models.Transaction).count() == 3
    for transaction_id, snapshot in snapshots.items():
        transaction = db_session.get(models.Transaction, transaction_id)
        assert {field: getattr(transaction, field) for field in fields} == snapshot
        assert transaction.subscription_id == (None if operation == "delete" else subscription_id)
    assert db_session.get(models.Transaction, unrelated_transaction.id).subscription_id == unrelated.id
    if operation == "delete":
        assert db_session.get(models.Subscription, subscription_id) is None
        assert client.delete(f"/api/accounting/recurring/subscriptions/{subscription_id}").status_code == 404
    else:
        assert db_session.get(models.Subscription, subscription_id).active is False


def test_skip_subscription_current_month_is_reversible_without_deleting_history(client, db_session, monkeypatch):
    db_session.add(models.PaymentMethod(name="Cash", is_active=True))
    db_session.commit()

    class FrozenDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 10, 17)

    monkeypatch.setattr(recurring_service, "date", FrozenDate)
    skipped = recurring_service.create_subscription(
        db_session,
        _subscription_create(
            db_session,
            category_name="訂閱略過",
            name="本月略過",
            amount=100,
            day_of_month=5,
            payment_method="Cash",
        ),
    )
    with_history = recurring_service.create_subscription(
        db_session,
        _subscription_create(
            db_session,
            category_name="訂閱略過",
            name="保留既有帳目",
            amount=200,
            day_of_month=8,
            payment_method="Cash",
        ),
    )
    previous_month = recurring_service.create_subscription(
        db_session,
        _subscription_create(
            db_session,
            category_name="訂閱略過",
            name="上月略過",
            amount=300,
            day_of_month=12,
            payment_method="Cash",
        ),
    )
    previous_month.skipped_month = date(2026, 9, 1)
    existing = models.Transaction(
        date=date(2026, 10, 8),
        category_id=with_history.category_id,
        item="保留既有帳目",
        paid_amount=200,
        transaction_amount=200,
        payment_method="Cash",
        subscription_id=with_history.id,
        transaction_type="EXPENSE",
    )
    db_session.add(existing)
    db_session.commit()
    existing_snapshot = {field: getattr(existing, field) for field in (
        "date", "category_id", "item", "paid_amount", "transaction_amount", "payment_method", "transaction_type"
    )}

    for subscription in (skipped, with_history):
        response = client.post(
            f"/api/accounting/recurring/subscriptions/{subscription.id}/skip-current-month"
        )
        assert response.status_code == 200
        assert response.json()["skippedMonth"] == "2026-10-01"

    recurring_service.generate_recurring_items(db_session)
    assert db_session.query(models.Transaction).filter(models.Transaction.subscription_id == skipped.id).count() == 0
    preserved = db_session.query(models.Transaction).filter(models.Transaction.subscription_id == with_history.id).one()
    assert {field: getattr(preserved, field) for field in existing_snapshot} == existing_snapshot
    assert db_session.query(models.Transaction).filter(models.Transaction.subscription_id == previous_month.id).count() == 1

    response = client.delete(f"/api/accounting/recurring/subscriptions/{skipped.id}/skip-current-month")
    assert response.status_code == 200
    assert response.json()["skippedMonth"] is None
    recurring_service.generate_recurring_items(db_session)
    assert db_session.query(models.Transaction).filter(models.Transaction.subscription_id == skipped.id).count() == 1


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
        category_id=_get_or_create_category(db_session, "分期付款").id,
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


@pytest.mark.parametrize(
    "changes",
    [
        {"totalAmount": 0},
        {"monthlyAmount": 0},
        {"totalPeriods": 0},
        {"remainingPeriods": 4},
        {"totalAmount": 100, "monthlyAmount": 50},
    ],
)
def test_create_installment_rejects_invalid_amounts_and_periods(client: TestClient, db_session, changes):
    db_session.add(models.PaymentMethod(name="Cash", is_active=True))
    db_session.commit()
    payload = {
        "name": "測試分期",
        "totalAmount": 100,
        "monthlyAmount": 30,
        "totalPeriods": 3,
        "remainingPeriods": 3,
        "startDate": "2026-01-15",
        "paymentMethod": "Cash",
    }
    payload.update(changes)

    response = client.post("/api/accounting/recurring/installments", json=payload)

    assert response.status_code == 400


def test_update_installment_validates_merged_contract_and_nulls(client: TestClient, db_session):
    db_session.add(models.PaymentMethod(name="Cash", is_active=True))
    db_session.commit()
    installment = recurring_service.create_installment(
        db_session,
        schemas.InstallmentCreate(
            name="測試分期",
            total_amount=100,
            monthly_amount=30,
            total_periods=3,
            remaining_periods=3,
            start_date=date(2026, 1, 15),
            payment_method="Cash",
        ),
    )

    for payload in (
        {"totalAmount": None},
        {"monthlyAmount": None},
        {"totalPeriods": None},
        {"remainingPeriods": None},
        {"startDate": None},
        {"remainingPeriods": 4},
        {"monthlyAmount": 50},
    ):
        response = client.put(
            f"/api/accounting/recurring/installments/{installment.id}",
            json=payload,
        )
        assert response.status_code == 400

    response = client.put(
        f"/api/accounting/recurring/installments/{installment.id}",
        json={"monthlyAmount": 33},
    )
    assert response.status_code == 200
    assert response.json()["monthlyAmount"] == 33


def test_final_installment_uses_positive_contractual_tail(db_session, monkeypatch):
    db_session.add(models.PaymentMethod(name="Cash", is_active=True))
    db_session.commit()

    class FrozenDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 3, 17)

    monkeypatch.setattr(recurring_service, "date", FrozenDate)
    installment = recurring_service.create_installment(
        db_session,
        schemas.InstallmentCreate(
            name="自訂金額分期",
            total_amount=100,
            monthly_amount=30,
            total_periods=3,
            remaining_periods=3,
            start_date=date(2026, 1, 17),
            payment_method="Cash",
        ),
    )

    recurring_service.generate_recurring_items(db_session)

    transaction = db_session.query(models.Transaction).filter(
        models.Transaction.installment_id == installment.id
    ).one()
    assert transaction.paid_amount == transaction.transaction_amount == 40


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


def test_recurring_services_apply_card_default_payment_method_consistently(db_session):
    category = models.Category(name="娛樂", color="#123456")
    card = models.CreditCard(name="訂閱卡", billing_day=5, default_payment_method="Apple Pay")
    db_session.add_all(
        [
            category,
            card,
            models.PaymentMethod(name="Apple Pay", is_active=True),
        ]
    )
    db_session.commit()
    db_session.refresh(category)
    db_session.refresh(card)

    subscription = recurring_service.create_subscription(
        db_session,
        _subscription_create(
            db_session,
            category_name="娛樂",
            name="串流",
            amount=100,
            day_of_month=15,
            card_id=card.id,
        ),
    )
    assert subscription.payment_method == "Apple Pay"

    updated_subscription = recurring_service.update_subscription(
        db_session,
        subscription.id,
        schemas.SubscriptionUpdate(card_id=card.id),
    )
    assert updated_subscription.payment_method == "Apple Pay"

    installment = recurring_service.create_installment(
        db_session,
        schemas.InstallmentCreate(
            name="筆電",
            total_amount=36000,
            monthly_amount=3000,
            total_periods=12,
            remaining_periods=12,
            start_date=date(2026, 1, 15),
            card_id=card.id,
        ),
    )
    assert installment.payment_method == "Apple Pay"

    updated_installment = recurring_service.update_installment(
        db_session,
        installment.id,
        schemas.InstallmentUpdate(card_id=card.id),
    )
    assert updated_installment.payment_method == "Apple Pay"


@pytest.mark.parametrize(
    ("today_value", "expected_day"),
    [
        (date(2026, 2, 10), 28),
        (date(2026, 4, 10), 30),
        (date(2026, 3, 10), 31),
    ],
)
def test_generate_recurring_items_uses_real_month_end_for_subscription(db_session, monkeypatch, today_value, expected_day):
    db_session.add(models.PaymentMethod(name="Cash", is_active=True))
    db_session.commit()

    class FixedDate(date):
        @classmethod
        def today(cls):
            return cls(today_value.year, today_value.month, today_value.day)

    monkeypatch.setattr(recurring_service, "date", FixedDate)

    subscription = recurring_service.create_subscription(
        db_session,
        _subscription_create(
            db_session,
            category_name="娛樂",
            name=f"月底訂閱-{today_value.month}",
            amount=250,
            day_of_month=31,
            payment_method="Cash",
        ),
    )

    recurring_service.generate_recurring_items(db_session)
    generated = db_session.query(models.Transaction).filter(models.Transaction.subscription_id == subscription.id).one()

    assert generated.date == date(today_value.year, today_value.month, expected_day)


def test_generate_recurring_items_uses_real_month_end_for_installment(db_session, monkeypatch):
    db_session.add(models.PaymentMethod(name="Cash", is_active=True))
    db_session.commit()

    class FixedDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 3, 10)

    monkeypatch.setattr(recurring_service, "date", FixedDate)

    installment = recurring_service.create_installment(
        db_session,
        schemas.InstallmentCreate(
            name="月底分期",
            total_amount=9000,
            monthly_amount=3000,
            total_periods=3,
            remaining_periods=3,
            start_date=date(2026, 1, 31),
            payment_method="Cash",
        ),
    )

    recurring_service.generate_recurring_items(db_session)
    generated = db_session.query(models.Transaction).filter(models.Transaction.installment_id == installment.id).one()

    assert generated.date == date(2026, 3, 31)


def test_generate_recurring_items_skips_future_installments(db_session, monkeypatch):
    db_session.add(models.PaymentMethod(name="Cash", is_active=True))
    db_session.commit()

    class FixedDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 5, 20)

    monkeypatch.setattr(recurring_service, "date", FixedDate)

    installment = recurring_service.create_installment(
        db_session,
        schemas.InstallmentCreate(
            name="未來分期",
            total_amount=9000,
            monthly_amount=3000,
            total_periods=3,
            remaining_periods=3,
            start_date=date(2026, 6, 15), # June 15, 2026 (future)
            payment_method="Cash",
        ),
    )

    recurring_service.generate_recurring_items(db_session)
    generated = db_session.query(models.Transaction).filter(models.Transaction.installment_id == installment.id).all()

    # Should be empty because it hasn't started yet
    assert len(generated) == 0


def test_generate_recurring_items_determines_period_by_elapsed_months(db_session, monkeypatch):
    db_session.add(models.PaymentMethod(name="Cash", is_active=True))
    db_session.commit()

    class FixedDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 5, 20)

    monkeypatch.setattr(recurring_service, "date", FixedDate)

    # Created a 3-period installment with start date Feb 15, 2026
    # Today is May 20, 2026.
    # Feb -> Period 1
    # Mar -> Period 2
    # Apr -> Period 3
    # May -> Period 4 (already elapsed/out of range, should skip and set remaining_periods = 0)
    installment = recurring_service.create_installment(
        db_session,
        schemas.InstallmentCreate(
            name="過期分期",
            total_amount=9000,
            monthly_amount=3000,
            total_periods=3,
            remaining_periods=3,
            start_date=date(2026, 2, 15),
            payment_method="Cash",
        ),
    )

    recurring_service.generate_recurring_items(db_session)
    
    # Verify remaining periods is updated to 0 automatically
    db_session.refresh(installment)
    assert installment.remaining_periods == 0

    generated = db_session.query(models.Transaction).filter(models.Transaction.installment_id == installment.id).all()
    assert len(generated) == 0
