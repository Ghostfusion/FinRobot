"""Fund coordinator — canonical fund profile + NAV/price series → FundData → FundAssessment.

A 取数协调器 (ADR-0005), NOT a leaf: unlike the pure ``fund_metrics`` operators
it feeds, it may touch the data layer. It owns the two things the operators must
not: the fetch (provider chain + circuit breaker + provenance) and the projection
of the canonical contracts onto the engine models.

The NAV/price series comes from the explicit ``PRICE_RANGE`` door — ~5 years of
adjusted daily closes. The trailing-~252-bar canonical ``PRICE`` cannot span the
1y CAGR window (a window needs ``years*252 + 1`` points), let alone 3y/5y or a
bond fund's multi-year drawdown (IEI: 251 bars, VTSAX: 253). For an ETF the
traded close tracks NAV; for a NAV-priced mutual fund the closing price IS the
NAV, so one series serves both.
"""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from finrobot.engine.compute.operators.fund_metrics import (
    DAYS_PER_YEAR,
    duration_rate_sensitivity,
    expense_cost_analysis,
    nav_series_statistics,
    portfolio_concentration,
    premium_discount,
    years_ago,
)
from finrobot.engine.data.interface import ProviderError
from finrobot.engine.data.normalize.contracts import (
    NormalizedFundHoldings,
    NormalizedFundProfile,
    PriceBar,
)
from finrobot.engine.data.types import DataType
from finrobot.engine.models.fund import FundAssessment, FundData, FundHolding, FundProvenance

if TYPE_CHECKING:
    from finrobot.engine.data.layer import DataLayer

#: ``portfolio_source`` when the concentration panel is the fund's own SEC
#: N-PORT filing rather than the vendor's top-holdings excerpt.
_SEC_PORTFOLIO_SOURCE = "sec_nport"
#: Wall-clock budget for the optional FUND_HOLDINGS side-fetch. SEC is slow
#: (measured 2026-10-12: ~10s cold) and a fund report must never hang on it, so a
#: timeout degrades to the vendor top-holdings exactly like a ProviderError.
_FUND_HOLDINGS_TIMEOUT_S = 45.0

#: Horizon for the expense cost-drag illustration ($ per $10,000 holding).
_COST_DRAG_HORIZON_YEARS = 5
#: Risk-free anchor for the Sharpe ratio. 0.0 keeps it an honest excess-over-cash
#: measure rather than inventing a market rate the profile does not carry.
_DEFAULT_RISK_FREE_RATE = 0.0
#: Years of NAV/price history requested for the series.
#:
#: SIX, not five: a window of exactly N calendar years can never measure an N-year
#: CAGR, because the window is anchored on the LAST bar while the series starts at
#: the first session at-or-after ``today − N``. Measured live 2026-10-12 on IEI:
#: a 5-year request returned 1253 bars spanning 2021-10-13 → 2026-10-09 (4.988
#: years — the last session was Friday, Monday being a market holiday), so the 5y
#: window was one week out of reach and the report warned instead of publishing the
#: number. One extra year covers the boundary with room for holidays and for the
#: long weekend at either end, and buys a fuller multi-year drawdown too.
_NAV_SERIES_YEARS = 6


async def _fetch_nav_range_bars(ticker: str, layer: DataLayer) -> list[PriceBar]:
    """~``_NAV_SERIES_YEARS`` years of adjusted daily closes (ascending).

    ``fetch_price_range`` raises ``ProviderError`` when every capable provider
    fails; ``DataLayer`` normalizes/trims, this only drops unusable points.
    """
    today = datetime.now(tz=timezone.utc).date()
    start = years_ago(today, _NAV_SERIES_YEARS)
    end_exclusive = today + timedelta(days=1)
    bars = await layer.fetch_price_range(ticker, start.isoformat(), end_exclusive.isoformat())
    return [bar for bar in bars if bar.close > 0 and bar.date >= start]


async def _fetch_optional_fund_holdings(
    ticker: str, layer: DataLayer, warnings: list[str]
) -> NormalizedFundHoldings | None:
    """The fund's SEC N-PORT portfolio, or ``None`` when it cannot be served.

    Optional and always-degrading: any failure (slow/unreachable SEC, an
    unresolvable ticker, an unparseable filing) yields ``None`` and a warning,
    never a failed fund report — mirroring the NAV-series fallback below. The
    fetch is bounded by ``_FUND_HOLDINGS_TIMEOUT_S`` so a slow SEC cannot stall a
    fund report; the timeout path is just another degrade.
    """
    try:
        result = await asyncio.wait_for(
            layer.fetch_canonical(DataType.FUND_HOLDINGS, ticker),
            timeout=_FUND_HOLDINGS_TIMEOUT_S,
        )
    except (ProviderError, TimeoutError, ValueError, KeyError) as exc:
        warnings.append(
            f"The fund's own SEC N-PORT portfolio is unavailable for {ticker} "
            f"({type(exc).__name__}: {exc}); the portfolio panel falls back to the "
            "vendor's top-holdings excerpt, which typically covers only the largest "
            "positions."
        )
        return None
    if isinstance(result, NormalizedFundHoldings) and result.holdings:
        return result
    return None


