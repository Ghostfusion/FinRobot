# finrobot/engine/data/providers/moomoo_provider.py
"""MoomooProvider — Data Layer v3 adapter for the local moomoo OpenD gateway.

Transport is NOT HTTP: it talks to the locally installed **OpenD** daemon through
the ``moomoo-api`` Python SDK (``OpenQuoteContext(host, port)``), the SDK
documented at https://openapi.moomoo.com. ``build_provider`` only constructs this
adapter when a TCP probe of ``MOOMOO_HOST:MOOMOO_PORT`` succeeds, and the SDK
import is lazy/guarded here as well — so a machine without ``moomoo-api``
installed degrades exactly like "OpenD is down": a plain ``ProviderError`` that
the failover chain skips.

No credential is read or stored: only the gateway host/port. The moomoo password
is NEVER touched — OpenD owns the session and must already be logged in.
"""

from __future__ import annotations

import asyncio
import contextlib
import importlib
import math
from datetime import date, datetime, timezone
from typing import Any, NoReturn

from finrobot.engine.data.categories import Category, category_of
from finrobot.engine.data.catalog import EndpointSpec
from finrobot.engine.data.interface import (
    DataProvider,
    DataResult,
    ProviderError,
    ProviderPlanError,
    RateLimitedProviderError,
    is_rate_limit_error,
)
from finrobot.engine.data.types import DataType

#: SDK return code for success (``moomoo.RET_OK``) — constants live in the
#: optional SDK, so the value is inlined rather than imported at module scope.
_RET_OK = 0
#: Cap on an upstream SDK error string echoed into a ProviderError message.
_MAX_ERR_CHARS = 200

#: Substrings marking an OpenD *entitlement* gate (quote right / plan) rather
#: than throttling — the moomoo analogue of FMP/Finnhub's HTTP-403 "exclusive
#: endpoint" body. A deterministic capability gap: fall through WITHOUT
#: charging the circuit breaker.
_PLAN_MARKERS: tuple[str, ...] = (
    "no permission",
    "permission",
    "no right",
    "quote right",
    "not authorized",
    "unauthorized",
    "entitlement",
    "subscribe",
)

#: Market prefixes understood by the SDK's ``<MARKET>.<SYMBOL>`` code format.
_MARKETS = frozenset({"US", "HK", "SH", "SZ", "SG", "JP", "AU", "CA", "MY", "CC", "EC", "FX"})

#: SDK placeholders for "no value" — treated as absent, never as a fake 0.
_MISSING = frozenset({"", "n/a", "na", "null", "none", "-", "--"})

#: Categories this provider serves. Transcribed from the owner's priority table
#: (``docs/DATA_PROVIDERS_V3_DESIGN.md`` §5.2): the moomoo-owned single-vendor
#: rows plus the fallback rows where it appears.
_CATEGORIES: tuple[Category, ...] = (
    Category.CORE_STOCK_APIS,
    Category.TECHNICAL_INDICATORS,
    Category.OPTIONS_DATA,
    Category.SHORT_INTEREST,
    Category.INSTITUTION_DATA,
    Category.MACRO_DATA,
    Category.PREDICTION_MARKETS,
    Category.CORPORATE_ACTIONS,
    Category.CAPITAL_FLOW,
    Category.EARNINGS_CATALYST,
    Category.EARNINGS_SURPRISE,
    Category.ECONOMIC_CALENDAR,
    Category.EXPECTED_MOVE,
    Category.FED_WATCH,
    Category.MARKET_BREADTH,
    Category.REVENUE_BREAKDOWN,
    Category.SMART_MONEY,
    Category.ANALYST_RATINGS,
    Category.EARNINGS_CALENDAR,
)


def _ep(capability: Category, sdk_method: str) -> EndpointSpec:
    """One gateway catalog row.

    The ``moomoo://`` pseudo-URL names the SDK method the probe should exercise;
    there is no HTTP request and no credential placeholder (OpenD auth is out of
    band), so ``params``/``auth_header`` stay empty.
    """
    return EndpointSpec(capability=capability, method="GET", url=f"moomoo://{sdk_method}")


