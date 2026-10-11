"""Agent-based market simulation — the zero-intelligence null arm.

Why this package exists
-----------------------
``strategies/qfin-tr/agent-based-market-simulation.md`` §5.1, §5.2 and §5.7 ask
for a discrete-event continuous-double-auction engine, a stylized-facts
coverage harness, and a zero-intelligence (ZI) control that every model
comparison is reported against. The engine and the agents are self-contained
code whose only external need is a calibration target, so they live here
instead of behind the data layer.

Why we *build* the engine rather than adopt ABIDES (E1)
------------------------------------------------------
The obvious off-the-shelf choice is ABIDES (and its Gym wrapper
ABIDES-Gym). We do not use either:

* **Python version.** ABIDES pins an older interpreter than this project's
  3.14 venv, so it cannot be installed into the runtime at all.
* **Dependencies.** ABIDES-Gym needs ``gym``/``gymnasium``. Neither is in the
  runtime dependency set, and an architectural test keeps the heavy
  simulation/RL stack (scipy, torch, stable-baselines3, gymnasium) out of the
  runtime — this package is pure NumPy.

The honest downside: ABIDES is battle-tested, scales to many assets and is
used in published work; this is a small null-arm engine that models only
trader↔exchange latency (the "delay the send" trick of §2.1) and a single
price-time-priority book. It is a *calibration baseline*, not a replacement.

Explicitly NOT implemented (out of scope for this package)
----------------------------------------------------------
* The Figgie card-game fixture (the $407.5 cash / $75.43 bonus figures) —
  mentioned in §2.1/§5 only as the source of the discrete-event queue design;
  no card game is modelled here.
* The flash-crash / mini-crash scenario generator of §2.7 — no POV sell
  algorithm, spiking traders, or prominence-based amplitude.
"""

from __future__ import annotations

from finrobot.engine.simulation.agents import ZeroIntelligenceAgent
from finrobot.engine.simulation.engine import (
    EventQueue,
    SimulationConfig,
    SimulationResult,
    run_simulation,
)
from finrobot.engine.simulation.report import ValidationReport, validation_report
from finrobot.engine.simulation.stylized_facts import (
    CoverageMatrix,
    Moment,
    MomentKind,
    block_bootstrap_weights,
    bootstrap_paths,
    coverage_matrix,
    default_moments,
    evaluate_moment,
    hill_tail_index,
    realized_volatility,
    return_autocorr,
    squared_return_autocorr,
)

__all__ = [
    "CoverageMatrix",
    "EventQueue",
    "Moment",
    "MomentKind",
    "SimulationConfig",
    "SimulationResult",
    "ValidationReport",
    "ZeroIntelligenceAgent",
    "block_bootstrap_weights",
    "bootstrap_paths",
    "coverage_matrix",
    "default_moments",
    "evaluate_moment",
    "hill_tail_index",
    "realized_volatility",
    "return_autocorr",
    "run_simulation",
    "squared_return_autocorr",
    "validation_report",
]
