"""Tiingo provider for the Data Layer v3.

Fetches end-of-day price history and reported financial statements from the
Tiingo API (https://api.tiingo.com). Requires an API key (env
``TIINGO_API_KEY``) sent in the ``Authorization: Token <key>`` header; get one
at https://www.tiingo.com/.

Serves the ``core_stock_apis`` and ``fundamental_data`` categories
(see ``docs/DATA_PROVIDERS_V3_DESIGN.md`` §5.2).

Authentication note: Tiingo's header value is ``Token <key>`` — the scheme
prefix is added by ``TiingoProvider._get``. ``ENDPOINTS`` carries the header
NAME in ``auth_header`` (the ``EndpointSpec`` value placeholder is ``$KEY``), so
the probe must prepend the ``Token `` scheme for Tiingo.
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from finrobot.engine.data.catalog import EndpointSpec
from finrobot.engine.data.categories import Category
from finrobot.engine.data.interface import (
    DataProvider,
    DataResult,
    ProviderError,
    ProviderPlanError,
    RateLimitedProviderError,
)
from finrobot.engine.data.types import DataType

_BASE_URL = "https://api.tiingo.com"
_TIMEOUT = 15.0
# Tiingo limits by hourly/daily/monthly budgets, not per-second — a light gate
# only prevents a concurrent burst from hammering the shared client.
_MIN_INTERVAL = 0.05
_PRICE_HISTORY_DAYS = 372
_QUOTE_WINDOW_DAYS = 10
# Bound the statements response to a reasonable window; the latest annual (or
# most recent period) still lands inside it.
_STATEMENTS_LOOKBACK_DAYS = 365 * 8

# Body substrings that mark an HTTP 403 as a plan/entitlement gate (valid key,
# subscription does not include the endpoint). Key-free; the URL is never read.
_PLAN_GATE_MARKERS = ("subscription", "upgrade", "not authorized", "does not include")

_CATEGORIES: list[str | DataType | Category] = [
    Category.CORE_STOCK_APIS,
    Category.FUNDAMENTAL_DATA,
]

_SUPPORTED_TYPES: tuple[DataType, ...] = (
    DataType.PRICE,
    DataType.QUOTE,
    DataType.FINANCIALS,
)

#: Canonical FINANCIALS field → Tiingo statement ``dataCode`` (from Tiingo's
#: /fundamentals/definitions). Only codes with a genuine 1:1 meaning are mapped;
#: a field absent from the payload is omitted, never defaulted.
_CANONICAL_FROM_TIINGO: dict[str, str] = {
    "revenue": "revenue",
    "operating_income": "opinc",
    "ebitda": "ebitda",
    "net_income": "netinc",
    "income_tax_expense": "taxExp",
    "interest_expense": "intexp",
    "depreciation_amortization": "depamor",
    "rd_expense": "rnd",
    "sga_expense": "sga",
    "total_debt": "debt",
    "total_cash": "cashAndEq",
    # NOTE: no NCI / preferred mapping. Tiingo's only NCI-shaped data code is
    # ``nonControllingInterests``, and /fundamentals/definitions declares it an
    # incomeStatement code — "the portion of income attributable to non-controlling
    # interest shareholders, subtracted from consolidated net income". That is the
    # period's FLOW to NCI, while ``noncontrolling_interest`` is the balance-sheet
    # CARRYING AMOUNT of their equity claim that calculate_ev folds into EV (stock,
    # not flow; verified against the 85-code definitions list, which carries no
    # balanceSheet NCI code at all). Wiring them together put an arbitrary fraction
    # of one year's earnings into EV as if it were an equity claim. The field stays
    # absent (None) so ev_bridge reports the EV as unverifiable instead.
    "operating_cash_flow": "ncfo",
    "capital_expenditure": "capex",
    "book_value_per_share": "bvps",
    "return_on_equity": "roe",
    "gross_margin": "grossMargin",
    "shares_outstanding": "sharesBasic",
    "trailing_eps": "epsDil",
}

#: The four sections Tiingo nests under ``statementData``; together they form a
#: flat ``{dataCode: value}`` map (codes are globally unique across sections).
_STATEMENT_SECTIONS: tuple[str, ...] = (
    "incomeStatement",
    "balanceSheet",
    "cashFlow",
    "overview",
)

#: Endpoint catalog rows for the v3 probe. Auth is header-based; see the module
#: docstring for the ``Token `` scheme note.
ENDPOINTS: dict[Category, EndpointSpec] = {
    Category.CORE_STOCK_APIS: EndpointSpec(
        Category.CORE_STOCK_APIS,
        "GET",
        "https://api.tiingo.com/tiingo/daily/{ticker}/prices",
        {"format": "json", "resampleFreq": "daily"},
        auth_header="Authorization",
        auth_value="Token $KEY",
    ),
    Category.FUNDAMENTAL_DATA: EndpointSpec(
        Category.FUNDAMENTAL_DATA,
        "GET",
        "https://api.tiingo.com/tiingo/fundamentals/{ticker}/statements",
        {"format": "json"},
        auth_header="Authorization",
        auth_value="Token $KEY",
    ),
}


def _num(value: Any) -> float | None:
    """Scalar → float, else None. Missing data stays missing (never a fake 0)."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _bar(row: dict[str, Any]) -> dict[str, Any] | None:
    """One canonical PRICE bar, whole-bar adjusted where Tiingo provides it.

    Tiingo returns raw (*open/close/…*) and adjusted (*adjOpen/adjClose/…*)
    fields side by side. We prefer the adjusted set for every field so a bar is
    internally consistent across splits (matching yfinance/FMP's adjusted
    history); the raw field is the fallback when an adjusted one is absent.
    """
    date = row.get("date")
    close = row.get("adjClose")
    if close is None:
        close = row.get("close")
    if not date or close is None:
        return None

    def pick(adjusted: str, raw: str) -> Any:
        value = row.get(adjusted)
        return value if value is not None else row.get(raw)

    return {
        "date": str(date)[:10],
        "open": pick("adjOpen", "open"),
        "high": pick("adjHigh", "high"),
        "low": pick("adjLow", "low"),
        "close": close,
        "volume": pick("adjVolume", "volume"),
    }


