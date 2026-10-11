"""Cost sensitivity — does the verdict survive trading costs? (§5.4, §2.12).

What this code does that raw LLM cannot: re-price an already-recorded trial
ledger across a grid of per-side costs and report the gate's verdict at each
level. A model can say "costs matter"; only arithmetic can say *where* the
verdict flips, and the corpus's own finding is that it flips inside a range —
weak signals die by 4-5 bps per side while stronger ones survive
(arXiv:2609.23703, arXiv:2507.18417) — so reporting one cost assumption is not an
answer to "is this real?".

Two choices are deliberate and stated rather than hidden:

* **Re-pricing needs a turnover, and without one the grid refuses.** The stored
  returns are net, so recovering gross requires the notional traded per bar. Where
  the ledger recorded it, the grid uses it; where it did not, the grid raises
  instead of inventing one, because a fabricated turnover would manufacture
  exactly the conclusion the caller is looking for.
* **An unpinned winner is re-selected at every cost level.** The question the grid
  answers is what the *search* would have concluded under those costs, and a
  different parameter set legitimately wins once costs move. Passing
  ``winner_trial_id`` pins one trial across the whole grid instead.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from pydantic import BaseModel, Field

from finrobot.engine.backtest.validation.ledger import (
    CostModel,
    TrialLedger,
    build_ledger_from_search,
)
from finrobot.engine.backtest.validation.minerva import MarginCalibration
from finrobot.engine.backtest.validation.stats import net_of_costs
from finrobot.engine.backtest.validation.validate import ValidationConfig, validate_ledger

__all__ = ["DEFAULT_BPS_GRID", "CostGridResult", "CostLevel", "cost_grid"]

#: The corpus's sensitivity grid, 0-10 bps per side (arXiv:2602.00080v1 Fig. 3).
DEFAULT_BPS_GRID: tuple[float, ...] = (0.0, 1.0, 2.0, 5.0, 10.0)

#: Basis points per unit return, for inverting ``net_of_costs``' drag.
_BPS_PER_UNIT = 10_000.0


def _cost_drag(per_side_bps: float, turnover: float) -> float:
    """Per-bar return cost of a round trip, matching :func:`net_of_costs`."""
    return 2.0 * per_side_bps / _BPS_PER_UNIT * turnover


def _index_of_trial_id(ledger: TrialLedger, trial_id: int) -> int:
    ids = [record.trial_id for record in ledger.trials]
    if trial_id not in ids:
        raise ValueError(f"winner_trial_id {trial_id} is not in the ledger (ids: {ids})")
    return ids.index(trial_id)


def _best_sharpe_index(ledger: TrialLedger) -> int:
    """Position of the best annualized Sharpe — the same rule ``validate_ledger`` uses.

    Mirrored rather than re-derived: if the two rules drift, the grid would score a
    different trial than the caller's own ``finrobot validate`` does.
    """
    annualized = [
        record.annualized_sharpe if record.annualized_sharpe is not None else -np.inf
        for record in ledger.trials
    ]
    return int(np.argmax(annualized))


class CostLevel(BaseModel):
    """The gate's verdict at one per-side cost level."""

    per_side_bps: float
    sealed: bool = Field(description="True iff every gate passed at this cost level")
    display: float | None = Field(description="0-100 display; None when a gate failed closed")
    winner_trial_id: int = Field(description="The trial scored at this level")
    winner_annualized_sharpe: float | None = None


class CostGridResult(BaseModel):
    """The gate's verdict across a grid of per-side costs."""

    levels: list[CostLevel]
    turnover: float = Field(description="Notional traded per bar as a fraction of capital")
    repriced_from_bps: float = Field(
        description="The per-side rate the ledger's returns were net of"
    )
    notes: list[str] = Field(default_factory=list)

    @property
    def breaks_at(self) -> float | None:
        """The first cost level whose seal fails, or ``None`` if every level sealed.

        The useful output: "this edge survives to 5 bps and dies at 10" is a claim
        about a strategy; "this edge has a Sharpe of 2.85" is a claim about a
        frictionless world.
        """
        for level in self.levels:
            if not level.sealed:
                return level.per_side_bps
        return None

    def format_summary(self) -> str:
        """Human-readable block, mirroring the other result formatters."""
        lines = [
            f"Cost grid (turnover {self.turnover:.4g}/bar, re-priced from "
            f"{self.repriced_from_bps:g} bps per side)"
        ]
        for level in self.levels:
            display = "n/a (fail closed)" if level.display is None else f"{level.display:5.1f}"
            seal = "SEAL" if level.sealed else "open"
            sharpe = (
                "n/a"
                if level.winner_annualized_sharpe is None
                else f"{level.winner_annualized_sharpe:+.3f}"
            )
            lines.append(
                f"  {level.per_side_bps:5g} bps  display={display}  {seal}  "
                f"trial {level.winner_trial_id}  Sharpe={sharpe}"
            )
        breaks = self.breaks_at
        lines.append(
            "  survives the whole grid"
            if breaks is None
            else f"  fails from {breaks:g} bps per side onward"
        )
        for note in self.notes:
            lines.append(f"  note: {note}")
        return "\n".join(lines)