#: Declared endpoints (probe input). Truthful: each row names a real
#: ``OpenQuoteContext`` method used by the matching handler below.
ENDPOINTS: dict[Category, EndpointSpec] = {
    Category.CORE_STOCK_APIS: _ep(Category.CORE_STOCK_APIS, "get_market_snapshot"),
    Category.TECHNICAL_INDICATORS: _ep(Category.TECHNICAL_INDICATORS, "get_cur_kline"),
    Category.OPTIONS_DATA: _ep(Category.OPTIONS_DATA, "get_option_chain"),
    Category.SHORT_INTEREST: _ep(Category.SHORT_INTEREST, "get_short_interest"),
    Category.INSTITUTION_DATA: _ep(Category.INSTITUTION_DATA, "get_shareholders_institutional"),
    Category.MACRO_DATA: _ep(Category.MACRO_DATA, "get_macro_indicator_list"),
    Category.PREDICTION_MARKETS: _ep(Category.PREDICTION_MARKETS, "get_event_contract_category"),
    Category.CORPORATE_ACTIONS: _ep(Category.CORPORATE_ACTIONS, "get_corporate_actions_dividends"),
    Category.CAPITAL_FLOW: _ep(Category.CAPITAL_FLOW, "get_capital_flow"),
    Category.EARNINGS_CATALYST: _ep(
        Category.EARNINGS_CATALYST, "get_financials_earnings_price_history"
    ),
    Category.EARNINGS_SURPRISE: _ep(
        Category.EARNINGS_SURPRISE, "get_financials_earnings_price_move"
    ),
    Category.ECONOMIC_CALENDAR: _ep(Category.ECONOMIC_CALENDAR, "get_economic_calendar"),
    Category.EXPECTED_MOVE: _ep(Category.EXPECTED_MOVE, "get_option_underlying_overview"),
    Category.FED_WATCH: _ep(Category.FED_WATCH, "get_fed_watch_target_rate"),
    Category.MARKET_BREADTH: _ep(Category.MARKET_BREADTH, "get_rise_fall_distribution"),
    Category.REVENUE_BREAKDOWN: _ep(Category.REVENUE_BREAKDOWN, "get_financials_revenue_breakdown"),
    Category.SMART_MONEY: _ep(Category.SMART_MONEY, "get_insider_trade_list"),
    Category.ANALYST_RATINGS: _ep(Category.ANALYST_RATINGS, "get_research_rating_summary"),
    Category.EARNINGS_CALENDAR: _ep(Category.EARNINGS_CALENDAR, "get_earnings_calendar"),
}


def _import_sdk() -> Any:
    """Lazily import the moomoo OpenAPI SDK.

    Tries the ``moomoo`` package first (``moomoo-api`` on PyPI) and falls back to
    ``futu`` (the upstream fork's import name). Raises ``ProviderError`` when
    neither is installed so an SDK-less box degrades like "OpenD down" instead of
    crashing at import time.
    """
    for module_name in ("moomoo", "futu"):
        try:
            return importlib.import_module(module_name)
        except ImportError:
            continue
    raise ProviderError("moomoo SDK unavailable (install the 'moomoo-api' package)")


def _split_result(result: Any) -> tuple[Any, Any]:
    """Split the SDK's ``(ret, data[, page_req_key])`` convention.

    A bare non-tuple payload is treated as a successful data value.
    """
    if isinstance(result, tuple) and result:
        data = result[1] if len(result) > 1 else None
        return result[0], data
    return _RET_OK, result


def _raise_sdk_error(method: str, data: Any) -> NoReturn:
    """Map an SDK ``ret != RET_OK`` payload to the typed provider errors.

    The payload never carries a credential (OpenD auth is out of band), but it is
    still truncated before echoing so a pathological upstream string can't bloat
    the message.
    """
    message = data if isinstance(data, str) else str(data)
    if is_rate_limit_error(ProviderError(message)):
        raise RateLimitedProviderError(f"moomoo {method} rate limited by OpenD")
    lowered = message.lower()
    if any(marker in lowered for marker in _PLAN_MARKERS):
        raise ProviderPlanError(f"moomoo {method} blocked by account entitlement")
    raise ProviderError(f"moomoo {method} error: {message[:_MAX_ERR_CHARS]}")


