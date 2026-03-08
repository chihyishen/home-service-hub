import unittest
from datetime import datetime
from decimal import Decimal
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import portfolio as models
from app.schemas import portfolio as schemas
from app.services import portfolio_service


class TestPortfolioService(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        TestingSessionLocal = sessionmaker(bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.db = TestingSessionLocal()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)

    def test_sanitize_symbol(self):
        self.assertEqual(portfolio_service.sanitize_symbol("0050.TW"), "0050")
        self.assertEqual(portfolio_service.sanitize_symbol("00919.two"), "00919")
        self.assertEqual(portfolio_service.sanitize_symbol(" 2330 "), "2330")

    @patch("app.services.portfolio_service.get_stock_quotes")
    def test_get_portfolio_summary_with_holdings(self, mock_get_quotes):
        self.db.add(
            models.Transaction(
                symbol="0050.TW",
                name="元大台灣50",
                type=models.TransactionType.BUY,
                quantity=100,
                price=Decimal("100"),
                fee=Decimal("10"),
                tax=Decimal("0"),
                trade_date=datetime(2026, 1, 1),
            )
        )
        self.db.add(
            models.Transaction(
                symbol="0050",
                name="元大台灣50",
                type=models.TransactionType.SELL,
                quantity=20,
                price=Decimal("110"),
                fee=Decimal("5"),
                tax=Decimal("0"),
                trade_date=datetime(2026, 1, 2),
            )
        )
        self.db.add(
            models.Dividend(
                symbol="0050",
                amount=Decimal("120"),
                ex_dividend_date=datetime(2026, 1, 15),
                received_date=datetime(2026, 1, 20),
            )
        )
        self.db.commit()

        mock_get_quotes.return_value = {
            "0050": {
                "symbol": "0050",
                "name": "元大台灣50",
                "current_price": Decimal("120"),
                "yesterday_close": Decimal("119"),
                "time": "13:30:00",
            }
        }

        summary = portfolio_service.get_portfolio_summary(self.db)
        self.assertIsInstance(summary, schemas.PortfolioSummary)
        self.assertEqual(len(summary.holdings), 1)
        self.assertEqual(summary.holdings[0].symbol, "0050")
        self.assertEqual(summary.holdings[0].total_quantity, 80)
        self.assertEqual(summary.total_dividends, Decimal("120.00"))
        self.assertGreater(summary.total_market_value, Decimal("0"))

    def test_create_update_delete_transaction_and_dividend(self):
        created_tx = portfolio_service.create_transaction(
            self.db,
            schemas.TransactionCreate(
                symbol="00919.tw",
                name="群益台灣精選高息",
                type=schemas.TransactionType.BUY,
                quantity=10,
                price=Decimal("20"),
                fee=Decimal("0"),
                tax=Decimal("0"),
            ),
        )
        self.assertEqual(created_tx.symbol, "00919")

        updated_tx = portfolio_service.update_transaction(
            self.db,
            created_tx.id,
            schemas.TransactionCreate(
                symbol="00919.TWO",
                name="群益台灣精選高息",
                type=schemas.TransactionType.BUY,
                quantity=12,
                price=Decimal("21"),
                fee=Decimal("0"),
                tax=Decimal("0"),
            ),
        )
        self.assertIsNotNone(updated_tx)
        self.assertEqual(updated_tx.symbol, "00919")
        self.assertEqual(updated_tx.quantity, 12)

        created_div = portfolio_service.create_dividend(
            self.db,
            schemas.DividendCreate(
                symbol="00919.tw",
                amount=Decimal("25"),
                ex_dividend_date=datetime(2026, 2, 1),
                received_date=datetime(2026, 2, 10),
            ),
        )
        self.assertEqual(created_div.symbol, "00919")

        updated_div = portfolio_service.update_dividend(
            self.db,
            created_div.id,
            schemas.DividendCreate(
                symbol="00919.two",
                amount=Decimal("30"),
                ex_dividend_date=datetime(2026, 2, 1),
                received_date=datetime(2026, 2, 10),
            ),
        )
        self.assertIsNotNone(updated_div)
        self.assertEqual(updated_div.symbol, "00919")
        self.assertEqual(updated_div.amount, Decimal("30"))

        self.assertTrue(portfolio_service.delete_transaction(self.db, created_tx.id))
        self.assertTrue(portfolio_service.delete_dividend(self.db, created_div.id))


if __name__ == "__main__":
    unittest.main()
