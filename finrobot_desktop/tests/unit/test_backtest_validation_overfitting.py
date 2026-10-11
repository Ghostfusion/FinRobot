"""Tests for the overfitting gates.

Covers the §4 'how to test an implementation is sound' list of
``strategies/qfin-st/backtest-methodology.md`` where it applies to the individual
gates: determinism, sensitivity to search size (item 4), and the flat-trend
property of the null benchmark as history grows (item 5). The aggregate-level
items (verdict consistency, rank stability, synthetic ground truth) live in
``test_backtest_validation_minerva.py``.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from finrobot.engine.backtest.validation import stats
from finrobot.engine.backtest.validation.overfitting import (
    PBOResult,
    agent_acceptance_test,
    deflated_sharpe_ratio,
    effective_trial_count,
    min_track_record_length,
    pbo_cscv,
    pbo_fold_proxy,
    regime_stability,
    spa_test,
)

PERIODS_PER_YEAR = 252


def _noise_matrix(
    *,
    n_observations: int = PERIODS_PER_YEAR,
    n_trials: int = 20,
    seed: int = 42,
    vol: float = 0.01,
) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.normal(0.0, vol, size=(n_observations, n_trials))


def _with_edge(matrix: np.ndarray, *, column: int, annualized_sharpe: float) -> np.ndarray:
    """Shift one column's mean so it carries the requested annualized Sharpe."""
    out = matrix.copy()
    out[:, column] += annualized_sharpe / math.sqrt(PERIODS_PER_YEAR) * out[:, column].std(ddof=1)
    return out


class TestPBOCSCV:
    def test_dominant_trial_is_never_overfit(self) -> None:
        """A 5-Sharpe edge over 2 years: every split must agree, so PBO is a point mass.

        The edge is deliberately extreme — at a realistic 1-2 Sharpe over a
        two-year sample, individual 40-bar blocks can rank the winner below
        median, and a non-zero PBO is then the estimator working correctly.
        """
        matrix = _with_edge(
            _noise_matrix(n_observations=504, n_trials=6), column=2, annualized_sharpe=5.0
        )
        result = pbo_cscv(matrix, n_blocks=6)
        assert result.pbo == 0.0
        assert result.degenerate is True
        assert result.proxy is False
        assert result.label() == "cscv"
        assert result.logit_mean > 0.0

    def test_pure_noise_lands_near_a_coin_flip(self) -> None:
        result = pbo_cscv(_noise_matrix(n_trials=20, seed=7), n_blocks=10)
        # Observed 0.44 on this seed; the estimator's whole job is to be high for
        # noise searches, so the band is deliberately wide.
        assert 0.2 < result.pbo < 0.8
        assert result.n_splits == math.comb(10, 5)
        assert result.n_trials == 20

    def test_block_count_changes_the_split_count_by_combinatorics(self) -> None:
        matrix = _noise_matrix(n_trials=10, seed=3)
        assert pbo_cscv(matrix, n_blocks=4).n_splits == math.comb(4, 2)
        assert pbo_cscv(matrix, n_blocks=6).n_splits == math.comb(6, 3)

    def test_zero_variance_trial_is_dropped_and_named(self) -> None:
        matrix = _noise_matrix(n_trials=5, seed=11)
        matrix[:, 3] = 0.5
        result = pbo_cscv(matrix, n_blocks=4)
        assert result.dropped_trials == [3]
        assert result.n_trials == 4
        assert any("zero-variance" in warning for warning in result.warnings)

    def test_deterministic(self) -> None:
        matrix = _noise_matrix(n_trials=8, seed=5)
        assert pbo_cscv(matrix, n_blocks=4) == pbo_cscv(matrix, n_blocks=4)

    @pytest.mark.parametrize("n_blocks", [1, 3, 0])
    def test_rejects_non_even_block_counts(self, n_blocks: int) -> None:
        with pytest.raises(ValueError, match="n_blocks"):
            pbo_cscv(_noise_matrix(n_trials=4), n_blocks=n_blocks)

    def test_rejects_too_few_rows(self) -> None:
        with pytest.raises(ValueError, match="at least 2 \\* n_blocks"):
            pbo_cscv(_noise_matrix(n_observations=15, n_trials=4), n_blocks=10)

    def test_rejects_non_finite(self) -> None:
        matrix = _noise_matrix(n_trials=4)
        matrix[0, 0] = float("nan")
        with pytest.raises(ValueError, match="non-finite"):
            pbo_cscv(matrix, n_blocks=4)


