from datetime import date

import pytest
from fastapi.testclient import TestClient

from app import models


def _create_category(client: TestClient, name: str, color: str) -> dict:
    response = client.post(
        "/categories/",
        json={"name": name, "color": color},
    )
    assert response.status_code == 200
    return response.json()


def _build_transaction(*, category: str, category_id: int | None, item: str) -> models.Transaction:
    return models.Transaction(
        date=date.today(),
        category=category,
        category_id=category_id,
        item=item,
        paid_amount=100,
        transaction_amount=100,
        payment_method="Cash",
        transaction_type="EXPENSE",
    )


def _build_subscription(*, category: str, category_id: int | None, name: str) -> models.Subscription:
    return models.Subscription(
        name=name,
        amount=200,
        category=category,
        category_id=category_id,
        sub_type="SUBSCRIPTION",
        payment_method="Cash",
        day_of_month=1,
        active=True,
    )


def test_update_category_syncs_linked_transactions_and_subscriptions(client: TestClient, db_session):
    category = _create_category(client, name="餐飲", color="#111111")

    linked_transaction = _build_transaction(category="餐飲", category_id=category["id"], item="午餐")
    legacy_transaction = _build_transaction(category="餐飲", category_id=None, item="舊資料")
    linked_subscription = _build_subscription(category="餐飲", category_id=category["id"], name="午餐訂閱")
    legacy_subscription = _build_subscription(category="餐飲", category_id=None, name="舊訂閱")
    db_session.add_all([
        linked_transaction,
        legacy_transaction,
        linked_subscription,
        legacy_subscription,
    ])
    db_session.commit()

    response = client.put(
        f"/categories/{category['id']}",
        json={"name": "外食", "color": "#222222"},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "外食"
    assert response.json()["color"] == "#222222"

    db_session.expire_all()
    refreshed_linked_transaction = db_session.get(models.Transaction, linked_transaction.id)
    refreshed_legacy_transaction = db_session.get(models.Transaction, legacy_transaction.id)
    refreshed_linked_subscription = db_session.get(models.Subscription, linked_subscription.id)
    refreshed_legacy_subscription = db_session.get(models.Subscription, legacy_subscription.id)

    assert refreshed_linked_transaction.category_id == category["id"]
    assert refreshed_linked_transaction.category == "外食"
    assert refreshed_legacy_transaction.category_id is None
    assert refreshed_legacy_transaction.category == "餐飲"
    assert refreshed_linked_subscription.category_id == category["id"]
    assert refreshed_linked_subscription.category == "外食"
    assert refreshed_legacy_subscription.category_id is None
    assert refreshed_legacy_subscription.category == "餐飲"


def test_category_merge_preview_returns_source_target_and_affected_counts(client: TestClient, db_session):
    source = _create_category(client, name="餐飲", color="#111111")
    target = _create_category(client, name="外食", color="#222222")

    db_session.add_all(
        [
            _build_transaction(category="餐飲", category_id=source["id"], item="午餐"),
            _build_transaction(category="餐飲", category_id=source["id"], item="晚餐"),
            _build_transaction(category="外食", category_id=target["id"], item="宵夜"),
            _build_subscription(category="餐飲", category_id=source["id"], name="餐盒"),
        ]
    )
    db_session.commit()

    response = client.post(
        "/categories/merge-preview",
        json={
            "sourceCategoryId": source["id"],
            "targetCategoryId": target["id"],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["affectedTransactions"] == 2
    assert body["affectedSubscriptions"] == 1
    assert body["sourceCategory"]["id"] == source["id"]
    assert body["sourceCategory"]["name"] == "餐飲"
    assert body["sourceCategory"]["color"] == "#111111"
    assert body["sourceCategory"]["createdAt"]
    assert body["sourceCategory"]["updatedAt"]
    assert body["targetCategory"]["id"] == target["id"]
    assert body["targetCategory"]["name"] == "外食"
    assert body["targetCategory"]["color"] == "#222222"
    assert body["targetCategory"]["createdAt"]
    assert body["targetCategory"]["updatedAt"]


def test_category_merge_apply_repoints_records_and_deletes_source(client: TestClient, db_session):
    source = _create_category(client, name="串流", color="#333333")
    target = _create_category(client, name="娛樂", color="#444444")

    linked_transaction = _build_transaction(category="串流", category_id=source["id"], item="影音月費")
    linked_subscription = _build_subscription(category="串流", category_id=source["id"], name="串流服務")
    legacy_transaction = _build_transaction(category="串流", category_id=None, item="舊字串")
    db_session.add_all([linked_transaction, linked_subscription, legacy_transaction])
    db_session.commit()

    response = client.post(
        "/categories/merge",
        json={
            "sourceCategoryId": source["id"],
            "targetCategoryId": target["id"],
        },
    )

    assert response.status_code == 200
    assert response.json()["sourceCategory"]["id"] == source["id"]
    assert response.json()["targetCategory"]["id"] == target["id"]
    assert response.json()["affectedTransactions"] == 1
    assert response.json()["affectedSubscriptions"] == 1
    assert response.json()["deletedSourceCategoryId"] == source["id"]

    db_session.expire_all()
    merged_transaction = db_session.get(models.Transaction, linked_transaction.id)
    merged_subscription = db_session.get(models.Subscription, linked_subscription.id)
    unchanged_legacy_transaction = db_session.get(models.Transaction, legacy_transaction.id)

    assert db_session.get(models.Category, source["id"]) is None
    assert merged_transaction.category_id == target["id"]
    assert merged_transaction.category == "娛樂"
    assert merged_subscription.category_id == target["id"]
    assert merged_subscription.category == "娛樂"
    assert unchanged_legacy_transaction.category_id is None
    assert unchanged_legacy_transaction.category == "串流"


@pytest.mark.parametrize("path", ["/categories/merge-preview", "/categories/merge"])
def test_category_merge_errors(client: TestClient, path: str):
    existing = _create_category(client, name="交通", color="#555555")

    same_response = client.post(
        path,
        json={
            "sourceCategoryId": existing["id"],
            "targetCategoryId": existing["id"],
        },
    )
    assert same_response.status_code == 400
    same_body = same_response.json()
    assert same_body["code"] == 400
    assert same_body["message"] == "Source and target categories must be different"
    assert same_body["trace_id"]

    missing_source_response = client.post(
        path,
        json={
            "sourceCategoryId": 9999,
            "targetCategoryId": existing["id"],
        },
    )
    assert missing_source_response.status_code == 404
    missing_source_body = missing_source_response.json()
    assert missing_source_body["code"] == 404
    assert missing_source_body["message"] == "Source category not found"
    assert missing_source_body["trace_id"]

    missing_target_response = client.post(
        path,
        json={
            "sourceCategoryId": existing["id"],
            "targetCategoryId": 9999,
        },
    )
    assert missing_target_response.status_code == 404
    missing_target_body = missing_target_response.json()
    assert missing_target_body["code"] == 404
    assert missing_target_body["message"] == "Target category not found"
    assert missing_target_body["trace_id"]
