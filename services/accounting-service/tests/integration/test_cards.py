import requests
import random

BASE_URL = "http://127.0.0.1:8000/cards/"

def test_card_crud():
    name = f"卡片_{random.randint(1000, 9999)}"
    # Create
    card = requests.post(BASE_URL, json={"name": name, "billingDay": 10}).json()
    cid = card["id"]
    assert card["name"] == name

    # Update
    new_name = f"新名_{random.randint(1000, 9999)}"
    resp = requests.put(f"{BASE_URL}{cid}", json={"name": new_name})
    assert resp.status_code == 200
    updated = requests.get(f"{BASE_URL}{cid}").json()
    assert updated["name"] == new_name

    # Status
    status = requests.get(f"{BASE_URL}{cid}/status").json()
    assert "currentCycleTotal" in status

    # Cleanup
    requests.delete(f"{BASE_URL}{cid}")