class TestPBOFoldProxy:
    def test_is_labeled_as_a_proxy(self) -> None:
        performance = np.array([[1.0, 0.2], [0.9, 0.3], [1.1, 0.1], [0.8, 0.4]])
        result = pbo_fold_proxy(performance)
        assert result.proxy is True
        assert result.label() == "proxy"
        assert result.pbo == 0.0
        assert any("proxy" in warning for warning in result.warnings)

    def test_proxy_needs_at_least_three_folds(self) -> None:
        with pytest.raises(ValueError, match="3 folds"):
            pbo_fold_proxy(np.zeros((2, 3)))


class TestEffectiveTrialCount:
    def test_duplicated_trials_count_as_one(self) -> None:
        matrix = _noise_matrix(n_trials=2, seed=1)
        matrix[:, 1] = matrix[:, 0]
        assert effective_trial_count(matrix) == pytest.approx(1.0, abs=1e-9)

    def test_independent_trials_approach_the_raw_count(self) -> None:
        count = effective_trial_count(_noise_matrix(n_observations=1000, n_trials=18, seed=2))
        assert 0.85 * 18 <= count <= 18.0

    def test_correlated_trials_deflate_the_count(self) -> None:
        rng = np.random.default_rng(4)
        shared = rng.normal(0.0, 0.01, size=(1000, 1))
        matrix = shared + rng.normal(0.0, 0.0001, size=(1000, 8))
        assert effective_trial_count(matrix) < 3.0

    def test_single_trial_is_one(self) -> None:
        assert effective_trial_count(_noise_matrix(n_trials=1)) == 1.0

    def test_constant_trial_fails_closed(self) -> None:
        matrix = _noise_matrix(n_trials=3, seed=6)
        matrix[:, 1] = 1.0
        with pytest.raises(ValueError, match="constant"):
            effective_trial_count(matrix)


class TestDeflatedSharpeRatio:
    def test_stored_statistic_reproduces_the_dsr(self) -> None:
        rng = np.random.default_rng(8)
        returns = rng.normal(0.0005, 0.01, size=500)
        result = deflated_sharpe_ratio(returns, n_trials=100.0)
        assert result.dsr == pytest.approx(stats.norm_cdf(result.pre_phi_statistic), rel=1e-12)
        assert result.benchmark_sr > 0.0

    def test_single_trial_has_no_deflation_benchmark(self) -> None:
        rng = np.random.default_rng(9)
        returns = rng.normal(0.0005, 0.01, size=500)
        assert deflated_sharpe_ratio(returns, n_trials=1.0).benchmark_sr == 0.0

    def test_strong_edge_passes_and_noise_does_not(self) -> None:
        rng = np.random.default_rng(10)
        edge = rng.normal(0.0015, 0.01, size=1260)  # ~1.5 * sqrt(252) annualized
        noise = rng.normal(0.0, 0.01, size=1260)
        assert deflated_sharpe_ratio(edge, n_trials=1.0).dsr > 0.99
        assert deflated_sharpe_ratio(noise, n_trials=1000.0).dsr < 0.5

    def test_margin_falls_monotonically_with_trial_count(self) -> None:
        rng = np.random.default_rng(11)
        returns = rng.normal(0.0006, 0.01, size=1000)
        margins = [
            deflated_sharpe_ratio(returns, n_trials=float(n)).pre_phi_statistic
            for n in (1, 10, 100, 1000, 10000)
        ]
        assert all(a > b for a, b in zip(margins, margins[1:]))

    def test_search_size_sensitivity_is_about_one_sigma_per_decade(self) -> None:
        """§4 item 4: the margin must fall ~0.7 standard deviations per tenfold."""
        rng = np.random.default_rng(12)
        returns = rng.normal(0.0, 0.01, size=1260)
        low = deflated_sharpe_ratio(returns, n_trials=10.0).pre_phi_statistic
        high = deflated_sharpe_ratio(returns, n_trials=1000.0).pre_phi_statistic
        assert 0.4 <= (low - high) / 2.0 <= 1.0

    def test_noise_margin_is_flat_in_history_and_a_real_edge_is_not(self) -> None:
        """§4 item 5: the null benchmark must not drift with T."""
        noise_means = []
        edge_means = []
        for observations in (504, 2520):
            noise, edge = [], []
            for seed in range(25):
                rng = np.random.default_rng(1000 + seed)
                noise.append(
                    deflated_sharpe_ratio(rng.normal(0.0, 0.01, observations), n_trials=1000.0)
                )
                edge.append(
                    deflated_sharpe_ratio(rng.normal(0.0008, 0.01, observations), n_trials=1000.0)
                )
            noise_means.append(sum(r.pre_phi_statistic for r in noise) / len(noise))
            edge_means.append(sum(r.pre_phi_statistic for r in edge) / len(edge))
        assert abs(noise_means[1] - noise_means[0]) < 0.35
        assert edge_means[1] > edge_means[0] + 0.5

    def test_rejects_bad_inputs(self) -> None:
        rng = np.random.default_rng(13)
        returns = rng.normal(0.0005, 0.01, size=500)
        with pytest.raises(ValueError, match="at least 4 observations"):
            deflated_sharpe_ratio([0.01, 0.02, 0.03])
        with pytest.raises(ValueError, match="n_trials"):
            deflated_sharpe_ratio(returns, n_trials=0.5)
        with pytest.raises(ValueError, match="periods_per_year"):
            deflated_sharpe_ratio(returns, periods_per_year=0)


