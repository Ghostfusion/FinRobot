"""Historical EV/EBITDA + P/FCF band computation (v5 §6.6).

Pure leaf-layer: route adapter feeds in already-fetched financials + price
history, this module emits a deterministic band + timeline. No providers,
no LLM, no upper-layer imports.

Algorithm (single function, no per-metric duplication):
  1. The yearly financials list is sorted by ascending fiscal-year date.
  2. For each price point we attach the most recent fiscal year on or before
     that price's date — that's the "current at the time" denominator.
  3. We compute the multiple per sample, drop non-finite / non-positive
     samples, and reduce to (current, P25, median, P75, P90) plus a sampled
     timeline (≤120 points so the UI line stays readable).

Why deterministic + audit-pinned: spec §6.6 lets the front end say "现在贵 /
合理 / 便宜" verbatim by comparing `current` to `p75` / `p90`. That
classification has to be reproducible — same inputs, same answer, no LLM.
"""

from __future__ import annotations

import bisect
import math
import statistics
from dataclasses import dataclass
from datetime import date
from typing import Literal

HistoricalMetricName = Literal["ev_ebitda", "p_fcf"]
"""Two metrics supported in v5 (spec §6.6)."""

_MAX_TIMELINE_POINTS = 120
"""Front-end chart caps at ~3y * monthly = 36 points; 120 is a safe ceiling
that keeps the JSON payload small while preserving variation when callers
ask for higher-resolution windows."""

_STRUCTURAL_BREAK_STEP_MULTIPLE = 3.0
"""A year-over-year EBITDA step at or above this multiple is a structural break.

EBITDA is the EV/EBITDA denominator, so a 3x annual step means the window's
multiples changed regime mid-sample: the quantiles then average a small-base
regime with a large-base one. 3x is the same order-of-magnitude threshold the
project already uses to flag a base that is not comparable across a window
(a 2x step is ordinary growth / a cyclical swing)."""


@dataclass(frozen=True)
class EbitdaStructuralBreak:
    """A structural step in the window's EBITDA base (a regime change).

    The whole 5-year sample is reduced to P25/P75/P90, so ONE year-over-year EBITDA
    step ≥ ``_STRUCTURAL_BREAK_STEP_MULTIPLE`` makes the quantiles a blend of two
    regimes. NVDA 2026-10-13: FY2023 EBITDA $5.99B → FY2024 $35.58B (5.9x), so the
    window's p90 = 183.3x and p25 = 37.8x are driven by the pre-ramp small-EBITDA
    base, and ``classify_band`` badged the stock CHEAP (27.06x ≤ 37.76x) off it.

    The quantile METHOD is a product decision and is NOT changed here — this object
    only DISCLOSES the break so the UI can caveat the badge.
    """

    from_fiscal_date: date
    """Fiscal-year-end date of the pre-step year (annual basis)."""

    to_fiscal_date: date
    """Fiscal-year-end date of the post-step year."""

    from_ebitda: float
    """EBITDA of the pre-step fiscal year (absolute, reporting currency)."""

    to_ebitda: float
    """EBITDA of the post-step fiscal year."""

    step_multiple: float
    """The step magnitude (≥ 1): the larger of ``to_ebitda`` / ``from_ebitda`` and its
    reciprocal, so a ≥3x ramp and a ≥3x collapse are both reported as ≥ 3."""


@dataclass(frozen=True)
class YearlyFinancials:
    """Single fiscal-year snapshot needed for one band metric.

    The route layer parses raw yfinance / FMP rows into this shape so the
    compute function stays agnostic to provider keys.
    """

    fiscal_date: date
    """The fiscal-year-end date — used to align with price history."""

    ebitda: float | None
    """Annual EBITDA in absolute dollars. None means EBITDA not reported."""

    free_cash_flow: float | None
    """Annual FCF (OperatingCF - CapEx). None means data unavailable."""

    net_debt: float | None
    """Total debt minus cash & equivalents; can be negative (net cash).
    None means a balance leg was missing for the year (None ≠ 0 — filling 0
    fabricated a debt-free EV for levered issuers); the EV/EBITDA sample for
    that year is skipped."""


@dataclass(frozen=True)
class PricePoint:
    """A single (date, close-price) row from the historical price stream."""

    sample_date: date
    close: float


