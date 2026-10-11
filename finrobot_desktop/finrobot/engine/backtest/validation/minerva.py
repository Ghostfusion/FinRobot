"""MinervaScore aggregation — §2.11 of the methodology document.

What this code does that raw LLM cannot: it turns five independently computed
gates into one audit-traceable verdict whose display can never contradict the
Seal. The invariant "display >= 80 iff every gate passed" is enforced by
construction and re-checked at runtime, which is the property the source paper
holds over 359,062 production backtests — a model writing prose would have no way
to guarantee it, and this is precisely the kind of guarantee that must not depend
on prose.

Calibration honesty (read this before trusting a number). The shipped scale
factors, thresholds, correlation matrix and reference point are the source
paper's own published values (Tables 3-4, Eqs. 6-9), not invented here — but they
were estimated on that paper's production population, so the *magnitude* of
``display`` stays population-relative: recalibrate with ``estimate_margin_sigma``
and ``estimate_sigma_eff`` over FinRobot's own ledger and bump the calibration
``version``. Nothing here is more than one calibration away from being wrong, and
two things differ from the paper's setup by construction: the failing-population
CDF is uniform (the paper's reference population is not available), and
``margin_clip`` is a saturation guard this implementation adds.

The **Seal does not depend on any of it.** Every margin is zero exactly at its
gate threshold and positive exactly when that gate passes, so a mis-scaled
constant can compress or stretch the display but never flip the verdict — a
property the tests pin down rather than assume. Keep the display out of the
search loop: a validator stops meaning anything once it is the objective
(Goodhart), which is also why the search objective lives in ``scores.py``.
"""

from __future__ import annotations

import bisect
import math
from collections.abc import Mapping, Sequence

import numpy as np
from pydantic import BaseModel, Field, model_validator

from finrobot.engine.backtest.validation.overfitting import (
    DSRResult,
    MinTRLResult,
    PBOResult,
    RegimeResult,
    SPAResult,
)
from finrobot.engine.backtest.validation.stats import clamp, logit, norm_cdf, norm_ppf

__all__ = [
    "GATE_ORDER",
    "WEIGHTS",
    "GateMargin",
    "GateThresholds",
    "MarginCalibration",
    "MinervaReport",
    "default_calibration",
    "equicorrelation_matrix",
    "estimate_margin_sigma",
    "estimate_sigma_eff",
    "evaluate_gates",
    "gate_margins",
    "minerva_score",
]

#: Blend weights, in ``GATE_ORDER`` (arXiv:2608.23808v2 §2.11).
WEIGHTS: tuple[float, ...] = (0.35, 0.25, 0.20, 0.10, 0.10)

#: Gate order the weights and the effective-correlation matrix are expressed in.
GATE_ORDER: tuple[str, ...] = ("dsr", "pbo", "spa", "mintrl", "regime")

# Every gate's margin is zero at its threshold by construction. That anchoring is
# what makes the Seal independent of the (provisional) scale factors.


class GateThresholds(BaseModel):
    """Pass thresholds. Any change here re-labels the Seal, so it ships versioned."""

    dsr: float = Field(default=0.95, description="Pass iff deflated Sharpe >= this")
    pbo: float = Field(default=0.50, description="Pass iff PBO <= this")
    spa: float = Field(default=0.10, description="Pass iff SPA p-value <= this")
    regime: float = Field(default=0.60, description="Pass iff regime rho >= this")


#: The cross-gate correlation matrix the source paper publishes (Table 4), frozen
#: on its calibration population: winsorized-1% Pearson correlations of the
#: standardized margins, pairwise complete. Positive definite without projection,
#: smallest eigenvalue 0.21, and ``sqrt(w^T Sigma w) = 0.753`` with the paper's
#: weights. Shipped as the default because the paper reports it verbatim; the
#: alternative is to re-estimate it on FinRobot's own ledger with
#: :func:`estimate_sigma_eff` and bump the calibration version.
PAPER_SIGMA_EFF: list[list[float]] = [
    [1.00, 0.23, 0.32, 0.71, 0.25],
    [0.23, 1.00, 0.65, 0.48, 0.51],
    [0.32, 0.65, 1.00, 0.57, 0.60],
    [0.71, 0.48, 0.57, 1.00, 0.55],
    [0.25, 0.51, 0.60, 0.55, 1.00],
]


