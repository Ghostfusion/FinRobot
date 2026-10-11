"""Tests for validation_report — the structural ZI-arm guard (§4, §5.7).

The rule enforced here is not a convention: a simulated result cannot be
reported without the ZI arm beside it, and that failure is a raised error, not a
warning.
"""

from __future__ import annotations

import numpy as np
import pytest

from finrobot.engine.simulation.report import validation_report
from finrobot.engine.simulation.stylized_facts import Moment, MomentKind


def _series(n: int, seed: int, *, heavy: bool = False) -> np.ndarray:
    rng = np.random.default_rng(seed)
    if heavy:
        return rng.standard_t(3, size=n) * 0.01
    return rng.normal(0.0, 1.0, size=n) * 0.01


def _moments() -> list[Moment]:
    return [
        Moment(name="hill", kind=MomentKind.HILL, param=0.05),
        Moment(name="ret_acf_30", kind=MomentKind.RETURN_ACF, param=30.0),
    ]


class TestZeroIntelligenceArmGuard:
    def test_missing_zi_arm_raises(self) -> None:
        with pytest.raises(ValueError, match="ZI arm"):
            validation_report(_series(400, 1), _series(400, 2))

    def test_present_zi_arm_reports_true(self) -> None:
        report = validation_report(
            _series(400, 1), _series(400, 2), zi_series=_series(400, 3), moments=_moments()
        )
        assert report.zi_arm_present is True


class TestReportContent:
    def test_same_moments_for_all_groups(self) -> None:
        moments = _moments()
        names = [m.name for m in moments]
        report = validation_report(
            _series(500, 1, heavy=True),
            _series(500, 2),
            zi_series=_series(500, 3),
            moments=moments,
        )
        assert report.moments == names
        for group in ("real", "simulated", "zi"):
            assert list(report.moment_values[group]) == names
        for arm in ("simulated", "zi"):
            assert list(report.coverage[arm].per_moment) == names

    def test_kurtosis_by_group(self) -> None:
        report = validation_report(
            _series(800, 1, heavy=True),
            _series(800, 2),
            zi_series=_series(800, 3),
            moments=_moments(),
        )
        assert set(report.kurtosis) == {"real", "simulated", "zi"}
        assert report.kurtosis["real"] > 0.0
        assert report.kurtosis["simulated"] < report.kurtosis["real"]

    def test_coverage_available_for_both_arms(self) -> None:
        report = validation_report(
            _series(400, 1),
            _series(400, 2),
            zi_series=_series(400, 3),
            moments=_moments(),
        )
        assert set(report.coverage) == {"simulated", "zi"}
        for arm in report.coverage.values():
            assert 0.0 <= arm.aggregate <= 1.0

    def test_validates_alpha(self) -> None:
        with pytest.raises(ValueError):
            validation_report(
                _series(200, 1),
                _series(200, 2),
                zi_series=_series(200, 3),
                moments=_moments(),
                alpha=2.0,
            )
