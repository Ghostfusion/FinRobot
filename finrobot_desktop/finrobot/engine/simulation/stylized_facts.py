"""Stylized-facts distance and moment-coverage validation (§2.2).

This module turns "the simulation looks realistic" into a deterministic number:
the Hill tail index, realized volatility, and the return / squared-return
autocorrelations of §2.2, plus the *per-moment, per-path* coverage matrix that
the document insists on over an averaged loss. A single low-coverage cell (the
document's own example: a 10%% coverage cell on squared-return ACF(60)) is a
real miss and must never be hidden by averaging across moments.

Pure NumPy, no SciPy/statsmodels: the inverse-normal quantile for the coverage
band uses Acklam's rational approximation, and the block bootstrap is the same
scheme the document's weights are built from (``w_i = 1 / sigma_i^2``).
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from enum import Enum

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "CoverageMatrix",
    "Moment",
    "MomentKind",
    "block_bootstrap_weights",
    "bootstrap_paths",
    "coverage_matrix",
    "evaluate_moment",
    "default_moments",
    "hill_tail_index",
    "realized_volatility",
    "return_autocorr",
    "squared_return_autocorr",
]

#: Document defaults (§2.2): return-ACF lags and squared-return-ACF lags, each
#: smoothed by a 3-lag average. The Hill estimator uses a 5%% tail.
DEFAULT_HILL_TAIL_FRACTION = 0.05
DEFAULT_VOL_WINDOW = 30
RETURN_ACF_LAGS: tuple[int, ...] = (30, 31, 32, 60, 61, 62, 90, 91, 92)
SQUARED_ACF_LAGS: tuple[int, ...] = (1, 2, 3, 30, 31, 32, 60, 61, 62, 90, 91, 92)

#: Bootstrap resample count and block length used for the coverage band and the
#: inverse-variance weights. Fixed so every call is deterministic; the caller
#: chooses the seed only where the API exposes one.
_BOOTSTRAP_RESAMPLES = 200
_DEFAULT_BLOCK = 25
#: Internal seed for the coverage band, which has no seed parameter.
_COVERAGE_SEED = 0


class MomentKind(str, Enum):
    """The family of stylized fact a :class:`Moment` selects."""

    HILL = "hill"
    REALIZED_VOLATILITY = "realized_volatility"
    RETURN_ACF = "return_acf"
    SQUARED_RETURN_ACF = "squared_return_acf"


class Moment(BaseModel):
    """One named stylized fact: a kind plus the parameter that kind needs.

    ``param`` is the ``tail_fraction`` (Hill), the ``window`` (realized
    volatility) or the ``lag`` (the two autocorrelations). The ``name`` is what
    the coverage matrix keys cells by.
    """

    model_config = ConfigDict(frozen=True)

    name: str
    kind: MomentKind
    param: float


class CoverageMatrix(BaseModel):
    """Per-moment, per-path coverage of the historical sampling band.

    ``cells[i][j]`` is 1.0 when path ``j``'s value for moment ``i`` lies inside
    the historical band, else 0.0 — the raw matrix the document's 10%%-cell
    example refers to. ``per_moment`` averages each row and ``aggregate``
    averages the rows; the aggregate is a convenience, NEVER a substitute for
    reading the cells (a 10%% cell is a real failure even at a high aggregate).
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    moments: list[str] = Field(description="Moment names, one row per moment")
    cells: list[list[float]] = Field(description="n_moments x n_paths 0/1 coverage cells")
    per_moment: dict[str, float] = Field(description="Coverage fraction per moment")
    aggregate: float = Field(description="Mean of per_moment; not a substitute for cells")
    alpha: float = Field(description="Confidence level used for the historical band")

    def cell(self, moment: str, path_index: int) -> float:
        """Return the 0/1 coverage cell for ``moment`` and path ``path_index``."""
        row = self.moments.index(moment)
        return self.cells[row][path_index]


def _as_series(values: Sequence[float] | np.ndarray, *, name: str) -> np.ndarray:
    """Coerce to a 1-D float64 array, rejecting empty or non-finite input."""
    series: np.ndarray = np.asarray(values, dtype=np.float64).reshape(-1)
    if series.size == 0:
        raise ValueError(f"{name} must be non-empty")
    if not bool(np.all(np.isfinite(series))):
        raise ValueError(f"{name} contains non-finite values")
    return series


