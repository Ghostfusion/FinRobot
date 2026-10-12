"""Run-scoped as-of clock — the lookahead guard for point-in-time reads.

A replay/backtest must never let a dated read observe anything after the run's
as-of instant: a 2020-06-01 replay that reads a price stamped 2020-09-30 is
lookahead bias, and it stays invisible unless every clamp funnels through ONE
clock. This module is that clock. It is a ``contextvars.ContextVar`` rather than
a module global on purpose: pipeline steps run inside separate ``asyncio`` tasks
/ threads, and a global would leak one step's as-of into a concurrent sibling's
reads (two tickers replayed to different dates would cross-contaminate). A
``ContextVar`` hands each task its own copy; ``set``/``clear`` inside a task
never touch the parent, and the parent never touches a task.

INVARIANT (load-bearing): **unset ⇒ every clamp is a no-op.** :func:`as_of`
returns its argument unchanged, so live calls and every existing test are
bit-identical to the pre-PIT behavior; only a run that explicitly calls
:func:`set_run_as_of` opts into clamping, and then no dated read can observe an
instant after the run's as-of. That asymmetry is what lets this land without
changing any existing call site's semantics.

Vocabulary: this mirrors ``Provenance.as_of`` — the *semantic* instant a datum
belongs to (latest bar / fiscal period end), not the wall-clock ``fetched_at``.
The run's as-of is an upper bound on that semantic instant, never on the fetch
time.
"""

from __future__ import annotations

import contextvars
from datetime import date, datetime, time, timezone

__all__ = [
    "as_of",
    "as_of_window",
    "clear_run_as_of",
    "current_run_as_of",
    "set_run_as_of",
]

#: Per-task/thread as-of ceiling. ``None`` (the default) means "unset — clamp is
#: a no-op". A ContextVar copy survives into ``asyncio`` tasks, so a run can set
#: it once and every step it spawns inherits the same bound without a global.
_RUN_AS_OF: contextvars.ContextVar[datetime | None] = contextvars.ContextVar(
    "finrobot_run_as_of", default=None
)


def _ensure_tz(dt: datetime) -> datetime:
    """Treat naive datetimes as UTC — the repo's ``_ensure_tz`` convention.

    JSON round-tripped timestamps may drop their tzinfo; a naive value compared
    against a UTC-aware ceiling raises ``TypeError``. Normalizing here is what
    keeps :func:`as_of` from ever crashing on naive-vs-aware.
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _to_utc(value: datetime | date | None) -> datetime | None:
    """A run as-of as UTC-aware. A bare ``date`` is its calendar boundary
    (UTC midnight), matching the accounting-period convention.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return _ensure_tz(value)
    return datetime.combine(value, time.min, tzinfo=timezone.utc)


def set_run_as_of(value: datetime | date | None) -> None:
    """Set this task's as-of ceiling (``None`` clears it).

    Affects only the current context: a sibling task created before this call, or
    running after it, keeps its own value.
    """
    _RUN_AS_OF.set(_to_utc(value))


def clear_run_as_of() -> None:
    """Return this task to the unset state — every clamp becomes a no-op again."""
    _RUN_AS_OF.set(None)


def current_run_as_of() -> datetime | None:
    """This task's as-of ceiling, or ``None`` when unset (live behavior)."""
    return _RUN_AS_OF.get()


def as_of(when: datetime) -> datetime:
    """Clamp ``when`` to the run's as-of: ``min(when, ceiling)`` when set.

    Unset ⇒ ``when`` is returned unchanged (the same object for an aware input),
    so pristine live behavior. Never inverts (``min`` is monotone non-decreasing)
    and never crashes on a naive ``when`` (normalized to UTC first).
    """
    moment = _ensure_tz(when)
    ceiling = _RUN_AS_OF.get()
    if ceiling is None:
        return moment
    return min(moment, ceiling)


def as_of_window(start: datetime, end: datetime) -> tuple[datetime, datetime]:
    """Clamp BOTH ends of ``[start, end]`` and refuse an inverted result.

    A window that is still ``start > end`` after clamping is a caller bug, not an
    empty window: swapping the ends would silently turn a lookahead mistake into a
    plausible-looking range, so it raises ``ValueError`` instead. Equal ends are a
    legitimate empty window and pass through.
    """
    low = as_of(start)
    high = as_of(end)
    if high < low:
        raise ValueError(
            "as-of window inverted after clamping: "
            f"start={low.isoformat()} > end={high.isoformat()}"
        )
    return low, high
