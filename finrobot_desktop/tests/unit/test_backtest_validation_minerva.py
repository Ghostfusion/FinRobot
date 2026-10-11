"""Tests for the MinervaScore aggregate, including the document's §4 harness.

The methodology document lists eight ways to test that such an implementation is
sound; the aggregate-level ones are here:

* item 1 — the invariant ``display >= 80`` iff the Seal passed, over synthetic
  records (no failing record displays >= 80, no passing record below it);
* item 2 — rank stability under a +/-20% perturbation of every weight, and exact
  rank-invariance for the conservative offset;
* item 3 — a synthetic ground-truth harness: searches whose winner carries a
  genuine edge must be separated from searches over pure noise.

Plus the fail-closed rules, the calibration validators, and the seal's
independence from the (provisional) margin scale factors.
"""

from __future__ import annotations

import math
import random

import numpy as np
import pytest

from finrobot.engine.backtest.validation import minerva, stats
from finrobot.engine.backtest.validation.minerva import (
    GATE_ORDER,
    WEIGHTS,
    GateMargin,
    MarginCalibration,
    default_calibration,
    equicorrelation_matrix,
    estimate_margin_sigma,
    estimate_sigma_eff,
    evaluate_gates,
    gate_margins,
    minerva_score,
)
from finrobot.engine.backtest.validation.overfitting import (
    deflated_sharpe_ratio,
    effective_trial_count,
    min_track_record_length,
    pbo_cscv,
    pbo_fold_proxy,
    regime_stability,
    spa_test,
)

_PERIODS_PER_YEAR = 252

# The paper's cross-gate correlation matrix, transcribed from Table 4. Held as a
# literal so the test verifies the shipped default against the source rather than
# against itself, and so the denominator below is the paper's own 0.753.
_PAPER_SIGMA_EFF = [
    [1.00, 0.23, 0.32, 0.71, 0.25],
    [0.23, 1.00, 0.65, 0.48, 0.51],
    [0.32, 0.65, 1.00, 0.57, 0.60],
    [0.71, 0.48, 0.57, 1.00, 0.55],
    [0.25, 0.51, 0.60, 0.55, 1.00],
]
_DENOMINATOR = math.sqrt(
    sum(
        WEIGHTS[row] * _PAPER_SIGMA_EFF[row][column] * WEIGHTS[column]
        for row in range(len(WEIGHTS))
        for column in range(len(WEIGHTS))
    )
)


def _margins(
    *,
    dsr_pre_phi: float | None = 3.0,
    pbo: float | None = 0.30,
    spa_p: float | None = 0.05,
    observed_bars: int | None = 1500,
    required_bars: float | None = 900.0,
    regime_rho: float | None = 0.80,
    calibration: MarginCalibration | None = None,
) -> list[GateMargin]:
    return gate_margins(
        dsr_pre_phi=dsr_pre_phi,
        pbo=pbo,
        spa_p=spa_p,
        observed_bars=observed_bars,
        required_bars=required_bars,
        regime_rho=regime_rho,
        calibration=calibration or default_calibration(),
    )


