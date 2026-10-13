"""Coverage re-run-all orchestration — bounded fan-out with a real queue.

The Coverage Desk's "re-run all reports" control selects a filtered set of
tickers and re-runs the research pipeline across them. It must not fire N runs
at once: the effective cap is whichever data provider throttles first (see
:mod:`finrobot.run_concurrency`). This module owns that policy in one place:

* :func:`select_targets` — the ONE filter predicate the route and the UI agree
  on (ownership + rating), so "what the cards show" and "what gets re-run" can
  never drift.
* :class:`CoverageBatch` — a bounded fan-out that keeps at most ``plan.limit``
  runs in flight and leaves the rest queued until a slot frees, until all are
  terminal.

Orchestration layer per ADR-0012: it imports the coverage models and the
concurrency policy, never the routes. The two boundaries that touch the outside
world — ``spawn`` (ticker → run_id) and ``run_status`` (run_id → run-store
status) — are injected, so the queue unit-tests without HTTP, a run store, or a
real pipeline.
"""

from __future__ import annotations

import asyncio
import logging
import sqlite3
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import HTTPException
from pydantic import BaseModel

from finrobot.coverage.models import CoverageRow
from finrobot.run_concurrency import ProviderLimitView, RunConcurrencyPlan

logger = logging.getLogger(__name__)

# How often a running item re-checks its run's status. The run is an independent
# task (spawn_run registers it on ``app.state.run_tasks``), so the batch never
# awaits it — it POLLS. Polling rather than awaiting is deliberate: cancelling
# the batch task then only stops the poll loop and leaves the underlying run to
# finish on its own, which is what a user expects when they close the desk
# mid-batch. Runs take minutes, so a sub-second poll is cheap.
_POLL_INTERVAL_S = 0.5

# Terminal run-store statuses (mirrors run_store.TERMINAL_RUN_STATUSES). Kept as
# a local literal so this orchestration module needn't reach into the run store
# for a single constant.
_TERMINAL = frozenset({"completed", "failed", "cancelled"})

# What a spawn call may raise without taking the whole batch down. In production
# ``spawn`` wraps ``routes.runs.spawn_run``, which raises ValueError (bad ticker /
# unknown pipeline) or HTTPException (503 not-ready / 409 lineage mismatch); the
# local run store it writes through can raise sqlite3.Error / OSError /
# RuntimeError. Enumerated rather than a bare ``except Exception`` (the project's
# no-bare-catch rule); CancelledError is excluded so a shutdown propagates.
_SPAWN_FAILURES = (ValueError, RuntimeError, OSError, sqlite3.Error, HTTPException)


def _iso_z() -> str:
    """UTC ISO-8601 timestamp with a ``Z`` suffix (matches the UI contract)."""
    return datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z")


def select_targets(
    rows: list[CoverageRow],
    *,
    owned: bool | None,
    ratings: Sequence[str] | None,
) -> list[str]:
    """The ONE filter predicate the re-run-all route and its UI agree on.

    ``owned=None`` applies no ownership filter; ``True`` keeps only owned names;
    ``False`` keeps only not-owned. ``ratings=None`` (or empty) applies no rating
    filter; otherwise a row is kept when its
    ``(latest_verdict or "UNRATED").upper()`` is in the set — so the UI's
    ``UNRATED`` token selects exactly the rows that carry no verdict yet, and a
    ``BUY``/``HOLD``/``SELL`` token matches the uppercase verdicts the artifact
    store records. Input order is preserved so the queue drains predictably.
    """
    rating_set = {r.strip().upper() for r in ratings} if ratings else None
    selected: list[str] = []
    for row in rows:
        if owned is not None and row.owned != owned:
            continue
        if rating_set is not None:
            token = (row.latest_verdict or "UNRATED").upper()
            if token not in rating_set:
                continue
        selected.append(row.ticker)
    return selected


class CoverageBatchItemProgress(BaseModel):
    """One ticker's position in the batch — what the UI renders per row."""

    ticker: str
    state: str
    """``queued`` | ``running`` | ``completed`` | ``failed``."""
    run_id: str | None = None
    error: str | None = None


class CoverageBatchProgress(BaseModel):
    """A batch's live progress plus the plan that produced its concurrency cap.

    Carries the resolved plan (``limit``/``ceiling``/``binding_provider``/
    ``binding_reason``/``providers``/``undeclared_count``) so the UI can show
    which provider set the cap and why, not just a bare number.
    """

    batch_id: str
    group_id: str
    pipeline_type: str
    state: str
    """``queued`` | ``running`` | ``completed``."""
    limit: int
    ceiling: int
    binding_provider: str | None
    binding_reason: str
    providers: list[ProviderLimitView]
    undeclared_count: int
    total: int
    queued: int
    running: int
    completed: int
    failed: int
    items: list[CoverageBatchItemProgress]
    created_at: str


