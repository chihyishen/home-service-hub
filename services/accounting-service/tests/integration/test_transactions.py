import requests

BASE_URL = "http://127.0.0.1:8000/transactions/"

def test_transaction_and_refund():
    # 1. Create
    tx = requests.post(BASE_URL, json={
        "category": "測試", "item": "測試支出", "personalAmount": 1000, 
        "actualSwipe": 1000, "paymentMethod": "Cash"
    }).json()
    tid = tx["id"]

    # 2. Refund
    refund = requests.post(f"{BASE_URL}{tid}/refund", params={"refund_amount": 200}).json()
    assert refund["transactionType"] == "INCOME"
    assert refund["relatedTransactionId"] == tid
    assert "退款" in refund["item"]

    # 3. Report
    from datetime import date
    today = date.today()
    report = requests.get(f"{BASE_URL}report/{today.year}/{today.month}").json()
    assert "summary" in report
