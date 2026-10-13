"""``coverage.batch`` — the re-run-all selection predicate + the queued runner.

The runner's outside boundaries (``spawn``, ``run_status``) are injected, so the
whole queue is exercised without HTTP, a run store, or a real pipeline. The
headline test proves the queue: at ``limit=2`` no more than two runs are ever in
flight, and every selected ticker still reaches a terminal state.
"""

from __future__ import annotations

import asyncio

import pytest

from finrobot.coverage.batch import CoverageBatch, select_targets
from finrobot.coverage.models import CoverageRow
from finrobot.run_concurrency import RunConcurrencyPlan


def _plan(limit: int, *, ceiling: int = 4) -> RunConcurrencyPlan:
    return RunConcurrencyPlan(
        limit=limit,
        ceiling=ceiling,
        binding_provider=None,
        binding_reason="test plan",
        providers=[],
        undeclared_count=0,
    )


async def _wait_until(predicate, timeout: float = 5.0) -> None:
    """Spin the loop until ``predicate()`` is true, or fail after ``timeout``."""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while not predicate():
        assert loop.time() < deadline, "condition not met before timeout"
        await asyncio.sleep(0)


# ── select_targets ───────────────────────────────────────────────────────────


def _row(ticker: str, *, owned: bool = False, verdict: str | None = None) -> CoverageRow:
    return CoverageRow(ticker=ticker, owned=owned, latest_verdict=verdict)


def test_select_targets_no_filters_keeps_all_in_order() -> None:
    rows = [_row("AAPL"), _row("MSFT", verdict="BUY"), _row("TSLA", owned=True)]
    assert select_targets(rows, owned=None, ratings=None) == ["AAPL", "MSFT", "TSLA"]


def test_select_targets_owned_true_and_false() -> None:
    rows = [_row("AAPL", owned=True), _row("MSFT", owned=False), _row("TSLA", owned=True)]
    assert select_targets(rows, owned=True, ratings=None) == ["AAPL", "TSLA"]
    assert select_targets(rows, owned=False, ratings=None) == ["MSFT"]


def test_select_targets_rating_filter_and_unrated() -> None:
    rows = [
        _row("AAPL", verdict="BUY"),
        _row("MSFT", verdict="HOLD"),
        _row("TSLA", verdict=None),  # no verdict → UNRATED
    ]
    assert select_targets(rows, owned=None, ratings=["BUY"]) == ["AAPL"]
    assert select_targets(rows, owned=None, ratings=["BUY", "HOLD"]) == ["AAPL", "MSFT"]
    # The UI's UNRATED token selects exactly the rows with no verdict yet.
    assert select_targets(rows, owned=None, ratings=["UNRATED"]) == ["TSLA"]


def test_select_targets_empty_ratings_is_no_filter() -> None:
    rows = [_row("AAPL", verdict="BUY"), _row("MSFT", verdict="SELL")]
    assert select_targets(rows, owned=None, ratings=[]) == ["AAPL", "MSFT"]


def test_select_targets_combines_owned_and_rating() -> None:
    rows = [
        _row("AAPL", owned=True, verdict="BUY"),
        _row("MSFT", owned=True, verdict="HOLD"),
        _row("TSLA", owned=False, verdict="BUY"),
    ]
    assert select_targets(rows, owned=True, ratings=["BUY"]) == ["AAPL"]


# ── CoverageBatch: the queue ─────────────────────────────────────────────────


async def test_batch_never_exceeds_limit_and_drains_the_queue() -> None:
    """The queue proof: limit=2, 5 tickers → at most 2 runs in flight at once,
    every ticker still reaches a terminal state, and the batch ends completed."""
    tickers = ["A", "B", "C", "D", "E"]
    release: dict[str, asyncio.Event] = {t: asyncio.Event() for t in tickers}
    active: set[str] = set()
    started: list[str] = []
    max_in_flight = 0

    async def spawn(ticker: str) -> str:
        nonlocal max_in_flight
        active.add(ticker)
        started.append(ticker)
        max_in_flight = max(max_in_flight, len(active))
        return f"run_{ticker}"

    async def run_status(run_id: str) -> str | None:
        ticker = run_id.removeprefix("run_")
        if release[ticker].is_set():
            active.discard(ticker)
            return "completed"
        return "running"

    batch = CoverageBatch(
        batch_id="cb_test",
        group_id="cov_test",
        pipeline_type="research",
        tickers=tickers,
        plan=_plan(2),
        spawn=spawn,
        run_status=run_status,
        poll_interval_s=0.001,
    )
    task = asyncio.create_task(batch.run())

    # Exactly two start; the other three stay queued behind the semaphore.
    await _wait_until(lambda: len(started) == 2)
    await asyncio.sleep(0.05)  # give a would-be third spawn a chance to fire
    assert started == ["A", "B"]
    assert max_in_flight == 2
    assert batch.progress().queued == 3
    assert batch.progress().running == 2
    assert batch.progress().state == "running"

    # Free the slots one at a time; each release lets exactly one more start.
    release["A"].set()
    await _wait_until(lambda: len(started) == 3)
    release["B"].set()
    await _wait_until(lambda: len(started) == 4)
    release["C"].set()
    await _wait_until(lambda: len(started) == 5)
    release["D"].set()
    release["E"].set()

    await asyncio.wait_for(task, timeout=5.0)

    assert max_in_flight == 2  # NEVER more than the limit, across the whole run
    assert sorted(started) == tickers
    prog = batch.progress()
    assert prog.state == "completed"
    assert prog.limit == 2
    assert prog.total == 5
    assert prog.completed == 5
    assert prog.failed == 0
    assert prog.queued == 0 and prog.running == 0
    assert all(item.state == "completed" for item in prog.items)


