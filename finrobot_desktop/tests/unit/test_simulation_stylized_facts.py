"""Tests for the stylized-facts / moment-coverage harness (§2.2).

Pins the properties the document cares about: the estimators are the ones
specified (Hill on absolute returns, 3-lag-smoothed squared-return ACF), and the
coverage matrix is judged PER CELL — a series against itself is a clean 1.0,
while i.i.d. noise against a heavy-tailed series leaves the shape cells cold.
"""

from __future__ import annotations

import numpy as np
import pytest

from finrobot.engine.simulation.stylized_facts import (
    Moment,
    MomentKind,
    block_bootstrap_weights,
    bootstrap_paths,
    coverage_matrix,
    default_moments,
    hill_tail_index,
    realized_volatility,
    return_autocorr,
    squared_return_autocorr,
)


def _heavy_tailed(n: int, seed: int) -> np.ndarray:
    return np.random.default_rng(seed).standard_t(3, size=n) * 0.01


def _normal(n: int, seed: int) -> np.ndarray:
    return np.random.default_rng(seed).normal(0.0, 1.0, size=n) * 0.01


class TestEstimators:
    def test_hill_tail_index_heavy_beats_normal(self) -> None:
        heavy = hill_tail_index(_heavy_tailed(5000, 1), tail_fraction=0.05)
        normal = hill_tail_index(_normal(5000, 2), tail_fraction=0.05)
        assert heavy > normal

    def test_hill_tail_index_validates_tail_fraction(self) -> None:
        with pytest.raises(ValueError):
            hill_tail_index([0.1, 0.2], tail_fraction=0.0)
        with pytest.raises(ValueError):
            hill_tail_index([0.1, 0.2], tail_fraction=1.5)

    def test_realized_volatility_matches_manual(self) -> None:
        assert realized_volatility([3.0, 4.0], window=2) == pytest.approx(5.0)

    def test_realized_volatility_mean_across_blocks(self) -> None:
        # two blocks: sqrt(3^2+4^2)=5 and sqrt(5^2+12^2)=13 -> mean 9
        assert realized_volatility([3.0, 4.0, 5.0, 12.0], window=2) == pytest.approx(9.0)

    def test_return_autocorr_alternating_series(self) -> None:
        series = [1.0, -1.0] * 50
        assert return_autocorr(series, lag=1) == pytest.approx(-1.0)
        assert return_autocorr(series, lag=2) == pytest.approx(1.0)

    def test_squared_return_autocorr_is_three_lag_smoothed(self) -> None:
        rng = np.random.default_rng(0)
        series = rng.normal(0.0, 1.0, size=400)
        squared = series**2
        expected = float(np.mean([return_autocorr(squared, lag=k) for k in (1, 2, 3)]))
        assert squared_return_autocorr(series, lag=2) == pytest.approx(expected)


class TestBootstrapWeights:
    def test_weights_positive_finite_and_deterministic(self) -> None:
        rng = np.random.default_rng(3)
        real = rng.normal(0.0, 1.0, size=600)
        first = block_bootstrap_weights(real, n_block=25, seed=11)
        second = block_bootstrap_weights(real, n_block=25, seed=11)
        assert first.shape == (4,)
        assert bool(np.all(np.isfinite(first)))
        assert bool(np.all(first > 0.0))
        assert np.array_equal(first, second)

    def test_bootstrap_paths_deterministic_and_sized(self) -> None:
        rng = np.random.default_rng(4)
        series = rng.normal(0.0, 1.0, size=200)
        paths = bootstrap_paths(series, n_paths=10, n_block=20, seed=5)
        assert len(paths) == 10
        assert all(path.size == series.size for path in paths)
        again = bootstrap_paths(series, n_paths=10, n_block=20, seed=5)
        assert np.array_equal(paths[0], again[0])


def _moments() -> list[Moment]:
    return [
        Moment(name="hill", kind=MomentKind.HILL, param=0.05),
        Moment(name="vol", kind=MomentKind.REALIZED_VOLATILITY, param=30.0),
        Moment(name="ret_acf_30", kind=MomentKind.RETURN_ACF, param=30.0),
        Moment(name="sq_acf_1", kind=MomentKind.SQUARED_RETURN_ACF, param=1.0),
    ]


class TestCoverageMatrix:
    def test_series_against_itself_is_identity(self) -> None:
        rng = np.random.default_rng(7)
        real = rng.normal(0.0, 1.0, size=800)
        cov = coverage_matrix(real, [real], moments=_moments(), alpha=0.95)
        assert cov.aggregate == 1.0
        assert all(cell == 1.0 for row in cov.cells for cell in row)
        assert cov.cell("hill", 0) == 1.0

    def test_iid_noise_against_heavy_tailed_has_low_hill_coverage(self) -> None:
        real = _heavy_tailed(4000, 21)
        noise_paths = [_normal(4000, 100 + i) for i in range(50)]
        cov = coverage_matrix(real, noise_paths, moments=_moments(), alpha=0.95)
        # stated range: the tail-index cell is cold (< 0.5) and the aggregate is
        # strictly below the perfect self-coverage of 1.0, but never negative.
        assert cov.per_moment["hill"] < 0.5
        assert 0.0 <= cov.aggregate < 1.0
        assert set(cov.per_moment) == {"hill", "vol", "ret_acf_30", "sq_acf_1"}

    def test_coverage_matrix_validates_inputs(self) -> None:
        real = [0.1, -0.2, 0.3, -0.4]
        with pytest.raises(ValueError):
            coverage_matrix(real, [real], moments=_moments(), alpha=1.5)
        with pytest.raises(ValueError):
            coverage_matrix(real, [], moments=_moments(), alpha=0.95)
        with pytest.raises(ValueError):
            coverage_matrix(real, [real], moments=[], alpha=0.95)

    def test_default_moments_has_hill_and_both_acf_families(self) -> None:
        names = [moment.name for moment in default_moments()]
        assert "hill" in names and "vol" in names
        assert any(name.startswith("ret_acf_") for name in names)
        assert any(name.startswith("sq_acf_") for name in names)
