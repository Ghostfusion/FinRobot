"""EODHD (EOD Historical Data) provider for the Data Layer v3.

Fetches end-of-day prices, financial news, news sentiment, dividend history and
exchange symbol lists from the EODHD API (https://eodhd.com/api). Requires an
API key (env ``EODHD_API_KEY``) passed as the ``api_token`` query parameter; get
one at https://eodhd.com/.

Serves the ``core_stock_apis``, ``news_data``, ``news_sentiment``,
``corporate_actions``, ``exchange_symbols`` and ``fund_data`` categories
(see ``docs/DATA_PROVIDERS_V3_DESIGN.md`` §5.2).

EODHD US tickers carry an exchange suffix (``AAPL.US``); the adapter passes the
caller's ticker through verbatim and never invents a suffix.
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

_BASE_URL = "https://eodhd.com/api"
_TIMEOUT = 15.0
_MIN_INTERVAL = 0.1  # EODHD paid tiers allow ~1000 req/min → pace request starts at 10/s
# Trailing calendar window for the OHLC fetch: 52 weeks + a cushion so the
# downstream 52-week high/low window (366 days) is fully covered across
# weekend/holiday gaps at the boundary (mirrors Finnhub/FMP's window).
_PRICE_HISTORY_DAYS = 372
# Short window for the lightweight QUOTE call — only the latest close is read.
_QUOTE_WINDOW_DAYS = 10
_NEWS_LIMIT = 50

# Body substrings that mark an HTTP 403 as a plan/entitlement gate (the key is
# valid, the subscription does not include the endpoint). Key-free by
# construction; the request URL (which carries ``api_token``) is never read.
_PLAN_GATE_MARKERS = ("subscription", "upgrade", "not included in your", "does not include")

_CATEGORIES: list[str | DataType | Category] = [
    Category.CORE_STOCK_APIS,
    Category.NEWS_DATA,
    Category.NEWS_SENTIMENT,
    Category.CORPORATE_ACTIONS,
    Category.EXCHANGE_SYMBOLS,
    Category.FUND_DATA,
]

_SUPPORTED_TYPES: tuple[DataType, ...] = (
    DataType.PRICE,
    DataType.QUOTE,
    DataType.NEWS,
    DataType.SENTIMENT,
    DataType.DIVIDENDS,
    DataType.FUND_PROFILE,
)

#: Endpoint catalog rows for the v3 probe (see ``engine.data.catalog``).
#: ``exchange_symbols`` is a single-vendor category with no DataType of its own,
#: so its row uses a concrete exchange (``US`` = combined US exchanges) rather
#: than an unsubstitutable placeholder.
ENDPOINTS: dict[Category, EndpointSpec] = {
    Category.CORE_STOCK_APIS: EndpointSpec(
        Category.CORE_STOCK_APIS,
        "GET",
        "https://eodhd.com/api/eod/{ticker}",
        {"api_token": "$KEY", "fmt": "json", "period": "d"},
    ),
    Category.NEWS_DATA: EndpointSpec(
        Category.NEWS_DATA,
        "GET",
        "https://eodhd.com/api/news",
        {"api_token": "$KEY", "s": "{ticker}", "fmt": "json", "limit": str(_NEWS_LIMIT)},
    ),
    Category.NEWS_SENTIMENT: EndpointSpec(
        Category.NEWS_SENTIMENT,
        "GET",
        "https://eodhd.com/api/sentiments",
        {"api_token": "$KEY", "s": "{ticker}", "fmt": "json"},
    ),
    Category.CORPORATE_ACTIONS: EndpointSpec(
        Category.CORPORATE_ACTIONS,
        "GET",
        "https://eodhd.com/api/div/{ticker}",
        {"api_token": "$KEY", "fmt": "json"},
    ),
    Category.EXCHANGE_SYMBOLS: EndpointSpec(
        Category.EXCHANGE_SYMBOLS,
        "GET",
        "https://eodhd.com/api/exchange-symbol-list/US",
        {"api_token": "$KEY", "fmt": "json"},
    ),
    # Fund fundamentals (mutual funds + ETFs). Documented ticker format is
    # ``{SYMBOL}.{EXCHANGE}`` (``SWPPX.US``); the arm also retries a bare symbol
    # with a ``.US`` suffix (see ``_fund_payload``). JSON-only, 10 API calls.
    Category.FUND_DATA: EndpointSpec(
        Category.FUND_DATA,
        "GET",
        "https://eodhd.com/api/fundamentals/{ticker}",
        {"api_token": "$KEY", "fmt": "json"},
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
    """One canonical PRICE bar ({date, open, high, low, close, volume}), or None.

    A row without a date or close is unusable and skipped rather than emitted
    with fabricated placeholders. Values keep their provider form (None when
    absent); the canonical layer coerces them.
    """
    date = row.get("date")
    close = row.get("close")
    if not date or close is None:
        return None
    return {
        "date": str(date)[:10],
        "open": row.get("open"),
        "high": row.get("high"),
        "low": row.get("low"),
        "close": close,
        "volume": row.get("volume"),
    }


def _sentiment_series(payload: Any) -> list[dict[str, Any]]:
    """Extract the per-date sentiment list from an EODHD /sentiments payload.

    EODHD keys the response by ticker (``{"AAPL.US": [{date, count,
    normalized}, ...]}``); accept a bare list too so a shape change degrades to
    "no rows" instead of an AttributeError.
    """
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        for value in payload.values():
            if isinstance(value, list):
                return [row for row in value if isinstance(row, dict)]
    return []


# ---------------------------------------------------------------------------
# Fund-profile reading (DataType.FUND_PROFILE).
#
# Vendor doc: eodhd-claude-skills/skills/eodhd-api/references/general/
# fundamentals-fund.md — 20k+ US mutual funds, ``GET /fundamentals/{SYMBOL}.{EXCHANGE}``
# (e.g. ``SWPPX.US``), JSON with two top-level sections ``General`` +
# ``MutualFund_Data``.
#
# THE VENDOR MIXES UNITS INSIDE ONE PAYLOAD (its own guide calls them all
# "decimal strings"), so every field is converted here to the canonical
# contract's single convention (a FRACTION = 0.0015 for 15 bp) using OBSERVED
# values as the unit evidence — the doc's SWPPX sample cross-checked against the
# fund's published figures:
#
#   MutualFund_Data.Yield             "0.0118"  = 1.18%   fraction → as-is
#   MutualFund_Data.Expense_Ratio     "0.0200"  = 0.02%   PERCENT  → ÷100
#       (SWPPX's real net expense ratio is 0.02%, so reading the raw as a
#        fraction would be a 100× error — the doc labels the field "decimal",
#        but the as-filed figure proves it is a percent NUMBER)
#   MutualFund_Data.Yield_YTD         "26.6621" = 26.66%  PERCENT  → ÷100
#   MutualFund_Data.Yield_1Year_YTD   "32.8114" = 32.81%  PERCENT  → ÷100
#   MutualFund_Data.Yield_3Year_YTD   "10.0894" = 10.09%  PERCENT  → ÷100
#   MutualFund_Data.Yield_5Year_YTD   "15.7262" = 15.73%  PERCENT  → ÷100
#   Asset_Allocation[].Net_%          "0.34539" = 34.54%  fraction → as-is
#   Sector_Weights[].Amount_%         10.20911  = 10.21%  PERCENT  → ÷100
#   World_Regions[].Stocks_%          99.399    = 99.40%  PERCENT  → ÷100
#   Top_Holdings[].Weight             "6.88%"   = 6.88%   percent string → ÷100
#   Value_Growth "Price/Prospective Earnings" Stock_Portfolio 21.18843 = a P/E
#       MULTIPLE (compare: benchmark 21.21499), not a percent → equity_pe as-is.
#
# Contract fields EODHD has no source for (fund family is covered, but legal
# entity type, category, gross/category-average expense ratio, turnover, 3-month
# return, beta, bond ratings/duration/maturity, shares outstanding) are simply
# absent — never invented.
# ---------------------------------------------------------------------------

#: The ``Value_Growth`` row whose ``Stock_Portfolio`` is the fund's forward P/E.
_PE_LABEL = "Price/Prospective Earnings"

# EODHD's fundamentals endpoint 403s with a body carrying NONE of the
# ``_PLAN_GATE_MARKERS``: "Forbidden. Please contact support@eodhistoricaldata.com".
# Probed 2026-10-12: GET /fundamentals/{IEI.US,VTSAX.US,SWPPX.US,AAPL.US} all
# returned HTTP 403 with exactly that body — AAPL included, so this is a PLAN
# gate (the key has no Fundamentals entitlement), not a fund/symbol problem, and
# the request shape is accepted. The fund arm maps a 403 here to
# ``ProviderPlanError`` so the circuit breaker is not charged and the FUND_DATA
# chain falls through to the next provider.


def _section_rows(raw: Any) -> list[dict[str, Any]]:
    """Rows of an EODHD fund subsection, whatever its container spelling.

    Fund subsections are positional objects (``{"0": {...}, "1": {...}}``), with
    one nested super-sector level for ``Sector_Weights``/``World_Regions``; a
    bare list is accepted too so a shape change degrades to "no rows" instead of
    an AttributeError.
    """
    if isinstance(raw, dict):
        return [value for value in raw.values() if isinstance(value, dict)]
    if isinstance(raw, list):
        return [value for value in raw if isinstance(value, dict)]
    return []


def _fraction(value: Any) -> float | None:
    """Vendor PERCENT NUMBER → fraction (absent stays absent, never a fake 0)."""
    num = _num(value)
    return None if num is None else num / 100.0


def _percent_string(value: Any) -> float | None:
    """Vendor percent string/number (``"6.88%"`` or ``6.88``) → fraction."""
    return _fraction(value.strip().rstrip("%").strip() if isinstance(value, str) else value)


def _asset_classes(raw: Any) -> dict[str, float]:
    """``Asset_Allocation`` rows → ``{Type: Net_%}`` (already a fraction)."""
    out: dict[str, float] = {}
    for row in _section_rows(raw):
        label = row.get("Type")
        weight = _num(row.get("Net_%"))
        if label and weight is not None:
            out[str(label).strip()] = weight
    return out


def _named_weights(raw: Any, value_key: str) -> dict[str, float]:
    """Nested super-sector rows → ``{Name: value/100}`` (values are PERCENTs)."""
    out: dict[str, float] = {}
    if not isinstance(raw, dict):
        return out
    for group in raw.values():
        for row in _section_rows(group):
            label = row.get("Name")
            weight = _fraction(row.get(value_key))
            if label and weight is not None:
                out[str(label).strip()] = weight
    return out


def _equity_pe(raw: Any) -> float | None:
    """The ``Value_Growth`` forward P/E (a MULTIPLE, so unconverted), or None."""
    for row in _section_rows(raw):
        if str(row.get("Name") or "").strip() == _PE_LABEL:
            return _num(row.get("Stock_Portfolio"))
    return None


def _top_holdings(raw: Any) -> list[dict[str, Any]]:
    """``Top_Holdings`` rows → ``[{symbol, name, weight}]`` (weight a fraction).

    EODHD names the security only (``Name``) and ships no ticker, so ``symbol``
    stays None rather than a fabricated guess; the canonical layer keeps the row
    on its reported weight.
    """
    out: list[dict[str, Any]] = []
    for row in _section_rows(raw):
        weight = _percent_string(row.get("Weight"))
        if weight is None:
            continue
        name = row.get("Name")
        out.append({"symbol": None, "name": str(name).strip() if name else None, "weight": weight})
    return out


def _map_fund_payload(payload: Any) -> dict[str, Any]:
    """EODHD fund fundamentals → the canonical FUND_PROFILE key space.

    Pure: no I/O and no vendor calls. Keys mirror ``NormalizedFundProfile``, and
    the value scales are the contract's fractions (see the comment block above).
    A payload missing either top-level section degrades to absent fields rather
    than raising, so a thin fund still yields a usable profile.
    """
    root = payload if isinstance(payload, dict) else {}
    general = root.get("General")
    general = general if isinstance(general, dict) else {}
    fund = root.get("MutualFund_Data")
    fund = fund if isinstance(fund, dict) else {}
    return {
        "name": general.get("Name"),
        "fund_family": general.get("Fund_Family"),
        # ``Type`` is "FUND" for a fund — the vendor's instrument class, i.e. the
        # contract's ``quote_type`` (it is not a legal entity type).
        "quote_type": general.get("Type"),
        "currency": fund.get("Currency") or general.get("CurrencyCode"),
        "inception_date": fund.get("Inception_Date"),
        "total_net_assets": _num(fund.get("Portfolio_Net_Assets")),
        "nav_per_share": _num(fund.get("Nav")),
        "market_price": _num(fund.get("Prev_Close_Price")),
        "net_expense_ratio": _fraction(fund.get("Expense_Ratio")),
        "distribution_yield": _num(fund.get("Yield")),
        "ytd_return": _fraction(fund.get("Yield_YTD")),
        "return_1y": _fraction(fund.get("Yield_1Year_YTD")),
        "return_3y_annual": _fraction(fund.get("Yield_3Year_YTD")),
        "return_5y_annual": _fraction(fund.get("Yield_5Year_YTD")),
        "asset_classes": _asset_classes(fund.get("Asset_Allocation")),
        "sector_weights": _named_weights(fund.get("Sector_Weights"), "Amount_%"),
        "region_weights": _named_weights(fund.get("World_Regions"), "Stocks_%"),
        "equity_pe": _equity_pe(fund.get("Value_Growth")),
        "top_holdings": _top_holdings(fund.get("Top_Holdings")),
    }


def _is_fund_payload(payload: Any) -> bool:
    """True for a fund fundamentals body (has ``General``/``MutualFund_Data``)."""
    if not isinstance(payload, dict) or payload.get("error"):
        return False
    return isinstance(payload.get("General"), dict) or isinstance(
        payload.get("MutualFund_Data"), dict
    )


class EODHDProvider(DataProvider):
    """DataProvider backed by the EODHD API (https://eodhd.com/api).

    Provides price history + a lightweight quote, financial news, news
    sentiment, dividend history, fund profiles (mutual funds / ETFs) and (via
    the catalog/probe) exchange symbol lists. API key required — get one at
    https://eodhd.com/.
    """

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._lock = asyncio.Lock()
        self._last_call: float = 0.0
        # Reuse one AsyncClient across the session to amortise TLS handshakes.
        self._client = httpx.AsyncClient(timeout=_TIMEOUT)

    @property
    def name(self) -> str:
        return "eodhd"

    def capabilities(self) -> list[str | DataType | Category]:
        return list(_CATEGORIES)

    async def fetch(self, ticker: str, data_type: str | DataType, **kwargs: Any) -> DataResult:
        if data_type not in _SUPPORTED_TYPES:
            raise ProviderError(
                f"data_type '{data_type}' is not supported by EODHD. "
                f"Supported: {[str(t) for t in _SUPPORTED_TYPES]}"
            )
        try:
            if data_type == DataType.PRICE:
                return await self._fetch_price(ticker, quote_only=False)
            if data_type == DataType.QUOTE:
                return await self._fetch_price(ticker, quote_only=True)
            if data_type == DataType.NEWS:
                return await self._fetch_news(ticker)
            if data_type == DataType.SENTIMENT:
                return await self._fetch_sentiment(ticker)
            if data_type == DataType.DIVIDENDS:
                return await self._fetch_dividends(ticker)
            if data_type == DataType.FUND_PROFILE:
                return await self._fetch_fund_profile(ticker)
            raise ProviderError(f"Unhandled data_type: {data_type}")
        except httpx.TimeoutException as e:
            raise ProviderError(f"EODHD timeout for '{ticker}'") from e
        except httpx.HTTPStatusError as e:
            # 429 is typed in ``_get`` before raise_for_status, so only
            # non-rate-limit statuses reach here (401 invalid key, 403 non-plan,
            # 5xx …). Never interpolate the raw exception: its str() embeds the
            # request URL with the live ``api_token``.
            raise ProviderError(
                f"EODHD API error for '{ticker}' (HTTP {e.response.status_code})"
            ) from e
        except (
            httpx.ConnectError,
            httpx.RemoteProtocolError,
            httpx.ReadError,
            httpx.WriteError,
        ) as e:
            raise ProviderError(f"EODHD network error for '{ticker}' ({type(e).__name__})") from e
        except ProviderError:
            raise
        except (ValueError, KeyError, TypeError, AttributeError) as e:
            raise ProviderError(f"EODHD fetch failed for '{ticker}' ({type(e).__name__})") from e

    async def _fetch_price(self, ticker: str, *, quote_only: bool) -> DataResult:
        """Trailing OHLC history (PRICE) or the latest close (QUOTE) from /eod.

        Both read the same endpoint: ``quote_only`` shrinks the window to the
        last few sessions. Returns the canonical PRICE shape (``current_price``
        + oldest-first ``price_history`` bars + ``exchange``) so provider-
        agnostic consumers need no EODHD branch.
        """
        today = datetime.now(tz=timezone.utc).date()
        window = _QUOTE_WINDOW_DAYS if quote_only else _PRICE_HISTORY_DAYS
        start = today - timedelta(days=window)
        resp = await self._get(
            f"/eod/{ticker}",
            params={
                "from": start.isoformat(),
                "to": today.isoformat(),
                "period": "d",
                "fmt": "json",
            },
        )
        raw = resp.json()
        rows = raw if isinstance(raw, list) else []
        bars = [bar for bar in (_bar(r) for r in rows if isinstance(r, dict)) if bar is not None]
        bars.sort(key=lambda b: b["date"])
        if not bars:
            raise ProviderError(f"EODHD /eod returned no rows for '{ticker}' (delisted or unknown)")
        current_price = _num(bars[-1]["close"])
        if current_price is None or current_price <= 0:
            raise ProviderError(f"EODHD /eod returned no usable price for '{ticker}'")

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

    async def _fetch_news(self, ticker: str) -> DataResult:
        """Recent company news from /news (canonical ``news_items`` shape).

        EODHD news carries no per-article source field, so ``source`` stays the
        empty string (the same honest default Finnhub uses) rather than an
        invented outlet. ``sentiment_score`` is the article polarity when EODHD
        supplies it.
        """
        resp = await self._get(
            "/news",
            params={"s": ticker, "fmt": "json", "limit": _NEWS_LIMIT},
        )
        raw = resp.json()
        rows = raw if isinstance(raw, list) else []
        news_items: list[dict[str, Any]] = []
        for item in rows:
            if not isinstance(item, dict):
                continue
            title = item.get("title")
            if not title:
                continue
            sentiment = item.get("sentiment")
            news_items.append(
                {
                    "title": title,
                    "source": "",
                    "published": item.get("date") or "",
                    "url": item.get("link") or "",
                    "sentiment_score": (
                        sentiment.get("polarity") if isinstance(sentiment, dict) else None
                    ),
                }
            )
        return DataResult(
            data={"news_items": news_items},
            provider=self.name,
            ticker=ticker,
            data_type=DataType.NEWS,
            timestamp=datetime.now(tz=timezone.utc),
        )

    async def _fetch_sentiment(self, ticker: str) -> DataResult:
        """News sentiment from /sentiments.

        Ships the raw per-date series plus two aggregates derived ONLY from the
        returned rows: ``average_score`` (mean of EODHD's ``normalized`` score,
        which is in [-1, 1]) and ``bullish_avg`` (that mean linearly rescaled to
        a 0–100 bullish reading, matching the sentiment snapshot vocabulary).
        Both are None when no usable score was returned.
        """
        resp = await self._get("/sentiments", params={"s": ticker, "fmt": "json"})
        series = [
            {
                "date": row.get("date"),
                "count": row.get("count"),
                "normalized": row.get("normalized"),
            }
            for row in _sentiment_series(resp.json())
        ]
        scores = [
            score for score in (_num(row.get("normalized")) for row in series) if score is not None
        ]
        mean = sum(scores) / len(scores) if scores else None
        return DataResult(
            data={
                "sentiment": series,
                "average_score": round(mean, 4) if mean is not None else None,
                "bullish_avg": round((mean + 1.0) / 2.0 * 100.0, 1) if mean is not None else None,
                "sources": [],
                "source_alignment": "single_source" if scores else "no_data",
            },
            provider=self.name,
            ticker=ticker,
            data_type=DataType.SENTIMENT,
            timestamp=datetime.now(tz=timezone.utc),
        )

    async def _fetch_dividends(self, ticker: str) -> DataResult:
        """Declared dividend history from /div, aggregated to calendar-year DPS.

        Mirrors FMP's DIVIDENDS contract: per-payment rows are summed within
        their payment-date year under ``annual_dps`` (a JSON-serialisable
        ``{"YYYY": total}`` map), so the DDM seed can share one shape across
        providers. The provider never derives a growth rate itself.
        """
        resp = await self._get(f"/div/{ticker}", params={"fmt": "json"})
        raw = resp.json()
        rows = raw if isinstance(raw, list) else []
        annual: dict[str, float] = {}
        for row in rows:
            if not isinstance(row, dict):
                continue
            date_str = row.get("paymentDate") or row.get("date")
            amount = row.get("value")
            if amount is None:
                amount = row.get("unadjustedValue")
            value = _num(amount)
            if not date_str or value is None:
                continue
            annual[str(date_str)[:4]] = annual.get(str(date_str)[:4], 0.0) + value
        return DataResult(
            data={"annual_dps": annual},
            provider=self.name,
            ticker=ticker,
            data_type=DataType.DIVIDENDS,
            timestamp=datetime.now(tz=timezone.utc),
        )

    async def _fetch_fund_profile(self, ticker: str) -> DataResult:
        """Fund profile + composition from /fundamentals (canonical key space).

        Emits the raw mapping ``_map_fund_payload`` builds — keys mirror
        ``NormalizedFundProfile`` and every ratio/return/yield/weight is already
        the contract's FRACTION (see the comment block above
        ``_map_fund_payload`` for the per-field unit evidence); the canonical
        layer coerces and sanitises it.
        """
        payload = await self._fund_payload(ticker)
        return DataResult(
            data=_map_fund_payload(payload),
            provider=self.name,
            ticker=ticker,
            data_type=DataType.FUND_PROFILE,
            timestamp=datetime.now(tz=timezone.utc),
        )

    async def _fund_payload(self, ticker: str) -> dict[str, Any]:
        """Fundamentals JSON for a fund, trying the bare symbol then ``.US``.

        EODHD documents the fund ticker as ``{SYMBOL}.{EXCHANGE}`` (``SWPPX.US``),
        so a suffix-less symbol is retried with ``.US`` — the ONE exception to
        this provider's "never invent an exchange suffix" rule, and only after
        the caller's verbatim symbol comes back not-found.
        """
        candidates = [ticker]
        if "." not in ticker:
            candidates.append(f"{ticker}.US")
        for symbol in candidates:
            try:
                resp = await self._get(f"/fundamentals/{symbol}", params={"fmt": "json"})
            except httpx.HTTPStatusError as e:
                status = e.response.status_code
                if status == 403:
                    # Plan/entitlement gate (see the block comment above the
                    # mapper helpers): this body is not in ``_PLAN_GATE_MARKERS``.
                    # Typed as a plan gap so the chain skips EODHD without a
                    # circuit-breaker charge. Key-free message by construction.
                    raise ProviderPlanError(
                        f"EODHD plan does not include /fundamentals (HTTP 403) for '{ticker}'"
                    ) from e
                if status == 404:
                    continue  # unknown without the exchange suffix → try ``.US``
                raise
            payload = resp.json()
            if isinstance(payload, dict) and _is_fund_payload(payload):
                return payload
        raise ProviderError(f"EODHD /fundamentals has no fund profile for '{ticker}'")

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> httpx.Response:
        """Authenticated, paced GET against the EODHD API.

        Holds the rate-limit lock only long enough to pace request STARTS
        (``_MIN_INTERVAL`` apart) and releases it before the round-trip so
        concurrent requests overlap. ``api_token`` is added here so call sites
        never handle the credential. The typed 429/plan-gate errors are raised
        before ``raise_for_status`` with key-free messages.
        """
        async with self._lock:
            elapsed = time.monotonic() - self._last_call
            if elapsed < _MIN_INTERVAL:
                await asyncio.sleep(_MIN_INTERVAL - elapsed)
            self._last_call = time.monotonic()
        query: dict[str, Any] = {"api_token": self._api_key}
        if params:
            query.update(params)
        resp = await self._client.get(f"{_BASE_URL}{path}", params=query)
        if resp.status_code == 429:
            raise RateLimitedProviderError(f"EODHD rate limited (HTTP 429) for {path}")
        if resp.status_code == 403:
            body = resp.text[:500].lower()
            if any(marker in body for marker in _PLAN_GATE_MARKERS):
                raise ProviderPlanError(
                    f"EODHD plan does not include {path} (HTTP 403 plan/entitlement gate)"
                )
        resp.raise_for_status()
        return resp

    async def close(self) -> None:
        """Release the shared httpx client. Called from DataLayer.close()."""
        await self._client.aclose()
