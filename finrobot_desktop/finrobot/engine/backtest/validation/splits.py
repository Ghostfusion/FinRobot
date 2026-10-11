"""Walk-forward and combinatorial purged cross-validation splits.

What this code does that raw LLM cannot: it materialises the exact, leak-free
train/validate index windows that the backtest validation gate
(``finrobot.engine.backtest.validation``) scores against. An LLM asked to
"split the history into train and validation" silently overlaps the two
windows, forgets the embargo after the training window, or mis-counts the
number of combinatorial paths --- and each of those mistakes inflates every
downstream gate (GT-Score, PBO, DSR). Here the windows are arithmetic on bar
indices, so a split is reproducible and auditable.

The protocol is the fixed structure of ``strategies/qfin-st/
backtest-methodology.md`` §2.3-2.4: train 4y / validate 2y / step 1y with a
30-day embargo between training and validation, and the combinatorial purged
cross-validation whose distinct-path count is ``phi[N,k] = (k/N) * C(N,k)``
(N=6, k=2 gives 15 splits but only 5 distinct paths --- fold count is not
effective sample size). All indices are bar indices into ``[0, n_bars)`` and
all ranges are half-open ``[start, end)``.
"""

from __future__ import annotations

from fractions import Fraction
from itertools import combinations
from math import comb

import numpy as np
import numpy.typing as npt
from pydantic import BaseModel, ConfigDict, Field, model_validator

__all__ = [
    "CombinatorialPurgedConfig",
    "CombinatorialSplit",
    "Split",
    "WalkForwardConfig",
    "combinatorial_purged_splits",
    "group_bounds",
    "n_backtest_paths",
    "walk_forward_splits",
]


class WalkForwardConfig(BaseModel):
    """Rolling train/embargo/validate window geometry (§2.3)."""

    train_bars: int = Field(gt=0, description="Length of the training window, in bars.")
    validate_bars: int = Field(gt=0, description="Length of the validation window, in bars.")
    step_bars: int = Field(gt=0, description="Bars the window advances between consecutive splits.")
    embargo_bars: int = Field(
        default=30,
        ge=0,
        description="Bars dropped between train_end and validate_start to stop leakage.",
    )

    @classmethod
    def from_periods(
        cls,
        *,
        bars_per_year: int = 252,
        train_years: float = 4.0,
        validate_years: float = 2.0,
        step_years: float = 1.0,
        embargo_days: int = 30,
    ) -> WalkForwardConfig:
        """Build the §2.3 default (4y/2y/1y, 30-day embargo) from year counts.

        ``bars_per_year`` maps a year to its bar count (252 trading days by
        default) and each ``*_years`` is rounded to the nearest bar. The
        embargo is passed through as a bar count: ``embargo_days`` becomes
        ``embargo_bars`` directly, since the gate is defined on bar indices and
        the caller may pass any calendar-to-bar conversion it prefers.
        """
        return cls(
            train_bars=round(train_years * bars_per_year),
            validate_bars=round(validate_years * bars_per_year),
            step_bars=round(step_years * bars_per_year),
            embargo_bars=embargo_days,
        )


class Split(BaseModel):
    """One walk-forward split: half-open train, embargo and validate windows."""

    model_config = ConfigDict(frozen=True)

    index: int = Field(description="0-based sequential split number.")
    train_start: int = Field(description="Inclusive start of the training window.")
    train_end: int = Field(description="Exclusive end of the training window.")
    embargo_start: int = Field(description="Inclusive start of the embargo gap.")
    embargo_end: int = Field(description="Exclusive end of the embargo gap.")
    validate_start: int = Field(description="Inclusive start of the validation window.")
    validate_end: int = Field(description="Exclusive end of the validation window.")

    @model_validator(mode="after")
    def _check_geometry(self) -> Split:
        if self.train_end != self.embargo_start:
            raise ValueError("embargo_start must equal train_end")
        if self.embargo_end != self.validate_start:
            raise ValueError("validate_start must equal embargo_end")
        if self.train_start > self.train_end:
            raise ValueError("train_start must be <= train_end")
        if self.validate_start > self.validate_end:
            raise ValueError("validate_start must be <= validate_end")
        return self

    def train_slice(self) -> slice:
        """Python slice selecting the training bars from a bar-indexed array."""
        return slice(self.train_start, self.train_end)

    def validate_slice(self) -> slice:
        """Python slice selecting the validation bars from a bar-indexed array."""
        return slice(self.validate_start, self.validate_end)


