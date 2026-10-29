from contextlib import contextmanager
from datetime import date
from decimal import Decimal

from app.models.portfolio_recalc_state import PortfolioRecalcState
from app.schemas.portfolio import TransactionCreate, TransactionType
from app.services import portfolio_recalc_service as recalc_state
from app.services import portfolio_service
from app.services import post_import_orchestrator as orch


def test_manual_transaction_marks_snapshot_only_work(db_session):
    portfolio_service.create_transaction(
        db_session,
        TransactionCreate(
            symbol="2330",
            type=TransactionType.BUY,
            quantity=10,
            price=Decimal("50"),
            trade_date="2026-05-14T00:00:00Z",
        ),
    )

    work = recalc_state.get_work(db_session)
    assert work is not None
    assert work.mode == "snapshots"
    assert work.touched_symbols == {"2330"}


def test_new_generation_survives_stale_worker_completion(db_session):
    first = recalc_state.mark_dirty(
        db_session,
        recalc_from=date(2026, 5, 10),
        recalc_to=date(2026, 5, 15),
        touched_symbols={"2330"},
        mode="snapshots",
    )
    db_session.commit()
    recalc_state.mark_dirty(
        db_session,
        recalc_from=date(2026, 5, 12),
        recalc_to=date(2026, 5, 18),
        touched_symbols={"0050"},
        mode="chain",
    )
    db_session.commit()

    assert recalc_state.set_status(db_session, first, status="idle") is False
    work = recalc_state.get_work(db_session)
    assert work is not None
    assert work.generation == first + 1
    assert work.recalc_from == date(2026, 5, 10)
    assert work.recalc_to == date(2026, 5, 18)
    assert work.touched_symbols == {"2330", "0050"}
    assert work.mode == "chain"


def test_retry_refreshes_preloaded_locked_state(db_session):
    generation = recalc_state.mark_dirty(
        db_session,
        recalc_from=date(2026, 5, 10),
        recalc_to=date(2026, 5, 15),
        touched_symbols={"2330"},
        mode="snapshots",
    )
    db_session.commit()
    assert recalc_state.get_work(db_session).generation == generation
    preloaded = db_session.get(PortfolioRecalcState, 1)

    # Simulate another transaction changing the row after the endpoint's read.
    db_session.connection().execute(
        PortfolioRecalcState.__table__
        .update()
        .where(PortfolioRecalcState.id == 1)
        .values(generation=generation + 1, status="failed", error="previous attempt")
    )

    retried = recalc_state.retry_work(db_session)
    assert retried is not None
    assert retried.generation == generation + 2
    assert retried.status == "pending"
    assert preloaded.generation == generation + 2


def test_pending_snapshot_work_completes_without_full_chain(db_session, monkeypatch):
    recalc_state.mark_dirty(
        db_session,
        recalc_from=date(2026, 5, 14),
        recalc_to=date(2026, 5, 15),
        touched_symbols={"2330"},
        mode="snapshots",
    )
    db_session.commit()

    @contextmanager
    def session_factory():
        yield db_session

    def snapshots_only(_factory, from_date, to_date):
        assert (from_date, to_date) == (date(2026, 5, 14), date(2026, 5, 15))
        return orch.StepResult("networth_snapshot_replay", "ok")

    monkeypatch.setattr(orch, "_step_snapshot_replay", snapshots_only)
    monkeypatch.setattr(orch, "run_chain", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("full chain called")))

    result = orch.run_pending_portfolio_recalc(session_factory)
    assert result["status"] == "completed"
    assert recalc_state.get_work(db_session) is None


def test_failed_snapshot_work_remains_visible_and_retryable(db_session, monkeypatch):
    recalc_state.mark_dirty(
        db_session,
        recalc_from=date(2026, 5, 14),
        recalc_to=date(2026, 5, 15),
        touched_symbols={"2330"},
        mode="snapshots",
    )
    db_session.commit()

    @contextmanager
    def session_factory():
        yield db_session

    outcomes = iter((
        orch.StepResult("networth_snapshot_replay", "failed", error="write failed"),
        orch.StepResult("networth_snapshot_replay", "ok"),
    ))
    monkeypatch.setattr(orch, "_step_snapshot_replay", lambda *_args: next(outcomes))

    assert orch.run_pending_portfolio_recalc(session_factory)["status"] == "failed"
    status = recalc_state.status_response(db_session)
    assert status["state"] == "failed"
    assert status["steps"][0]["error"] == "write failed"

    assert orch.run_pending_portfolio_recalc(session_factory)["status"] == "failed"
    assert recalc_state.retry_work(db_session) is not None
    assert orch.run_pending_portfolio_recalc(session_factory)["status"] == "completed"
    assert recalc_state.get_work(db_session) is None
