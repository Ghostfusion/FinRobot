import asyncio
import logging
import math
import os
import tempfile
from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Any, cast

import pandas as pd
import yfinance as yf
from yfinance.exceptions import YFException, YFRateLimitError

from finrobot.engine.data.instrument import is_fund_quote_type
from finrobot.engine.data.interface import (
    DataProvider,
    DataResult,
    ProviderError,
    RateLimitedProviderError,
)
from finrobot.engine.data.types import DataType

logger = logging.getLogger(__name__)

# Reduce "Too Many Requests" errors from Yahoo Finance
try:
    # Cross-platform temp dir (Windows has no /tmp). Non-critical tz cache that
    # just trims Yahoo rate-limit hits; the guard below swallows any failure.
    yf.set_tz_cache_dir(os.path.join(tempfile.gettempdir(), "yf_cache"))
except (AttributeError, OSError, TypeError):
    pass  # non-critical, ignore if not supported by this yfinance version

_SUPPORTED = [
    DataType.FINANCIALS,
    DataType.PRICE,
    DataType.PRICE_RANGE,
    DataType.QUOTE,
    DataType.NEWS,
    # Investment-fund profile. Yahoo serves `funds_data` (NAV, expense ratio,
    # TNA, holdings, asset/sector mix, bond duration + credit quality) for
    # ~20k US funds, which is why this provider is the always-on tail of the
    # FUND_DATA chain rather than an optional extra.
    DataType.FUND_PROFILE,
]
_CALL_DELAY = 1.0  # seconds between the info fetch and subsequent calls

# ---------------------------------------------------------------------------
# yfinance row-name lookup tables for the historical (multi-year) financials.
# yfinance uses different row labels by ticker/region/version — each list is
# tried in order, first match wins. These live here (not in the compute layer)
# because they encode yfinance-specific schema variance; the compute consumer
# (historical_extractor) reads the normalized per-year dict this provider emits.
# ---------------------------------------------------------------------------
_REVENUE_NAMES = ["Total Revenue", "Revenue", "Net Revenue"]
_GROSS_PROFIT_NAMES = ["Gross Profit"]
_EBITDA_NAMES = ["EBITDA", "Normalized EBITDA"]

# Balance-sheet rows for the per-year NET DEBT the historical valuation bands need
# (EV = market cap + net debt). yfinance's `balance_sheet` carries both legs per
# fiscal year; the yearly dict read only income_stmt + cashflow, so `total_debt` /
# `total_cash` were absent and every EV-based sample was unmeasurable — measured on
# NFLX 2026-10-12, where all five years had net_debt None and the EV/EBITDA band plus
# BOTH Football-Field reverse multiples were withheld even though the multiples'
# numerator was one DataFrame away. Complete-debt rows ONLY: falling back to a
# long-term-debt leg would understate debt and skew the multiple LOW for a levered
# issuer, which is worse than an absent band.
_TOTAL_DEBT_NAMES = ["Total Debt", "Total Debt And Capital Lease Obligation"]
_CASH_NAMES = ["Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments"]
_OPERATING_INCOME_NAMES = ["Operating Income", "Total Operating Profit Loss"]
_NET_INCOME_NAMES = [
    "Net Income",
    "Net Income Common Stockholders",
    "Net Income From Continuing And Discontinued Operation",
]
_EPS_NAMES = ["Basic EPS", "Diluted EPS", "EPS"]
_SGA_NAMES = [
    "Selling General Administrative",
    "Selling General And Administration",
    "General And Administrative Expense",
]
_OPERATING_CF_NAMES = [
    "Operating Cash Flow",
    "Cash Flow From Continuing Operating Activities",
    "Net Cash Provided By Operating Activities",
]
_INVESTING_CF_NAMES = [
    "Investing Cash Flow",
    "Cash Flow From Continuing Investing Activities",
    "Net Cash Used For Investing Activities",
    "Net Cash Provided By Investing Activities",
]
_FINANCING_CF_NAMES = [
    "Financing Cash Flow",
    "Cash Flow From Continuing Financing Activities",
    "Net Cash Used Provided By Financing Activities",
    "Net Cash Provided By Financing Activities",
]
_DA_NAMES = [
    "Depreciation And Amortization",
    "Depreciation Amortization Depletion",
    "Reconciled Depreciation",
    "Depreciation",
]
_CAPEX_NAMES = [
    "Capital Expenditure",
    "Capital Expenditures",
    "Purchase Of Ppe",
    "Net Ppe Purchase And Sale",
]
_NWC_CHANGE_NAMES = [
    "Change In Working Capital",
    "Changes In Working Capital",
]
# EV-bridge balance-sheet rows (numeric-audit family 3). Preferred equity and
# noncontrolling (minority) interest are claims on the enterprise beside common
# equity, so EV includes them (compute/operators/multiples.calculate_ev). FMP
# carries both as schema fields on its balance-sheet payload; this path has to
# read them off the statement DataFrame, which Yahoo populates per issuer:
#   ``Preferred Stock``        carrying amount (live WFC 15.348B, INCY 0.0)
#   ``Preferred Stock Equity`` the same concept on some issuers/periods
#   ``Minority Interest``      the NCI carrying amount (live WFC 2.133B, KO 2.165B)
# A row that is ABSENT (or NaN) stays None, never a fabricated 0 — Yahoo omits the
# row entirely for an issuer with no such claim (MSFT has no NCI row) while
# shipping an explicit 0.0 for one whose nil balance it does carry (INCY pref).
_PREFERRED_STOCK_NAMES = ["Preferred Stock", "Preferred Stock Equity"]
_MINORITY_INTEREST_NAMES = ["Minority Interest"]


