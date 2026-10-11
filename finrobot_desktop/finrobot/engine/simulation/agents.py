"""Zero-intelligence agent set — the §5.7 permanent null arm.

The engine's mechanics are only informative relative to a market that contains
no intelligence at all (§4, "Report the null"). The cheapest such market is the
2312.14903-style minimal set of §2.4: liquidity takers pick a side at random and
liquidity providers quote a random lognormal-shifted price around the prevailing
mid. Both flavours are *zero-intelligence* — no learning, no memory, no
adaptation — so any claim the model reproduces a stylized fact is measured
against this arm on the same moments.

One flavour, ``FUNDAMENTAL``, anchors its random limit price on the injected
fundamental process instead of the mid. A market of only these agents is the
"homogeneous fundamentalist" configuration of §2.1/§5.1: it is still random
(side and offset are drawn), but its centre is the fundamental, which is what
makes the tracking acceptance test meaningful.
"""

from __future__ import annotations

import math
from enum import Enum
from typing import Literal

import numpy as np

__all__ = ["AgentKind", "Side", "ZeroIntelligenceAgent"]

Side = Literal["buy", "sell"]


class AgentKind(str, Enum):
    """Which zero-intelligence rule an agent follows."""

    #: Quotes a random limit price around the injected fundamental value.
    FUNDAMENTAL = "fundamental"
    #: Quotes a random limit price around the prevailing mid.
    NOISE = "noise"


class ZeroIntelligenceAgent:
    """A rule-based agent with no state beyond its outstanding order.

    The consideration process is memoryless: the agent's next look is drawn
    ``Exp(C_i)`` ahead (mean ``1 / C_i``), matching §2.1. Each look produces one
    randomly-drawn limit order; the engine applies the agent's latency by
    delaying *when that order is sent* (§2.1 "delay the send"), which keeps the
    engine from storing historical books.
    """

    def __init__(
        self,
        agent_id: int,
        kind: AgentKind,
        consideration_rate: float,
        price_noise: float,
        order_size: int,
        rng: np.random.Generator,
    ) -> None:
        if consideration_rate <= 0.0:
            raise ValueError(f"consideration_rate must be > 0, got {consideration_rate}")
        if price_noise < 0.0:
            raise ValueError(f"price_noise must be >= 0, got {price_noise}")
        if order_size < 1:
            raise ValueError(f"order_size must be >= 1, got {order_size}")
        self.agent_id = agent_id
        self.kind = kind
        self.consideration_rate = consideration_rate
        self.price_noise = price_noise
        self.order_size = order_size
        self.rng = rng
        #: The one order the agent currently has resting; cancelled on the next
        #: send. Bounded book size keeps the engine O(n) in memory.
        self.outstanding_order_id: int | None = None

    def next_consideration_time(self, now: float) -> float:
        """Schedule the next look ``Exp(rate)`` ahead of ``now`` (memoryless)."""
        u = float(self.rng.random())
        u = min(max(u, 1e-12), 1.0 - 1e-12)
        return now + (-math.log(1.0 - u) / self.consideration_rate)

    def decide(self, mid: float, fundamental: float) -> tuple[Side, float, int]:
        """Draw a random limit order: side, price, size.

        Price is a lognormal-style shift of the anchor — ``fundamental`` for a
        ``FUNDAMENTAL`` agent, the prevailing ``mid`` otherwise — per §2.4's
        zero-intelligence liquidity-provider rule. Side is a fair coin, so the
        arm has no directional edge.
        """
        anchor = fundamental if self.kind is AgentKind.FUNDAMENTAL else mid
        if anchor <= 0.0:
            anchor = max(mid, 1e-9)
        offset = float(self.rng.normal(0.0, self.price_noise))
        price = anchor * (1.0 + offset)
        if price <= 0.0:
            price = anchor * 0.5
        side: Side = "buy" if float(self.rng.random()) < 0.5 else "sell"
        return side, price, self.order_size
