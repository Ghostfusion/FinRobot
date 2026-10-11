"""Optimizer trial ledger — the persisted record the overfitting gates consume.

What this code does that raw LLM cannot: an LLM can describe PBO, the deflated
Sharpe ratio, and effective-trial counts, but it cannot *compute* them without
the raw material those gates consume — every parameter set an optimizer
evaluated, with that trial's per-fold net returns and its pre-Phi DSR statistic.
This module is that schema and its deterministic JSONL persistence: the ledger
is the single source of truth from which ``return_matrix()`` feeds combinatorial
cross-validation (PBO) and from which the pre-Phi statistic feeds DSR deflation
(arXiv:2608.23808v2 sec.2.11). The gates fail closed on a trial whose pre-Phi
statistic is missing, so that statistic is stored at DSR computation time and
never reconstructed from ``Phi(u)`` — ``Phi^-1(0)`` collapses to ~-4.75 and
destroys the ranking.

The cost-model version is recorded per ledger (arXiv:2602.00133v1, sec.2.12):
rankings flip once fees are included, so a result is comparable only to another
produced under the same cost model. Everything here is offline and
deterministic; ``created_utc`` is supplied by the caller.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path

import numpy as np
from pydantic import BaseModel, Field, field_validator, model_validator

from finrobot.engine.backtest.validation.overfitting import (
    deflated_sharpe_ratio,
    effective_trial_count,
)
from finrobot.engine.backtest.validation.stats import annualized_sharpe

__all__ = [
    "CostModel",
    "FoldResult",
    "TrialLedger",
    "TrialRecord",
    "build_ledger_from_search",
]


class CostModel(BaseModel):
    """The fee/cost configuration a ledger's net returns were produced under."""

    version: str = Field(description="Cost-model version tag, e.g. 'flat-2bps-v1'")
    per_side_bps: float = Field(ge=0, description="Per-side cost in basis points (>= 0)")
    description: str = ""

    @field_validator("version")
    @classmethod
    def _version_non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("cost model version must be non-empty")
        return v


class FoldResult(BaseModel):
    """One validation fold's per-bar NET returns for a single trial."""

    fold_index: int = Field(ge=0, description="0-based fold index within the trial")
    validate_start: str | None = Field(default=None, description="ISO date of the first bar")
    validate_end: str | None = Field(default=None, description="ISO date of the last bar")
    n_bars: int = Field(gt=0, description="Number of bars; equals len(returns)")
    returns: list[float] = Field(description="Per-bar NET returns, chronological")

    @model_validator(mode="after")
    def _check_n_bars(self) -> FoldResult:
        if self.n_bars != len(self.returns):
            raise ValueError(
                f"fold {self.fold_index}: n_bars={self.n_bars} != len(returns)={len(self.returns)}"
            )
        return self


class TrialRecord(BaseModel):
    """One evaluated parameter set and its per-fold out-of-sample returns."""

    trial_id: int = Field(ge=0, description="Unique within the ledger")
    params: dict[str, float | int | str] = Field(description="The parameter set evaluated")
    folds: list[FoldResult] = Field(description="Per-fold results, in fold order")
    pre_phi_dsr: float | None = Field(
        default=None,
        description="The pre-Phi statistic u of sec.2.11 (NOT Phi(u)); None => gates fail closed",
    )
    annualized_sharpe: float | None = None
    objective: float | None = Field(default=None, description="The optimizer's own objective value")

    @model_validator(mode="after")
    def _check_folds(self) -> TrialRecord:
        if not self.folds:
            raise ValueError(f"trial {self.trial_id} has no folds")
        for i, fold in enumerate(self.folds):
            if fold.fold_index != i:
                raise ValueError(
                    f"trial {self.trial_id}: fold at position {i} has fold_index "
                    f"{fold.fold_index}; folds must be 0-based contiguous ascending"
                )
        return self


class TrialLedger(BaseModel):
    """A full optimizer run: header metadata plus every evaluated trial."""

    schema_version: str = "1"
    strategy: str
    tickers: list[str]
    periods_per_year: int = 252
    cost_model: CostModel
    created_utc: str = Field(description="ISO-8601 UTC timestamp, supplied by the caller")
    trials: list[TrialRecord]

    @model_validator(mode="after")
    def _check_ledger(self) -> TrialLedger:
        if not self.trials:
            raise ValueError("ledger must contain at least one trial")
        ids: set[int] = set()
        for t in self.trials:
            if t.trial_id in ids:
                raise ValueError(f"duplicate trial_id {t.trial_id}")
            ids.add(t.trial_id)
        ref = self.trials[0]
        for t in self.trials[1:]:
            if len(t.folds) != len(ref.folds):
                raise ValueError(
                    f"trial {t.trial_id} has {len(t.folds)} folds but trial "
                    f"{ref.trial_id} has {len(ref.folds)}"
                )
            for i, (a, b) in enumerate(zip(t.folds, ref.folds, strict=True)):
                if a.n_bars != b.n_bars:
                    raise ValueError(
                        f"trial {t.trial_id} fold {i} has n_bars={a.n_bars} but trial "
                        f"{ref.trial_id} fold {i} has n_bars={b.n_bars}"
                    )
        for t in self.trials:
            try:
                json.dumps(t.params, sort_keys=True)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"trial {t.trial_id} params are not JSON-serialisable: {exc}"
                ) from exc
        try:
            json.dumps(self.tickers, sort_keys=True)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"tickers are not JSON-serialisable: {exc}") from exc
        return self

    @property
    def n_trials(self) -> int:
        """Number of trials in the ledger."""
        return len(self.trials)

    @property
    def n_bars(self) -> int:
        """Bars per trial (the common grid size)."""
        return sum(fold.n_bars for fold in self.trials[0].folds)

    def fold_offsets(self) -> list[int]:
        """Cumulative bar offsets; fold i spans ``[offsets[i-1], offsets[i])``."""
        offsets: list[int] = []
        total = 0
        for fold in self.trials[0].folds:
            total += fold.n_bars
            offsets.append(total)
        return offsets

    def return_matrix(self) -> np.ndarray:
        """``(n_bars, n_trials)`` float64 matrix; trials are columns."""
        columns = [[r for fold in t.folds for r in fold.returns] for t in self.trials]
        return np.asarray(columns, dtype=np.float64).T

    def missing_pre_phi(self) -> list[int]:
        """Trial ids whose ``pre_phi_dsr`` is ``None`` (the gates fail closed on these)."""
        return [t.trial_id for t in self.trials if t.pre_phi_dsr is None]

    def write_jsonl(self, path: Path) -> None:
        """Write the header on line 1 and one ``TrialRecord`` per following line."""
        lines = [self.model_dump_json(exclude={"trials"})]
        lines.extend(t.model_dump_json() for t in self.trials)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    @classmethod
    def read_jsonl(cls, path: Path) -> TrialLedger:
        """Reconstruct a ledger written by :meth:`write_jsonl` (blank lines tolerated)."""
        lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        if not lines:
            raise ValueError(f"ledger file '{path}' contains no header line")
        header = json.loads(lines[0])
        if not isinstance(header, dict):
            raise ValueError(f"ledger file '{path}' first line is not a JSON object")
        trials = [TrialRecord.model_validate_json(ln) for ln in lines[1:]]
        return cls(**header, trials=trials)


