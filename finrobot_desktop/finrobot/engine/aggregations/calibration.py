"""Confidence calibration — does FinRobot's own stated conviction predict its hits?

Why this module exists
----------------------
The engine already *measures* accuracy: `compute_signal` grades every artifact
hit / watching / failed, and the sibling `hit_rate_overview` rolls that up per
verdict. Neither asks the calibration question, which is the one a reader of a
research tool actually cares about: **when FinRobot says "high confidence", is it
right more often than when it says "low confidence"?** Without that, the
"confidence" dial (`ValuationSynthesis.confidence`, the graded call that drives
band width and the asymmetric verdict thresholds) is an unfalsifiable claim —
the engine grades its own homework and never checks the grade against outcomes.

A raw hit rate cannot answer the question, and actively misleads: a 60% hit rate
reads as a triumph until you learn the engine's own base rate is 65% — i.e. the
"confident" bucket is *worse* than average. Every bucket therefore ships
`lift_vs_overall` (the bucket's rate minus the overall rate across all closed
rows), so a bucket is only ever read relative to the engine's own average, never
against an implicit "50% is neutral" or "higher is better" prior.

Two honesty rules, both load-bearing
------------------------------------
1. **Event-count floor.** A bucket below `MIN_CLOSED_EVENTS` closed rows reports
   `hit_rate=None` + `status="insufficient"` — never `0.0`, and never a neutral
   `0.5`. A 1-of-2 bucket is noise; a fabricated mid-point would be read as a
   measurement. `None` is the only honest value, and the route/UI render it as
   "not enough data" (the same convention as `HitRateStats.hit_rate`). A rate is
   also never computed from a bucket with `n_closed == 0`.
2. **Nothing is silently dropped.** A row whose `signal is None` (unpriced,
   legacy, or a type with no thesis) still counts toward `n_total` — it is a
   produced artifact that merely cannot be judged yet. A row whose confidence is
   missing or outside the tier vocabulary lands in an explicit `"unknown"`
   bucket. Discarding either would let the table describe a smaller,
   self-selected population than the engine actually produced.

The statistics themselves are delegated to `compute_hit_rate` (v5 §7.3): the
closed-sample denominator and the survivor-bias correction live in exactly one
place. This module only partitions rows, applies the floor, and derives the
lift — it never recomputes a rate a different way.

Leaf-layer rules (same as the sibling aggregation): pure, no I/O, no imports
from `routes/` or `artifact/`; callers assemble the rows, own the clock, and
decide the time window (a row carries no timestamp, so windowing cannot live
here without duplicating the route's clock).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from finrobot.engine.compute.operators.signal import (
    ClosedReturn,
    HitRateStats,
    Signal,
    compute_hit_rate,
)

ConfidenceTier = Literal["high", "medium", "low", "very_low"]
"""The valuation-synthesis confidence dial — the primary bucket key."""

CalibrationStatus = Literal["measured", "insufficient"]
"""Closed vocabulary for a bucket's measurement state (see `MIN_CLOSED_EVENTS`)."""

UNKNOWN_CONFIDENCE = "unknown"
"""Bucket for rows whose confidence is missing or outside the tier vocabulary."""

_CONFIDENCE_TIERS: tuple[ConfidenceTier, ...] = ("high", "medium", "low", "very_low")
"""The tier vocabulary, in descending conviction — and the `by_confidence` key order."""

_TIER_LOOKUP: frozenset[str] = frozenset(_CONFIDENCE_TIERS)

CALIBRATION_BUCKETS: tuple[str, ...] = (*_CONFIDENCE_TIERS, UNKNOWN_CONFIDENCE)
"""Every key `by_confidence` always carries, empty buckets included.

The route/UI must never have to handle a missing key: "high has no closed rows
yet" and "high is not in this table" are different facts, and only the first is
true here (same always-present convention as the verdict buckets).
"""

MIN_CLOSED_EVENTS = 5
"""Closed-event floor below which a bucket's rate is reported as `None`.

At 5 closed rows a 95% binomial interval on a 0.6 rate still spans roughly
0.15–0.95, so the lift a smaller bucket would imply is indistinguishable from
noise — and a desktop track record accrues closed events slowly, so a lower
floor would publish noise as calibration. Below the floor the rate is `None`
(never 0.0, never 0.5); at or above it the bucket is `"measured"`.
"""

_CLOSED_SIGNALS: frozenset[Signal] = frozenset(("hit", "failed"))
"""`watching` is deliberately absent: too young to judge (v5 §7.3)."""


@dataclass(frozen=True)
class CalibrationRow:
    """One artifact's calibration facts, assembled by the caller.

    Everything here is a fact the route layer already holds (summary columns) or
    reads from the artifact payload; the aggregation itself never fetches,
    prices or classifies.
    """

    confidence: str | None
    """Valuation-synthesis tier ("high" | "medium" | "low" | "very_low"), or None
    when the artifact predates the dial / carries no synthesis block. Anything
    outside the vocabulary (including a blank string) is bucketed as
    `"unknown"` rather than dropped."""

    verdict: str | None
    """The rating (BUY / HOLD / SELL). Carried for provenance — the bucket key is
    the confidence tier, so the verdict does not enter the statistics."""

    signal: Signal | None
    """Post-trade outcome. None means "not judgeable" (unpriced / no thesis): the
    row still counts toward `n_total`, never toward `n_closed`."""

    closed_return: ClosedReturn | None = None
    """Realised return vs the market, for rows whose signal is closed. None when
    the caller could not price the row (or has no benchmark leg) — the row still
    counts as closed, it just does not contribute to `avg_excess_return`."""


