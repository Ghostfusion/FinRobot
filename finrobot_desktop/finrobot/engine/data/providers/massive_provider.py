"""Massive DataProvider adapter.

Serves core stock data from the Massive REST API at https://api.massive.com
(Massive is Polygon.io rebranded; the request shape is unchanged). Requests
authenticate with the ``apiKey`` query parameter. API key required — set
``MASSIVE_API_KEY``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from finrobot.engine.data.catalog import EndpointSpec
from finrobot.engine.data.categories import Category, category_of
from finrobot.engine.data.interface import (
    DataProvider,
    DataResult,
    ProviderError,
    ProviderPlanError,
    RateLimitedProviderError,
)
from finrobot.engine.data.types import DataType

_BASE_URL = "https://api.massive.com"
_TIMEOUT = 15.0

#: Categories this provider serves (from the owner's priority table).
_CATEGORIES: list[Category] = [Category.CORE_STOCK_APIS]

# Plan/entitlement markers in a 403 body → ProviderPlanError (deterministic
# capability gap). Key-free substrings only.
_PLAN_MARKERS: tuple[str, ...] = (
    "plan",
    "entitlement",
    "not entitled",
    "exclusive",
    "legacy",
    "subscription",
    "upgrade",
)

#: Declarative catalog row. The previous-day-bar endpoint needs only a ticker
#: (no date range), so it is probe-safe; ``apiKey`` carries the credential.
ENDPOINTS: dict[Category, EndpointSpec] = {
    Category.CORE_STOCK_APIS: EndpointSpec(
        Category.CORE_STOCK_APIS,
        "GET",
        f"{_BASE_URL}/v2/aggs/ticker/{{ticker}}/prev",
        {"adjusted": "true", "apiKey": "$KEY"},
    ),
}


def _classify_http_error(exc: httpx.HTTPStatusError, ticker: str) -> ProviderError:
    """Map an httpx HTTP error to a typed ProviderError.

    The message never interpolates the raw exception or the request URL (which
    carries the live key).
    """
    status = exc.response.status_code
    if status == 429:
        return RateLimitedProviderError(f"Massive rate limited (HTTP 429) for '{ticker}'")
    if status == 403:
        try:
            body = exc.response.text.lower()
        except (httpx.ResponseNotRead, UnicodeDecodeError):
            body = ""
        if any(marker in body for marker in _PLAN_MARKERS):
            return ProviderPlanError(f"Massive plan/entitlement gate (HTTP 403) for '{ticker}'")
    return ProviderError(f"Massive API error for '{ticker}' (HTTP {status})")


class MassiveProvider(DataProvider):
    """DataProvider backed by the Massive API (https://api.massive.com).

    Serves core stock aggregates (previous trading day OHLCV). API key
    required — set ``MASSIVE_API_KEY``.
    """

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        # Reuse one AsyncClient across the session to amortise TLS handshakes.
        self._client = httpx.AsyncClient(timeout=_TIMEOUT)

    @property
    def name(self) -> str:
        return "massive"

    def capabilities(self) -> list[str | DataType | Category]:
        return list(_CATEGORIES)

    async def fetch(self, ticker: str, data_type: str | DataType, **kwargs: Any) -> DataResult:
        category = self._resolve_category(data_type)
        if category != Category.CORE_STOCK_APIS:
            raise ProviderError(
                f"data_type '{data_type}' is not supported by Massive. "
                f"Supported: {list(_CATEGORIES)}"
            )
        try:
            data = await self._fetch_previous_day(ticker)
        except httpx.TimeoutException as e:
            raise ProviderError(f"Massive timeout for '{ticker}'") from e
        except httpx.HTTPStatusError as e:
            raise _classify_http_error(e, ticker) from e
        except (
            httpx.ConnectError,
            httpx.RemoteProtocolError,
            httpx.ReadError,
            httpx.WriteError,
        ) as e:
            raise ProviderError(f"Massive network error for '{ticker}' ({type(e).__name__})") from e
        except ProviderError:
            raise
        except (ValueError, KeyError, TypeError, AttributeError) as e:
            raise ProviderError(f"Massive fetch failed for '{ticker}' ({type(e).__name__})") from e

        return DataResult(
            data=data,
            provider=self.name,
            ticker=ticker,
            data_type=data_type,
            timestamp=datetime.now(tz=timezone.utc),
        )

    @staticmethod
    def _resolve_category(data_type: str | DataType) -> Category | None:
        """Accept either a ``Category`` value or a legacy ``DataType``."""
        try:
            return Category(data_type)
        except ValueError:
            return category_of(data_type)

    async def _fetch_previous_day(self, ticker: str) -> dict[str, Any]:
        """Fetch the previous trading day's OHLCV bar from ``/v2/aggs/.../prev``."""
        payload = (await self._get(f"/v2/aggs/ticker/{ticker}/prev")).json()
        if not isinstance(payload, dict) or payload.get("status") not in {"OK", "DELAYED"}:
            # Massive returns a key-free ``error`` string for bad requests.
            error = payload.get("error") if isinstance(payload, dict) else None
            detail = f": {error}" if isinstance(error, str) and error else ""
            raise ProviderError(f"Massive returned no data for '{ticker}'{detail}")

        results = payload.get("results")
        bars: list[dict[str, Any]] = []
        if isinstance(results, list):
            for bar in results:
                if not isinstance(bar, dict):
                    continue
                bars.append(
                    {
                        "timestamp": bar.get("t"),
                        "open": bar.get("o"),
                        "high": bar.get("h"),
                        "low": bar.get("l"),
                        "close": bar.get("c"),
                        "volume": bar.get("v"),
                        "vwap": bar.get("vw"),
                    }
                )
        return {
            "ticker": payload.get("ticker") or ticker,
            "adjusted": payload.get("adjusted"),
            "bars": bars,
        }

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> httpx.Response:
        """Authenticated GET against Massive (key in the ``apiKey`` query param)."""
        merged = dict(params or {})
        merged["apiKey"] = self._api_key
        resp = await self._client.get(f"{_BASE_URL}{path}", params=merged)
        resp.raise_for_status()
        return resp

    async def close(self) -> None:
        """Release the shared httpx client. Called from DataLayer.close()."""
        await self._client.aclose()
