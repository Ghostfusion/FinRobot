"""Overfitting and selection-bias gates — §2.5-2.10 of the methodology document.

What this code does that raw LLM cannot: it decides whether a backtest result is
distinguishable from luck, using estimators that depend on the *joint*
distribution of every trial the optimizer evaluated (CSCV rank logits, deflated
Sharpe, a block-bootstrap Reality Check). A model cannot hold a candidate-by-fold
matrix in its head, and would report a plausible-looking Sharpe instead.

Sources (``strategies/qfin-st/backtest-methodology.md``): arXiv:2608.23808v2 for
PBO/DSR/MinTRL/SPA/regime, arXiv:2209.05559v6 for the CSCV estimator, the
hypothesis-test framing and the trial-count rule, arXiv:2602.00080v1 for the
selection effect itself.

Two unit conventions are load-bearing and stated once here:

* the Sharpe in :func:`deflated_sharpe_ratio` is **annualized**, because its
  benchmark uses Lo (2002)'s ``1 / years`` null sampling variance; the
  per-observation Sharpe is carried in the result for audit;
* :func:`min_track_record_length` uses the **per-observation** Sharpe and returns
  a **bar count**, because that is the form of the published formula.

Two inference primitives live here as well, because they answer the same question
from the other side: :func:`diebold_mariano` asks whether one forecast beats
another on paired losses, and :func:`sharpe_confidence_interval` reports how wide
the Sharpe estimate really is. Both reuse the module's moving-block resampler, so
their serial-dependence treatment cannot drift from the Reality Check's.

Both gates defensively reject non-finite and degenerate inputs rather than
returning a NaN that would silently pass every threshold.
"""

from __future__ import annotations

import itertools
import math
from typing import Literal

import numpy as np
from pydantic import BaseModel, Field

from finrobot.engine.backtest.validation.stats import (
    EPS,
    FloatSequence,
    annualized_sharpe,
    clamp,
    mertens_variance_factor,
    norm_cdf,
    norm_ppf,
    sharpe_ratio,
    std,
)

__all__ = [
    "AgentAcceptanceResult",
    "DMResult",
    "DSRResult",
    "MinTRLResult",
    "PBOResult",
    "RegimeResult",
    "SPAResult",
    "SharpeCIResult",
    "agent_acceptance_test",
    "deflated_sharpe_ratio",
    "diebold_mariano",
    "effective_trial_count",
    "min_track_record_length",
    "pbo_cscv",
    "pbo_fold_proxy",
    "regime_stability",
    "sharpe_confidence_interval",
    "spa_test",
]

#: Euler-Mascheroni constant, in the expected-maximum-of-N-normals approximation
#: (arXiv:2608.23808v2 §2.7).
_EULER_MASCHERONI = 0.5772156649015329


def _as_matrix(values: np.ndarray, *, name: str) -> np.ndarray:
    """Validate a 2-D float matrix: finite, non-empty, at least 2 columns."""
    # Explicit annotation: np.asarray on a bare ndarray annotation infers Any,
    # which would defeat the return type of every caller.
    matrix: np.ndarray = np.asarray(values, dtype=np.float64)
    if matrix.ndim != 2:
        raise ValueError(f"{name} must be 2-D (rows = observations, columns = trials)")
    n_rows, n_cols = matrix.shape
    if n_rows < 2 or n_cols < 2:
        raise ValueError(f"{name} needs at least 2 rows and 2 columns, got {matrix.shape}")
    if not np.isfinite(matrix).all():
        raise ValueError(f"{name} contains non-finite values; the gate fails closed on NaN/inf")
    return matrix


def _sharpe_columns(matrix: np.ndarray) -> np.ndarray:
    """Per-column (per-trial) Sharpe ratio, ``ddof=1``, no annualization."""
    # Both locals are annotated because reductions on a bare ``np.ndarray``
    # annotation infer ``Any``, which mypy then rejects on the way out
    # (no-any-return) — silently losing the return type of every caller.
    spread: np.ndarray = matrix.std(axis=0, ddof=1)
    if np.any(spread == 0.0):
        flat = np.flatnonzero(spread == 0.0).tolist()
        raise ValueError(f"trial columns {flat} have zero variance; their Sharpe is undefined")
    column_means: np.ndarray = matrix.mean(axis=0)
    ratios: np.ndarray = column_means / spread
    return ratios


def _mid_rank(values: np.ndarray, target: float) -> float:
    """1-based mid-rank of ``target`` within ``values`` (ties share the mean rank)."""
    below = float(np.count_nonzero(values < target))
    equal = float(np.count_nonzero(values == target))
    return 1.0 + below + (equal - 1.0) / 2.0


def _block_bounds(n_rows: int, n_blocks: int) -> list[tuple[int, int]]:
    """Contiguous half-open block bounds; the remainder goes to the earliest blocks."""
    base, extra = divmod(n_rows, n_blocks)
    bounds: list[tuple[int, int]] = []
    start = 0
    for index in range(n_blocks):
        width = base + (1 if index < extra else 0)
        bounds.append((start, start + width))
        start += width
    return bounds