def _make_ticker(symbol: str) -> yf.Ticker:
    """Create a Ticker. Let yfinance use its internal curl_cffi session."""
    return yf.Ticker(symbol)


def _get_row(df: pd.DataFrame | None, names: Sequence[str]) -> pd.Series | None:
    """Return the first matching row from *df* by trying *names* in order.

    Returns None if *df* is empty, *names* is empty, or no name matches.
    This is the single point of yfinance row-name variance handling.
    """
    if df is None or df.empty or not names:
        return None
    for name in names:
        if name in df.index:
            return cast(pd.Series, df.loc[name])
    return None


def _safe_float(value: object) -> float | None:
    """Convert a scalar to float; return None on any error or non-finite value.

    NaN/±Inf are treated as missing (not a legitimate 0) so the downstream
    consumer can distinguish "row existed but empty" from "cell was zero".
    """
    try:
        result = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if not math.isfinite(result):
        return None
    return result


def _cell(row: pd.Series | None, col: Any) -> float | None:
    """Read one cell from a row Series, tolerating a missing row/column/NaN."""
    if row is None:
        return None
    try:
        return _safe_float(row[col])
    except (KeyError, IndexError):
        return None


def _build_yearly_financials(
    income_stmt: pd.DataFrame,
    cashflow: pd.DataFrame | None,
    balance_sheet: pd.DataFrame | None,
    max_years: int,
) -> list[dict[str, Any]]:
    """Transform yfinance income_stmt + cashflow + balance_sheet DataFrames into the
    canonical per-year normalized dict (same schema FMP emits), newest-first.

    Emits None (not 0.0) for missing cells — the historical_extractor consumer
    owns the None→0.0 fill and the revenue-NaN year filtering, so this stays a
    pure provider-shape→normalized-dict translation. CapEx is sign-flipped to a
    positive magnitude (FCF formula convention); D&A is reported positive.

    ``balance_sheet`` supplies the debt/cash legs the historical bands build EV
    from; a missing frame (or a missing row in it) leaves those keys None rather
    than inventing a debt-free year (see ``_TOTAL_DEBT_NAMES``).
    """
    cols = list(income_stmt.columns[:max_years])
    has_cf = cashflow is not None and not cashflow.empty
    has_bs = balance_sheet is not None and not balance_sheet.empty

    rev_row = _get_row(income_stmt, _REVENUE_NAMES)
    gp_row = _get_row(income_stmt, _GROSS_PROFIT_NAMES)
    ebitda_row = _get_row(income_stmt, _EBITDA_NAMES)
    oi_row = _get_row(income_stmt, _OPERATING_INCOME_NAMES)
    ni_row = _get_row(income_stmt, _NET_INCOME_NAMES)
    eps_row = _get_row(income_stmt, _EPS_NAMES)
    sga_row = _get_row(income_stmt, _SGA_NAMES)

    ocf_row = _get_row(cashflow, _OPERATING_CF_NAMES) if has_cf else None
    icf_row = _get_row(cashflow, _INVESTING_CF_NAMES) if has_cf else None
    fcf_row = _get_row(cashflow, _FINANCING_CF_NAMES) if has_cf else None
    da_row = _get_row(cashflow, _DA_NAMES) if has_cf else None
    capex_row = _get_row(cashflow, _CAPEX_NAMES) if has_cf else None
    nwc_row = _get_row(cashflow, _NWC_CHANGE_NAMES) if has_cf else None

    debt_row = _get_row(balance_sheet, _TOTAL_DEBT_NAMES) if has_bs else None
    cash_row = _get_row(balance_sheet, _CASH_NAMES) if has_bs else None

    yearly: list[dict[str, Any]] = []
    for col in cols:
        rev = _cell(rev_row, col)
        gp = _cell(gp_row, col)
        oi = _cell(oi_row, col)
        capex_raw = _cell(capex_row, col)
        yearly.append(
            {
                "fiscal_year": str(col.date()) if hasattr(col, "date") else str(col),
                "revenue": rev,
                "gross_profit": gp,
                "operating_income": oi,
                "ebitda": _cell(ebitda_row, col),
                "net_income": _cell(ni_row, col),
                "eps": _cell(eps_row, col),
                "sga_expense": _cell(sga_row, col),
                "gross_margin": gp / rev if (gp is not None and rev) else None,
                "operating_margin": oi / rev if (oi is not None and rev) else None,
                "operating_cash_flow": _cell(ocf_row, col),
                "investing_cash_flow": _cell(icf_row, col),
                "financing_cash_flow": _cell(fcf_row, col),
                "depreciation_amortization": _cell(da_row, col),
                "capital_expenditure": abs(capex_raw) if capex_raw is not None else None,
                "change_in_working_capital": _cell(nwc_row, col),
                # Net debt legs (the historical band's EV numerator). None when the
                # balance sheet is absent or the row is missing — a fabricated 0
                # here reads as a debt-free year and skews the multiple low.
                "total_debt": _cell(debt_row, col),
                "total_cash": _cell(cash_row, col),
            }
        )
    return yearly


