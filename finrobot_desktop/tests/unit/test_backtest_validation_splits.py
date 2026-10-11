"""Unit tests for the walk-forward / CPCV split geometry.

Deterministic and offline: indices only, no data and no randomness. CPCV
path counts are checked against brute-force combinations because
``phi[N,k] = (k/N) * C(N,k)`` is algebraically ``C(N-1, k-1)`` and therefore
never fractional for valid input --- there is no small fractional (N, k) case
to assert a raise on, so the guard is exercised through invalid k instead.
"""

from __future__ import annotations

from fractions import Fraction
from itertools import combinations
from math import comb

import numpy as np
import pytest
from pydantic import ValidationError

from finrobot.engine.backtest.validation.splits import (
    CombinatorialPurgedConfig,
    CombinatorialSplit,
    Split,
    WalkForwardConfig,
    combinatorial_purged_splits,
    group_bounds,
    n_backtest_paths,
    walk_forward_splits,
)

_YEAR = 252
_CPCV_62 = CombinatorialPurgedConfig(n_groups=6, n_test_groups=2)


class TestWalkForwardConfig:
    def test_from_periods_canonical_4y_2y_1y_30d(self) -> None:
        cfg = WalkForwardConfig.from_periods()
        assert (cfg.train_bars, cfg.validate_bars, cfg.step_bars, cfg.embargo_bars) == (
            1008,
            504,
            252,
            30,
        )

    def test_from_periods_rounds_year_counts(self) -> None:
        cfg = WalkForwardConfig.from_periods(bars_per_year=10, train_years=1.5, validate_years=0.5)
        assert (cfg.train_bars, cfg.validate_bars) == (15, 5)

    def test_non_positive_fields_raise(self) -> None:
        with pytest.raises(ValidationError):
            WalkForwardConfig(train_bars=0, validate_bars=1, step_bars=1)
        with pytest.raises(ValidationError):
            WalkForwardConfig(train_bars=1, validate_bars=1, step_bars=1, embargo_bars=-1)


class TestWalkForwardSplits:
    def test_canonical_9y_count_and_exact_windows(self) -> None:
        n_bars = 9 * _YEAR  # 2268
        splits = walk_forward_splits(n_bars, WalkForwardConfig.from_periods())
        # 4th split would need validate_end = 252*3 + 30 + 504 = 2298 > 2268.
        assert len(splits) == 3

        first = splits[0]
        assert (
            first.index,
            first.train_start,
            first.train_end,
            first.embargo_start,
            first.embargo_end,
            first.validate_start,
            first.validate_end,
        ) == (0, 0, 1008, 1008, 1038, 1038, 1542)

        last = splits[-1]
        assert (
            last.index,
            last.train_start,
            last.train_end,
            last.embargo_start,
            last.embargo_end,
            last.validate_start,
            last.validate_end,
        ) == (2, 504, 1512, 1512, 1542, 1542, 2046)

    def test_default_config_matches_from_periods(self) -> None:
        default = walk_forward_splits(2268)
        explicit = walk_forward_splits(2268, WalkForwardConfig.from_periods())
        assert [s.model_dump() for s in default] == [s.model_dump() for s in explicit]

    def test_invariants_hold_for_every_split(self) -> None:
        n_bars = 9 * _YEAR
        splits = walk_forward_splits(n_bars)
        assert splits  # non-vacuous
        for split in splits:
            assert split.train_end == split.embargo_start
            assert split.embargo_start < split.validate_start
            assert split.embargo_end == split.validate_start
            assert split.validate_end <= n_bars
            assert split.train_slice() == slice(split.train_start, split.train_end)
            assert split.validate_slice() == slice(split.validate_start, split.validate_end)
            train = set(range(split.train_start, split.train_end))
            validate = set(range(split.validate_start, split.validate_end))
            assert train.isdisjoint(validate)

    def test_step_is_respected_between_splits(self) -> None:
        splits = walk_forward_splits(9 * _YEAR)
        assert [s.train_start for s in splits] == [0, 252, 504]

    def test_short_history_is_trimmed_not_truncated(self) -> None:
        cfg = WalkForwardConfig.from_periods()
        # First full window ends at 1542; one step of 252 fits only two splits.
        assert len(walk_forward_splits(2016, cfg)) == 2
        assert len(walk_forward_splits(1542, cfg)) == 1
        assert walk_forward_splits(1541, cfg) == []

    def test_empty_history_returns_no_splits(self) -> None:
        assert walk_forward_splits(0) == []

    def test_negative_history_raises(self) -> None:
        with pytest.raises(ValueError, match="n_bars"):
            walk_forward_splits(-1)


class TestSplitValueObject:
    def test_is_frozen(self) -> None:
        split = walk_forward_splits(1600)[0]
        with pytest.raises(ValidationError):
            split.index = 99  # type: ignore[misc]

    def test_geometry_validator_rejects_inconsistent_windows(self) -> None:
        with pytest.raises(ValidationError):
            Split(
                index=0,
                train_start=0,
                train_end=10,
                embargo_start=11,  # must equal train_end
                embargo_end=20,
                validate_start=20,
                validate_end=30,
            )