def _clean(value: Any) -> Any:
    """Normalise one SDK cell: NaN / blank placeholders become ``None``."""
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, str) and value.strip().lower() in _MISSING:
        return None
    return value


def _records(data: Any) -> list[dict[str, Any]]:
    """Normalise an SDK DataFrame / dict / record list to clean dicts.

    Fields whose value is missing (None / NaN / "N/A") are omitted — the adapter
    never fabricates a placeholder 0. Non-record payloads yield an empty list.
    """
    if data is None:
        return []
    to_dict = getattr(data, "to_dict", None)
    if callable(to_dict):
        try:
            raw: Any = to_dict(orient="records")
        except TypeError:
            raw = to_dict()
    else:
        raw = data
    if isinstance(raw, dict):
        raw = [raw]
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for record in raw:
        if not isinstance(record, dict):
            continue
        cleaned = {str(key): _clean(value) for key, value in record.items()}
        out.append({key: value for key, value in cleaned.items() if value is not None})
    return out


def _first(data: Any) -> dict[str, Any]:
    """First cleaned record of a single-row SDK payload, or ``{}``."""
    records = _records(data)
    return records[0] if records else {}


def _to_code(ticker: str, market: str | None = None) -> str:
    """Build the SDK's ``<MARKET>.<SYMBOL>`` code from a bare ticker.

    An input that already carries a known market prefix is passed through; no
    other dot-bearing symbol (e.g. ``BRK.B``) is mistaken for a prefixed code.
    """
    symbol = ticker.strip().upper()
    if "." in symbol and symbol.split(".", 1)[0] in _MARKETS:
        return symbol
    return f"{(market or 'US').upper()}.{symbol}"


def _market(kwargs: dict[str, Any]) -> str:
    """Requested market for market-scoped SDK calls (default ``US``)."""
    return str(kwargs.get("market") or "US").upper()


#: Category → handler method name. ``fetch`` resolves the requested data type to
#: a Category and dispatches here; a category absent from this map is unsupported.
_CATEGORY_HANDLERS: dict[Category, str] = {
    Category.CORE_STOCK_APIS: "_fetch_core_stock_apis",
    Category.TECHNICAL_INDICATORS: "_fetch_technical_indicators",
    Category.OPTIONS_DATA: "_fetch_options_data",
    Category.SHORT_INTEREST: "_fetch_short_interest",
    Category.INSTITUTION_DATA: "_fetch_institution_data",
    Category.MACRO_DATA: "_fetch_macro_data",
    Category.PREDICTION_MARKETS: "_fetch_prediction_markets",
    Category.CORPORATE_ACTIONS: "_fetch_corporate_actions",
    Category.CAPITAL_FLOW: "_fetch_capital_flow",
    Category.EARNINGS_CATALYST: "_fetch_earnings_catalyst",
    Category.EARNINGS_SURPRISE: "_fetch_earnings_surprise",
    Category.ECONOMIC_CALENDAR: "_fetch_economic_calendar",
    Category.EXPECTED_MOVE: "_fetch_expected_move",
    Category.FED_WATCH: "_fetch_fed_watch",
    Category.MARKET_BREADTH: "_fetch_market_breadth",
    Category.REVENUE_BREAKDOWN: "_fetch_revenue_breakdown",
    Category.SMART_MONEY: "_fetch_smart_money",
    Category.ANALYST_RATINGS: "_fetch_analyst_ratings",
    Category.EARNINGS_CALENDAR: "_fetch_earnings_calendar",
}


def _resolve_category(data_type: str | DataType) -> Category | None:
    """Map a requested data type (Category, DataType, or either's string) to a Category."""
    try:
        return Category(data_type)
    except ValueError:
        return category_of(data_type)


def _bars(frame: Any) -> list[dict[str, Any]]:
    """Kline frame → canonical ``price_history`` bars (oldest-first)."""
    bars: list[dict[str, Any]] = []
    for record in _records(frame):
        close = record.get("close")
        if close is None:
            continue
        bars.append(
            {
                "date": record.get("time_key"),
                "open": record.get("open"),
                "high": record.get("high"),
                "low": record.get("low"),
                "close": close,
                "volume": record.get("volume"),
            }
        )
    return bars


