"""Pure fund-metric operators (leaf).

A fund has no income statement, so the equity valuation operators
(``calculate_ddm`` / ``calculate_dcf`` / ``calculate_multiples``) are undefined
for it. What a fund IS worth and what it COSTS are instead NAV-, expense- and
portfolio-composition measures — computed here, deterministically, from already
normalized inputs.

Leaf-layer rules (ADR-0005 §2.1): no data-fetch I/O, no imports from
``agents`` / ``pipelines`` / ``orchestrator``, no LLM libraries, no
``finrobot.artifact.*``. Identical inputs → identical outputs.

Unit convention: every ratio / return / yield is a FRACTION (0.0015 = 15 bp of
expense; 0.0382 = 3.82% yield), matching ``NormalizedFundProfile``. The single
exception is a ``*_pct`` field, whose name says percent.

报错 > 编数字: a metric whose inputs are missing returns ``None`` (or the key
stays ``None`` inside the returned mapping) — NEVER a fabricated ``0``. A
volatility of ``0`` means "the series never moved"; "we could not measure it"
must not look the same.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from datetime import date

from finrobot.engine.compute.operators.data_processor import calculate_cagr

#: Trading days per year for annualizing a daily NAV/price series.
TRADING_DAYS_PER_YEAR = 252
#: Calendar days per year for converting a date span into years.
DAYS_PER_YEAR = 365.25
#: Number of largest positions summed for the concentration snapshot.
_TOP_N = 10
#: 100 basis points as a decimal — the rate shock in duration sensitivity.
_100BP = 0.01


def years_ago(day: date, years: int) -> date:
    """The same calendar day ``years`` earlier (Feb-29 → Feb-28).

    The leap-year rule is shared by the NAV/price window anchor here and the
    coordinator's ``PRICE_RANGE`` fetch window, so both speak the same calendar
    (same rule as ``historical_loaders._same_day_years_ago``).
    """
    try:
        return day.replace(year=day.year - years)
    except ValueError:
        return day.replace(year=day.year - years, month=2, day=28)


def _usable_points(
    closes: Sequence[float], dates: Sequence[date] | None
) -> list[tuple[date | None, float]]:
    """``(date, close)`` pairs with a finite close, oldest → newest.

    ``dates`` (one per close) is carried only when it is the same length as
    ``closes`` AND non-decreasing — a misaligned or out-of-order date axis would
    silently mis-anchor every window, so it is treated as absent instead.
    """
    aligned: Sequence[date] | None = None
    if dates is not None and len(dates) == len(closes):
        if all(earlier <= later for earlier, later in zip(dates, dates[1:], strict=False)):
            aligned = dates
    points: list[tuple[date | None, float]] = []
    for index, close in enumerate(closes):
        if not math.isfinite(close):
            continue
        points.append((aligned[index] if aligned is not None else None, close))
    return points


def _annualized_return(start: float, end: float, years: float) -> float | None:
    """``end / start`` annualized over ``years`` (fractional allowed), or ``None``.

    The shared :func:`calculate_cagr` owns the guard set (non-finite or
    non-positive endpoints, non-positive years) and yields the total return via
    its one-year case; the fractional root then re-annualizes that over the
    window's ACTUAL elapsed years. ``calculate_cagr`` itself takes ``years: int``,
    which cannot express the fraction of a year a calendar-anchored window ends
    short of the last bar — annualizing over a nominal 5.0 when only 4.98 elapsed
    would overstate the rate.
    """
    total_return = calculate_cagr(start, end, 1)
    if total_return is None:
        return None
    if not math.isfinite(years) or years <= 0:
        return None
    return float((1.0 + total_return) ** (1.0 / years) - 1.0)


def _calendar_window_cagrs(points: Sequence[tuple[date, float]]) -> dict[str, float | None]:
    """1y / 3y / 5y CAGRs anchored to the CALENDAR, oldest → newest.

    A window is available when the series reaches back N calendar years; its
    start is the first bar at-or-after ``last_date − N years`` and the return is
    annualized over the ACTUAL elapsed years to the last bar. This is deliberately
    NOT a session count: five calendar years hold ~1253–1258 US trading sessions,
    not ``5 × 252 = 1260``, so an ``N × 252 + 1`` bar-count rule makes ``cagr_5y``
    unreachable from a real 5-year fetch (measured: 1253 bars).
    """
    out: dict[str, float | None] = {"cagr_1y": None, "cagr_3y": None, "cagr_5y": None}
    last_day, last_close = points[-1]
    for label, years in (("cagr_1y", 1), ("cagr_3y", 3), ("cagr_5y", 5)):
        anchor = years_ago(last_day, years)
        if points[0][0] > anchor:
            # The series does not reach back this far — the window is genuinely
            # unmeasurable, not merely thin.
            continue
        start_index = next((i for i, (day, _) in enumerate(points) if day >= anchor), None)
        if start_index is None or start_index >= len(points) - 1:
            continue
        start_day, start_close = points[start_index]
        elapsed_years = (last_day - start_day).days / DAYS_PER_YEAR
        out[label] = _annualized_return(start_close, last_close, elapsed_years)
    return out


def nav_series_statistics(
    closes: Sequence[float],
    risk_free_rate: float = 0.0,
    dates: Sequence[date] | None = None,
) -> dict[str, float | None]:
    """Risk/return statistics from a NAV (or price) series, oldest → newest.

    Returns the 1y / 3y / 5y CAGRs, the annualized volatility of daily returns,
    the maximum peak-to-trough drawdown (a positive fraction of the peak) and the
    annualized Sharpe ratio ``(annualized return − risk_free) / volatility``.

    ``dates`` (one per close) drives the CAGRs: the windows are anchored to the
    CALENDAR (see :func:`_calendar_window_cagrs`), so a series that spans a window
    yields that window's CAGR regardless of how many sessions the window holds.
    Without ``dates`` the CAGRs stay ``None`` — a bar count cannot decide whether a
    series actually spans a calendar year — while volatility, max drawdown and
    Sharpe, which need no calendar, are still computed.

    Non-finite points are dropped (a ``NaN`` NAV would poison every mean); a
    series with fewer than two usable points returns the all-``None`` shape.
    """
    stats: dict[str, float | None] = {
        "cagr_1y": None,
        "cagr_3y": None,
        "cagr_5y": None,
        "volatility": None,
        "max_drawdown": None,
        "sharpe": None,
    }
    points = _usable_points(closes, dates)
    if len(points) < 2:
        return stats
    values = [close for _, close in points]

    # Daily simple returns over consecutive usable closes. A zero / negative
    # previous close cannot anchor a return, so that step is skipped rather than
    # divided by zero.
    daily = [values[i] / values[i - 1] - 1.0 for i in range(1, len(values)) if values[i - 1] > 0]
    if len(daily) >= 2:
        n = len(daily)
        mean = math.fsum(daily) / n
        variance = math.fsum((r - mean) ** 2 for r in daily) / (n - 1)
        volatility = math.sqrt(variance) * math.sqrt(TRADING_DAYS_PER_YEAR)
        stats["volatility"] = volatility
        if volatility > 0:
            annualized_return = mean * TRADING_DAYS_PER_YEAR
            stats["sharpe"] = (annualized_return - risk_free_rate) / volatility

    peak = values[0]
    max_drawdown = 0.0
    for close in values:
        if close > peak:
            peak = close
        if peak > 0:
            drawdown = (peak - close) / peak
            if drawdown > max_drawdown:
                max_drawdown = drawdown
    stats["max_drawdown"] = max_drawdown

    dated = [(day, close) for day, close in points if day is not None]
    if len(dated) == len(points):
        stats.update(_calendar_window_cagrs(dated))

    return stats


def expense_cost_analysis(
    net_expense_ratio: float | None,
    gross_expense_ratio: float | None,
    nav_cagr: float | None,
    horizon_years: int,
    category_avg_expense_ratio: float | None,
) -> dict[str, float | None]:
    """What the expense ratio costs an investor over ``horizon_years``.

    ``expense_drag_usd_per_10k`` is the compounded dollar cost of the fee on a
    $10,000 holding grown at ``nav_cagr`` gross vs ``nav_cagr − net_expense_ratio``
    net — the visible cost of the fee, not just its level.
    ``fee_share_of_gross_return`` is the fee as a fraction of the gross annual
    return (how much of what the portfolio earns the manager keeps).
    ``fee_vs_category_avg`` is ``net − category average`` (negative = cheaper than
    peers).

    Every derived figure stays ``None`` when its inputs are missing (no fee, no
    growth rate, no peer benchmark) — never a fabricated ``0``.
    """
    out: dict[str, float | None] = {
        "expense_drag_usd_per_10k": None,
        "fee_share_of_gross_return": None,
        "fee_vs_category_avg": None,
        "horizon_years": float(horizon_years),
        "net_expense_ratio": net_expense_ratio,
        "gross_expense_ratio": gross_expense_ratio,
        "category_avg_expense_ratio": category_avg_expense_ratio,
        "nav_cagr": nav_cagr,
    }
    if (
        net_expense_ratio is None
        or nav_cagr is None
        or horizon_years <= 0
        or not math.isfinite(net_expense_ratio)
        or not math.isfinite(nav_cagr)
    ):
        return out

    # Compounding needs a positive growth base; a net return at or below -100%
    # (or a gross base at or below 0) has no honest future value to subtract.
    gross_base = 1.0 + nav_cagr
    net_base = 1.0 + nav_cagr - net_expense_ratio
    if gross_base > 0 and net_base > 0:
        gross_value = 10_000.0 * gross_base**horizon_years
        net_value = 10_000.0 * net_base**horizon_years
        out["expense_drag_usd_per_10k"] = gross_value - net_value

    if nav_cagr > 0:
        out["fee_share_of_gross_return"] = net_expense_ratio / nav_cagr

    if category_avg_expense_ratio is not None and math.isfinite(category_avg_expense_ratio):
        out["fee_vs_category_avg"] = net_expense_ratio - category_avg_expense_ratio

    return out


def portfolio_concentration(weights: Mapping[str, float]) -> dict[str, float | None]:
    """Concentration snapshot for a ``{label: weight}`` portfolio mapping.

    ``top10_weight`` sums the ten largest positions, ``hhi`` is the Herfindahl
    index (Σ w²), ``effective_n`` is its reciprocal (the equivalent number of
    equal-weight positions) and ``unlisted_remainder`` is ``1 − Σ w`` clamped at
    zero — how much of the portfolio the reported positions leave unaccounted
    (a partial top-holdings list, not a data error).

    An empty / all-non-positive mapping returns the all-``None`` shape: "no
    reported positions" is not "a perfectly diversified fund".
    """
    out: dict[str, float | None] = {
        "top10_weight": None,
        "hhi": None,
        "effective_n": None,
        "unlisted_remainder": None,
        "holdings_count": None,
    }
    values = [
        float(w) for w in weights.values() if w is not None and math.isfinite(w) and float(w) > 0
    ]
    if not values:
        return out

    values.sort(reverse=True)
    total = math.fsum(values)
    hhi = math.fsum(w * w for w in values)
    out["top10_weight"] = math.fsum(values[:_TOP_N])
    out["hhi"] = hhi
    out["effective_n"] = (1.0 / hhi) if hhi > 0 else None
    out["unlisted_remainder"] = max(0.0, 1.0 - total)
    out["holdings_count"] = float(len(values))
    return out


def duration_rate_sensitivity(
    bond_duration: float | None, nav_per_share: float | None
) -> dict[str, float | None] | None:
    """NAV change for a ±100 bp parallel shift in rates, or ``None``.

    First-order modified-duration estimate ``ΔP/P ≈ −D × Δy``: a +100 bp shift
    moves NAV by ``−duration × 1%`` (a negative move for a positive duration),
    −100 bp by ``+duration × 1%``. Both the fractional and the dollar change
    (per ``nav_per_share``) are returned. ``None`` when either input is missing —
    a bond fund with no reported duration has no rate sensitivity to state.
    """
    if bond_duration is None or nav_per_share is None:
        return None
    if not (math.isfinite(bond_duration) and math.isfinite(nav_per_share)):
        return None
    up = -bond_duration * _100BP
    down = bond_duration * _100BP
    return {
        "modified_duration": bond_duration,
        # Fractional NAV moves (``-0.0354`` = -3.54%) …
        "nav_change_up_100bp": up,
        "nav_change_down_100bp": down,
        # … and the same move in dollars per share, explicitly suffixed.
        "nav_change_up_100bp_usd": nav_per_share * up,
        "nav_change_down_100bp_usd": nav_per_share * down,
    }


def premium_discount(nav_per_share: float | None, market_price: float | None) -> float | None:
    """Market price vs NAV as a fraction (``market / nav − 1``), or ``None``.

    Positive = trading at a premium to NAV (common for a closed-end fund);
    negative = a discount. ``None`` when either leg is missing or NAV is
    non-positive (the ratio is undefined without a positive NAV anchor).
    """
    if nav_per_share is None or market_price is None:
        return None
    if not (math.isfinite(nav_per_share) and math.isfinite(market_price)) or nav_per_share <= 0:
        return None
    return market_price / nav_per_share - 1.0