def equicorrelation_matrix(n: int, rho: float) -> list[list[float]]:
    """Equicorrelation matrix with unit diagonal and off-diagonal ``rho``.

    Kept as the simplest positive-definite alternative when a calibration
    population is unavailable: ``rho = 0.79`` happens to reproduce the smallest
    eigenvalue (0.21) of the paper's published matrix, which is why it was the
    placeholder default before that matrix was read off Table 4. The shipped
    default is now :data:`PAPER_SIGMA_EFF`.
    """
    if n < 1:
        raise ValueError(f"n must be positive, got {n!r}")
    if not -1.0 < rho < 1.0:
        raise ValueError(f"rho must lie in (-1, 1), got {rho!r}")
    return [[1.0 if i == j else rho for j in range(n)] for i in range(n)]


class MarginCalibration(BaseModel):
    """Scale factors, offset and reference matrix for the aggregate score."""

    version: str = Field(description="Calibration vintage; bump it when anything here changes")
    thresholds: GateThresholds = Field(default_factory=GateThresholds)
    sigma_dsr: float = Field(
        default=1.128,
        description="Scale of the pre-Phi DSR statistic: pooled IQR/1.349 of the paper's "
        "calibration margins (Table 3)",
    )
    sigma_pbo: float = Field(
        default=10.028,
        description="Clamp-inclusive dispersion of the PBO logit margin (Table 3). Large by "
        "design: it is what stops the degenerate PBO=0 point mass (14.4% of the paper's rows) "
        "from dominating the blend, whose clamp-free dispersion is only ~1.1",
    )
    sigma_spa: float = Field(
        default=6.013, description="Clamp-inclusive dispersion of the SPA logit margin (Table 3)"
    )
    sigma_regime: float = Field(
        default=1.161, description="Dispersion of the regime logit margin (Table 3)"
    )
    mintrl_scale: float = Field(default=0.2, description="sigma_T >= mintrl_scale * MinTRL")
    mintrl_min_sigma: float = Field(default=50.0, description="Absolute floor on sigma_T, in bars")
    offset: float = Field(default=0.5, description="Conservative offset c subtracted from S")
    fail_delta: float = Field(default=0.1, description="Failed records stay below 80 by this much")
    margin_clip: float = Field(
        default=12.0,
        description="Saturation guard: margins beyond ~1e-33 probability are indistinguishable",
    )
    r_star: float = Field(
        default=0.9997,
        description="Raw score of a theoretically perfect strategy (every gate at its physical "
        "limit), per the paper's display mapping",
    )
    sigma_eff: list[list[float]] = Field(
        default_factory=lambda: [list(row) for row in PAPER_SIGMA_EFF],
        description="Effective cross-gate correlation matrix (positive definite)",
    )
    fail_cdf: list[float] | None = Field(
        default=None,
        description="Sorted raw scores of a failing reference population; None means the uniform "
        "CDF. The paper stores this population as 81 quantile knots and interpolates; this "
        "implementation treats the list as a step (empirical) CDF, which is monotone and agrees "
        "to within one knot spacing",
    )

    @model_validator(mode="after")
    def _check_calibration(self) -> MarginCalibration:
        scales = {
            "sigma_dsr": self.sigma_dsr,
            "sigma_pbo": self.sigma_pbo,
            "sigma_spa": self.sigma_spa,
            "sigma_regime": self.sigma_regime,
            "mintrl_scale": self.mintrl_scale,
            "mintrl_min_sigma": self.mintrl_min_sigma,
            "margin_clip": self.margin_clip,
        }
        for name, value in scales.items():
            if not math.isfinite(value) or value <= 0.0:
                raise ValueError(f"{name} must be positive and finite, got {value!r}")
        if not 0.0 <= self.offset:
            raise ValueError(f"offset must be non-negative, got {self.offset!r}")
        if not 0.0 < self.fail_delta < 80.0:
            raise ValueError(f"fail_delta must lie in (0, 80), got {self.fail_delta!r}")
        r_zero = norm_cdf(-self.offset)
        if not r_zero < self.r_star <= 1.0:
            raise ValueError(
                f"r_star must exceed Phi(-offset) = {r_zero:.6f} and be <= 1, got {self.r_star!r}"
            )
        matrix = np.asarray(self.sigma_eff, dtype=float)
        if matrix.shape != (len(GATE_ORDER), len(GATE_ORDER)):
            raise ValueError(
                f"sigma_eff must be {len(GATE_ORDER)}x{len(GATE_ORDER)}, got {matrix.shape}"
            )
        if not np.allclose(matrix, matrix.T):
            raise ValueError("sigma_eff must be symmetric")
        if float(np.linalg.eigvalsh(matrix).min()) <= 0.0:
            raise ValueError("sigma_eff must be positive definite")
        if self.fail_cdf is not None and any(
            b < a for a, b in zip(self.fail_cdf, self.fail_cdf[1:], strict=False)
        ):
            raise ValueError("fail_cdf must be sorted ascending")
        return self