def _moving_block_indices(
    n_rows: int, *, block_length: int, n_bootstrap: int, seed: int
) -> np.ndarray:
    """``(n_bootstrap, n_rows)`` resample indices from a moving-block bootstrap.

    Shared by the Reality Check and the Sharpe interval, because the block layout
    is the point of both: resampling i.i.d. destroys exactly the serial dependence
    each is trying to respect. One implementation keeps them from drifting apart.
    The draw is a function of ``seed`` alone, so results stay reproducible.
    """
    n_blocks = math.ceil(n_rows / block_length)
    generator = np.random.default_rng(seed)
    starts: np.ndarray = generator.integers(
        0, n_rows - block_length + 1, size=(n_bootstrap, n_blocks)
    )
    offsets: np.ndarray = np.arange(block_length)
    drawn: np.ndarray = (starts[:, :, None] + offsets[None, None, :]).reshape(n_bootstrap, -1)
    return drawn[:, :n_rows]


def _default_block_length(n_rows: int) -> int:
    """The corpus's moving-block rule, ``ceil(T ** (1/3))`` (arXiv:2608.23808v2).

    ``math.cbrt`` rather than ``T ** (1/3)``: the power form rounds *up* at exact
    cubes (``27 ** (1/3)`` is 3.0000000000000004, so ``ceil`` gives 4) and
    typeshed types ``int ** float`` as ``Any``, which mypy rejects on the way out
    of a function declared to return ``int``.
    """
    return max(1, math.ceil(math.cbrt(n_rows)))


class PBOResult(BaseModel):
    """Probability of backtest overfitting, from CSCV or its labeled proxy."""

    pbo: float = Field(
        description="Fraction of splits where the in-sample winner ranks below median OOS"
    )
    n_trials: int = Field(description="Trials ranked (columns of the performance matrix)")
    n_splits: int = Field(description="Number of IS/OOS splits evaluated")
    n_blocks: int = Field(description="Blocks the timeline was cut into")
    logit_mean: float = Field(description="Mean CSCV logit (negative = overfit-leaning)")
    logit_std: float = Field(description="Std of the CSCV logits, clamp-inclusive")
    degenerate: bool = Field(description="True when every split produced an identical logit")
    proxy: bool = Field(description="True when this is the labeled fold-wise proxy, not CSCV")
    dropped_trials: list[int] = Field(description="Columns excluded for zero variance")
    warnings: list[str] = Field(description="Human-readable caveats attached to this estimate")

    def label(self) -> Literal["cscv", "proxy"]:
        """Which estimator produced ``pbo`` — never present a proxy as CSCV."""
        return "proxy" if self.proxy else "cscv"


def pbo_cscv(returns_matrix: np.ndarray, *, n_blocks: int = 10) -> PBOResult:
    """PBO by Combinatorial Symmetric Cross-Validation (arXiv:2209.05559v6 §2.5).

    ``returns_matrix`` is ``(n_observations, n_trials)`` of per-bar returns, all
    trials on the same bar grid. The timeline is cut into ``n_blocks`` contiguous
    blocks; each split uses half of them in-sample and the complement
    out-of-sample. The in-sample winner's out-of-sample rank is mapped to a
    logit, and PBO is the fraction of splits whose logit is negative — the
    in-sample winner landed below the out-of-sample median.

    The clamp is structural, not cosmetic: collapsed combinatorics give a
    degenerate point mass at ``PBO=0`` (14.4% of the paper's production rows),
    whose logit would be ``-inf`` without the ``EPS`` floor in the rank
    denominator ``H+1``. ``degenerate`` reports when every split agreed.

    Cost is ``O(C(n_blocks, n_blocks/2) * n_observations * n_trials)`` — roughly
    250 splits at the paper's default of 10 blocks.
    """
    matrix = _as_matrix(returns_matrix, name="returns_matrix")
    n_rows, n_trials = matrix.shape
    if n_blocks < 2 or n_blocks % 2 != 0:
        raise ValueError(f"n_blocks must be even and >= 2, got {n_blocks!r}")
    if n_rows < 2 * n_blocks:
        raise ValueError(f"need at least 2 * n_blocks = {2 * n_blocks} rows, got {n_rows}")

    warnings: list[str] = []
    keep = np.flatnonzero(matrix.std(axis=0, ddof=1) > 0.0)
    dropped = [index for index in range(n_trials) if index not in set(keep.tolist())]
    if dropped:
        warnings.append(
            f"dropped {len(dropped)} zero-variance trial(s) {dropped}: they cannot be ranked"
        )
    if keep.size < 2:
        raise ValueError("fewer than 2 trials with non-zero variance; PBO is undefined")
    matrix = matrix[:, keep]
    n_trials = int(matrix.shape[1])

    bounds = _block_bounds(n_rows, n_blocks)
    half = n_blocks // 2
    logits: list[float] = []
    for combo in itertools.combinations(range(n_blocks), half):
        in_sample_rows = np.concatenate([np.arange(*bounds[b]) for b in combo])
        out_rows = np.concatenate(
            [np.arange(*bounds[b]) for b in range(n_blocks) if b not in set(combo)]
        )
        in_sample = _sharpe_columns(matrix[in_sample_rows])
        out_sample = _sharpe_columns(matrix[out_rows])
        winner = int(np.argmax(in_sample))
        omega = _mid_rank(out_sample, float(out_sample[winner])) / (n_trials + 1)
        logits.append(math.log(clamp(omega, EPS, 1.0 - EPS) / (1.0 - clamp(omega, EPS, 1.0 - EPS))))

    values = np.asarray(logits, dtype=np.float64)
    dispersion = float(values.std(ddof=1)) if values.size > 1 else 0.0
    if dispersion == 0.0:
        warnings.append(
            "every split produced the same logit (degenerate CSCV); PBO is a point mass, "
            "so the Minerva blend must floor this gate's dispersion"
        )
    return PBOResult(
        pbo=float(np.count_nonzero(values < 0.0)) / values.size,
        n_trials=n_trials,
        n_splits=int(values.size),
        n_blocks=n_blocks,
        logit_mean=float(values.mean()),
        logit_std=dispersion,
        degenerate=dispersion == 0.0,
        proxy=False,
        dropped_trials=dropped,
        warnings=warnings,
    )


