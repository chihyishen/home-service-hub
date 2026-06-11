import logging
import os
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from ...models.symbol_map import SymbolMap
from .helpers import _env_decimal, sanitize_symbol

logger = logging.getLogger(__name__)


def _schedule_symbol_history_backfill(symbol: str, from_date) -> None:
    """Fire-and-forget per-symbol price-history backfill in a daemon thread.

    No-op when ``SYMBOL_HISTORY_AUTOBACKFILL`` is falsy (the test suite and
    any deployment that disables it) so we never spawn network threads where
    they are not wanted. Runs in its own ``SessionLocal`` because the request
    session must not be touched from another thread.
    """
    if os.getenv("SYMBOL_HISTORY_AUTOBACKFILL", "true").lower() in {"false", "0", "no"}:
        return None

    import threading

    def _run() -> None:
        from ...database import SessionLocal
        from .. import symbol_history_service

        db = SessionLocal()
        try:
            today = datetime.now(UTC).date()
            written = symbol_history_service.backfill_symbol_history(
                db, symbol, from_date, today
            )
            logger.info(
                "symbol_history.autobackfill_done symbol=%s rows=%s", symbol, written
            )
        except Exception:
            logger.exception("symbol_history.autobackfill_failed symbol=%s", symbol)
        finally:
            db.close()

    threading.Thread(
        target=_run, name=f"history-backfill-{symbol}", daemon=True
    ).start()
    return None


def _is_tpex_marker(value: object) -> bool:
    text = str(value or "").strip().upper()
    return "TPEX" in text or "OTC" in text or "上櫃" in text


def _symbol_uses_tpex_history(db: Session, symbol: str) -> bool:
    """Return true when symbol_map says the ticker lives on TPEx/OTC."""
    rows = (
        db.query(SymbolMap.market, SymbolMap.type)
        .filter(SymbolMap.symbol == sanitize_symbol(symbol))
        .all()
    )
    return any(_is_tpex_marker(market) or _is_tpex_marker(type_) for market, type_ in rows)


def _schedule_tpex_symbol_history_backfill(symbol: str, from_date) -> None:
    """Fire-and-forget TPEx history fill for a newly held OTC symbol.

    TPEx has no cheap per-symbol equivalent to TWSE STOCK_DAY in this service,
    so this deliberately fetches TPEx full-market rows per weekday and lets
    ``market_data_service.backfill_date`` persist only ever-held symbols.
    Unlike the normal networth backfill, this does not skip dates merely
    because TPEx already has rows for other held symbols.
    """
    if os.getenv("SYMBOL_HISTORY_AUTOBACKFILL", "true").lower() in {"false", "0", "no"}:
        return None

    import threading
    import time

    def _run() -> None:
        from ...database import SessionLocal
        from .. import market_data_service, networth_backfill_service

        db = SessionLocal()
        try:
            today = datetime.now(UTC).date()
            throttle_sec = _env_decimal(
                "SYMBOL_HISTORY_TPEX_THROTTLE_SEC", "1.5"
            )
            dates_processed = 0
            rows_written = 0
            for trading_day in networth_backfill_service._iter_trading_days(
                from_date, today
            ):
                if dates_processed > 0 and throttle_sec > 0:
                    time.sleep(float(throttle_sec))
                result = market_data_service.backfill_date(
                    db, trading_day, market="TPEX"
                )
                dates_processed += 1
                rows_written += int(result.get("written", 0))
            logger.info(
                "symbol_history.tpex_autobackfill_done symbol=%s dates=%s rows=%s",
                symbol,
                dates_processed,
                rows_written,
            )
        except Exception:
            logger.exception("symbol_history.tpex_autobackfill_failed symbol=%s", symbol)
        finally:
            db.close()

    threading.Thread(
        target=_run, name=f"history-backfill-tpex-{symbol}", daemon=True
    ).start()
    return None