class TestMinTrackRecordLength:
    def test_formula_matches_an_independent_recomputation(self) -> None:
        rng = np.random.default_rng(14)
        returns = rng.normal(0.0008, 0.01, size=1000)
        result = min_track_record_length(returns, alpha=0.05)
        sr = stats.sharpe_ratio(returns)
        factor = 1.0 - stats.skewness(returns) * sr + (stats.kurtosis(returns) - 1.0) / 4.0 * sr**2
        expected = 1.0 + factor * (stats.norm_ppf(0.95) / sr) ** 2
        assert result.required_bars == pytest.approx(expected, rel=1e-12)

    def test_stronger_sharpe_needs_less_history(self) -> None:
        rng = np.random.default_rng(15)
        weak = rng.normal(0.0002, 0.01, size=1000)
        strong = rng.normal(0.0010, 0.01, size=1000)
        weak_required = min_track_record_length(weak).required_bars
        strong_required = min_track_record_length(strong).required_bars
        assert weak_required is not None and strong_required is not None
        assert strong_required < weak_required

    def test_long_history_passes(self) -> None:
        rng = np.random.default_rng(16)
        result = min_track_record_length(rng.normal(0.0010, 0.01, size=2520))
        assert result.passed is True

    def test_non_positive_sharpe_is_unbounded_and_never_passes(self) -> None:
        rng = np.random.default_rng(17)
        result = min_track_record_length(rng.normal(-0.0005, 0.01, size=500))
        assert result.unbounded is True
        assert result.required_bars is None
        assert result.passed is False

    def test_rejects_bad_alpha(self) -> None:
        rng = np.random.default_rng(18)
        with pytest.raises(ValueError, match="alpha"):
            min_track_record_length(rng.normal(0.001, 0.01, size=500), alpha=1.5)