def pbo_fold_proxy(fold_performance: np.ndarray) -> PBOResult:
    """Labeled fold-wise proxy for PBO, for when only per-fold aggregates exist.

    ``fold_performance`` is ``(n_folds, n_trials)`` of that fold's performance
    (Sharpe or mean return). Each fold is held out once; the trial that wins on
    the others is ranked on the held-out fold, exactly as in CSCV — but the folds
    are the walk-forward windows rather than the ``C(n_blocks, n_blocks/2)``
    combinatorial subsets, which is what makes this a proxy. The doc is explicit
    that this must be labeled rather than reported as the CSCV estimator.
    """
    matrix = np.asarray(fold_performance, dtype=np.float64)
    if matrix.ndim != 2:
        raise ValueError("fold_performance must be 2-D (rows = folds, columns = trials)")
    n_folds, n_trials = matrix.shape
    if n_folds < 3 or n_trials < 2:
        raise ValueError(f"need at least 3 folds and 2 trials, got {matrix.shape}")
    if not np.isfinite(matrix).all():
        raise ValueError("fold_performance contains non-finite values")

    logits: list[float] = []
    for held_out in range(n_folds):
        others = [index for index in range(n_folds) if index != held_out]
        winner = int(np.argmax(matrix[others].mean(axis=0)))
        omega = _mid_rank(matrix[held_out], float(matrix[held_out][winner])) / (n_trials + 1)
        clamped = clamp(omega, EPS, 1.0 - EPS)
        logits.append(math.log(clamped / (1.0 - clamped)))

    values = np.asarray(logits, dtype=np.float64)
    dispersion = float(values.std(ddof=1)) if values.size > 1 else 0.0
    return PBOResult(
        pbo=float(np.count_nonzero(values < 0.0)) / values.size,
        n_trials=n_trials,
        n_splits=int(values.size),
        n_blocks=n_folds,
        logit_mean=float(values.mean()),
        logit_std=dispersion,
        degenerate=dispersion == 0.0,
        proxy=True,
        dropped_trials=[],
        warnings=["fold-wise proxy: not the combinatorially symmetric CSCV estimator"],
    )


def effective_trial_count(returns_matrix: np.ndarray) -> float:
    """Effective number of independent trials, by eigenvalue participation ratio.

    A search that evaluated 500 parameter sets has not run 500 independent tests —
    neighbouring parameters produce near-identical return series. §2.7 resolves
    the count by decorrelating the trial return vectors: ``(sum lambda)^2 /
    sum(lambda^2)`` over the eigenvalues of their correlation matrix. Identical
    trials give 1.0, mutually orthogonal trials give the raw count.
    """
    # Validated locally rather than via _as_matrix: a one-trial search is a
    # legitimate input here (its effective count is trivially 1), while PBO and
    # SPA genuinely need at least two candidates to rank.
    matrix: np.ndarray = np.asarray(returns_matrix, dtype=np.float64)
    if matrix.ndim != 2:
        raise ValueError("returns_matrix must be 2-D (rows = observations, columns = trials)")
    n_rows, n_trials = matrix.shape
    if n_rows < 2 or n_trials < 1:
        raise ValueError(f"returns_matrix needs at least 2 rows and 1 column, got {matrix.shape}")
    if not np.isfinite(matrix).all():
        raise ValueError("returns_matrix contains non-finite values; the gate fails closed")
    if n_trials == 1:
        return 1.0
    # Checked before np.corrcoef: a constant column divides by zero there, which
    # emits a RuntimeWarning and only afterwards yields the NaN we would reject.
    flat = np.flatnonzero(matrix.std(axis=0, ddof=1) == 0.0).tolist()
    if flat:
        raise ValueError(
            f"trial columns {flat} are constant, so their correlation is undefined; "
            "effective_trial_count fails closed rather than counting them"
        )
    correlations = np.corrcoef(matrix, rowvar=False)
    if not np.isfinite(correlations).all():
        raise ValueError("trial correlation matrix is not finite; the gate fails closed")
    eigenvalues = np.clip(np.linalg.eigvalsh(correlations), 0.0, None)
    total = float(eigenvalues.sum())
    squared = float((eigenvalues**2).sum())
    if squared == 0.0:
        raise ValueError("correlation matrix has no positive eigenvalues; input is degenerate")
    return total * total / squared