def default_calibration() -> MarginCalibration:
    """The shipped calibration — the source paper's own published constants.

    Every scale factor here is read off the paper (Table 3 for the dispersions,
    Table 4 for the correlation matrix, Eq. 9 for ``r_star``), so the display is
    calibrated the way the paper calibrated it rather than guessed. Two caveats
    remain, both versioned by ``version``: the constants were estimated on the
    paper's production population and may not describe FinRobot's, and the
    failing-population CDF (``fail_cdf``) is uniformly approximated here because
    that population is not available. Recalibrate with
    :func:`estimate_margin_sigma` and :func:`estimate_sigma_eff` on a real ledger,
    then bump ``version`` — scores are only comparable within one version.
    """
    return MarginCalibration(version="minerva-2608.23808v2-published")


class GateMargin(BaseModel):
    """One gate's margin, on a scale where 0 is the threshold and positive passes."""

    gate: str = Field(description="Gate name (see GATE_ORDER)")
    statistic: float | None = Field(description="Raw gate statistic; None when unavailable")
    threshold: float = Field(description="Pass threshold the margin is anchored at")
    margin: float = Field(description="Standardized margin; >= 0 iff the gate passed")
    passed: bool = Field(description="Gate verdict")
    active: bool = Field(
        default=True,
        description="False when the statistic could not be computed at all (fail closed); the "
        "blend then renormalizes its weights over the active gates",
    )
    detail: str = Field(default="", description="Human-readable note, e.g. a fail-closed reason")


class MinervaReport(BaseModel):
    """Aggregate robustness verdict for one backtest."""

    seal: bool = Field(description="True iff every gate passed")
    display: float | None = Field(description="0-100 display; None when the gates fail closed")
    s: float | None = Field(description="Combined inverse-normal statistic before the offset")
    margins: list[GateMargin] = Field(description="Per-gate margins, in GATE_ORDER")
    calibration_version: str = Field(description="Calibration vintage this score belongs to")
    verdict_consistent: bool = Field(description="True iff display >= 80 exactly when seal is True")
    warnings: list[str] = Field(description="Caveats: proxies, fail-closed reasons, saturation")

    def format_summary(self) -> str:
        """Human-readable block, mirroring the other result formatters."""
        head = "SEAL PASSED" if self.seal else "SEAL NOT PASSED"
        display = "n/a (fail closed)" if self.display is None else f"{self.display:.1f}"
        lines = [f"MinervaScore: {display}  [{head}]  calibration={self.calibration_version}"]
        if self.s is not None:
            lines.append(f"  combined S:   {self.s:+.4f}")
        for margin in self.margins:
            flag = "pass" if margin.passed else "FAIL"
            statistic = "n/a" if margin.statistic is None else f"{margin.statistic:+.4f}"
            note = f"  {margin.detail}" if margin.detail else ""
            lines.append(
                f"  {margin.gate:<7} {flag}  stat={statistic} thr={margin.threshold:.4f} "
                f"margin={margin.margin:+.3f}{note}"
            )
        lines.extend(f"  ! {warning}" for warning in self.warnings)
        return "\n".join(lines)


