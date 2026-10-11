"""Tests for the ledger→verdict gate (``validation/validate.py``).

The unit-level properties live with each module; what is tested here is the
composition — that a persisted search produces a verdict, that the verdict is what
the underlying gates say it should be for a search with a real edge versus a search
over noise, and that the fail-closed rules survive the wiring.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from finrobot.engine.backtest.validation import (
    CostModel,
    TrialLedger,
    ValidationConfig,
    build_ledger_from_search,
    validate_ledger,
)

BARS = 1260
FOLDS = [630, 1260]
TRIALS = 12
COST = CostModel(version="flat-2bps-v1", per_side_bps=2.0, description="test")


def _search(*, genuine: bool, seed: int, trials: int = TRIALS, bars: int = BARS) -> np.ndarray:
    rng = np.random.default_rng(seed)
    matrix = rng.normal(0.0, 0.01, size=(bars, trials))
    if genuine:
        matrix[:, 2] += 2.5 / math.sqrt(252) * 0.01
    return matrix


def _ledger(matrix: np.ndarray, **overrides: object) -> TrialLedger:
    bars = matrix.shape[0]
    kwargs: dict[str, object] = {
        "strategy": "sma_crossover",
        "tickers": ["AAPL"],
        "trial_returns": matrix,
        "fold_boundaries": [bars // 2, bars],
        "params_by_trial": [{"lookback": 10 + index} for index in range(matrix.shape[1])],
        "cost_model": COST,
        "created_utc": "2026-10-10T00:00:00+00:00",
    }
    kwargs.update(overrides)
    return build_ledger_from_search(**kwargs)  # type: ignore[arg-type]


GENUINE = _ledger(_search(genuine=True, seed=7))
NOISE = _ledger(_search(genuine=False, seed=11))
FAST = ValidationConfig(n_blocks=6, spa_bootstrap=200)


class TestBuildLedgerFromSearch:
    def test_fold_structure_follows_the_boundaries(self) -> None:
        assert GENUINE.n_trials == TRIALS
        assert GENUINE.n_bars == BARS
        assert GENUINE.fold_offsets() == FOLDS
        assert [fold.n_bars for fold in GENUINE.trials[0].folds] == [630, 630]

    def test_pre_phi_statistic_is_stored_at_construction(self) -> None:
        """The §2.11 hard rule: u is stored when the DSR is computed, not later."""
        assert GENUINE.missing_pre_phi() == []
        for record in GENUINE.trials:
            assert record.pre_phi_dsr is not None
            assert math.isfinite(record.pre_phi_dsr)
        # The winner's statistic is a real z-scale number, not a saturation artifact.
        assert GENUINE.trials[2].pre_phi_dsr is not None
        assert GENUINE.trials[2].pre_phi_dsr > 1.0

    def test_skipping_the_statistic_leaves_it_absent(self) -> None:
        ledger = _ledger(_search(genuine=False, seed=3), compute_pre_phi_dsr=False)
        assert ledger.missing_pre_phi() == [record.trial_id for record in ledger.trials]

    def test_ledger_round_trips_through_jsonl(self, tmp_path: pytest.TempPathFactory) -> None:
        path = tmp_path / "trials.jsonl"  # type: ignore[operator]
        GENUINE.write_jsonl(path)
        assert TrialLedger.read_jsonl(path) == GENUINE

    def test_return_matrix_columns_are_the_trials(self) -> None:
        matrix = GENUINE.return_matrix()
        assert matrix.shape == (BARS, TRIALS)
        assert matrix[:, 0][:5].tolist() == pytest.approx(GENUINE.trials[0].folds[0].returns[:5])

    @pytest.mark.parametrize(
        ("overrides", "match"),
        [
            ({"params_by_trial": [{"a": 1}]}, "params_by_trial has 1 entries"),
            ({"objective_by_trial": [1.0, 2.0]}, "objective_by_trial has 2 entries"),
            ({"fold_boundaries": [630, 1200]}, "must end at n_bars=1260"),
            ({"fold_boundaries": [0, 630]}, "strictly increasing"),
            ({"fold_boundaries": []}, "at least one fold"),
            (
                {"created_utc": "x", "trial_returns": np.full((BARS, TRIALS), float("nan"))},
                "non-finite",
            ),
            ({"trial_returns": np.zeros((BARS,))}, "must be 2-D"),
        ],
    )
    def test_rejects_inconsistent_inputs(self, overrides: dict[str, object], match: str) -> None:
        with pytest.raises(ValueError, match=match):
            _ledger(_search(genuine=False, seed=5), **overrides)


class TestValidateLedger:
    def test_a_real_edge_seals(self) -> None:
        report = validate_ledger(GENUINE, config=FAST)
        assert report.seal is True
        assert report.display is not None and report.display >= 80.0
        assert report.verdict_consistent is True

    def test_a_noise_search_does_not_seal(self) -> None:
        report = validate_ledger(NOISE, config=FAST)
        assert report.seal is False
        assert report.display is not None and report.display < 80.0
        # The winner is the best-looking of twelve noise trials, so the gates that
        # know about the search must reject it.
        assert {margin.gate for margin in report.margins if not margin.passed} >= {"dsr", "spa"}

    def test_deterministic_for_a_given_config(self) -> None:
        first = validate_ledger(NOISE, config=FAST)
        assert validate_ledger(NOISE, config=FAST) == first

    def test_winner_selection_is_the_best_sharpe_by_default(self) -> None:
        report = validate_ledger(GENUINE, config=FAST)
        assert any("winner trial 2 of 12" in warning for warning in report.warnings)

    def test_explicit_winner_changes_the_scored_strategy(self) -> None:
        default = validate_ledger(GENUINE, config=FAST)
        other = validate_ledger(GENUINE, winner_trial_id=0, config=FAST)
        assert any("winner trial 0 of 12" in warning for warning in other.warnings)
        assert other.s != default.s

    def test_unknown_winner_id_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="not in the ledger"):
            validate_ledger(GENUINE, winner_trial_id=999, config=FAST)

    def test_benchmark_must_align_bar_for_bar(self) -> None:
        with pytest.raises(ValueError, match="benchmark must have shape"):
            validate_ledger(GENUINE, benchmark=[0.0] * 10, config=FAST)

    def test_unaligned_benchmark_of_the_right_length_is_accepted(self) -> None:
        report = validate_ledger(GENUINE, benchmark=[0.0] * BARS, config=FAST)
        assert not any("no benchmark supplied" in warning for warning in report.warnings)

    def test_missing_pre_phi_recomputes_by_default_and_fails_closed_on_request(self) -> None:
        unstored = _ledger(_search(genuine=False, seed=11), compute_pre_phi_dsr=False)
        recomputed = validate_ledger(unstored, config=FAST)
        assert recomputed.display is not None
        assert any("recomputed" in warning for warning in recomputed.warnings)

        closed = validate_ledger(unstored, allow_recompute_pre_phi=False, config=FAST)
        assert closed.display is None
        assert closed.s is None
        assert any("fail closed" in warning for warning in closed.warnings)

    def test_single_fold_ledger_still_produces_a_report(self) -> None:
        single = _ledger(_search(genuine=True, seed=7), fold_boundaries=[BARS])
        report = validate_ledger(single, config=FAST)
        assert any("one fold" in warning for warning in report.warnings)
        assert report.display is not None

    def test_provenance_records_the_run(self) -> None:
        report = validate_ledger(NOISE, config=FAST)
        joined = " ".join(report.warnings)
        assert "effective independent trials" in joined
        assert "CSCV blocks: 6" in joined
        assert "SPA: 200 resamples" in joined
        assert "cost model: flat-2bps-v1" in joined
