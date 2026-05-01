import pytest
from datetime import date
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models.category import Category
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
    assert isinstance(report.summary.total_income, int)
    assert isinstance(report.expense_breakdown[0].amount, int)


def test_annual_report_math_and_category_sort(db_session):
    report_year = date.today().year - 1
    food = Category(name="餐飲", color="#f00")
    transport = Category(name="交通", color="#0f0")
    db_session.add_all([food, transport])
    db_session.flush()

    db_session.add_all(
        [
            Transaction(
                item="薪資", paid_amount=50000, transaction_amount=50000,
                transaction_type="INCOME", date=date(report_year, 1, 5), category="薪資", payment_method="Bank"
            ),
            Transaction(
                item="午餐", paid_amount=3000, transaction_amount=3000,
                transaction_type="EXPENSE", date=date(report_year, 1, 10), category="舊餐飲", category_id=food.id, payment_method="Cash"
            ),
            Transaction(
                item="捷運", paid_amount=1200, transaction_amount=1200,
                transaction_type="EXPENSE", date=date(report_year, 6, 3), category="交通", category_id=transport.id, payment_method="EasyCard"
            ),
            Transaction(
                item="年終", paid_amount=10000, transaction_amount=10000,
                transaction_type="INCOME", date=date(report_year, 12, 20), category="獎金", payment_method="Bank"
            ),
            Transaction(
                item="聚餐", paid_amount=4500, transaction_amount=4500,
                transaction_type="EXPENSE", date=date(report_year, 12, 25), category="餐飲", category_id=food.id, payment_method="Cash"
            ),
        ]
    )
    db_session.commit()

    report = analytics_service.get_annual_report(db_session, report_year)

    assert report.year == report_year
    assert len(report.monthly_trend) == 12
    assert report.monthly_trend[0].month == f"{report_year}-01"
    assert report.monthly_trend[0].total_income == 50000
    assert report.monthly_trend[0].total_expense == 3000
    assert report.monthly_trend[5].total_expense == 1200
    assert report.monthly_trend[11].total_income == 10000
    assert report.summary.total_income == 60000
    assert report.summary.total_expense == 8700
    assert report.summary.surplus == 51300
    assert report.summary.highest_expense_month == f"{report_year}-12"
    assert report.summary.lowest_expense_month == f"{report_year}-06"
    assert report.category_trend[0].category == "餐飲"
    assert report.category_trend[0].monthly_amounts[0] == 3000
    assert report.category_trend[0].monthly_amounts[11] == 4500
    assert report.category_trend[0].total == 7500
    assert report.category_trend[0].average == 625
    assert isinstance(report.category_trend[0].total, int)
    assert isinstance(report.summary.savings_rate, float)


def test_annual_report_empty_year_and_single_query(db_session):
    empty_year = date.today().year - 2
    statements: list[str] = []
    engine = db_session.get_bind()

    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        if "from transactions" in statement.lower():
            statements.append(statement)

    event.listen(engine, "before_cursor_execute", before_cursor_execute)
    try:
        report = analytics_service.get_annual_report(db_session, empty_year)
    finally:
        event.remove(engine, "before_cursor_execute", before_cursor_execute)

    assert len(report.monthly_trend) == 12
    assert all(point.total_income == 0 for point in report.monthly_trend)
    assert all(point.total_expense == 0 for point in report.monthly_trend)
    assert report.category_trend == []
    assert report.summary.total_income == 0
    assert report.summary.total_expense == 0
    assert report.summary.highest_expense_month is None
    assert report.summary.lowest_expense_month is None
    assert len(statements) == 1


def test_current_year_annual_report_returns_year_to_date_months(db_session):
    current_year = date.today().year
    current_month = date.today().month

    db_session.add_all(
        [
            Transaction(
                item="今年薪資", paid_amount=32000, transaction_amount=32000,
                transaction_type="INCOME", date=date(current_year, 1, 5), category="薪資", payment_method="Bank"
            ),
            Transaction(
                item="最近支出", paid_amount=1200, transaction_amount=1200,
                transaction_type="EXPENSE", date=date(current_year, current_month, 3), category="餐飲", payment_method="Cash"
            ),
        ]
    )
    db_session.commit()

    report = analytics_service.get_annual_report(db_session, current_year)

    assert len(report.monthly_trend) == current_month
    assert report.monthly_trend[0].month == f"{current_year}-01"
    assert report.monthly_trend[-1].month == f"{current_year}-{current_month:02d}"
    assert report.monthly_trend[0].total_income == 32000
    assert report.monthly_trend[-1].total_expense == 1200
    assert len(report.category_trend[0].monthly_amounts) == current_month


def test_annual_report_matches_monthly_report_for_same_month(db_session):
    report_year = date.today().year - 1
    db_session.add_all(
        [
            Transaction(
                item="薪資", paid_amount=40000, transaction_amount=40000,
                transaction_type="INCOME", date=date(report_year, 3, 5), category="薪資", payment_method="Bank"
            ),
            Transaction(
                item="晚餐", paid_amount=1800, transaction_amount=1800,
                transaction_type="EXPENSE", date=date(report_year, 3, 8), category="餐飲", payment_method="Cash"
            ),
            Transaction(
                item="電影", paid_amount=600, transaction_amount=600,
                transaction_type="EXPENSE", date=date(report_year, 3, 20), category="娛樂", payment_method="Cash"
            ),
            Transaction(
                item="其他月份", paid_amount=500, transaction_amount=500,
                transaction_type="EXPENSE", date=date(report_year, 4, 1), category="雜項", payment_method="Cash"
            ),
        ]
    )
    db_session.commit()

    monthly = analytics_service.get_monthly_report(db_session, report_year, 3)
    annual = analytics_service.get_annual_report(db_session, report_year)
    march = annual.monthly_trend[2]

    assert march.total_income == monthly.summary.total_income
    assert march.total_expense == monthly.summary.total_expense
    assert march.surplus == monthly.summary.surplus