class DSRResult(BaseModel):
    """Deflated Sharpe ratio and every term that produced it."""

    dsr: float = Field(description="Phi(u) — probability the Sharpe is genuine after deflation")
    pre_phi_statistic: float = Field(
        description="u, the pre-Phi statistic. STORE THIS: Phi(u) saturates near 0 and "
        "cannot be inverted back into a ranking (arXiv:2608.23808v2 §2.11)"
    )
    sharpe_annualized: float = Field(description="Observed annualized Sharpe")
    sharpe_per_observation: float = Field(description="Observed per-observation Sharpe")
    benchmark_sr: float = Field(description="Deflated benchmark (expected max under the null)")
    n_trials: float = Field(description="Effective number of independent trials used")
    n_observations: int = Field(description="Bar count T")
    mertens_factor: float = Field(description="1 - skew*SR + (kurt-1)/4*SR^2, per observation")
    se_null: float = Field(description="Null sampling std of the annualized Sharpe, sqrt(q/T)")
    se_sharpe: float = Field(description="Mertens-corrected sampling std of the annualized Sharpe")
    warnings: list[str] = Field(description="Caveats attached to this estimate")


def deflated_sharpe_ratio(
    returns: FloatSequence,
    *,
    n_trials: float = 1.0,
    periods_per_year: int = 252,
    risk_free: float = 0.0,
) -> DSRResult:
    """Sharpe significance after deflating for the number of trials (arXiv:2608.23808v2 §2.7).

    ``returns`` are per-bar strategy returns; ``n_trials`` should be the
    *effective* count from :func:`effective_trial_count`, not the raw grid size —
    the paper's practical note, and the difference between a usable gate and one
    that over-deflates every wide search.

    The benchmark is ``se_null * E[max of n_trials standard normals]`` with
    ``se_null = sqrt(periods_per_year / T)``: Lo (2002)'s null sampling variance,
    *not* a fixed constant, which is what keeps the benchmark flat as history
    grows for a pure-noise strategy (the paper's own flat-trend check). The
    observed Sharpe enters annualized and is divided by the Mertens-corrected
    standard error on the same scale, so ``u`` is a standardized statistic under
    the null and ``dsr = Phi(u)``.
    """
    observations = list(returns)
    n_observations = len(observations)
    if n_observations < 4:
        raise ValueError(
            f"deflated_sharpe_ratio needs at least 4 observations, got {n_observations}"
        )
    if periods_per_year < 1:
        raise ValueError(f"periods_per_year must be positive, got {periods_per_year!r}")
    if not math.isfinite(n_trials) or n_trials < 1.0:
        raise ValueError(f"n_trials must be a finite number >= 1, got {n_trials!r}")

    warnings: list[str] = []
    sr_per_observation = sharpe_ratio(observations, risk_free=risk_free)
    sr_annualized = sr_per_observation * math.sqrt(periods_per_year)
    factor = mertens_variance_factor(observations, risk_free=risk_free)

    se_null = math.sqrt(periods_per_year / n_observations)
    if n_trials <= 1.0:
        expected_max = 0.0
    else:
        expected_max = (1.0 - _EULER_MASCHERONI) * norm_ppf(1.0 - 1.0 / n_trials) + (
            _EULER_MASCHERONI
        ) * norm_ppf(1.0 - 1.0 / (n_trials * math.e))
    benchmark_sr = se_null * expected_max
    se_sharpe = math.sqrt(periods_per_year * factor / n_observations)
    if se_sharpe == 0.0:
        raise ValueError("Mertens-corrected standard error is zero; DSR is undefined")

    u = (sr_annualized - benchmark_sr) / se_sharpe
    if abs(u) > 8.0:
        warnings.append(
            f"pre-Phi statistic is extreme (u={u:.1f}); the Gaussian/i.i.d. significance screen "
            "is a heuristic on fat-tailed autocorrelated returns, so treat it as a gate, not a test"
        )
    return DSRResult(
        dsr=norm_cdf(u),
        pre_phi_statistic=u,
        sharpe_annualized=sr_annualized,
        sharpe_per_observation=sr_per_observation,
        benchmark_sr=benchmark_sr,
        n_trials=n_trials,
        n_observations=n_observations,
        mertens_factor=factor,
        se_null=se_null,
        se_sharpe=se_sharpe,
        warnings=warnings,
    )


class MinTRLResult(BaseModel):
    """Minimum track record length — how many bars the evidence needs."""

    required_bars: float | None = Field(description="MinTRL in bars; None when unbounded")
    unbounded: bool = Field(
        description="True when the observed Sharpe does not exceed the benchmark"
    )
    observed_bars: int = Field(description="Bars actually available")
    passed: bool = Field(description="observed_bars >= required_bars")
    alpha: float = Field(description="Confidence level used")
    sharpe_per_observation: float = Field(description="Observed per-observation Sharpe")
    mertens_factor: float = Field(description="Skew/kurtosis correction factor")
    z_alpha: float = Field(description="Phi^-1(1 - alpha)")


def min_track_record_length(
    returns: FloatSequence, *, alpha: float = 0.05, benchmark_sr: float = 0.0
) -> MinTRLResult:
    """Bars needed for the observed per-bar Sharpe to be significant (§2.8).

    ``1 + factor * (Phi^-1(1-alpha) / SR)^2`` with the Mertens factor of
    :func:`~finrobot.engine.backtest.validation.stats.mertens_variance_factor`.
    Depends only on this strategy — unlike Minimum Backtest Length, it says
    nothing about multiple testing; that is the DSR's job.

    A strategy whose excess Sharpe is not positive has no finite evidence length:
    ``unbounded`` is returned (and the gate fails) rather than a ``inf`` that
    would break JSON serialization downstream.
    """
    observations = list(returns)
    if len(observations) < 4:
        raise ValueError(
            f"min_track_record_length needs at least 4 observations, got {len(observations)}"
        )
    if not 0.0 < alpha < 1.0:
        raise ValueError(f"alpha must lie in (0, 1), got {alpha!r}")

    sr = sharpe_ratio(observations)
    factor = mertens_variance_factor(observations)
    z_alpha = norm_ppf(1.0 - alpha)
    excess = sr - benchmark_sr
    if excess <= 0.0:
        return MinTRLResult(
            required_bars=None,
            unbounded=True,
            observed_bars=len(observations),
            passed=False,
            alpha=alpha,
            sharpe_per_observation=sr,
            mertens_factor=factor,
            z_alpha=z_alpha,
        )
    required = 1.0 + factor * (z_alpha / excess) ** 2
    return MinTRLResult(
        required_bars=required,
        unbounded=False,
        observed_bars=len(observations),
        passed=len(observations) >= required,
        alpha=alpha,
        sharpe_per_observation=sr,
        mertens_factor=factor,
        z_alpha=z_alpha,
    )