def cost_grid(
    ledger: TrialLedger,
    *,
    bps_grid: Sequence[float] = DEFAULT_BPS_GRID,
    turnover: float | None = None,
    winner_trial_id: int | None = None,
    benchmark: Sequence[float] | None = None,
    config: ValidationConfig | None = None,
    calibration: MarginCalibration | None = None,
) -> CostGridResult:
    """Score a ledger at every cost level in ``bps_grid``.

    Each level is a full gate run over a ledger rebuilt from re-priced returns,
    with the pre-Phi statistics recomputed — not reused — because they were
    derived from the previous cost level's Sharpe. Re-pricing alone would leave the
    ledger internally inconsistent, which is the failure mode this package fails
    closed on everywhere else.
    """
    bps_values = [float(value) for value in bps_grid]
    if not bps_values:
        raise ValueError("bps_grid must contain at least one cost level")
    if any(value < 0.0 for value in bps_values):
        raise ValueError(f"bps_grid entries must be non-negative, got {bps_values!r}")
    if len(set(bps_values)) != len(bps_values):
        raise ValueError(f"bps_grid contains duplicates: {bps_values!r}")

    effective_turnover = ledger.cost_model.turnover if turnover is None else turnover
    if effective_turnover is None:
        raise ValueError(
            "this ledger records no turnover and none was supplied: re-pricing its returns "
            "would mean inventing the notional traded, which is the number the grid is "
            "supposed to inform — pass turnover= to state the assumption explicitly"
        )
    if effective_turnover < 0.0:
        raise ValueError(f"turnover must be non-negative, got {effective_turnover!r}")

    stored_bps = ledger.cost_model.per_side_bps
    # Invert the netting: the ledger's returns are net of its own cost drag.
    gross: np.ndarray = ledger.return_matrix() + _cost_drag(stored_bps, effective_turnover)
    boundaries = ledger.fold_offsets()
    params_by_trial = [dict(record.params) for record in ledger.trials]
    objectives = [record.objective for record in ledger.trials]
    objective_by_trial = (
        [float(value) for value in objectives if value is not None]
        if all(value is not None for value in objectives)
        else None
    )
    pinned_index = None if winner_trial_id is None else _index_of_trial_id(ledger, winner_trial_id)
    notes = [
        f"re-priced from the ledger's stored {stored_bps:g} bps per side and a turnover of "
        f"{effective_turnover:.4g} of capital per bar"
    ]
    if ledger.cost_model.turnover is None:
        notes.append("turnover was supplied by the caller, not measured in the ledger")
    if pinned_index is None:
        notes.append("the winner is re-selected at each level; pass winner_trial_id to pin one")
    else:
        notes.append(f"the winner is pinned to the ledger's trial at position {pinned_index}")

    levels: list[CostLevel] = []
    for bps in bps_values:
        columns = [
            net_of_costs(gross[:, index], per_side_bps=bps, turnover=effective_turnover)
            for index in range(gross.shape[1])
        ]
        recosted = build_ledger_from_search(
            strategy=ledger.strategy,
            tickers=list(ledger.tickers),
            trial_returns=np.column_stack(
                [np.asarray(column, dtype=np.float64) for column in columns]
            ),
            fold_boundaries=boundaries,
            params_by_trial=params_by_trial,
            cost_model=CostModel(
                version=f"cost-grid-{bps:g}bps",
                per_side_bps=bps,
                turnover=effective_turnover,
                description="re-priced by cost_grid; see the grid's notes",
            ),
            created_utc=ledger.created_utc,
            periods_per_year=ledger.periods_per_year,
            objective_by_trial=objective_by_trial,
        )
        winner_index = _best_sharpe_index(recosted) if pinned_index is None else pinned_index
        winner_record = recosted.trials[winner_index]
        report = validate_ledger(
            recosted,
            winner_trial_id=winner_record.trial_id,
            benchmark=benchmark,
            config=config,
            calibration=calibration,
        )
        levels.append(
            CostLevel(
                per_side_bps=bps,
                sealed=report.seal,
                display=report.display,
                winner_trial_id=winner_record.trial_id,
                winner_annualized_sharpe=winner_record.annualized_sharpe,
            )
        )

    return CostGridResult(
        levels=levels,
        turnover=effective_turnover,
        repriced_from_bps=stored_bps,
        notes=notes,
    )
