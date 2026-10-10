"""Twelve Data provider for the Data Layer v3.

Fetches end-of-day OHLC history (and a lightweight quote) from the Twelve Data
API (https://api.twelvedata.com). Requires an API key (env
``TWELVEDATA_API_KEY``) passed as the ``apikey`` query parameter; get one at
https://twelvedata.com/.

Serves the ``core_stock_apis`` category (see
``docs/DATA_PROVIDERS_V3_DESIGN.md`` §5.2). Both PRICE and QUOTE are served by
the single ``/time_series`` endpoint declared in ``ENDPOINTS``.
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
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

_BASE_URL = "https://api.twelvedata.com"
_TIMEOUT = 15.0
# Twelve Data's free tier is 8 API credits/minute (a /time_series request may
# cost several credits), so pace request starts conservatively.
_MIN_INTERVAL = 1.0
# ~1 trading year of sessions; a few extra so the trailing 52-week window is
# fully covered across holidays.
_HISTORY_SIZE = 400
_QUOTE_SIZE = 5

# Body substrings that mark an HTTP 403 as a plan/entitlement gate (valid key,
# subscription does not include the endpoint). Key-free; the URL is never read.
_PLAN_GATE_MARKERS = ("subscription", "upgrade", "plan", "not available on your")

_CATEGORIES: list[str | DataType | Category] = [
    Category.CORE_STOCK_APIS,
]

_SUPPORTED_TYPES: tuple[DataType, ...] = (DataType.PRICE, DataType.QUOTE)

#: Endpoint catalog row for the v3 probe (``/time_series`` serves the whole
#: ``core_stock_apis`` category — price history and the latest price alike).
ENDPOINTS: dict[Category, EndpointSpec] = {
    Category.CORE_STOCK_APIS: EndpointSpec(
        Category.CORE_STOCK_APIS,
        "GET",
        "https://api.twelvedata.com/time_series",
        {
            "symbol": "{ticker}",
            "interval": "1day",
            "outputsize": str(_HISTORY_SIZE),
            "apikey": "$KEY",
        },
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

    Twelve Data returns string-typed OHLCV; values are coerced to float (None
    when absent). A row without a datetime or close is skipped rather than
    emitted with fabricated placeholders.
    """
    date = row.get("datetime")
    close = _num(row.get("close"))
    if not date or close is None:
        return None
    return {
        "date": str(date)[:10],
        "open": _num(row.get("open")),
        "high": _num(row.get("high")),
        "low": _num(row.get("low")),
        "close": close,
        "volume": _num(row.get("volume")),
    }


