"""Validation report that structurally refuses to omit the ZI arm (§4, §5.7).

The document's rule is blunt: a zero-intelligence market already reproduces six
univariate stylized facts without any history, so "our model reproduces stylized
facts" is only informative relative to a ZI baseline and to real data on the
*same* moments. This module enforces that rule in code rather than by
convention — :func:`validation_report` raises unless a ZI arm is supplied beside
the simulated series, so a simulated result can never be reported bare.

The report carries, for one shared moment set: each arm's per-moment coverage of
the real sampling band, every group's excess kurtosis, and the raw moment values
for real, simulated and ZI side by side.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from finrobot.engine.simulation.stylized_facts import (
    CoverageMatrix,
    Moment,
    bootstrap_paths,
    coverage_matrix,
    default_moments,
    evaluate_moment,
)

__all__ = ["ValidationReport", "validation_report"]

#: Coverage is estimated over this many block-bootstrap resamples of each arm
#: (§2.2 "resample simulated paths"), with this block length and internal seed.
_REPORT_PATHS = 100
_REPORT_BLOCK = 25
_REPORT_SEED = 12345


class ValidationReport(BaseModel):
    """A simulation result *with* its ZI arm: coverage, kurtosis and moments."""

    model_config = ConfigDict(frozen=True)

    moments: list[str] = Field(description="Moment names shared by every group")
    coverage: dict[str, CoverageMatrix] = Field(description="Band coverage vs real, by arm")
    kurtosis: dict[str, float] = Field(description="Excess kurtosis by group")
    moment_values: dict[str, dict[str, float]] = Field(description="group -> moment -> value")
    alpha: float = Field(description="Band confidence level")
    zi_arm_present: bool = Field(default=True, description="Hard-coded True; the guard is enforced")


def _as_series(values: Sequence[float] | np.ndarray, *, name: str) -> np.ndarray:
    series: np.ndarray = np.asarray(values, dtype=np.float64).reshape(-1)
    if series.size < 2:
        raise ValueError(f"{name} must have at least two points")
    if not bool(np.all(np.isfinite(series))):
        raise ValueError(f"{name} contains non-finite values")
    return series


def _excess_kurtosis(series: np.ndarray) -> float:
    """Excess (Fisher) kurtosis; 0.0 for a degenerate zero-variance series."""
    centered: np.ndarray = series - series.mean()
    variance = float(np.mean(centered * centered))
    if variance <= 0.0:
        return 0.0
    fourth = float(np.mean(centered**4))
    return fourth / (variance * variance) - 3.0


def validation_report(
    real_series: Sequence[float] | np.ndarray,
    simulated_series: Sequence[float] | np.ndarray,
    *,
    zi_series: Sequence[float] | np.ndarray | None = None,
    moments: Sequence[Moment] | None = None,
    alpha: float = 0.95,
) -> ValidationReport:
    """Build the coverage/kurtosis report, refusing to omit the ZI arm.

    A simulated series is only interpretable against the ZI null (§4, "Report
    the null"), so passing ``simulated_series`` without ``zi_series`` raises —
    the rule is structural, not a docstring convention. The real, simulated and
    ZI groups are all evaluated on the *same* moments.
    """
    if zi_series is None:
        raise ValueError(
            "a simulated series cannot be reported without the ZI arm beside it "
            "(agent-based-market-simulation.md §4/§5.7)"
        )
    if not 0.0 < alpha < 1.0:
        raise ValueError(f"alpha must lie in (0, 1), got {alpha}")
    moment_set = list(moments) if moments is not None else default_moments()
    if not moment_set:
        raise ValueError("moments must be non-empty")

    real = _as_series(real_series, name="real_series")
    simulated = _as_series(simulated_series, name="simulated_series")
    zi = _as_series(zi_series, name="zi_series")

    simulated_paths = bootstrap_paths(
        simulated, n_paths=_REPORT_PATHS, n_block=_REPORT_BLOCK, seed=_REPORT_SEED
    )
    zi_paths = bootstrap_paths(
        zi, n_paths=_REPORT_PATHS, n_block=_REPORT_BLOCK, seed=_REPORT_SEED + 1
    )

    coverage = {
        "simulated": coverage_matrix(real, simulated_paths, moments=moment_set, alpha=alpha),
        "zi": coverage_matrix(real, zi_paths, moments=moment_set, alpha=alpha),
    }

    groups: dict[str, np.ndarray] = {"real": real, "simulated": simulated, "zi": zi}
    moment_values: dict[str, dict[str, float]] = {
        group: {m.name: evaluate_moment(series, m) for m in moment_set}
        for group, series in groups.items()
    }
    kurtosis = {group: _excess_kurtosis(series) for group, series in groups.items()}

    return ValidationReport(
        moments=[m.name for m in moment_set],
        coverage=coverage,
        kurtosis=kurtosis,
        moment_values=moment_values,
        alpha=alpha,
        zi_arm_present=True,
    )
