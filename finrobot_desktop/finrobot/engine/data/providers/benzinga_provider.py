"""Benzinga DataProvider adapter.

Serves Benzinga's news, calendar, and analyst feeds over the REST API at
https://api.benzinga.com/api. Requests authenticate with a query-string
``token`` and ask for JSON with an ``Accept: application/json`` header (the
default response format is XML). API key required — set ``BENZINGA_API_KEY``.
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

_BASE_URL = "https://api.benzinga.com/api"
_TIMEOUT = 15.0

#: Categories this provider serves (from the owner's priority table).
_CATEGORIES: list[Category] = [
    Category.NEWS_DATA,
    Category.ANALYST_RATINGS,
    Category.EARNINGS_CALENDAR,
    Category.CORPORATE_ACTIONS,
    Category.ANALYST_ACTIONS,
    Category.FDA_CALENDAR,
    Category.GUIDANCE_REVISIONS,
    Category.NEWS_RETRACTIONS,
    Category.OFFERINGS_CALENDAR,
]

# Plan/entitlement markers in a 403 body → ProviderPlanError (a deterministic
# capability gap, not provider ill-health). Key-free substrings only.
_PLAN_MARKERS: tuple[str, ...] = (
    "plan",
    "entitlement",
    "not entitled",
    "exclusive",
    "legacy",
    "subscription",
    "upgrade",
)

# Category → (path, ticker param name | None, upstream response key | None,
# output key). ``upstream_key`` is None when the body is a bare array; a None
# ticker param means the feed is not ticker-scoped (news retractions).
_ROUTES: dict[Category, tuple[str, str | None, str | None, str]] = {
    Category.NEWS_DATA: ("/v2/news", "tickers", None, "news_items"),
    Category.ANALYST_RATINGS: (
        "/v2.1/calendar/ratings",
        "parameters[tickers]",
        "ratings",
        "ratings",
    ),
    Category.EARNINGS_CALENDAR: (
        "/v2.1/calendar/earnings",
        "parameters[tickers]",
        "earnings",
        "earnings",
    ),
    Category.CORPORATE_ACTIONS: (
        "/v2.2/calendar/dividends",
        "parameters[tickers]",
        "dividends",
        "dividends",
    ),
    Category.ANALYST_ACTIONS: (
        "/v1/analyst/insights",
        "symbols",
        "analyst-insights",
        "analyst_actions",
    ),
    Category.FDA_CALENDAR: (
        "/v2.1/calendar/fda",
        "parameters[securities]",
        "fda",
        "fda_events",
    ),
    Category.GUIDANCE_REVISIONS: (
        "/v2.1/calendar/guidance",
        "parameters[tickers]",
        "guidance",
        "guidance",
    ),
    Category.NEWS_RETRACTIONS: ("/v2/news-removed", None, None, "news_retractions"),
    Category.OFFERINGS_CALENDAR: (
        "/v2.1/calendar/offerings",
        "parameters[tickers]",
        "offerings",
        "offerings",
    ),
}

#: Declarative catalog rows (the probe substitutes ``$KEY`` for the token and
#: ``{ticker}`` for the symbol). The adapter additionally sends the
#: ``Accept: application/json`` header that EndpointSpec cannot express.
ENDPOINTS: dict[Category, EndpointSpec] = {
    Category.NEWS_DATA: EndpointSpec(
        Category.NEWS_DATA,
        "GET",
        f"{_BASE_URL}/v2/news",
        {"tickers": "{ticker}", "pageSize": "15", "token": "$KEY"},
    ),
    Category.ANALYST_RATINGS: EndpointSpec(
        Category.ANALYST_RATINGS,
        "GET",
        f"{_BASE_URL}/v2.1/calendar/ratings",
        {"parameters[tickers]": "{ticker}", "token": "$KEY"},
    ),
    Category.EARNINGS_CALENDAR: EndpointSpec(
        Category.EARNINGS_CALENDAR,
        "GET",
        f"{_BASE_URL}/v2.1/calendar/earnings",
        {"parameters[tickers]": "{ticker}", "token": "$KEY"},
    ),
    Category.CORPORATE_ACTIONS: EndpointSpec(
        Category.CORPORATE_ACTIONS,
        "GET",
        f"{_BASE_URL}/v2.2/calendar/dividends",
        {"parameters[tickers]": "{ticker}", "token": "$KEY"},
    ),
    Category.ANALYST_ACTIONS: EndpointSpec(
        Category.ANALYST_ACTIONS,
        "GET",
        f"{_BASE_URL}/v1/analyst/insights",
        {"symbols": "{ticker}", "token": "$KEY"},
    ),
    Category.FDA_CALENDAR: EndpointSpec(
        Category.FDA_CALENDAR,
        "GET",
        f"{_BASE_URL}/v2.1/calendar/fda",
        {"parameters[securities]": "{ticker}", "token": "$KEY"},
    ),
    Category.GUIDANCE_REVISIONS: EndpointSpec(
        Category.GUIDANCE_REVISIONS,
        "GET",
        f"{_BASE_URL}/v2.1/calendar/guidance",
        {"parameters[tickers]": "{ticker}", "token": "$KEY"},
    ),
    Category.NEWS_RETRACTIONS: EndpointSpec(
        Category.NEWS_RETRACTIONS,
        "GET",
        f"{_BASE_URL}/v2/news-removed",
        {"token": "$KEY"},
    ),
    Category.OFFERINGS_CALENDAR: EndpointSpec(
        Category.OFFERINGS_CALENDAR,
        "GET",
        f"{_BASE_URL}/v2.1/calendar/offerings",
        {"parameters[tickers]": "{ticker}", "token": "$KEY"},
    ),
}


def _classify_http_error(exc: httpx.HTTPStatusError, ticker: str) -> ProviderError:
    """Map an httpx HTTP error to a typed ProviderError.

    The message never interpolates the raw exception or the request URL (which
    carries the live token).
    """
    status = exc.response.status_code
    if status == 429:
        return RateLimitedProviderError(f"Benzinga rate limited (HTTP 429) for '{ticker}'")
    if status == 403:
        try:
            body = exc.response.text.lower()
        except (httpx.ResponseNotRead, UnicodeDecodeError):
            body = ""
        if any(marker in body for marker in _PLAN_MARKERS):
            return ProviderPlanError(f"Benzinga plan/entitlement gate (HTTP 403) for '{ticker}'")
    return ProviderError(f"Benzinga API error for '{ticker}' (HTTP {status})")


def _extract_list(payload: Any, upstream_key: str | None, out_key: str) -> list[dict[str, Any]]:
    """Pull the record array out of a Benzinga body without inventing records."""
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        if upstream_key is not None:
            value = payload.get(upstream_key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
            raise ProviderError(f"Benzinga response missing '{upstream_key}' for '{out_key}'")
        # Feeds without a fixed key (e.g. /v2/news-removed) return a map of
        # key -> array; collect every list value rather than fabricating one.
        collected: list[dict[str, Any]] = []
        for value in payload.values():
            if isinstance(value, list):
                collected.extend(item for item in value if isinstance(item, dict))
        if collected:
            return collected
    raise ProviderError(f"Benzinga returned an unexpected payload for '{out_key}'")


class BenzingaProvider(DataProvider):
    """DataProvider backed by the Benzinga API (https://api.benzinga.com/api).

    Serves news, analyst ratings/actions, earnings, dividends, FDA, guidance,
    and offerings calendars. API key required — set ``BENZINGA_API_KEY``.
    """

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        # Reuse one AsyncClient across the session to amortise TLS handshakes.
        self._client = httpx.AsyncClient(timeout=_TIMEOUT)

    @property
    def name(self) -> str:
        return "benzinga"

    def capabilities(self) -> list[str | DataType | Category]:
        return list(_CATEGORIES)

    async def fetch(self, ticker: str, data_type: str | DataType, **kwargs: Any) -> DataResult:
        category = self._resolve_category(data_type)
        if category is None or category not in _CATEGORIES:
            raise ProviderError(
                f"data_type '{data_type}' is not supported by Benzinga. "
                f"Supported: {list(_CATEGORIES)}"
            )
        try:
            data = await self._fetch_category(category, ticker)
        except httpx.TimeoutException as e:
            raise ProviderError(f"Benzinga timeout for '{ticker}'") from e
        except httpx.HTTPStatusError as e:
            raise _classify_http_error(e, ticker) from e
        except (
            httpx.ConnectError,
            httpx.RemoteProtocolError,
            httpx.ReadError,
            httpx.WriteError,
        ) as e:
            raise ProviderError(
                f"Benzinga network error for '{ticker}' ({type(e).__name__})"
            ) from e
        except ProviderError:
            raise
        except (ValueError, KeyError, TypeError, AttributeError) as e:
            raise ProviderError(f"Benzinga fetch failed for '{ticker}' ({type(e).__name__})") from e

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

    async def _fetch_category(self, category: Category, ticker: str) -> dict[str, Any]:
        path, param_name, upstream_key, out_key = _ROUTES[category]
        params: dict[str, str] = {param_name: ticker} if param_name else {}
        payload = (await self._get(path, params=params)).json()
        return {out_key: _extract_list(payload, upstream_key, out_key)}

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> httpx.Response:
        """Authenticated GET against the Benzinga API (JSON via Accept header)."""
        merged = dict(params or {})
        merged["token"] = self._api_key
        headers = {"Accept": "application/json"}
        resp = await self._client.get(f"{_BASE_URL}{path}", params=merged, headers=headers)
        resp.raise_for_status()
        return resp

    async def close(self) -> None:
        """Release the shared httpx client. Called from DataLayer.close()."""
        await self._client.aclose()