@dataclass(frozen=True)
class HistoricalBand:
    """v5 §6.6 response payload for one ticker/metric."""

    metric: HistoricalMetricName
    current: float | None
    median: float | None
    p25: float | None
    p75: float | None
    p90: float | None
    timeline: list[tuple[date, float]]
    sample_count: int
    warnings: list[str]
    structural_break: EbitdaStructuralBreak | None = None
    """The largest year-over-year EBITDA step ≥ ``_STRUCTURAL_BREAK_STEP_MULTIPLE``
    between two fiscal years the window's samples actually use, or None.

    A disclosure, not a method change: the published quantiles/current/timeline are
    byte-identical to before this field existed. Consumers (the technical payload,
    the UI) must caveat a cheap/fair/expensive badge derived from a window whose
    quantiles blend two earnings regimes."""


def compute_historical_band(
    *,
    metric: HistoricalMetricName,
    yearly: list[YearlyFinancials],
    prices: list[PricePoint],
    shares_outstanding: float,
    current_override: float | None = None,
) -> HistoricalBand:
    """Build the band + timeline + quantiles for a single metric.

    Inputs are typed dataclasses so callers can't accidentally pass raw
    provider dicts; alignment between fiscal years and price dates is
    handled here (most recent fiscal year ≤ price date), and degenerate
    rows are dropped rather than raising — the UI shows what's available.

    ``current_override``: when given, replaces the band's *current* multiple
    with a caller-supplied value (B2). The historical samples here use the
    trailing **annual** EBITDA at each price date (the only series available
    without quarterly data), but the report's comps chapter reports the
    **current** EV/EBITDA on **TTM** EBITDA. Passing the canonical TTM
    multiple as ``current_override`` keeps the headline "current EV/EBITDA"
    identical across chapters instead of showing two口径. The historical
    quantiles/timeline stay annual-based, so we record a warning disclosing
    the mixed basis rather than silently masking it.
    """
    warnings: list[str] = []

    if shares_outstanding <= 0:
        return _empty(
            metric, ["shares_outstanding unavailable — historical bands cannot be computed"]
        )
    if not prices:
        return _empty(metric, ["price history is empty — historical bands cannot be computed"])
    if not yearly:
        return _empty(metric, ["financials history is empty — historical bands cannot be computed"])

    fiscal_dates, fiscals = _sort_yearly(yearly)

    samples: list[tuple[date, float]] = []
    skipped_no_financial = 0
    # Fiscal years the window's samples actually use. The structural-break check
    # below runs over THESE only: a break in a fiscal year no price point ever
    # aligned to cannot have shaped the published quantiles, and flagging it would
    # be a caveat about a regime the band does not contain.
    sampled_fiscal_dates: set[date] = set()
    for point in prices:
        fy = _financial_for_date(point.sample_date, fiscal_dates, fiscals)
        if fy is None:
            skipped_no_financial += 1
            continue
        multiple = _compute_multiple(metric, point, fy, shares_outstanding)
        # math.isfinite: a single NaN close (halted session / bad provider row)
        # passes both `is None` and `<= 0` (NaN comparisons are False) and
        # poisons every quantile of the band — same family as the peer-median
        # NaN fix in operators/multiples.
        if multiple is None or not math.isfinite(multiple) or multiple <= 0:
            continue
        samples.append((point.sample_date, multiple))
        sampled_fiscal_dates.add(fy.fiscal_date)

    if not samples:
        # Name WHICH input is missing instead of guessing "EBITDA / FCF": the live
        # NFLX case (2026-10-12) had both while net debt was absent on every year,
        # and the old wording sent the reader looking for a disclosure that was
        # right there in the band's own payload.
        missing: list[str] = []
        if metric == "ev_ebitda":
            if any(fy.ebitda is None or fy.ebitda <= 0 for fy in fiscals):
                missing.append("EBITDA")
            if all(fy.net_debt is None for fy in fiscals):
                missing.append("net debt")
            elif any(fy.net_debt is None for fy in fiscals):
                missing.append("net debt for some years")
        elif any(fy.free_cash_flow is None or fy.free_cash_flow <= 0 for fy in fiscals):
            missing.append("free cash flow")
        detail = (
            f"the serving provider reports no usable {', '.join(missing)} for the "
            "aligned fiscal years"
            if missing
            else "no price/financial pair produced a positive multiple"
        )
        return _empty(metric, [f"no sample could compute a multiple — {detail}"])

    if skipped_no_financial:
        warnings.append(
            f"{skipped_no_financial} price point(s) predate the earliest fiscal year — skipped"
        )

    # Structural-break disclosure (NOT a method change): the quantiles below reduce
    # the whole window to a few order statistics, so a ≥3x year-over-year EBITDA step
    # makes them a blend of two regimes. NVDA 2026-10-13 windowed 2023-01-31 onward,
    # where FY2023 EBITDA $5.99B → FY2024 $35.58B (5.9x) put p25 at 37.76x / p90 at
    # 183.34x and badged the stock CHEAP against a distorted p25. The published
    # numbers stay exactly as computed; the break and which years it spans are named
    # so the consumer can caveat the badge.
    structural_break = (
        _detect_structural_break([fy for fy in fiscals if fy.fiscal_date in sampled_fiscal_dates])
        if metric == "ev_ebitda"
        else None
    )
    if structural_break is not None:
        warnings.append(_structural_break_warning(structural_break))

    values = [v for _, v in samples]
    timeline = _downsample(samples, _MAX_TIMELINE_POINTS)
    if current_override is not None and current_override > 0:
        # B2: use the caller's canonical TTM multiple as the headline current
        # point (matches the comps chapter). Historical *quantiles* stay on the
        # trailing-annual basis (``values`` untouched) — disclose the mixed基差
        # rather than hide it. The timeline's last point is shifted to the same
        # TTM value so the rendered "current" dot sits on the line end instead of
        # floating off it; the historical shape is otherwise preserved.
        current = current_override
        if timeline:
            timeline = [*timeline[:-1], (timeline[-1][0], current_override)]
        warnings.append(
            "current point uses TTM EBITDA (consistent with the comps caliber); historical quantiles use each annual-report year's EBITDA, "
            "so the two carry a caliber basis difference (no quarterly data, so a rolling TTM cannot be reconstructed point by point)."
        )
    else:
        current = samples[-1][1]  # last sample is the most recent price multiple
        # W1-C2: no canonical TTM multiple was supplied, so the current point is
        # the most recent price × the trailing-ANNUAL EBITDA — a different口径
        # than the report's comps/technical chapters (which use TTM). Disclose it
        # so a consumer (the standalone /historical-bands route) can't silently
        # classify a ticker 贵/合理/便宜 on an annual basis while the report calls
        # the same ticker the opposite on TTM (the signal flip).
        warnings.append(
            "current point is based on the [annual-report year] EBITDA matching the most recent price (no canonical TTM multiple passed in) — "
            "this carries a basis difference vs the TTM caliber of the report's comps / technical chapters; the expensive/fair/cheap classification is on an annual-report basis, "
            "so do not compare it directly with the TTM caliber."
        )

    return HistoricalBand(
        metric=metric,
        current=current,
        median=statistics.median(values),
        p25=_quantile(values, 0.25),
        p75=_quantile(values, 0.75),
        p90=_quantile(values, 0.90),
        timeline=timeline,
        sample_count=len(values),
        warnings=warnings,
        structural_break=structural_break,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _empty(metric: HistoricalMetricName, warnings: list[str]) -> HistoricalBand:
    return HistoricalBand(
        metric=metric,
        current=None,
        median=None,
        p25=None,
        p75=None,
        p90=None,
        timeline=[],
        sample_count=0,
        warnings=warnings,
    )


def _sort_yearly(
    yearly: list[YearlyFinancials],
) -> tuple[list[date], list[YearlyFinancials]]:
    items = sorted(yearly, key=lambda y: y.fiscal_date)
    return [y.fiscal_date for y in items], items


def _financial_for_date(
    sample_date: date,
    fiscal_dates: list[date],
    fiscals: list[YearlyFinancials],
) -> YearlyFinancials | None:
    """Return the most recent fiscal year on or before sample_date, or None."""
    idx = bisect.bisect_right(fiscal_dates, sample_date) - 1
    if idx < 0:
        return None
    return fiscals[idx]


def _compute_multiple(
    metric: HistoricalMetricName,
    price: PricePoint,
    fy: YearlyFinancials,
    shares: float,
) -> float | None:
    market_cap = price.close * shares
    if market_cap <= 0:
        return None
    if metric == "ev_ebitda":
        if fy.ebitda is None or fy.ebitda <= 0 or fy.net_debt is None:
            return None
        return (market_cap + fy.net_debt) / fy.ebitda
    # metric == "p_fcf" — the Literal alias has no other variants.
    if fy.free_cash_flow is None or fy.free_cash_flow <= 0:
        return None
    return market_cap / fy.free_cash_flow


def _detect_structural_break(fiscals: list[YearlyFinancials]) -> EbitdaStructuralBreak | None:
    """Largest ≥``_STRUCTURAL_BREAK_STEP_MULTIPLE`` EBITDA step between adjacent years.

    ``fiscals`` must be the sampled fiscal years in ascending order. Only positive
    EBITDA pairs are comparable (a loss-making year has no meaningful ratio and its
    multiple is dropped upstream anyway); non-finite legs are ignored. The step is
    measured as a magnitude ≥ 1 in EITHER direction — a 3x collapse blends regimes
    exactly as a 3x ramp does — and the LARGEST step is returned so the disclosure
    names the dominant regime change, or None.
    """
    largest: EbitdaStructuralBreak | None = None
    for prev, curr in zip(fiscals, fiscals[1:]):
        if prev.ebitda is None or curr.ebitda is None:
            continue
        if not (math.isfinite(prev.ebitda) and math.isfinite(curr.ebitda)):
            continue
        if prev.ebitda <= 0 or curr.ebitda <= 0:
            continue
        ratio = curr.ebitda / prev.ebitda
        step = ratio if ratio >= 1.0 else 1.0 / ratio
        if step < _STRUCTURAL_BREAK_STEP_MULTIPLE:
            continue
        if largest is None or step > largest.step_multiple:
            largest = EbitdaStructuralBreak(
                from_fiscal_date=prev.fiscal_date,
                to_fiscal_date=curr.fiscal_date,
                from_ebitda=prev.ebitda,
                to_ebitda=curr.ebitda,
                step_multiple=step,
            )
    return largest


def _structural_break_warning(break_: EbitdaStructuralBreak) -> str:
    """Reader-facing warning for a window whose quantiles blend two regimes.

    Names the years, the step and the direction of the distortion, and states that
    the quantile method itself is unchanged — the disclaimer is about HOW the
    published P25/P75/P90 should be read, not a silent re-computation.
    """
    direction = "small-EBITDA" if break_.to_ebitda > break_.from_ebitda else "large-EBITDA"
    return (
        "the historical band spans a structural EBITDA break: "
        f"FY{break_.from_fiscal_date.isoformat()}→FY{break_.to_fiscal_date.isoformat()} "
        f"EBITDA stepped {break_.step_multiple:.1f}x "
        f"(${break_.from_ebitda / 1e9:.2f}B→${break_.to_ebitda / 1e9:.2f}B, annual basis), "
        f"so the P25/P75/P90 quantiles blend the pre-step ({direction}) base with the "
        "post-step base and the cheap/fair/expensive classification is on a mixed "
        "regime — treat the badge as directional only. The quantile method is unchanged."
    )


def _quantile(values: list[float], q: float) -> float:
    """Inclusive linear-interpolation quantile (matches numpy default)."""
    if not values:
        raise ValueError("quantile on empty values")
    if len(values) == 1:
        return values[0]
    s = sorted(values)
    pos = q * (len(s) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(s) - 1)
    frac = pos - lo
    return s[lo] + frac * (s[hi] - s[lo])


def _downsample(
    samples: list[tuple[date, float]],
    max_points: int,
) -> list[tuple[date, float]]:
    """Uniform downsample to at most max_points keeping the first + last samples."""
    if len(samples) <= max_points:
        return samples
    # Leave 2 slots for the explicit first / last indices to stay under the cap.
    interior = max(0, max_points - 2)
    step = (len(samples) - 1) / (interior + 1)
    indices = {0, len(samples) - 1}
    for i in range(1, interior + 1):
        indices.add(int(i * step))
    ordered = sorted(indices)[:max_points]
    return [samples[i] for i in ordered]


# Re-export the runtime sentinel for type checkers — kept for parity with the
# rest of compute/* which expose Literal aliases at module scope.
__all__ = [
    "EbitdaStructuralBreak",
    "HistoricalBand",
    "HistoricalMetricName",
    "PricePoint",
    "YearlyFinancials",
    "compute_historical_band",
]
