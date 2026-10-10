# finrobot/engine/data/providers/gdelt_provider.py
"""GDELT DOC 2.0 news-sentiment provider (keyless).

Backed by the GDELT DOC 2.0 full-text search API at
https://api.gdeltproject.org/api/v2/doc/doc. Serves ``news_sentiment`` only:
``fetch`` runs the ``ticker`` as a search query and returns the matching
article list (ArtList) plus the average-tone timeline (TimelineTone). No
credential; the API searches a rolling window of the last 3 months.
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

_BASE_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
_TIMEOUT = 15.0
_MIN_INTERVAL = 1.0
_DEFAULT_MAX_RECORDS = 75
_MAX_MAX_RECORDS = 250
_DEFAULT_TIMESPAN = "1week"
_SUPPORTED: list[str | DataType] = [Category.NEWS_SENTIMENT]

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


class GdeltProvider(DataProvider):
    """DataProvider backed by the GDELT DOC 2.0 API.

    Provides news coverage and tone (``news_sentiment``) from
    https://api.gdeltproject.org/api/v2/doc/doc. No API key required.
    """

    def __init__(self) -> None:
        # Reuse one AsyncClient across the session to amortise TLS handshakes.
        self._client = httpx.AsyncClient(timeout=_TIMEOUT)

    @property
    def name(self) -> str:
        return "gdelt"

    def capabilities(self) -> list[str | DataType]:
        return list(_SUPPORTED)

    async def fetch(self, ticker: str, data_type: str | DataType, **kwargs: Any) -> DataResult:
        if data_type not in _SUPPORTED:
            raise ProviderError(
                f"data_type '{data_type}' is not supported by GDELT. Supported: {_SUPPORTED}"
            )
        query = (ticker or str(kwargs.get("query") or "")).strip()
        if not query:
            raise ProviderError("GDELT requires a non-empty search query")
        max_records = _clamp_records(kwargs.get("maxrecords", _DEFAULT_MAX_RECORDS))
        timespan = str(kwargs.get("timespan") or _DEFAULT_TIMESPAN)
        try:
            articles = _parse_articles(
                await self._get(
                    {
                        "query": query,
                        "mode": "artlist",
                        "format": "json",
                        "maxrecords": max_records,
                        "timespan": timespan,
                        "sort": "datedesc",
                    }
                )
            )
            tone = _parse_tone(
                await self._get(
                    {
                        "query": query,
                        "mode": "timelinetone",
                        "format": "json",
                        "timespan": timespan,
                    }
                )
            )
        except httpx.TimeoutException as e:
            raise ProviderError(f"GDELT timeout for '{query}'") from e
        except httpx.HTTPStatusError as e:
            raise _classify_http_error(e, query) from e
        except (
            httpx.ConnectError,
            httpx.RemoteProtocolError,
            httpx.ReadError,
            httpx.WriteError,
        ) as e:
            raise ProviderError(f"GDELT network error for '{query}' ({type(e).__name__})") from e
        except ProviderError:
            raise
        except (ValueError, KeyError, TypeError, AttributeError) as e:
            raise ProviderError(f"GDELT fetch failed for '{query}' ({type(e).__name__})") from e

        return DataResult(
            data={"query": query, "articles": articles, "tone_timeline": tone},
            provider=self.name,
            ticker=ticker,
            data_type=data_type,
            timestamp=datetime.now(tz=timezone.utc),
        )

    async def _get(self, params: dict[str, Any]) -> dict[str, Any]:
        """GET the DOC 2.0 endpoint; an empty (zero-result) body is a valid empty dict."""
        resp = await self._client.get(_BASE_URL, params=params)
        resp.raise_for_status()
        if not resp.text.strip():
            return {}
        try:
            payload = resp.json()
        except ValueError as e:
            raise ProviderError("GDELT returned a non-JSON response") from e
        if not isinstance(payload, dict):
            raise ProviderError("GDELT returned a non-object JSON payload")
        return payload

    async def close(self) -> None:
        """Release the shared httpx client. Called from DataLayer.close()."""
        await self._client.aclose()


def _clamp_records(value: Any) -> str:
    """Clamp a requested record count to GDELT's 1..250 range."""
    try:
        count = int(value)
    except (TypeError, ValueError):
        count = _DEFAULT_MAX_RECORDS
    return str(max(1, min(_MAX_MAX_RECORDS, count)))


def _parse_articles(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalise the ArtList ``articles`` array; absent fields stay None."""
    raw = payload.get("articles")
    articles: list[dict[str, Any]] = []
    for row in raw if isinstance(raw, list) else []:
        if not isinstance(row, dict):
            continue
        articles.append(
            {
                "title": row.get("title"),
                "url": row.get("url"),
                "domain": row.get("domain"),
                "published": row.get("seendate"),
                "language": row.get("language"),
                "source_country": row.get("sourcecountry"),
            }
        )
    return articles


def _parse_tone(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalise the TimelineTone series into ``{date, tone}`` points."""
    timeline = payload.get("timeline")
    if not isinstance(timeline, list) or not timeline:
        return []
    series = timeline[0]
    if not isinstance(series, dict):
        return []
    raw = series.get("data")
    points: list[dict[str, Any]] = []
    for row in raw if isinstance(raw, list) else []:
        if not isinstance(row, dict):
            continue
        points.append({"date": row.get("date"), "tone": _optional_float(row.get("value"))})
    return points


def _classify_http_error(exc: httpx.HTTPStatusError, query: str) -> ProviderError:
    """Map a GDELT HTTP failure onto the typed taxonomy (no request URL in messages)."""
    status = exc.response.status_code
    if status == 429:
        return RateLimitedProviderError(f"GDELT rate limited (HTTP 429) for '{query}'")
    if status == 403 and _is_plan_gate(exc.response):
        return ProviderPlanError(f"GDELT endpoint gated upstream (HTTP 403) for '{query}'")
    return ProviderError(f"GDELT API error for '{query}' (HTTP {status})")


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
    Category.NEWS_SENTIMENT: EndpointSpec(
        capability=Category.NEWS_SENTIMENT,
        method="GET",
        url=_BASE_URL,
        params={
            "query": "finance",
            "mode": "artlist",
            "format": "json",
            "maxrecords": "75",
            "timespan": _DEFAULT_TIMESPAN,
        },
    ),
}
