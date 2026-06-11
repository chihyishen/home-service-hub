from datetime import date

import pytest
from app.database import Base
from app.models.category import Category
from app.models.transaction import Transaction
from app.services import analytics_service
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()


def _get_or_create_category(db_session, name: str, color: str = "#64748b") -> Category:
    category = db_session.query(Category).filter(Category.name == name).first()
    if category:
        return category

    category = Category(name=name, color=color)
    db_session.add(category)
    db_session.flush()
    return category


def _transaction(db_session, *, category_name: str, **kwargs) -> Transaction:
    category = _get_or_create_category(db_session, category_name)
    return Transaction(category_id=category.id, **kwargs)

def test_monthly_report_math(db_session):
    # Setup test data
    db_session.add(_transaction(
        db_session,
        category_name="薪資",
        item="薪資", paid_amount=1000, transaction_amount=0,
        transaction_type="INCOME", date=date(2026, 2, 1), payment_method="Bank"
    ))
    db_session.add(_transaction(
        db_session,
        category_name="餐飲",
        item="晚餐", paid_amount=200, transaction_amount=200,
        transaction_type="EXPENSE", date=date(2026, 2, 1), payment_method="Cash"
    ))
    db_session.commit()

    report = analytics_service.get_monthly_report(db_session, 2026, 2)
    assert report.summary.total_income == 1000
    assert report.summary.total_expense == 200
    assert report.summary.surplus == 800
    assert isinstance(report.summary.total_income, int)
    assert isinstance(report.expense_breakdown[0].amount, int)


def test_monthly_report_nets_refund_against_original_expense(db_session):
    expense = _transaction(
        db_session,
        category_name="餐飲",
        item="晚餐",
        paid_amount=200,
        transaction_amount=200,
        transaction_type="EXPENSE",
        date=date(2026, 2, 15),
        payment_method="Cash",
    )
    salary = _transaction(
        db_session,
        category_name="薪資",
        item="薪資",
        paid_amount=1000,
        transaction_amount=1000,
        transaction_type="INCOME",
        date=date(2026, 2, 1),
        payment_method="Bank",
    )
    db_session.add_all([expense, salary])
    db_session.flush()

    refund = _transaction(
        db_session,
        category_name="餐飲",
        item="退款: 晚餐",
        paid_amount=50,
        transaction_amount=50,
        transaction_type="INCOME",
        date=date(2026, 2, 20),
        payment_method="Cash",
        related_transaction_id=expense.id,
    )
    db_session.add(refund)
    db_session.commit()

    report = analytics_service.get_monthly_report(db_session, 2026, 2)

    assert report.summary.total_income == 1000
    assert report.summary.total_expense == 150
    assert report.summary.surplus == 850
    assert report.summary.savings_rate == pytest.approx(85.0)
    assert report.expense_breakdown[0].category == "餐飲"
    assert report.expense_breakdown[0].amount == 150
    assert report.payment_breakdown[0].method == "Cash"
    assert report.payment_breakdown[0].amount == 150


def test_monthly_report_ignores_orphan_refund_income(db_session):
    db_session.add(
        _transaction(
            db_session,
            category_name="餐飲",
            item="退款: 孤兒",
            paid_amount=75,
            transaction_amount=75,
            transaction_type="INCOME",
            date=date(2026, 2, 20),
            payment_method="Cash",
            related_transaction_id=9999,
        )
    )
    db_session.commit()

    report = analytics_service.get_monthly_report(db_session, 2026, 2)

    assert report.summary.total_income == 0
    assert report.summary.total_expense == 0
    assert report.expense_breakdown == []
    assert report.payment_breakdown == []


