# finrobot/engine/data/providers/cboe_provider.py
"""Cboe delayed-quote options-surface provider (keyless).

Backed by the public Cboe delayed quotes CDN at https://cdn.cboe.com. Serves
``options_surface`` only: ``fetch`` pulls the (roughly 15-minute delayed) full
option chain JSON for one underlying and returns its contracts with bid/ask,
implied vol, open interest and greeks. No credential.

Index option chains use an underscore-prefixed index symbol, e.g.
``/api/global/delayed_quotes/options/_SPX.json``.
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

_BASE_URL = "https://cdn.cboe.com"
_OPTIONS_PATH = "/api/global/delayed_quotes/options/{symbol}.json"
_TIMEOUT = 15.0
_MIN_INTERVAL = 0.5
_SUPPORTED: list[str | DataType] = [Category.OPTIONS_SURFACE]

# Cboe publishes index option chains under an underscore-prefixed root.
_INDEX_SYMBOLS: frozenset[str] = frozenset(
    {
        "SPX",
        "SPXW",
        "SPXPM",
        "NDX",
        "NDXP",
        "RUT",
        "RUTW",
        "VIX",
        "XSP",
        "DJX",
        "OEX",
        "MXEA",
        "MXEF",
    }
)

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


class CboeProvider(DataProvider):
    """DataProvider backed by Cboe's public delayed-quote option chains.

    Provides index/equity option surfaces (``options_surface``) from
    https://cdn.cboe.com, roughly 15 minutes delayed. No API key required.
    """

    def __init__(self) -> None:
        # follow_redirects: cdn.cboe.com 302s to cdn-api.cboe.com for chain JSON.
        self._client = httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True)

    @property
    def name(self) -> str:
        return "cboe"

    def capabilities(self) -> list[str | DataType]:
        return list(_SUPPORTED)

    async def fetch(self, ticker: str, data_type: str | DataType, **kwargs: Any) -> DataResult:
        if data_type not in _SUPPORTED:
            raise ProviderError(
                f"data_type '{data_type}' is not supported by Cboe. Supported: {_SUPPORTED}"
            )
        try:
            data = await self._fetch_surface(ticker)
        except httpx.TimeoutException as e:
            raise ProviderError(f"Cboe timeout for '{ticker}'") from e
        except httpx.HTTPStatusError as e:
            raise _classify_http_error(e, ticker) from e
        except (
            httpx.ConnectError,
            httpx.RemoteProtocolError,
            httpx.ReadError,
            httpx.WriteError,
        ) as e:
            raise ProviderError(f"Cboe network error for '{ticker}' ({type(e).__name__})") from e
        except ProviderError:
            raise
        except (ValueError, KeyError, TypeError, AttributeError) as e:
            raise ProviderError(f"Cboe fetch failed for '{ticker}' ({type(e).__name__})") from e

        return DataResult(
            data=data,
            provider=self.name,
            ticker=ticker,
            data_type=data_type,
            timestamp=datetime.now(tz=timezone.utc),
        )

    async def _fetch_surface(self, ticker: str) -> dict[str, Any]:
        """Fetch the delayed option chain for one underlying."""
        symbol = _normalize_symbol(ticker)
        resp = await self._get(_OPTIONS_PATH.format(symbol=symbol))
        payload = resp.json()
        if not isinstance(payload, dict):
            raise ProviderError(f"Cboe returned an unexpected payload for '{symbol}'")
        block = payload.get("data")
        if not isinstance(block, dict):
            raise ProviderError(f"Cboe chain response had no 'data' block for '{symbol}'")
        raw = block.get("options")
        contracts: list[dict[str, Any]] = []
        for row in raw if isinstance(raw, list) else []:
            if isinstance(row, dict):
                contracts.append(_parse_contract(row))
        if not contracts:
            raise ProviderError(f"Cboe returned no option contracts for '{symbol}'")
        return {
            "underlying": symbol.lstrip("_"),
            "timestamp": payload.get("timestamp"),
            "contracts": contracts,
        }

    async def _get(self, path: str) -> httpx.Response:
        """GET ``path`` on the Cboe CDN."""
        resp = await self._client.get(f"{_BASE_URL}{path}")
        resp.raise_for_status()
        return resp

    async def close(self) -> None:
        """Release the shared httpx client. Called from DataLayer.close()."""
        await self._client.aclose()


def _normalize_symbol(ticker: str) -> str:
    """Map a user ticker to Cboe's chain root (index roots are ``_``-prefixed)."""
    raw = (ticker or "").strip().upper()
    if raw.startswith("^"):
        raw = raw[1:]
    if not raw:
        raise ProviderError("Cboe requires a non-empty underlying symbol")
    if raw.startswith("_"):
        return raw
    if raw in _INDEX_SYMBOLS:
        return f"_{raw}"
    return raw


def _parse_contract(row: dict[str, Any]) -> dict[str, Any]:
    """Normalise one Cboe chain row; absent fields stay None (never a fake 0)."""
    code = row.get("option")
    parsed = _parse_occ(code) if isinstance(code, str) else None
    return {
        "option": code,
        "expiry": parsed["expiry"] if parsed else None,
        "type": parsed["type"] if parsed else None,
        "strike": parsed["strike"] if parsed else None,
        "bid": _optional_float(row.get("bid")),
        "ask": _optional_float(row.get("ask")),
        "iv": _optional_float(row.get("iv")),
        "open_interest": _optional_int(row.get("open_interest")),
        "volume": _optional_int(row.get("volume")),
        "delta": _optional_float(row.get("delta")),
        "gamma": _optional_float(row.get("gamma")),
        "vega": _optional_float(row.get("vega")),
        "theta": _optional_float(row.get("theta")),
    }


def _parse_occ(code: str) -> dict[str, Any] | None:
    """Decode an OCC option symbol ``<root><YYMMDD><C|P><strike*1000>`` into parts."""
    if len(code) < 15:
        return None
    strike_part = code[-8:]
    cp = code[-9]
    date_part = code[-15:-9]
    if cp not in ("C", "P") or not strike_part.isdigit() or not date_part.isdigit():
        return None
    strike = int(strike_part) / 1000.0
    year, month, day = int(date_part[0:2]), int(date_part[2:4]), int(date_part[4:6])
    return {
        "type": "call" if cp == "C" else "put",
        "strike": strike,
        "expiry": f"20{year:02d}-{month:02d}-{day:02d}",
    }


def _classify_http_error(exc: httpx.HTTPStatusError, ticker: str) -> ProviderError:
    """Map a Cboe HTTP failure onto the typed taxonomy (no request URL in messages)."""
    status = exc.response.status_code
    if status == 429:
        return RateLimitedProviderError(f"Cboe rate limited (HTTP 429) for '{ticker}'")
    if status == 403 and _is_plan_gate(exc.response):
        return ProviderPlanError(f"Cboe endpoint gated upstream (HTTP 403) for '{ticker}'")
    return ProviderError(f"Cboe API error for '{ticker}' (HTTP {status})")


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


def _optional_int(value: Any) -> int | None:
    """Parse an integer cell, preserving None for absent/blank values."""
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        parsed = _optional_float(value)
        return int(parsed) if parsed is not None else None


ENDPOINTS: dict[Category, EndpointSpec] = {
    Category.OPTIONS_SURFACE: EndpointSpec(
        capability=Category.OPTIONS_SURFACE,
        method="GET",
        url=f"{_BASE_URL}{_OPTIONS_PATH.format(symbol='_SPX')}",
        params={},
    ),
}