# ---------------------------------------------------------------------------
# Fund-profile reading (DataType.FUND_PROFILE).
#
# Yahoo mixes PERCENT and FRACTION in one payload, so every field is converted
# here to the canonical contract's single convention (a FRACTION = 0.0015 for
# 15 bp) using OBSERVED values as the unit evidence — probed live 2026-10-12 on
# IEI (bond ETF) and VTSAX (mutual fund), cross-checked against each fund's
# published expense ratio / yield:
#
#   info.netExpenseRatio            0.15   = 0.15%    PERCENT  → ÷100
#   info.annualReportExpenseRatio   0.0004 = 0.04%    fraction → as-is
#   info.yield                      0.0382 = 3.82%    fraction → as-is
#   info.ytdReturn                 -2.55   = -2.55%   PERCENT  → ÷100
#   info.trailingThreeMonthReturns -2.48   = -2.48%   PERCENT  → ÷100
#   info.threeYearAverageReturn     0.0352 = 3.52%    fraction → as-is
#   info.annualHoldingsTurnover     0.03   = 3%       fraction → as-is
#   funds_data.top_holdings[NVDA]   0.0687 = 6.87%    fraction → as-is
#
# The expense ratio PREFERS funds_data.fund_operations ("Annual Report Expense
# Ratio": 0.0015 for IEI, 0.0004 for VTSAX = the as-filed figures) over
# info.netExpenseRatio, because that frame is already a fraction and matches the
# fund's own report; its neighbouring "Category Average" column is the peer cost
# yardstick the pipeline compares against.
# ---------------------------------------------------------------------------
_ASSET_CLASS_KEYS: dict[str, str] = {
    "cashPosition": "cash",
    "stockPosition": "stock",
    "bondPosition": "bond",
    "preferredPosition": "preferred",
    "convertiblePosition": "convertible",
    "otherPosition": "other",
}
_TOP_HOLDINGS_NAME = "Name"
_TOP_HOLDINGS_WEIGHT = "Holding Percent"


def _finite(value: Any) -> float | None:
    """Finite float, or None. A ``NaN`` / ``<NA>`` cell must never become a number."""
    if isinstance(value, bool) or value is None:
        return None
    try:
        num = float(value)
    except (TypeError, ValueError):
        return None
    return num if math.isfinite(num) else None


def _pct(value: Any) -> float | None:
    """Vendor PERCENT scalar → fraction (absent stays absent, never a fake 0)."""
    num = _finite(value)
    return None if num is None else num / 100.0


def _safe_fund_attr(funds: Any, attr: str) -> Any:
    """Read a ``funds_data`` attribute, or None.

    ``FundsData`` raises ``YFDataException`` ("No Fund data found") LAZILY, per
    attribute — the object itself constructs fine for an equity (verified on
    AAPL), so every read must be guarded rather than the construction.
    """
    if funds is None:
        return None
    try:
        return getattr(funds, attr, None)
    except (YFException, ValueError, KeyError, TypeError, AttributeError, OSError, RuntimeError):
        return None


def _fund_cell(frame: Any, label: str, column: int = 0) -> float | None:
    """One labelled cell of a Yahoo fund frame, or None.

    These frames put the row label in the index and the FUND's own column FIRST
    (``Duration / 3.54 / <NA>``: column 0 = the fund, column 1 = category
    average), so ``column`` defaults to the fund's.
    """
    if not isinstance(frame, pd.DataFrame) or frame.empty:
        return None
    try:
        if label not in frame.index:
            return None
        row = frame.loc[label]
        return _finite(row.iloc[column]) if hasattr(row, "iloc") else _finite(row)
    except (KeyError, IndexError, TypeError, ValueError):
        return None


def _fund_asset_classes(raw: Any) -> dict[str, float]:
    """Yahoo's camelCase asset mix → the contract's labels (fractions as reported).

    IEI: ``{cash: 0.0085, bond: 0.9915}`` — a full breakdown. A missing class is
    OMITTED rather than zero-filled, so "unreported" never reads as "no
    exposure".
    """
    if not isinstance(raw, dict):
        return {}
    out: dict[str, float] = {}
    for vendor_key, contract_key in _ASSET_CLASS_KEYS.items():
        value = _finite(raw.get(vendor_key))
        if value is not None:
            out[contract_key] = value
    return out


def _fund_numeric_map(raw: Any) -> dict[str, float]:
    """``{label: finite float}`` from a vendor mapping (sector weights / ratings)."""
    if not isinstance(raw, dict):
        return {}
    out: dict[str, float] = {}
    for key, value in raw.items():
        num = _finite(value)
        label = str(key).strip()
        if num is not None and label:
            out[label] = num
    return out


def _fund_holdings(frame: Any) -> list[dict[str, Any]]:
    """Top-holdings frame (index = symbol) → ``[{"symbol","name","weight"}]``.

    Weights are passed through exactly as Yahoo reports them (VTSAX NVDA 0.0687 =
    6.87%) — no rescaling, so a mis-unit cannot masquerade as a portfolio weight.
    A position with no weight carries no portfolio information and is dropped.
    """
    if not isinstance(frame, pd.DataFrame) or frame.empty:
        return []
    out: list[dict[str, Any]] = []
    for symbol, row in frame.iterrows():
        weight = _finite(row.get(_TOP_HOLDINGS_WEIGHT))
        if weight is None or weight < 0:
            continue
        name = row.get(_TOP_HOLDINGS_NAME)
        label = str(symbol).strip() if symbol is not None else ""
        out.append(
            {
                "symbol": label or None,
                "name": str(name).strip() if isinstance(name, str) and name.strip() else None,
                "weight": weight,
            }
        )
    return out


