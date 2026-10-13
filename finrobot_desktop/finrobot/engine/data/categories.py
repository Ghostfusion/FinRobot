# finrobot/engine/data/categories.py
"""Data categories + failover priority (Data Layer v3).

The owner's priority table defines 33 categories in two groups: a *fallback*
group (an ordered provider list) and a *single-vendor* group (exactly one
provider). These are the routing key for the single failover chain: the layer
walks providers in ``PRIORITY[category]`` order for the requested data type.

Why a separate ``Category`` and not the existing ``DataType``: the table's
categories (``core_stock_apis``, ``options_surface``, ``fed_watch`` …) do not
correspond 1:1 to ``DataType`` values, and several have no existing DataType at
all. ``DATATYPE_CATEGORY`` maps each legacy ``DataType`` onto its category so
existing consumers keep working unchanged.

See ``docs/DATA_PROVIDERS_V3_DESIGN.md`` §5.
"""

from __future__ import annotations

from enum import StrEnum

from finrobot.engine.data.types import DataType


class Category(StrEnum):
    """Routing categories from the owner's priority table."""

    # ── fallback groups (ordered provider lists) ──────────────────────────
    CORE_STOCK_APIS = "core_stock_apis"
    NEWS_DATA = "news_data"
    FUNDAMENTAL_DATA = "fundamental_data"
    ANALYST_RATINGS = "analyst_ratings"
    EARNINGS_CALENDAR = "earnings_calendar"
    TECHNICAL_INDICATORS = "technical_indicators"
    OPTIONS_DATA = "options_data"
    SHORT_INTEREST = "short_interest"
    INSTITUTION_DATA = "institution_data"
    MACRO_DATA = "macro_data"
    PREDICTION_MARKETS = "prediction_markets"
    CORPORATE_ACTIONS = "corporate_actions"
    NEWS_SENTIMENT = "news_sentiment"
    # Investment-fund profile/analytics (ETF / mutual fund / CEF). Owner policy:
    # EODHD first, moomoo second, then the free tail — EODHD's Fundamentals feed
    # carries an ETF_Data / MutualFund_Data section, but the CURRENT key's plan
    # gates it (403 on every symbol incl. AAPL, probed 2026-10-12), so the chain
    # degrades to the next capable provider rather than inventing a profile.
    FUND_DATA = "fund_data"

    # ── single-vendor groups ──────────────────────────────────────────────
    SEC_FILINGS = "sec_filings"
    RISK_FREE_CURVE = "risk_free_curve"
    OPTIONS_SURFACE = "options_surface"
    EXCHANGE_SYMBOLS = "exchange_symbols"
    EQUITY_SCREENER = "equity_screener"
    MARKET_MOVERS = "market_movers"
    CAPITAL_FLOW = "capital_flow"
    EARNINGS_CATALYST = "earnings_catalyst"
    EARNINGS_SURPRISE = "earnings_surprise"
    ECONOMIC_CALENDAR = "economic_calendar"
    EXPECTED_MOVE = "expected_move"
    FED_WATCH = "fed_watch"
    MARKET_BREADTH = "market_breadth"
    REVENUE_BREAKDOWN = "revenue_breakdown"
    SMART_MONEY = "smart_money"
    ANALYST_ACTIONS = "analyst_actions"
    FDA_CALENDAR = "fda_calendar"
    GUIDANCE_REVISIONS = "guidance_revisions"
    NEWS_RETRACTIONS = "news_retractions"
    OFFERINGS_CALENDAR = "offerings_calendar"


