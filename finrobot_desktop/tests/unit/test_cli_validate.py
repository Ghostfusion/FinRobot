"""Tests for ``finrobot validate`` and its cost grid.

The CLI is the human entry point to the gate (it is deliberately not an LLM tool:
a validator the model can optimise would be optimising the thing judging it), so
these tests cover the two surfaces a person actually uses — the report and the
cost grid — plus the fail-closed path when a ledger has no turnover to re-price.
"""

from __future__ import annotations

import json

import numpy as np
import pytest
from click.testing import CliRunner

from finrobot.cli import cli
from finrobot.engine.backtest.validation import (
    CostModel,
    TrialLedger,
    build_ledger_from_search,
)

N_BARS = 150


def _write_ledger(path, *, turnover: float | None) -> None:
    rng = np.random.default_rng(11)
    columns = [
        rng.normal(mean, spread, size=N_BARS)
        for mean, spread in ((0.0004, 0.01), (0.0006, 0.012), (0.0002, 0.009))
    ]
    ledger = build_ledger_from_search(
        strategy="sma_crossover",
        tickers=["SYNTH"],
        trial_returns=np.column_stack(columns),
        fold_boundaries=[N_BARS],
        params_by_trial=[
            {"fast": 5, "slow": 20},
            {"fast": 10, "slow": 30},
            {"fast": 20, "slow": 60},
        ],
        cost_model=CostModel(version="test-flat", per_side_bps=0.0, turnover=turnover),
        created_utc="2026-10-10T00:00:00Z",
    )
    ledger.write_jsonl(path)


@pytest.fixture()
def ledger_path(tmp_path):
    path = tmp_path / "trials.jsonl"
    _write_ledger(path, turnover=0.4)
    return path


class TestValidateCommand:
    def test_reports_the_gate(self, ledger_path) -> None:
        result = CliRunner().invoke(cli, ["validate", str(ledger_path)])
        assert result.exit_code == 0, result.output
        assert "MinervaScore" in result.output

    def test_cost_grid_flag_uses_the_corpus_grid(self, ledger_path) -> None:
        result = CliRunner().invoke(cli, ["validate", str(ledger_path), "--cost-grid"])
        assert result.exit_code == 0, result.output
        assert "Cost grid" in result.output
        # The bare flag means the document's 0/1/2/5/10 grid.
        for bps in ("0 bps", "1 bps", "2 bps", "5 bps", "10 bps"):
            assert bps in result.output

    def test_cost_bps_implies_the_grid_and_emits_one_json_document(self, ledger_path) -> None:
        result = CliRunner().invoke(
            cli, ["validate", str(ledger_path), "--cost-bps", "0,5", "--as-json"]
        )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert set(payload) == {"report", "cost_grid"}
        assert [level["per_side_bps"] for level in payload["cost_grid"]["levels"]] == [0.0, 5.0]
        assert payload["cost_grid"]["turnover"] == pytest.approx(0.4)

    def test_cost_grid_refuses_a_ledger_without_turnover(self, tmp_path) -> None:
        path = tmp_path / "no-turnover.jsonl"
        _write_ledger(path, turnover=None)
        result = CliRunner().invoke(cli, ["validate", str(path), "--cost-grid"])
        assert result.exit_code == 1
        assert "records no turnover" in result.output
        # And the same ledger scores fine when the caller states the assumption.
        supplied = CliRunner().invoke(
            cli, ["validate", str(path), "--cost-bps", "0,5", "--turnover", "0.25"]
        )
        assert supplied.exit_code == 0, supplied.output
        assert "supplied by the caller" in supplied.output

    def test_rejects_an_unparseable_grid(self, ledger_path) -> None:
        result = CliRunner().invoke(cli, ["validate", str(ledger_path), "--cost-bps", "abc"])
        assert result.exit_code == 1
        assert "Invalid --cost-bps" in result.output

    def test_unknown_trial_id_is_reported_not_a_traceback(self, ledger_path) -> None:
        result = CliRunner().invoke(cli, ["validate", str(ledger_path), "--trial-id", "99"])
        assert result.exit_code == 1
        assert "99" in result.output

    def test_ledger_round_trips_through_the_reader(self, ledger_path) -> None:
        """The file the CLI reads is the file the writer produced."""
        loaded = TrialLedger.read_jsonl(ledger_path)
        assert loaded.n_trials == 3
        assert loaded.n_bars == N_BARS
        assert loaded.cost_model.turnover == pytest.approx(0.4)