async def build_fund_data(ticker: str, layer: DataLayer) -> FundData:
    """Fetch the canonical fund profile + the NAV/price series and project them.

    The series is the ~5-year ``PRICE_RANGE`` history; when that fetch fails or
    returns nothing usable it falls back to the trailing-~1y canonical ``PRICE``
    (with an honest warning), so a provider that can only serve the short window
    still yields a report — just with 1y/3y/5y CAGRs and multi-year drawdowns
    limited to that window.

    Raises ``ProviderError`` (from the data layer) when no provider can serve a
    fund profile — e.g. the symbol is an operating company, which the fund
    providers refuse.
    """
    profile = await layer.fetch_canonical(DataType.FUND_PROFILE, ticker)

    bars: list[PriceBar] = []
    series_warnings: list[str] = []
    range_error: Exception | None = None
    try:
        bars = await _fetch_nav_range_bars(ticker, layer)
    except (ProviderError, ValueError, KeyError) as exc:
        range_error = exc

    if not bars:
        price = await layer.fetch_canonical(DataType.PRICE, ticker)
        bars = [bar for bar in price.bars if bar.close > 0]
        series_warnings.extend(price.warnings)
        reason = (
            f"{type(range_error).__name__}: {range_error}"
            if range_error is not None
            else "the provider returned no usable bars"
        )
        series_warnings.append(
            f"A {_NAV_SERIES_YEARS}-year NAV/price history is unavailable for {ticker} "
            f"({reason}); the series falls back to the trailing ~1-year canonical PRICE, so "
            "the 1y/3y/5y CAGRs and multi-year drawdowns stay limited to that window."
        )

    holdings = await _fetch_optional_fund_holdings(ticker, layer, series_warnings)

    return project_fund_data(profile, bars, series_warnings=series_warnings, holdings=holdings)


def project_fund_data(
    profile: NormalizedFundProfile,
    bars: Sequence[PriceBar],
    *,
    series_warnings: Sequence[str] = (),
    holdings: NormalizedFundHoldings | None = None,
) -> FundData:
    """Project the canonical fund profile + a NAV/price bar series into :class:`FundData`.

    ``holdings`` is the fund's own SEC N-PORT portfolio when it was available; it
    is carried ADDITIVELY as ``portfolio_holdings`` (with ``portfolio_source`` /
    ``portfolio_as_of`` provenance) and the coordinator prefers it for the
    concentration panel. When it is ``None`` the projection is byte-identical to
    the vendor-only behaviour — ``top_holdings`` is untouched.
    """
    portfolio_holdings: list[FundHolding] = []
    portfolio_source: str | None = None
    portfolio_as_of = None
    holdings_warnings: list[str] = []
    if holdings is not None and holdings.holdings:
        portfolio_holdings = [
            FundHolding(symbol=h.symbol, name=h.name, weight=h.weight) for h in holdings.holdings
        ]
        portfolio_source = _SEC_PORTFOLIO_SOURCE
        portfolio_as_of = holdings.as_of
        holdings_warnings.extend(holdings.warnings)

    return FundData(
        ticker=profile.ticker,
        name=profile.name,
        fund_family=profile.fund_family,
        legal_type=profile.legal_type,
        category=profile.category,
        quote_type=profile.quote_type,
        inception_date=profile.inception_date,
        currency=profile.currency,
        as_of=profile.as_of,
        total_net_assets=profile.total_net_assets,
        nav_per_share=profile.nav_per_share,
        market_price=profile.market_price,
        shares_outstanding=profile.shares_outstanding,
        net_expense_ratio=profile.net_expense_ratio,
        gross_expense_ratio=profile.gross_expense_ratio,
        category_avg_expense_ratio=profile.category_avg_expense_ratio,
        turnover=profile.turnover,
        distribution_yield=profile.distribution_yield,
        ytd_return=profile.ytd_return,
        return_3m=profile.return_3m,
        return_1y=profile.return_1y,
        return_3y_annual=profile.return_3y_annual,
        return_5y_annual=profile.return_5y_annual,
        beta_3y=profile.beta_3y,
        asset_classes=dict(profile.asset_classes),
        sector_weights=dict(profile.sector_weights),
        region_weights=dict(profile.region_weights),
        bond_ratings=dict(profile.bond_ratings),
        bond_duration=profile.bond_duration,
        bond_maturity=profile.bond_maturity,
        equity_pe=profile.equity_pe,
        top_holdings=[
            FundHolding(symbol=holding.symbol, name=holding.name, weight=holding.weight)
            for holding in profile.top_holdings
        ],
        portfolio_holdings=portfolio_holdings,
        portfolio_source=portfolio_source,
        portfolio_as_of=portfolio_as_of,
        nav_dates=[bar.date for bar in bars],
        nav_closes=[bar.close for bar in bars],
        provenance=FundProvenance(
            provider=profile.provenance.provider,
            as_of=profile.provenance.as_of,
            fetched_at=profile.provenance.fetched_at,
            degraded=list(profile.provenance.degraded),
        ),
        warnings=[*profile.warnings, *series_warnings, *holdings_warnings],
    )


