"""GT-Score and the generalization ratio — selection objectives for §2.1-2.2.

What this code does that raw LLM cannot: it evaluates the composite
overfitting-resistant objective of ``strategies/qfin-st/backtest-methodology.md``
§2.1 (arXiv:2602.00080v1) as a deterministic number, so a parameter search can be
scored identically by any machine — a model asked to "score this strategy" will
produce a different number every time.

**Direction (read before wiring this into a search).** The paper's objective is a
**minimized loss**, not a maximized score, and the code returns it that way —
``GTScoreResult.direction == "minimize"``. Its Algorithm 1 is explicit: the
underperformance branch is a *large positive penalty* (163-200), the marginal
branch transitions down to 0, and the standard branch carries a leading minus
sign (``score <- -mu*ln(z)*r^2/(sigma_d + eps)``), i.e. it is the negation of
Eq. 1. All four comparators in the paper's Sec 2.6 are named "Loss Function"
(Simple = -Profit, Sharpe = -Sharpe, Sortino = -Sortino), which is consistent:
only under minimization do those branch labels make sense.

A maximizer handed these numbers will select the *worst* strategy in the grid.
``maximization_value()`` returns ``-score`` for optimizers that can only
maximize; do not feed ``score`` itself into one. Verified against the source PDF
(arXiv:2602.00080v1 Algorithm 1, p. 5) because the repo document's §2.1
transcription dropped that minus sign.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Literal

from pydantic import BaseModel, Field

from finrobot.engine.backtest.validation.stats import (
    FloatSequence,
    downside_deviation,
    equity_curve_r2,
    mean,
    std,
)

__all__ = ["GTScoreResult", "generalization_ratio", "gt_score", "stabilized_period_length"]

#: Sentinel for the paper's ``n_min`` rule. The paper says only that
#: parameterizations below ``n_min`` are "assigned a large penalty" and gives no
#: value, so this number is FinRobot's: the supremum of the paper's
#: underperformance branch (``100 + 100*(1 - exp(-|z-1|))`` as ``|z-1| -> inf``).
#: A minimized loss must exceed every other branch to be a penalty, and 200 does.
INSUFFICIENT_SAMPLE_PENALTY = 200.0

#: The paper's ``epsilon`` in the GT-Score denominator (§2.1 Eq. 1).
_EPSILON = 1e-6


class GTScoreResult(BaseModel):
    """Outcome of :func:`gt_score` — the score, its branch, and every input term."""

    score: float = Field(description="GT-Score value; LOWER is better (see direction)")
    direction: Literal["minimize"] = Field(
        default="minimize", description="Optimization sense of `score`"
    )
    branch: Literal["insufficient_sample", "underperform", "marginal", "standard"] = Field(
        description="Which piecewise branch produced the score"
    )
    z: float = Field(description="Significance gate (mu - mu_benchmark) / (sigma / sqrt(N))")
    mean_return: float = Field(description="Mean strategy return per observation")
    benchmark_mean: float = Field(description="Mean benchmark return per observation")
    std_return: float = Field(description="Std of strategy returns")
    downside_deviation: float = Field(description="Downside deviation used in the denominator")
    equity_r2: float = Field(description="Equity-curve linear fit (consistency)")
    n_observations: int = Field(description="Number of return observations (trades/bars)")
    n_min: int = Field(description="Minimum observation count below which the score is penalized")
    benchmark_provided: bool = Field(
        description="False when the benchmark series was omitted and treated as zero"
    )

    def maximization_value(self) -> float:
        """Negated score, for optimizers that can only maximize."""
        return -self.score

    def format_summary(self) -> str:
        """Human-readable one-block summary, mirroring ``BacktestResult``."""
        return "\n".join(
            [
                f"GT-Score:       {self.score:.6f}  ({self.direction}, {self.branch})",
                f"  z gate:       {self.z:.4f}   (n={self.n_observations}, n_min={self.n_min})",
                f"  mean/sigma:   {self.mean_return:.6f} / {self.std_return:.6f}",
                f"  benchmark:    {self.benchmark_mean:.6f}"
                + ("" if self.benchmark_provided else "  [assumed zero]"),
                f"  downside dev: {self.downside_deviation:.6f}",
                f"  equity r^2:   {self.equity_r2:.4f}",
            ]
        )


def gt_score(
    returns: FloatSequence,
    *,
    benchmark_returns: FloatSequence | None = None,
    equity_curve: FloatSequence | None = None,
    n_min: int = 50,
) -> GTScoreResult:
    """Composite objective that refuses to select significance-failing parameter sets.

    ``returns`` are per-observation strategy returns (per trade or per bar —
    the paper uses executed trades, in which case ``n_min=50`` means 50 trades).
    ``benchmark_returns`` is the buy-and-hold series over the same observations;
    when omitted it is treated as zero and the result says so
    (``benchmark_provided=False``) — deliberately visible, because a benchmark
    that is silently wrong shifts ``z`` and therefore the score.

    ``equity_curve`` is used only for the consistency term ``r^2``. When omitted
    it is compounded from ``returns``; when supplied it must carry one more
    point than there are returns (the initial value).

    **Provenance of `r^2`.** The paper defines it only as "the R-squared value
    measuring consistency of returns" and never says what is regressed against
    what, so *this* computation — the fit of the equity curve to a straight line,
    which penalizes returns that arrive in one jump — is FinRobot's choice, not
    the paper's. Scores computed with a different ``r^2`` definition are not
    comparable, so the docstring states it rather than leaving it implied.
    """
    observations = list(returns)
    if not observations:
        raise ValueError("gt_score needs at least one observation")
    if n_min < 1:
        raise ValueError(f"n_min must be positive, got {n_min!r}")

    if benchmark_returns is None:
        benchmark_mean = 0.0
        benchmark_provided = False
    else:
        benchmark = list(benchmark_returns)
        if len(benchmark) != len(observations):
            raise ValueError(
                f"benchmark_returns has {len(benchmark)} observations, "
                f"returns has {len(observations)}; they must be aligned"
            )
        benchmark_mean = mean(benchmark)
        benchmark_provided = True

    if equity_curve is None:
        if len(observations) < 2:
            raise ValueError("gt_score needs at least 2 observations to build an equity curve")
        curve = [1.0]
        for value in observations:
            curve.append(curve[-1] * (1.0 + value))
    else:
        curve = list(equity_curve)
        if len(curve) != len(observations) + 1:
            raise ValueError(
                f"equity_curve must have len(returns) + 1 = {len(observations) + 1} points, "
                f"got {len(curve)}"
            )

    mu = mean(observations)
    sigma = std(observations)
    n_observations = len(observations)
    z = (mu - benchmark_mean) / (sigma / math.sqrt(n_observations))
    r_squared = equity_curve_r2(curve)
    sigma_d = downside_deviation(observations)

    if z > 1.0:
        branch: Literal["insufficient_sample", "underperform", "marginal", "standard"] = "standard"
        # Negated: Algorithm 1 line 6 writes `score <- -mu*ln(z)*r^2/(sigma_d+eps)`
        # because the objective is a loss to minimize. Dropping this minus (as the
        # repo document's transcription did) makes a maximizer pick losers.
        score = -mu * math.log(z) * r_squared / (sigma_d + _EPSILON)
    elif z > 0.0:
        branch = "marginal"
        score = 100.0 * (1.0 - math.exp(-abs(z - 1.0)))
    else:
        branch = "underperform"
        score = 100.0 + 100.0 * (1.0 - math.exp(-abs(z - 1.0)))

    if n_observations < n_min:
        branch = "insufficient_sample"
        score = max(score, INSUFFICIENT_SAMPLE_PENALTY)

    return GTScoreResult(
        score=score,
        branch=branch,
        z=z,
        mean_return=mu,
        benchmark_mean=benchmark_mean,
        std_return=sigma,
        downside_deviation=sigma_d,
        equity_r2=r_squared,
        n_observations=n_observations,
        n_min=n_min,
        benchmark_provided=benchmark_provided,
    )


def generalization_ratio(validation_return: float, training_return: float) -> float:
    """``validation_return / training_return`` — how much survives out of sample.

    The cheapest single health metric for a walk-forward run (§2.2): near 1 means
    little decay. Only meaningful for a positive training return; a non-positive
    one makes the ratio's sign meaningless (a negative denominator flips it), so
    this raises instead of returning a number that would be read as an improvement.
    """
    if not math.isfinite(training_return) or not math.isfinite(validation_return):
        raise ValueError("generalization_ratio requires finite returns")
    if training_return <= 0.0:
        raise ValueError(
            f"generalization_ratio is undefined for a non-positive training return "
            f"({training_return!r}); report the pair instead"
        )
    return validation_return / training_return


def stabilized_period_length(
    returns: FloatSequence,
    *,
    candidates: Sequence[int] | None = None,
    tolerance: float = 0.01,
    fallback: int = 50,
) -> int:
    """Optional §2.1 'stabilized variance' periodization.

    Walk candidate period lengths in ascending order and return the first one
    whose period-aggregated return variance differs from the previous candidate's
    by less than ``tolerance`` (relative) — i.e. the shortest period past which
    the volatility estimate stops moving. Returns ``fallback`` (the paper's
    ``n=50``) when no candidate stabilizes.

    The paper states the rule in one sentence and does not fix the candidate
    ladder, so the ladder is explicit here (default: every length from 5 up to
    ``len(returns) // 4``) and callers can override it. This function is a
    diagnostic knob, not a gate: ``gt_score`` does not apply it silently.
    """
    data = list(returns)
    if len(data) < 8:
        return fallback
    ladder = list(candidates) if candidates is not None else list(range(5, len(data) // 4 + 1))
    if not ladder:
        return fallback

    previous: float | None = None
    for period in ladder:
        if period < 2 or period > len(data):
            raise ValueError(f"candidate period {period!r} is outside 2..{len(data)}")
        buckets = len(data) // period
        if buckets < 2:
            break
        period_returns = [
            math.fsum(data[i * period : (i + 1) * period]) / period for i in range(buckets)
        ]
        variance = std(period_returns) ** 2
        if previous is not None and previous > 0.0:
            if abs(variance - previous) / previous < tolerance:
                return period
        previous = variance
    return fallback
