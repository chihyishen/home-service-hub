import pytest
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models.transaction import Transaction
from app.services import analytics_service

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()

def test_monthly_report_math(db_session):
    # Setup test data
    db_session.add(Transaction(
        item="薪資", paid_amount=1000, transaction_amount=0, 
        transaction_type="INCOME", date=date(2026, 2, 1), category="Work", payment_method="Bank"
    ))
    db_session.add(Transaction(
        item="晚餐", paid_amount=200, transaction_amount=200, 
        transaction_type="EXPENSE", date=date(2026, 2, 1), category="Food", payment_method="Cash"
    ))
    db_session.commit()

    report = analytics_service.get_monthly_report(db_session, 2026, 2)
    assert report.summary.total_income == 1000
    assert report.summary.total_expense == 200
    assert report.summary.surplus == 800