class TestGroupBounds:
    def test_exact_partition(self) -> None:
        assert group_bounds(12, 4) == [(0, 3), (3, 6), (6, 9), (9, 12)]

    def test_remainder_goes_to_earliest_groups(self) -> None:
        assert group_bounds(10, 3) == [(0, 4), (4, 7), (7, 10)]

    def test_every_bar_covered_exactly_once_with_remainder(self) -> None:
        n_bars, n_groups = 100, 7
        covered = [i for start, end in group_bounds(n_bars, n_groups) for i in range(start, end)]
        assert covered == list(range(n_bars))

    def test_zero_bars_yields_empty_groups(self) -> None:
        assert group_bounds(0, 3) == [(0, 0), (0, 0), (0, 0)]

    def test_invalid_arguments_raise(self) -> None:
        with pytest.raises(ValueError, match="n_bars"):
            group_bounds(-1, 2)
        with pytest.raises(ValueError, match="n_groups"):
            group_bounds(10, 0)


class TestCombinatorialPurgedSplits:
    def test_n6_k2_gives_15_splits_and_5_paths(self) -> None:
        splits = combinatorial_purged_splits(600, _CPCV_62)
        assert len(splits) == 15
        assert n_backtest_paths(6, 2) == 5

    def test_each_pair_of_groups_is_tested_exactly_once(self) -> None:
        splits = combinatorial_purged_splits(600, _CPCV_62)
        seen = [s.test_groups for s in splits]
        assert len(set(seen)) == 15
        assert set(seen) == set(combinations(range(6), 2))

    def test_test_ranges_are_exactly_the_group_bounds(self) -> None:
        splits = combinatorial_purged_splits(600, _CPCV_62)
        bounds = group_bounds(600, 6)
        for split in splits:
            assert split.test_ranges == [bounds[g] for g in split.test_groups]
            assert split.test_indices().tolist() == [
                i for g in split.test_groups for i in range(*bounds[g])
            ]

    def test_no_purge_no_embargo_covers_all_bars_disjointly(self) -> None:
        n_bars = 97  # deliberately not divisible by 6
        splits = combinatorial_purged_splits(
            n_bars, CombinatorialPurgedConfig(n_groups=6, n_test_groups=2)
        )
        for split in splits:
            train = split.train_indices()
            test = split.test_indices()
            assert np.intersect1d(train, test).size == 0
            assert np.array_equal(np.union1d(train, test), np.arange(n_bars))

    def test_purge_and_embargo_exclude_exact_bars(self) -> None:
        n_bars = 600
        cfg = CombinatorialPurgedConfig(n_groups=6, n_test_groups=2, purge_bars=5, embargo_bars=7)
        splits = combinatorial_purged_splits(n_bars, cfg)
        split = next(s for s in splits if s.test_groups == (0, 4))

        train = set(split.train_indices().tolist())
        test = set(split.test_indices().tolist())
        assert test == set(range(0, 100)) | set(range(400, 500))
        assert train.isdisjoint(test)

        removed = set(range(n_bars)) - train - test
        # after group 0: purge [100,105) and embargo [100,107) -> [100,107)
        # before group 4: purge [395,400); after: purge [500,505) + embargo [500,507)
        assert removed == set(range(100, 107)) | set(range(395, 400)) | set(range(500, 507))
        # purge/embargo must never eat into a test group itself
        assert test == set(range(0, 100)) | set(range(400, 500))

    def test_train_ranges_are_sorted_and_merged(self) -> None:
        cfg = CombinatorialPurgedConfig(n_groups=6, n_test_groups=2, purge_bars=3, embargo_bars=4)
        for split in combinatorial_purged_splits(600, cfg):
            starts = [start for start, _ in split.train_ranges]
            assert starts == sorted(starts)
            for (_, end), (next_start, _) in zip(split.train_ranges, split.train_ranges[1:]):
                assert end < next_start

    def test_is_frozen(self) -> None:
        split = CombinatorialSplit(
            index=0,
            test_groups=(0, 3),
            train_ranges=[(100, 200)],
            test_ranges=[(0, 100), (300, 400)],
        )
        with pytest.raises(ValidationError):
            split.index = 99  # type: ignore[misc]

    def test_k_must_be_below_n_groups(self) -> None:
        with pytest.raises(ValidationError):
            CombinatorialPurgedConfig(n_groups=3, n_test_groups=3)


class TestNBacktestPaths:
    @pytest.mark.parametrize(
        ("n_groups", "k"),
        [(6, 2), (5, 2), (6, 3), (4, 2), (4, 1), (7, 3), (3, 2)],
    )
    def test_matches_brute_force_and_binomial_identity(self, n_groups: int, k: int) -> None:
        brute_force = Fraction(k, n_groups) * len(list(combinations(range(n_groups), k)))
        assert brute_force.denominator == 1
        expected = int(brute_force)
        assert n_backtest_paths(n_groups, k) == expected
        # algebraically phi[N,k] == C(N-1, k-1)
        assert n_backtest_paths(n_groups, k) == comb(n_groups - 1, k - 1)

    def test_invalid_arguments_raise(self) -> None:
        with pytest.raises(ValueError, match="n_test_groups"):
            n_backtest_paths(4, 0)
        with pytest.raises(ValueError, match="n_test_groups"):
            n_backtest_paths(4, 4)
        with pytest.raises(ValueError, match="n_groups"):
            n_backtest_paths(0, 1)