async def test_batch_spawn_failure_fails_only_its_own_item() -> None:
    """A raising spawn marks only that item failed; the queue keeps going."""
    completed_runs: list[str] = []

    async def spawn(ticker: str) -> str:
        if ticker == "BAD":
            raise ValueError("spawn explosion")
        return f"run_{ticker}"

    async def run_status(run_id: str) -> str | None:
        completed_runs.append(run_id)
        return "completed"

    batch = CoverageBatch(
        batch_id="cb_fail",
        group_id="cov_test",
        pipeline_type="research",
        tickers=["AAPL", "BAD", "MSFT"],
        plan=_plan(4),
        spawn=spawn,
        run_status=run_status,
        poll_interval_s=0.001,
    )
    await asyncio.wait_for(batch.run(), timeout=5.0)

    prog = batch.progress()
    by_ticker = {item.ticker: item for item in prog.items}
    assert prog.state == "completed"
    assert prog.failed == 1
    assert prog.completed == 2
    assert by_ticker["BAD"].state == "failed"
    assert by_ticker["BAD"].error == "spawn explosion"
    assert by_ticker["BAD"].run_id is None
    assert by_ticker["AAPL"].state == "completed"
    assert by_ticker["MSFT"].state == "completed"
    # The failed item never reached a run, so run_status was never polled for it.
    assert sorted(completed_runs) == ["run_AAPL", "run_MSFT"]


async def test_batch_empty_selection_completes_immediately() -> None:
    batch = CoverageBatch(
        batch_id="cb_empty",
        group_id="cov_test",
        pipeline_type="research",
        tickers=[],
        plan=_plan(2),
        spawn=lambda ticker: _never(ticker),
        run_status=lambda run_id: _never(run_id),
    )
    await asyncio.wait_for(batch.run(), timeout=1.0)
    prog = batch.progress()
    assert prog.state == "completed"
    assert prog.total == 0
    assert prog.items == []


async def test_batch_non_completed_terminal_marks_item_failed() -> None:
    async def spawn(ticker: str) -> str:
        return f"run_{ticker}"

    async def run_status(run_id: str) -> str | None:
        return "cancelled"

    batch = CoverageBatch(
        batch_id="cb_cancel",
        group_id="cov_test",
        pipeline_type="research",
        tickers=["AAPL"],
        plan=_plan(2),
        spawn=spawn,
        run_status=run_status,
        poll_interval_s=0.001,
    )
    await asyncio.wait_for(batch.run(), timeout=5.0)
    (item,) = batch.progress().items
    assert item.state == "failed"
    assert batch.progress().failed == 1


async def test_start_retains_the_driving_task_and_drains_the_queue() -> None:
    """``start()`` must keep a STRONG reference to the task it creates.

    The event loop holds only a weak reference to a task, so a bare
    ``asyncio.create_task(batch.run())`` can be garbage-collected mid-queue: the
    batch stops dispatching with items stuck at ``queued`` and nothing in any log
    (the same hazard ``app.state.run_tasks`` exists to prevent for runs). Pinning
    both halves — the reference is retained, and the queue still drains to
    ``completed`` when driven by ``start()`` alone.
    """

    async def spawn(ticker: str) -> str:
        return f"run_{ticker}"

    async def run_status(run_id: str) -> str | None:
        return "completed"

    batch = CoverageBatch(
        batch_id="cb_start",
        group_id="cov_test",
        pipeline_type="research",
        tickers=["AAPL", "MSFT"],
        plan=_plan(1),
        spawn=spawn,
        run_status=run_status,
        poll_interval_s=0.001,
    )
    batch.start()
    task = batch._task
    assert task is not None
    await asyncio.wait_for(task, timeout=5.0)
    prog = batch.progress()
    assert prog.state == "completed"
    assert prog.completed == 2
    assert prog.queued == 0


async def _never(value: str) -> str:
    pytest.fail(f"boundary should not be called in the empty-selection case: {value}")
    raise AssertionError  # pragma: no cover - pytest.fail always raises