#: Category → ordered provider ids (highest priority first). Transcribed from the
#: owner's reference table, with two owner-requested deviations, dated here because
#: this table IS the failover chain:
#:
#: * 2026-10-12 (owner policy — EODHD first, moomoo second, wherever they can
#:   serve): ``core_stock_apis`` now leads ``eodhd``, then ``moomoo``, with FMP
#:   behind both. FMP's free quota is exhausted in practice — every quote/price
#:   fetch 429s — while EODHD's plan serves prices and moomoo's gateway serves
#:   quotes, so the previous FMP-first order burned a timeout per call before
#:   falling through to the provider that could answer. FMP was also the
#:   owner-requested lead of ``core_stock_apis``/``fundamental_data`` because the
#:   reference table omitted it; this supersedes that for ``core_stock_apis``
#:   only. ``fundamental_data`` keeps FMP first, because EODHD's Fundamentals feed
#:   403s on this plan (probed 2026-10-12, AAPL included) and moomoo declares no
#:   fundamentals capability — no earlier provider can serve it.
#: * Same-day audit against each provider's own ``capabilities()``. Entries a
#:   provider does NOT declare are no-ops the layer skips: ``moomoo`` under
#:   ``fundamental_data`` and ``news_data``, ``benzinga`` under
#:   ``core_stock_apis``, ``finnhub``/``yfinance`` under ``analyst_ratings`` and
#:   ``earnings_calendar``, ``yfinance`` under the technicals/options/short/
#:   institution rows, and ``equity_screener``/``market_movers`` — which name only
#:   ``yfinance`` and therefore have NO capable provider at all. They stay as the
#:   owner's rows (the runtime skips them, so the effect is drift in this
#:   documentation, not a misroute), and the audit is recorded here so the next
#:   reader does not have to re-derive it.
PRIORITY: dict[Category, tuple[str, ...]] = {
    Category.CORE_STOCK_APIS: (
        "eodhd",
        "moomoo",
        "fmp",
        "yfinance",
        "tiingo",
        "twelvedata",
        "stockdata",
        "benzinga",
    ),
    Category.NEWS_DATA: (
        "eodhd",
        "benzinga",
        "moomoo",
        "yfinance",
        "alpha_vantage",
        "stockdata",
        "newsapi",
    ),
    Category.FUNDAMENTAL_DATA: ("fmp", "moomoo", "yfinance", "tiingo", "alpha_vantage"),
    Category.ANALYST_RATINGS: ("moomoo", "finnhub", "yfinance", "benzinga"),
    Category.EARNINGS_CALENDAR: ("moomoo", "finnhub", "yfinance", "benzinga"),
    Category.TECHNICAL_INDICATORS: ("moomoo", "yfinance", "alpha_vantage"),
    Category.OPTIONS_DATA: ("moomoo", "yfinance"),
    Category.SHORT_INTEREST: ("moomoo", "yfinance"),
    Category.INSTITUTION_DATA: ("moomoo", "yfinance"),
    Category.MACRO_DATA: ("fred", "moomoo"),
    Category.PREDICTION_MARKETS: ("polymarket", "moomoo"),
    Category.CORPORATE_ACTIONS: ("eodhd", "moomoo", "benzinga"),
    # Owner policy (2026-10-12): EODHD first, moomoo second. EODHD's Fundamentals
    # feed has the ETF_Data / MutualFund_Data section this contract mirrors, but
    # the key's current plan 403s every fundamentals request (probed 2026-10-12,
    # AAPL included) so the chain falls through to moomoo's gateway and then to
    # the free tail. Ordering is capability-honest: no provider here is listed
    # after one that can actually serve the type.
    Category.FUND_DATA: ("eodhd", "moomoo", "yfinance"),
    Category.NEWS_SENTIMENT: ("eodhd", "alpha_vantage", "gdelt"),
    Category.SEC_FILINGS: ("sec_edgar",),
    Category.RISK_FREE_CURVE: ("federal_reserve",),
    Category.OPTIONS_SURFACE: ("cboe",),
    Category.EXCHANGE_SYMBOLS: ("eodhd",),
    Category.EQUITY_SCREENER: ("yfinance",),
    Category.MARKET_MOVERS: ("yfinance",),
    Category.CAPITAL_FLOW: ("moomoo",),
    Category.EARNINGS_CATALYST: ("moomoo",),
    Category.EARNINGS_SURPRISE: ("moomoo",),
    Category.ECONOMIC_CALENDAR: ("moomoo",),
    Category.EXPECTED_MOVE: ("moomoo",),
    Category.FED_WATCH: ("moomoo",),
    Category.MARKET_BREADTH: ("moomoo",),
    Category.REVENUE_BREAKDOWN: ("moomoo",),
    Category.SMART_MONEY: ("moomoo",),
    Category.ANALYST_ACTIONS: ("benzinga",),
    Category.FDA_CALENDAR: ("benzinga",),
    Category.GUIDANCE_REVISIONS: ("benzinga",),
    Category.NEWS_RETRACTIONS: ("benzinga",),
    Category.OFFERINGS_CALENDAR: ("benzinga",),
}

#: Every provider id referenced anywhere in :data:`PRIORITY`.
PRIORITY_PROVIDER_IDS: frozenset[str] = frozenset(
    pid for providers in PRIORITY.values() for pid in providers
)

#: Legacy ``DataType`` → :class:`Category`. Deterministic, exhaustive over the
#: DataType enum (a unit test pins exhaustiveness so a new DataType cannot be
#: added without assigning a category).
DATATYPE_CATEGORY: dict[DataType, Category] = {
    DataType.FINANCIALS: Category.FUNDAMENTAL_DATA,
    DataType.PRICE: Category.CORE_STOCK_APIS,
    DataType.QUOTE: Category.CORE_STOCK_APIS,
    DataType.NEWS: Category.NEWS_DATA,
    DataType.EARNINGS: Category.EARNINGS_CALENDAR,
    DataType.FILINGS: Category.SEC_FILINGS,
    DataType.PROFILE: Category.CORE_STOCK_APIS,
    DataType.RAG_10K: Category.SEC_FILINGS,
    DataType.EARNINGS_TRANSCRIPT: Category.EARNINGS_CALENDAR,
    DataType.SENTIMENT: Category.NEWS_SENTIMENT,
    DataType.HISTORICAL: Category.CORE_STOCK_APIS,
    DataType.QUARTERLY: Category.FUNDAMENTAL_DATA,
    DataType.CATALYST: Category.EARNINGS_CATALYST,
    DataType.PRICE_RANGE: Category.CORE_STOCK_APIS,
    DataType.HISTORICAL_BANDS: Category.CORE_STOCK_APIS,
    DataType.FILINGS_10K: Category.SEC_FILINGS,
    DataType.FILINGS_10Q: Category.SEC_FILINGS,
    DataType.FILINGS_8K: Category.SEC_FILINGS,
    DataType.XBRL_FACTS: Category.SEC_FILINGS,
    DataType.INSIDER_TRADES: Category.SEC_FILINGS,
    DataType.INSTITUTIONAL_HOLDINGS: Category.SEC_FILINGS,
    DataType.PROXY_STATEMENT: Category.SEC_FILINGS,
    DataType.SCHEDULE_13: Category.SEC_FILINGS,
    DataType.CEO_CERTIFICATION: Category.SEC_FILINGS,
    DataType.FORWARD_ESTIMATES: Category.ANALYST_RATINGS,
    DataType.PEER_CANDIDATES: Category.FUNDAMENTAL_DATA,
    DataType.DIVIDENDS: Category.CORPORATE_ACTIONS,
    DataType.FUND_PROFILE: Category.FUND_DATA,
}


def category_of(data_type: str | DataType) -> Category | None:
    """The routing category for a data type, or None when unmapped."""
    try:
        dt = DataType(data_type)
    except ValueError:
        return None
    return DATATYPE_CATEGORY.get(dt)