def _fund_equity_pe(frame: Any) -> tuple[float | None, str | None]:
    """A P/E (or None) from Yahoo's fund "Price/Earnings" row, plus a note.

    That row is an EARNINGS YIELD, not a P/E: probed 2026-10-12, VTSAX reports
    0.04118 while the same ticker's ``info.trailingPE`` is 24.51 —
    ``1/0.04118 = 24.28``, i.e. the frame carries E/P. Publishing it as a P/E
    would understate the multiple ~600×, so it is inverted (and the inversion is
    stated in a warning) or dropped when it cannot be an earnings yield.
    """
    earnings_yield = _fund_cell(frame, "Price/Earnings")
    if earnings_yield is None or not 0 < earnings_yield < 1:
        return None, None
    return (
        1.0 / earnings_yield,
        "Yahoo's fund-level Price/Earnings row is an earnings yield (E/P), not a "
        f"P/E; inverted to {1.0 / earnings_yield:.2f}× (1/x).",
    )


class YFinanceProvider(DataProvider):
    """DataProvider backed by yfinance. Free, no API key required."""

    @property
    def name(self) -> str:
        return "yfinance"

    def capabilities(self) -> list[str | DataType]:
        return list(_SUPPORTED)

    @property
    def financials_fields(self) -> set[str]:
        return {
            "revenue",
            "ebitda",
            "net_income",
            "market_cap",
            "shares_outstanding",
            "gross_margin",
            "operating_margin",
            "pe_ratio",
            "total_debt",
            "total_cash",
        }

    async def fetch(self, ticker: str, data_type: str | DataType, **kwargs: Any) -> DataResult:
        if data_type == DataType.FILINGS:
            raise ProviderError(
                f"data_type '{DataType.FILINGS}' is not supported by yfinance. "
                "SEC EDGAR provider will be added in P2b."
            )
        if data_type not in _SUPPORTED:
            raise ProviderError(
                f"data_type '{data_type}' is not supported by yfinance. Supported: {_SUPPORTED}"
            )

        # QUOTE is the lightweight current-price path: fast_info.last_price only,
        # NO heavy .info round-trip. Handled before the validation block below so
        # high-fan-out dashboard quotes stay cheap (the whole point of QUOTE vs PRICE).
        if data_type == DataType.QUOTE:
            return await self._fetch_quote(ticker)

        # PRICE_RANGE is OHLCV-only — no current-price/marketCap needed, so skip
        # the heavy .info round-trip like QUOTE does.
        if data_type == DataType.PRICE_RANGE:
            return await self._fetch_price_range(
                ticker,
                start=kwargs["start"],
                end=kwargs["end"],
                interval=kwargs.get("interval", "1d"),
            )

        # Fetch and validate ticker info. info is passed to sub-methods
        # to avoid a redundant second HTTP call. We use explicit
        # if-raise instead of `assert` because Tauri builds may run
        # Python under -O, which strips `assert` and would let a None
        # leak into _fetch_* and surface as a generic AttributeError.
        #
        # No in-provider retry/backoff: the DataLayer already iterates
        # providers in priority order (FMP → Finnhub → yfinance → ...)
        # on ProviderError, so retrying inside yfinance both blocked
        # fallback for ~17s per call (3 × [2,5,10] sleep) and double-
        # counted toward Yahoo's rate-limit budget. Surfacing the 429
        # immediately lets the layer hop to the next provider in <1s.
        info: dict[str, Any] | None = None
        t: yf.Ticker | None = None
        try:
            t = await asyncio.to_thread(_make_ticker, ticker)
            if t is None:
                raise ProviderError(f"yfinance returned no Ticker object for '{ticker}'")
            _t: yf.Ticker = t  # capture for lambda — avoids mypy union-attr on closure
            info = await asyncio.to_thread(lambda: _t.info)
            if not info or (
                info.get("regularMarketPrice") is None
                and info.get("currentPrice") is None
                and info.get("marketCap") is None
            ):
                # All three price/cap anchors are absent → dead page (delisted /
                # OTC residual), regardless of how many other keys Yahoo still
                # returns. The old ``len(info) <= 1`` sub-gate let key-rich but
                # priceless pages through, and their payload fabricated a $0
                # quote downstream (normalize_price now also refuses — this is
                # the entry-side twin of that canonical关卡).
                raise ProviderError(f"Ticker '{ticker}' not found or returned no data")
        except ProviderError:
            raise
        # Yahoo 429 arrives as the TYPED YFRateLimitError (yfinance ≥0.2.x);
        # map it to RateLimitedProviderError BEFORE the generic YFException arm
        # so callers classify it structurally (message wording is the fallback).
        except YFRateLimitError as e:
            raise RateLimitedProviderError(f"Failed to fetch ticker '{ticker}': {e}") from e
        except (
            ValueError,
            KeyError,
            TypeError,
            AttributeError,
            RuntimeError,
            OSError,
            YFException,
        ) as e:
            raise ProviderError(f"Failed to fetch ticker '{ticker}': {e}") from e

        if t is None or info is None:
            raise ProviderError(
                f"yfinance fetch exited without populating ticker/info for '{ticker}'"
            )

        if data_type == DataType.FINANCIALS:
            years_kwarg = kwargs.get("years")
            if years_kwarg and years_kwarg > 1:
                result = await self._fetch_historical_financials(ticker, info, t, years_kwarg)
            else:
                result = self._fetch_financials(
                    ticker, info, await self._ev_bridge_claims(ticker, t)
                )
        elif data_type == DataType.PRICE:
            await asyncio.sleep(_CALL_DELAY)
            result = await self._fetch_price(ticker, t, info)
        elif data_type == DataType.NEWS:
            await asyncio.sleep(_CALL_DELAY)
            result = await self._fetch_news(ticker, t)
        elif data_type == DataType.FUND_PROFILE:
            await asyncio.sleep(_CALL_DELAY)
            result = await self._fetch_fund_profile(ticker, info, t)
        else:
            raise ProviderError(
                f"data_type '{data_type}' is in _SUPPORTED but no fetch branch handles it. "
                "Add an elif above this guard when extending _SUPPORTED."
            )

        return result

    async def _fetch_fund_profile(
        self, ticker: str, info: dict[str, Any], t: yf.Ticker
    ) -> DataResult:
        """Fund profile + portfolio composition (ETF / mutual fund / CEF).

        A fund's ``info`` payload carries the profile fields and
        ``Ticker.funds_data`` carries the portfolio (asset classes, sector
        weights, top holdings, bond duration/credit quality, the as-filed expense
        ratio and its category average). Both come off the SAME Ticker object the
        caller already fetched ``info`` from.

        Raises ``ProviderError`` for a positively non-fund symbol: a fund profile
        requested for an operating company is a caller error, not a data gap, and
        must fall through the chain rather than return a hollow "fund".
        """
        quote_type = info.get("quoteType")
        if not is_fund_quote_type(quote_type):
            raise ProviderError(
                f"'{ticker}' is not an investment fund (quoteType={quote_type!r}); "
                "FUND_PROFILE describes ETFs / mutual funds / closed-end funds."
            )

        warnings: list[str] = []
        try:
            funds: Any = await asyncio.to_thread(lambda: t.funds_data)
        except (
            YFException,
            ValueError,
            KeyError,
            TypeError,
            AttributeError,
            OSError,
            RuntimeError,
        ) as exc:
            # A priced fund with no funds_data page still has a usable profile
            # from `info` alone — degrade with a warning, never fail the fetch.
            funds = None
            warnings.append(
                f"Yahoo's fund detail page is unavailable ({type(exc).__name__}: {exc}); "
                "the profile carries quote-level fields only (no holdings/allocation)."
            )

        overview = _safe_fund_attr(funds, "fund_overview")
        overview = overview if isinstance(overview, dict) else {}
        operations = _safe_fund_attr(funds, "fund_operations")
        equity_pe, pe_note = _fund_equity_pe(_safe_fund_attr(funds, "equity_holdings"))
        if pe_note:
            warnings.append(pe_note)

        # As-filed expense ratio (fraction) first, the quoted percent as fallback.
        reported_expense = _fund_cell(operations, "Annual Report Expense Ratio")
        net_expense = (
            reported_expense if reported_expense is not None else _pct(info.get("netExpenseRatio"))
        )
        reported_turnover = _fund_cell(operations, "Annual Holdings Turnover")
        turnover = (
            reported_turnover
            if reported_turnover is not None
            else _finite(info.get("annualHoldingsTurnover"))
        )

        data: dict[str, Any] = {
            "quote_type": quote_type,
            "name": info.get("longName") or info.get("shortName"),
            "fund_family": overview.get("family") or info.get("fundFamily"),
            "legal_type": overview.get("legalType") or info.get("legalType"),
            # `info.category` is absent for several mutual funds (VTSAX) while
            # fund_overview.categoryName carries "Large Blend" — prefer the page.
            "category": overview.get("categoryName") or info.get("category"),
            "inception_date": info.get("fundInceptionDate"),
            "currency": info.get("currency") or "USD",
            "total_net_assets": _finite(info.get("totalAssets")),
            "nav_per_share": _finite(info.get("navPrice")),
            # Mutual funds have no separate NAV quote (VTSAX navPrice is None);
            # the traded/closing price is then the only market price available.
            "market_price": _finite(
                info.get("regularMarketPrice")
                or info.get("currentPrice")
                or info.get("previousClose")
            ),
            "shares_outstanding": _finite(info.get("sharesOutstanding")),
            "net_expense_ratio": net_expense,
            "gross_expense_ratio": _finite(info.get("annualReportExpenseRatio")),
            # Column 1 of fund_operations is the "Category Average" — the peer
            # yardstick for the fee (IEI 0.005287 vs its own 0.0015).
            "category_avg_expense_ratio": _fund_cell(
                operations, "Annual Report Expense Ratio", column=1
            ),
            "turnover": turnover,
            "distribution_yield": _finite(info.get("yield")),
            "ytd_return": _pct(info.get("ytdReturn")),
            "return_3m": _pct(info.get("trailingThreeMonthReturns")),
            "return_3y_annual": _finite(info.get("threeYearAverageReturn")),
            "return_5y_annual": _finite(info.get("fiveYearAverageReturn")),
            "beta_3y": _finite(info.get("beta3Year")),
            "asset_classes": _fund_asset_classes(_safe_fund_attr(funds, "asset_classes")),
            "sector_weights": _fund_numeric_map(_safe_fund_attr(funds, "sector_weightings")),
            "bond_ratings": _fund_numeric_map(_safe_fund_attr(funds, "bond_ratings")),
            "bond_duration": _fund_cell(_safe_fund_attr(funds, "bond_holdings"), "Duration"),
            "bond_maturity": _fund_cell(_safe_fund_attr(funds, "bond_holdings"), "Maturity"),
            "equity_pe": equity_pe,
            "top_holdings": _fund_holdings(_safe_fund_attr(funds, "top_holdings")),
        }

        return DataResult(
            data=data,
            provider=self.name,
            ticker=ticker,
            data_type=DataType.FUND_PROFILE,
            timestamp=datetime.now(tz=timezone.utc),
            warnings=warnings,
        )

    async def _fetch_quote(self, ticker: str) -> DataResult:
        """Lightweight current price via ``fast_info`` — no ``.info`` round-trip.

        Raises ProviderError on any failure. A Yahoo 429 arrives as the typed
        ``YFRateLimitError`` and is mapped to ``RateLimitedProviderError`` so
        ``is_rate_limit_error`` classifies it structurally; the message text is
        only the legacy fallback.
        """

        def _blocking() -> tuple[float | None, str | None]:
            t = _make_ticker(ticker)
            info = t.fast_info
            price = getattr(info, "last_price", None)
            if price is None:
                price = getattr(info, "lastPrice", None)
            # fast_info also exposes the quote currency (USD for AAPL/TSM-ADR, TWD
            # for 2330.TW) on the SAME cheap call — no .info round-trip. Carry it so
            # a foreign listing's price travels with its currency (the signal
            # consumer converts to USD instead of guessing). None when absent.
            currency = getattr(info, "currency", None)
            return (
                float(price) if price is not None else None,
                str(currency) if currency else None,
            )

        try:
            price, currency = await asyncio.to_thread(_blocking)
        except YFRateLimitError as e:
            raise RateLimitedProviderError(f"Failed to fetch quote for '{ticker}': {e}") from e
        except (
            ValueError,
            KeyError,
            TypeError,
            AttributeError,
            RuntimeError,
            OSError,
            YFException,
        ) as e:
            raise ProviderError(f"Failed to fetch quote for '{ticker}': {e}") from e
        if price is None:
            raise ProviderError(f"yfinance returned no quote for '{ticker}'")
        return DataResult(
            data={"price": price, "quote_currency": currency},
            provider=self.name,
            ticker=ticker,
            data_type=DataType.QUOTE,
            timestamp=datetime.now(tz=timezone.utc),
        )

    async def _ev_bridge_claims(self, ticker: str, t: yf.Ticker) -> dict[str, float | None]:
        """Preferred stock + NCI carrying amounts off the balance-sheet DataFrame.

        The flat ``info`` snapshot this provider otherwise serves carries neither
        field, so on a yfinance-sourced run EV silently omitted both claims and the
        ev_bridge audit could only report them unverifiable — while the statement
        module had them all along (live WFC quarterly: 15.348B preferred / 2.133B
        NCI, matching the SEC XBRL facts to the dollar). Quarterly sheet first: the
        flat snapshot's debt/cash legs are FMP's freshest quarter, so these instant
        items must be that same period's, and it is the fresher sheet (WFC's annual
        balance still carried the prior year's 16.608B).

        Best-effort by construction: these are completeness fields, so an empty or
        rate-limited statement read degrades to (None, None) — the audit then
        reports the gap honestly — rather than failing the whole FINANCIALS fetch.
        """
        both_none: dict[str, float | None] = {
            "preferred_stock": None,
            "noncontrolling_interest": None,
        }
        try:
            sheet = await asyncio.to_thread(lambda: t.quarterly_balance_sheet)
            if sheet is None or sheet.empty:
                sheet = await asyncio.to_thread(lambda: t.balance_sheet)
        except (
            YFRateLimitError,
            YFException,
            AttributeError,
            KeyError,
            TypeError,
            ValueError,
            RuntimeError,
            OSError,
        ) as e:
            logger.warning(f"EV-bridge balance-sheet rows unavailable for {ticker}: {e}")
            return both_none
        if sheet is None or sheet.empty:
            return both_none
        # Columns are newest-first (verified live: quarterly col 0 = the latest
        # reported quarter), matching every other statement read in this module.
        latest = sheet.columns[0]
        return {
            "preferred_stock": _cell(_get_row(sheet, _PREFERRED_STOCK_NAMES), latest),
            "noncontrolling_interest": _cell(_get_row(sheet, _MINORITY_INTEREST_NAMES), latest),
        }

    def _fetch_financials(
        self, ticker: str, info: dict[str, Any], claims: dict[str, float | None]
    ) -> DataResult:
        # dict.get() never raises; no try/except needed here
        data = {
            "revenue": info.get("totalRevenue"),
            "ebitda": info.get("ebitda"),
            "net_income": info.get("netIncomeToCommon"),
            "gross_margin": info.get("grossMargins"),
            "operating_margin": info.get("operatingMargins"),
            "pe_ratio": info.get("trailingPE"),
            "market_cap": info.get("marketCap"),
            "shares_outstanding": info.get("sharesOutstanding"),
            "total_debt": info.get("totalDebt"),
            "total_cash": info.get("totalCash"),
            # EV-bridge completeness (numeric-audit family 3), symmetric with
            # FMP's ``preferredStock``/``minorityInterest``. None ≠ 0: a row the
            # statement omits stays None, and ev_bridge reports the EV as
            # unverifiable rather than pretending the claim is nil.
            "preferred_stock": claims["preferred_stock"],
            "noncontrolling_interest": claims["noncontrolling_interest"],
            "company_name": info.get("shortName") or info.get("longName"),
            # TTM cash-flow actuals for a real FCF = OCF − CapEx (computed
            # downstream, never LLM-estimated). yfinance `info` exposes TTM
            # operatingCashflow + freeCashflow but no capex line, so derive
            # capex = OCF − FCF (positive magnitude) when both are present.
            "operating_cash_flow": info.get("operatingCashflow"),
            "capital_expenditure": (
                info["operatingCashflow"] - info["freeCashflow"]
                if isinstance(info.get("operatingCashflow"), int | float)
                and isinstance(info.get("freeCashflow"), int | float)
                else None
            ),
            # Industry/sector for valuation model routing (DDM vs DCF)
            "industry": info.get("industry"),
            "sector": info.get("sector"),
            # What the security actually IS (EQUITY / ETF / MUTUALFUND). Routed
            # by engine.data.instrument so a fund is sent to the fund pipeline
            # instead of dying downstream as "Missing or zero revenue".
            "quote_type": info.get("quoteType"),
            # Dividend data for DDM valuation
            "dividend_per_share": info.get("dividendRate"),
            "dividend_yield": info.get("dividendYield"),
            "payout_ratio": info.get("payoutRatio"),
            # Bank-specific metrics (available for financials)
            "book_value_per_share": info.get("bookValue"),
            "return_on_equity": info.get("returnOnEquity"),
            # v5 PR4c forward-estimate inputs — required by
            # engine/compute/operators/forward_estimates.py. yfinance only carries
            # forward EPS / PE (no consensus EBITDA / FCF), so the leaf has
            # to derive forward EBITDA/FCF from forward_revenue × TTM margin.
            "forward_eps": info.get("forwardEps"),
            "forward_pe": info.get("forwardPE"),
            "trailing_eps": info.get("trailingEps"),
            # ISO 4217 currency codes — yfinance carries two different ones
            # and they DISAGREE for foreign-listed ADRs:
            #
            #   - "currency"          → quote currency: marketCap, price,
            #                            shares × price are in this unit
            #   - "financialCurrency" → IS/BS reporting currency: revenue,
            #                            ebitda, net_income, debt, cash are
            #                            in this unit
            #
            # For TSM (ADR): currency=USD, financialCurrency=TWD — the very
            # mismatch that produces EV/EBITDA=0.158x without normalization.
            # For 2330.TW (local listing): both = TWD.
            # For most US issuers: both = USD.
            "quote_currency": info.get("currency") or "USD",
            "financial_currency": info.get("financialCurrency") or "USD",
            # Country of incorporation — used by extractor to cross-check
            # financialCurrency when the provider tag is unreliable (e.g. TSM
            # ADR where yfinance returns financialCurrency="USD" despite IS/BS
            # being reported in TWD).
            "country": info.get("country"),
            # yfinance .info carries no ADR structural flag, so is_adr stays None
            # on this path — the family-1 acceptor keeps its full review behavior
            # for yfinance snapshots (None ≠ False: "unknown", not "confirmed
            # non-ADR"). Only FMP's /profile isAdr can suppress the banner.
            "is_adr": None,
        }
        return DataResult(
            data=data,
            provider=self.name,
            ticker=ticker,
            data_type=DataType.FINANCIALS,
            timestamp=datetime.now(tz=timezone.utc),
        )

    async def _fetch_historical_financials(
        self, ticker: str, info: dict[str, Any], t: yf.Ticker, years: int
    ) -> DataResult:
        """Fetch multi-year financials from the income_stmt + cashflow DataFrames.

        Emits the canonical per-year normalized dict (the same schema FMP emits)
        so the provider-agnostic historical_extractor can build a complete
        HistoricalMetrics — including the DCF cash-flow trio (OCF/CapEx/ΔNWC),
        D&A, EPS and SGA — when yfinance is the active source. Falls back to
        single-year (_fetch_financials) if income_stmt is empty.
        """
        try:
            income_stmt = await asyncio.to_thread(lambda: t.income_stmt)
            cashflow = await asyncio.to_thread(lambda: t.cashflow)
        except (AttributeError, KeyError, ValueError, TypeError) as e:
            logger.warning(
                f"Historical data extraction failed for {ticker}, falling back to single-year: {e}"
            )
            return self._fetch_financials(ticker, info, await self._ev_bridge_claims(ticker, t))

        if income_stmt is None or income_stmt.empty:
            return self._fetch_financials(ticker, info, await self._ev_bridge_claims(ticker, t))

        # Tolerant: the balance sheet only supplies the net-debt legs, so its absence
        # must not cost the income/cashflow years (it would send a multi-year fetch
        # down the single-year fallback). Without it the EV-based bands stay withheld
        # with their own warning, exactly as before.
        try:
            balance_sheet = await asyncio.to_thread(lambda: t.balance_sheet)
        except (AttributeError, KeyError, ValueError, TypeError) as e:
            logger.info(f"yfinance balance sheet unavailable for {ticker}: {e}")
            balance_sheet = None

        yearly_data = _build_yearly_financials(income_stmt, cashflow, balance_sheet, years)

        return DataResult(
            data={"yearly_data": yearly_data},
            provider=self.name,
            ticker=ticker,
            data_type=DataType.FINANCIALS,
            timestamp=datetime.now(tz=timezone.utc),
        )

    async def _fetch_price(self, ticker: str, t: yf.Ticker, info: dict[str, Any]) -> DataResult:
        try:
            current_price = info.get("currentPrice") or info.get("regularMarketPrice")
            quote_currency = info.get("currency")
            # Exchange name for the LIVE pill (TickerHero) — NASDAQ vs NYSE
            # vs AMEX matters for retail investors who associate trust signals
            # with exchange. fullExchangeName ("NasdaqGS" etc.) gets pretty-
            # printed by the UI; raw "exchange" code is the fallback.
            exchange = (
                info.get("fullExchangeName")
                or info.get("exchange")
                or info.get("exchangeShortName")
            )
            hist = await asyncio.to_thread(t.history, period="1y")
            price_history = []
            for date, row in hist.iterrows():
                # yfinance can hand back an all-NaN OHLC row for a session
                # (observed live 2026-06-11: AAPL 2026-06-10 NaN close with a
                # real volume). A bar without a finite close is not a bar —
                # serialized it becomes close:null and crashes every chart
                # consumer (PriceTrendChart toFixed). Skip it; never fabricate.
                if _safe_float(row["Close"]) is None:
                    continue
                price_history.append(
                    {
                        "date": str(date.date()),
                        "open": row["Open"],
                        "high": row["High"],
                        "low": row["Low"],
                        "close": row["Close"],
                        "volume": row["Volume"],
                    }
                )
        except YFRateLimitError as e:
            raise RateLimitedProviderError(f"Failed to fetch price for '{ticker}': {e}") from e
        except (
            ValueError,
            KeyError,
            TypeError,
            AttributeError,
            RuntimeError,
            OSError,
            YFException,
        ) as e:
            raise ProviderError(f"Failed to fetch price for '{ticker}': {e}") from e

        return DataResult(
            data={
                "current_price": current_price,
                "price_history": price_history,
                "exchange": exchange,
                "quote_currency": quote_currency,
                # Authoritative observation instant (unix epoch seconds). Same key
                # as the FMP path (Mode A/B symmetry) so normalize_price stamps
                # Provenance.as_of from one provider-agnostic chain.
                "quote_timestamp": info.get("regularMarketTime"),
                # Per-exchange session phase straight from the feed (REGULAR / PRE
                # / PREPRE / POST / POSTPOST / CLOSED). The primary signal for
                # compute_session_state — it already splits pre/post from regular
                # per exchange, so we don't re-derive extended hours from a clock.
                # FMP's /quote has no equivalent → that path leaves this None and
                # session state falls back to the clock window (still correct).
                "market_state": info.get("marketState"),
            },
            provider=self.name,
            ticker=ticker,
            data_type=DataType.PRICE,
            timestamp=datetime.now(tz=timezone.utc),
        )

    async def _fetch_price_range(
        self, ticker: str, *, start: str, end: str, interval: str = "1d"
    ) -> DataResult:
        """Arbitrary-range split/dividend-adjusted daily OHLCV.

        Uses ``Ticker.history(start, end, auto_adjust=True)`` — the adjusted
        basis that lines up with FMP's ``adjClose`` (verified live 2026-06-02),
        so a multi-year backtest doesn't break across a split. Throttled by
        ``_CALL_DELAY`` like every other yfinance call; no in-provider retry
        (DataLayer owns fallback). ``interval`` passes through to yfinance.
        """
        await asyncio.sleep(_CALL_DELAY)
        bars: list[dict[str, Any]] = []
        try:
            t = await asyncio.to_thread(_make_ticker, ticker)
            if t is None:
                raise ProviderError(f"yfinance returned no Ticker object for '{ticker}'")
            _t: yf.Ticker = t  # capture for the closure — avoids mypy union-attr
            hist = await asyncio.to_thread(
                lambda: _t.history(start=start, end=end, interval=interval, auto_adjust=True)
            )
            # Some yfinance versions return MultiIndex columns even for a single
            # ticker; flatten to the level-0 OHLCV names.
            if hasattr(hist.columns, "levels") and len(hist.columns.levels) > 1:
                hist.columns = hist.columns.droplevel(1)
            for dt, row in hist.iterrows():
                # Same NaN-session guard as _fetch_price: a bar without a finite
                # close is not a bar, and these dicts feed PriceBar directly
                # (whose close validator now refuses non-finite — 构造期不变量).
                if _safe_float(row["Close"]) is None:
                    continue
                bars.append(
                    {
                        "date": str(dt.date()),
                        "open": float(row["Open"]),
                        "high": float(row["High"]),
                        "low": float(row["Low"]),
                        "close": float(row["Close"]),
                        "volume": float(row["Volume"]),
                    }
                )
        except ProviderError:
            raise
        except YFRateLimitError as e:
            raise RateLimitedProviderError(
                f"Failed to fetch price range for '{ticker}': {e}"
            ) from e
        except (
            ValueError,
            KeyError,
            TypeError,
            AttributeError,
            RuntimeError,
            OSError,
            YFException,
        ) as e:
            raise ProviderError(f"Failed to fetch price range for '{ticker}': {e}") from e

        if not bars:
            raise ProviderError(
                f"yfinance returned no bars for '{ticker}' between {start} and {end}"
            )
        return DataResult(
            data={
                "ticker": ticker.upper(),
                "interval": interval,
                "bars": bars,
                "adjusted": True,
                "source_provider": self.name,
            },
            provider=self.name,
            ticker=ticker,
            data_type=DataType.PRICE_RANGE,
            timestamp=datetime.now(tz=timezone.utc),
        )

    async def _fetch_news(self, ticker: str, t: yf.Ticker) -> DataResult:
        try:
            raw_news = await asyncio.to_thread(lambda: t.news or [])
            news_items = []
            for item in raw_news:
                content = item.get("content", {})
                title = content.get("title") or item.get("title", "")
                if not title:
                    continue
                news_items.append(
                    {
                        "title": title,
                        "source": (
                            content.get("provider", {}).get("displayName")
                            or item.get("publisher", "yfinance")
                        ),
                        "published": (
                            content.get("pubDate") or item.get("providerPublishTime", "")
                        ),
                        "url": (content.get("canonicalUrl", {}).get("url") or item.get("link", "")),
                    }
                )
        except YFRateLimitError as e:
            raise RateLimitedProviderError(f"Failed to fetch news for '{ticker}': {e}") from e
        except (
            ValueError,
            KeyError,
            TypeError,
            AttributeError,
            RuntimeError,
            OSError,
            YFException,
        ) as e:
            raise ProviderError(f"Failed to fetch news for '{ticker}': {e}") from e

        return DataResult(
            data={"news_items": news_items},
            provider=self.name,
            ticker=ticker,
            data_type=DataType.NEWS,
            timestamp=datetime.now(tz=timezone.utc),
        )
