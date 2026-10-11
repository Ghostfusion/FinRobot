"""Tests for GT-Score and the generalization ratio (``validation.scores``).

The direction convention is pinned explicitly: the paper's objective is a
*minimized* loss, so a profitable strategy has a negative ``score`` and a
positive ``maximization_value()``. A sign regression must fail loudly here.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

import pytest

from finrobot.engine.backtest.validation import stats
from finrobot.engine.backtest.validation.scores import (
    INSUFFICIENT_SAMPLE_PENALTY,
    generalization_ratio,
    gt_score,
    stabilized_period_length,
)

_PROFITABLE = [0.02, 0.03, 0.01, 0.025, 0.015]


def _expected_standard(returns: Sequence[float]) -> float:
    """Recompute the standard branch straight from the documented formula."""
    mu = stats.mean(returns)
    sigma = stats.std(returns)
    z = mu / (sigma / math.sqrt(len(returns)))
    curve = [1.0]
    for value in returns:
        curve.append(curve[-1] * (1.0 + value))
    r2 = stats.equity_curve_r2(curve)
    sigma_d = stats.downside_deviation(returns)
    return -mu * math.log(z) * r2 / (sigma_d + 1e-6)


class TestGtScoreBranches:
    def test_standard_branch_is_negative(self) -> None:
        result = gt_score(_PROFITABLE, n_min=1)
        assert result.branch == "standard"
        assert result.z > 1.0
        assert result.score < 0.0
        assert result.score == pytest.approx(_expected_standard(_PROFITABLE))

    def test_marginal_branch(self) -> None:
        result = gt_score([0.02] * 4 + [-0.01] * 6, n_min=1)
        assert result.branch == "marginal"
        assert 0.0 < result.z <= 1.0
        assert result.score == pytest.approx(100.0 * (1.0 - math.exp(-abs(result.z - 1.0))))

    def test_underperform_branch(self) -> None:
        result = gt_score([0.01] * 4 + [-0.02] * 6, n_min=1)
        assert result.branch == "underperform"
        assert result.z <= 0.0
        assert result.score == pytest.approx(100.0 + 100.0 * (1.0 - math.exp(-abs(result.z - 1.0))))

    def test_z_exactly_one_is_marginal(self) -> None:
        result = gt_score([4.0, 0.0, 0.0, 0.0], n_min=1)
        assert result.z == 1.0
        assert result.branch == "marginal"
        assert result.score == 0.0

    def test_z_exactly_zero_is_underperform(self) -> None:
        result = gt_score([0.02, -0.02, 0.03, -0.03], n_min=1)
        assert result.z == 0.0
        assert result.branch == "underperform"


class TestMinimizationContract:
    def test_profitable_beats_underperforming_under_both_conventions(self) -> None:
        underperforming = gt_score([0.01] * 4 + [-0.02] * 6, n_min=1)
        profitable = gt_score(_PROFITABLE, n_min=1)
        assert profitable.direction == "minimize"
        assert profitable.score < underperforming.score
        assert profitable.maximization_value() > underperforming.maximization_value()


class TestNMin:
    def test_short_series_is_penalized(self) -> None:
        result = gt_score(_PROFITABLE, n_min=50)
        assert result.branch == "insufficient_sample"
        assert result.score >= INSUFFICIENT_SAMPLE_PENALTY

    def test_sufficient_series_is_not_penalized(self) -> None:
        assert gt_score(_PROFITABLE, n_min=len(_PROFITABLE)).branch != "insufficient_sample"

    def test_invalid_n_min_and_empty_raise(self) -> None:
        with pytest.raises(ValueError, match="n_min"):
            gt_score(_PROFITABLE, n_min=0)
        with pytest.raises(ValueError, match="at least one observation"):
            gt_score([], n_min=1)


class TestBenchmark:
    def test_omitted_benchmark_is_zero_and_flagged(self) -> None:
        result = gt_score(_PROFITABLE, n_min=1)
        assert result.benchmark_provided is False
        assert result.benchmark_mean == 0.0

    def test_supplied_benchmark_shifts_z(self) -> None:
        benchmark = [0.05, 0.05, 0.05, 0.05, 0.05]
        with_bench = gt_score(_PROFITABLE, benchmark_returns=benchmark, n_min=1)
        without = gt_score(_PROFITABLE, n_min=1)
        assert with_bench.benchmark_provided is True
        assert with_bench.benchmark_mean == pytest.approx(0.05)
        assert with_bench.z < without.z
        expected_z = (stats.mean(_PROFITABLE) - 0.05) / (
            stats.std(_PROFITABLE) / math.sqrt(len(_PROFITABLE))
        )
        assert with_bench.z == pytest.approx(expected_z)

    def test_mismatched_benchmark_raises(self) -> None:
        with pytest.raises(ValueError, match="aligned"):
            gt_score(_PROFITABLE, benchmark_returns=[0.01, 0.02], n_min=1)


class TestEquityCurveInput:
    def test_supplied_curve_is_used(self) -> None:
        returns = [0.0, 0.0, 0.5]
        supplied = [1.0, 2.0, 3.0, 4.0]
        result = gt_score(returns, equity_curve=supplied, n_min=1)
        assert result.equity_r2 == pytest.approx(stats.equity_curve_r2(supplied))
        compounded = [1.0, 1.0, 1.0, 1.5]
        assert result.equity_r2 != pytest.approx(stats.equity_curve_r2(compounded))

    def test_wrong_length_raises(self) -> None:
        with pytest.raises(ValueError, match="equity_curve must have"):
            gt_score(_PROFITABLE, equity_curve=[1.0, 2.0], n_min=1)


class TestStabilizedPeriodLength:
    def test_short_series_returns_fallback(self) -> None:
        assert stabilized_period_length([1.0] * 5) == 50
        assert stabilized_period_length([1.0] * 5, fallback=7) == 7

    def test_returns_value_from_default_ladder(self) -> None:
        data = [float(i) for i in range(40)]
        assert stabilized_period_length(data, tolerance=10.0) in range(5, len(data) // 4 + 1)

    def test_explicit_candidates_respected(self) -> None:
        data = [float(i) for i in range(40)]
        result = stabilized_period_length(data, candidates=[3, 4, 5], tolerance=10.0)
        assert result == 4
        assert result in (3, 4, 5)

    def test_deterministic(self) -> None:
        data = [float(i) for i in range(40)]
        assert stabilized_period_length(data, tolerance=10.0) == stabilized_period_length(
            data, tolerance=10.0
        )


class TestGeneralizationRatio:
    def test_exact_ratio(self) -> None:
        assert generalization_ratio(0.15, 0.30) == pytest.approx(0.5)

    @pytest.mark.parametrize("training", [0.0, -0.1])
    def test_non_positive_training_raises(self, training: float) -> None:
        with pytest.raises(ValueError, match="non-positive training return"):
            generalization_ratio(0.1, training)

    @pytest.mark.parametrize(
        ("validation", "training"),
        [(float("nan"), 0.1), (0.1, float("nan")), (float("inf"), 0.1), (0.1, float("inf"))],
    )
    def test_non_finite_raises(self, validation: float, training: float) -> None:
        with pytest.raises(ValueError, match="finite"):
            generalization_ratio(validation, training)


class TestFormatSummary:
    def test_contains_score_direction_and_branch(self) -> None:
        result = gt_score(_PROFITABLE, n_min=1)
        summary = result.format_summary()
        assert isinstance(summary, str)
        assert f"{result.score:.6f}" in summary
        assert "minimize" in summary
        assert result.branch in summary