class TestSPATest:
    def test_a_genuine_edge_clears_the_gate(self) -> None:
        rng = np.random.default_rng(19)
        matrix = rng.normal(0.0, 0.01, size=(500, 10))
        matrix[:, 3] += 0.0015
        result = spa_test(matrix, n_bootstrap=200, seed=7)
        # Tested against the gate's own threshold, not a tighter one: the
        # studentized maximum over ten candidates already reaches ~2 sigma under
        # the null, so a real edge lands near the boundary rather than at zero.
        assert result.p_value <= 0.10
        assert result.n_trials == 10
        assert 1 <= result.n_relevant_trials <= 10

    def test_a_lone_strong_trial_clears_the_stricter_boundary(self) -> None:
        rng = np.random.default_rng(19)
        matrix = rng.normal(0.0, 0.01, size=(500, 4))
        matrix[:, 1] += 0.0025
        assert spa_test(matrix, n_bootstrap=200, seed=7).p_value <= 0.05

    def test_pure_noise_does_not_pass_the_gate(self) -> None:
        rng = np.random.default_rng(20)
        result = spa_test(rng.normal(0.0, 0.01, size=(500, 30)), n_bootstrap=200, seed=7)
        assert result.p_value > 0.10

    def test_deterministic_for_a_fixed_seed_and_stable_across_seeds(self) -> None:
        rng = np.random.default_rng(21)
        matrix = rng.normal(0.0, 0.01, size=(400, 12))
        first = spa_test(matrix, n_bootstrap=120, seed=1).p_value
        assert spa_test(matrix, n_bootstrap=120, seed=1).p_value == first
        assert abs(spa_test(matrix, n_bootstrap=120, seed=2).p_value - first) < 0.1

    def test_benchmark_differentials_change_the_verdict(self) -> None:
        rng = np.random.default_rng(22)
        matrix = rng.normal(0.001, 0.01, size=(500, 8))
        versus_zero = spa_test(matrix, n_bootstrap=200, seed=3)
        versus_self = spa_test(matrix, matrix.mean(axis=1), n_bootstrap=200, seed=3)
        assert versus_zero.p_value < versus_self.p_value

    def test_common_blocks_preserve_cross_sectional_dependence(self) -> None:
        """One dominant, highly correlated set beats a wide independent one."""
        rng = np.random.default_rng(23)
        shared = rng.normal(0.0005, 0.01, size=(500, 1))
        correlated = np.repeat(shared, 10, axis=1) + rng.normal(0.0, 0.0002, size=(500, 10))
        result = spa_test(correlated, n_bootstrap=200, seed=5)
        assert result.p_value > 0.05

    def test_rejects_degenerate_inputs(self) -> None:
        rng = np.random.default_rng(24)
        flat = rng.normal(0.0, 0.01, size=(100, 4))
        flat[:, 2] = 0.0
        with pytest.raises(ValueError, match="zero variance"):
            spa_test(flat, n_bootstrap=50)
        with pytest.raises(ValueError, match="benchmark must have shape"):
            spa_test(rng.normal(0.0, 0.01, size=(100, 4)), [0.0] * 99, n_bootstrap=50)
        with pytest.raises(ValueError, match="block_length"):
            spa_test(rng.normal(0.0, 0.01, size=(100, 4)), n_bootstrap=50, block_length=1000)
        with pytest.raises(ValueError, match="n_bootstrap"):
            spa_test(rng.normal(0.0, 0.01, size=(100, 4)), n_bootstrap=1)


class TestRegimeStability:
    def test_hand_computed_stable_winner(self) -> None:
        result = regime_stability([1.0, 1.0, 1.0, 1.0])
        expected = 0.5 + 0.3 + 0.2 * (1.0 / (1.0 + math.exp(-1.0)))
        assert result.rho == pytest.approx(expected, rel=1e-12)
        assert result.rho == pytest.approx(0.94621172, abs=1e-8)
        assert result.passed is True

    def test_hand_computed_loser_fails(self) -> None:
        result = regime_stability([-1.0, -1.0, -1.0, -1.0])
        expected = 0.3 + 0.2 * (1.0 / (1.0 + math.exp(1.0)))
        assert result.rho == pytest.approx(expected, rel=1e-12)
        assert result.passed is False

    def test_high_dispersion_zeroes_the_stability_term(self) -> None:
        result = regime_stability([-5.0, 5.0])
        assert result.positive_fraction == 0.5
        assert result.rho < 0.4

    def test_needs_two_windows(self) -> None:
        with pytest.raises(ValueError, match="at least 2 windows"):
            regime_stability([1.0])


class TestAgentAcceptance:
    @staticmethod
    def _pbo(p_value: float, *, n_trials: int = 100, proxy: bool = False) -> PBOResult:
        return PBOResult(
            pbo=p_value,
            n_trials=n_trials,
            n_splits=10,
            n_blocks=5,
            logit_mean=0.0,
            logit_std=0.5,
            degenerate=False,
            proxy=proxy,
            dropped_trials=[],
            warnings=[],
        )

    def test_accepts_below_alpha_and_rejects_at_or_above(self) -> None:
        assert agent_acceptance_test(self._pbo(0.08)).accepted is True
        assert agent_acceptance_test(self._pbo(0.10)).accepted is False
        assert agent_acceptance_test(self._pbo(0.213)).accepted is False

    def test_under_searched_grid_is_flagged(self) -> None:
        result = agent_acceptance_test(self._pbo(0.02, n_trials=20))
        assert result.accepted is True
        assert result.trials_sufficient is False
        assert any("grid-coverage" in warning for warning in result.warnings)

    def test_proxy_pbo_carries_a_warning(self) -> None:
        result = agent_acceptance_test(self._pbo(0.05, proxy=True))
        assert any("proxy" in warning for warning in result.warnings)
