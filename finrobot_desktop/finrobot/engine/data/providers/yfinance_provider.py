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
from finrobot.engine.primitives.ebitda import calculate_ebitda_operating

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
_OPERATING_INCOME_NAMES = [
    "Operating Income",
    "Total Operating Profit Loss",
    "Total Operating Income As Reported",
]
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
# Cost-of-revenue row. Emitted so the historical_extractor's gross-margin
# plausibility guard can fall back to ``revenue − cost_of_revenue`` (the
# provider's own reported cost) when the derived ``revenue − gross_profit`` is
# implausible. Yahoo normally keeps ``Gross Profit`` == ``Total Revenue`` −
# ``Cost Of Revenue``, so this is usually redundant — but when a single column's
# cost lines are crossed it is one of the two independent legs the guard needs
# (see _build_yearly_financials, EHC FY2025).
_COGS_NAMES = ["Cost Of Revenue", "Cost Of Goods Sold", "Reconciled Cost Of Revenue"]
# Parent-only shareholders' equity, the caliber FMP's ``totalStockholdersEquity``
# reports and the one ``historical_extractor`` reads as ``total_equity`` (the
# through-cycle ROE denominator). Without it the yfinance history shipped an
# all-null ``shareholders_equity`` series while the balance sheet carried the
# figure one DataFrame away. ``Total Equity Gross Minority Interest`` is
# deliberately NOT in the list: it folds NCI into equity, which would make the
# net_income/equity ROE ratio inconsistent with the parent-only numerator.
_TOTAL_EQUITY_NAMES = ["Stockholders Equity", "Common Stock Equity", "Total Stockholders Equity"]
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

# Income-statement rows the flat ``info`` snapshot omits ENTIRELY. Live probe
# 2026-10-14 (NFLX): ``info`` carries no operatingIncome / incomeTaxExpense /
# depreciation / researchDevelopment / sellingGeneralAdministrative /
# interestExpense key AT ALL, so the canonical published ``null (not provided)``
# for six standard income-statement lines while Yahoo's own ``ttm_income_stmt``
# frame — the same frame family ``_build_yearly_financials`` already reads per
# fiscal year — carried every one of them on the TTM basis the flat snapshot
# already claims. Rows are read from the TTM frames ONLY: the annual
# ``income_stmt`` never substitutes, because an annual leg inside a statement the
# canonical labels ``ttm`` is exactly the period-mixing defect the report
# contract exists to prevent. A row the issuer does not report stays None.
#
# These are not completeness cosmetics: ``compute/coordinators/extractor``
# recomputes BOTH EBITDA calibers from absolute line items and falls back to the
# provider's opaque ``ebitda`` scalar only "when components are absent (e.g.
# yfinance-sourced snapshots)" — which is what every yfinance run used to force.
_TAX_NAMES = ["Tax Provision", "Income Tax Expense", "Provision For Income Taxes"]
_RD_NAMES = ["Research And Development", "Research And Development Expense"]
_INTEREST_EXPENSE_NAMES = ["Interest Expense", "Interest Expense Non Operating"]


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


def _column_iso_date(col: Any) -> str | None:
    """A statement frame's column label (a fiscal period end) as an ISO date.

    yfinance labels columns with ``pd.Timestamp`` (newest-first); a plain string
    label is truncated to its date part. None when the label carries no date —
    never a fabricated period.
    """
    if hasattr(col, "date"):
        return str(col.date())
    text = str(col)
    return text[:10] if text[:4].isdigit() else None


def _epoch_iso_date(value: Any) -> str | None:
    """A Yahoo epoch-seconds timestamp as an ISO date; None when absent/invalid.

    ``info.mostRecentQuarter`` / ``lastFiscalYearEnd`` arrive as Unix seconds. An
    unusable value (missing, non-numeric, non-positive, out of range) stays None —
    never a fabricated period.
    """
    if isinstance(value, bool) or not isinstance(value, int | float) or value <= 0:
        return None
    try:
        return datetime.fromtimestamp(value, tz=timezone.utc).date().isoformat()
    except (OverflowError, OSError, ValueError):
        return None


