"""Tests for the discrete-event CDA engine and the ZI null arm (§2.1, §5.1).

The complexity acceptance is asserted on OPERATION COUNTS, never wall time: an
insert is exactly one heap operation and the "next" look is a constant-time peek
that does not mutate the heap.
"""

from __future__ import annotations

import numpy as np
import pytest

from finrobot.engine.simulation.engine import (
    Event,
    EventQueue,
    SimulationConfig,
    run_simulation,
)


def _config(**overrides: object) -> SimulationConfig:
    base: dict[str, object] = {"n_agents": 20, "n_events": 1500, "price_noise": 0.002}
    base.update(overrides)
    return SimulationConfig(**base)


class TestEventQueue:
    def test_insert_is_one_heap_operation_per_push(self) -> None:
        queue = EventQueue()
        for i in range(64):
            queue.push(Event(time=float(64 - i), kind="consider", agent_id=i))
        assert queue.push_operations == 64
        assert len(queue) == 64
        assert queue.pop_operations == 0

    def test_next_event_is_constant_time_peek(self) -> None:
        queue = EventQueue()
        for t in (5.0, 1.0, 3.0):
            queue.push(Event(time=t, kind="consider", agent_id=0))
        top = queue.peek()
        assert top.time == 1.0
        assert queue.peek_operations == 1
        assert queue.pop_operations == 0
        assert len(queue) == 3

    def test_pops_in_time_order(self) -> None:
        queue = EventQueue()
        times = [7.0, 2.0, 9.0, 1.0, 5.0]
        for t in times:
            queue.push(Event(time=t, kind="consider", agent_id=0))
        popped = [queue.pop().time for _ in range(len(queue))]
        assert popped == sorted(times)
        assert queue.pop_operations == len(times)

    def test_empty_queue_raises(self) -> None:
        queue = EventQueue()
        with pytest.raises(IndexError):
            queue.peek()
        with pytest.raises(IndexError):
            queue.pop()


class TestDeterminism:
    def test_same_seed_identical_series(self) -> None:
        first = run_simulation(_config(), seed=7)
        second = run_simulation(_config(), seed=7)
        assert np.array_equal(first.mid_prices, second.mid_prices)
        assert np.array_equal(first.fundamental_values, second.fundamental_values)
        assert [o.model_dump() for o in first.order_flow] == [
            o.model_dump() for o in second.order_flow
        ]

    def test_different_seed_differs(self) -> None:
        assert not np.array_equal(
            run_simulation(_config(), seed=1).mid_prices,
            run_simulation(_config(), seed=2).mid_prices,
        )


class TestHomogeneousZeroIntelligence:
    def test_mid_tracks_injected_fundamental_within_tolerance(self) -> None:
        result = run_simulation(_config(), seed=3)
        mid = result.mid_prices
        fundamental = result.fundamental_values
        mask = (mid > 0.0) & (fundamental > 0.0)
        relative_error = np.abs(mid[mask] - fundamental[mask]) / fundamental[mask]
        assert float(relative_error.mean()) < 0.05

    def test_exposes_order_flow_and_conserves_cash(self) -> None:
        result = run_simulation(_config(n_events=1200), seed=4)
        assert len(result.order_flow) > 0
        assert result.mid_prices.size == len(result.order_flow)
        total_cash = sum(state.cash for state in result.agent_states)
        assert abs(total_cash) < 1e-6
        assert sum(state.orders_sent for state in result.agent_states) == len(result.order_flow)