def gate_margins(
    *,
    dsr_pre_phi: float | None,
    pbo: float | None,
    spa_p: float | None,
    observed_bars: int | None,
    required_bars: float | None,
    regime_rho: float | None,
    calibration: MarginCalibration,
    mintrl_unbounded: bool = False,
) -> list[GateMargin]:
    """Convert the five raw statistics into signed, comparable margins.

    Each margin is standardized so that it is **exactly zero at the gate's
    threshold** and positive exactly when the gate passes. A missing statistic
    fails closed: verdict ``False``, margin at the negative clip, and the reason
    recorded in ``detail`` — a gate that could not be computed must never read as
    a pass.
    """
    thresholds = calibration.thresholds
    clip = calibration.margin_clip
    margins: list[GateMargin] = []

    if dsr_pre_phi is None:
        margins.append(
            GateMargin(
                gate="dsr",
                statistic=None,
                threshold=thresholds.dsr,
                margin=-clip,
                passed=False,
                active=False,
                detail="missing pre-Phi statistic (fail closed)",
            )
        )
    else:
        # The verdict is decided by the STORED statistic against Phi^-1(tau), not
        # by the round-tripped Phi(u): Phi(Phi^-1(0.95)) evaluates to
        # 0.9499999999999998, so comparing the displayed DSR against 0.95 would
        # fail a record that sits exactly on the threshold. Taking both the
        # verdict and the margin from the same comparison also makes
        # "margin >= 0 iff passed" exact, which the seal's consistency relies on.
        threshold_stat = norm_ppf(thresholds.dsr)
        margin = (dsr_pre_phi - threshold_stat) / calibration.sigma_dsr
        margins.append(
            GateMargin(
                gate="dsr",
                statistic=norm_cdf(dsr_pre_phi),
                threshold=thresholds.dsr,
                margin=clamp(margin, -clip, clip),
                passed=dsr_pre_phi >= threshold_stat,
            )
        )

    bounded = (
        ("pbo", pbo, thresholds.pbo, calibration.sigma_pbo, "lower"),
        ("spa", spa_p, thresholds.spa, calibration.sigma_spa, "lower"),
        ("regime", regime_rho, thresholds.regime, calibration.sigma_regime, "higher"),
    )
    for name, value, threshold, sigma, direction in bounded:
        if value is None:
            margins.append(
                GateMargin(
                    gate=name,
                    statistic=None,
                    threshold=threshold,
                    margin=-clip,
                    passed=False,
                    active=False,
                    detail=f"missing {name} statistic (fail closed)",
                )
            )
            continue
        # Sign convention: for a lower-is-better gate the margin grows as the
        # statistic falls; for a higher-is-better gate as it rises. Either way it
        # is zero exactly at the threshold.
        if direction == "lower":
            margin = (logit(threshold) - logit(value)) / sigma
            passed = value <= threshold
        else:
            margin = (logit(value) - logit(threshold)) / sigma
            passed = value >= threshold
        margins.append(
            GateMargin(
                gate=name,
                statistic=value,
                threshold=threshold,
                margin=clamp(margin, -clip, clip),
                passed=passed,
            )
        )

    if observed_bars is None or (required_bars is None and not mintrl_unbounded):
        margins.append(
            GateMargin(
                gate="mintrl",
                statistic=None,
                threshold=0.0,
                margin=-clip,
                passed=False,
                active=False,
                detail="missing MinTRL (fail closed)",
            )
        )
    elif required_bars is None:
        # Eq. 6's limit: tanh((T - MinTRL) / sigma_T) -> -1 as MinTRL -> inf, which
        # is what an observed Sharpe at or below its benchmark implies — no finite
        # track length would establish significance. The gate stays active (it has
        # a margin) but cannot pass, which is the honest reading.
        margins.append(
            GateMargin(
                gate="mintrl",
                statistic=None,
                threshold=0.0,
                margin=-1.0,
                passed=False,
                detail="unbounded MinTRL: no finite track length would suffice",
            )
        )
    else:
        sigma_t = max(calibration.mintrl_scale * required_bars, calibration.mintrl_min_sigma)
        margins.append(
            GateMargin(
                gate="mintrl",
                statistic=float(observed_bars),
                threshold=required_bars,
                margin=math.tanh((observed_bars - required_bars) / sigma_t),
                passed=observed_bars >= required_bars,
            )
        )

    by_name = {margin.gate: margin for margin in margins}
    return [by_name[gate] for gate in GATE_ORDER]


def _fail_percentile(r: float, calibration: MarginCalibration) -> float:
    """Empirical CDF of the failing population's ``r`` (uniform when uncalibrated)."""
    if calibration.fail_cdf is None:
        return clamp(r, 0.0, 1.0)
    cdf = calibration.fail_cdf
    if not cdf:
        return 0.0
    return clamp(bisect.bisect_right(cdf, r) / len(cdf), 0.0, 1.0)


