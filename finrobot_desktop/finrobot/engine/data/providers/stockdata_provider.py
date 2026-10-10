"""StockData.org provider for the Data Layer v3.

Fetches end-of-day OHLC history (and a lightweight quote) plus market news from
the StockData.org API (https://api.stockdata.org). Requires an API token (env
``STOCKDATA_API_KEY``) passed as the ``api_token`` query parameter; get one at
https://www.stockdata.org/.

Serves the ``core_stock_apis`` and ``news_data`` categories (see
``docs/DATA_PROVIDERS_V3_DESIGN.md`` §5.2). Both PRICE and QUOTE are served by
the single ``/v1/data/eod`` endpoint declared in ``ENDPOINTS``.

Note: ``/v1/data/eod`` is a Standard-plan-and-above endpoint — a free-tier key
gets a plan-gated 403, which maps to ``ProviderPlanError`` so the data layer
falls through without charging the circuit breaker.
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

_BASE_URL = "https://api.stockdata.org"
_TIMEOUT = 15.0
# StockData's free tier is capped per day; a light per-start pace keeps a
# concurrent burst from tripping the burst limiter.
_MIN_INTERVAL = 0.34
_PRICE_HISTORY_DAYS = 372
_QUOTE_WINDOW_DAYS = 10
_NEWS_LIMIT = 50

# Body substrings that mark an HTTP 403 as a plan/entitlement gate (valid key,
# subscription does not include the endpoint). Key-free; the URL is never read.
_PLAN_GATE_MARKERS = ("subscription", "upgrade", "plan", "not included")

_CATEGORIES: list[str | DataType | Category] = [
    Category.CORE_STOCK_APIS,
    Category.NEWS_DATA,
]

_SUPPORTED_TYPES: tuple[DataType, ...] = (DataType.PRICE, DataType.QUOTE, DataType.NEWS)

#: Endpoint catalog rows for the v3 probe. ``/v1/data/eod`` serves the whole
#: ``core_stock_apis`` category (history and the latest close alike).
ENDPOINTS: dict[Category, EndpointSpec] = {
    Category.CORE_STOCK_APIS: EndpointSpec(
        Category.CORE_STOCK_APIS,
        "GET",
        "https://api.stockdata.org/v1/data/eod",
        {"symbols": "{ticker}", "interval": "day", "api_token": "$KEY"},
    ),
    Category.NEWS_DATA: EndpointSpec(
        Category.NEWS_DATA,
        "GET",
        "https://api.stockdata.org/v1/news/all",
        {"symbols": "{ticker}", "api_token": "$KEY", "limit": str(_NEWS_LIMIT)},
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

    StockData returns a flat bar object per session; a row without a date or
    close is skipped rather than emitted with fabricated placeholders.
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


class StockDataProvider(DataProvider):
    """DataProvider backed by the StockData.org API (https://api.stockdata.org).

    Provides end-of-day OHLC history + a lightweight quote and market news. API
    token required — get one at https://www.stockdata.org/.
    """

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._lock = asyncio.Lock()
        self._last_call: float = 0.0
        # Reuse one AsyncClient across the session to amortise TLS handshakes.
        self._client = httpx.AsyncClient(timeout=_TIMEOUT)

    @property
    def name(self) -> str:
        return "stockdata"

    def capabilities(self) -> list[str | DataType | Category]:
        return list(_CATEGORIES)

    async def fetch(self, ticker: str, data_type: str | DataType, **kwargs: Any) -> DataResult:
        if data_type not in _SUPPORTED_TYPES:
            raise ProviderError(
                f"data_type '{data_type}' is not supported by StockData. "
                f"Supported: {[str(t) for t in _SUPPORTED_TYPES]}"
            )
        try:
            if data_type == DataType.PRICE:
                return await self._fetch_price(ticker, quote_only=False)
            if data_type == DataType.QUOTE:
                return await self._fetch_price(ticker, quote_only=True)
            if data_type == DataType.NEWS:
                return await self._fetch_news(ticker)
            raise ProviderError(f"Unhandled data_type: {data_type}")
        except httpx.TimeoutException as e:
            raise ProviderError(f"StockData timeout for '{ticker}'") from e
        except httpx.HTTPStatusError as e:
            # 429/403-plan are typed in ``_get`` before raise_for_status. Never
            # interpolate the raw exception: its str() embeds the request URL
            # with the live ``api_token``.
            raise ProviderError(
                f"StockData API error for '{ticker}' (HTTP {e.response.status_code})"
            ) from e
        except (
            httpx.ConnectError,
            httpx.RemoteProtocolError,
            httpx.ReadError,
            httpx.WriteError,
        ) as e:
            raise ProviderError(
                f"StockData network error for '{ticker}' ({type(e).__name__})"
            ) from e
        except ProviderError:
            raise
        except (ValueError, KeyError, TypeError, AttributeError) as e:
            raise ProviderError(
                f"StockData fetch failed for '{ticker}' ({type(e).__name__})"
            ) from e

    async def _fetch_price(self, ticker: str, *, quote_only: bool) -> DataResult:
        """EOD OHLC history (PRICE) or the latest close (QUOTE).

        Both read ``/v1/data/eod``; ``quote_only`` shrinks the window to the last
        few sessions. Emits the canonical PRICE shape (``current_price`` +
        oldest-first ``price_history`` + ``exchange``).
        """
        today = datetime.now(tz=timezone.utc).date()
        window = _QUOTE_WINDOW_DAYS if quote_only else _PRICE_HISTORY_DAYS
        start = today - timedelta(days=window)
        resp = await self._get(
            "/v1/data/eod",
            params={
                "symbols": ticker,
                "interval": "day",
                "sort": "asc",
                "date_from": start.isoformat(),
                "date_to": today.isoformat(),
            },
        )
        payload = resp.json()
        if isinstance(payload, dict) and payload.get("error"):
            # StockData signals errors with an "error" object; that vendor
            # message is not interpolated (kept key-free and stable).
            raise ProviderError(f"StockData returned an error response for '{ticker}'")
        rows = payload.get("data") if isinstance(payload, dict) else payload
        rows = rows if isinstance(rows, list) else []
        bars = [bar for bar in (_bar(r) for r in rows if isinstance(r, dict)) if bar is not None]
        bars.sort(key=lambda b: b["date"])
        if not bars:
            raise ProviderError(
                f"StockData /v1/data/eod returned no rows for '{ticker}' (unknown symbol)"
            )
        current_price = _num(bars[-1]["close"])
        if current_price is None or current_price <= 0:
            raise ProviderError(f"StockData /v1/data/eod returned no usable price for '{ticker}'")

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
        """Recent market news from /v1/news/all (canonical ``news_items`` shape)."""
        resp = await self._get(
            "/v1/news/all",
            params={"symbols": ticker, "limit": _NEWS_LIMIT},
        )
        payload = resp.json()
        if isinstance(payload, dict) and payload.get("error"):
            raise ProviderError(f"StockData returned an error response for '{ticker}'")
        rows = payload.get("data") if isinstance(payload, dict) else payload
        rows = rows if isinstance(rows, list) else []
        news_items: list[dict[str, Any]] = []
        for item in rows:
            if not isinstance(item, dict):
                continue
            title = item.get("title")
            if not title:
                continue
            news_items.append(
                {
                    "title": title,
                    "source": item.get("source") or "",
                    "published": item.get("published_at") or "",
                    "url": item.get("url") or "",
                }
            )
        return DataResult(
            data={"news_items": news_items},
            provider=self.name,
            ticker=ticker,
            data_type=DataType.NEWS,
            timestamp=datetime.now(tz=timezone.utc),
        )

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> httpx.Response:
        """Authenticated, paced GET against the StockData API.

        Holds the rate-limit lock only long enough to pace request STARTS and
        releases it before the round-trip so concurrent requests overlap.
        ``api_token`` is added here so call sites never handle the credential.
        The typed 429/plan-gate errors are raised before ``raise_for_status``
        with key-free messages.
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
            raise RateLimitedProviderError(f"StockData rate limited (HTTP 429) for {path}")
        if resp.status_code == 403:
            body = resp.text[:500].lower()
            if any(marker in body for marker in _PLAN_GATE_MARKERS):
                raise ProviderPlanError(
                    f"StockData plan does not include {path} (HTTP 403 plan/entitlement gate)"
                )
        resp.raise_for_status()
        return resp

    async def close(self) -> None:
        """Release the shared httpx client. Called from DataLayer.close()."""
        await self._client.aclose()
