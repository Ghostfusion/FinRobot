"""Run the whole validation gate over a persisted optimizer trial ledger.

What this code does that raw LLM cannot: it produces the one verdict the
methodology document's §5 asks for — deflated Sharpe, PBO/CSCV, SPA, MinTRL and
regime stability, combined into a display that cannot contradict its own Seal —
from the ledger alone, deterministically and offline. A model asked to "is this
backtest overfit?" will answer from the equity curve it can see; this scores the
whole search that produced it.

Selection is explicit and conservative: the report scores ``winner_trial_id``
when given, and otherwise the trial with the highest annualized Sharpe — the
best-looking candidate, which is precisely the one the gates exist to be able to
reject. Trials the optimizer discarded are not part of the ledger's story only if
they were never evaluated; every *evaluated* trial must be here, because PBO and
DSR deflation need the whole search, and a ledger that omits the losers will look
better than the search actually was.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from pydantic import BaseModel, Field

from finrobot.engine.backtest.validation.ledger import TrialLedger
from finrobot.engine.backtest.validation.minerva import (
    MarginCalibration,
    MinervaReport,
    evaluate_gates,
)
from finrobot.engine.backtest.validation.overfitting import (
    deflated_sharpe_ratio,
    effective_trial_count,
    min_track_record_length,
    pbo_cscv,
    regime_stability,
    spa_test,
)
from finrobot.engine.backtest.validation.stats import sharpe_ratio

__all__ = ["ValidationConfig", "validate_ledger"]

#: Windows used for the regime diagnostic when a ledger has fewer than two folds,
#: which is the minimum the diagnostic can be computed over at all.
_FALLBACK_REGIME_WINDOWS = 4


class ValidationConfig(BaseModel):
    """Knobs for one gate run. Every value is recorded in the report's provenance."""

    n_blocks: int = Field(
        default=10,
        description="CSCV blocks; even, and n_bars must be at least twice this. Fewer blocks "
        "means fewer combinatorial splits but a longer block, so it tolerates short histories",
    )
    spa_bootstrap: int = Field(default=1000, gt=1, description="SPA bootstrap resamples")
    spa_block_length: int | None = Field(
        default=None, description="Moving-block length; None uses ceil(T^(1/3))"
    )
    seed: int = Field(default=42, description="RNG seed; the run is deterministic given it")
    min_trials_for_agent_acceptance: int = Field(default=50, gt=0)


def validate_ledger(
    ledger: TrialLedger,
    *,
    winner_trial_id: int | None = None,
    benchmark: Sequence[float] | None = None,
    config: ValidationConfig | None = None,
    calibration: MarginCalibration | None = None,
    allow_recompute_pre_phi: bool = True,
) -> MinervaReport:
    """Score a ledger: every gate, then the verdict-consistent aggregate.

    ``benchmark`` is the buy-and-hold (or other reference) per-bar return series
    for the SPA test, aligned with the ledger's bar grid; omitted, SPA tests "no
    trial beats zero", which is weaker and is reported as such in the warnings.

    ``allow_recompute_pre_phi`` decides what happens when the winner's stored
    pre-Phi statistic is missing. The document's rule forbids *reconstructing it
    from the reported DSR value* — ``Phi^-1(0)`` collapses to about -4.75 and
    destroys the ranking — but here the underlying returns are in the ledger, so
    the statistic can be recomputed exactly as it was first computed. That is the
    default and it emits a warning; set it to ``False`` to fail closed instead
    and produce no score at all.
    """
    settings = config or ValidationConfig()
    matrix = ledger.return_matrix()
    n_bars, n_trials = matrix.shape

    if winner_trial_id is None:
        annualized = [
            record.annualized_sharpe if record.annualized_sharpe is not None else -np.inf
            for record in ledger.trials
        ]
        winner = int(np.argmax(annualized))
        winner_record = ledger.trials[winner]
    else:
        matches = [record for record in ledger.trials if record.trial_id == winner_trial_id]
        if not matches:
            raise ValueError(
                f"winner_trial_id {winner_trial_id} is not in the ledger "
                f"(ids: {[record.trial_id for record in ledger.trials]})"
            )
        winner_record = matches[0]
        winner = ledger.trials.index(winner_record)

    winner_returns = matrix[:, winner]
    n_effective = effective_trial_count(matrix)

    warnings: list[str] = []
    recomputed = deflated_sharpe_ratio(
        winner_returns, n_trials=n_effective, periods_per_year=ledger.periods_per_year
    )
    stored_pre_phi = winner_record.pre_phi_dsr
    if stored_pre_phi is None:
        if allow_recompute_pre_phi:
            dsr = recomputed
            warnings.append(
                "the winner had no stored pre-Phi DSR statistic; it was recomputed from the "
                "ledger's returns (exact here, but a record whose returns were purged is "
                "permanently unscorable)"
            )
        else:
            dsr = None
            warnings.append(
                "fail closed: the winner has no stored pre-Phi DSR statistic and recomputation "
                "was disabled"
            )
    else:
        dsr = recomputed
        if recomputed.pre_phi_statistic != stored_pre_phi:
            warnings.append(
                f"the stored pre-Phi statistic ({stored_pre_phi:.6f}) differs from the one "
                f"recomputed here ({recomputed.pre_phi_statistic:.6f}); the stored value is the "
                "one gated on, since it is what the search actually saw"
            )
            dsr = recomputed.model_copy(update={"pre_phi_statistic": stored_pre_phi})

    pbo = pbo_cscv(matrix, n_blocks=settings.n_blocks)
    spa = spa_test(
        matrix,
        benchmark,
        n_bootstrap=settings.spa_bootstrap,
        block_length=settings.spa_block_length,
        seed=settings.seed,
    )
    mintrl = min_track_record_length(winner_returns)

    offsets = ledger.fold_offsets()
    if len(offsets) >= 2:
        edges = [0, *offsets]
        window_sharpes = [
            sharpe_ratio(winner_returns[edges[i] : edges[i + 1]]) for i in range(len(offsets))
        ]
    else:
        window_sharpes = [
            sharpe_ratio(chunk)
            for chunk in np.array_split(winner_returns, _FALLBACK_REGIME_WINDOWS)
            if len(chunk) >= 2
        ]
        warnings.append(
            f"the ledger has one fold, so the regime diagnostic used "
            f"{_FALLBACK_REGIME_WINDOWS} equal windows of the winner's returns instead"
        )
    regime = regime_stability(window_sharpes)

    report = evaluate_gates(
        dsr=dsr,
        pbo=pbo,
        spa=spa,
        mintrl=mintrl,
        regime=regime,
        calibration=calibration,
    )
    provenance = [
        f"winner trial {winner_record.trial_id} of {n_trials} evaluated trials "
        f"({len(ledger.trials)} in the ledger)",
        f"effective independent trials: {n_effective:.2f}",
        f"CSCV blocks: {settings.n_blocks} over {n_bars} bars",
        f"SPA: {settings.spa_bootstrap} resamples, block length {spa.block_length}, "
        f"seed {settings.seed}",
        f"cost model: {ledger.cost_model.version} ({ledger.cost_model.per_side_bps} bps per side)",
    ]
    if pbo.dropped_trials:
        provenance.append(f"dropped {len(pbo.dropped_trials)} zero-variance trials")
    missing = ledger.missing_pre_phi()
    if missing:
        provenance.append(
            f"{len(missing)} of {len(ledger.trials)} trials have no stored pre-Phi statistic "
            f"(ids {missing[:5]}{'...' if len(missing) > 5 else ''})"
        )
    return report.model_copy(update={"warnings": [*warnings, *report.warnings, *provenance]})
