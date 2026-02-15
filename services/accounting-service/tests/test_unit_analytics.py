import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import date

# 修正路徑以匯入 app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "app/..")))

from app import models, schemas
from app.database import Base
from app.services import analytics_service

# 使用記憶體資料庫進行測試
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def test_report():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    try:
        # 1. 建立測試資料
        db.add(models.Transaction(
            date=date(2026, 2, 1),
            category="薪資",
            item="2月薪資",
            personal_amount=50000.0,
            actual_swipe=0.0,
            payment_method="Bank",
            transaction_type="INCOME"
        ))
        db.add(models.Transaction(
            date=date(2026, 2, 5),
            category="餐飲",
            item="午餐",
            personal_amount=150.0,
            actual_swipe=150.0,
            payment_method="Cash",
            transaction_type="EXPENSE"
        ))
        db.add(models.Transaction(
            date=date(2026, 2, 10),
            category="娛樂",
            item="Netflix",
            personal_amount=390.0,
            actual_swipe=390.0,
            payment_method="FlyGo",
            transaction_type="EXPENSE"
        ))
        db.commit()

        # 2. 執行報表計算
        report = analytics_service.get_monthly_report(db, 2026, 2)

        # 3. 驗證
        print(f"Period: {report.period}")
        print(f"Total Income: {report.summary.total_income}")
        print(f"Total Expense: {report.summary.total_expense}")
        print(f"Surplus: {report.summary.surplus}")
        
        assert report.summary.total_income == 50000.0
        assert report.summary.total_expense == 540.0
        print("\n✅ Test Passed!")

    finally:
        db.close()

if __name__ == "__main__":
    test_report()