def _ttm_capex(info: dict[str, Any], from_frame: float | None) -> float | None:
    """TTM CapEx as a POSITIVE magnitude — the statement frame first, else the
    ``OCF − freeCashflow`` derivation, and only while that derivation is
    self-consistent (``0 <= OCF − FCF``).

    Sign: positive magnitude is this module's one convention (the yearly builder
    emits ``abs(capex_raw)``) and it is what the consumers assume —
    ``compute/operators/multiples`` documents "``capital_expenditure`` is a
    positive magnitude" and computes ``fcf = operating_cash_flow −
    capital_expenditure``; ``dcf_seed``'s TTM ratio requires ``0 < capex/revenue``.

    Why the frame wins (live probe 2026-10-14, NFLX): ``info.freeCashflow`` was
    25,387,552,768 against an ``operatingCashflow`` of 11,970,833,408 — Yahoo's own
    flat FCF is incoherent (larger than the OCF it is supposedly net of), so
    ``OCF − FCF`` published CapEx of **-13,416,719,360**. That number then (a)
    inverted the sign convention, so ``multiples`` computed an FCF of +25.4B, and
    (b) made ``dcf_seed`` reject the TTM ratio and fall back to the historical
    median. ``ttm_cashflow`` carries ``Capital Expenditure`` -818,828,000 →
    +818.8M, and OCF − that = 11.15B, matching the frame's own ``Free Cash Flow``
    row (11,152,005,000) to 0.00%.
    """
    if from_frame is not None:
        return from_frame
    ocf = info.get("operatingCashflow")
    fcf = info.get("freeCashflow")
    if not isinstance(ocf, int | float) or not isinstance(fcf, int | float):
        return None
    derived = float(ocf) - float(fcf)
    return derived if derived >= 0 else None


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
    than inventing a debt-free year (see ``_TOTAL_DEBT_NAMES``), plus the
    parent-only equity the through-cycle ROE needs (``_TOTAL_EQUITY_NAMES``).

    Rows are read straight off Yahoo's statement frames; a value that is crossed
    or missing ON THE SOURCE (not in this mapping) is left as reported here and
    repaired by the consumer's plausibility guard — this function stays a pure
    shape translation. Live example (probe 2026-10-13): Yahoo's EHC annual frame
    carries FY2025 ``Cost Of Revenue`` 254.4M (the real SG&A magnitude) and
    ``Selling General And Administration`` 3411.1M (the real cost of revenue), so
    its own ``Gross Profit`` row reads revenue − 254.4M = 5680.8M → a 95.7%
    margin against 40-42% for FY2022-24; the same cross appears in every quarterly
    column from 2025-09-30 on. ``cost_of_revenue`` is emitted so the guard has the
    provider's own cost leg to test.
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
    cogs_row = _get_row(income_stmt, _COGS_NAMES)

    ocf_row = _get_row(cashflow, _OPERATING_CF_NAMES) if has_cf else None
    icf_row = _get_row(cashflow, _INVESTING_CF_NAMES) if has_cf else None
    fcf_row = _get_row(cashflow, _FINANCING_CF_NAMES) if has_cf else None
    da_row = _get_row(cashflow, _DA_NAMES) if has_cf else None
    capex_row = _get_row(cashflow, _CAPEX_NAMES) if has_cf else None
    nwc_row = _get_row(cashflow, _NWC_CHANGE_NAMES) if has_cf else None

    debt_row = _get_row(balance_sheet, _TOTAL_DEBT_NAMES) if has_bs else None
    cash_row = _get_row(balance_sheet, _CASH_NAMES) if has_bs else None
    equity_row = _get_row(balance_sheet, _TOTAL_EQUITY_NAMES) if has_bs else None

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
                # Provider's own cost-of-revenue leg (see _COGS_NAMES) — the
                # guard's ``revenue − cost_of_revenue`` fallback input.
                "cost_of_revenue": _cell(cogs_row, col),
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
                # Parent-only equity (see _TOTAL_EQUITY_NAMES). None when absent,
                # never a fabricated 0 — a 0 equity year would make the
                # through-cycle ROE divide by zero / read as "no book value".
                "total_equity": _cell(equity_row, col),
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
                result = await self._flat_financials(ticker, info, t)
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

    async def _ttm_snapshot_meta(
        self, ticker: str, t: yf.Ticker, info: dict[str, Any]
    ) -> dict[str, Any]:
        """Metadata the flat ``info`` snapshot lacks, read off the balance-sheet frame.

        Two families, both served by the SAME statement read:

        * **EV-bridge claims** — preferred stock + NCI carrying amounts. The flat
          ``info`` snapshot carries neither, so on a yfinance-sourced run EV
          silently omitted both claims and the ev_bridge audit could only report
          them unverifiable — while the statement module had them all along (live
          WFC quarterly: 15.348B preferred / 2.133B NCI, matching the SEC XBRL
          facts to the dollar). Quarterly sheet first: the flat snapshot's
          debt/cash legs are FMP's freshest quarter, so these instant items must be
          that same period's, and it is the fresher sheet (WFC's annual balance
          still carried the prior year's 16.608B).
        * **TTM window** — ``period_end`` (newest reported quarter end) and
          ``ttm_quarter_ends`` (the four newest). Yahoo's ``info`` exposes no
          period end, so a yfinance snapshot shipped ``fiscal_period_end=None`` /
          ``ttm_quarter_ends=[]`` and the report could not distinguish a
          TTM-based projection year from a fiscal-year one (owner review:
          "2026E" was really the twelve months ending mid-2027). ``period_end``
          prefers ``info.mostRecentQuarter`` and falls back to the quarterly
          frame's newest column; ``ttm_quarter_ends`` comes ONLY from the
          quarterly frame — an annual column date is a fiscal-year end, and
          publishing it as a TTM quarter end would make audit.ttm_period's
          non-overlap check "pass" on a window that is not one.

        Best-effort by construction: these are completeness fields, so an empty or
        rate-limited statement read degrades to all-None/[] — the audit then
        reports the gap honestly — rather than failing the whole FINANCIALS fetch.
        """
        empty: dict[str, Any] = {
            "preferred_stock": None,
            "noncontrolling_interest": None,
            "period_end": _epoch_iso_date(info.get("mostRecentQuarter")),
            "ttm_quarter_ends": [],
        }
        try:
            sheet = await asyncio.to_thread(lambda: t.quarterly_balance_sheet)
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
            logger.warning(f"Balance-sheet rows unavailable for {ticker}: {e}")
            return empty
        quarterly = sheet is not None and not sheet.empty
        if not quarterly:
            try:
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
                logger.warning(f"Balance-sheet rows unavailable for {ticker}: {e}")
                return empty
        if sheet is None or sheet.empty:
            return empty
        # Columns are newest-first (verified live: quarterly col 0 = the latest
        # reported quarter), matching every other statement read in this module.
        latest = sheet.columns[0]
        quarter_ends = [_column_iso_date(c) for c in list(sheet.columns[:4])] if quarterly else []
        return {
            "preferred_stock": _cell(_get_row(sheet, _PREFERRED_STOCK_NAMES), latest),
            "noncontrolling_interest": _cell(_get_row(sheet, _MINORITY_INTEREST_NAMES), latest),
            "period_end": empty["period_end"] or (_column_iso_date(latest) if quarterly else None),
            "ttm_quarter_ends": [d for d in quarter_ends if d is not None],
        }

    async def _ttm_statement_lines(self, ticker: str, t: yf.Ticker) -> dict[str, Any]:
        """The income/cash-flow lines the flat ``info`` snapshot cannot supply.

        Six income-statement lines off ``ttm_income_stmt`` (operating income, tax,
        D&A, R&D, SG&A, interest expense) plus TTM CapEx off ``ttm_cashflow``. TTM
        frames ONLY — see ``_TAX_NAMES`` for why the annual frames may not
        substitute. Each statement read is independently best-effort, so a
        rate-limited or missing frame leaves its fields None (the report then shows
        an honest gap) instead of failing the whole FINANCIALS fetch.
        """
        frames: dict[str, Any] = {
            "operating_income": None,
            "income_tax_expense": None,
            "depreciation_amortization": None,
            "rd_expense": None,
            "sga_expense": None,
            "interest_expense": None,
            "capital_expenditure": None,
        }
        income = await self._read_statement(ticker, t, "ttm_income_stmt")
        if income is not None and not income.empty:
            col = income.columns[0]  # newest-first, like every other read here
            frames.update(
                {
                    "operating_income": _cell(_get_row(income, _OPERATING_INCOME_NAMES), col),
                    "income_tax_expense": _cell(_get_row(income, _TAX_NAMES), col),
                    "depreciation_amortization": _cell(_get_row(income, _DA_NAMES), col),
                    "rd_expense": _cell(_get_row(income, _RD_NAMES), col),
                    "sga_expense": _cell(_get_row(income, _SGA_NAMES), col),
                    "interest_expense": _cell(_get_row(income, _INTEREST_EXPENSE_NAMES), col),
                }
            )
        cashflow = await self._read_statement(ticker, t, "ttm_cashflow")
        if cashflow is not None and not cashflow.empty:
            capex = _cell(_get_row(cashflow, _CAPEX_NAMES), cashflow.columns[0])
            frames["capital_expenditure"] = abs(capex) if capex is not None else None
        return frames

    async def _read_statement(self, ticker: str, t: yf.Ticker, attr: str) -> pd.DataFrame | None:
        """One lazily-fetched statement frame, or None when Yahoo will not serve it.

        yfinance statement properties are lazy HTTP reads, so they raise the same
        transport errors ``fetch`` already maps (rate limit, YFException, and the
        AttributeError/KeyError family a missing frame surfaces as). Completeness
        fields must not fail the FINANCIALS fetch, so every arm degrades to None
        with a log line.
        """
        try:
            frame = await asyncio.to_thread(lambda: getattr(t, attr))
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
            logger.warning(f"{attr} unavailable for {ticker}: {e}")
            return None
        if frame is None or not isinstance(frame, pd.DataFrame):
            return None
        return cast(pd.DataFrame, frame)

    async def _flat_financials(self, ticker: str, info: dict[str, Any], t: yf.Ticker) -> DataResult:
        """The flat FINANCIALS payload: ``info`` scalars + everything the statement
        frames add (EV-bridge claims, the TTM window, the six income lines, CapEx).

        One entry point so every path that lands on the flat snapshot — the direct
        FINANCIALS branch and the two multi-year fallbacks — carries the same
        fields; the alternative (each caller remembering to merge two dicts) is how
        the six lines went missing in the first place.
        """
        meta = await self._ttm_snapshot_meta(ticker, t, info)
        meta.update(await self._ttm_statement_lines(ticker, t))
        return self._fetch_financials(ticker, info, meta)

    def _fetch_financials(
        self, ticker: str, info: dict[str, Any], meta: dict[str, Any]
    ) -> DataResult:
        # EBITDA on the OPERATING caliber (EBIT + D&A) now that the statement read
        # supplies both legs — the same rule and the same fallback FMP's own
        # payloads use (fmp_provider.py:712). This field is the canonical's, and
        # the canonical is what the report's income table and the data-collection
        # prompt read; ``extractor`` independently recomputes its
        # ``ebitda_operating`` for the multiples. Serving Yahoo's opaque
        # ``info.ebitda`` scalar here let the two disagree the moment the legs
        # existed: live NFLX 2026-10-14, canonical 14,726,931,456 against a
        # projection of 32,023,120,000, so the published table read
        # "EBIT 14.355B · D&A 17.669B · EBITDA 14.727B" — an internally
        # inconsistent statement. Falls back to the scalar only when a leg is
        # missing (faithful, never fabricated).
        ebitda_operating = calculate_ebitda_operating(
            meta["operating_income"], meta["depreciation_amortization"]
        )
        # dict.get() never raises; no try/except needed here
        data = {
            "revenue": info.get("totalRevenue"),
            "ebitda": (ebitda_operating if ebitda_operating is not None else info.get("ebitda")),
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
            "preferred_stock": meta["preferred_stock"],
            "noncontrolling_interest": meta["noncontrolling_interest"],
            # TTM window (owner review: forecast-year labels were off by a base).
            # Yahoo's flat ``info`` carries no period end, so this snapshot shipped
            # ``fiscal_period_end=None`` / ``ttm_quarter_ends=[]`` and the report
            # could not tell that its DCF ``revenue_base`` is the TTM window while
            # the chart's labels came from the last FISCAL year. Read from the
            # statement frame (see _ttm_snapshot_meta); None / [] when unavailable
            # — the same honest-empty semantics the FMP path has.
            "fiscal_year": meta["period_end"],
            "ttm_quarter_ends": meta["ttm_quarter_ends"],
            "company_name": info.get("shortName") or info.get("longName"),
            # TTM cash-flow actuals for a real FCF = OCF − CapEx (computed
            # downstream, never LLM-estimated). CapEx prefers ``ttm_cashflow``'s
            # own row; the old ``OCF − info.freeCashflow`` derivation survives only
            # as the guarded fallback (see _ttm_capex — Yahoo's flat freeCashflow
            # is not always net of capex, and it published a 16x-wrong, wrong-signed
            # CapEx on NFLX).
            "operating_cash_flow": info.get("operatingCashflow"),
            "capital_expenditure": _ttm_capex(info, meta["capital_expenditure"]),
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
            # ── statement-frame completions (see _ttm_statement_lines) ──────
            # Six standard income-statement lines ``info`` does not carry on any
            # issuer. All TTM, all read off ``ttm_income_stmt``; None when Yahoo
            # omits the row.
            "operating_income": meta["operating_income"],
            "income_tax_expense": meta["income_tax_expense"],
            "depreciation_amortization": meta["depreciation_amortization"],
            "rd_expense": meta["rd_expense"],
            "sga_expense": meta["sga_expense"],
            "interest_expense": meta["interest_expense"],
            # 5y monthly beta for the WACC leg. Free in ``info`` on every issuer
            # probed, but the flat snapshot never mapped it, so the canonical's
            # ``beta`` published null on every yfinance run (live NFLX
            # 2026-10-14: info.beta = 1.613) and the valuation had to fall back to
            # whatever its no-beta default is.
            "beta": info.get("beta"),
            # This payload IS Yahoo's TTM snapshot — totalRevenue / ebitda /
            # netIncomeToCommon / operatingCashflow are all trailing-twelve-month,
            # and ``ttm_quarter_ends`` above names the window — but it never SAID
            # so, so ``normalize_financials`` treated the basis as undeclared and
            # stamped DEGRADED_PERIOD_BASIS_UNKNOWN on every yfinance run while
            # still publishing "ttm". Declaring it removes the flag without
            # changing the number.
            "period_basis": "ttm",
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
            return await self._flat_financials(ticker, info, t)

        if income_stmt is None or income_stmt.empty:
            return await self._flat_financials(ticker, info, t)

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
