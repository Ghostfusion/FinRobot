"""Alpha Vantage DataProvider adapter.

Serves news/sentiment, company fundamentals, and technical indicators from the
Alpha Vantage REST API at https://www.alphavantage.co/query. Requests
authenticate with the ``apikey`` query parameter. API key required — set
``ALPHAVANTAGE_API_KEY``.

Alpha Vantage answers HTTP 200 with a ``Note`` / ``Information`` /
``Error Message`` body for invalid keys or rate limits (never a 4xx status), so
the adapter inspects the parsed body and raises the matching typed error.
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
    RateLimitedProviderError,
)
from finrobot.engine.data.types import DataType

_BASE_URL = "https://www.alphavantage.co/query"
_TIMEOUT = 15.0

#: Categories this provider serves (from the owner's priority table).
_CATEGORIES: list[Category] = [
    Category.NEWS_DATA,
    Category.NEWS_SENTIMENT,
    Category.FUNDAMENTAL_DATA,
    Category.TECHNICAL_INDICATORS,
]

# Substrings in an HTTP-200 note body that mark upstream throttling. Matches the
# data layer's shared rate-limit vocabulary plus Alpha Vantage's own wording.
_AV_RATE_MARKERS: tuple[str, ...] = (
    "429",
    "too many requests",
    "rate limit",
    "rate-limit",
    "throttl",
    "requests per day",
    "requests per minute",
)

#: Declarative catalog rows; the credential rides in the ``apikey`` param.
ENDPOINTS: dict[Category, EndpointSpec] = {
    Category.NEWS_DATA: EndpointSpec(
        Category.NEWS_DATA,
        "GET",
        _BASE_URL,
        {"function": "NEWS_SENTIMENT", "tickers": "{ticker}", "limit": "50", "apikey": "$KEY"},
    ),
    Category.NEWS_SENTIMENT: EndpointSpec(
        Category.NEWS_SENTIMENT,
        "GET",
        _BASE_URL,
        {"function": "NEWS_SENTIMENT", "tickers": "{ticker}", "limit": "50", "apikey": "$KEY"},
    ),
    Category.FUNDAMENTAL_DATA: EndpointSpec(
        Category.FUNDAMENTAL_DATA,
        "GET",
        _BASE_URL,
        {"function": "OVERVIEW", "symbol": "{ticker}", "apikey": "$KEY"},
    ),
    Category.TECHNICAL_INDICATORS: EndpointSpec(
        Category.TECHNICAL_INDICATORS,
        "GET",
        _BASE_URL,
        {
            "function": "RSI",
            "symbol": "{ticker}",
            "interval": "daily",
            "time_period": "14",
            "series_type": "close",
            "apikey": "$KEY",
        },
    ),
}


class AlphaVantageProvider(DataProvider):
    """DataProvider backed by Alpha Vantage (https://www.alphavantage.co/query).

    Serves market news + sentiment, company overview fundamentals, and
    technical indicators. API key required — set ``ALPHAVANTAGE_API_KEY``.
    """

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        # Reuse one AsyncClient across the session to amortise TLS handshakes.
        self._client = httpx.AsyncClient(timeout=_TIMEOUT)

    @property
    def name(self) -> str:
        return "alpha_vantage"

    def capabilities(self) -> list[str | DataType | Category]:
        return list(_CATEGORIES)

    async def fetch(self, ticker: str, data_type: str | DataType, **kwargs: Any) -> DataResult:
        category = self._resolve_category(data_type)
        if category is None or category not in _CATEGORIES:
            raise ProviderError(
                f"data_type '{data_type}' is not supported by Alpha Vantage. "
                f"Supported: {list(_CATEGORIES)}"
            )
        try:
            data: dict[str, Any]
            if category in (Category.NEWS_DATA, Category.NEWS_SENTIMENT):
                data = {"news_items": await self._fetch_news(ticker)}
            elif category == Category.FUNDAMENTAL_DATA:
                data = {"fundamental": await self._fetch_overview(ticker)}
            else:
                data = {"technical_indicators": await self._fetch_rsi(ticker)}
        except httpx.TimeoutException as e:
            raise ProviderError(f"Alpha Vantage timeout for '{ticker}'") from e
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise RateLimitedProviderError(
                    f"Alpha Vantage rate limited (HTTP 429) for '{ticker}'"
                ) from e
            raise ProviderError(
                f"Alpha Vantage API error for '{ticker}' (HTTP {e.response.status_code})"
            ) from e
        except (
            httpx.ConnectError,
            httpx.RemoteProtocolError,
            httpx.ReadError,
            httpx.WriteError,
        ) as e:
            raise ProviderError(
                f"Alpha Vantage network error for '{ticker}' ({type(e).__name__})"
            ) from e
        except ProviderError:
            raise
        except (ValueError, KeyError, TypeError, AttributeError) as e:
            raise ProviderError(
                f"Alpha Vantage fetch failed for '{ticker}' ({type(e).__name__})"
            ) from e

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

    def _raise_av_note(self, data: Any) -> None:
        """Raise the typed error carried by an Alpha Vantage HTTP-200 note body.

        The note text is surfaced only after the live key is redacted, so a body
        that echoes the credential cannot leak it.
        """
        if not isinstance(data, dict):
            return
        note = data.get("Note") or data.get("Information") or data.get("Error Message")
        if not note:
            return
        text = str(note)
        if self._api_key:
            text = text.replace(self._api_key, "***")
        if any(marker in text.lower() for marker in _AV_RATE_MARKERS):
            raise RateLimitedProviderError(f"Alpha Vantage: {text}")
        raise ProviderError(f"Alpha Vantage: {text}")

    async def _fetch_news(self, ticker: str) -> list[dict[str, Any]]:
        """Fetch news + per-ticker sentiment from the NEWS_SENTIMENT function."""
        params = {
            "function": "NEWS_SENTIMENT",
            "tickers": ticker,
            "limit": "50",
            "sort": "LATEST",
        }
        payload = (await self._get(params)).json()
        self._raise_av_note(payload)
        if not isinstance(payload, dict) or not isinstance(payload.get("feed"), list):
            raise ProviderError(f"Alpha Vantage returned no news feed for '{ticker}'")

        items: list[dict[str, Any]] = []
        for article in payload["feed"]:
            if not isinstance(article, dict):
                continue
            title = str(article.get("title") or "").strip()
            if not title:
                continue
            items.append(
                {
                    "title": title,
                    "source": article.get("source") or "Alpha Vantage",
                    "url": article.get("url") or "",
                    "published": self._parse_av_date(article.get("time_published")),
                    "sentiment_score": self._ticker_sentiment(article, ticker),
                    "category": article.get("category_within_source"),
                }
            )
        return items

    async def _fetch_overview(self, ticker: str) -> dict[str, Any]:
        """Fetch the company overview fundamentals from the OVERVIEW function."""
        payload = (await self._get({"function": "OVERVIEW", "symbol": ticker})).json()
        self._raise_av_note(payload)
        if not isinstance(payload, dict) or "Symbol" not in payload:
            raise ProviderError(f"Alpha Vantage returned no overview for '{ticker}'")
        return payload

    async def _fetch_rsi(self, ticker: str) -> dict[str, Any]:
        """Fetch the daily 14-period RSI from the RSI function."""
        params = {
            "function": "RSI",
            "symbol": ticker,
            "interval": "daily",
            "time_period": "14",
            "series_type": "close",
        }
        payload = (await self._get(params)).json()
        self._raise_av_note(payload)
        if not isinstance(payload, dict) or "Technical Analysis: RSI" not in payload:
            raise ProviderError(f"Alpha Vantage returned no RSI series for '{ticker}'")
        return payload

    @staticmethod
    def _ticker_sentiment(article: dict[str, Any], ticker: str) -> float | None:
        """Per-ticker sentiment score from ``ticker_sentiment``; None when absent."""
        for entry in article.get("ticker_sentiment") or []:
            if not isinstance(entry, dict):
                continue
            if str(entry.get("ticker", "")).upper() == ticker.upper():
                raw = entry.get("ticker_sentiment_score")
                if raw is None:
                    return None
                try:
                    return float(raw)
                except (ValueError, TypeError):
                    return None
        return None

    @staticmethod
    def _parse_av_date(date_str: Any) -> str:
        """Parse Alpha Vantage ``YYYYMMDDTHHmmss`` to ISO; "" when unknown."""
        if not date_str:
            return ""
        try:
            dt = datetime.strptime(str(date_str), "%Y%m%dT%H%M%S")
        except (ValueError, TypeError):
            return ""
        return dt.replace(tzinfo=timezone.utc).isoformat()

    async def _get(self, params: dict[str, Any]) -> httpx.Response:
        """Authenticated GET against Alpha Vantage (key in the ``apikey`` param)."""
        merged = dict(params)
        merged["apikey"] = self._api_key
        resp = await self._client.get(_BASE_URL, params=merged)
        resp.raise_for_status()
        return resp

    async def close(self) -> None:
        """Release the shared httpx client. Called from DataLayer.close()."""
        await self._client.aclose()
