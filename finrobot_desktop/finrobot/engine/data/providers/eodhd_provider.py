"""EODHD (EOD Historical Data) provider for the Data Layer v3.

Fetches end-of-day prices, financial news, news sentiment, dividend history and
exchange symbol lists from the EODHD API (https://eodhd.com/api). Requires an
API key (env ``EODHD_API_KEY``) passed as the ``api_token`` query parameter; get
one at https://eodhd.com/.

Serves the ``core_stock_apis``, ``news_data``, ``news_sentiment``,
``corporate_actions`` and ``exchange_symbols`` categories
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
]

_SUPPORTED_TYPES: tuple[DataType, ...] = (
    DataType.PRICE,
    DataType.QUOTE,
    DataType.NEWS,
    DataType.SENTIMENT,
    DataType.DIVIDENDS,
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


class EODHDProvider(DataProvider):
    """DataProvider backed by the EODHD API (https://eodhd.com/api).

    Provides price history + a lightweight quote, financial news, news
    sentiment, dividend history and (via the catalog/probe) exchange symbol
    lists. API key required — get one at https://eodhd.com/.
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