def walk_forward_splits(n_bars: int, config: WalkForwardConfig | None = None) -> list[Split]:
    """Sequential walk-forward splits over ``[0, n_bars)`` (§2.3).

    Split ``i`` uses ``train_start = i * step_bars``, ``train_end =
    train_start + train_bars``, an embargo ``[train_end, train_end +
    embargo_bars)`` and ``validate_start = train_end + embargo_bars``, with
    ``validate_end = validate_start + validate_bars``. A split is emitted only
    while ``validate_end <= n_bars`` (a window is never truncated).

    A history too short to host even the first full split returns ``[]`` --- the
    friendlier behaviour the methodology implies, since a short series simply
    yields no usable split. ``ValueError`` is raised only when ``n_bars < 0``.

    ``config=None`` uses :meth:`WalkForwardConfig.from_periods` defaults (the
    4y/2y/1y/30d structure).
    """
    if n_bars < 0:
        raise ValueError(f"n_bars must be >= 0, got {n_bars}")
    cfg = config if config is not None else WalkForwardConfig.from_periods()
    splits: list[Split] = []
    index = 0
    while True:
        train_start = index * cfg.step_bars
        train_end = train_start + cfg.train_bars
        embargo_start = train_end
        embargo_end = embargo_start + cfg.embargo_bars
        validate_start = embargo_end
        validate_end = validate_start + cfg.validate_bars
        if validate_end > n_bars:
            break
        splits.append(
            Split(
                index=index,
                train_start=train_start,
                train_end=train_end,
                embargo_start=embargo_start,
                embargo_end=embargo_end,
                validate_start=validate_start,
                validate_end=validate_end,
            )
        )
        index += 1
    return splits


class CombinatorialPurgedConfig(BaseModel):
    """CPCV geometry: ``n_groups`` contiguous groups, ``n_test_groups`` held out (§2.4)."""

    n_groups: int = Field(
        ge=2, description="Number of contiguous groups the timeline is partitioned into."
    )
    n_test_groups: int = Field(
        ge=1, description="Groups held out as test per split; must satisfy 1 <= k < n_groups."
    )
    embargo_bars: int = Field(
        default=0,
        ge=0,
        description="Bars dropped immediately after each test group's end.",
    )
    purge_bars: int = Field(
        default=0,
        ge=0,
        description="Bars dropped on each side of every test-group boundary.",
    )

    @model_validator(mode="after")
    def _check_k(self) -> CombinatorialPurgedConfig:
        if self.n_test_groups >= self.n_groups:
            raise ValueError(
                f"n_test_groups ({self.n_test_groups}) must be < n_groups ({self.n_groups})"
            )
        return self


def group_bounds(n_bars: int, n_groups: int) -> list[tuple[int, int]]:
    """Partition ``[0, n_bars)`` into ``n_groups`` contiguous half-open groups.

    When ``n_bars % n_groups != 0`` the remainder bars go to the EARLIEST
    groups, so the bounds stay contiguous, non-overlapping and total exactly
    ``n_bars`` bars. For example ``n_bars=10, n_groups=3`` gives
    ``[(0, 4), (4, 7), (7, 10)]``.
    """
    if n_bars < 0:
        raise ValueError(f"n_bars must be >= 0, got {n_bars}")
    if n_groups < 1:
        raise ValueError(f"n_groups must be >= 1, got {n_groups}")
    base, remainder = divmod(n_bars, n_groups)
    bounds: list[tuple[int, int]] = []
    start = 0
    for group in range(n_groups):
        end = start + base + (1 if group < remainder else 0)
        bounds.append((start, end))
        start = end
    return bounds


def _indices_from_ranges(ranges: list[tuple[int, int]]) -> npt.NDArray[np.int64]:
    """Materialise sorted bar indices from sorted, merged half-open ranges."""
    if not ranges:
        return np.empty(0, dtype=np.int64)
    return np.concatenate([np.arange(start, end, dtype=np.int64) for start, end in ranges])


