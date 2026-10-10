# finrobot/engine/data/providers/fred_provider.py
"""FRED macro-series provider.

Backed by the St. Louis Fed FRED API at https://api.stlouisfed.org/fred.
Requires a free API key (env ``FRED_API_KEY``); register at
https://fred.stlouisfed.org/docs/api/api_key.html. Serves ``macro_data`` only —
``fetch`` treats the ``ticker`` argument as a FRED series id (e.g. ``GDP``,
``CPIAUCSL``) and returns that series' observations.
"""

from __future__ import annotations

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

_BASE_URL = "https://api.stlouisfed.org/fred"
_TIMEOUT = 15.0
# FRED allows ~120 requests/minute per key; pace comfortably below that.
_MIN_INTERVAL = 0.5
_SUPPORTED: list[str | DataType] = [Category.MACRO_DATA]

_PLAN_MARKERS: tuple[str, ...] = (
    "subscription",
    "plan",
    "upgrade",
    "entitlement",
    "not authorized",
    "does not have access",
    "premium",
    "exclusive",
)
# Caller kwargs forwarded verbatim to /series/observations.
_PASSTHROUGH_KWARGS: tuple[str, ...] = (
    "observation_start",
    "observation_end",
    "frequency",
    "units",
    "aggregation_method",
    "sort_order",
    "limit",
    "offset",
)


class FredProvider(DataProvider):
    """DataProvider backed by the St. Louis Fed FRED API.

    Provides macro-economic series observations (``macro_data``). API key
    required — get one free at https://fred.stlouisfed.org/docs/api/api_key.html.
    """

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        # Reuse one AsyncClient across the session to amortise TLS handshakes.
        self._client = httpx.AsyncClient(timeout=_TIMEOUT)

    @property
    def name(self) -> str:
        return "fred"

    def capabilities(self) -> list[str | DataType]:
        return list(_SUPPORTED)

    async def fetch(self, ticker: str, data_type: str | DataType, **kwargs: Any) -> DataResult:
        if data_type not in _SUPPORTED:
            raise ProviderError(
                f"data_type '{data_type}' is not supported by FRED. Supported: {_SUPPORTED}"
            )
        try:
            data = await self._fetch_observations(ticker, **kwargs)
        except httpx.TimeoutException as e:
            raise ProviderError(f"FRED timeout for '{ticker}'") from e
        except httpx.HTTPStatusError as e:
            raise _classify_http_error(e, ticker) from e
        except (
            httpx.ConnectError,
            httpx.RemoteProtocolError,
            httpx.ReadError,
            httpx.WriteError,
        ) as e:
            raise ProviderError(f"FRED network error for '{ticker}' ({type(e).__name__})") from e
        except ProviderError:
            raise
        except (ValueError, KeyError, TypeError, AttributeError) as e:
            raise ProviderError(f"FRED fetch failed for '{ticker}' ({type(e).__name__})") from e

        return DataResult(
            data=data,
            provider=self.name,
            ticker=ticker,
            data_type=data_type,
            timestamp=datetime.now(tz=timezone.utc),
        )

    async def _fetch_observations(self, ticker: str, **kwargs: Any) -> dict[str, Any]:
        """Fetch one FRED series' observations from ``/series/observations`` (JSON)."""
        series_id = ticker or "GDP"
        params: dict[str, Any] = {
            "series_id": series_id,
            "api_key": self._api_key,
            "file_type": "json",
        }
        for key in _PASSTHROUGH_KWARGS:
            value = kwargs.get(key)
            if value is not None:
                params[key] = value
        payload = (await self._get("/series/observations", params=params)).json()
        if not isinstance(payload, dict):
            raise ProviderError(f"FRED returned an unexpected payload for '{series_id}'")
        raw = payload.get("observations")
        observations: list[dict[str, Any]] = []
        for row in raw if isinstance(raw, list) else []:
            if not isinstance(row, dict):
                continue
            observations.append(
                {"date": row.get("date"), "value": _optional_float(row.get("value"))}
            )
        result: dict[str, Any] = {"series_id": series_id, "observations": observations}
        count = payload.get("count")
        if count is not None:
            result["count"] = count
        return result

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> httpx.Response:
        """GET ``path`` on the FRED API; the key travels as the ``api_key`` query param."""
        resp = await self._client.get(f"{_BASE_URL}{path}", params=params or {})
        resp.raise_for_status()
        return resp

    async def close(self) -> None:
        """Release the shared httpx client. Called from DataLayer.close()."""
        await self._client.aclose()


def _classify_http_error(exc: httpx.HTTPStatusError, ticker: str) -> ProviderError:
    """Map an FRED HTTP failure onto the typed taxonomy WITHOUT leaking the key.

    The request URL carries ``api_key``, so it is never interpolated into a
    message; only the status/context is.
    """
    status = exc.response.status_code
    if status == 429:
        return RateLimitedProviderError(f"FRED rate limited (HTTP 429) for '{ticker}'")
    if status == 403 and _is_plan_gate(exc.response):
        return ProviderPlanError(
            f"FRED endpoint not available on this API key's plan (HTTP 403) for '{ticker}'"
        )
    return ProviderError(f"FRED API error for '{ticker}' (HTTP {status})")


def _is_plan_gate(response: httpx.Response) -> bool:
    """True when a 403 body reads as a plan/entitlement gate rather than a bad key."""
    try:
        body = response.text.lower()
    except (httpx.ResponseNotRead, UnicodeDecodeError):
        return False
    return any(marker in body for marker in _PLAN_MARKERS)


def _optional_float(value: Any) -> float | None:
    """Parse a FRED observation cell, preserving None for absent/'.'/'NaN' values."""
    if value is None or value == "":
        return None
    if isinstance(value, str) and value.strip() in {".", "NaN", "null"}:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


ENDPOINTS: dict[Category, EndpointSpec] = {
    Category.MACRO_DATA: EndpointSpec(
        capability=Category.MACRO_DATA,
        method="GET",
        url=f"{_BASE_URL}/series/observations",
        params={"series_id": "GDP", "api_key": "$KEY", "file_type": "json"},
    ),
}