@dataclass
class _BatchItem:
    """Mutable per-ticker state; the batch mutates it as the queue drains."""

    ticker: str
    state: str = "queued"
    run_id: str | None = None
    error: str | None = None


class CoverageBatch:
    """A bounded fan-out of pipeline runs with a real FIFO queue.

    At most ``plan.limit`` runs are in flight at once; every other selected
    ticker stays ``queued`` and starts only when a slot frees, until all are
    terminal. ``spawn`` (ticker → run_id) and ``run_status`` (run_id → run-store
    status) are injected boundaries so the whole queue is unit-testable without
    HTTP or a real run store.
    """

    def __init__(
        self,
        *,
        batch_id: str,
        group_id: str,
        pipeline_type: str,
        tickers: list[str],
        plan: RunConcurrencyPlan,
        spawn: Callable[[str], Awaitable[str]],
        run_status: Callable[[str], Awaitable[str | None]],
        poll_interval_s: float = _POLL_INTERVAL_S,
    ) -> None:
        self.batch_id = batch_id
        self.group_id = group_id
        self.pipeline_type = pipeline_type
        self._plan = plan
        self._spawn = spawn
        self._run_status = run_status
        self._poll_interval_s = poll_interval_s
        self._items = [_BatchItem(ticker=t) for t in tickers]
        self._state = "queued"
        self._created_at = _iso_z()
        # Strong reference to the driving task. The event loop keeps only a WEAK
        # reference to a task, so a bare ``asyncio.create_task(batch.run())`` can
        # be garbage-collected mid-queue — the batch would silently stop
        # dispatching with items stuck at ``queued`` and no error anywhere. The
        # registry holding this batch keeps the task alive with it (same reason
        # ``routes/runs.py`` stores every run task in ``app.state.run_tasks``).
        self._task: asyncio.Task[None] | None = None

    def start(self) -> None:
        """Drive the queue in the background, retaining the driving task."""
        self._task = asyncio.create_task(self.run())

    async def run(self) -> None:
        """Drive the queue to completion. Scheduled as a background task.

        One worker per ticker; each holds a slot for the whole run (spawn → poll
        to terminal). The semaphore IS the queue: the first ``limit`` workers
        acquire a slot and spawn, the rest block on ``async with sem`` — still
        ``queued`` — until a running worker releases.
        """
        if not self._items:
            self._state = "completed"
            return
        # ``max(1, ...)`` so a degenerate plan can never deadlock the queue.
        sem = asyncio.Semaphore(max(1, self._plan.limit))
        await asyncio.gather(*(self._worker(item, sem) for item in self._items))
        self._state = "completed"

    async def _worker(self, item: _BatchItem, sem: asyncio.Semaphore) -> None:
        async with sem:
            try:
                run_id = await self._spawn(item.ticker)
            except _SPAWN_FAILURES as exc:
                # A spawn failure is that item's own problem: mark it failed and
                # let the queue carry on (the error text is the caller's).
                item.state = "failed"
                item.error = str(exc)
                return
            item.run_id = run_id
            item.state = "running"
            self._state = "running"
            # Poll until the run is terminal. Never await the run's task — see
            # the module docstring for why polling keeps a batch cancellation
            # from cancelling the run.
            while True:
                status = await self._run_status(run_id)
                if status in _TERMINAL:
                    # ``completed`` is the only success; ``failed``/``cancelled``
                    # both leave the item failed (it did not produce a report).
                    item.state = "completed" if status == "completed" else "failed"
                    return
                await asyncio.sleep(self._poll_interval_s)

    def progress(self) -> CoverageBatchProgress:
        """A consistent snapshot of the batch, safe to read while it runs."""
        counts = {"queued": 0, "running": 0, "completed": 0, "failed": 0}
        for item in self._items:
            counts[item.state] += 1
        return CoverageBatchProgress(
            batch_id=self.batch_id,
            group_id=self.group_id,
            pipeline_type=self.pipeline_type,
            state=self._state,
            limit=self._plan.limit,
            ceiling=self._plan.ceiling,
            binding_provider=self._plan.binding_provider,
            binding_reason=self._plan.binding_reason,
            providers=self._plan.providers,
            undeclared_count=self._plan.undeclared_count,
            total=len(self._items),
            queued=counts["queued"],
            running=counts["running"],
            completed=counts["completed"],
            failed=counts["failed"],
            items=[
                CoverageBatchItemProgress(
                    ticker=i.ticker, state=i.state, run_id=i.run_id, error=i.error
                )
                for i in self._items
            ],
            created_at=self._created_at,
        )
