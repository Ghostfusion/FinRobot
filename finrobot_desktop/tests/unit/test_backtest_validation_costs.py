"""Tests for the cost sensitivity grid.

The grid exists so a verdict is a range rather than one frictionless number, so
these tests are about the two things that could quietly turn it into decoration:
the re-pricing arithmetic (does 5 bps mean 5 bps?) and the fail-closed rule when
the notional traded is unknown.
"""

from __future__ import annotations

import numpy as np
import pytest

from finrobot.engine.backtest.validation import (
    CostModel,
    TrialLedger,
    build_ledger_from_search,
    cost_grid,
)

N_BARS = 250


def _ledger(
    *,
    steady: np.ndarray,
    jumpy: np.ndarray,
    turnover: float | None,
    per_side_bps: float = 0.0,
) -> TrialLedger:
    return build_ledger_from_search(
        strategy="sma_crossover",
        tickers=["SYNTH"],
        trial_returns=np.column_stack([steady, jumpy]),
        fold_boundaries=[N_BARS],
        params_by_trial=[{"fast": 5, "slow": 20}, {"fast": 10, "slow": 30}],
        cost_model=CostModel(version="test-flat", per_side_bps=per_side_bps, turnover=turnover),
        created_utc="2026-10-10T00:00:00Z",
    )


def _steady(seed: int = 1, mean: float = 0.001, spread: float = 0.0005) -> np.ndarray:
    return np.random.default_rng(seed).normal(mean, spread, size=N_BARS)


def _jumpy(seed: int = 2, mean: float = 0.004, spread: float = 0.01) -> np.ndarray:
    return np.random.default_rng(seed).normal(mean, spread, size=N_BARS)


class TestCostGrid:
    def test_scores_every_level_in_order(self) -> None:
        ledger = _ledger(steady=_steady(), jumpy=_jumpy(), turnover=0.25)
        result = cost_grid(ledger, bps_grid=(0.0, 2.0, 5.0))
        assert [level.per_side_bps for level in result.levels] == [0.0, 2.0, 5.0]
        assert result.turnover == 0.25
        assert result.repriced_from_bps == 0.0
        assert all(level.display is not None for level in result.levels)
        assert all(level.winner_annualized_sharpe is not None for level in result.levels)

    def test_costs_erode_the_winning_sharpe(self) -> None:
        ledger = _ledger(steady=_steady(), jumpy=_jumpy(), turnover=1.0)
        result = cost_grid(ledger, bps_grid=(0.0, 5.0, 10.0))
        sharpes = [level.winner_annualized_sharpe for level in result.levels]
        first, last = sharpes[0], sharpes[-1]
        assert first is not None and last is not None
        assert first > last

    def test_a_crushing_cost_level_fails_the_seal_and_names_the_break(self) -> None:
        ledger = _ledger(steady=_steady(), jumpy=_jumpy(), turnover=1.0)
        result = cost_grid(ledger, bps_grid=(0.0, 200.0))
        assert result.levels[-1].sealed is False
        assert result.breaks_at == 200.0
        assert "fails from 200 bps" in result.format_summary()

    def test_winner_is_reselected_per_level_but_pinned_on_request(self) -> None:
        """At 50 bps the low-volatility trial's edge is gone and the other wins.

        That is the behaviour the grid is for: the question is what the search
        would have concluded under those costs. Pinning a trial answers a
        different question, so it must be available and must hold.
        """
        ledger = _ledger(steady=_steady(), jumpy=_jumpy(), turnover=1.0)
        unpinned = cost_grid(ledger, bps_grid=(0.0, 50.0))
        assert unpinned.levels[0].winner_trial_id == 0  # steady wins while it is free
        assert unpinned.levels[1].winner_trial_id == 1  # costs hand it to the jumpy one

        pinned = cost_grid(ledger, bps_grid=(0.0, 50.0), winner_trial_id=0)
        assert [level.winner_trial_id for level in pinned.levels] == [0, 0]
        assert any("pinned" in note for note in pinned.notes)

    def test_refuses_to_invent_a_turnover(self) -> None:
        """The stored returns are net, so gross cannot be recovered without it."""
        ledger = _ledger(steady=_steady(), jumpy=_jumpy(), turnover=None)
        with pytest.raises(ValueError, match="records no turnover"):
            cost_grid(ledger)
        supplied = cost_grid(ledger, turnover=0.3)
        assert any("supplied by the caller" in note for note in supplied.notes)

    def test_rejects_bad_grids_and_unknown_winners(self) -> None:
        ledger = _ledger(steady=_steady(), jumpy=_jumpy(), turnover=0.5)
        with pytest.raises(ValueError, match="at least one cost level"):
            cost_grid(ledger, bps_grid=())
        with pytest.raises(ValueError, match="non-negative"):
            cost_grid(ledger, bps_grid=(0.0, -1.0))
        with pytest.raises(ValueError, match="duplicates"):
            cost_grid(ledger, bps_grid=(1.0, 1.0))
        with pytest.raises(ValueError, match="winner_trial_id 7"):
            cost_grid(ledger, bps_grid=(0.0,), winner_trial_id=7)
        with pytest.raises(ValueError, match="turnover must be non-negative"):
            cost_grid(ledger, turnover=-0.1)