class MoomooProvider(DataProvider):
    """DataProvider backed by a local moomoo OpenD gateway.

    Reached through the optional ``moomoo-api`` SDK (imported lazily) at
    ``OpenQuoteContext(host, port)`` — see https://openapi.moomoo.com. The gateway
    must be installed, running, and already logged in; no API key or password is
    handled here. Every failing path raises ``ProviderError`` (or a typed
    subclass) so the failover chain moves on.
    """

    def __init__(self, host: str, port: int) -> None:
        self._host = host
        self._port = port
        # Lazily created on first successful call; None until then.
        self._ctx: Any | None = None
        # Serialises SDK access: the OpenD context is a single socket session and
        # is not safe for concurrent calls.
        self._lock = asyncio.Lock()

    @property
    def name(self) -> str:
        return "moomoo"

    def capabilities(self) -> list[str | DataType | Category]:
        return list(_CATEGORIES)

    async def fetch(self, ticker: str, data_type: str | DataType, **kwargs: Any) -> DataResult:
        category = _resolve_category(data_type)
        handler_name = _CATEGORY_HANDLERS.get(category) if category is not None else None
        if handler_name is None:
            supported = [cat.value for cat in _CATEGORIES]
            raise ProviderError(
                f"data_type '{data_type}' is not supported by moomoo. Supported: {supported}"
            )
        try:
            data = await getattr(self, handler_name)(ticker, data_type, **kwargs)
        except ProviderError:
            raise
        except (OSError, TimeoutError) as e:
            raise ProviderError(f"moomoo gateway transport error ({type(e).__name__})") from e
        except (ValueError, KeyError, TypeError, AttributeError) as e:
            raise ProviderError(f"moomoo fetch failed for '{ticker}' ({type(e).__name__})") from e
        return DataResult(
            data=data,
            provider=self.name,
            ticker=ticker,
            data_type=data_type,
            timestamp=datetime.now(tz=timezone.utc),
        )

    async def close(self) -> None:
        """Release the OpenD quote context, if one was opened. Best-effort."""
        context, self._ctx = self._ctx, None
        if context is None:
            return
        with contextlib.suppress(Exception):
            await asyncio.to_thread(context.close)

    # ── transport ─────────────────────────────────────────────────────────

    def _connect(self) -> Any:
        """Create the OpenD quote context (runs in a worker thread)."""
        sdk = _import_sdk()
        try:
            return sdk.OpenQuoteContext(host=self._host, port=self._port)
        except (OSError, RuntimeError, ValueError, TypeError, TimeoutError) as e:
            # e.g. connection refused / handshake rejected while OpenD is down.
            raise ProviderError(f"moomoo OpenD connect failed ({type(e).__name__})") from e

    @staticmethod
    def _invoke(context: Any, method: str, args: tuple[Any, ...], kwargs: dict[str, Any]) -> Any:
        """Call one SDK method (worker thread) and unwrap its ``(ret, data)``."""
        fn = getattr(context, method, None)
        if not callable(fn):
            raise ProviderError(f"moomoo SDK does not expose '{method}'")
        try:
            result = fn(*args, **kwargs)
        except ProviderError:
            raise
        except (OSError, TimeoutError) as e:
            raise ProviderError(f"moomoo {method} transport error ({type(e).__name__})") from e
        except (OSError, RuntimeError, ValueError, TypeError, TimeoutError) as e:
            raise ProviderError(f"moomoo {method} failed ({type(e).__name__})") from e
        ret, data = _split_result(result)
        if ret != _RET_OK:
            _raise_sdk_error(method, data)
        return data

    async def _call(self, method: str, *args: Any, **kwargs: Any) -> Any:
        """Serialised, thread-offloaded SDK call. Returns the unwrapped payload."""
        async with self._lock:
            if self._ctx is None:
                self._ctx = await asyncio.to_thread(self._connect)
            context = self._ctx
            return await asyncio.to_thread(self._invoke, context, method, args, kwargs)

    async def _kline(
        self, code: str, kwargs: dict[str, Any], default_num: int
    ) -> list[dict[str, Any]]:
        """Trailing daily bars via ``get_cur_kline`` (caller may override ``num_bars``)."""
        num = int(kwargs.get("num_bars") or default_num)
        return _bars(await self._call("get_cur_kline", code, num))

    # ── handlers ──────────────────────────────────────────────────────────

    async def _fetch_core_stock_apis(
        self, ticker: str, data_type: str | DataType, **kwargs: Any
    ) -> dict[str, Any]:
        """Snapshot + daily OHLC (US/HK listings) for price/quote/profile types."""
        code = _to_code(ticker, kwargs.get("market"))
        if data_type == DataType.PROFILE:
            info = _first(await self._call("get_stock_basicinfo", _market(kwargs), "STOCK", [code]))
            profile = _first(await self._call("get_company_profile", code))
            return {**info, **profile}
        if data_type == DataType.PRICE_RANGE:
            frame = await self._call(
                "request_history_kline",
                code,
                kwargs.get("start"),
                kwargs.get("end"),
            )
            return {"price_history": _bars(frame)}
        snapshot = _first(await self._call("get_market_snapshot", [code]))
        price = snapshot.get("last_price")
        if price is None:
            raise ProviderError(f"moomoo returned no snapshot price for '{ticker}'")
        if data_type == DataType.QUOTE:
            return {"price": price}
        return {"current_price": price, "price_history": await self._kline(code, kwargs, 260)}

    async def _fetch_technical_indicators(
        self, ticker: str, data_type: str | DataType, **kwargs: Any
    ) -> dict[str, Any]:
        """Daily OHLC series the indicator layer derives from."""
        code = _to_code(ticker, kwargs.get("market"))
        return {"price_history": await self._kline(code, kwargs, 260)}

    async def _fetch_options_data(
        self, ticker: str, data_type: str | DataType, **kwargs: Any
    ) -> dict[str, Any]:
        """Option chain for the underlying."""
        code = _to_code(ticker, kwargs.get("market"))
        return {"option_chain": _records(await self._call("get_option_chain", code))}

    async def _fetch_short_interest(
        self, ticker: str, data_type: str | DataType, **kwargs: Any
    ) -> dict[str, Any]:
        """Short-interest history."""
        code = _to_code(ticker, kwargs.get("market"))
        return {"short_interest": _records(await self._call("get_short_interest", code))}

    async def _fetch_institution_data(
        self, ticker: str, data_type: str | DataType, **kwargs: Any
    ) -> dict[str, Any]:
        """Institutional shareholder holdings."""
        code = _to_code(ticker, kwargs.get("market"))
        frame = await self._call("get_shareholders_institutional", code)
        return {"institutional_holders": _records(frame)}

    async def _fetch_macro_data(
        self, ticker: str, data_type: str | DataType, **kwargs: Any
    ) -> dict[str, Any]:
        """Macro indicator catalogue, plus history when ``indicator_id`` is given."""
        data: dict[str, Any] = {
            "macro_indicators": _records(
                await self._call("get_macro_indicator_list", str(kwargs.get("region") or "US"))
            )
        }
        indicator_id = kwargs.get("indicator_id")
        if indicator_id:
            history = await self._call("get_macro_indicator_history", str(indicator_id))
            data["macro_indicator_history"] = _records(history)
        return data

    async def _fetch_prediction_markets(
        self, ticker: str, data_type: str | DataType, **kwargs: Any
    ) -> dict[str, Any]:
        """Event-contract categories, plus one series' events when ``series_code`` is given."""
        data: dict[str, Any] = {
            "event_categories": _records(await self._call("get_event_contract_category"))
        }
        series_code = kwargs.get("series_code")
        if series_code:
            events = await self._call("get_event_contract_event_list", str(series_code))
            data["events"] = _records(events)
        return data

    async def _fetch_corporate_actions(
        self, ticker: str, data_type: str | DataType, **kwargs: Any
    ) -> dict[str, Any]:
        """Dividends, splits and buybacks for the issuer."""
        code = _to_code(ticker, kwargs.get("market"))
        return {
            "dividends": _records(await self._call("get_corporate_actions_dividends", code)),
            "stock_splits": _records(await self._call("get_corporate_actions_stock_splits", code)),
            "buybacks": _records(await self._call("get_corporate_actions_buybacks", code)),
        }

    async def _fetch_capital_flow(
        self, ticker: str, data_type: str | DataType, **kwargs: Any
    ) -> dict[str, Any]:
        """Capital flow series + order-size distribution."""
        code = _to_code(ticker, kwargs.get("market"))
        return {
            "capital_flow": _records(await self._call("get_capital_flow", code)),
            "capital_distribution": _records(await self._call("get_capital_distribution", code)),
        }

    async def _fetch_earnings_catalyst(
        self, ticker: str, data_type: str | DataType, **kwargs: Any
    ) -> dict[str, Any]:
        """Historical earnings-day price reaction for the issuer."""
        code = _to_code(ticker, kwargs.get("market"))
        frame = await self._call("get_financials_earnings_price_history", code)
        return {"earnings_price_history": _records(frame)}

    async def _fetch_earnings_surprise(
        self, ticker: str, data_type: str | DataType, **kwargs: Any
    ) -> dict[str, Any]:
        """Price move around recent earnings releases."""
        code = _to_code(ticker, kwargs.get("market"))
        frame = await self._call("get_financials_earnings_price_move", code)
        return {"earnings_price_move": _records(frame)}

    async def _fetch_economic_calendar(
        self, ticker: str, data_type: str | DataType, **kwargs: Any
    ) -> dict[str, Any]:
        """Macro economic calendar over the requested window (defaults to today)."""
        begin = str(kwargs.get("begin_date") or date.today().isoformat())
        frame = await self._call("get_economic_calendar", begin, kwargs.get("end_date"))
        return {"economic_events": _records(frame)}

    async def _fetch_expected_move(
        self, ticker: str, data_type: str | DataType, **kwargs: Any
    ) -> dict[str, Any]:
        """Option-underlying overview (IV / expected-move inputs)."""
        code = _to_code(ticker, kwargs.get("market"))
        frame = await self._call("get_option_underlying_overview", [code])
        return {"option_underlying_overview": _records(frame)}

    async def _fetch_fed_watch(
        self, ticker: str, data_type: str | DataType, **kwargs: Any
    ) -> dict[str, Any]:
        """Fed target-rate probabilities + dot plot."""
        return {
            "fed_watch_target_rate": _records(await self._call("get_fed_watch_target_rate")),
            "fed_watch_dot_plot": _records(await self._call("get_fed_watch_dot_plot")),
        }

    async def _fetch_market_breadth(
        self, ticker: str, data_type: str | DataType, **kwargs: Any
    ) -> dict[str, Any]:
        """Rise/fall distribution for the requested market."""
        frame = await self._call("get_rise_fall_distribution", market=_market(kwargs))
        return {"rise_fall_distribution": _records(frame)}

    async def _fetch_revenue_breakdown(
        self, ticker: str, data_type: str | DataType, **kwargs: Any
    ) -> dict[str, Any]:
        """Revenue split by segment/geography."""
        code = _to_code(ticker, kwargs.get("market"))
        frame = await self._call("get_financials_revenue_breakdown", code)
        return {"revenue_breakdown": _records(frame)}

    async def _fetch_smart_money(
        self, ticker: str, data_type: str | DataType, **kwargs: Any
    ) -> dict[str, Any]:
        """Insider trades + shareholder holding changes."""
        code = _to_code(ticker, kwargs.get("market"))
        return {
            "insider_trades": _records(await self._call("get_insider_trade_list", code)),
            "shareholders_holding_changes": _records(
                await self._call("get_shareholders_holding_changes", code)
            ),
        }

    async def _fetch_analyst_ratings(
        self, ticker: str, data_type: str | DataType, **kwargs: Any
    ) -> dict[str, Any]:
        """Analyst rating summary + consensus."""
        code = _to_code(ticker, kwargs.get("market"))
        return {
            "rating_summary": _records(await self._call("get_research_rating_summary", code)),
            "analyst_consensus": _records(await self._call("get_research_analyst_consensus", code)),
        }

    async def _fetch_earnings_calendar(
        self, ticker: str, data_type: str | DataType, **kwargs: Any
    ) -> dict[str, Any]:
        """Earnings calendar for the requested market."""
        frame = await self._call(
            "get_earnings_calendar",
            _market(kwargs),
            None,
            kwargs.get("begin_date"),
            kwargs.get("end_date"),
        )
        return {"earnings_calendar": _records(frame)}