def minerva_score(
    *,
    margins: Sequence[GateMargin],
    calibration: MarginCalibration | None = None,
    fail_closed_reason: str | None = None,
) -> MinervaReport:
    """Blend gate margins into a verdict-consistent display.

    ``S = w^T z / sqrt(w^T Sigma_eff w)``, then ``r = Phi(S - c)``. A sealed
    record maps into ``[80, 100]`` from ``r_0 = Phi(-c)``, so a marginal pass
    (``S = 0``) displays exactly 80; a failed record is capped at ``80 - delta``.
    Weights are renormalized over the gates whose statistic was computable, and
    the display is floored and capped at 100, both following the source paper.
    Because every margin is non-negative exactly when its gate passes, a seal
    implies ``S >= 0``, hence ``r >= r_0``, hence ``display >= 80`` — the
    invariant is structural. It is re-checked here anyway, so a custom calibration
    that broke it would raise instead of publishing a contradictory score.
    """
    config = calibration or default_calibration()
    ordered = {margin.gate: margin for margin in margins}
    missing = [gate for gate in GATE_ORDER if gate not in ordered]
    if missing:
        raise ValueError(f"margins missing gates {missing}; expected all of {list(GATE_ORDER)}")

    warnings: list[str] = [
        margin.detail for margin in margins if margin.detail and not margin.passed
    ]
    seal = all(margin.passed for margin in margins)

    if fail_closed_reason is not None:
        return MinervaReport(
            seal=False,
            display=None,
            s=None,
            margins=[ordered[gate] for gate in GATE_ORDER],
            calibration_version=config.version,
            verdict_consistent=True,
            warnings=[fail_closed_reason, *warnings],
        )

    active = [gate for gate in GATE_ORDER if ordered[gate].active]
    if not active:
        return MinervaReport(
            seal=False,
            display=None,
            s=None,
            margins=[ordered[gate] for gate in GATE_ORDER],
            calibration_version=config.version,
            verdict_consistent=True,
            warnings=["no gate statistic is available; no score can be produced", *warnings],
        )

    # Weights are renormalized over the active gates (the paper's rule when a gate
    # is unavailable). A sealed record always has all five active — an inactive
    # gate cannot pass — so the pass branch below is unaffected.
    indices = [GATE_ORDER.index(gate) for gate in active]
    weights = np.asarray([WEIGHTS[index] for index in indices], dtype=float)
    weights = weights / float(weights.sum())
    correlation = np.asarray(config.sigma_eff, dtype=float)[np.ix_(indices, indices)]
    vector = np.asarray([ordered[gate].margin for gate in active], dtype=float)
    denominator = float(math.sqrt(float(weights @ correlation @ weights)))
    if denominator <= 0.0:
        raise ValueError("w^T Sigma_eff w is not positive; the calibration matrix is degenerate")
    combined = float(weights @ vector) / denominator
    if len(active) < len(GATE_ORDER):
        warnings.append(
            f"S is computed over {len(active)} of {len(GATE_ORDER)} gates with renormalized "
            "weights, so it is not comparable with a full-gate S"
        )

    r = norm_cdf(combined - config.offset)
    if seal:
        r_zero = norm_cdf(-config.offset)
        # The floor exists for floating point, not for policy: r >= r_zero holds
        # analytically for a sealed record (every margin >= 0 => S >= 0), and the
        # seal must not lose its exact 80 to a 1-ULP rounding in norm_cdf.
        raw = max(80.0 + 20.0 * (r - r_zero) / (config.r_star - r_zero), 80.0)
    else:
        raw = min(80.0 * _fail_percentile(r, config), 80.0 - config.fail_delta)
    display = float(math.floor(min(raw, 100.0)))

    consistent = seal == (display >= 80.0)
    if not consistent:
        raise ValueError(
            f"verdict-consistency violated: seal={seal} but display={display:.4f}; "
            "the calibration's offset/r_star combination is invalid"
        )
    if abs(combined) > config.margin_clip:
        warnings.append(
            f"combined statistic is saturated (|S|={abs(combined):.1f}); at least one gate margin "
            "was clipped, so the display understates how far the record is from the boundary"
        )
    return MinervaReport(
        seal=seal,
        display=display,
        s=combined,
        margins=[ordered[gate] for gate in GATE_ORDER],
        calibration_version=config.version,
        verdict_consistent=consistent,
        warnings=warnings,
    )


