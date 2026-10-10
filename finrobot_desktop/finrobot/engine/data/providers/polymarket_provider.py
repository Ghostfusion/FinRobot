# finrobot/engine/data/providers/polymarket_provider.py
"""Polymarket prediction-markets provider (keyless).

Backed by the Polymarket Gamma API at https://gamma-api.polymarket.com. Serves
``prediction_markets`` only: ``fetch`` lists active markets (``/markets``),
ordered by volume, and — when a ``ticker`` is supplied — keeps the markets whose
question or slug mentions it. No credential.
"""

from __future__ import annotations

import json
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

_BASE_URL = "https://gamma-api.polymarket.com"
_TIMEOUT = 15.0
_MIN_INTERVAL = 0.5
_DEFAULT_LIMIT = 50
_MAX_LIMIT = 500
_SUPPORTED: list[str | DataType] = [Category.PREDICTION_MARKETS]

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


class PolymarketProvider(DataProvider):
    """DataProvider backed by the Polymarket Gamma API.

    Provides live prediction markets (``prediction_markets``) from
    https://gamma-api.polymarket.com. No API key required.
    """

    def __init__(self) -> None:
        # Reuse one AsyncClient across the session to amortise TLS handshakes.
        self._client = httpx.AsyncClient(timeout=_TIMEOUT)

    @property
    def name(self) -> str:
        return "polymarket"

    def capabilities(self) -> list[str | DataType]:
        return list(_SUPPORTED)

    async def fetch(self, ticker: str, data_type: str | DataType, **kwargs: Any) -> DataResult:
        if data_type not in _SUPPORTED:
            raise ProviderError(
                f"data_type '{data_type}' is not supported by Polymarket. Supported: {_SUPPORTED}"
            )
        limit = _clamp_limit(kwargs.get("limit", _DEFAULT_LIMIT))
        closed = bool(kwargs.get("closed", False))
        try:
            data = await self._fetch_markets(ticker, limit, closed)
        except httpx.TimeoutException as e:
            raise ProviderError(f"Polymarket timeout for '{ticker}'") from e
        except httpx.HTTPStatusError as e:
            raise _classify_http_error(e, ticker) from e
        except (
            httpx.ConnectError,
            httpx.RemoteProtocolError,
            httpx.ReadError,
            httpx.WriteError,
        ) as e:
            raise ProviderError(
                f"Polymarket network error for '{ticker}' ({type(e).__name__})"
            ) from e
        except ProviderError:
            raise
        except (ValueError, KeyError, TypeError, AttributeError) as e:
            raise ProviderError(
                f"Polymarket fetch failed for '{ticker}' ({type(e).__name__})"
            ) from e

        return DataResult(
            data=data,
            provider=self.name,
            ticker=ticker,
            data_type=data_type,
            timestamp=datetime.now(tz=timezone.utc),
        )

    async def _fetch_markets(self, ticker: str, limit: int, closed: bool) -> dict[str, Any]:
        """List markets from ``/markets``; optionally filter client-side by ``ticker``."""
        params = {
            "limit": str(limit),
            "closed": str(closed).lower(),
            "order": "volume",
            "ascending": "false",
        }
        payload = (await self._get("/markets", params=params)).json()
        if not isinstance(payload, list):
            raise ProviderError("Polymarket returned an unexpected payload for /markets")
        markets = [_parse_market(row) for row in payload if isinstance(row, dict)]
        needle = (ticker or "").strip().lower()
        if needle and needle not in {"*", "all"}:
            markets = [m for m in markets if _matches(m, needle)]
        return {"query": ticker or None, "markets": markets}

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> httpx.Response:
        """GET ``path`` on the Polymarket Gamma API."""
        resp = await self._client.get(f"{_BASE_URL}{path}", params=params or {})
        resp.raise_for_status()
        return resp

    async def close(self) -> None:
        """Release the shared httpx client. Called from DataLayer.close()."""
        await self._client.aclose()


def _matches(market: dict[str, Any], needle: str) -> bool:
    """True when the market's question or slug contains the search term."""
    for field in ("question", "slug"):
        value = market.get(field)
        if isinstance(value, str) and needle in value.lower():
            return True
    return False


def _parse_market(row: dict[str, Any]) -> dict[str, Any]:
    """Normalise one Gamma market; absent fields stay None (never a fake 0)."""
    volume = row.get("volumeNum")
    if volume is None:
        volume = row.get("volume")
    liquidity = row.get("liquidityNum")
    if liquidity is None:
        liquidity = row.get("liquidity")
    return {
        "id": row.get("id"),
        "question": row.get("question"),
        "slug": row.get("slug"),
        "end_date": row.get("endDate"),
        "outcomes": _json_list(row.get("outcomes")),
        "outcome_prices": _json_list(row.get("outcomePrices")),
        "volume": _optional_float(volume),
        "liquidity": _optional_float(liquidity),
        "active": row.get("active"),
        "closed": row.get("closed"),
    }


def _json_list(value: Any) -> list[Any] | None:
    """Decode Gamma's JSON-string lists (``outcomes`` / ``outcomePrices``)."""
    if isinstance(value, list):
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
        except ValueError:
            return None
        return parsed if isinstance(parsed, list) else None
    return None


def _clamp_limit(value: Any) -> int:
    """Clamp a requested market count to the Gamma API's usable range."""
    try:
        count = int(value)
    except (TypeError, ValueError):
        count = _DEFAULT_LIMIT
    return max(1, min(_MAX_LIMIT, count))


def _classify_http_error(exc: httpx.HTTPStatusError, ticker: str) -> ProviderError:
    """Map a Gamma HTTP failure onto the typed taxonomy (no request URL in messages)."""
    status = exc.response.status_code
    if status == 429:
        return RateLimitedProviderError(f"Polymarket rate limited (HTTP 429) for '{ticker}'")
    if status == 403 and _is_plan_gate(exc.response):
        return ProviderPlanError(f"Polymarket endpoint gated upstream (HTTP 403) for '{ticker}'")
    return ProviderError(f"Polymarket API error for '{ticker}' (HTTP {status})")


def _is_plan_gate(response: httpx.Response) -> bool:
    """True when a 403 body reads as an upstream plan/entitlement gate."""
    try:
        body = response.text.lower()
    except (httpx.ResponseNotRead, UnicodeDecodeError):
        return False
    return any(marker in body for marker in _PLAN_MARKERS)


def _optional_float(value: Any) -> float | None:
    """Parse a numeric cell, preserving None for absent/blank values."""
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


ENDPOINTS: dict[Category, EndpointSpec] = {
    Category.PREDICTION_MARKETS: EndpointSpec(
        capability=Category.PREDICTION_MARKETS,
        method="GET",
        url=f"{_BASE_URL}/markets",
        params={"limit": "50", "closed": "false", "order": "volume", "ascending": "false"},
    ),
}