class TwelveDataProvider(DataProvider):
    """DataProvider backed by the Twelve Data API (https://api.twelvedata.com).

    Provides daily OHLC history and a lightweight quote. API key required — get
    one at https://twelvedata.com/.
    """

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._lock = asyncio.Lock()
        self._last_call: float = 0.0
        # Reuse one AsyncClient across the session to amortise TLS handshakes.
        self._client = httpx.AsyncClient(timeout=_TIMEOUT)

    @property
    def name(self) -> str:
        return "twelvedata"

    def capabilities(self) -> list[str | DataType | Category]:
        return list(_CATEGORIES)

    async def fetch(self, ticker: str, data_type: str | DataType, **kwargs: Any) -> DataResult:
        if data_type not in _SUPPORTED_TYPES:
            raise ProviderError(
                f"data_type '{data_type}' is not supported by Twelve Data. "
                f"Supported: {[str(t) for t in _SUPPORTED_TYPES]}"
            )
        try:
            if data_type == DataType.PRICE:
                return await self._fetch_price(ticker, quote_only=False)
            if data_type == DataType.QUOTE:
                return await self._fetch_price(ticker, quote_only=True)
            raise ProviderError(f"Unhandled data_type: {data_type}")
        except httpx.TimeoutException as e:
            raise ProviderError(f"Twelve Data timeout for '{ticker}'") from e
        except httpx.HTTPStatusError as e:
            # 429/403-plan are typed in ``_get`` before raise_for_status. Never
            # interpolate the raw exception: its str() embeds the request URL.
            raise ProviderError(
                f"Twelve Data API error for '{ticker}' (HTTP {e.response.status_code})"
            ) from e
        except (
            httpx.ConnectError,
            httpx.RemoteProtocolError,
            httpx.ReadError,
            httpx.WriteError,
        ) as e:
            raise ProviderError(
                f"Twelve Data network error for '{ticker}' ({type(e).__name__})"
            ) from e
        except ProviderError:
            raise
        except (ValueError, KeyError, TypeError, AttributeError) as e:
            raise ProviderError(
                f"Twelve Data fetch failed for '{ticker}' ({type(e).__name__})"
            ) from e

    async def _fetch_price(self, ticker: str, *, quote_only: bool) -> DataResult:
        """Daily OHLC history (PRICE) or the latest close (QUOTE).

        Both read ``/time_series``; ``quote_only`` trims the requested size.
        Emits the canonical PRICE shape (``current_price`` + oldest-first
        ``price_history`` + ``exchange`` + ``quote_currency``).
        """
        outputsize = _QUOTE_SIZE if quote_only else _HISTORY_SIZE
        resp = await self._get(
            "/time_series",
            params={
                "symbol": ticker,
                "interval": "1day",
                "outputsize": outputsize,
                "order": "asc",
            },
        )
        payload = resp.json()
        if isinstance(payload, dict) and payload.get("status") == "error":
            # Twelve Data signals API errors with a status:"error" body; the
            # vendor message is not interpolated (kept key-free and stable).
            raise ProviderError(f"Twelve Data returned an error response for '{ticker}'")
        values = payload.get("values") if isinstance(payload, dict) else None
        rows = values if isinstance(values, list) else []
        bars = [bar for bar in (_bar(r) for r in rows if isinstance(r, dict)) if bar is not None]
        bars.sort(key=lambda b: b["date"])
        if not bars:
            raise ProviderError(
                f"Twelve Data /time_series returned no rows for '{ticker}' (unknown symbol)"
            )
        current_price = _num(bars[-1]["close"])
        if current_price is None or current_price <= 0:
            raise ProviderError(f"Twelve Data /time_series returned no usable price for '{ticker}'")

        meta = payload.get("meta") if isinstance(payload, dict) else None
        meta = meta if isinstance(meta, dict) else {}
        exchange = meta.get("exchange")
        currency = meta.get("currency")

        timestamp = datetime.now(tz=timezone.utc)
        if quote_only:
            return DataResult(
                data={"price": current_price, "quote_currency": currency},
                provider=self.name,
                ticker=ticker,
                data_type=DataType.QUOTE,
                timestamp=timestamp,
            )
        return DataResult(
            data={
                "current_price": current_price,
                "price_history": bars,
                "exchange": exchange,
                "quote_currency": currency,
            },
            provider=self.name,
            ticker=ticker,
            data_type=DataType.PRICE,
            timestamp=timestamp,
        )

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> httpx.Response:
        """Authenticated, paced GET against the Twelve Data API.

        Holds the rate-limit lock only long enough to pace request STARTS and
        releases it before the round-trip so concurrent requests overlap.
        ``apikey`` is added here so call sites never handle the credential. The
        typed 429/plan-gate errors are raised before ``raise_for_status`` with
        key-free messages.
        """
        async with self._lock:
            elapsed = time.monotonic() - self._last_call
            if elapsed < _MIN_INTERVAL:
                await asyncio.sleep(_MIN_INTERVAL - elapsed)
            self._last_call = time.monotonic()
        query: dict[str, Any] = {"apikey": self._api_key}
        if params:
            query.update(params)
        resp = await self._client.get(f"{_BASE_URL}{path}", params=query)
        if resp.status_code == 429:
            raise RateLimitedProviderError(f"Twelve Data rate limited (HTTP 429) for {path}")
        if resp.status_code == 403:
            body = resp.text[:500].lower()
            if any(marker in body for marker in _PLAN_GATE_MARKERS):
                raise ProviderPlanError(
                    f"Twelve Data plan does not include {path} (HTTP 403 plan/entitlement gate)"
                )
        resp.raise_for_status()
        return resp

    async def close(self) -> None:
        """Release the shared httpx client. Called from DataLayer.close()."""
        await self._client.aclose()