def _mask_to_ranges(mask: npt.NDArray[np.bool_]) -> list[tuple[int, int]]:
    """Merge a boolean bar mask into sorted, contiguous half-open ranges."""
    ranges: list[tuple[int, int]] = []
    start = -1
    for i in range(mask.shape[0]):
        if mask[i]:
            if start < 0:
                start = i
        elif start >= 0:
            ranges.append((start, i))
            start = -1
    if start >= 0:
        ranges.append((start, int(mask.shape[0])))
    return ranges


class CombinatorialSplit(BaseModel):
    """One CPCV split: held-out test groups and the surviving training bars."""

    model_config = ConfigDict(frozen=True)

    index: int = Field(description="0-based index in the deterministic combination order.")
    test_groups: tuple[int, ...] = Field(description="Group numbers held out as test.")
    train_ranges: list[tuple[int, int]] = Field(
        description="Merged contiguous (start, end) training ranges, purge/embargo removed."
    )
    test_ranges: list[tuple[int, int]] = Field(
        description="Merged contiguous (start, end) test ranges, equal to the test group bounds."
    )

    def train_indices(self) -> npt.NDArray[np.int64]:
        """Sorted bar indices belonging to the training set."""
        return _indices_from_ranges(self.train_ranges)

    def test_indices(self) -> npt.NDArray[np.int64]:
        """Sorted bar indices belonging to the test set."""
        return _indices_from_ranges(self.test_ranges)


def combinatorial_purged_splits(
    n_bars: int, config: CombinatorialPurgedConfig
) -> list[CombinatorialSplit]:
    """One CPCV split per combination of ``config.n_test_groups`` groups (§2.4).

    Groups come from :func:`group_bounds`; combinations are enumerated with
    :func:`itertools.combinations`, so the order (and therefore the split
    indices) is deterministic. The test set is exactly the selected groups'
    bars. The training set is every bar not in a test group, MINUS
    ``purge_bars`` bars on each side of every test boundary and MINUS
    ``embargo_bars`` bars immediately after each test group's end; purge and
    embargo only ever drop bars *outside* a test group, so they can never shrink
    ``test_indices()``. Surviving bars are merged into contiguous ranges.
    """
    bounds = group_bounds(n_bars, config.n_groups)
    splits: list[CombinatorialSplit] = []
    for index, combo in enumerate(combinations(range(config.n_groups), config.n_test_groups)):
        test_groups = tuple(combo)
        test_ranges = [bounds[group] for group in test_groups]
        blocked = np.zeros(n_bars, dtype=bool)
        for group in test_groups:
            start, end = bounds[group]
            blocked[start:end] = True
            blocked[max(0, start - config.purge_bars) : start] = True
            blocked[end : min(n_bars, end + config.purge_bars)] = True
            blocked[end : min(n_bars, end + config.embargo_bars)] = True
        splits.append(
            CombinatorialSplit(
                index=index,
                test_groups=test_groups,
                train_ranges=_mask_to_ranges(~blocked),
                test_ranges=test_ranges,
            )
        )
    return splits


def n_backtest_paths(n_groups: int, n_test_groups: int) -> int:
    """Distinct backtest paths ``phi[N,k] = (k/N) * C(N,k)`` (§2.4).

    Raises ``ValueError`` when ``k`` is outside ``[1, N)`` or when the quotient
    is not a whole number. The quotient is in fact ``C(N-1, k-1)`` and therefore
    always integral for valid input; the guard is kept so a future weighting
    change cannot silently hand back a fractional path count.
    """
    if n_groups < 1:
        raise ValueError(f"n_groups must be >= 1, got {n_groups}")
    if not 1 <= n_test_groups < n_groups:
        raise ValueError(
            f"n_test_groups must satisfy 1 <= k < n_groups, got k={n_test_groups}, N={n_groups}"
        )
    value = Fraction(n_test_groups, n_groups) * comb(n_groups, n_test_groups)
    if value.denominator != 1:
        raise ValueError(
            f"phi[{n_groups},{n_test_groups}] = {value.numerator}/{value.denominator} "
            "is not a whole number"
        )
    return int(value)
