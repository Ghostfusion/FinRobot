"""Tests for the backtest-validation trial ledger.

Verifies grid validation, the return matrix / fold offsets the overfitting
gates consume, missing pre-Phi reporting, and JSONL round-trip equality.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from finrobot.engine.backtest.validation.ledger import (
    CostModel,
    FoldResult,
    TrialLedger,
    TrialRecord,
)


def _fold(index: int, returns: list[float], n_bars: int | None = None) -> FoldResult:
    return FoldResult(
        fold_index=index,
        validate_start="2024-01-01",
        validate_end="2024-06-30",
        n_bars=len(returns) if n_bars is None else n_bars,
        returns=returns,
    )


def _ledger(**overrides: object) -> TrialLedger:
    base: dict[str, object] = {
        "strategy": "sma_crossover",
        "tickers": ["AAPL", "MSFT"],
        "cost_model": CostModel(version="flat-2bps-v1", per_side_bps=2.0),
        "created_utc": "2026-10-10T00:00:00+00:00",
        "trials": [
            TrialRecord(
                trial_id=0,
                params={"fast": 10, "slow": 30.5, "mode": "sma"},
                folds=[_fold(0, [0.01, 0.02]), _fold(1, [0.03, 0.04])],
                pre_phi_dsr=1.25,
                annualized_sharpe=0.9,
                objective=0.42,
            ),
            TrialRecord(
                trial_id=1,
                params={"fast": 5, "slow": 20.0, "mode": "sma"},
                folds=[_fold(0, [0.05, 0.06]), _fold(1, [0.07, 0.08])],
                pre_phi_dsr=None,
                annualized_sharpe=0.5,
                objective=0.31,
            ),
            TrialRecord(
                trial_id=2,
                params={"fast": 15, "slow": 40.0, "mode": "ema"},
                folds=[_fold(0, [0.09, 0.10]), _fold(1, [0.11, 0.12])],
                pre_phi_dsr=-0.3,
                annualized_sharpe=0.2,
                objective=0.11,
            ),
        ],
    }
    base.update(overrides)
    return TrialLedger(**base)  # type: ignore[arg-type]


class TestGridAndProperties:
    def test_counts_and_offsets(self) -> None:
        led = _ledger()
        assert led.n_trials == 3
        assert led.n_bars == 4
        assert led.fold_offsets() == [2, 4]

    def test_return_matrix_shape_dtype_and_values(self) -> None:
        mat = _ledger().return_matrix()
        assert mat.shape == (4, 3)
        assert mat.dtype == np.float64
        np.testing.assert_array_equal(mat[:, 0], [0.01, 0.02, 0.03, 0.04])
        np.testing.assert_array_equal(mat[:, 1], [0.05, 0.06, 0.07, 0.08])
        np.testing.assert_array_equal(mat[:, 2], [0.09, 0.10, 0.11, 0.12])

    def test_missing_pre_phi(self) -> None:
        assert _ledger().missing_pre_phi() == [1]

    def test_missing_pre_phi_empty_when_all_present(self) -> None:
        led = _ledger()
        for trial in led.trials:
            trial.pre_phi_dsr = 0.5
        assert led.missing_pre_phi() == []


class TestValidation:
    def test_empty_trials_raises(self) -> None:
        with pytest.raises(ValueError, match="at least one trial"):
            _ledger(trials=[])

    def test_duplicate_trial_id_raises(self) -> None:
        led = _ledger()
        with pytest.raises(ValueError, match="duplicate trial_id 1"):
            _ledger(trials=[led.trials[0], led.trials[1], led.trials[1]])

    def test_different_fold_count_raises(self) -> None:
        led = _ledger()
        short = TrialRecord(
            trial_id=7,
            params={"fast": 1},
            folds=[_fold(0, [0.1, 0.2])],
        )
        with pytest.raises(ValueError, match="trial 7 has 1 folds"):
            _ledger(trials=[led.trials[0], short])

    def test_different_n_bars_raises(self) -> None:
        led = _ledger()
        mismatched = TrialRecord(
            trial_id=8,
            params={"fast": 1},
            folds=[_fold(0, [0.1, 0.2, 0.3]), _fold(1, [0.4, 0.5])],
        )
        with pytest.raises(ValueError, match="trial 8 fold 0 has n_bars=3"):
            _ledger(trials=[led.trials[0], mismatched])

    def test_negative_per_side_bps_raises(self) -> None:
        with pytest.raises(ValueError, match="per_side_bps"):
            CostModel(version="flat-v1", per_side_bps=-1.0)

    def test_empty_cost_version_raises(self) -> None:
        with pytest.raises(ValueError, match="non-empty"):
            CostModel(version="   ", per_side_bps=1.0)

    def test_n_bars_must_match_returns(self) -> None:
        with pytest.raises(ValueError, match="n_bars=5 != len"):
            _fold(0, [0.1, 0.2], n_bars=5)

    def test_fold_index_must_be_contiguous(self) -> None:
        with pytest.raises(ValueError, match="contiguous ascending"):
            TrialRecord(trial_id=0, params={}, folds=[_fold(1, [0.1])])


class TestJsonlRoundTrip:
    def test_round_trip_equality(self, tmp_path: Path) -> None:
        led = _ledger()
        path = tmp_path / "ledger.jsonl"
        led.write_jsonl(path)
        restored = TrialLedger.read_jsonl(path)
        assert restored == led
        # Mixed param types survive the JSON round-trip unchanged.
        assert restored.trials[0].params == {"fast": 10, "slow": 30.5, "mode": "sma"}
        assert restored.trials[1].pre_phi_dsr is None
        assert restored.trials[2].objective == 0.11

    def test_blank_lines_tolerated(self, tmp_path: Path) -> None:
        led = _ledger()
        path = tmp_path / "ledger.jsonl"
        led.write_jsonl(path)
        path.write_text(path.read_text(encoding="utf-8") + "\n\n", encoding="utf-8")
        assert TrialLedger.read_jsonl(path) == led

    def test_empty_file_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "empty.jsonl"
        path.write_text("", encoding="utf-8")
        with pytest.raises(ValueError, match="no header line"):
            TrialLedger.read_jsonl(path)

    def test_non_object_first_line_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.jsonl"
        path.write_text("[1, 2, 3]\n", encoding="utf-8")
        with pytest.raises(ValueError, match="not a JSON object"):
            TrialLedger.read_jsonl(path)
