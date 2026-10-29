import os
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from urllib.parse import urlparse
from uuid import uuid4

import pytest
from app import models
from app.database import Base
from app.services.recurring_service import generate_recurring_items
from sqlalchemy import create_engine, event, extract, text
from sqlalchemy.orm import sessionmaker


@pytest.mark.skipif(
    not os.getenv("ACCOUNTING_CONCURRENCY_TEST_DATABASE_URL"),
    reason="requires an explicitly configured disposable PostgreSQL database",
)
@pytest.mark.parametrize("source_type", ["subscription", "installment"])
def test_concurrent_generation_creates_one_transaction(source_type):
    url = os.environ["ACCOUNTING_CONCURRENCY_TEST_DATABASE_URL"]
    parsed = urlparse(url)
    if parsed.hostname not in {"127.0.0.1", "localhost", "::1"} or parsed.path != "/audit":
        pytest.fail("concurrency test URL must point to loopback database /audit")

    admin_engine = create_engine(url)
    schema = f"recurring_race_{uuid4().hex}"
    engine = create_engine(
        url,
        connect_args={"options": f"-csearch_path={schema} -cstatement_timeout=5000 -clock_timeout=2000"},
        pool_size=2,
        max_overflow=0,
    )
    listener_added = False
    try:
        with admin_engine.begin() as conn:
            conn.execute(text(f'CREATE SCHEMA "{schema}"'))
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        first_checked = threading.Event()
        second_checked = threading.Event()
        check_count = 0
        count_lock = threading.Lock()
        today = date.today()

        with Session() as db:
            category = models.Category(name="Concurrency Test")
            db.add(category)
            db.flush()
            if source_type == "subscription":
                source = models.Subscription(
                    name="Concurrent subscription",
                    amount=1,
                    category_id=category.id,
                    sub_type="SUBSCRIPTION",
                    payment_method="Cash",
                    day_of_month=1,
                    active=True,
                )
            else:
                source = models.Installment(
                    name="Concurrent installment",
                    total_amount=12,
                    monthly_amount=1,
                    payment_method="Cash",
                    total_periods=12,
                    remaining_periods=12,
                    start_date=today.replace(day=1),
                )
            db.add(source)
            db.commit()
            source_id = source.id

        def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            nonlocal check_count
            normalized = " ".join(statement.lower().split())
            if "from transactions" not in normalized or f"{source_type}_id" not in normalized:
                return
            with count_lock:
                check_count += 1
                index = check_count
            if index == 1:
                first_checked.set()
                second_checked.wait(timeout=1)
            elif index == 2:
                second_checked.set()

        event.listen(engine, "after_cursor_execute", after_cursor_execute)
        listener_added = True

        def run_generation():
            with Session() as db:
                generate_recurring_items(db)

        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(run_generation)
            assert first_checked.wait(timeout=3)
            second = pool.submit(run_generation)
            first.result(timeout=5)
            second.result(timeout=5)
        with Session() as db:
            generated = db.query(models.Transaction).filter(
                getattr(models.Transaction, f"{source_type}_id") == source_id,
                extract("year", models.Transaction.date) == today.year,
                extract("month", models.Transaction.date) == today.month,
            ).count()
        assert generated == 1
    finally:
        if listener_added:
            event.remove(engine, "after_cursor_execute", after_cursor_execute)
        engine.dispose()
        with admin_engine.begin() as conn:
            conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        admin_engine.dispose()
