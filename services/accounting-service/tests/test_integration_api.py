import requests
import sys

BASE_URL = "http://127.0.0.1:8000"

def test_full_workflow():
    print("🚀 開始 API 整合測試...")

    try:
        # 1. 健康檢查
        resp = requests.get(f"{BASE_URL}/")
        print(f"Health check status: {resp.status_code}")
        assert resp.status_code == 200
        print("✅ [GET /] 健康檢查正常")

        # 2. 建立信用卡
        import random
        card_data = {
            "name": f"測試卡_{random.randint(1000, 9999)}",
            "billing_day": 10,
            "reward_rules": [{"threshold": 5000, "name": "測試回饋"}],
            "alert_threshold": 10000
        }
        resp = requests.post(f"{BASE_URL}/cards/", json=card_data)
        if resp.status_code != 200:
            print(f"Post Card Failed: {resp.text}")
        assert resp.status_code == 200
        card_id = resp.json()["id"]
        print(f"✅ [POST /cards/] 信用卡建立成功 (ID: {card_id})")

        # 3. 新增收支
        resp = requests.post(f"{BASE_URL}/transactions/", json={
            "category": "薪資", "item": "API測試收入", "personal_amount": 5000.0,
            "actual_swipe": 0.0, "payment_method": "Bank", "transaction_type": "INCOME"
        })
        if resp.status_code != 200:
            print(f"Post Income Failed: {resp.text}")
        assert resp.status_code == 200
        
        resp = requests.post(f"{BASE_URL}/transactions/", json={
            "category": "餐飲", "item": "API測試支出", "personal_amount": 1000.0,
            "actual_swipe": 1000.0, "payment_method": "TestCard", "transaction_type": "EXPENSE",
            "card_id": card_id
        })
        if resp.status_code != 200:
            print(f"Post Expense Failed: {resp.text}")
        assert resp.status_code == 200
        print("✅ [POST /transactions/] 收支紀錄建立成功")

        # 4. 測試報表
        from datetime import date
        today = date.today()
        resp = requests.get(f"{BASE_URL}/transactions/report/{today.year}/{today.month}")
        assert resp.status_code == 200
        report = resp.json()
        print(f"✅ [GET /report] 報表獲取成功 (總收入: {report['summary']['total_income']})")

        # 5. 測試軟刪除
        resp = requests.delete(f"{BASE_URL}/cards/{card_id}")
        assert resp.status_code == 200
        resp = requests.get(f"{BASE_URL}/cards/{card_id}")
        assert resp.status_code == 404
        print("✅ [DELETE /cards/{id}] 軟刪除與過濾驗證成功")

        print("\n🎉 所有 API 整合測試通過！")

    except Exception as e:
        print(f"\n❌ 測試異常中斷: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    test_full_workflow()
