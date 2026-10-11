"""Tests for the backtest-validation return-series statistics.

Every estimator is pinned against a hand-computed value or an independent
recomputation from the module's own building blocks, and every documented
``ValueError`` path (domain, length, zero variance, inverted bounds,
non-finite) is exercised.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence

import pytest

from finrobot.engine.backtest.validation import stats


class TestNormalDistribution:
    def test_cdf_exact_and_known(self) -> None:
        assert stats.norm_cdf(0.0) == 0.5
        assert stats.norm_cdf(1.96) == pytest.approx(0.975, abs=1e-4)

    @pytest.mark.parametrize("x", [0.1, 0.5, 1.0, 1.96, 2.5, 4.0])
    def test_cdf_symmetry(self, x: float) -> None:
        assert stats.norm_cdf(-x) == pytest.approx(1.0 - stats.norm_cdf(x), abs=1e-15)

    def test_ppf_known_values(self) -> None:
        assert stats.norm_ppf(0.95) == pytest.approx(1.6448536269514715, abs=1e-15)
        assert stats.norm_ppf(0.5) == 0.0

    @pytest.mark.parametrize(
        "p",
        [0.001, 0.025, 0.5, 0.95, 1 - 1 / 5000, 1 - 1 / (5000 * math.e), 1e-9, 1 - 1e-9],
    )
    def test_ppf_round_trip(self, p: float) -> None:
        assert stats.norm_cdf(stats.norm_ppf(p)) == pytest.approx(p, abs=1e-12)

    @pytest.mark.parametrize("p", [0.0, 1.0, -0.1, 1.1, float("nan"), float("inf")])
    def test_ppf_rejects_out_of_domain(self, p: float) -> None:
        with pytest.raises(ValueError, match=r"p in \(0, 1\)"):
            stats.norm_ppf(p)


class TestScalarHelpers:
    def test_clamp_both_directions(self) -> None:
        assert stats.clamp(5.0, 0.0, 10.0) == 5.0
        assert stats.clamp(-5.0, 0.0, 10.0) == 0.0
        assert stats.clamp(15.0, 0.0, 10.0) == 10.0
        with pytest.raises(ValueError, match="inverted"):
            stats.clamp(0.0, 10.0, 0.0)

    def test_logit_zero_and_sign(self) -> None:
        assert stats.logit(0.5) == 0.0
        assert stats.logit(0.75) == pytest.approx(math.log(3.0))
        assert stats.logit(0.75) > 0.0
        assert stats.logit(0.25) < 0.0

    def test_logit_epsilon_clamp_keeps_degenerate_finite(self) -> None:
        assert math.isfinite(stats.logit(0.0))
        assert math.isfinite(stats.logit(1.0))
        assert stats.logit(0.0) == pytest.approx(math.log(stats.EPS / (1.0 - stats.EPS)))

    @pytest.mark.parametrize("eps", [0.0, 0.5, -0.1, 0.6])
    def test_logit_bad_epsilon_raises(self, eps: float) -> None:
        with pytest.raises(ValueError, match=r"\(0, 0.5\)"):
            stats.logit(0.5, eps=eps)

    def test_mean_and_std_ddof_one(self) -> None:
        assert stats.mean([1.0, 2.0, 3.0, 4.0]) == pytest.approx(2.5)
        assert stats.std([1.0, 2.0, 3.0, 4.0]) == pytest.approx(1.2909944487358056)

    def test_mean_empty_and_std_underpowered_raise(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            stats.mean([])
        with pytest.raises(ValueError, match="ddof"):
            stats.std([])
        with pytest.raises(ValueError, match="ddof"):
            stats.std([1.0])


class TestMoments:
    def test_symmetric_and_normal_ish(self) -> None:
        sample = [-8.0, -2.0, -1.0, 0.0, 1.0, 2.0, 8.0]
        assert stats.skewness(sample) == 0.0
        assert stats.kurtosis(sample) == pytest.approx(3.0236294896030245)
        assert stats.kurtosis(sample) == pytest.approx(3.0, abs=0.1)

    def test_excess_is_raw_minus_three(self) -> None:
        sample = [-2.0, -1.0, 0.0, 1.0, 5.0, 7.0]
        assert stats.kurtosis(sample, excess=True) == pytest.approx(stats.kurtosis(sample) - 3.0)

    def test_skewness_kurtosis_errors(self) -> None:
        with pytest.raises(ValueError, match="at least 3"):
            stats.skewness([1.0, 2.0])
        with pytest.raises(ValueError, match="at least 4"):
            stats.kurtosis([1.0, 2.0, 3.0])
        with pytest.raises(ValueError, match="zero-variance"):
            stats.skewness([2.0, 2.0, 2.0])
        with pytest.raises(ValueError, match="zero-variance"):
            stats.kurtosis([2.0, 2.0, 2.0, 2.0])

    def test_downside_deviation_over_all_observations(self) -> None:
        returns = [0.02, -0.01, 0.03, -0.04]
        value = stats.downside_deviation(returns)
        assert value == pytest.approx(0.020615528128088305)
        # NOT the loss-only denominator, which is materially larger.
        assert value != pytest.approx(math.sqrt((0.01**2 + 0.04**2) / 2))
        assert value == pytest.approx(math.sqrt((0.01**2 + 0.04**2) / 4))
        with pytest.raises(ValueError, match="empty"):
            stats.downside_deviation([])


class TestSharpeAndMertens:
    def test_annualized_is_sqrt_scaling(self) -> None:
        returns = [0.01, 0.02, -0.01, 0.03, 0.0]
        base = stats.sharpe_ratio(returns)
        assert stats.annualized_sharpe(returns, periods_per_year=252) == pytest.approx(
            base * math.sqrt(252)
        )
        assert stats.annualized_sharpe(returns, periods_per_year=1) == pytest.approx(base)

    def test_sharpe_errors(self) -> None:
        with pytest.raises(ValueError, match="at least 2"):
            stats.sharpe_ratio([0.01])
        with pytest.raises(ValueError, match="zero-variance"):
            stats.sharpe_ratio([0.01, 0.01])
        for periods in (0, -1):
            with pytest.raises(ValueError, match="periods_per_year"):
                stats.annualized_sharpe([0.01, 0.02], periods_per_year=periods)

    def test_mertens_composition_cross_check(self) -> None:
        returns = [0.02, -0.01, 0.03, -0.04, 0.015, -0.005, 0.01]
        sr = stats.sharpe_ratio(returns)
        expected = (
            1.0 - stats.skewness(returns) * sr + (stats.kurtosis(returns) - 1.0) / 4.0 * sr * sr
        )
        assert stats.mertens_variance_factor(returns) == pytest.approx(expected)

    def test_mertens_floored_at_eps_for_violent_skew(self) -> None:
        returns = [8.0] * 4 + [3.0] * 11
        sr = stats.sharpe_ratio(returns)
        raw = 1.0 - stats.skewness(returns) * sr + (stats.kurtosis(returns) - 1.0) / 4.0 * sr * sr
        assert raw < stats.EPS
        assert stats.mertens_variance_factor(returns) == stats.EPS


class TestCurveMetrics:
    def test_equity_curve_r2_line_and_constant(self) -> None:
        assert stats.equity_curve_r2([1.0, 2.0, 3.0, 4.0]) == 1.0
        assert stats.equity_curve_r2([5.0, 5.0, 5.0, 5.0]) == 1.0

    def test_equity_curve_r2_flat_then_jump_is_penalized(self) -> None:
        r2 = stats.equity_curve_r2([1.0, 1.0, 1.0, 1.0, 2.0])
        assert r2 == pytest.approx(0.5000000000000002)
        assert r2 < 0.9

    def test_max_drawdown(self) -> None:
        assert stats.max_drawdown([100.0, 120.0, 90.0, 110.0]) == pytest.approx(0.25)
        assert stats.max_drawdown([1.0, 2.0, 3.0, 4.0]) == 0.0

    def test_curve_length_errors(self) -> None:
        with pytest.raises(ValueError, match="at least 3"):
            stats.equity_curve_r2([1.0, 2.0])
        with pytest.raises(ValueError, match="at least 2"):
            stats.max_drawdown([1.0])


class TestRankAndCosts:
    def test_spearman_monotone_both_directions(self) -> None:
        up = stats.spearman_rho([1.0, 2.0, 3.0, 4.0], [10.0, 20.0, 30.0, 40.0])
        down = stats.spearman_rho([1.0, 2.0, 3.0, 4.0], [40.0, 30.0, 20.0, 10.0])
        assert up == pytest.approx(1.0)
        assert down == pytest.approx(-1.0)

    def test_spearman_hand_computed_tie_case(self) -> None:
        # mid-ranks [1, 2.5, 2.5, 4] vs [1, 2, 3, 4]: cov=4.5, sx=sqrt(4.5), sy=sqrt(5)
        assert stats.spearman_rho([1.0, 2.0, 2.0, 3.0], [1.0, 2.0, 3.0, 4.0]) == pytest.approx(
            4.5 / math.sqrt(4.5 * 5.0)
        )

    def test_spearman_errors(self) -> None:
        with pytest.raises(ValueError, match="length mismatch"):
            stats.spearman_rho([1.0, 2.0, 3.0], [1.0, 2.0])
        with pytest.raises(ValueError, match="at least 2"):
            stats.spearman_rho([1.0], [2.0])
        with pytest.raises(ValueError, match="constant"):
            stats.spearman_rho([1.0, 1.0, 1.0], [1.0, 2.0, 3.0])

    def test_net_of_costs_round_trip(self) -> None:
        gross = [0.01, 0.02, -0.005]
        net = stats.net_of_costs(gross, per_side_bps=7.5, turnover=1.0)
        assert net == pytest.approx([x - 0.0015 for x in gross])
        assert net[0] == pytest.approx(0.0085)
        assert stats.net_of_costs([0.01, -0.02], per_side_bps=0.0) == [0.01, -0.02]

    def test_net_of_costs_negative_inputs_raise(self) -> None:
        with pytest.raises(ValueError, match="non-negative"):
            stats.net_of_costs([0.01], per_side_bps=-1.0)
        with pytest.raises(ValueError, match="non-negative"):
            stats.net_of_costs([0.01], per_side_bps=1.0, turnover=-0.5)


class TestNonFiniteRejection:
    @pytest.mark.parametrize(
        "estimator",
        [
            stats.mean,
            stats.std,
            stats.skewness,
            stats.kurtosis,
            stats.downside_deviation,
            stats.sharpe_ratio,
            stats.mertens_variance_factor,
            stats.equity_curve_r2,
            stats.max_drawdown,
        ],
    )
    @pytest.mark.parametrize("bad", [float("nan"), float("inf")])
    def test_estimator_rejects_non_finite(
        self, estimator: Callable[[Sequence[float]], object], bad: float
    ) -> None:
        with pytest.raises(ValueError, match="non-finite"):
            estimator([0.1, 0.2, bad, 0.3, 0.4])

    @pytest.mark.parametrize("bad", [float("nan"), float("inf")])
    def test_other_estimators_reject_non_finite(self, bad: float) -> None:
        series = [0.1, 0.2, bad, 0.3]
        with pytest.raises(ValueError, match="non-finite"):
            stats.annualized_sharpe(series)
        with pytest.raises(ValueError, match="non-finite"):
            stats.net_of_costs(series, per_side_bps=1.0)
        with pytest.raises(ValueError, match="non-finite"):
            stats.spearman_rho(series, [1.0, 2.0, 3.0, 4.0])
        with pytest.raises(ValueError, match="non-finite"):
            stats.spearman_rho([1.0, 2.0, 3.0, 4.0], series)
