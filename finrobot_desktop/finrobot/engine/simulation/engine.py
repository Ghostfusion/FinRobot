"""Discrete-event continuous-double-auction engine (§2.1) plus the ZI null arm (§5.7).

The engine drives a market from asynchronous agent decisions rather than fixed
time steps, so event timing, latency and price-time matching are explicit and
testable. Two event types (§2.1): a *consideration* event schedules the next
look by agent i at ``t + Exp(C_i)``; an *add-order* event inserts an order and
runs the matcher. Latency is the memoryless-equivalent "delay the send" trick —
the agent decides from the book as of ``t`` but the order enters at ``t + lambda``
— which avoids storing historical books.

The event queue is a binary min-heap: ``O(log n)`` insert and an ``O(1)`` next
look (a bare index into the heap root), asserted on operation counts rather than
wall time. Memory is ``O(n_agents)`` resting orders because each agent cancels
its previous order when it sends the next one.

Everything is derived from a single seed, so ``run_simulation(config, seed)`` is
byte-for-byte reproducible. Pure NumPy; no SciPy/torch/gymnasium.
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass
from typing import Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, model_validator

from finrobot.engine.simulation.agents import AgentKind, Side, ZeroIntelligenceAgent

__all__ = [
    "AgentState",
    "Event",
    "EventQueue",
    "Order",
    "SimulationConfig",
    "SimulationResult",
    "Trade",
    "run_simulation",
]


@dataclass(order=False)
class Event:
    """One scheduled event; ``time`` and the heap's unique sequence break ties."""

    time: float
    kind: Literal["consider", "add_order"]
    agent_id: int
    side: Side | None = None
    price: float = 0.0
    size: int = 0
    decided_at: float = 0.0


class EventQueue:
    """Binary min-heap event queue with operation counters for the complexity test.

    ``push`` performs exactly one heap operation (``O(log n)``). ``peek`` reads
    the heap root in ``O(1)`` and never mutates the heap; ``pop`` performs exactly
    one heap operation. The counters let a test assert the complexity on
    *operation counts* — no wall-clock timing, which is flaky.
    """

    def __init__(self) -> None:
        self._heap: list[tuple[float, int, Event]] = []
        self._sequence = 0
        self.push_operations = 0
        self.pop_operations = 0
        self.peek_operations = 0

    def __len__(self) -> int:
        return len(self._heap)

    def push(self, event: Event) -> None:
        """Insert ``event``; one heap operation, ``O(log n)``."""
        heapq.heappush(self._heap, (event.time, self._sequence, event))
        self._sequence += 1
        self.push_operations += 1

    def peek(self) -> Event:
        """Return the earliest event without removing it; ``O(1)``, no heap op."""
        if not self._heap:
            raise IndexError("peek from an empty event queue")
        self.peek_operations += 1
        return self._heap[0][2]

    def pop(self) -> Event:
        """Remove and return the earliest event; one heap operation, ``O(log n)``."""
        if not self._heap:
            raise IndexError("pop from an empty event queue")
        event = heapq.heappop(self._heap)[2]
        self.pop_operations += 1
        return event


class SimulationConfig(BaseModel):
    """Engine/agent parameters; the defaults are a homogeneous ZI fundamental market."""

    model_config = ConfigDict(frozen=True)

    n_agents: int = Field(default=20, ge=1, description="Number of agents")
    n_events: int = Field(default=4000, ge=1, description="Total events to process")
    initial_price: float = Field(default=100.0, gt=0.0, description="Opening mid price")
    fundamental_mean: float = Field(
        default=100.0, gt=0.0, description="Fundamental reversion level"
    )
    fundamental_kappa: float = Field(default=0.1, gt=0.0, le=1.0, description="Reversion speed")
    fundamental_sigma: float = Field(default=0.2, ge=0.0, description="Fundamental shock std")
    n_fundamental_steps: int = Field(
        default=500, ge=2, description="Precomputed fundamental length"
    )
    fundamental_dt: float = Field(default=2.0, gt=0.0, description="Fundamental grid spacing")
    consideration_rate: float = Field(default=1.0, gt=0.0, description="Per-agent look rate C_i")
    latency: float = Field(default=0.0, ge=0.0, description="Trader-to-exchange latency lambda")
    price_noise: float = Field(default=0.002, ge=0.0, description="Relative limit-price noise")
    order_size: int = Field(default=10, ge=1, description="Units per order")
    tick_size: float = Field(default=0.0, ge=0.0, description="Price grid; 0 disables rounding")
    agent_kinds: list[AgentKind] = Field(
        default_factory=lambda: [AgentKind.FUNDAMENTAL],
        description="Cycled agent kinds across the population",
    )

    @model_validator(mode="after")
    def _require_agent_kinds(self) -> SimulationConfig:
        if not self.agent_kinds:
            raise ValueError("agent_kinds must be non-empty")
        return self


class Order(BaseModel):
    """A limit order the engine accepted, kept for the exposed order flow."""

    model_config = ConfigDict(frozen=True)

    order_id: int
    agent_id: int
    side: Side
    price: float
    size: int
    event_time: float
    decided_at: float