def _index_statement_codes(payload: dict[str, Any]) -> dict[str, Any]:
    """Flatten a statement period's four sections into one ``{dataCode: value}`` map."""
    data = payload.get("statementData")
    if not isinstance(data, dict):
        return {}
    indexed: dict[str, Any] = {}
    for section in _STATEMENT_SECTIONS:
        for item in data.get(section) or []:
            if isinstance(item, dict) and item.get("dataCode") is not None:
                indexed[item["dataCode"]] = item.get("value")
    return indexed


class TiingoProvider(DataProvider):
    """DataProvider backed by the Tiingo API (https://api.tiingo.com).

    Provides end-of-day price history + a lightweight quote and reported
    financial statements. API key required — get one at
    https://www.tiingo.com/.
    """

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._lock = asyncio.Lock()
        self._last_call: float = 0.0
        # Reuse one AsyncClient across the session to amortise TLS handshakes.
        self._client = httpx.AsyncClient(timeout=_TIMEOUT)

    @property
    def name(self) -> str:
        return "tiingo"

    def capabilities(self) -> list[str | DataType | Category]:
        return list(_CATEGORIES)

    async def fetch(self, ticker: str, data_type: str | DataType, **kwargs: Any) -> DataResult:
        if data_type not in _SUPPORTED_TYPES:
            raise ProviderError(
                f"data_type '{data_type}' is not supported by Tiingo. "
                f"Supported: {[str(t) for t in _SUPPORTED_TYPES]}"
            )
        try:
            if data_type == DataType.PRICE:
                return await self._fetch_price(ticker, quote_only=False)
            if data_type == DataType.QUOTE:
                return await self._fetch_price(ticker, quote_only=True)
            if data_type == DataType.FINANCIALS:
                return await self._fetch_statements(ticker)
            raise ProviderError(f"Unhandled data_type: {data_type}")
        except httpx.TimeoutException as e:
            raise ProviderError(f"Tiingo timeout for '{ticker}'") from e
        except httpx.HTTPStatusError as e:
            # 429/403-plan are typed in ``_get`` before raise_for_status. Never
            # interpolate the raw exception: its str() embeds the request URL.
            raise ProviderError(
                f"Tiingo API error for '{ticker}' (HTTP {e.response.status_code})"
            ) from e
        except (
            httpx.ConnectError,
            httpx.RemoteProtocolError,
            httpx.ReadError,
            httpx.WriteError,
        ) as e:
            raise ProviderError(f"Tiingo network error for '{ticker}' ({type(e).__name__})") from e
        except ProviderError:
            raise
        except (ValueError, KeyError, TypeError, AttributeError) as e:
            raise ProviderError(f"Tiingo fetch failed for '{ticker}' ({type(e).__name__})") from e

    async def _fetch_price(self, ticker: str, *, quote_only: bool) -> DataResult:
        """Trailing OHLC history (PRICE) or the latest close (QUOTE).

        Both read ``/tiingo/daily/{ticker}/prices``; ``quote_only`` shortens the
        window. Emits the canonical PRICE shape (``current_price`` +
        oldest-first ``price_history`` + ``exchange``).
        """
        today = datetime.now(tz=timezone.utc).date()
        window = _QUOTE_WINDOW_DAYS if quote_only else _PRICE_HISTORY_DAYS
        start = today - timedelta(days=window)
        resp = await self._get(
            f"/tiingo/daily/{ticker}/prices",
            params={
                "format": "json",
                "resampleFreq": "daily",
                "startDate": start.isoformat(),
                "endDate": today.isoformat(),
            },
        )
        raw = resp.json()
        rows = raw if isinstance(raw, list) else []
        bars = [bar for bar in (_bar(r) for r in rows if isinstance(r, dict)) if bar is not None]
        bars.sort(key=lambda b: b["date"])
        if not bars:
            raise ProviderError(
                f"Tiingo /prices returned no rows for '{ticker}' (delisted or unknown)"
            )
        current_price = _num(bars[-1]["close"])
        if current_price is None or current_price <= 0:
            raise ProviderError(f"Tiingo /prices returned no usable price for '{ticker}'")

        timestamp = datetime.now(tz=timezone.utc)
        if quote_only:
            return DataResult(
                data={"price": current_price, "quote_currency": None},
                provider=self.name,
                ticker=ticker,
                data_type=DataType.QUOTE,
                timestamp=timestamp,
            )
        return DataResult(
            data={
                "current_price": current_price,
                "price_history": bars,
                "exchange": None,
                "quote_currency": None,
            },
            provider=self.name,
            ticker=ticker,
            data_type=DataType.PRICE,
            timestamp=timestamp,
        )

    async def _fetch_statements(self, ticker: str) -> DataResult:
        """Reported financial statements → canonical FINANCIALS keys.

        Prefers the most recent ANNUAL period (``quarter == 0``) because annual
        figures are the closest honest analogue of the TTM basis the canonical
        contract assumes; when no annual row is present the latest period is
        used and tagged ``quarterly``. Fields absent from the payload are
        omitted — no fabricated defaults.
        """
        today = datetime.now(tz=timezone.utc).date()
        start = today - timedelta(days=_STATEMENTS_LOOKBACK_DAYS)
        resp = await self._get(
            f"/tiingo/fundamentals/{ticker}/statements",
            params={"format": "json", "startDate": start.isoformat()},
        )
        raw = resp.json()
        periods = [p for p in (raw if isinstance(raw, list) else []) if isinstance(p, dict)]
        if not periods:
            raise ProviderError(f"Tiingo /statements returned no rows for '{ticker}'")

        periods.sort(key=lambda p: str(p.get("date") or ""))
        annual = [p for p in periods if p.get("quarter") == 0]
        period = annual[-1] if annual else periods[-1]
        is_annual = period.get("quarter") == 0

        indexed = _index_statement_codes(period)
        period_date = str(period.get("date") or "")[:10]
        data: dict[str, Any] = {
            # ``fiscal_year`` is the fiscal period-end date string (FMP precedent
            # in normalize_financials reads it as the period end).
            "fiscal_year": period_date,
            "date": period_date,
            "period_basis": "annual" if is_annual else "quarterly",
        }
        for canonical, code in _CANONICAL_FROM_TIINGO.items():
            value = _num(indexed.get(code))
            if value is not None:
                data[canonical] = value

        revenue = data.get("revenue")
        operating_income = data.get("operating_income")
        if (
            isinstance(revenue, int | float)
            and revenue
            and isinstance(operating_income, int | float)
        ):
            data["operating_margin"] = operating_income / revenue

        return DataResult(
            data=data,
            provider=self.name,
            ticker=ticker,
            data_type=DataType.FINANCIALS,
            timestamp=datetime.now(tz=timezone.utc),
        )

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> httpx.Response:
        """Authenticated, paced GET against the Tiingo API.

        The credential rides the ``Authorization: Token <key>`` header so it
        never appears in the URL. Typed 429/plan-gate errors are raised before
        ``raise_for_status`` with key-free messages.
        """
        async with self._lock:
            elapsed = time.monotonic() - self._last_call
            if elapsed < _MIN_INTERVAL:
                await asyncio.sleep(_MIN_INTERVAL - elapsed)
            self._last_call = time.monotonic()
        headers = {
            "Authorization": f"Token {self._api_key}",
            "Content-Type": "application/json",
        }
        resp = await self._client.get(f"{_BASE_URL}{path}", params=params or {}, headers=headers)
        if resp.status_code == 429:
            raise RateLimitedProviderError(f"Tiingo rate limited (HTTP 429) for {path}")
        if resp.status_code == 403:
            body = resp.text[:500].lower()
            if any(marker in body for marker in _PLAN_GATE_MARKERS):
                raise ProviderPlanError(
                    f"Tiingo plan does not include {path} (HTTP 403 plan/entitlement gate)"
                )
        resp.raise_for_status()
        return resp

    async def close(self) -> None:
        """Release the shared httpx client. Called from DataLayer.close()."""
        await self._client.aclose()