class SPAResult(BaseModel):
    """Studentized Superior Predictive Ability test (White's Reality Check)."""

    p_value: float = Field(description="Bootstrap p-value, (1 + #{S* > S}) / (B + 1)")
    statistic: float = Field(description="Studentized max of the per-trial mean differentials")
    n_trials: int = Field(description="Trials tested")
    n_relevant_trials: int = Field(description="Trials kept by Hansen's poor-performer trimming")
    n_observations: int = Field(description="Bar count")
    block_length: int = Field(description="Moving-block bootstrap block length")
    n_bootstrap: int = Field(description="Bootstrap resamples")
    seed: int = Field(description="RNG seed (the test is deterministic given it)")
    warnings: list[str] = Field(description="Caveats attached to this estimate")


def spa_test(
    returns_matrix: np.ndarray,
    benchmark: FloatSequence | None = None,
    *,
    n_bootstrap: int = 1000,
    block_length: int | None = None,
    seed: int = 42,
) -> SPAResult:
    """Block-bootstrap test for benchmark luck across trials (§2.9).

    Tests the null that no trial beats ``benchmark``. Each trial's mean
    differential is studentized by its own standard error and the maximum over
    trials is compared against a **moving-block bootstrap** distribution, drawn
    with the *same* blocks for every trial so cross-sectional dependence survives
    the resample — independent resampling per trial would destroy exactly the
    correlation that makes the max statistic's null distribution wide, i.e. it
    would manufacture significance.

    Trials that are clearly worse than the benchmark are trimmed from the max
    (Hansen's relevant set), which is the "less conservative than Reality Check"
    step: including hopeless variants inflates the bootstrap maximum and makes the
    test reward a wide search.
    """
    matrix = _as_matrix(returns_matrix, name="returns_matrix")
    n_rows, n_trials = matrix.shape
    if n_bootstrap < 2:
        raise ValueError(f"n_bootstrap must be >= 2, got {n_bootstrap!r}")
    if block_length is None:
        block_length = _default_block_length(n_rows)
    if not 1 <= block_length <= n_rows:
        raise ValueError(f"block_length must lie in 1..{n_rows}, got {block_length!r}")

    if benchmark is None:
        differentials = matrix
        warnings = ["no benchmark supplied: the null tested is 'no trial has positive mean'"]
    else:
        bench = np.asarray(benchmark, dtype=np.float64)
        if bench.shape != (n_rows,):
            raise ValueError(f"benchmark must have shape ({n_rows},), got {bench.shape}")
        if not np.isfinite(bench).all():
            raise ValueError("benchmark contains non-finite values")
        differentials = matrix - bench[:, None]
        warnings = []

    spread = differentials.std(axis=0, ddof=1)
    if np.any(spread == 0.0):
        flat = np.flatnonzero(spread == 0.0).tolist()
        raise ValueError(f"trial columns {flat} have zero variance; SPA cannot studentize them")

    trial_means = differentials.mean(axis=0)
    studentized = math.sqrt(n_rows) * trial_means / spread
    statistic = float(studentized.max())

    # Hansen's poor-performer trimming: keep trials whose studentized mean is not
    # implausibly low under the null. Guarded for tiny samples where the log-log
    # term is not defined.
    if n_rows >= 3:
        threshold = -math.sqrt(2.0 * math.log(math.log(n_rows)))
    else:
        threshold = -math.inf
    relevant = studentized >= threshold
    if not relevant.any():
        relevant = np.ones(n_trials, dtype=bool)
        warnings.append("no trial passed the poor-performer trim; all were used in the maximum")
    n_relevant = int(relevant.sum())

    resample_indices = _moving_block_indices(
        n_rows, block_length=block_length, n_bootstrap=n_bootstrap, seed=seed
    )
    exceedances = 0
    for draw in range(n_bootstrap):
        sample = differentials[resample_indices[draw]]
        sample_means = sample.mean(axis=0)
        sample_spread = sample.std(axis=0, ddof=1)
        sample_spread = np.where(sample_spread > 0.0, sample_spread, np.inf)
        resampled = math.sqrt(n_rows) * (sample_means - trial_means) / sample_spread
        if float(resampled[relevant].max()) > statistic:
            exceedances += 1

    return SPAResult(
        p_value=(1.0 + exceedances) / (n_bootstrap + 1.0),
        statistic=statistic,
        n_trials=n_trials,
        n_relevant_trials=n_relevant,
        n_observations=n_rows,
        block_length=block_length,
        n_bootstrap=n_bootstrap,
        seed=seed,
        warnings=warnings,
    )