def hill_tail_index(returns: Sequence[float] | np.ndarray, *, tail_fraction: float) -> float:
    """Hill estimator of the tail index on |returns| (§2.2).

    Applied to absolute returns, so it measures heavy-tailedness without sign
    asymmetry. Larger values mean fatter tails. Returns 0.0 for a degenerate
    series (fewer than two points, or a zero tail cutoff) rather than NaN.
    """
    if not 0.0 < tail_fraction <= 1.0:
        raise ValueError(f"tail_fraction must lie in (0, 1], got {tail_fraction}")
    series = _as_series(returns, name="returns")
    n = series.size
    if n < 2:
        return 0.0
    k = max(1, int(math.floor(tail_fraction * n)))
    k = min(k, n - 1)
    ordered: np.ndarray = np.sort(np.abs(series))[::-1]
    cutoff = float(ordered[k])
    if cutoff <= 0.0:
        return 0.0
    ratios: np.ndarray = ordered[:k] / cutoff
    return float(np.mean(np.log(ratios)))


def realized_volatility(returns: Sequence[float] | np.ndarray, *, window: int) -> float:
    """Mean realized volatility over consecutive ``window``-length blocks.

    Each block's realized volatility is ``sqrt(sum(r^2))``; the moment is the
    mean across blocks. A series shorter than ``window`` is treated as one
    block, so the function is always defined for non-empty input.
    """
    if window < 1:
        raise ValueError(f"window must be >= 1, got {window}")
    series = _as_series(returns, name="returns")
    n = series.size
    if n < window:
        return float(math.sqrt(float(np.sum(series * series))))
    n_blocks = n // window
    usable: np.ndarray = series[: n_blocks * window].reshape(n_blocks, window)
    per_block: np.ndarray = np.sqrt(np.sum(usable * usable, axis=1))
    return float(np.mean(per_block))


def _pearson_autocorr(series: np.ndarray, lag: int) -> float:
    """Lag-``lag`` Pearson autocorrelation; 0.0 when a slice is constant."""
    n = series.size
    if lag < 1 or lag >= n:
        return 0.0
    left: np.ndarray = series[: n - lag]
    right: np.ndarray = series[lag:]
    left_dev: np.ndarray = left - left.mean()
    right_dev: np.ndarray = right - right.mean()
    denom = float(math.sqrt(float(left_dev @ left_dev) * float(right_dev @ right_dev)))
    if denom == 0.0:
        return 0.0
    return float((left_dev @ right_dev) / denom)


def return_autocorr(returns: Sequence[float] | np.ndarray, *, lag: int) -> float:
    """Lag-``lag`` autocorrelation of the raw returns (§2.2 ACF^1)."""
    series = _as_series(returns, name="returns")
    return _pearson_autocorr(series, lag)


def squared_return_autocorr(returns: Sequence[float] | np.ndarray, *, lag: int) -> float:
    """3-lag-smoothed autocorrelation of squared returns (§2.2 ACF^2).

    The document damps single-lag noise with a 3-lag average, so the value at
    nominal ``lag`` is the mean of the raw squared-return ACF at lags
    ``{lag-1, lag, lag+1}`` intersected with ``[1, n-1]``. Lag 0 is excluded:
    it is 1.0 by construction and would only inflate every cell.
    """
    if lag < 1:
        raise ValueError(f"lag must be >= 1, got {lag}")
    series = _as_series(returns, name="returns")
    squared: np.ndarray = series * series
    neighbours = [k for k in (lag - 1, lag, lag + 1) if k >= 1]
    raw: list[float] = [_pearson_autocorr(squared, k) for k in neighbours]
    if not raw:
        return 0.0
    return float(np.mean(np.asarray(raw, dtype=np.float64)))


def evaluate_moment(series: np.ndarray, moment: Moment) -> float:
    """Evaluate ``moment`` on a single series by dispatching on its kind."""
    if moment.kind is MomentKind.HILL:
        return hill_tail_index(series, tail_fraction=moment.param)
    if moment.kind is MomentKind.REALIZED_VOLATILITY:
        return realized_volatility(series, window=int(moment.param))
    if moment.kind is MomentKind.RETURN_ACF:
        return return_autocorr(series, lag=int(moment.param))
    return squared_return_autocorr(series, lag=int(moment.param))