def build_ledger_from_search(
    *,
    strategy: str,
    tickers: Sequence[str],
    trial_returns: np.ndarray,
    fold_boundaries: Sequence[int],
    params_by_trial: Sequence[Mapping[str, float | int | str]],
    cost_model: CostModel,
    created_utc: str,
    periods_per_year: int = 252,
    objective_by_trial: Sequence[float] | None = None,
    compute_pre_phi_dsr: bool = True,
) -> TrialLedger:
    """Assemble a ledger from what a parameter search already holds in memory.

    ``trial_returns`` is ``(n_bars, n_trials)`` of per-bar NET returns and
    ``fold_boundaries`` are cumulative bar offsets, so fold ``i`` spans
    ``[boundaries[i - 1], boundaries[i])`` — the same convention
    :meth:`TrialLedger.fold_offsets` returns. All trials must share that grid,
    which is the invariant the ledger itself enforces.

    With ``compute_pre_phi_dsr`` (the default), each trial's §2.11 pre-Phi
    statistic is computed **here**, at construction, against the search's
    effective trial count (from :func:`effective_trial_count`, not the raw grid
    size). That ordering is the point of the function: once only ``Phi(u)`` is
    stored the statistic is gone for good — ``Phi^-1(0)`` collapses to about
    -4.75 — and the record is permanently unscorable. Pass
    ``compute_pre_phi_dsr=False`` only to reproduce that failure deliberately.
    """
    matrix: np.ndarray = np.asarray(trial_returns, dtype=np.float64)
    if matrix.ndim != 2:
        raise ValueError("trial_returns must be 2-D (rows = bars, columns = trials)")
    n_bars, n_trials = matrix.shape
    if n_trials < 1 or n_bars < 2:
        raise ValueError(f"trial_returns needs at least 2 bars and 1 trial, got {matrix.shape}")
    if not np.isfinite(matrix).all():
        raise ValueError("trial_returns contains non-finite values")
    if len(params_by_trial) != n_trials:
        raise ValueError(
            f"params_by_trial has {len(params_by_trial)} entries for {n_trials} trials"
        )
    if objective_by_trial is not None and len(objective_by_trial) != n_trials:
        raise ValueError(
            f"objective_by_trial has {len(objective_by_trial)} entries for {n_trials} trials"
        )

    boundaries = [int(value) for value in fold_boundaries]
    if not boundaries:
        raise ValueError("fold_boundaries must name at least one fold")
    if any(b <= a for a, b in zip([0, *boundaries], boundaries)):
        raise ValueError(f"fold_boundaries must be strictly increasing, got {boundaries}")
    if boundaries[-1] != n_bars:
        raise ValueError(
            f"fold_boundaries must end at n_bars={n_bars}, got {boundaries[-1]}; "
            "a partial fold would break the common grid the gates assume"
        )

    n_effective = effective_trial_count(matrix) if compute_pre_phi_dsr else 1.0
    edges = [0, *boundaries]
    records: list[TrialRecord] = []
    for index in range(n_trials):
        column = matrix[:, index]
        folds = [
            FoldResult(
                fold_index=fold,
                n_bars=edges[fold + 1] - edges[fold],
                returns=[float(value) for value in column[edges[fold] : edges[fold + 1]]],
            )
            for fold in range(len(boundaries))
        ]
        records.append(
            TrialRecord(
                trial_id=index,
                params=dict(params_by_trial[index]),
                folds=folds,
                pre_phi_dsr=(
                    deflated_sharpe_ratio(
                        column, n_trials=n_effective, periods_per_year=periods_per_year
                    ).pre_phi_statistic
                    if compute_pre_phi_dsr
                    else None
                ),
                annualized_sharpe=annualized_sharpe(column, periods_per_year=periods_per_year),
                objective=None if objective_by_trial is None else float(objective_by_trial[index]),
            )
        )

    return TrialLedger(
        strategy=strategy,
        tickers=list(tickers),
        periods_per_year=periods_per_year,
        cost_model=cost_model,
        created_utc=created_utc,
        trials=records,
    )