def assess_fund(
    data: FundData,
    *,
    risk_free_rate: float = _DEFAULT_RISK_FREE_RATE,
    horizon_years: int = _COST_DRAG_HORIZON_YEARS,
) -> FundAssessment:
    """Compute the deterministic :class:`FundAssessment` from :class:`FundData`.

    Pure: identical ``FundData`` → identical assessment. Every operator returns
    ``None`` / an empty mapping when its inputs are missing, and this records why
    in ``warnings`` so the report can say "not available" instead of a fabricated
    number.
    """
    stats = nav_series_statistics(data.nav_closes, risk_free_rate, data.nav_dates)
    returns: dict[str, float | None] = {
        "cagr_1y": stats["cagr_1y"],
        "cagr_3y": stats["cagr_3y"],
        "cagr_5y": stats["cagr_5y"],
        "ytd": data.ytd_return,
        "return_3m": data.return_3m,
    }

    cost_drag = expense_cost_analysis(
        data.net_expense_ratio,
        data.gross_expense_ratio,
        stats["cagr_1y"],
        horizon_years,
        data.category_avg_expense_ratio,
    )

    # Prefer the fund's own SEC N-PORT portfolio when present: it is the FULL
    # reported portfolio, so the concentration panel reflects the real fund
    # (unlisted_remainder ≈ 0) instead of the vendor's top-N excerpt (which for
    # VTSAX left ~66% of net assets unaccounted). Fall back to the vendor
    # top-holdings byte-identically when SEC could not serve it.
    panel = data.portfolio_holdings or data.top_holdings
    holding_weights: dict[str, float] = {}
    for index, holding in enumerate(panel):
        if holding.weight is None:
            continue
        label = holding.symbol or holding.name or f"position_{index + 1}"
        # The full SEC portfolio routinely reports DISTINCT positions under the
        # same issuer name (IEI carries many separate Treasuries all named
        # "United States of America"), so a repeated label must be disambiguated
        # or the mapping merges them into one position and the panel collapses
        # (measured 2026-10-12: IEI's 84 positions read as 2). Unique labels keep
        # the vendor top-holdings path byte-identical.
        if label in holding_weights:
            label = f"{label} [{index + 1}]"
        holding_weights[label] = holding.weight
    concentration = portfolio_concentration(holding_weights)

    if data.portfolio_holdings:
        portfolio_source: str | None = data.portfolio_source or _SEC_PORTFOLIO_SOURCE
        portfolio_as_of = data.portfolio_as_of
        portfolio_holding_count: int | None = len(data.portfolio_holdings)
    else:
        portfolio_source = data.provenance.provider or None
        portfolio_as_of = data.as_of.date() if data.as_of is not None else None
        portfolio_holding_count = len(data.top_holdings) or None

    premium = premium_discount(data.nav_per_share, data.market_price)

    warnings: list[str] = []
    if not data.nav_closes:
        warnings.append(
            "No NAV/price series was available — the 1y/3y/5y CAGRs, volatility, max drawdown "
            "and Sharpe could not be computed."
        )
    else:
        observed_span = (
            (data.nav_dates[-1] - data.nav_dates[0]).days / DAYS_PER_YEAR
            if len(data.nav_dates) >= 2
            else None
        )
        unavailable = [
            label
            for label, key in (("1y", "cagr_1y"), ("3y", "cagr_3y"), ("5y", "cagr_5y"))
            if stats[key] is None
        ]
        if unavailable:
            span_text = (
                f"~{observed_span:.1f} years" if observed_span is not None else "an unknown span"
            )
            warnings.append(
                f"NAV/price series spans {span_text} ({len(data.nav_closes)} points) — too short "
                f"for the {', '.join(unavailable)} CAGR window(s); those are not reported."
            )
    if data.nav_per_share is None:
        warnings.append(
            "NAV per share unavailable — premium/discount to NAV could not be computed."
        )
    if data.category_avg_expense_ratio is None:
        warnings.append(
            "Category-average expense ratio unavailable — the fund's fee is not compared "
            "against its peer group."
        )

    return FundAssessment(
        ticker=data.ticker,
        risk_free_rate=risk_free_rate,
        returns=returns,
        volatility=stats["volatility"],
        max_drawdown=stats["max_drawdown"],
        sharpe=stats["sharpe"],
        premium_discount=premium,
        cost_drag=cost_drag,
        concentration=concentration,
        portfolio_source=portfolio_source,
        portfolio_as_of=portfolio_as_of,
        portfolio_holding_count=portfolio_holding_count,
        duration_sensitivity=duration_rate_sensitivity(data.bond_duration, data.nav_per_share),
        warnings=warnings,
    )
