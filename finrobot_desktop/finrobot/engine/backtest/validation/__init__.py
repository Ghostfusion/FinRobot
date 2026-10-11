"""Backtest validation gate — the statistics that decide if a result is luck.

What this code does that raw LLM cannot: it computes, reproducibly and from
stored inputs, whether a backtest's apparent edge survives selection bias,
multiple testing, regime dependence and cost realism — then emits one verdict
whose display can never contradict its own gates. Every module here is pure
computation over already-computed series; nothing calls a model.

Implements ``strategies/qfin-st/backtest-methodology.md`` (arXiv:2602.00080v1 for
the selection objective, arXiv:2608.23808v2 for the gates and the aggregate,
arXiv:2209.05559v6 for CSCV/PBO and the agent acceptance test, arXiv:2602.00133v1
for cost/settlement realism):

* :mod:`stats` — return-series estimators and the normal quantile functions.
* :mod:`splits` — walk-forward splits with an embargo, and combinatorial purged
  cross-validation.
* :mod:`scores` — GT-Score (a minimized loss) and the generalization ratio.
* :mod:`ledger` — the trial ledger every search-weighted gate depends on.
* :mod:`costs` — the cost sensitivity grid: the same verdict re-priced at
  0/1/2/5/10 bps per side, so a result is a range rather than one frictionless
  number.
* :mod:`overfitting` — PBO/CSCV, deflated Sharpe, MinTRL, SPA block bootstrap,
  regime stability, and the two inference primitives a report needs beside them:
  a Diebold–Mariano comparison of two forecasts and a percentile block-bootstrap
  Sharpe interval.
* :mod:`minerva` — the five-gate blend, its verdict-consistent 0-100 display and
  the fail-closed rules.

**Fail-closed contract.** Missing inputs produce a lower verdict, never a
synthetic pass: no pre-Phi DSR statistic means no display at all (``Phi(u)``
saturates and cannot be inverted); a degenerate CSCV reports itself as
degenerate rather than as an unusually good score; uncallable statistics raise
instead of returning NaN, since every NaN comparison would silently pass.
"""

from __future__ import annotations

from finrobot.engine.backtest.validation.costs import (
    DEFAULT_BPS_GRID,
    CostGridResult,
    CostLevel,
    cost_grid,
)
from finrobot.engine.backtest.validation.ledger import (
    CostModel,
    FoldResult,
    TrialLedger,
    TrialRecord,
    build_ledger_from_search,
)
from finrobot.engine.backtest.validation.minerva import (
    GATE_ORDER,
    WEIGHTS,
    GateMargin,
    GateThresholds,
    MarginCalibration,
    MinervaReport,
    default_calibration,
    equicorrelation_matrix,
    estimate_margin_sigma,
    estimate_sigma_eff,
    evaluate_gates,
    gate_margins,
    minerva_score,
)
from finrobot.engine.backtest.validation.overfitting import (
    AgentAcceptanceResult,
    DMResult,
    DSRResult,
    MinTRLResult,
    PBOResult,
    RegimeResult,
    SPAResult,
    SharpeCIResult,
    agent_acceptance_test,
    deflated_sharpe_ratio,
    diebold_mariano,
    effective_trial_count,
    min_track_record_length,
    pbo_cscv,
    pbo_fold_proxy,
    regime_stability,
    sharpe_confidence_interval,
    spa_test,
)
from finrobot.engine.backtest.validation.scores import (
    INSUFFICIENT_SAMPLE_PENALTY,
    GTScoreResult,
    generalization_ratio,
    gt_score,
    stabilized_period_length,
)
from finrobot.engine.backtest.validation.validate import ValidationConfig, validate_ledger
from finrobot.engine.backtest.validation.splits import (
    CombinatorialPurgedConfig,
    CombinatorialSplit,
    Split,
    WalkForwardConfig,
    combinatorial_purged_splits,
    group_bounds,
    n_backtest_paths,
    walk_forward_splits,
)

__all__ = [
    "DEFAULT_BPS_GRID",
    "GATE_ORDER",
    "INSUFFICIENT_SAMPLE_PENALTY",
    "WEIGHTS",
    "AgentAcceptanceResult",
    "CombinatorialPurgedConfig",
    "CombinatorialSplit",
    "CostGridResult",
    "CostLevel",
    "CostModel",
    "DMResult",
    "DSRResult",
    "FoldResult",
    "GTScoreResult",
    "GateMargin",
    "GateThresholds",
    "MarginCalibration",
    "MinTRLResult",
    "MinervaReport",
    "PBOResult",
    "RegimeResult",
    "SPAResult",
    "SharpeCIResult",
    "Split",
    "TrialLedger",
    "TrialRecord",
    "ValidationConfig",
    "WalkForwardConfig",
    "agent_acceptance_test",
    "build_ledger_from_search",
    "combinatorial_purged_splits",
    "cost_grid",
    "default_calibration",
    "deflated_sharpe_ratio",
    "diebold_mariano",
    "effective_trial_count",
    "equicorrelation_matrix",
    "estimate_margin_sigma",
    "estimate_sigma_eff",
    "evaluate_gates",
    "gate_margins",
    "generalization_ratio",
    "group_bounds",
    "gt_score",
    "min_track_record_length",
    "minerva_score",
    "n_backtest_paths",
    "pbo_cscv",
    "pbo_fold_proxy",
    "regime_stability",
    "sharpe_confidence_interval",
    "spa_test",
    "stabilized_period_length",
    "validate_ledger",
    "walk_forward_splits",
]