class DMResult(BaseModel):
    """Diebold–Mariano comparison of two forecasts' relative accuracy.

    Sign convention is the standard one: a **negative** statistic means the first
    forecast carries the lower loss, i.e. it is the more accurate of the two. That
    is how the corpus reports it (e.g. DM = -7.12 for an LLM against a dictionary
    baseline), so a reader comparing our number to a paper's is comparing like
    with like.
    """

    statistic: float = Field(description="HLN-corrected DM statistic; < 0 => forecast A better")
    p_value: float = Field(description="Two-sided p-value, normal approximation")
    p_value_one_sided: float = Field(description="One-sided p-value for A beating B")
    mean_differential: float = Field(
        description="Mean loss differential (A - B); < 0 => A more accurate"
    )
    n_observations: int
    lag: int = Field(description="Newey-West Bartlett truncation lag used")
    loss: Literal["squared", "absolute"]
    forecast_horizon: int
    warnings: list[str] = Field(default_factory=list)


def diebold_mariano(
    actual: FloatSequence,
    forecast_a: FloatSequence,
    forecast_b: FloatSequence,
    *,
    loss: Literal["squared", "absolute"] = "squared",
    lag: int | None = None,
    forecast_horizon: int = 1,
) -> DMResult:
    """Test that two forecasts are equally accurate, on paired observations (§5.4).

    Why this and not two accuracy scores side by side: a model can top a
    classification benchmark and still lose money, and two accuracies are not a
    significance statement. DM reduces the paired loss differential to one
    statistic whose variance is HAC-corrected, so overlapping multi-step horizons
    (``forecast_horizon > 1``) do not get credited with precision they lack.

    The p-value uses the normal approximation of the HLN-corrected statistic rather
    than Student-t, because the corpus reports DM against a normal critical value
    and this package carries no t-distribution (no SciPy). The correction term is
    what makes that defensible at our sample sizes; a short sample is warned about.
    """
    a = np.asarray(actual, dtype=np.float64)
    fa = np.asarray(forecast_a, dtype=np.float64)
    fb = np.asarray(forecast_b, dtype=np.float64)
    if a.ndim != 1 or fa.ndim != 1 or fb.ndim != 1:
        raise ValueError("actual, forecast_a and forecast_b must all be 1-D")
    if not (a.shape == fa.shape == fb.shape):
        raise ValueError(
            f"paired series must be the same length, got actual={a.shape}, "
            f"forecast_a={fa.shape}, forecast_b={fb.shape}"
        )
    n_rows = int(a.size)
    if n_rows < 3:
        raise ValueError(
            f"diebold_mariano needs at least 3 paired observations, got {n_rows}; "
            "with fewer the HAC variance is not estimable"
        )
    if forecast_horizon < 1:
        raise ValueError(f"forecast_horizon must be >= 1, got {forecast_horizon}")
    if not (np.isfinite(a).all() and np.isfinite(fa).all() and np.isfinite(fb).all()):
        raise ValueError("inputs contain non-finite values; the test fails closed on NaN/inf")

    if loss == "squared":
        loss_a = (a - fa) ** 2
        loss_b = (a - fb) ** 2
    elif loss == "absolute":
        loss_a = np.abs(a - fa)
        loss_b = np.abs(a - fb)
    else:
        raise ValueError(f"loss must be 'squared' or 'absolute', got {loss!r}")

    if lag is None:
        # Newey-West's automatic rule, floor(4 * (T/100)^(2/9)).
        lag = int(math.floor(4.0 * (n_rows / 100.0) ** (2.0 / 9.0)))
    if not 0 <= lag < n_rows:
        raise ValueError(f"lag must lie in 0..{n_rows - 1}, got {lag}")

    differential: np.ndarray = loss_a - loss_b
    mean_differential = float(differential.mean())
    deviation: np.ndarray = differential - mean_differential
    warnings: list[str] = []

    gamma0 = float((deviation * deviation).mean())
    long_run_variance = gamma0
    for k in range(1, lag + 1):
        gamma_k = float((deviation[k:] * deviation[:-k]).mean())
        long_run_variance += 2.0 * (1.0 - k / (lag + 1.0)) * gamma_k
    if long_run_variance <= 0.0:
        raise ValueError(
            f"HAC long-run variance is non-positive ({long_run_variance:.3e}); the statistic "
            "is undefined — the differential is degenerate, not merely noisy"
        )

    dm = mean_differential / math.sqrt(long_run_variance / n_rows)
    # Harvey-Leybourne-Newbold: the corrected statistic is DM * sqrt(...) with the
    # leading term shrinking to 1 as n grows.
    correction_term = (
        n_rows + 1 - 2 * forecast_horizon + forecast_horizon * (forecast_horizon - 1) / n_rows
    ) / n_rows
    if correction_term > 0.0:
        statistic = dm * math.sqrt(correction_term)
    else:
        statistic = dm
        warnings.append(
            "Harvey-Leybourne-Newbold correction is undefined for this "
            "n/horizon combination; the uncorrected statistic is reported"
        )
    if n_rows < 20:
        warnings.append(
            f"only {n_rows} observations: the normal approximation is optimistic at this size"
        )
    if lag >= n_rows // 2:
        warnings.append(f"truncation lag {lag} is half the sample or more; HAC is unreliable here")

    return DMResult(
        statistic=statistic,
        p_value=clamp(2.0 * (1.0 - norm_cdf(abs(statistic))), 0.0, 1.0),
        # P(Z <= statistic) — small when the first forecast is the accurate one,
        # i.e. the one-sided evidence *for* A beating B, matching the field name.
        p_value_one_sided=clamp(norm_cdf(statistic), 0.0, 1.0),
        mean_differential=mean_differential,
        n_observations=n_rows,
        lag=lag,
        loss=loss,
        forecast_horizon=forecast_horizon,
        warnings=warnings,
    )