def test_annual_report_math_and_category_sort(db_session):
    report_year = date.today().year - 1

    db_session.add_all(
        [
            _transaction(
                db_session,
                category_name="薪資",
                item="薪資", paid_amount=50000, transaction_amount=50000,
                transaction_type="INCOME", date=date(report_year, 1, 5), payment_method="Bank"
            ),
            _transaction(
                db_session,
                category_name="餐飲",
                item="午餐", paid_amount=3000, transaction_amount=3000,
                transaction_type="EXPENSE", date=date(report_year, 1, 10), payment_method="Cash"
            ),
            _transaction(
                db_session,
                category_name="交通",
                item="捷運", paid_amount=1200, transaction_amount=1200,
                transaction_type="EXPENSE", date=date(report_year, 6, 3), payment_method="EasyCard"
            ),
            _transaction(
                db_session,
                category_name="獎金",
                item="年終", paid_amount=10000, transaction_amount=10000,
                transaction_type="INCOME", date=date(report_year, 12, 20), payment_method="Bank"
            ),
            _transaction(
                db_session,
                category_name="餐飲",
                item="聚餐", paid_amount=4500, transaction_amount=4500,
                transaction_type="EXPENSE", date=date(report_year, 12, 25), payment_method="Cash"
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


def test_annual_report_nets_cross_month_refunds_to_original_month(db_session):
    report_year = date.today().year - 1
    march_food = _transaction(
        db_session,
        category_name="餐飲",
        item="聚餐",
        paid_amount=500,
        transaction_amount=500,
        transaction_type="EXPENSE",
        date=date(report_year, 3, 15),
        payment_method="Cash",
    )
    april_transport = _transaction(
        db_session,
        category_name="交通",
        item="高鐵",
        paid_amount=1000,
        transaction_amount=1000,
        transaction_type="EXPENSE",
        date=date(report_year, 4, 5),
        payment_method="Card",
    )
    june_transport = _transaction(
        db_session,
        category_name="交通",
        item="計程車",
        paid_amount=700,
        transaction_amount=700,
        transaction_type="EXPENSE",
        date=date(report_year, 6, 10),
        payment_method="Card",
    )
    salary = _transaction(
        db_session,
        category_name="薪資",
        item="薪資",
        paid_amount=5000,
        transaction_amount=5000,
        transaction_type="INCOME",
        date=date(report_year, 1, 5),
        payment_method="Bank",
    )
    db_session.add_all([salary, march_food, april_transport, june_transport])
    db_session.flush()

    db_session.add_all(
        [
            _transaction(
                db_session,
                category_name="餐飲",
                item="退款: 聚餐",
                paid_amount=500,
                transaction_amount=500,
                transaction_type="INCOME",
                date=date(report_year, 6, 1),
                payment_method="Cash",
                related_transaction_id=march_food.id,
            ),
            _transaction(
                db_session,
                category_name="交通",
                item="退款: 高鐵",
                paid_amount=400,
                transaction_amount=400,
                transaction_type="INCOME",
                date=date(report_year, 5, 1),
                payment_method="Card",
                related_transaction_id=april_transport.id,
            ),
        ]
    )
    db_session.commit()

    report = analytics_service.get_annual_report(db_session, report_year)
    food_trend = next(item for item in report.category_trend if item.category == "餐飲")

    assert report.summary.total_income == 5000
    assert report.summary.total_expense == 1300
    assert report.summary.surplus == 3700
    assert report.summary.highest_expense_month == f"{report_year}-06"
    assert report.summary.lowest_expense_month == f"{report_year}-04"
    assert report.monthly_trend[3].total_expense == 600
    assert report.monthly_trend[4].total_income == 0
    assert report.monthly_trend[5].total_expense == 700
    assert food_trend.monthly_amounts[2] == 0


def test_monthly_compare_nets_refunds_to_original_month(db_session):
    report_year = date.today().year - 1
    march_expense = _transaction(
        db_session,
        category_name="餐飲",
        item="三月聚餐",
        paid_amount=400,
        transaction_amount=400,
        transaction_type="EXPENSE",
        date=date(report_year, 3, 8),
        payment_method="Cash",
    )
    april_expense = _transaction(
        db_session,
        category_name="餐飲",
        item="四月聚餐",
        paid_amount=300,
        transaction_amount=300,
        transaction_type="EXPENSE",
        date=date(report_year, 4, 8),
        payment_method="Cash",
    )
    db_session.add_all([march_expense, april_expense])
    db_session.flush()

    db_session.add_all(
        [
            _transaction(
                db_session,
                category_name="餐飲",
                item="退款: 三月聚餐",
                paid_amount=100,
                transaction_amount=100,
                transaction_type="INCOME",
                date=date(report_year, 4, 3),
                payment_method="Cash",
                related_transaction_id=march_expense.id,
            ),
            _transaction(
                db_session,
                category_name="餐飲",
                item="退款: 四月聚餐",
                paid_amount=50,
                transaction_amount=50,
                transaction_type="INCOME",
                date=date(report_year, 5, 3),
                payment_method="Cash",
                related_transaction_id=april_expense.id,
            ),
        ]
    )
    db_session.commit()

    report = analytics_service.get_monthly_compare_report(db_session, report_year, 4)

    assert report.summary.total_expense_delta == -50
    assert report.categories[0].category == "餐飲"
    assert report.categories[0].current_amount == 250
    assert report.categories[0].previous_amount == 300
    assert report.categories[0].delta_amount == -50
    assert report.categories[0].status == "down"


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
            _transaction(
                db_session,
                category_name="薪資",
                item="今年薪資", paid_amount=32000, transaction_amount=32000,
                transaction_type="INCOME", date=date(current_year, 1, 5), payment_method="Bank"
            ),
            _transaction(
                db_session,
                category_name="餐飲",
                item="最近支出", paid_amount=1200, transaction_amount=1200,
                transaction_type="EXPENSE", date=date(current_year, current_month, 3), payment_method="Cash"
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
            _transaction(
                db_session,
                category_name="薪資",
                item="薪資", paid_amount=40000, transaction_amount=40000,
                transaction_type="INCOME", date=date(report_year, 3, 5), payment_method="Bank"
            ),
            _transaction(
                db_session,
                category_name="餐飲",
                item="晚餐", paid_amount=1800, transaction_amount=1800,
                transaction_type="EXPENSE", date=date(report_year, 3, 8), payment_method="Cash"
            ),
            _transaction(
                db_session,
                category_name="娛樂",
                item="電影", paid_amount=600, transaction_amount=600,
                transaction_type="EXPENSE", date=date(report_year, 3, 20), payment_method="Cash"
            ),
            _transaction(
                db_session,
                category_name="雜項",
                item="其他月份", paid_amount=500, transaction_amount=500,
                transaction_type="EXPENSE", date=date(report_year, 4, 1), payment_method="Cash"
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
