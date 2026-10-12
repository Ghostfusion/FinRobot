"""Unit tests for the run-scoped as-of clock (the lookahead guard).

The load-bearing property is the asymmetry: with the clock *unset* every clamp
must be a no-op (existing behavior is bit-identical), and with it *set* no dated
read may see anything later than the run's as-of. Both halves are asserted here,
plus per-``asyncio``-task isolation — the reason this is a ``ContextVar`` and not
a module global.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from datetime import date, datetime, timezone

import pytest

from finrobot.engine.data.asof import (
    as_of,
    as_of_window,
    clear_run_as_of,
    current_run_as_of,
    set_run_as_of,
)

UTC = timezone.utc
T0 = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
T1 = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)
T2 = datetime(2026, 12, 1, 12, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def _unset_clock() -> Iterator[None]:
    """Each test starts (and ends) with the clock unset, whatever it did."""
    clear_run_as_of()
    yield
    clear_run_as_of()


def test_unset_clock_leaves_an_instant_untouched() -> None:
    """Unset ⇒ no-op: the same object comes back, so live calls are bit-identical."""
    assert as_of(T2) is T2


def test_set_clock_caps_a_future_instant() -> None:
    set_run_as_of(T1)
    assert as_of(T2) == T1


def test_clamp_never_pulls_an_instant_after_the_ceiling() -> None:
    set_run_as_of(T2)
    assert as_of(T0) == T0


def test_naive_input_is_normalised_to_utc_not_crashed() -> None:
    """A naive timestamp must not blow up comparing against an aware ceiling."""
    naive = datetime(2026, 1, 1, 0, 0)
    assert as_of(naive).tzinfo is UTC

    set_run_as_of(T1)
    assert as_of(naive) == datetime(2026, 1, 1, tzinfo=UTC)
    assert as_of(datetime(2027, 1, 1)) == T1


def test_set_accepts_a_bare_date_as_utc_midnight() -> None:
    set_run_as_of(date(2026, 1, 1))
    assert current_run_as_of() == datetime(2026, 1, 1, tzinfo=UTC)


def test_window_clamps_both_ends() -> None:
    set_run_as_of(T1)
    start, end = as_of_window(T0, T2)
    assert start == T0
    assert end == T1


def test_window_with_equal_ends_is_a_legitimate_empty_range() -> None:
    start, end = as_of_window(T1, T1)
    assert start == T1
    assert end == T1


def test_inverted_window_raises_instead_of_silently_swapping() -> None:
    with pytest.raises(ValueError):
        as_of_window(T1, T0)

    # Clamping both ends must not rescue an inverted span by turning it into a
    # plausible-looking one — the raise is the whole point of "clamp totally".
    set_run_as_of(T2)
    with pytest.raises(ValueError):
        as_of_window(T1, T0)


def test_clear_restores_the_unset_noop_state() -> None:
    set_run_as_of(T1)
    assert current_run_as_of() == T1

    clear_run_as_of()
    assert current_run_as_of() is None
    assert as_of(T2) is T2


async def test_set_as_of_is_isolated_per_asyncio_task() -> None:
    """Two concurrent replays must not see each other's as-of (ContextVar copy)."""
    seen: dict[str, datetime | None] = {}

    async def worker(name: str, value: datetime) -> None:
        set_run_as_of(value)
        await asyncio.sleep(0)
        seen[name] = current_run_as_of()

    await asyncio.gather(worker("a", T0), worker("b", T1))

    assert seen["a"] == T0
    assert seen["b"] == T1
    # The parent context was never touched by either child.
    assert current_run_as_of() is None
