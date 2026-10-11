"""Return-series statistics for the backtest validation gate.

What this code does that raw LLM cannot: it computes the significance and
robustness terms — Sharpe, downside deviation, skewness, kurtosis, equity-curve
fit, normal quantiles, rank correlation — that every gate in
``finrobot.engine.backtest.validation`` is defined in terms of, using the
estimators in ``strategies/qfin-st/backtest-methodology.md`` §2.1-2.8. The
arithmetic is loop-based pure Python (NumPy is imported only for annotations and
to accept array inputs), so a published score is reproducible bit-for-bit on any
machine — which is the whole point of a validation gate.

**Unit convention — read before using.** ``sharpe_ratio`` is **per
observation** (per bar). The gates' standard errors are per bar too:
``min_track_record_length`` returns a bar count, and the deflation benchmark
variance is ``1/years`` — i.e. ``periods_per_year / T`` once expressed on the
annualized scale. ``annualized_sharpe`` exists only at the reporting boundary.
Mixing the two scales silently mis-sizes every gate, so each function's
docstring states which scale it returns.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np

__all__ = [
    "EPS",
    "FloatSequence",
    "annualized_sharpe",
    "clamp",
    "downside_deviation",
    "equity_curve_r2",
    "kurtosis",
    "logit",
    "max_drawdown",
    "mean",
    "mertens_variance_factor",
    "net_of_costs",
    "norm_cdf",
    "norm_ppf",
    "sharpe_ratio",
    "skewness",
    "spearman_rho",
    "std",
]

#: Inputs the estimators accept: any float sequence, including a NumPy array —
#: which is what a backtest engine naturally hands over. NumPy appears only in
#: annotations and in the sibling modules that need linear algebra; every
#: estimator here stays loop-based and deterministic, so a published number does
#: not depend on a BLAS version.
FloatSequence = Sequence[float] | np.ndarray

#: Clamp floor used wherever a probability is pushed through a logit. Mirrors
#: the ``epsilon = 1e-6`` in arXiv:2608.23808v2 §2.11 — bounded gates have
#: degenerate point masses (14.4% of the paper's production rows were exactly
#: ``PBO = 0``), and an unclamped logit turns them into infinities that dominate
#: any blend they enter.
EPS = 1e-6

# Acklam's rational approximation to the inverse normal CDF, used with one
# Halley refinement step below (see ``norm_ppf``). Coefficients are the
# published ones; the refinement is what makes ``norm_cdf(norm_ppf(p))`` agree
# with ``p`` to ~1e-15 instead of ~1e-9.
_A = (
    -3.969683028665376e01,
    2.209460984245205e02,
    -2.759285104469687e02,
    1.383577518672690e02,
    -3.066479806614716e01,
    2.506628277459239e00,
)
_B = (
    -5.447609879822406e01,
    1.615858368580409e02,
    -1.556989798598866e02,
    6.680131188771972e01,
    -1.328068155288572e01,
)
_C = (
    -7.784894002430293e-03,
    -3.223964580411365e-01,
    -2.400758277161838e00,
    -2.549732539343734e00,
    4.374664141464968e00,
    2.938163982698783e00,
)
_D = (
    7.784695709041462e-03,
    3.224671290700398e-01,
    2.445134137142996e00,
    3.754408661907416e00,
)
_P_LOW = 0.02425
_P_HIGH = 1.0 - _P_LOW


def _finite(values: FloatSequence, *, name: str) -> list[float]:
    """Coerce ``values`` to floats, refusing non-finite entries.

    Every gate fails closed: a NaN that reaches a Sharpe or a bootstrap silently
    poisons the whole report (NaN comparisons are all false, so a NaN record can
    pass every threshold). Better to raise at the boundary.
    """
    out: list[float] = []
    for value in values:
        as_float = float(value)
        if not math.isfinite(as_float):
            raise ValueError(
                f"{name} contains a non-finite value ({as_float!r}); the validation "
                "gate fails closed on non-finite inputs"
            )
        out.append(as_float)
    return out


def clamp(value: float, low: float, high: float) -> float:
    """Clamp ``value`` into ``[low, high]`` (``low`` must not exceed ``high``)."""
    if low > high:
        raise ValueError(f"clamp bounds inverted: low={low!r} > high={high!r}")
    return low if value < low else high if value > high else value


def norm_cdf(x: float) -> float:
    """Standard normal CDF, ``P(Z <= x)``."""
    return 0.5 * math.erfc(-float(x) / math.sqrt(2.0))


def norm_ppf(p: float) -> float:
    """Standard normal quantile function (inverse CDF).

    Acklam's rational approximation plus one Halley step against ``norm_cdf``:
    accurate to ~1e-15 in the body and the far tails, which matters because the
    deflation benchmark is an *expected maximum* — it evaluates ``norm_ppf`` at
    ``1 - 1/N`` for N in the thousands, where a 1e-9-accurate approximation
    moves the gate.
    """
    probability = float(p)
    if not math.isfinite(probability) or probability <= 0.0 or probability >= 1.0:
        raise ValueError(f"norm_ppf requires p in (0, 1), got {p!r}")

    if probability < _P_LOW:
        q = math.sqrt(-2.0 * math.log(probability))
        x = (((((_C[0] * q + _C[1]) * q + _C[2]) * q + _C[3]) * q + _C[4]) * q + _C[5]) / (
            (((_D[0] * q + _D[1]) * q + _D[2]) * q + _D[3]) * q + 1.0
        )
    elif probability <= _P_HIGH:
        q = probability - 0.5
        r = q * q
        x = ((((((_A[0] * r + _A[1]) * r + _A[2]) * r + _A[3]) * r + _A[4]) * r + _A[5]) * q) / (
            ((((_B[0] * r + _B[1]) * r + _B[2]) * r + _B[3]) * r + _B[4]) * r + 1.0
        )
    else:
        q = math.sqrt(-2.0 * math.log(1.0 - probability))
        x = -(((((_C[0] * q + _C[1]) * q + _C[2]) * q + _C[3]) * q + _C[4]) * q + _C[5]) / (
            (((_D[0] * q + _D[1]) * q + _D[2]) * q + _D[3]) * q + 1.0
        )

    # One Halley refinement step: err = Phi(x) - p, derivative Phi'(x).
    err = norm_cdf(x) - probability
    u = err * math.sqrt(2.0 * math.pi) * math.exp(0.5 * x * x)
    return x - u / (1.0 + 0.5 * x * u)


def logit(p: float, *, eps: float = EPS) -> float:
    """``ln(p / (1 - p))`` with ``p`` clamped to ``[eps, 1 - eps]``.

    The clamp is deliberate, not defensive: a degenerate gate (exactly 0 or 1)
    must produce a finite, bounded margin, or the record dominates the blend.
    """
    if eps <= 0.0 or eps >= 0.5:
        raise ValueError(f"logit epsilon must lie in (0, 0.5), got {eps!r}")
    bounded = clamp(float(p), eps, 1.0 - eps)
    return math.log(bounded / (1.0 - bounded))


def mean(values: FloatSequence) -> float:
    """Arithmetic mean of ``values`` (non-empty)."""
    data = _finite(values, name="values")
    if not data:
        raise ValueError("mean of an empty sequence is undefined")
    return math.fsum(data) / len(data)


def std(values: FloatSequence, *, ddof: int = 1) -> float:
    """Sample standard deviation with ``ddof`` degrees of freedom removed."""
    data = _finite(values, name="values")
    if len(data) <= ddof:
        raise ValueError(f"std needs more than ddof={ddof} observations, got {len(data)}")
    mu = math.fsum(data) / len(data)
    variance = math.fsum((x - mu) ** 2 for x in data) / (len(data) - ddof)
    return math.sqrt(variance)


def skewness(values: FloatSequence) -> float:
    """Population skewness ``E[(x - mu)^3] / sigma^3`` (the raw moment ratio).

    This is ``gamma_3`` in the Mertens correction to the Sharpe variance
    (arXiv:2608.23808v2 §2.7), which is a *population* moment — do not swap in a
    bias-corrected sample skewness and expect the gate to hold its calibration.
    """
    data = _finite(values, name="values")
    n = len(data)
    if n < 3:
        raise ValueError(f"skewness needs at least 3 observations, got {n}")
    mu = math.fsum(data) / n
    m2 = math.fsum((x - mu) ** 2 for x in data) / n
    if m2 == 0.0:
        raise ValueError("skewness of a zero-variance series is undefined")
    m3 = math.fsum((x - mu) ** 3 for x in data) / n
    # m2 * sqrt(m2), not m2 ** 1.5: mypy infers `Any` for a float base with a
    # float exponent, and `Any` would silently leak out of the return type.
    return m3 / (m2 * math.sqrt(m2))


def kurtosis(values: FloatSequence, *, excess: bool = False) -> float:
    """Kurtosis ``E[(x - mu)^4] / sigma^4``; raw by default.

    Raw is the default because the Mertens factor is written
    ``(gamma_4 - 1) / 4`` with raw ``gamma_4`` (equivalently ``(kappa + 2) / 4``
    in excess kurtosis, as the source document notes).
    """
    data = _finite(values, name="values")
    n = len(data)
    if n < 4:
        raise ValueError(f"kurtosis needs at least 4 observations, got {n}")
    mu = math.fsum(data) / n
    m2 = math.fsum((x - mu) ** 2 for x in data) / n
    if m2 == 0.0:
        raise ValueError("kurtosis of a zero-variance series is undefined")
    m4 = math.fsum((x - mu) ** 4 for x in data) / n
    raw = m4 / m2**2
    return raw - 3.0 if excess else raw


def downside_deviation(returns: FloatSequence, *, target: float = 0.0) -> float:
    """Downside deviation: ``sqrt(mean(min(r - target, 0)^2))``.

    The mean runs over *all* observations, not just the losing ones — the
    convention in the GT-Score denominator (arXiv:2602.00080v1 Eq. 1). Averaging
    over losers only inflates the denominator and would silently shrink every
    GT-Score.
    """
    data = _finite(returns, name="returns")
    if not data:
        raise ValueError("downside_deviation of an empty series is undefined")
    squares = math.fsum(min(x - target, 0.0) ** 2 for x in data)
    return math.sqrt(squares / len(data))


def sharpe_ratio(returns: FloatSequence, *, risk_free: float = 0.0) -> float:
    """**Per-observation** Sharpe ratio: ``(mean - risk_free) / std``.

    Per bar, not annualized — see the module docstring. Annualize explicitly and
    only for reporting, via ``annualized_sharpe``.
    """
    data = _finite(returns, name="returns")
    if len(data) < 2:
        raise ValueError(f"sharpe_ratio needs at least 2 observations, got {len(data)}")
    spread = std(data)
    if spread == 0.0:
        raise ValueError("sharpe_ratio is undefined for zero-variance returns")
    return (math.fsum(data) / len(data) - risk_free) / spread


def annualized_sharpe(
    returns: FloatSequence, *, periods_per_year: int = 252, risk_free: float = 0.0
) -> float:
    """Per-observation Sharpe scaled by ``sqrt(periods_per_year)``.

    Reporting only. ``periods_per_year`` must be positive: it is the same
    ``q`` the deflation benchmark variance divides by, so a wrong value here
    changes nothing about the gates but will contradict them in a report.
    """
    if periods_per_year < 1:
        raise ValueError(f"periods_per_year must be positive, got {periods_per_year!r}")
    return sharpe_ratio(returns, risk_free=risk_free) * math.sqrt(periods_per_year)


def mertens_variance_factor(returns: FloatSequence, *, risk_free: float = 0.0) -> float:
    """``1 - gamma_3 * SR + (gamma_4 - 1) / 4 * SR^2`` — the i.i.d. Mertens
    correction to the Sharpe estimator's variance (arXiv:2608.23808v2 §2.7).

    ``SR`` here is the **per-observation** Sharpe, matching MinTRL's bar count.
    Callers that need the annualized-scale standard error multiply the whole
    factor by ``periods_per_year / T``; see
    ``overfitting.deflated_sharpe_ratio``.
    """
    data = _finite(returns, name="returns")
    sr = sharpe_ratio(data, risk_free=risk_free)
    factor = 1.0 - skewness(data) * sr + (kurtosis(data) - 1.0) / 4.0 * sr * sr
    # A negative factor is possible for violently skewed series; the sampling
    # variance cannot be, so floor it at EPS rather than returning NaN from a
    # later sqrt.
    return max(factor, EPS)


def equity_curve_r2(equity: FloatSequence) -> float:
    """R^2 of the equity curve against a straight line (the GT-Score ``r^2``).

    Measures *consistency*: a strategy that ends up ahead but via one jump fits
    a line badly and is penalized. A perfectly flat curve is a perfect fit by
    construction (``SS_res = 0``), for which the limiting ratio is 1; the score
    is still zero because GT-Score's numerator carries ``mu``.
    """
    data = _finite(equity, name="equity")
    n = len(data)
    if n < 3:
        raise ValueError(f"equity_curve_r2 needs at least 3 observations, got {n}")
    x_mean = (n - 1) / 2.0
    y_mean = math.fsum(data) / n
    sxx = math.fsum((i - x_mean) ** 2 for i in range(n))
    sxy = math.fsum((i - x_mean) * (y - y_mean) for i, y in enumerate(data))
    ss_tot = math.fsum((y - y_mean) ** 2 for y in data)
    if ss_tot == 0.0:
        return 1.0
    slope = sxy / sxx
    ss_res = math.fsum((y - (y_mean + slope * (i - x_mean))) ** 2 for i, y in enumerate(data))
    return clamp(1.0 - ss_res / ss_tot, 0.0, 1.0)


def max_drawdown(equity: FloatSequence) -> float:
    """Largest peak-to-trough decline as a positive fraction of the peak."""
    data = _finite(equity, name="equity")
    if len(data) < 2:
        raise ValueError(f"max_drawdown needs at least 2 observations, got {len(data)}")
    peak = data[0]
    worst = 0.0
    for value in data:
        peak = max(peak, value)
        if peak > 0.0:
            worst = max(worst, (peak - value) / peak)
    return worst


def spearman_rho(a: FloatSequence, b: FloatSequence) -> float:
    """Spearman rank correlation with mid-ranks for ties.

    Used by the rank-stability audit (arXiv:2608.23808v2 §4 item 2: perturbing
    the blend weights must not reorder the population) and by the labeled PBO
    proxy. Ranks, not values, so it is invariant to any monotone rescaling of
    either input — which is exactly what makes it the right check for "did the
    ranking move".
    """
    left = _finite(a, name="a")
    right = _finite(b, name="b")
    if len(left) != len(right):
        raise ValueError(f"length mismatch: {len(left)} vs {len(right)}")
    if len(left) < 2:
        raise ValueError("spearman_rho needs at least 2 paired observations")
    ranks_left = _mid_ranks(left)
    ranks_right = _mid_ranks(right)
    if std(ranks_left) == 0.0 or std(ranks_right) == 0.0:
        raise ValueError("spearman_rho is undefined when a variable is constant")
    x_mean = math.fsum(ranks_left) / len(ranks_left)
    y_mean = math.fsum(ranks_right) / len(ranks_right)
    cov = math.fsum(
        (x - x_mean) * (y - y_mean) for x, y in zip(ranks_left, ranks_right, strict=True)
    )
    sx = math.sqrt(math.fsum((x - x_mean) ** 2 for x in ranks_left))
    sy = math.sqrt(math.fsum((y - y_mean) ** 2 for y in ranks_right))
    return clamp(cov / (sx * sy), -1.0, 1.0)


def _mid_ranks(values: FloatSequence) -> list[float]:
    """Average (mid) ranks for ``values``, ties sharing the mean rank."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        shared = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[order[k]] = shared
        i = j + 1
    return ranks


def net_of_costs(
    gross_returns: FloatSequence, *, per_side_bps: float, turnover: float = 1.0
) -> list[float]:
    """Subtract round-trip trading cost from each gross return.

    ``turnover`` is the notional traded per bar as a fraction of capital, so a
    fully-switched position costs ``2 * per_side_bps`` per bar. Cost realism is
    not cosmetic: ignoring fees flips strategy rankings (arXiv:2602.00133v1), so
    the ledger stores the cost model alongside every result and the sensitivity
    harness re-runs at 0-10 bps per side (arXiv:2602.00080v1 Fig. 3).
    """
    data = _finite(gross_returns, name="gross_returns")
    if per_side_bps < 0.0:
        raise ValueError(f"per_side_bps must be non-negative, got {per_side_bps!r}")
    if turnover < 0.0:
        raise ValueError(f"turnover must be non-negative, got {turnover!r}")
    cost = 2.0 * per_side_bps / 10_000.0 * turnover
    return [x - cost for x in data]
