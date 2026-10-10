"""NewsAPI.org DataProvider adapter.

Serves article search from https://newsapi.org/v2 (the ``/everything``
endpoint). Requests authenticate with the ``X-Api-Key`` header. API key
required — set ``NEWSAPI_API_KEY``.
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

_BASE_URL = "https://newsapi.org/v2"
_TIMEOUT = 15.0

#: Categories this provider serves (from the owner's priority table).
_CATEGORIES: list[Category] = [Category.NEWS_DATA]

# Plan/entitlement markers in an error body → ProviderPlanError (deterministic
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

#: Declarative catalog row; auth is header-based, so ``$KEY`` lives in
#: ``auth_header`` rather than in ``params``.
ENDPOINTS: dict[Category, EndpointSpec] = {
    Category.NEWS_DATA: EndpointSpec(
        Category.NEWS_DATA,
        "GET",
        f"{_BASE_URL}/everything",
        {"q": "{ticker}", "sortBy": "publishedAt", "language": "en", "pageSize": "50"},
        auth_header="X-Api-Key",
    ),
}


def _classify_http_error(exc: httpx.HTTPStatusError, ticker: str) -> ProviderError:
    """Map an httpx HTTP error to a typed ProviderError.

    The message never interpolates the raw exception or the request URL (which
    carries the live key).
    """
    status = exc.response.status_code
    if status == 429:
        return RateLimitedProviderError(f"NewsAPI rate limited (HTTP 429) for '{ticker}'")
    if status == 403:
        try:
            body = exc.response.text.lower()
        except (httpx.ResponseNotRead, UnicodeDecodeError):
            body = ""
        if any(marker in body for marker in _PLAN_MARKERS):
            return ProviderPlanError(f"NewsAPI plan/entitlement gate (HTTP 403) for '{ticker}'")
    return ProviderError(f"NewsAPI error for '{ticker}' (HTTP {status})")


class NewsApiProvider(DataProvider):
    """DataProvider backed by NewsAPI.org (https://newsapi.org/v2).

    Serves general article search via ``/everything``. API key required — set
    ``NEWSAPI_API_KEY``.
    """

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        # Reuse one AsyncClient across the session to amortise TLS handshakes.
        self._client = httpx.AsyncClient(timeout=_TIMEOUT)

    @property
    def name(self) -> str:
        return "newsapi"

    def capabilities(self) -> list[str | DataType | Category]:
        return list(_CATEGORIES)

    async def fetch(self, ticker: str, data_type: str | DataType, **kwargs: Any) -> DataResult:
        category = self._resolve_category(data_type)
        if category != Category.NEWS_DATA:
            raise ProviderError(
                f"data_type '{data_type}' is not supported by NewsAPI. "
                f"Supported: {list(_CATEGORIES)}"
            )
        try:
            items = await self._fetch_news(ticker)
        except httpx.TimeoutException as e:
            raise ProviderError(f"NewsAPI timeout for '{ticker}'") from e
        except httpx.HTTPStatusError as e:
            raise _classify_http_error(e, ticker) from e
        except (
            httpx.ConnectError,
            httpx.RemoteProtocolError,
            httpx.ReadError,
            httpx.WriteError,
        ) as e:
            raise ProviderError(f"NewsAPI network error for '{ticker}' ({type(e).__name__})") from e
        except ProviderError:
            raise
        except (ValueError, KeyError, TypeError, AttributeError) as e:
            raise ProviderError(f"NewsAPI fetch failed for '{ticker}' ({type(e).__name__})") from e

        return DataResult(
            data={"news_items": items},
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

    async def _fetch_news(self, ticker: str) -> list[dict[str, Any]]:
        """Fetch articles matching ``ticker`` from ``/everything`` (newest first)."""
        params = {
            "q": ticker,
            "sortBy": "publishedAt",
            "language": "en",
            "pageSize": "50",
        }
        payload = (await self._get("/everything", params=params)).json()
        articles = payload.get("articles") if isinstance(payload, dict) else None
        if not isinstance(articles, list):
            # A key-free server message, when present, explains the empty body.
            message = payload.get("message") if isinstance(payload, dict) else None
            detail = f": {message}" if isinstance(message, str) and message else ""
            raise ProviderError(f"NewsAPI returned no articles for '{ticker}'{detail}")

        items: list[dict[str, Any]] = []
        for article in articles:
            if not isinstance(article, dict):
                continue
            source = article.get("source")
            source_name = source.get("name") if isinstance(source, dict) else None
            items.append(
                {
                    "title": article.get("title") or "",
                    "source": source_name or "",
                    "url": article.get("url") or "",
                    "published": article.get("publishedAt") or "",
                }
            )
        return items

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> httpx.Response:
        """Authenticated GET against NewsAPI (key in the ``X-Api-Key`` header)."""
        headers = {"X-Api-Key": self._api_key}
        resp = await self._client.get(f"{_BASE_URL}{path}", params=params or {}, headers=headers)
        resp.raise_for_status()
        return resp

    async def close(self) -> None:
        """Release the shared httpx client. Called from DataLayer.close()."""
        await self._client.aclose()
