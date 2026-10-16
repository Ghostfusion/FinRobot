"""Provider-agnostic historical financials extractor.

What this code does that raw LLM cannot:
- Consumes ``DataLayer.fetch_historical(FINANCIALS)`` — a list of per-year
  DataResults whose ``.data`` dicts follow the canonical normalized schema both
  providers emit (FMP and yfinance) — and assembles a typed HistoricalMetrics
  with CFA-standard derived ratios/CAGR. An LLM would produce plausible-but-
  varying numbers across invocations.
- Owns no provider/yfinance knowledge: the DataLayer provider chain
  (eodhd → moomoo → fmp → yfinance) selects the source and normalizes its shape. This module is
  the single point where all yfinance access for DCF history was收口 into the
  DataLayer abstraction (门一), so the future circuit-breaker covers it.
- Sorts data oldest-first so all parallel list fields are time-aligned. Absolute
  line items keep the None→0.0 fill the downstream dcf_seed medians expect (an
  all-zero row reads as "missing"); derived margins instead stay None when their
  numerator is absent, so a missing margin never reads as a real 0%.
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from typing import Any

from finrobot.engine.compute.operators.data_processor import calculate_cagr
from finrobot.engine.data.historical_loaders import resolve_historical_fx
from finrobot.engine.data.interface import DataResult, ProviderError
from finrobot.engine.data.layer import DataLayer
from finrobot.engine.data.types import DataType
from finrobot.engine.models.financial import HistoricalMetrics
from finrobot.engine.primitives.industry import is_commodity_cyclical

# Default trailing window for non-cyclicals: equity-research convention seeds the
# DCF off the trailing ~5y (sliced to ~3y for the median inside dcf_seed).
_DEFAULT_HISTORY_YEARS: int = 5

# Cyclical / commodity names need a window that spans a FULL business cycle plus
# the current regime (peak→trough→recovery), so the through-cycle median isn't
# computed on a truncated half-cycle. Memory was peak FY2018 → trough FY2023 →
# AI super-cycle FY2024-2026 (SEC-verified), ≈9 fiscal years end-to-end; pull 10
# so the whole cycle is in-window. Lands in its own cache slot (the cache key
# folds in ``years``, so 10 never collides with the 5-year slot — T6#2).
_CYCLICAL_HISTORY_YEARS: int = 10

# A cyclical whose chain fetch (FMP / yfinance) yields fewer usable years than this
# is missing peak/trough phases — augment with SEC companyfacts deep history. The
# memory cycle spans ~9 fiscal years (FY2018 peak → FY2023 trough → FY2025
# recovery); 6 is the floor below which the trailing window can't straddle a full
# peak→trough (it would catch only the current regime + one turn). FMP/yfinance
# empirically field ~4, so this fires for every memory/storage name on the default
# chain while never second-guessing a chain that already returned deep enough.
_MIN_THROUGH_CYCLE_YEARS: int = 6

# Plausibility guard for a provider's annual cost lines (owner review: EHC FY2025
# printed a 95.7% gross margin against 43.9% TTM).
#
# A fiscal year whose gross margin deviates by more than this many percentage
# points from EVERY available reference — the median of the OTHER years in the
# window and, when the provider reports one, its own TTM gross margin — is not a
# margin the business can have: the cost line feeding it is crossed or missing.
# Live case (probe 2026-10-13): Yahoo's EHC annual frame carries FY2025
# ``Cost Of Revenue`` 254.4M (the real SG&A magnitude) and ``Selling General And
# Administration`` 3411.1M (the real cost of revenue), so Yahoo's own
# ``Gross Profit`` row reads revenue − 254.4M = 5680.8M → 95.7%, against 40-42%
# for FY2022-24 and 43.9% TTM (the same cross appears in every quarterly column
# from 2025-09-30 on). Requiring agreement from BOTH references keeps a genuinely
# unusual year — a one-off margin step the TTM figure also reflects — out of the
# repair; when only one reference is available the guard still fires on it.
_GROSS_MARGIN_PLAUSIBILITY_PP = 0.30

# Minimum number of OTHER years before their median may serve as the guard's
# fallback reference. With one or two peers the "median" IS one of those years (or
# their average), so a single crossed year would drag the reference toward itself
# and the guard would then "repair" the HEALTHY years to match the broken one.
# Below this the provider's TTM margin is the only reference — and on a snapshot it
# is essentially always present, so the guard still fires where it matters.
_MIN_PEER_YEARS_FOR_MEDIAN = 3

# An annual series whose newest fiscal year ends this many months (or more) before
# the canonical TTM window end has silently dropped a reported period (owner
# review: "EPS and cash-flow charts stop at 2024" — a truncated provider fetch).
# Disclosed, never charted silently. 15 months = the newest year is more than a
# full fiscal year + the normal reporting lag behind the TTM window.
_ANNUAL_SERIES_MAX_LAG_MONTHS = 15

# The annual bars and the report's TTM EBITDA are DIFFERENT constructs, and the
# report compares them side by side: the bars take the provider's own-reported
# ``ebitda`` field verbatim per fiscal year, while the TTM figure is computed as
# operating income + D&A (engine/primitives/ebitda.py). This label is chosen only
# when the two genuinely disagree (see ebitda_caliber_label), so it states exactly
# that — the provider's annual figure is not its own operating income + D&A.
#
# It used to attribute the gap to "two different D&A calibers". That explanation is
# not supported by the numbers: NVDA FY2026's bar (144.552B) exceeds its own
# operating income + D&A (130.387B + 2.843B = 133.230B) by 8.5%, while the provider's
# D&A row is 1.3% of revenue — the same ratio as the TTM leg (1.2%), so D&A is not
# what differs. The gap is a different EBITDA CONSTRUCT (a provider figure that
# carries items this run's operating caliber excludes) and the label now says only
# what the comparison actually established (owner review 2026-10-16, item 8: "the
# 'not a data error' note should be verified"). Frozen onto every historical payload
# (builders.py) as ``historical_metrics.ebitda_caliber``.
EBITDA_CALIBER_LABEL = (
    "Annual bars are the provider's reported EBITDA per fiscal year; the TTM EBITDA "
    "shown beside them is computed as operating income + D&A. Those are different "
    "constructs for this issuer — the annual figure is not its own operating income "
    "+ D&A — so they must not be read as one continuous series; the difference is a "
    "definition, not a data error"
)

# The SAME-caliber label: when the newest annual bar IS operating income + D&A — the
# same formula the TTM figure uses, which is what a yfinance-served report looks like
# (Yahoo's own annual EBITDA row is exactly EBIT + its D&A) — the two figures are
# directly comparable and the mixed-caliber note would assert a gap that does not
# exist. GMED 2026-10-14 froze the mixed note while its newest annual bar
# (814,033,000) WAS 537,191,000 + 276,842,000 to the dollar.
EBITDA_CALIBER_SAME_LABEL = (
    "Annual bars are the provider's reported EBITDA per fiscal year; the TTM EBITDA "
    "shown beside them is the same operating caliber (operating income + D&A), so the "
    "two are directly comparable"
)

# Relative tolerance for "the annual bar IS the operating caliber": 1% absorbs
# provider rounding without accepting a genuinely different D&A definition.
_EBITDA_CALIBER_TOLERANCE = 0.01


def ebitda_caliber_label(
    ebitda: Sequence[float | None],
    operating_income: Sequence[float | None],
    depreciation_amortization: Sequence[float | None],
) -> str:
    """Which caliber note is TRUE for this history — the fact, not a constant.

    The report puts an annual EBITDA series directly beside a TTM figure and asks the
    reader to compare them, so whether they share a caliber is a property of the two
    series. Compares the NEWEST year only (the bar standing next to the TTM figure);
    any missing or non-finite leg keeps the mixed-caliber label, which is the
    conservative claim — it warns rather than reassures.
    """
    if not ebitda or not operating_income or not depreciation_amortization:
        return EBITDA_CALIBER_LABEL
    newest_ebitda = ebitda[-1]
    newest_operating = operating_income[-1]
    newest_da = depreciation_amortization[-1]
    if newest_ebitda is None or newest_operating is None or newest_da is None:
        return EBITDA_CALIBER_LABEL
    if not all(math.isfinite(v) for v in (newest_ebitda, newest_operating, newest_da)):
        return EBITDA_CALIBER_LABEL
    if newest_ebitda == 0:
        return EBITDA_CALIBER_LABEL
    same = abs(newest_ebitda - (newest_operating + newest_da)) <= (
        abs(newest_ebitda) * _EBITDA_CALIBER_TOLERANCE
    )
    return EBITDA_CALIBER_SAME_LABEL if same else EBITDA_CALIBER_LABEL


async def fetch_historical_metrics(
    data_layer: DataLayer,
    ticker: str,
    years: int | None = None,
    *,
    industry: str | None = None,
    sector: str | None = None,
) -> HistoricalMetrics:
    """Fetch multi-year financials via the DataLayer and build HistoricalMetrics.

    Args:
        data_layer: The shared DataLayer (provider chain eodhd → moomoo → fmp → yfinance).
        ticker: Upper-case stock ticker symbol (e.g. "AAPL").
        years: Maximum number of annual periods to include. ``None`` (the default)
            means AUTO: 5 for a normal name, 10 for a commodity-cyclical so the
            through-cycle median sees a full peak→trough→recovery window. Pass an
            explicit int only to override (e.g. the /historical route's UI window).
        industry: Provider industry label, when the caller already has the
            snapshot. Lets a non-memory cyclical (steel/oil/shipping) also get the
            extended window. None is fine — memory/storage names still extend via
            the curated ticker anchor inside ``is_commodity_cyclical``.
        sector: Provider sector label (reserved; industry tag is decisive).

    Returns:
        Fully populated HistoricalMetrics, sorted oldest-first. Returns a minimal
        placeholder (empty lists) when no usable historical data is available, so
        callers/dcf_seed degrade gracefully to industry medians rather than crash.

    Currency: a foreign issuer's yearly statements arrive in the native
    reporting currency (TSM: TWD) while the snapshot FinancialData in the same
    report is FX-normalized to the quote currency — the multi-year revenue/EPS
    charts and LLM narrative were silently mixing the two. Absolute monetary
    fields are converted at today's spot via the same chokepoint the band
    loader uses (resolve_historical_fx); ratios/margins/CAGR are
    currency-invariant. When FX is unavailable the figures stay native and the
    ``currency`` tag discloses it (the metrics still serve dcf_seed's
    currency-invariant ratio medians, so dropping them would be overkill).
    """
    # AUTO window: extend for commodity-cyclicals so the through-cycle median has a
    # full cycle in-window. The ticker anchor covers memory/storage on every call
    # site (none of which carries a description); industry covers the rest when the
    # caller has it. An explicit ``years`` always wins (the UI /historical window).
    cyclical = False
    if years is None:
        cyclical = is_commodity_cyclical(industry=industry, sector=sector, ticker=ticker)
        years = _CYCLICAL_HISTORY_YEARS if cyclical else _DEFAULT_HISTORY_YEARS
    results = await data_layer.fetch_historical(DataType.FINANCIALS, ticker, years=years)
    # Deep-history augmentation: FMP / yfinance only field ~4 annual periods, which
    # truncates a commodity-cyclical's through-cycle window (the MU FY2018 peak +
    # FY2018-22 downturn fall off-window, so the trailing median misprices). When a
    # cyclical's chain fetch is shallower than the window needs, pull the full SEC
    # companyfacts history (≥9y, no API key) and use it when it is genuinely deeper.
    # Non-cyclicals never touch SEC — their FMP/yfinance window stays byte-identical.
    if cyclical and _usable_year_count(results) < _MIN_THROUGH_CYCLE_YEARS:
        sec_results = await data_layer.fetch_deep_history(ticker, years)
        if sec_results is not None and _usable_year_count(sec_results) > _usable_year_count(
            results
        ):
            results = sec_results
    fx = await resolve_historical_fx(results, data_layer, ticker)
    # Trailing P/E + the TTM references (gross margin, window end) come from the
    # current-snapshot financials (yfinance's info). Best-effort and normally a
    # cache hit — most callers fetched the snapshot moments earlier.
    snapshot = await _fetch_snapshot_context(data_layer, ticker)
    return _build_from_yearly(
        ticker,
        results,
        years,
        snapshot.trailing_pe,
        fx_rate=fx.rate if fx.rate is not None else 1.0,
        currency=fx.currency_of_figures,
        data_source=_aggregate_provider(results),
        ttm_gross_margin=snapshot.ttm_gross_margin,
        ttm_period_end=snapshot.period_end,
    )


def _aggregate_provider(results: list[DataResult]) -> str | None:
    """Collapse per-year provider tags into one provenance string.

    One fetch normally serves every year from the same provider, but the
    contract doesn't promise it — an honest "mixed:a+b" beats silently
    reporting whichever year came last. None when there are no rows.
    """
    providers = sorted({r.provider for r in results if r.provider})
    if not providers:
        return None
    if len(providers) == 1:
        return providers[0]
    return "mixed:" + "+".join(providers)


@dataclass(frozen=True)
class _SnapshotContext:
    """TTM reference values the historical series needs, from ONE snapshot fetch.

    All three are best-effort: an unavailable snapshot leaves them None and each
    consumer degrades on its own (the P/E point is simply not plotted; the
    plausibility guard falls back to the median of the other years; the lag guard
    abstains).
    """

    trailing_pe: float | None = None
    ttm_gross_margin: float | None = None
    period_end: date | None = None


async def _fetch_snapshot_context(data_layer: DataLayer, ticker: str) -> _SnapshotContext:
    """Best-effort TTM references from the snapshot FINANCIALS canonical payload.

    ``trailing_pe`` fills the newest year's P/E point; ``ttm_gross_margin`` is the
    plausibility guard's primary reference margin; ``period_end`` is the TTM window
    end the annual series is measured against (so a truncated series is disclosed
    rather than charted silently).
    """
    try:
        fin = await data_layer.fetch_canonical(DataType.FINANCIALS, ticker)
        # NormalizedFinancials carries pe_ratio / gross_margin as typed optional floats.
        from finrobot.engine.data.normalize.contracts import NormalizedFinancials

        if isinstance(fin, NormalizedFinancials):
            return _SnapshotContext(
                trailing_pe=fin.pe_ratio,
                ttm_gross_margin=fin.gross_margin,
                period_end=fin.period_end,
            )
        return _SnapshotContext()
    except (ProviderError, ValueError, KeyError):
        return _SnapshotContext()


def _build_from_yearly(
    ticker: str,
    results: list[DataResult],
    max_years: int,
    trailing_pe: float | None,
    fx_rate: float = 1.0,
    currency: str | None = None,
    data_source: str | None = None,
    ttm_gross_margin: float | None = None,
    ttm_period_end: date | None = None,
) -> HistoricalMetrics:
    """Pure function: assemble HistoricalMetrics from normalized per-year dicts.

    Kept separate from the async wrapper so it can be tested synchronously.
    ``fx_rate`` scales every absolute monetary field (financial→quote spot);
    ``currency`` is the tag for the figures AFTER scaling. Ratios computed
    below are invariant (numerator and denominator scale together).

    ``ttm_gross_margin`` / ``ttm_period_end`` are the current snapshot's TTM
    references. They gate the two series guards below: a year whose cost lines are
    crossed/missing is repaired (and the repair disclosed), and an annual series
    that lags the TTM window is flagged — neither may ship silently.
    """
    # Parse rows; drop years without usable revenue (mirrors the old
    # revenue-NaN column filter so a NaN year doesn't poison CAGR/medians).
    rows: list[tuple[str, int, dict[str, Any]]] = []
    for result in results:
        data = result.data if isinstance(result.data, dict) else {}
        rev = _safe_float(data.get("revenue"))
        if rev is None or rev <= 0:
            continue
        fiscal_raw = data.get("fiscal_year") or data.get("date")
        year = _year_of(fiscal_raw)
        if year is None:
            continue
        rows.append((str(fiscal_raw), year, data))

    if not rows:
        return _empty_metrics(ticker)

    # Oldest-first, then window to the most recent ``max_years``.
    rows.sort(key=lambda r: r[0])
    rows = rows[-max_years:]

    years_list: list[int] = []
    revenue_list: list[float] = []
    gp_list: list[float | None] = []
    gross_margin_list: list[float | None] = []
    cogs_list: list[float | None] = []
    ebitda_list: list[float] = []
    ebitda_margin_list: list[float | None] = []
    oi_list: list[float] = []
    operating_margin_list: list[float | None] = []
    ni_list: list[float] = []
    eps_list: list[float] = []
    sga_list: list[float] = []
    sga_ratio_list: list[float | None] = []
    ocf_list: list[float] = []
    icf_list: list[float] = []
    financing_cf_list: list[float] = []
    da_list: list[float] = []
    capex_list: list[float] = []
    nwc_change_list: list[float] = []
    equity_list: list[float | None] = []
    # Provider's own reported cost-of-revenue leg (None on providers that don't
    # carry one). Only the gross-margin plausibility guard reads it.
    cost_of_revenue_list: list[float | None] = []
    # Raw per-year fiscal-end strings, oldest-first — the lag guard's input.
    fiscal_end_list: list[str] = []

    for fy_str, year, data in rows:
        # Raw (None when the provider omitted the row) drives the margins below
        # so a *missing* numerator yields a None margin, not a fabricated 0%.
        # The absolute line-item lists keep the 0.0 fill — downstream consumers
        # (dcf_seed._median_ratio, shares-from-EPS) already treat all-zero rows
        # as "missing", so 0.0 there is the established convention.
        raw_gp = _fx(_safe_float(data.get("gross_profit")), fx_rate)
        raw_ebitda = _fx(_safe_float(data.get("ebitda")), fx_rate)
        raw_oi = _fx(_safe_float(data.get("operating_income")), fx_rate)
        raw_sga = _fx(_safe_float(data.get("sga_expense")), fx_rate)
        rev = (_safe_float(data.get("revenue")) or 0.0) * fx_rate
        ebitda = raw_ebitda or 0.0
        oi = raw_oi or 0.0
        ni = (_safe_float(data.get("net_income")) or 0.0) * fx_rate
        eps = (_safe_float(data.get("eps")) or 0.0) * fx_rate
        sga = raw_sga or 0.0

        rev_positive = rev > 0
        years_list.append(year)
        revenue_list.append(rev)
        fiscal_end_list.append(fy_str)
        # cogs / gross_profit propagate None when the provider omits gross_profit
        # (no-COGS businesses like banks) — never fabricate cogs = revenue − 0,
        # which would render a bank's COGS as its full revenue.
        gp_list.append(raw_gp)
        gross_margin_list.append(raw_gp / rev if (raw_gp is not None and rev_positive) else None)
        cogs_list.append(rev - raw_gp if raw_gp is not None else None)
        ebitda_list.append(ebitda)
        ebitda_margin_list.append(
            raw_ebitda / rev if (raw_ebitda is not None and rev_positive) else None
        )
        oi_list.append(oi)
        operating_margin_list.append(
            raw_oi / rev if (raw_oi is not None and rev_positive) else None
        )
        ni_list.append(ni)
        eps_list.append(eps)
        sga_list.append(sga)
        sga_ratio_list.append(raw_sga / rev if (raw_sga is not None and rev_positive) else None)

        # Cash-flow scalars: a structurally-absent row stays 0.0. dcf_seed's
        # _median_ratio treats an all-zero row as "missing" and falls back to
        # industry medians, so 0.0 is the correct fill (not a fabricated value).
        ocf_list.append((_safe_float(data.get("operating_cash_flow")) or 0.0) * fx_rate)
        icf_list.append((_safe_float(data.get("investing_cash_flow")) or 0.0) * fx_rate)
        financing_cf_list.append((_safe_float(data.get("financing_cash_flow")) or 0.0) * fx_rate)
        # D&A is reported positive; CapEx is already a positive magnitude
        # (providers sign-flip the cash outflow) — both feed the FCF formula's
        # "+ D&A - CapEx" convention as positive numbers.
        da_list.append((_safe_float(data.get("depreciation_amortization")) or 0.0) * fx_rate)
        capex_list.append((_safe_float(data.get("capital_expenditure")) or 0.0) * fx_rate)
        nwc_change_list.append(
            (_safe_float(data.get("change_in_working_capital")) or 0.0) * fx_rate
        )
        # Per-year parent equity (None when omitted). FX-scaled like net_income so the
        # net_income/equity through-cycle ROE ratio is currency-invariant either way.
        equity_list.append(_fx(_safe_float(data.get("total_equity")), fx_rate))
        # Provider's own cost-of-revenue leg, FX-scaled like every other absolute
        # monetary field so it stays comparable with revenue_list.
        cost_of_revenue_list.append(_fx(_safe_float(data.get("cost_of_revenue")), fx_rate))

    # YoY revenue growth (None for the oldest year and across any 0-fill gaps).
    revenue_growth: list[float | None] = []
    for i, rev in enumerate(revenue_list):
        if i == 0:
            revenue_growth.append(None)
            continue
        prev = revenue_list[i - 1]
        revenue_growth.append((rev - prev) / prev if prev > 0 and rev > 0 else None)

    n = len(years_list)
    cagr = calculate_cagr(revenue_list[0], revenue_list[-1], n - 1) if n >= 2 else None

    # Trailing P/E only on the most-recent year (historical P/E needs per-year
    # price, which the financials feed doesn't carry); keeps EpsPeChart honest.
    pe_list: list[float | None] = [None] * n
    if trailing_pe is not None and n > 0:
        pe_list[-1] = trailing_pe

    # Series guards. Both are disclosure-first: they repair/flag what cannot be
    # true and record WHY in HistoricalMetrics.warnings, so a crossed cost line or
    # a truncated annual fetch never ships as a silently wrong chart.
    series_warnings: list[str] = []
    series_warnings += _repair_implausible_gross_margins(
        years=years_list,
        revenue=revenue_list,
        gross_profit=gp_list,
        cogs=cogs_list,
        gross_margin=gross_margin_list,
        sga=sga_list,
        sga_ratio=sga_ratio_list,
        cost_of_revenue=cost_of_revenue_list,
        ttm_gross_margin=ttm_gross_margin,
    )
    series_warnings += _annual_series_lag_warnings(
        fiscal_ends=fiscal_end_list, ttm_period_end=ttm_period_end
    )

    return HistoricalMetrics(
        warnings=series_warnings,
        currency=currency,
        data_source=data_source,
        years=years_list,
        revenue=revenue_list,
        revenue_growth_yoy=revenue_growth,
        cogs=cogs_list,
        gross_profit=gp_list,
        gross_margin=gross_margin_list,
        sga=sga_list,
        sga_ratio=sga_ratio_list,
        ebitda=ebitda_list,
        ebitda_margin=ebitda_margin_list,
        operating_income=oi_list,
        operating_margin=operating_margin_list,
        net_income=ni_list,
        eps=eps_list,
        pe_ratio=pe_list,
        cagr_revenue=cagr,
        ticker=ticker,
        price_data_available=trailing_pe is not None,
        operating_cash_flow=ocf_list,
        investing_cash_flow=icf_list,
        financing_cash_flow=financing_cf_list,
        depreciation_amortization=da_list,
        capital_expenditure=capex_list,
        change_in_working_capital=nwc_change_list,
        shareholders_equity=equity_list,
    )


def _parse_iso_date(raw: object) -> date | None:
    """Parse a 'YYYY-MM-DD' (or longer) period-end string; None when it isn't one."""
    if raw is None:
        return None
    try:
        return date.fromisoformat(str(raw)[:10])
    except ValueError:
        return None


def _months_between(older: date, newer: date) -> int:
    """Whole calendar months from ``older`` to ``newer`` (negative when reversed)."""
    return (newer.year - older.year) * 12 + (newer.month - older.month)


def _repair_implausible_gross_margins(
    *,
    years: list[int],
    revenue: list[float],
    gross_profit: list[float | None],
    cogs: list[float | None],
    gross_margin: list[float | None],
    sga: list[float],
    sga_ratio: list[float | None],
    cost_of_revenue: list[float | None],
    ttm_gross_margin: float | None,
) -> list[str]:
    """Repair, in place, any fiscal year whose cost lines are crossed or missing.

    A year fires when its gross margin deviates from EVERY available reference by
    more than ``_GROSS_MARGIN_PLAUSIBILITY_PP`` — the median of the other years in
    the window (only once ``_MIN_PEER_YEARS_FOR_MEDIAN`` peers exist) and, when the
    provider reports one, its own TTM gross margin (see that constant's comment for
    the live EHC FY2025 case).

    Repair candidates, first CONSISTENT one wins (|candidate − reference| ≤ PP):

      1. ``revenue − sga_expense`` — the crossed pair's other leg. Adopting it
         swaps the two line items back, so the year's ``sga`` also becomes its
         true SG&A (EHC FY2025 → 42.5%, the actual margin).
      2. ``revenue − cost_of_revenue`` — the provider's own cost leg, for a year
         whose ``Gross Profit`` row alone is stale.
      3. ``reference × revenue`` — the provider's own margin applied to the year,
         the disclosed fallback that always matches the reference (so a year whose
         cost lines cannot be reconciled still publishes a stated, sane margin
         rather than an impossible one).

    Every repair is described in the returned warnings.
    """
    warnings: list[str] = []
    for i, margin in enumerate(gross_margin):
        rev = revenue[i]
        if margin is None or rev <= 0:
            continue
        others = [m for j, m in enumerate(gross_margin) if j != i and m is not None]
        # See _MIN_PEER_YEARS_FOR_MEDIAN: too few peers makes the "median" a mirror
        # of the suspect year, which would drag the healthy years toward it.
        median_other = (
            statistics.median(others) if len(others) >= _MIN_PEER_YEARS_FOR_MEDIAN else None
        )
        references = [r for r in (median_other, ttm_gross_margin) if r is not None]
        if not references or not all(
            abs(margin - r) > _GROSS_MARGIN_PLAUSIBILITY_PP for r in references
        ):
            continue
        reference = ttm_gross_margin if ttm_gross_margin is not None else median_other
        if reference is None:  # unreachable — ``references`` is non-empty here
            continue
        reference_label = (
            "provider TTM margin" if ttm_gross_margin is not None else "other years' median"
        )
        refs_text = ", ".join(
            f"{name} {value:.1%}"
            for name, value in (
                ("other years' median", median_other),
                ("provider TTM", ttm_gross_margin),
            )
            if value is not None
        )
        sga_i = sga[i]
        cor_i = cost_of_revenue[i]
        candidates: list[tuple[str, float, float | None]] = []
        if sga_i > 0:
            # (1) the crossed pair's other leg — this year's SG&A carries the real COGS.
            candidates.append(("revenue − SG&A (crossed cost lines)", rev - sga_i, cogs[i]))
        if cor_i is not None:
            candidates.append(("revenue − reported cost of revenue", rev - cor_i, None))
        candidates.append((f"{reference_label} {reference:.1%} × revenue", reference * rev, None))

        for label, new_gp, new_sga in candidates:
            new_margin = new_gp / rev
            if abs(new_margin - reference) > _GROSS_MARGIN_PLAUSIBILITY_PP:
                continue
            gross_profit[i] = new_gp
            cogs[i] = rev - new_gp
            gross_margin[i] = new_margin
            if new_sga is not None:
                sga[i] = new_sga
                sga_ratio[i] = new_sga / rev
            warnings.append(
                f"FY{years[i]} gross margin {margin:.1%} deviates >"
                f"{_GROSS_MARGIN_PLAUSIBILITY_PP:.0%} from every reference ({refs_text}) — "
                f"the year's cost lines are crossed or missing; repaired via {label} to "
                f"{new_margin:.1%} instead of publishing the impossible value"
            )
            break
    return warnings


def _annual_series_lag_warnings(
    *, fiscal_ends: list[str], ttm_period_end: date | None
) -> list[str]:
    """Disclose an annual series that lags the canonical TTM window end.

    A provider fetch can silently return a SHORTER annual frame than the reported
    periods (the yfinance annual statement not yet exposing the newest fiscal
    year), which charts an EPS / cash-flow trajectory stopping a year early. Fires
    when the newest parsed fiscal end is more than ``_ANNUAL_SERIES_MAX_LAG_MONTHS``
    months before ``ttm_period_end``; abstains when either side is unknown.
    """
    if ttm_period_end is None:
        return []
    newest: date | None = None
    for raw in reversed(fiscal_ends):
        newest = _parse_iso_date(raw)
        if newest is not None:
            break
    if newest is None:
        return []
    months = _months_between(newest, ttm_period_end)
    if months <= _ANNUAL_SERIES_MAX_LAG_MONTHS:
        return []
    return [
        f"Annual series lags the reported periods: the newest fiscal year ends "
        f"{newest.isoformat()} while the TTM window ends {ttm_period_end.isoformat()} "
        f"({months} months later) — the provider's annual statement is missing the newest "
        f"reported period(s), so the trajectory/charts stop early rather than at the "
        f"latest data; read the newest year as absent, not flat"
    ]


def _empty_metrics(ticker: str) -> HistoricalMetrics:
    """Minimal placeholder when no usable history exists.

    Cash-flow / DCF list fields default to [] via the model; dcf_seed detects
    emptiness and falls back to industry medians.
    """
    return HistoricalMetrics(
        years=[],
        revenue=[],
        revenue_growth_yoy=[],
        cogs=[],
        gross_profit=[],
        gross_margin=[],
        sga=[],
        sga_ratio=[],
        ebitda=[],
        ebitda_margin=[],
        operating_income=[],
        operating_margin=[],
        net_income=[],
        eps=[],
        pe_ratio=[],
        cagr_revenue=None,
        ticker=ticker,
    )


def _fx(value: float | None, rate: float) -> float | None:
    """Scale an optional monetary value by the FX rate, preserving None."""
    return value * rate if value is not None else None


def _usable_year_count(results: list[DataResult]) -> int:
    """How many rows carry a usable (positive, finite) revenue.

    Mirrors the row filter in ``_build_from_yearly`` so the deep-history decision
    counts the SAME years that will actually feed the medians — a DataResult list
    whose rows are all revenue-less (an error/empty fetch) reads as 0, never as its
    nominal length, so a shallow-but-nonempty chain result can't block the SEC
    augmentation.
    """
    count = 0
    for result in results:
        data = result.data if isinstance(result.data, dict) else {}
        rev = _safe_float(data.get("revenue"))
        if rev is not None and rev > 0:
            count += 1
    return count


def _safe_float(value: object) -> float | None:
    """Convert a scalar to float; return None on any error or NaN.

    NaN is treated as missing — not a legitimate 0 — so a row that exists but is
    empty doesn't masquerade as a real zero in the derived ratios.
    """
    if value is None:
        return None
    try:
        result = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return None if math.isnan(result) else result


def _year_of(raw: object) -> int | None:
    """Extract the 4-digit fiscal year from a 'YYYY-MM-DD' (or 'YYYY') value."""
    if raw is None:
        return None
    text = str(raw)
    try:
        return int(text[:4])
    except ValueError:
        return None