@dataclass(frozen=True)
class CalibrationBucketStats:
    """Counts + rate + lift for one confidence bucket (or the overall row)."""

    n_total: int
    """Every row in the bucket, including rows with `signal is None`."""

    n_closed: int
    """Rows with signal ∈ {hit, failed} — `watching` does NOT count."""

    n_hit: int
    """Rows with signal == "hit"."""

    hit_rate: float | None
    """n_hit / n_closed, or None below the floor (never 0.0, never 0.5)."""

    avg_excess_return: float | None
    """mean(ticker_return - sp500_return) over the bucket's closed returns; None
    when none were supplied (unpriceable rows / no benchmark leg)."""

    lift_vs_overall: float | None
    """`hit_rate` minus the OVERALL hit rate — the base-rate correction. None
    unless both this bucket and the overall row are measured; a lift against an
    unmeasured base rate would be meaningless."""

    status: CalibrationStatus
    """"measured" when n_closed >= the floor, else "insufficient"."""


@dataclass(frozen=True)
class CalibrationOverview:
    """Roll-up returned to the route layer; the route wraps it into Pydantic."""

    overall: CalibrationBucketStats
    """All rows, regardless of confidence — the base rate the lifts are against."""

    by_confidence: dict[str, CalibrationBucketStats]
    """One entry per `CALIBRATION_BUCKETS` key, always present."""

    min_closed: int
    """The floor applied to every bucket (echoed so the UI can explain
    "insufficient" without hard-coding the number)."""

    status: CalibrationStatus
    """The whole table's state — mirrors `overall.status` (the overall floor is
    the table's floor: with no measured base rate, no lift is readable)."""


def compute_calibration(
    rows: Sequence[CalibrationRow],
    *,
    min_closed: int = MIN_CLOSED_EVENTS,
) -> CalibrationOverview:
    """Bucket rows by confidence tier and report rate + lift per bucket.

    Pure and deterministic: same rows in, same overview out (no clock, no I/O,
    no windowing — the caller filters by window before assembling rows).

    Args:
        rows: One `CalibrationRow` per artifact the caller wants counted.
        min_closed: Closed-event floor. A bucket (or the overall row) with fewer
            closed rows reports `hit_rate=None` + `status="insufficient"`.

    Raises:
        ValueError: If `min_closed < 1` — a zero floor would publish a rate for a
            bucket with `n_closed == 0`, the exact fabrication this module exists
            to prevent.

    Returns:
        `CalibrationOverview` — `by_confidence` always carries every tier plus
        `"unknown"`, so a missing key never has to be special-cased downstream.
    """
    if min_closed < 1:
        raise ValueError(f"min_closed must be >= 1, got {min_closed}")

    grouped: dict[str, list[CalibrationRow]] = {bucket: [] for bucket in CALIBRATION_BUCKETS}
    for row in rows:
        grouped[_bucket_for(row.confidence)].append(row)

    # The overall rate is the base rate every lift is measured against; resolve
    # it first so a bucket's lift is never computed against a half-known base.
    overall_stats = _hit_rate_stats(rows)
    overall_rate = _measured_rate(overall_stats, min_closed=min_closed)

    overall = _bucket_stats(
        overall_stats, n_total=len(rows), overall_rate=overall_rate, min_closed=min_closed
    )
    return CalibrationOverview(
        overall=overall,
        by_confidence={
            bucket: _bucket_stats(
                _hit_rate_stats(group),
                n_total=len(group),
                overall_rate=overall_rate,
                min_closed=min_closed,
            )
            for bucket, group in grouped.items()
        },
        min_closed=min_closed,
        status=overall.status,
    )


def _bucket_for(confidence: str | None) -> str:
    """Map a raw confidence value onto a bucket key.

    Missing / blank / out-of-vocabulary values all land in `"unknown"` — an
    unrecognised tier is not evidence of the tier it resembles, and dropping the
    row would shrink `n_total` below the population the engine produced.
    """
    if confidence is None:
        return UNKNOWN_CONFIDENCE
    key = confidence.strip().lower()
    return key if key in _TIER_LOOKUP else UNKNOWN_CONFIDENCE


def _hit_rate_stats(rows: Sequence[CalibrationRow]) -> HitRateStats:
    """Delegate the statistics to the single hit-rate implementation (v5 §7.3).

    Closed returns are matched to closed signals here: `compute_hit_rate`
    averages whatever returns it is handed, so a `watching` row's (or an
    unjudgeable row's) return must never reach it.
    """
    return compute_hit_rate(
        signals=[row.signal for row in rows],
        closed_returns=[
            row.closed_return
            for row in rows
            if row.signal in _CLOSED_SIGNALS and row.closed_return is not None
        ],
    )


def _measured_rate(stats: HitRateStats, *, min_closed: int) -> float | None:
    """The rate only when the closed sample clears the floor, else None."""
    return stats.hit_rate if stats.n_closed >= min_closed else None


def _bucket_stats(
    stats: HitRateStats,
    *,
    n_total: int,
    overall_rate: float | None,
    min_closed: int,
) -> CalibrationBucketStats:
    """Wrap one bucket's `HitRateStats` with the floor + the base-rate lift.

    `n_total` is passed in rather than read from `stats`: `compute_hit_rate`
    counts only judgeable rows, while this table counts every row it was handed
    (an unjudgeable artifact is still a produced artifact).
    """
    hit_rate = _measured_rate(stats, min_closed=min_closed)
    lift: float | None = None
    if hit_rate is not None and overall_rate is not None:
        lift = hit_rate - overall_rate
    return CalibrationBucketStats(
        n_total=n_total,
        n_closed=stats.n_closed,
        n_hit=stats.n_hit,
        hit_rate=hit_rate,
        avg_excess_return=stats.avg_excess_return,
        lift_vs_overall=lift,
        status="measured" if hit_rate is not None else "insufficient",
    )