def default_moments() -> list[Moment]:
    """The document's §2.2 moment set: Hill, volatility, and both ACF lags."""
    moments: list[Moment] = [
        Moment(name="hill", kind=MomentKind.HILL, param=DEFAULT_HILL_TAIL_FRACTION),
        Moment(name="vol", kind=MomentKind.REALIZED_VOLATILITY, param=DEFAULT_VOL_WINDOW),
    ]
    moments.extend(
        Moment(name=f"ret_acf_{lag}", kind=MomentKind.RETURN_ACF, param=float(lag))
        for lag in RETURN_ACF_LAGS
    )
    moments.extend(
        Moment(name=f"sq_acf_{lag}", kind=MomentKind.SQUARED_RETURN_ACF, param=float(lag))
        for lag in SQUARED_ACF_LAGS
    )
    return moments


def _block_bootstrap_sample(
    returns: np.ndarray, *, n_block: int, rng: np.random.Generator
) -> np.ndarray:
    """Draw one block-bootstrap resample of ``returns`` (stationary-ish, fixed blocks)."""
    n = returns.size
    block = min(n_block, n)
    n_blocks = int(math.ceil(n / block))
    starts: np.ndarray = rng.integers(0, max(1, n - block + 1), size=n_blocks)
    offsets: np.ndarray = np.arange(block)
    index: np.ndarray = (starts[:, None] + offsets[None, :]).reshape(-1)[:n]
    resampled: np.ndarray = returns[index]
    return resampled


def _bootstrap_moment_std(returns: np.ndarray, moment: Moment, *, n_block: int, seed: int) -> float:
    """Block-bootstrap standard deviation of a single moment on ``returns``."""
    rng = np.random.default_rng(seed)
    samples: np.ndarray = np.empty(_BOOTSTRAP_RESAMPLES, dtype=np.float64)
    for i in range(_BOOTSTRAP_RESAMPLES):
        sample = _block_bootstrap_sample(returns, n_block=n_block, rng=rng)
        samples[i] = evaluate_moment(sample, moment)
    return float(np.std(samples, ddof=1)) if samples.size > 1 else 0.0