class TestGateMargins:
    @pytest.mark.parametrize(
        ("kwargs", "gate"),
        [
            ({"dsr_pre_phi": stats.norm_ppf(0.95)}, "dsr"),
            ({"pbo": 0.50}, "pbo"),
            ({"spa_p": 0.10}, "spa"),
            ({"regime_rho": 0.60}, "regime"),
            ({"observed_bars": 900, "required_bars": 900.0}, "mintrl"),
        ],
    )
    def test_margin_is_exactly_zero_at_its_threshold(
        self, kwargs: dict[str, object], gate: str
    ) -> None:
        """The anchoring property the Seal's scale-independence rests on."""
        margin = {m.gate: m for m in _margins(**kwargs)}[gate]  # type: ignore[arg-type]
        assert margin.margin == pytest.approx(0.0, abs=1e-12)
        assert margin.passed is True

    @pytest.mark.parametrize(
        ("kwargs", "gate", "passes"),
        [
            ({"dsr_pre_phi": stats.norm_ppf(0.95) - 0.5}, "dsr", False),
            ({"pbo": 0.51}, "pbo", False),
            ({"pbo": 0.49}, "pbo", True),
            ({"spa_p": 0.11}, "spa", False),
            ({"spa_p": 0.09}, "spa", True),
            ({"regime_rho": 0.59}, "regime", False),
            ({"regime_rho": 0.61}, "regime", True),
            ({"observed_bars": 899, "required_bars": 900.0}, "mintrl", False),
            ({"observed_bars": 901, "required_bars": 900.0}, "mintrl", True),
        ],
    )
    def test_margin_sign_follows_the_verdict(
        self, kwargs: dict[str, object], gate: str, passes: bool
    ) -> None:
        margin = {m.gate: m for m in _margins(**kwargs)}[gate]  # type: ignore[arg-type]
        assert margin.passed is passes
        assert (margin.margin > 0.0) is passes

    def test_missing_statistics_fail_closed_at_the_negative_clip(self) -> None:
        margins = _margins(
            dsr_pre_phi=None,
            pbo=None,
            spa_p=None,
            regime_rho=None,
            observed_bars=None,
            required_bars=None,
        )
        calibration = default_calibration()
        for margin in margins:
            assert margin.passed is False
            assert margin.active is False
            assert margin.margin == -calibration.margin_clip
            assert "fail closed" in margin.detail

    def test_unbounded_mintrl_uses_the_tanh_limit(self) -> None:
        """Eq. 6's limit: no finite track length suffices, so the margin is -1."""
        margin = {
            m.gate: m
            for m in gate_margins(
                dsr_pre_phi=1.0,
                pbo=0.4,
                spa_p=0.2,
                observed_bars=1500,
                required_bars=None,
                regime_rho=0.7,
                calibration=default_calibration(),
                mintrl_unbounded=True,
            )
        }["mintrl"]
        assert margin.passed is False
        assert margin.active is True
        assert margin.margin == -1.0
        assert "unbounded" in margin.detail

    def test_one_inactive_gate_renormalizes_and_never_seals(self) -> None:
        margins = _margins(regime_rho=None)
        report = minerva_score(margins=margins)
        assert report.seal is False
        assert report.display is not None and report.display < 80.0
        assert any("renormalized" in warning for warning in report.warnings)

    def test_all_gates_inactive_produces_no_display(self) -> None:
        report = minerva_score(
            margins=_margins(
                dsr_pre_phi=None,
                pbo=None,
                spa_p=None,
                regime_rho=None,
                observed_bars=None,
                required_bars=None,
            )
        )
        assert report.display is None
        assert report.s is None

    def test_order_is_always_the_declared_gate_order(self) -> None:
        assert [margin.gate for margin in _margins()] == list(GATE_ORDER)


