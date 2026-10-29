"""Atomic, restart-safe state for portfolio derived-data recalculation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from ..models.portfolio_recalc_state import PortfolioRecalcState

_TW_OFFSET = timezone(timedelta(hours=8))


def today_tw() -> date:
    return datetime.now(_TW_OFFSET).date()


def mark_mutation(
    db: Session, *, dates: list[date], touched_symbols: set[str]
) -> int:
    today = today_tw()
    return mark_dirty(
        db,
        recalc_from=min(min(dates), today),
        recalc_to=today,
        touched_symbols=touched_symbols,
        mode="snapshots",
    )


def mark_import_row(db: Session, *, event_date: date, symbol: str) -> int:
    today = today_tw()
    return mark_dirty(
        db,
        recalc_from=min(event_date, today),
        recalc_to=today,
        touched_symbols={symbol},
        mode="chain",
    )


@dataclass(frozen=True)
class RecalcWork:
    generation: int
    mode: str
    recalc_from: date
    recalc_to: date
    touched_symbols: set[str]
    status: str


def mark_dirty(
    db: Session,
    *,
    recalc_from: date,
    recalc_to: date,
    touched_symbols: set[str],
    mode: str,
) -> int:
    """Merge a mutation into the singleton marker in the caller's transaction."""
    if recalc_from > recalc_to:
        raise ValueError("recalc_from must be <= recalc_to")
    if mode not in {"snapshots", "chain"}:
        raise ValueError(f"unsupported recalc mode: {mode}")

    row = (
        db.query(PortfolioRecalcState)
        .filter(PortfolioRecalcState.id == 1)
        .populate_existing()
        .with_for_update()
        .one_or_none()
    )
    if row is None:
        # Production migrations seed this row; create_all-based tests do not.
        row = PortfolioRecalcState(
            id=1,
            generation=0,
            status="idle",
            mode="snapshots",
            touched_symbols=[],
        )
        db.add(row)
        db.flush()

    if row.status != "idle" and row.recalc_from is not None:
        row.recalc_from = min(row.recalc_from, recalc_from)
        row.recalc_to = max(row.recalc_to, recalc_to)
        row.touched_symbols = sorted(set(row.touched_symbols or []) | touched_symbols)
        if mode == "chain":
            row.mode = "chain"
    else:
        row.recalc_from = recalc_from
        row.recalc_to = recalc_to
        row.touched_symbols = sorted(touched_symbols)
        row.mode = mode

    row.generation += 1
    row.status = "pending"
    row.current_step = None
    row.error = None
    return row.generation


def get_work(db: Session) -> RecalcWork | None:
    row = db.get(PortfolioRecalcState, 1)
    if row is None or row.status == "idle" or row.recalc_from is None or row.recalc_to is None:
        return None
    return RecalcWork(
        generation=row.generation,
        mode=row.mode,
        recalc_from=row.recalc_from,
        recalc_to=row.recalc_to,
        touched_symbols=set(row.touched_symbols or []),
        status=row.status,
    )


def retry_work(db: Session) -> RecalcWork | None:
    row = (
        db.query(PortfolioRecalcState)
        .filter(PortfolioRecalcState.id == 1)
        .populate_existing()
        .with_for_update()
        .one_or_none()
    )
    if row is None or row.status not in {"failed", "partial"}:
        return get_work(db)
    row.generation += 1
    row.status = "pending"
    row.current_step = None
    row.error = None
    db.commit()
    return get_work(db)


def set_status(
    db: Session,
    generation: int,
    *,
    status: str,
    current_step: str | None = None,
    error: str | None = None,
) -> bool:
    row = (
        db.query(PortfolioRecalcState)
        .filter(PortfolioRecalcState.id == 1)
        .populate_existing()
        .with_for_update()
        .one_or_none()
    )
    if row is None or row.generation != generation:
        return False
    row.status = status
    row.current_step = current_step
    row.error = error
    if status == "idle":
        row.mode = "snapshots"
        row.recalc_from = None
        row.recalc_to = None
        row.touched_symbols = []
    db.commit()
    return True


def status_response(db: Session) -> dict | None:
    row = db.get(PortfolioRecalcState, 1)
    if row is None or row.status == "idle":
        return None
    state = "running" if row.status in {"pending", "running"} else row.status
    steps = []
    if row.error:
        steps = [{"name": row.current_step or row.mode, "status": "failed", "error": row.error}]
    return {
        "state": state,
        "recalc_from": row.recalc_from.isoformat() if row.recalc_from else None,
        "recalc_to": row.recalc_to.isoformat() if row.recalc_to else None,
        "touched_symbols": row.touched_symbols or [],
        "current_step": row.current_step or ("queued" if row.status == "pending" else None),
        "steps": steps,
    }