def _normal_quantile(p: float) -> float:
    """Inverse standard-normal CDF via Acklam's rational approximation.

    NumPy has no inverse-normal quantile and SciPy is out of the runtime set,
    so the coverage band's critical value uses this closed form (~1e-9 abs
    error), which keeps the band deterministic and dependency-free.
    """
    if not 0.0 < p < 1.0:
        raise ValueError(f"probability must lie in (0, 1), got {p}")
    a = (
        -3.969683028665376e01,
        2.209460984245205e02,
        -2.759285104469687e02,
        1.383577518672690e02,
        -3.066479806614716e01,
        2.506628277459239e00,
    )
    b = (
        -5.447609879822406e01,
        1.615858368580409e02,
        -1.556989798598866e02,
        6.680131188771972e01,
        -1.328068155288572e01,
    )
    c = (
        -7.784894002430293e-03,
        -3.223964580411365e-01,
        -2.400758277161838e00,
        -2.549732539343734e00,
        4.374664141464968e00,
        2.938163982698783e00,
    )
    d = (
        7.784695709041462e-03,
        3.224671290700398e-01,
        2.445134137142996e00,
        3.754408661907416e00,
    )
    plow, phigh = 0.02425, 1.0 - 0.02425
    if p < plow:
        q = math.sqrt(-2.0 * math.log(p))
        num = ((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]
        den = (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0
        return num / den
    if p > phigh:
        q = math.sqrt(-2.0 * math.log(1.0 - p))
        num = ((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]
        den = (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0
        return -num / den
    q = p - 0.5
    r = q * q
    num = (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q
    den = ((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1.0
    return num / den


def bootstrap_paths(
    series: Sequence[float] | np.ndarray,
    *,
    n_paths: int,
    n_block: int,
    seed: int,
) -> list[np.ndarray]:
    """Block-bootstrap resamples of ``series`` — the paths a coverage ratios over."""
    if n_paths < 1:
        raise ValueError(f"n_paths must be >= 1, got {n_paths}")
    if n_block < 1:
        raise ValueError(f"n_block must be >= 1, got {n_block}")
    data = _as_series(series, name="series")
    rng = np.random.default_rng(seed)
    return [_block_bootstrap_sample(data, n_block=n_block, rng=rng) for _ in range(n_paths)]


def coverage_matrix(
    real_returns: Sequence[float] | np.ndarray,
    simulated_paths: Sequence[Sequence[float] | np.ndarray],
    *,
    moments: Sequence[Moment],
    alpha: float,
) -> CoverageMatrix:
    """Per-moment, per-path coverage of the historical sampling band (§2.2).

    The band for each moment is ``m_h +/- z_(1-alpha/2) * sigma`` where ``m_h``
    is the moment on ``real_returns`` and ``sigma`` its block-bootstrap standard
    deviation. Centering the band on ``m_h`` (rather than on bootstrap
    quantiles) guarantees that a series compared against itself scores a clean
    1.0 — the acceptance property this function must satisfy.
    """
    if not 0.0 < alpha < 1.0:
        raise ValueError(f"alpha must lie in (0, 1), got {alpha}")
    if not moments:
        raise ValueError("moments must be non-empty")
    if not simulated_paths:
        raise ValueError("simulated_paths must be non-empty")
    real = _as_series(real_returns, name="real_returns")
    paths = [_as_series(p, name="simulated_path") for p in simulated_paths]
    critical = _normal_quantile(1.0 - alpha / 2.0)

    cells: list[list[float]] = []
    per_moment: dict[str, float] = {}
    for moment in moments:
        target = evaluate_moment(real, moment)
        sigma = _bootstrap_moment_std(real, moment, n_block=_DEFAULT_BLOCK, seed=_COVERAGE_SEED)
        half_width = critical * sigma
        row = [
            1.0 if abs(evaluate_moment(path, moment) - target) <= half_width else 0.0
            for path in paths
        ]
        cells.append(row)
        per_moment[moment.name] = float(np.mean(np.asarray(row, dtype=np.float64)))

    aggregate = float(np.mean(np.asarray(list(per_moment.values()), dtype=np.float64)))
    return CoverageMatrix(
        moments=[m.name for m in moments],
        cells=cells,
        per_moment=per_moment,
        aggregate=aggregate,
        alpha=alpha,
    )


def block_bootstrap_weights(
    real_returns: Sequence[float] | np.ndarray,
    *,
    n_block: int,
    seed: int,
) -> np.ndarray:
    """Inverse block-bootstrap-variance weights for the §2.2 distance terms.

    Returns the four weights for ``D(theta) = w1|dHill| + w2|dV| + w3*dACF1 +
    w4*dACF2`` with ``w_i = 1 / sigma_i^2``, where each ``sigma_i`` is the block
    bootstrap standard deviation of the historical moment. A zero-variance term
    is floored to the smallest positive weight the other terms imply, so the
    result is always finite and positive.
    """
    if n_block < 1:
        raise ValueError(f"n_block must be >= 1, got {n_block}")
    real = _as_series(real_returns, name="real_returns")

    aggregate_moments = [
        Moment(name="hill", kind=MomentKind.HILL, param=DEFAULT_HILL_TAIL_FRACTION),
        Moment(name="vol", kind=MomentKind.REALIZED_VOLATILITY, param=DEFAULT_VOL_WINDOW),
        Moment(name="acf1", kind=MomentKind.RETURN_ACF, param=30.0),
        Moment(name="acf2", kind=MomentKind.SQUARED_RETURN_ACF, param=1.0),
    ]
    variances = np.asarray(
        [
            _bootstrap_moment_std(real, m, n_block=n_block, seed=seed) ** 2
            for m in aggregate_moments
        ],
        dtype=np.float64,
    )
    positive = variances[variances > 0.0]
    floor = float(positive.min()) if positive.size else 1.0
    safe: np.ndarray = np.where(variances > 0.0, variances, floor)
    weights: np.ndarray = 1.0 / safe
    return weights