def evaluate_gates(
    *,
    dsr: DSRResult | None,
    pbo: PBOResult | None,
    spa: SPAResult | None,
    mintrl: MinTRLResult | None,
    regime: RegimeResult | None,
    calibration: MarginCalibration | None = None,
) -> MinervaReport:
    """Gate result objects in, one report out — with the paper's fail-closed rule.

    The aggregate needs the *pre-Phi* DSR statistic, not the DSR value: ``Phi(u)``
    saturates at 0 for most real records (60-95% in the source paper) and cannot be
    inverted back into a usable margin. So a missing ``DSRResult`` yields a report
    with **no display** and a warning, never a score computed from a saturated
    value.
    """
    config = calibration or default_calibration()
    if dsr is None:
        return minerva_score(
            margins=gate_margins(
                dsr_pre_phi=None,
                pbo=pbo.pbo if pbo else None,
                spa_p=spa.p_value if spa else None,
                observed_bars=mintrl.observed_bars if mintrl else None,
                required_bars=mintrl.required_bars if mintrl else None,
                regime_rho=regime.rho if regime else None,
                calibration=config,
                mintrl_unbounded=bool(mintrl is not None and mintrl.unbounded),
            ),
            calibration=config,
            fail_closed_reason=(
                "fail closed: no pre-Phi DSR statistic stored, and Phi(u) cannot be inverted "
                "(arXiv:2608.23808v2 §2.11)"
            ),
        )

    margins = gate_margins(
        dsr_pre_phi=dsr.pre_phi_statistic,
        pbo=pbo.pbo if pbo else None,
        spa_p=spa.p_value if spa else None,
        observed_bars=mintrl.observed_bars if mintrl else None,
        required_bars=mintrl.required_bars if mintrl else None,
        regime_rho=regime.rho if regime else None,
        calibration=config,
        mintrl_unbounded=bool(mintrl is not None and mintrl.unbounded),
    )
    report = minerva_score(margins=margins, calibration=config)
    extra: list[str] = []
    if pbo is not None and pbo.proxy:
        extra.append("PBO came from the fold-wise proxy, not CSCV; treat the margin as indicative")
    if pbo is not None and pbo.degenerate:
        extra.append(
            "CSCV was degenerate (PBO is a point mass); its dispersion was floored, not measured"
        )
    if spa is not None:
        extra.extend(spa.warnings)
    if mintrl is not None and mintrl.unbounded:
        extra.append("MinTRL is unbounded: the observed Sharpe does not exceed its benchmark")
    if dsr.warnings:
        extra.extend(dsr.warnings)
    return report.model_copy(update={"warnings": [*report.warnings, *extra]})


def estimate_sigma_eff(
    margin_vectors: Sequence[Sequence[float]] | np.ndarray, *, eigenvalue_floor: float = 0.05
) -> list[list[float]]:
    """Estimate the cross-gate correlation matrix from a population of margins.

    Provide ``(n_records, 5)`` margins in ``GATE_ORDER``; returns the correlation
    matrix with its eigenvalues floored at ``eigenvalue_floor`` so the result is
    positive definite and safe as a ``sigma_eff`` (measured correlations can be
    near-singular, and ``w^T Sigma w`` must stay strictly positive).
    """
    matrix = np.asarray(margin_vectors, dtype=float)
    if matrix.ndim != 2 or matrix.shape[1] != len(GATE_ORDER):
        raise ValueError(f"expected an (n_records, {len(GATE_ORDER)}) matrix, got {matrix.shape}")
    if matrix.shape[0] < 3:
        raise ValueError("at least 3 records are needed to estimate a correlation matrix")
    if not np.isfinite(matrix).all():
        raise ValueError("margin_vectors contains non-finite values")
    correlations = np.corrcoef(matrix, rowvar=False)
    correlations = np.nan_to_num(correlations, nan=0.0)
    np.fill_diagonal(correlations, 1.0)
    eigenvalues, eigenvectors = np.linalg.eigh(correlations)
    floored = np.clip(eigenvalues, eigenvalue_floor, None)
    rebuilt = eigenvectors @ np.diag(floored) @ eigenvectors.T
    scale = np.sqrt(np.diag(rebuilt))
    normalized = rebuilt / np.outer(scale, scale)
    np.fill_diagonal(normalized, 1.0)
    return [[float(value) for value in row] for row in normalized]


def estimate_margin_sigma(
    margins_by_gate: Mapping[str, Sequence[float]], *, floor: float = 0.1
) -> dict[str, float]:
    """Per-gate scale factors from a population of margins (recalibration helper).

    Returns the standard deviation of each gate's margin, floored at ``floor`` so
    a gate that happened to be constant in the sample cannot produce a zero scale
    (which would divide to infinity downstream). Feed the result into
    :class:`MarginCalibration` and bump its ``version``.
    """
    if floor <= 0.0:
        raise ValueError(f"floor must be positive, got {floor!r}")
    out: dict[str, float] = {}
    for gate in GATE_ORDER:
        values = list(margins_by_gate.get(gate, ()))
        if len(values) < 3:
            raise ValueError(f"gate {gate!r} needs at least 3 margins to estimate a scale")
        spread = float(np.asarray(values, dtype=float).std(ddof=1))
        out[gate] = max(spread, floor)
    return out