#: Above this lag-1 autocorrelation the percentile interval's coverage degrades
#: measurably. Measured over 200 replications at n=250: 0.955 at a nominal 0.95 on
#: i.i.d. Gaussian returns, but 0.900 on an AR(1) with phi=0.2 — the block
#: resample preserves serial dependence, it does not make the percentile interval
#: exact. The threshold sits at roughly 2.4 sampling standard errors (1/sqrt(n)),
#: so an i.i.d. series trips it only about 2% of the time.
AUTOCORRELATION_WARNING_THRESHOLD = 0.15


def _lag1_autocorrelation(data: np.ndarray) -> float:
    """Lag-1 autocorrelation of a 1-D series (the standard non-centred estimator)."""
    centred: np.ndarray = data - data.mean()
    denominator = float((centred * centred).sum())
    if denominator == 0.0:
        return 0.0
    return float((centred[1:] * centred[:-1]).sum()) / denominator


class SharpeCIResult(BaseModel):
    """Percentile moving-block-bootstrap interval for an annualized Sharpe."""

    point: float = Field(description="Annualized Sharpe of the observed series")
    lower: float
    upper: float
    level: float
    method: Literal["percentile-moving-block-bootstrap"]
    n_observations: int
    n_bootstrap: int
    block_length: int
    periods_per_year: int
    seed: int
    warnings: list[str] = Field(default_factory=list)


def sharpe_confidence_interval(
    returns: FloatSequence,
    *,
    level: float = 0.95,
    n_bootstrap: int = 1000,
    block_length: int | None = None,
    periods_per_year: int = 252,
    seed: int = 42,
) -> SharpeCIResult:
    """Percentile block-bootstrap interval for the annualized Sharpe (§5.4).

    Why a bootstrap rather than the textbook ``1/sqrt(T)`` error: that interval
    assumes i.i.d. returns, and a Sharpe estimated on serially correlated bars is
    the case this whole gate exists for — so the resample has to preserve blocks.
    Why percentile rather than BCa: BCa needs a bias-correction and an
    acceleration estimate, neither of which is published in the corpus, and a
    half-implemented BCa would look more authoritative than it is. So the interval
    is a sensitivity band, not a coverage guarantee — and its measured shortfall is
    stated rather than hidden: coverage is 0.955 at a nominal 0.95 on i.i.d.
    returns, but 0.900 on an AR(1) with phi=0.2, which is why a materially
    autocorrelated series gets its own warning.
    """
    data = np.asarray(returns, dtype=np.float64)
    if data.ndim != 1:
        raise ValueError("returns must be 1-D")
    n_rows = int(data.size)
    if n_rows < 2:
        raise ValueError(f"sharpe_confidence_interval needs at least 2 observations, got {n_rows}")
    if not np.isfinite(data).all():
        raise ValueError("returns contain non-finite values; the interval fails closed on NaN/inf")
    if not 0.0 < level < 1.0:
        raise ValueError(f"level must lie strictly inside (0, 1), got {level!r}")
    if n_bootstrap < 2:
        raise ValueError(f"n_bootstrap must be >= 2, got {n_bootstrap!r}")
    if periods_per_year < 1:
        raise ValueError(f"periods_per_year must be >= 1, got {periods_per_year!r}")
    if block_length is None:
        block_length = _default_block_length(n_rows)
    if not 1 <= block_length <= n_rows:
        raise ValueError(f"block_length must lie in 1..{n_rows}, got {block_length!r}")

    # A zero-variance series makes the point estimate itself undefined, and
    # ``annualized_sharpe`` already fails closed on it with a precise message —
    # no second, divergent guard here. Note the floating-point subtlety: a
    # constant series has std ~1e-18 rather than exactly 0, so only that deeper
    # check catches it.
    point = annualized_sharpe(data, periods_per_year=periods_per_year)

    indices = _moving_block_indices(
        n_rows, block_length=block_length, n_bootstrap=n_bootstrap, seed=seed
    )
    samples: np.ndarray = data[indices]
    sample_means: np.ndarray = samples.mean(axis=1)
    sample_spreads: np.ndarray = samples.std(axis=1, ddof=1)
    usable: np.ndarray = sample_spreads > 0.0
    warnings: list[str] = []
    rho1 = _lag1_autocorrelation(data)
    if abs(rho1) > AUTOCORRELATION_WARNING_THRESHOLD:
        warnings.append(
            f"lag-1 autocorrelation is {rho1:+.2f}, and the percentile interval under-covers on "
            "serially dependent returns (measured 0.900 against a nominal 0.95 on AR(1) phi=0.2); "
            "read a marginal interval as inconclusive rather than as evidence of an edge"
        )
    n_usable = int(usable.sum())
    if n_usable < 2:
        raise ValueError(
            f"only {n_usable} of {n_bootstrap} resamples had non-zero dispersion; the interval "
            "cannot be formed and is refused rather than widened by padding"
        )
    if n_usable < n_bootstrap:
        warnings.append(
            f"{n_bootstrap - n_usable} of {n_bootstrap} resamples were flat and dropped"
        )
    if n_bootstrap < 200:
        warnings.append(f"{n_bootstrap} resamples is coarse for a {level:.0%} percentile interval")
    warnings.append(
        "percentile interval: not bias-corrected, so treat it as a sensitivity band rather "
        "than a coverage guarantee"
    )

    ratios = (sample_means[usable] / sample_spreads[usable]) * math.sqrt(periods_per_year)
    tail = (1.0 - level) / 2.0
    lower, upper = (float(value) for value in np.quantile(ratios, [tail, 1.0 - tail]))

    return SharpeCIResult(
        point=point,
        lower=lower,
        upper=upper,
        level=level,
        method="percentile-moving-block-bootstrap",
        n_observations=n_rows,
        n_bootstrap=n_bootstrap,
        block_length=block_length,
        periods_per_year=periods_per_year,
        seed=seed,
        warnings=warnings,
    )