class TestMinervaScore:
    def test_marginal_pass_displays_exactly_eighty(self) -> None:
        report = minerva_score(
            margins=[
                GateMargin(gate=gate, statistic=None, threshold=0.0, margin=0.0, passed=True)
                for gate in GATE_ORDER
            ]
        )
        assert report.seal is True
        assert report.s == pytest.approx(0.0, abs=1e-12)
        assert report.display == pytest.approx(80.0, abs=1e-12)
        assert report.verdict_consistent is True

    def test_marginal_failure_displays_below_eighty(self) -> None:
        report = minerva_score(
            margins=[
                GateMargin(gate=gate, statistic=None, threshold=0.0, margin=0.0, passed=False)
                for gate in GATE_ORDER
            ]
        )
        assert report.seal is False
        # The paper floors the display, so the raw 24.68 becomes 24.
        assert report.display == math.floor(80.0 * stats.norm_cdf(-0.5))
        assert report.display is not None and report.display < 80.0

    def test_combined_statistic_matches_the_inverse_normal_blend(self) -> None:
        report = minerva_score(
            margins=[
                GateMargin(gate=gate, statistic=None, threshold=0.0, margin=1.0, passed=True)
                for gate in GATE_ORDER
            ]
        )
        assert report.s == pytest.approx(1.0 / _DENOMINATOR, rel=1e-12)
        assert report.s is not None
        calibration = default_calibration()
        r = stats.norm_cdf(report.s - calibration.offset)
        r_zero = stats.norm_cdf(-calibration.offset)
        raw = 80.0 + 20.0 * (r - r_zero) / (calibration.r_star - r_zero)
        assert report.display == math.floor(raw)

    def test_saturated_margins_reach_the_top_of_the_display(self) -> None:
        clip = default_calibration().margin_clip
        report = minerva_score(
            margins=[
                GateMargin(gate=gate, statistic=None, threshold=0.0, margin=clip, passed=True)
                for gate in GATE_ORDER
            ]
        )
        assert report.display == pytest.approx(100.0, abs=1e-6)

    def test_display_is_monotone_in_the_margins(self) -> None:
        displays = [
            minerva_score(
                margins=[
                    GateMargin(gate=gate, statistic=None, threshold=0.0, margin=value, passed=True)
                    for gate in GATE_ORDER
                ]
            ).display
            for value in (0.0, 0.5, 1.0, 2.0)
        ]
        scored = [display for display in displays if display is not None]
        assert len(scored) == 4
        assert all(a < b for a, b in zip(scored, scored[1:]))

    def test_verdict_consistency_invariant_over_synthetic_records(self) -> None:
        """§4 item 1 — the paper holds this with zero violations over 359k rows."""
        rng = random.Random(20261010)
        extremes = [0.0, 1.0, 1e-9, 1.0 - 1e-9, 0.5]
        for index in range(400):
            if index % 5 == 0:
                pbo = extremes[index % len(extremes)]
                spa = extremes[(index + 1) % len(extremes)]
                rho = extremes[(index + 2) % len(extremes)]
            else:
                pbo = rng.random()
                spa = rng.random()
                rho = rng.random()
            report = minerva_score(
                margins=_margins(
                    dsr_pre_phi=rng.gauss(0.0, 3.0),
                    pbo=pbo,
                    spa_p=spa,
                    observed_bars=rng.randint(50, 3000),
                    required_bars=rng.uniform(50.0, 2500.0),
                    regime_rho=rho,
                )
            )
            assert report.verdict_consistent is True
            assert (report.display is not None and report.display >= 80.0) is report.seal

    def test_seal_is_independent_of_the_margin_scale_factors(self) -> None:
        """A wrong sigma can stretch the display; it must never flip the verdict."""
        margins = _margins()
        baseline = minerva_score(margins=margins, calibration=default_calibration())
        for dsr_scale, pbo_scale, spa_scale, regime_scale in (
            (0.1, 0.1, 0.1, 0.1),
            (10.0, 10.0, 10.0, 10.0),
            (0.3, 7.0, 2.0, 5.0),
        ):
            calibration = MarginCalibration(
                version="perturbed",
                sigma_dsr=dsr_scale,
                sigma_pbo=pbo_scale,
                sigma_spa=spa_scale,
                sigma_regime=regime_scale,
            )
            perturbed = minerva_score(margins=margins, calibration=calibration)
            assert perturbed.seal is baseline.seal

    def test_rank_stability_under_weight_perturbation(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """§4 item 2 — reordering must not survive a +/-20% weight perturbation."""
        rng = random.Random(7)
        records = [
            _margins(
                dsr_pre_phi=rng.gauss(1.0, 2.5),
                pbo=rng.random(),
                spa_p=rng.random(),
                observed_bars=rng.randint(100, 3000),
                required_bars=rng.uniform(50.0, 2000.0),
                regime_rho=rng.random(),
            )
            for _ in range(60)
        ]

        def ranking() -> list[float]:
            scores = [minerva_score(margins=record).s for record in records]
            assert all(score is not None for score in scores)
            return [score for score in scores if score is not None]

        baseline = ranking()
        for position in range(len(WEIGHTS)):
            for factor in (0.8, 1.2):
                perturbed = list(WEIGHTS)
                perturbed[position] *= factor
                monkeypatch.setattr(minerva, "WEIGHTS", tuple(perturbed))
                # Observed minimum 0.994 on this synthetic population. The
                # document's 0.997 figure is a property of its calibrated
                # production population, which is not reproducible here, so the
                # floor is the property that matters: the ordering barely moves.
                assert stats.spearman_rho(baseline, ranking()) >= 0.99
            monkeypatch.setattr(minerva, "WEIGHTS", WEIGHTS)

    def test_offset_changes_no_ranking(self) -> None:
        """§4 item 2 — the conservative offset is an exact rank invariant."""
        rng = random.Random(11)
        records = [
            _margins(dsr_pre_phi=rng.gauss(1.0, 2.0), pbo=rng.random(), regime_rho=rng.random())
            for _ in range(40)
        ]
        baseline = [minerva_score(margins=record).display for record in records]
        shifted = [
            minerva_score(
                margins=record, calibration=MarginCalibration(version="offset", offset=0.55)
            ).display
            for record in records
        ]
        # The offset shifts r monotonically, so the ordering survives exactly — but
        # the display is floored to integers, so neighbours can tie. The claim being
        # tested is "the offset reorders nothing", not "no two displays are equal".
        baseline_values = [value for value in baseline if value is not None]
        shifted_values = [value for value in shifted if value is not None]
        assert stats.spearman_rho(baseline_values, shifted_values) >= 0.999
        # The verdict band is exactly invariant.
        assert [value >= 80.0 for value in baseline_values] == [
            value >= 80.0 for value in shifted_values
        ]

    def test_missing_gate_raises(self) -> None:
        partial = [m for m in _margins() if m.gate != "spa"]
        with pytest.raises(ValueError, match="missing gates"):
            minerva_score(margins=partial)

    def test_fail_closed_reason_suppresses_the_display(self) -> None:
        report = minerva_score(margins=_margins(), fail_closed_reason="no pre-Phi statistic")
        assert report.display is None
        assert report.s is None
        assert report.seal is False
        assert "no pre-Phi statistic" in report.warnings[0]

    def test_format_summary_reports_every_gate(self) -> None:
        summary = minerva_score(margins=_margins()).format_summary()
        assert "MinervaScore:" in summary
        for gate in GATE_ORDER:
            assert gate in summary


class TestEvaluateGates:
    def _noisy(self, seed: int = 42, bars: int = 750) -> dict[str, object]:
        rng = np.random.default_rng(seed)
        matrix = rng.normal(0.0, 0.01, size=(bars, 12))
        winner = matrix[:, 0]
        return {
            "dsr": deflated_sharpe_ratio(winner, n_trials=12.0),
            "pbo": pbo_cscv(matrix, n_blocks=6),
            "spa": spa_test(matrix, n_bootstrap=100, seed=3),
            "mintrl": min_track_record_length(winner),
            "regime": regime_stability(
                [float(stats.sharpe_ratio(chunk)) for chunk in np.array_split(winner, 5)]
            ),
        }

    def test_reports_all_five_gates(self) -> None:
        report = evaluate_gates(**self._noisy())  # type: ignore[arg-type]
        assert [margin.gate for margin in report.margins] == list(GATE_ORDER)
        assert report.display is not None
        assert 0.0 <= report.display <= 100.0

    def test_noise_is_not_sealed(self) -> None:
        report = evaluate_gates(**self._noisy())  # type: ignore[arg-type]
        assert report.seal is False

    def test_missing_dsr_result_fails_closed(self) -> None:
        inputs = self._noisy()
        inputs["dsr"] = None
        report = evaluate_gates(**inputs)  # type: ignore[arg-type]
        assert report.display is None
        assert any("pre-Phi" in warning for warning in report.warnings)
        assert report.seal is False

    def test_degenerate_pbo_warning_propagates(self) -> None:
        inputs = self._noisy()
        degenerate = pbo_cscv(_edge_matrix(), n_blocks=6)
        assert degenerate.degenerate is True  # precondition: the case is exercised
        inputs["pbo"] = degenerate
        report = evaluate_gates(**inputs)  # type: ignore[arg-type]
        assert any("degenerate" in warning for warning in report.warnings)

    def test_proxy_pbo_warning_propagates(self) -> None:
        inputs = self._noisy()
        inputs["pbo"] = pbo_fold_proxy(np.array([[1.0, 0.2], [0.9, 0.3], [1.1, 0.1], [0.8, 0.4]]))
        report = evaluate_gates(**inputs)  # type: ignore[arg-type]
        assert any("proxy" in warning for warning in report.warnings)

    def test_absurdly_good_noise_does_not_get_a_seal(self) -> None:
        """A lucky selection effect must not seal just because one gate looks great."""
        rng = np.random.default_rng(5)
        matrix = rng.normal(0.0, 0.01, size=(750, 500))
        winner = int(np.argmax(matrix[: 750 // 2].mean(axis=0) / matrix[: 750 // 2].std(axis=0)))
        report = evaluate_gates(
            dsr=deflated_sharpe_ratio(matrix[:, winner], n_trials=effective_trial_count(matrix)),
            pbo=pbo_cscv(matrix, n_blocks=6),
            spa=spa_test(matrix, n_bootstrap=100, seed=4),
            mintrl=min_track_record_length(matrix[:, winner]),
            regime=regime_stability(
                [float(stats.sharpe_ratio(chunk)) for chunk in np.array_split(matrix[:, winner], 5)]
            ),
        )
        assert report.seal is False


def _edge_matrix(
    bars: int = 504, n_trials: int = 6, seed: int = 1, annualized_sharpe: float = 5.0
) -> np.ndarray:
    """A search whose winner is unambiguous, so every CSCV split agrees."""
    rng = np.random.default_rng(seed)
    matrix = rng.normal(0.0, 0.01, size=(bars, n_trials))
    matrix[:, 2] += annualized_sharpe / math.sqrt(_PERIODS_PER_YEAR) * matrix[:, 2].std(ddof=1)
    return matrix


class TestCalibration:
    def test_shipped_calibration_is_the_paper_published_set(self) -> None:
        calibration = default_calibration()
        matrix = np.asarray(calibration.sigma_eff)
        assert calibration.sigma_eff == _PAPER_SIGMA_EFF
        assert np.allclose(np.diag(matrix), 1.0)
        # Table 4 is published to two decimals, and the smallest eigenvalue is the
        # most rounding-sensitive quantity in a correlation matrix: the transcribed
        # matrix gives 0.2040 against the paper's stated 0.21. The denominator is
        # the better-conditioned check and lands on the paper's own figure.
        assert float(np.linalg.eigvalsh(matrix).min()) == pytest.approx(0.204, abs=1e-3)
        assert _DENOMINATOR == pytest.approx(0.753, abs=2e-3)
        assert calibration.thresholds.dsr == 0.95
        assert calibration.thresholds.pbo == 0.50
        assert calibration.thresholds.spa == 0.10
        assert calibration.thresholds.regime == 0.60
        assert calibration.sigma_dsr == 1.128
        assert calibration.sigma_pbo == 10.028
        assert calibration.sigma_spa == 6.013
        assert calibration.sigma_regime == 1.161
        assert calibration.offset == 0.5
        assert calibration.fail_delta == 0.1
        assert calibration.r_star == pytest.approx(0.9997)
        assert sum(WEIGHTS) == pytest.approx(1.0)
        assert calibration.version.startswith("minerva-")

    def test_equicorrelation_helper_stays_available_and_positive_definite(self) -> None:
        matrix = np.asarray(equicorrelation_matrix(len(GATE_ORDER), 0.79))
        assert np.allclose(np.diag(matrix), 1.0)
        assert float(np.linalg.eigvalsh(matrix).min()) == pytest.approx(0.21, abs=1e-12)

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"sigma_pbo": 0.0},
            {"sigma_dsr": -1.0},
            {"fail_delta": 0.0},
            {"fail_delta": 90.0},
            {"r_star": 0.2},
            {"margin_clip": 0.0},
            {"mintrl_min_sigma": 0.0},
            {"sigma_eff": [[1.0] * 5] * 5},
            {"sigma_eff": equicorrelation_matrix(5, 0.79)[:4]},
            {"fail_cdf": [0.9, 0.1]},
        ],
    )
    def test_invalid_calibrations_are_rejected(self, kwargs: dict[str, object]) -> None:
        with pytest.raises(ValueError):
            MarginCalibration(version="bad", **kwargs)  # type: ignore[arg-type]

    def test_estimate_sigma_eff_is_positive_definite_with_unit_diagonal(self) -> None:
        rng = np.random.default_rng(3)
        shared = rng.normal(size=(200, 1))
        margins = np.hstack([shared + rng.normal(0.0, 0.5, size=(200, 1)) for _ in range(5)])
        estimated = np.asarray(estimate_sigma_eff(margins))
        assert estimated.shape == (5, 5)
        assert np.allclose(np.diag(estimated), 1.0)
        assert np.linalg.eigvalsh(estimated).min() > 0.0

    def test_estimate_margin_sigma_floors_a_constant_gate(self) -> None:
        scaled = estimate_margin_sigma(
            {gate: [1.0, 2.0, 3.0, 4.0] for gate in GATE_ORDER} | {"spa": [5.0, 5.0, 5.0, 5.0]}
        )
        assert scaled["spa"] == pytest.approx(0.1)
        assert scaled["pbo"] > 1.0

    def test_estimate_helpers_reject_tiny_populations(self) -> None:
        with pytest.raises(ValueError, match="at least 3 records"):
            estimate_sigma_eff([[1.0, 2.0, 3.0, 4.0, 5.0]] * 2)
        with pytest.raises(ValueError, match="at least 3 margins"):
            estimate_margin_sigma({gate: [1.0, 2.0] for gate in GATE_ORDER})


class TestSyntheticGroundTruth:
    """§4 item 3 — separate searches whose winner has a real edge from pure noise."""

    @staticmethod
    def _auroc(genuine: list[float], noise: list[float]) -> float:
        wins = sum(1.0 if g > n else 0.5 if g == n else 0.0 for g in genuine for n in noise)
        return wins / (len(genuine) * len(noise))

    @staticmethod
    def _search(
        rng: np.random.Generator, *, genuine: bool, n_trials: int, bars: int
    ) -> tuple[np.ndarray, np.ndarray, float]:
        """Run one parameter search; return (matrix, reported returns, pre-Phi DSR).

        A genuine record is one where the prior candidate (column 0) carries the
        edge and is the strategy reported — as a pre-registered hypothesis would
        be. A noise record has no edge anywhere, so what gets reported is simply
        the best in-sample column: the selection effect the gate exists to deflate.

        Search width is capped at a few tens of trials so a five-year sample can
        actually clear the deflation benchmark. The document's LogUniform(20, 5000)
        sweep is exercised by the search-size sensitivity test instead — with 5000
        trials and one year of data, *no* realistic edge should survive, and a
        harness asserting otherwise would be testing the wrong thing.
        """
        target = rng.uniform(0.5, 2.5) if genuine else 0.0
        matrix = rng.normal(0.0, 0.01, size=(bars, n_trials))
        matrix[:, 0] += target / math.sqrt(_PERIODS_PER_YEAR) * 0.01
        if genuine:
            winner = matrix[:, 0]
        else:
            half = bars // 2
            sharpes = matrix[:half].mean(axis=0) / matrix[:half].std(axis=0, ddof=1)
            winner = matrix[:, int(np.argmax(sharpes))]
        statistic = deflated_sharpe_ratio(winner, n_trials=effective_trial_count(matrix))
        return matrix, winner, statistic.pre_phi_statistic

    def test_dsr_margin_separates_edge_from_noise(self) -> None:
        rng = np.random.default_rng(2026)
        genuine, noise = [], []
        for _ in range(25):
            genuine.append(self._search(rng, genuine=True, n_trials=40, bars=1260)[2])
            noise.append(self._search(rng, genuine=False, n_trials=40, bars=1260)[2])
        auroc = self._auroc(genuine, noise)
        # Observed 0.90 on this seed. The paper reports 0.988 for its
        # corrected-DSR baseline on a far larger harness; this floor exists to
        # catch a broken gate, not to pin the value.
        assert auroc >= 0.8
        assert sum(genuine) / len(genuine) > sum(noise) / len(noise)

    def test_aggregate_score_separates_edge_from_noise(self) -> None:
        rng = np.random.default_rng(99)
        genuine: list[float] = []
        noise: list[float] = []
        for index in range(8):
            for target, bucket in ((True, genuine), (False, noise)):
                matrix, winner, _ = self._search(rng, genuine=target, n_trials=20, bars=1260)
                report = evaluate_gates(
                    dsr=deflated_sharpe_ratio(winner, n_trials=effective_trial_count(matrix)),
                    pbo=pbo_cscv(matrix, n_blocks=6),
                    spa=spa_test(matrix, n_bootstrap=100, seed=index),
                    mintrl=min_track_record_length(winner),
                    regime=regime_stability(
                        [float(stats.sharpe_ratio(chunk)) for chunk in np.array_split(winner, 4)]
                    ),
                )
                assert report.s is not None
                bucket.append(report.s)
        auroc = self._auroc(genuine, noise)
        # Observed 0.95-1.0 on this seed; floor set well below to catch regressions.
        assert auroc >= 0.75
