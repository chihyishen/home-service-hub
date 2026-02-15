import requests

BASE_URL = "http://127.0.0.1:8000/recurring/"

def test_subscription_and_auto_gen():
    # 1. Create Sub
    sub = requests.post(f"{BASE_URL}subscriptions", json={
        "name": "AutoTestSub", "amount": 100, "category": "T", "dayOfMonth": 1, "cardId": 1
    }).json()
    sid = sub["id"]

    # 2. Toggle
    requests.patch(f"{BASE_URL}subscriptions/{sid}/toggle")
    updated = requests.get(f"{BASE_URL}subscriptions").json()
    assert any(s["id"] == sid and s["active"] == False for s in updated)

    # 3. Generate
    requests.post(f"{BASE_URL}generate")
    print("✅ Recurring Generation Triggered")