class RegimeResult(BaseModel):
    """Regime-stability diagnostic and its gate verdict."""

    rho: float = Field(description="Stability score in [0, 1]")
    passed: bool = Field(description="rho >= tau")
    positive_fraction: float = Field(description="Fraction of windows with positive Sharpe")
    sharpe_std: float = Field(description="Std of per-window Sharpe")
    min_sharpe: float = Field(description="Worst window Sharpe")
    n_windows: int = Field(description="Validation windows")
    tau: float = Field(description="Gate threshold")
    sigma_ref: float = Field(description="Reference Sharpe dispersion")


def regime_stability(
    window_sharpes: FloatSequence, *, tau: float = 0.60, sigma_ref: float = 2.0
) -> RegimeResult:
    """Regime dependence of the edge across validation windows (§2.10).

    ``0.5 * p_plus + 0.3 * clip(1 - s_SR / sigma_ref) + 0.2 * logistic(SR_min)`` —
    rewards a strategy that is positive in most windows, has a *stable* Sharpe
    across them, and is not catastrophic in its worst one. The paper flags these
    weights as its most ad-hoc component, so treat a marginal failure as a prompt
    to look at the window Sharpes rather than as a verdict on its own.
    """
    sharpes = [float(value) for value in window_sharpes]
    if len(sharpes) < 2:
        raise ValueError(f"regime_stability needs at least 2 windows, got {len(sharpes)}")
    if not all(math.isfinite(value) for value in sharpes):
        raise ValueError("window_sharpes contains non-finite values")
    if sigma_ref <= 0.0:
        raise ValueError(f"sigma_ref must be positive, got {sigma_ref!r}")

    positive_fraction = sum(1 for value in sharpes if value > 0.0) / len(sharpes)
    dispersion = std(sharpes)
    worst = min(sharpes)
    logistic = 1.0 / (1.0 + math.exp(-worst))
    rho = clamp(
        0.5 * positive_fraction
        + 0.3 * clamp(1.0 - dispersion / sigma_ref, 0.0, 1.0)
        + 0.2 * logistic,
        0.0,
        1.0,
    )
    return RegimeResult(
        rho=rho,
        passed=rho >= tau,
        positive_fraction=positive_fraction,
        sharpe_std=dispersion,
        min_sharpe=worst,
        n_windows=len(sharpes),
        tau=tau,
        sigma_ref=sigma_ref,
    )


class AgentAcceptanceResult(BaseModel):
    """Accept/reject verdict for an RL or ML agent from the §2.6 hypothesis test."""

    p_value: float = Field(description="Estimated overfitting probability (PBO)")
    alpha: float = Field(description="Significance level")
    accepted: bool = Field(description="True when p_value < alpha (H0: not overfitted)")
    n_trials: int = Field(description="Trials the estimate was built from")
    trials_sufficient: bool = Field(description="n_trials >= min_trials for the grid-coverage rule")
    warnings: list[str] = Field(description="Caveats, e.g. too few trials to cover the search")


def agent_acceptance_test(
    pbo: PBOResult, *, alpha: float = 0.10, min_trials: int = 50
) -> AgentAcceptanceResult:
    """Reject overfitted agents before deployment (arXiv:2209.05559v6 §2.6).

    ``H0: p < alpha`` (not overfitted) vs ``H1: p >= alpha``. The trial-count rule
    comes from the paper: ``1 - (1 - 0.05)^H >= 0.9`` needs ``H >= 50`` for a good
    region covering 5% of the grid, so a smaller search is reported as
    insufficient evidence even when ``p`` looks acceptable — an under-searched
    grid understates overfitting rather than proving its absence.
    """
    if not 0.0 < alpha < 1.0:
        raise ValueError(f"alpha must lie in (0, 1), got {alpha!r}")
    warnings: list[str] = []
    sufficient = pbo.n_trials >= min_trials
    if not sufficient:
        warnings.append(
            f"only {pbo.n_trials} trials: the paper's grid-coverage rule needs >= {min_trials} "
            "for 1 - (1 - 0.05)^H >= 0.9, so this PBO understates overfitting"
        )
    if pbo.proxy:
        warnings.append("PBO came from the fold-wise proxy, not CSCV")
    return AgentAcceptanceResult(
        p_value=pbo.pbo,
        alpha=alpha,
        accepted=pbo.pbo < alpha,
        n_trials=pbo.n_trials,
        trials_sufficient=sufficient,
        warnings=warnings,
    )