class Trade(BaseModel):
    """A settled match between a resting and an incoming order."""

    model_config = ConfigDict(frozen=True)

    trade_id: int
    price: float
    size: int
    event_time: float
    buy_agent: int
    sell_agent: int


class AgentState(BaseModel):
    """Per-agent end state, exposed so a test can check cash/inventory conservation."""

    model_config = ConfigDict(frozen=True)

    agent_id: int
    kind: AgentKind
    cash: float
    inventory: int
    orders_sent: int


class SimulationResult(BaseModel):
    """Everything a caller needs from one run: prices, flow and end states."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    mid_prices: np.ndarray = Field(description="Generated mid-price series, one per add-order")
    fundamental_values: np.ndarray = Field(description="Injected fundamental at each mid sample")
    order_flow: list[Order] = Field(description="Orders accepted by the engine")
    trades: list[Trade] = Field(description="Settled matches")
    agent_states: list[AgentState] = Field(description="End-of-run cash and inventory")
    config: SimulationConfig
    seed: int


class _FundamentalProcess:
    """Precomputed discrete mean-reverting fundamental (§2.3, discrete variant).

    The OU form is preferred when agents arrive rarely, but it cannot be sampled
    independently at many query times without breaking path consistency — two
    agents waking at the same ``t`` must see the same value. So the fundamental
    is drawn once on a fixed grid and stepped (not interpolated): deterministic,
    shared, and ``O(1)`` per lookup.
    """

    def __init__(
        self,
        mean: float,
        kappa: float,
        sigma: float,
        n_steps: int,
        dt: float,
        rng: np.random.Generator,
    ) -> None:
        values = np.empty(n_steps, dtype=np.float64)
        previous = mean
        for i in range(n_steps):
            shock = float(rng.normal(0.0, sigma))
            current = max(0.0, kappa * mean + (1.0 - kappa) * previous + shock)
            values[i] = current
            previous = current
        self._values = values
        self._dt = dt

    def value_at(self, t: float) -> float:
        """Fundamental value for time ``t`` (piecewise constant on the grid)."""
        index = int(t / self._dt)
        index = min(max(index, 0), self._values.size - 1)
        return float(self._values[index])


@dataclass
class _Resting:
    """A live order sitting in a book side."""

    order_id: int
    agent_id: int
    side: Side
    price: float
    remaining: int
    sequence: int


class _OrderBook:
    """Single-asset price-time-priority continuous double auction (§2.1).

    Bids are a max-heap (negated price) and asks a min-heap; the unique
    ``sequence`` gives time priority and, because it never ties, keeps heap
    comparisons from touching the payload. Cancelled/filled orders are removed
    lazily when they reach a heap root, so each heap operation stays ``O(log n)``.
    """

    def __init__(self, tick_size: float) -> None:
        self._bids: list[tuple[float, int, int]] = []  # (-price, sequence, order_id)
        self._asks: list[tuple[float, int, int]] = []  # (price, sequence, order_id)
        self._orders: dict[int, _Resting] = {}
        self._sequence = 0
        self._trade_sequence = 0
        self._tick_size = tick_size
        self.last_price = 0.0

    def _round_price(self, price: float) -> float:
        if self._tick_size <= 0.0:
            return price
        return round(price / self._tick_size) * self._tick_size

    def _prune(self, side: Side) -> None:
        heap = self._bids if side == "buy" else self._asks
        while heap:
            order_id = heap[0][2]
            resting = self._orders.get(order_id)
            if resting is None or resting.remaining <= 0:
                heapq.heappop(heap)
                continue
            break

    def cancel(self, order_id: int) -> None:
        """Mark ``order_id`` dead; it is dropped lazily on reaching a heap root."""
        self._orders.pop(order_id, None)

    def add(
        self,
        agent_id: int,
        side: Side,
        price: float,
        size: int,
        order_id: int,
        event_time: float,
    ) -> list[Trade]:
        """Insert an order then run the matcher; returns the trades it produced."""
        resting = _Resting(
            order_id=order_id,
            agent_id=agent_id,
            side=side,
            price=self._round_price(price),
            remaining=size,
            sequence=self._sequence,
        )
        self._sequence += 1
        self._orders[order_id] = resting
        self._push(resting)
        return self._match(event_time)

    def _push(self, resting: _Resting) -> None:
        if resting.side == "buy":
            heapq.heappush(self._bids, (-resting.price, resting.sequence, resting.order_id))
        else:
            heapq.heappush(self._asks, (resting.price, resting.sequence, resting.order_id))

    def _best(self, side: Side) -> _Resting | None:
        self._prune(side)
        heap = self._bids if side == "buy" else self._asks
        if not heap:
            return None
        return self._orders[heap[0][2]]

    def _match(self, event_time: float) -> list[Trade]:
        trades: list[Trade] = []
        while True:
            best_bid = self._best("buy")
            best_ask = self._best("sell")
            if best_bid is None or best_ask is None:
                break
            if best_bid.price < best_ask.price:
                break
            # Price-time priority: the older resting order sets the price.
            if best_bid.sequence < best_ask.sequence:
                trade_price = best_bid.price
            else:
                trade_price = best_ask.price
            quantity = min(best_bid.remaining, best_ask.remaining)
            best_bid.remaining -= quantity
            best_ask.remaining -= quantity
            self.last_price = trade_price
            trades.append(
                Trade(
                    trade_id=self._trade_sequence,
                    price=trade_price,
                    size=quantity,
                    event_time=event_time,
                    buy_agent=best_bid.agent_id,
                    sell_agent=best_ask.agent_id,
                )
            )
            self._trade_sequence += 1
        return trades

    def mid(self) -> float:
        """Mid of the best bid/ask, or the last trade price when a side is empty."""
        best_bid = self._best("buy")
        best_ask = self._best("sell")
        if best_bid is not None and best_ask is not None:
            return 0.5 * (best_bid.price + best_ask.price)
        if self.last_price > 0.0:
            return self.last_price
        if best_bid is not None:
            return best_bid.price
        if best_ask is not None:
            return best_ask.price
        return 0.0


def _agent_rng(master: np.random.Generator) -> np.random.Generator:
    """Spawn a per-agent stream from the master stream, deterministically."""
    child_seed = int(master.integers(0, 2**63 - 1))
    return np.random.default_rng(child_seed)


def run_simulation(config: SimulationConfig, seed: int) -> SimulationResult:
    """Run the ZI engine for ``config.n_events`` events; fully seed-deterministic.

    Returns the generated mid-price series, the injected fundamental aligned to
    it, the accepted order flow, the settled trades, and each agent's end cash
    and inventory. Identical ``seed`` values produce identical series.
    """
    master = np.random.default_rng(seed)
    fundamental = _FundamentalProcess(
        config.fundamental_mean,
        config.fundamental_kappa,
        config.fundamental_sigma,
        config.n_fundamental_steps,
        config.fundamental_dt,
        rng=_agent_rng(master),
    )
    agents = [
        ZeroIntelligenceAgent(
            agent_id=i,
            kind=config.agent_kinds[i % len(config.agent_kinds)],
            consideration_rate=config.consideration_rate,
            price_noise=config.price_noise,
            order_size=config.order_size,
            rng=_agent_rng(master),
        )
        for i in range(config.n_agents)
    ]

    queue = EventQueue()
    book = _OrderBook(config.tick_size)
    book.last_price = config.initial_price
    for agent in agents:
        queue.push(Event(agent.next_consideration_time(0.0), "consider", agent.agent_id))

    cash = [0.0 for _ in agents]
    inventory = [0 for _ in agents]
    orders_sent = [0 for _ in agents]
    order_flow: list[Order] = []
    trades: list[Trade] = []
    mid_prices: list[float] = []
    fundamental_values: list[float] = []
    order_sequence = 0
    processed = 0

    while processed < config.n_events and len(queue) > 0:
        event = queue.pop()
        processed += 1
        agent = agents[event.agent_id]
        if event.kind == "consider":
            side, price, size = agent.decide(book.mid(), fundamental.value_at(event.time))
            queue.push(
                Event(
                    time=event.time + config.latency,
                    kind="add_order",
                    agent_id=agent.agent_id,
                    side=side,
                    price=price,
                    size=size,
                    decided_at=event.time,
                )
            )
            queue.push(Event(agent.next_consideration_time(event.time), "consider", agent.agent_id))
            continue

        # add_order: cancel the agent's previous resting order, then send this one.
        if agent.outstanding_order_id is not None:
            book.cancel(agent.outstanding_order_id)
        order_sequence += 1
        assert event.side is not None
        order_flow.append(
            Order(
                order_id=order_sequence,
                agent_id=agent.agent_id,
                side=event.side,
                price=event.price,
                size=event.size,
                event_time=event.time,
                decided_at=event.decided_at,
            )
        )
        agent.outstanding_order_id = order_sequence
        orders_sent[agent.agent_id] += 1
        for trade in book.add(
            agent.agent_id, event.side, event.price, event.size, order_sequence, event.time
        ):
            trades.append(trade)
            if trade.buy_agent == trade.sell_agent:
                continue
            cash[trade.buy_agent] -= trade.price * trade.size
            inventory[trade.buy_agent] += trade.size
            cash[trade.sell_agent] += trade.price * trade.size
            inventory[trade.sell_agent] -= trade.size
        mid_prices.append(book.mid())
        fundamental_values.append(fundamental.value_at(event.time))

    states = [
        AgentState(
            agent_id=agent.agent_id,
            kind=agent.kind,
            cash=cash[agent.agent_id],
            inventory=inventory[agent.agent_id],
            orders_sent=orders_sent[agent.agent_id],
        )
        for agent in agents
    ]
    return SimulationResult(
        mid_prices=np.asarray(mid_prices, dtype=np.float64),
        fundamental_values=np.asarray(fundamental_values, dtype=np.float64),
        order_flow=order_flow,
        trades=trades,
        agent_states=states,
        config=config,
        seed=seed,
    )
