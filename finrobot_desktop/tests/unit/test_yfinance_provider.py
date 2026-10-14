"""
Unit tests use mocked yfinance.
Integration tests (marked @pytest.mark.integration) hit real yfinance.
"""

import time
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from finrobot.engine.data.interface import (
    DataResult,
    ProviderError,
    RateLimitedProviderError,
    is_rate_limit_error,
)
from finrobot.engine.data.providers.yfinance_provider import YFinanceProvider


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_ticker(
    info: dict,
    news: list | None = None,
    history: pd.DataFrame | None = None,
    income_stmt: pd.DataFrame | None = None,
    cashflow: pd.DataFrame | None = None,
    quarterly_balance_sheet: pd.DataFrame | None = None,
    balance_sheet: pd.DataFrame | None = None,
    ttm_income_stmt: pd.DataFrame | None = None,
    ttm_cashflow: pd.DataFrame | None = None,
    ttm_raises: type[Exception] | None = None,
):
    if ttm_raises is None:
        mock = MagicMock()
    else:
        # A real property on a LOCAL MagicMock subclass: a class-level property on
        # ``MagicMock`` itself would shadow the per-instance attribute every other
        # test sets (and leak across the whole session).
        class _RaisingTicker(MagicMock):
            @property
            def ttm_income_stmt(self):
                raise ttm_raises()

            @property
            def ttm_cashflow(self):
                raise ttm_raises()

        mock = _RaisingTicker()
    mock.info = info
    mock.news = news or []
    if history is None:
        history = pd.DataFrame(
            {
                "Open": [150.0],
                "High": [155.0],
                "Low": [148.0],
                "Close": [152.0],
                "Volume": [1_000_000],
            },
            index=pd.to_datetime(["2024-01-01"]),
        )
    mock.history.return_value = history
    # income_stmt / cashflow default to empty DataFrames (no historical data)
    if income_stmt is None:
        income_stmt = pd.DataFrame()
    mock.income_stmt = income_stmt
    if cashflow is None:
        cashflow = pd.DataFrame()
    mock.cashflow = cashflow
    # Balance sheets default to EMPTY DataFrames (not MagicMock attrs) so the
    # EV-bridge read is deterministic: empty sheet → no claims → (None, None).
    mock.quarterly_balance_sheet = (
        pd.DataFrame() if quarterly_balance_sheet is None else quarterly_balance_sheet
    )
    mock.balance_sheet = pd.DataFrame() if balance_sheet is None else balance_sheet
    # TTM statement frames (the flat snapshot's six income lines + CapEx). Empty
    # by default so every pre-existing test keeps the None it always saw; pass a
    # frame to exercise the read, or ``ttm_raises`` to model a rate-limited read
    # that must degrade to None without failing the fetch.
    if ttm_raises is None:  # the raising subclass defines them as properties
        mock.ttm_income_stmt = pd.DataFrame() if ttm_income_stmt is None else ttm_income_stmt
        mock.ttm_cashflow = pd.DataFrame() if ttm_cashflow is None else ttm_cashflow
    return mock


VALID_INFO = {
    "regularMarketPrice": 150.0,
    "marketCap": 2_500_000_000_000,
    "totalRevenue": 385_000_000_000,
    "ebitda": 130_000_000_000,
    "netIncomeToCommon": 97_000_000_000,
    "grossMargins": 0.44,
    "operatingMargins": 0.30,
    "trailingPE": 28.3,
    "sharesOutstanding": 15_500_000_000,
    "currency": "USD",
}


# ---------------------------------------------------------------------------
# Unit tests (mocked)
# ---------------------------------------------------------------------------


class TestYFinanceProviderMeta:
    def test_name(self):
        assert YFinanceProvider().name == "yfinance"

    def test_capabilities(self):
        caps = YFinanceProvider().capabilities()
        assert set(caps) == {
            "financials",
            "price",
            "price_range",
            "quote",
            "news",
            # Investment-fund profile (ETF / mutual fund / CEF): Yahoo serves
            # `funds_data` for ~20k US funds, which is why this provider is the
            # always-on tail of the FUND_DATA chain.
            "fund_profile",
        }


class TestFetchFinancials:
    @pytest.mark.asyncio
    async def test_returns_dataresult_with_revenue(self):
        provider = YFinanceProvider()
        mock_ticker = _make_mock_ticker(VALID_INFO)
        with patch(
            "finrobot.engine.data.providers.yfinance_provider.yf.Ticker", return_value=mock_ticker
        ):
            result = await provider.fetch("AAPL", "financials")
        assert isinstance(result, DataResult)
        assert result.data["revenue"] == 385_000_000_000
        assert result.data["market_cap"] is not None
        assert result.ticker == "AAPL"
        assert result.data_type == "financials"

    @pytest.mark.asyncio
    async def test_invalid_ticker_raises_provider_error(self):
        provider = YFinanceProvider()
        mock_ticker = _make_mock_ticker(
            {"regularMarketPrice": None, "currentPrice": None, "marketCap": None}
        )
        # Empty-ish info → invalid ticker
        mock_ticker.info = {}
        with patch(
            "finrobot.engine.data.providers.yfinance_provider.yf.Ticker", return_value=mock_ticker
        ):
            with pytest.raises(ProviderError):
                await provider.fetch("INVALID_TICKER_XYZ", "financials")

    @pytest.mark.asyncio
    async def test_key_rich_but_priceless_info_raises_provider_error(self):
        """Bug 21 entry gate: a delisted/OTC residual page can return a key-RICH
        info dict whose price/cap anchors (regularMarketPrice, currentPrice,
        marketCap) are ALL None. The old ``len(info) <= 1`` sub-gate let it
        through, and the priceless payload fabricated a $0 quote downstream."""
        provider = YFinanceProvider()
        mock_ticker = _make_mock_ticker(
            {
                "regularMarketPrice": None,
                "currentPrice": None,
                "marketCap": None,
                # Residual page noise — plenty of keys, zero price anchors.
                "longName": "Ghost Holdings Corp",
                "exchange": "PNK",
                "quoteType": "EQUITY",
                "currency": "USD",
                "symbol": "GHST",
            }
        )
        with patch(
            "finrobot.engine.data.providers.yfinance_provider.yf.Ticker", return_value=mock_ticker
        ):
            with pytest.raises(ProviderError, match="not found or returned no data"):
                await provider.fetch("GHST", "financials")


def _sheet(rows: dict[str, float], column: str = "2026-06-30") -> pd.DataFrame:
    """One-period balance-sheet DataFrame shaped like yfinance's (newest first)."""
    return pd.DataFrame({column: list(rows.values())}, index=list(rows))


class TestEvBridgeClaims:
    """Numeric-audit family 3: preferred equity and noncontrolling interest are
    claims on the enterprise beside common equity, so ``calculate_ev`` folds them
    into EV. yfinance's flat ``info`` snapshot carries neither, so this caliber
    must take them off the statement DataFrames — otherwise EV silently omits
    them (live WFC: 15.348B preferred + 2.133B NCI = 3.5% of enterprise value)
    and the ev_bridge audit can only report the bridge as unverifiable.
    """

    @pytest.mark.asyncio
    async def test_reads_preferred_and_nci_off_the_statement(self):
        # Live shape, WFC quarterly 2026-06-30 (== the SEC XBRL facts to the dollar).
        mock_ticker = _make_mock_ticker(
            VALID_INFO,
            quarterly_balance_sheet=_sheet(
                {"Preferred Stock": 15_348_000_000.0, "Minority Interest": 2_133_000_000.0}
            ),
        )
        with patch(
            "finrobot.engine.data.providers.yfinance_provider.yf.Ticker", return_value=mock_ticker
        ):
            result = await YFinanceProvider().fetch("WFC", "financials")
        assert result.data["preferred_stock"] == 15_348_000_000.0
        assert result.data["noncontrolling_interest"] == 2_133_000_000.0

    @pytest.mark.asyncio
    async def test_reported_zero_is_a_claim_not_a_gap(self):
        """INCY ships an explicit nil preferred balance → 0.0. Keeping the 0.0 is
        what clears the ev_bridge caveat honestly: the vendor DID state the claim
        and it is nil (SEC: 0 preferred shares issued/outstanding). Coercing it to
        None would keep flagging a claim that does not exist."""
        mock_ticker = _make_mock_ticker(
            VALID_INFO,
            quarterly_balance_sheet=_sheet({"Preferred Stock": 0.0, "Total Assets": 1.0}),
        )
        with patch(
            "finrobot.engine.data.providers.yfinance_provider.yf.Ticker", return_value=mock_ticker
        ):
            result = await YFinanceProvider().fetch("INCY", "financials")
        assert result.data["preferred_stock"] == 0.0
        # The NCI row is absent for INCY → None, never a fabricated 0.
        assert result.data["noncontrolling_interest"] is None

    @pytest.mark.asyncio
    async def test_absent_rows_and_nan_cells_stay_none(self):
        """Yahoo omits the row for an issuer with no such claim (MSFT: no NCI row)
        and can leave a cell NaN — neither is a reported zero, so EV must keep
        flagging the bridge as unverifiable rather than assume nil."""
        mock_ticker = _make_mock_ticker(
            VALID_INFO,
            quarterly_balance_sheet=_sheet(
                {"Preferred Stock": float("nan"), "Minority Interest": float("nan")}
            ),
        )
        with patch(
            "finrobot.engine.data.providers.yfinance_provider.yf.Ticker", return_value=mock_ticker
        ):
            result = await YFinanceProvider().fetch("MSFT", "financials")
        assert result.data["preferred_stock"] is None
        assert result.data["noncontrolling_interest"] is None

    @pytest.mark.asyncio
    async def test_quarterly_sheet_wins_over_the_stale_annual_one(self):
        """The flat snapshot's debt/cash legs are the FRESHEST quarter (FMP serves
        period=quarter), so these instant items must be that period's. The annual
        sheet still showed WFC's prior-year 16.608B against the quarterly 15.348B.
        Also pins the ``Preferred Stock Equity`` row alias."""
        mock_ticker = _make_mock_ticker(
            VALID_INFO,
            quarterly_balance_sheet=_sheet({"Preferred Stock Equity": 15_348_000_000.0}),
            balance_sheet=_sheet({"Preferred Stock Equity": 16_608_000_000.0}),
        )
        with patch(
            "finrobot.engine.data.providers.yfinance_provider.yf.Ticker", return_value=mock_ticker
        ):
            result = await YFinanceProvider().fetch("WFC", "financials")
        assert result.data["preferred_stock"] == 15_348_000_000.0

    @pytest.mark.asyncio
    async def test_falls_back_to_the_annual_sheet(self):
        mock_ticker = _make_mock_ticker(
            VALID_INFO,
            quarterly_balance_sheet=pd.DataFrame(),
            balance_sheet=_sheet({"Minority Interest": 2_106_000_000.0}),
        )
        with patch(
            "finrobot.engine.data.providers.yfinance_provider.yf.Ticker", return_value=mock_ticker
        ):
            result = await YFinanceProvider().fetch("KO", "financials")
        assert result.data["noncontrolling_interest"] == 2_106_000_000.0

    @pytest.mark.asyncio
    async def test_statement_failure_degrades_instead_of_failing_the_fetch(self):
        """These are completeness fields, not the reason the fetch exists: a
        rate-limited statement must leave them None (the audit then reports the
        gap) rather than take down the whole FINANCIALS fetch on the last-resort
        provider."""
        from yfinance.exceptions import YFRateLimitError

        mock_ticker = _make_mock_ticker(VALID_INFO)
        type(mock_ticker).quarterly_balance_sheet = property(
            lambda self: (_ for _ in ()).throw(YFRateLimitError())
        )
        with patch(
            "finrobot.engine.data.providers.yfinance_provider.yf.Ticker", return_value=mock_ticker
        ):
            result = await YFinanceProvider().fetch("AAPL", "financials")
        assert result.data["revenue"] == 385_000_000_000
        assert result.data["preferred_stock"] is None
        assert result.data["noncontrolling_interest"] is None


class TestFetchQuote:
    """门一 Step 3: lightweight QUOTE path via fast_info.last_price (no .info)."""

    class _FastInfo:
        def __init__(self, price: float | None, currency: str | None = "USD") -> None:
            self.last_price = price
            self.currency = currency

    def test_quote_in_capabilities(self):
        assert "quote" in YFinanceProvider().capabilities()

    @pytest.mark.asyncio
    async def test_quote_returns_price_from_fast_info(self):
        provider = YFinanceProvider()
        mock_ticker = MagicMock()
        mock_ticker.fast_info = self._FastInfo(187.5)
        with patch(
            "finrobot.engine.data.providers.yfinance_provider.yf.Ticker", return_value=mock_ticker
        ):
            result = await provider.fetch("AAPL", "quote")
        # The QUOTE payload now carries the quote currency from fast_info.currency
        # (same cheap call, no .info round-trip) so a foreign listing's price
        # travels with its currency.
        assert result.data == {"price": 187.5, "quote_currency": "USD"}
        assert result.data_type == "quote"

    @pytest.mark.asyncio
    async def test_quote_carries_foreign_currency_from_fast_info(self):
        """A foreign LOCAL listing (2330.TW) quotes in TWD — fast_info.currency
        surfaces it, and it must ride on the QUOTE payload."""
        provider = YFinanceProvider()
        mock_ticker = MagicMock()
        mock_ticker.fast_info = self._FastInfo(640.0, currency="TWD")
        with patch(
            "finrobot.engine.data.providers.yfinance_provider.yf.Ticker", return_value=mock_ticker
        ):
            result = await provider.fetch("2330.TW", "quote")
        assert result.data == {"price": 640.0, "quote_currency": "TWD"}

    @pytest.mark.asyncio
    async def test_quote_currency_none_when_fast_info_lacks_it(self):
        """fast_info without a currency → quote_currency None (consumer abstains,
        never assumes USD)."""
        provider = YFinanceProvider()
        mock_ticker = MagicMock()
        mock_ticker.fast_info = self._FastInfo(187.5, currency=None)
        with patch(
            "finrobot.engine.data.providers.yfinance_provider.yf.Ticker", return_value=mock_ticker
        ):
            result = await provider.fetch("AAPL", "quote")
        assert result.data == {"price": 187.5, "quote_currency": None}

    @pytest.mark.asyncio
    async def test_quote_none_price_raises_provider_error(self):
        provider = YFinanceProvider()
        mock_ticker = MagicMock()
        mock_ticker.fast_info = self._FastInfo(None)
        with patch(
            "finrobot.engine.data.providers.yfinance_provider.yf.Ticker", return_value=mock_ticker
        ):
            with pytest.raises(ProviderError):
                await provider.fetch("AAPL", "quote")


class TestFetchPrice:
    @pytest.mark.asyncio
    async def test_returns_price_history(self):
        provider = YFinanceProvider()
        mock_ticker = _make_mock_ticker(VALID_INFO)
        with patch(
            "finrobot.engine.data.providers.yfinance_provider.yf.Ticker", return_value=mock_ticker
        ):
            result = await provider.fetch("AAPL", "price")
        assert isinstance(result, DataResult)
        assert "price_history" in result.data
        assert result.data["quote_currency"] == "USD"
        assert len(result.data["price_history"]) == 1
        assert result.data["price_history"][0]["close"] == 152.0

    @pytest.mark.asyncio
    async def test_fetch_price_carries_foreign_quote_currency(self):
        provider = YFinanceProvider()
        mock_ticker = _make_mock_ticker({**VALID_INFO, "currency": "TWD"})
        with patch(
            "finrobot.engine.data.providers.yfinance_provider.yf.Ticker", return_value=mock_ticker
        ):
            result = await provider.fetch("2330.TW", "price")
        assert result.data["current_price"] == 150.0
        assert result.data["quote_currency"] == "TWD"


class TestFetchPriceRange:
    @pytest.mark.asyncio
    async def test_returns_adjusted_bars(self):
        provider = YFinanceProvider()
        hist = pd.DataFrame(
            {
                "Open": [100.0, 102.0],
                "High": [101.0, 103.0],
                "Low": [99.0, 101.0],
                "Close": [100.5, 102.5],
                "Volume": [1_000_000, 1_100_000],
            },
            index=pd.to_datetime(["2020-01-02", "2020-01-03"]),
        )
        mock_ticker = _make_mock_ticker(VALID_INFO, history=hist)
        with patch(
            "finrobot.engine.data.providers.yfinance_provider.yf.Ticker", return_value=mock_ticker
        ):
            result = await provider.fetch(
                "AAPL", "price_range", start="2020-01-01", end="2020-01-04", interval="1d"
            )
        assert result.data_type == "price_range"
        assert result.data["adjusted"] is True
        assert result.data["source_provider"] == "yfinance"
        bars = result.data["bars"]
        assert [b["date"] for b in bars] == ["2020-01-02", "2020-01-03"]
        assert bars[1]["close"] == 102.5
        # history called with auto_adjust=True (the adjusted basis).
        _, kwargs = mock_ticker.history.call_args
        assert kwargs["auto_adjust"] is True
        assert kwargs["start"] == "2020-01-01"

    @pytest.mark.asyncio
    async def test_empty_range_raises(self):
        provider = YFinanceProvider()
        mock_ticker = _make_mock_ticker(VALID_INFO, history=pd.DataFrame())
        with patch(
            "finrobot.engine.data.providers.yfinance_provider.yf.Ticker", return_value=mock_ticker
        ):
            with pytest.raises(ProviderError, match="no bars"):
                await provider.fetch("AAPL", "price_range", start="1990-01-01", end="1990-01-02")


class TestFetchNews:
    @pytest.mark.asyncio
    async def test_returns_news_items_list(self):
        provider = YFinanceProvider()
        raw_news = [
            {
                "content": {
                    "title": "Apple hits new high",
                    "provider": {"displayName": "Reuters"},
                    "pubDate": "2024-10-31T16:00:00Z",
                    "canonicalUrl": {"url": "https://example.com/1"},
                }
            },
            {
                "content": {
                    "title": "AAPL earnings beat",
                    "provider": {"displayName": "Bloomberg"},
                    "pubDate": "2024-10-30T14:00:00Z",
                    "canonicalUrl": {"url": "https://example.com/2"},
                }
            },
        ]
        mock_ticker = _make_mock_ticker(VALID_INFO, news=raw_news)
        with patch(
            "finrobot.engine.data.providers.yfinance_provider.yf.Ticker", return_value=mock_ticker
        ):
            result = await provider.fetch("AAPL", "news")
        assert isinstance(result, DataResult)
        assert "news_items" in result.data
        items = result.data["news_items"]
        assert len(items) == 2
        assert items[0]["title"] == "Apple hits new high"
        assert items[0]["source"] == "Reuters"
        assert items[0]["url"] == "https://example.com/1"

    @pytest.mark.asyncio
    async def test_empty_news_returns_empty_list(self):
        provider = YFinanceProvider()
        mock_ticker = _make_mock_ticker(VALID_INFO, news=[])
        with patch(
            "finrobot.engine.data.providers.yfinance_provider.yf.Ticker", return_value=mock_ticker
        ):
            result = await provider.fetch("AAPL", "news")
        assert result.data["news_items"] == []

    @pytest.mark.asyncio
    async def test_news_items_compatible_with_parse_raw_news(self):
        """Verify yfinance news format is parseable by parse_raw_news."""
        from finrobot.engine.compute.coordinators.news import RawNewsItem, parse_raw_news

        provider = YFinanceProvider()
        raw_news = [
            {
                "content": {
                    "title": "Apple Q4 beat",
                    "provider": {"displayName": "Reuters"},
                    "pubDate": "2024-10-31T16:00:00Z",
                    "canonicalUrl": {"url": "https://example.com/1"},
                }
            },
            {
                "content": {
                    "title": "iPhone sales surge",
                    "provider": {"displayName": "CNBC"},
                    "pubDate": "2024-10-30T10:00:00Z",
                    "canonicalUrl": {"url": "https://example.com/2"},
                }
            },
        ]
        mock_ticker = _make_mock_ticker(VALID_INFO, news=raw_news)
        with patch(
            "finrobot.engine.data.providers.yfinance_provider.yf.Ticker", return_value=mock_ticker
        ):
            result = await provider.fetch("AAPL", "news")
        items = parse_raw_news(result)
        assert len(items) == 2
        assert all(isinstance(item, RawNewsItem) for item in items)
        assert items[0].title == "Apple Q4 beat"
        assert items[0].source == "Reuters"

    @pytest.mark.asyncio
    async def test_news_fallback_fields(self):
        """When content sub-fields are missing, falls back to top-level fields."""
        provider = YFinanceProvider()
        # Old-style yfinance news format (no nested content.provider etc.)
        raw_news = [
            {
                "content": {"title": "Old format news"},
                "publisher": "Yahoo",
                "link": "https://y.com",
            },
        ]
        mock_ticker = _make_mock_ticker(VALID_INFO, news=raw_news)
        with patch(
            "finrobot.engine.data.providers.yfinance_provider.yf.Ticker", return_value=mock_ticker
        ):
            result = await provider.fetch("AAPL", "news")
        items = result.data["news_items"]
        assert len(items) == 1
        assert items[0]["source"] == "Yahoo"
        assert items[0]["url"] == "https://y.com"


class TestNonUSTickerFormat:
    """Track E: A-share / HK tickers must reach yfinance without format rejection."""

    @pytest.mark.asyncio
    async def test_non_us_ticker_format_not_rejected(self):
        """600519.SS (A-share), 000858.SZ (Shenzhen), 0700.HK must pass through."""
        received_symbols: list[str] = []

        original_make_mock = _make_mock_ticker

        def tracking_ticker(symbol: str):
            received_symbols.append(symbol)
            return original_make_mock(VALID_INFO)

        provider = YFinanceProvider()
        for ticker in ("600519.SS", "000858.SZ", "0700.HK"):
            received_symbols.clear()
            with patch(
                "finrobot.engine.data.providers.yfinance_provider.yf.Ticker",
                side_effect=tracking_ticker,
            ):
                result = await provider.fetch(ticker, "financials")
            assert received_symbols == [ticker], (
                f"Ticker '{ticker}' was not passed through to yfinance"
            )
            assert isinstance(result, DataResult)
            assert result.ticker == ticker


class TestRateLimitBehavior:
    """Provider must surface 429 immediately so DataLayer falls back fast.

    The in-provider retry loop (3 attempts × [2,5,10]s sleep = up to 17s
    per call) was removed because:
      1. DataLayer already iterates providers in priority order on
         ProviderError, so retry-inside-provider blocked the fallback
         to FMP/Finnhub by ~17s.
      2. Sleeping inside the rate-limit window burns the same Yahoo quota
         on retry that already failed — counterproductive.
    """

    @pytest.mark.asyncio
    async def test_rate_limit_raises_provider_error_within_1s(self):
        """Yahoo 429 must raise ProviderError in <1s, not sleep 17s.

        Guards against re-introducing the in-provider retry loop.
        """
        from yfinance.exceptions import YFRateLimitError

        # Mock t.info to raise YFRateLimitError so the error path fires.
        # We use PropertyMock so the access pattern (t.info inside the
        # asyncio.to_thread lambda) matches production. NOTE: yfinance 1.x's
        # YFRateLimitError takes NO message argument (fixed text) — passing one
        # raised TypeError inside the lambda, which the generic except arm also
        # wrapped into ProviderError, so the old test was green WITHOUT ever
        # exercising the rate-limit path (fake-green, caught 2026-06-11).
        provider = YFinanceProvider()
        mock_ticker = MagicMock()
        type(mock_ticker).info = property(lambda self: (_ for _ in ()).throw(YFRateLimitError()))

        start = time.monotonic()
        with patch(
            "finrobot.engine.data.providers.yfinance_provider.yf.Ticker",
            return_value=mock_ticker,
        ):
            # The typed YFRateLimitError must map to RateLimitedProviderError
            # (primary classification path — survives Yahoo rewording the
            # message), and the classifier must recognise it structurally.
            with pytest.raises(RateLimitedProviderError, match="Failed to fetch ticker") as ei:
                await provider.fetch("AAPL", "financials")
        assert is_rate_limit_error(ei.value)
        elapsed = time.monotonic() - start
        assert elapsed < 1.0, (
            f"Provider took {elapsed:.2f}s — retry loop must stay deleted. "
            "DataLayer.fetch() already iterates providers on ProviderError; "
            "retry-inside-provider blocks fallback to FMP/Finnhub."
        )

    @pytest.mark.asyncio
    async def test_no_retry_constants_exposed(self):
        """The retry constants must not be re-introduced as module symbols.

        Guards against partial-revert: if a future commit re-adds
        ``_MAX_RETRIES`` / ``_RETRY_DELAYS`` even without wiring them
        into ``fetch``, the next reviewer should be forced to defend it.
        """
        from finrobot.engine.data.providers import yfinance_provider

        assert not hasattr(yfinance_provider, "_MAX_RETRIES"), (
            "_MAX_RETRIES re-introduced — retry-inside-provider conflicts "
            "with DataLayer fallback. See yfinance_provider.py docstring."
        )
        assert not hasattr(yfinance_provider, "_RETRY_DELAYS"), (
            "_RETRY_DELAYS re-introduced — see _MAX_RETRIES rationale."
        )


class TestUnsupportedDataType:
    @pytest.mark.asyncio
    async def test_filings_raises_provider_error(self):
        provider = YFinanceProvider()
        mock_ticker = _make_mock_ticker(VALID_INFO)
        with patch(
            "finrobot.engine.data.providers.yfinance_provider.yf.Ticker", return_value=mock_ticker
        ):
            with pytest.raises(ProviderError, match="not supported"):
                await provider.fetch("AAPL", "filings")

    @pytest.mark.asyncio
    async def test_unknown_type_raises_provider_error(self):
        provider = YFinanceProvider()
        mock_ticker = _make_mock_ticker(VALID_INFO)
        with patch(
            "finrobot.engine.data.providers.yfinance_provider.yf.Ticker", return_value=mock_ticker
        ):
            with pytest.raises(ProviderError):
                await provider.fetch("AAPL", "unknown_type")


class TestFetchHistoricalFinancials:
    """Tests for multi-year financials via income_stmt DataFrame."""

    @staticmethod
    def _build_income_stmt(years: int = 3) -> pd.DataFrame:
        """Build a mock income_stmt DataFrame with `years` columns.

        Columns are fiscal-year-end dates (most recent first).
        Rows are standard yfinance income statement labels.
        """
        columns = pd.to_datetime([f"{2024 - i}-09-30" for i in range(years)])
        data = {
            col: {
                "Total Revenue": (400 - i * 10) * 1e9,
                "EBITDA": (130 - i * 5) * 1e9,
                "Net Income": (95 - i * 3) * 1e9,
                "Gross Profit": (170 - i * 4) * 1e9,
                "Operating Income": (120 - i * 5) * 1e9,
                "Basic EPS": 6.15 - i * 0.4,
                "Selling General Administrative": (25 - i) * 1e9,
            }
            for i, col in enumerate(columns)
        }
        return pd.DataFrame(data)

    @staticmethod
    def _build_cashflow(years: int = 3) -> pd.DataFrame:
        """Build a mock cashflow DataFrame aligned by fiscal-year-end date to
        ``_build_income_stmt``. CapEx is negative (yfinance convention)."""
        columns = pd.to_datetime([f"{2024 - i}-09-30" for i in range(years)])
        data = {
            col: {
                "Operating Cash Flow": (110 - i * 5) * 1e9,
                "Investing Cash Flow": -(8 + i * 0.4) * 1e9,
                "Financing Cash Flow": -(95 - i * 3) * 1e9,
                "Depreciation And Amortization": (11 - i * 0.1) * 1e9,
                "Capital Expenditure": -(10 + i * 0.5) * 1e9,
                "Change In Working Capital": (-2 + i * 0.3) * 1e9,
            }
            for i, col in enumerate(columns)
        }
        return pd.DataFrame(data)

    @staticmethod
    def _build_balance_sheet(years: int = 3, *, with_complete_debt: bool = True) -> pd.DataFrame:
        """Balance sheet aligned to ``_build_income_stmt`` / ``_build_cashflow``.

        Carries the two legs the historical valuation bands form EV from;
        ``with_complete_debt=False`` models a frame with no complete-debt row, which
        must leave debt unknown rather than borrowing a partial leg.
        """
        columns = pd.to_datetime([f"{2024 - i}-09-30" for i in range(years)])
        # Same orientation as _build_cashflow: outer key = fiscal-year-end column,
        # inner keys = statement row names.
        data: dict[object, dict[str, float]] = {
            col: {"Cash And Cash Equivalents": (30 - i * 2) * 1e9} for i, col in enumerate(columns)
        }
        if with_complete_debt:
            for i, col in enumerate(columns):
                data[col]["Total Debt"] = (120 - i * 5) * 1e9
        return pd.DataFrame(data)

    @pytest.mark.asyncio
    async def test_multi_year_includes_the_debt_and_cash_legs(self):
        """The bands build EV = market cap + net debt, so the yearly dict must carry
        the debt/cash legs. They were missing entirely, which withheld every EV-based
        band (and both Football-Field reverse multiples) whenever FMP was rate-limited
        — live 2026-10-12 on NFLX, all five years had net_debt None."""
        mock_ticker = _make_mock_ticker(
            VALID_INFO,
            income_stmt=self._build_income_stmt(3),
            cashflow=self._build_cashflow(3),
            balance_sheet=self._build_balance_sheet(3),
        )
        provider = YFinanceProvider()
        with patch(
            "finrobot.engine.data.providers.yfinance_provider.yf.Ticker",
            return_value=mock_ticker,
        ):
            result = await provider.fetch("AAPL", "financials", years=3)

        yearly = result.data["yearly_data"]
        assert yearly[0]["total_debt"] == 120e9
        assert yearly[0]["total_cash"] == 30e9
        assert yearly[2]["total_debt"] == 110e9  # 120 - 2*5
        assert yearly[2]["total_cash"] == 26e9  # 30 - 2*2

    @pytest.mark.asyncio
    async def test_missing_balance_sheet_leaves_debt_unknown_not_zero(self):
        """None ≠ 0: a fabricated 0 reads as a debt-free year and skews EV/EBITDA low."""
        mock_ticker = _make_mock_ticker(
            VALID_INFO, income_stmt=self._build_income_stmt(2), cashflow=self._build_cashflow(2)
        )
        provider = YFinanceProvider()
        with patch(
            "finrobot.engine.data.providers.yfinance_provider.yf.Ticker",
            return_value=mock_ticker,
        ):
            result = await provider.fetch("AAPL", "financials", years=2)

        yearly = result.data["yearly_data"]
        assert yearly[0]["total_debt"] is None
        assert yearly[0]["total_cash"] is None

    @pytest.mark.asyncio
    async def test_partial_balance_sheet_does_not_invent_debt(self):
        """A frame with no complete-debt row keeps debt unknown while cash, which IS
        reported, still comes through."""
        mock_ticker = _make_mock_ticker(
            VALID_INFO,
            income_stmt=self._build_income_stmt(2),
            balance_sheet=self._build_balance_sheet(2, with_complete_debt=False),
        )
        provider = YFinanceProvider()
        with patch(
            "finrobot.engine.data.providers.yfinance_provider.yf.Ticker",
            return_value=mock_ticker,
        ):
            result = await provider.fetch("AAPL", "financials", years=2)

        yearly = result.data["yearly_data"]
        assert yearly[0]["total_debt"] is None
        assert yearly[0]["total_cash"] == 30e9

    @pytest.mark.asyncio
    async def test_multi_year_returns_yearly_data(self):
        """When years > 1, result.data['yearly_data'] has N entries."""
        income_stmt = self._build_income_stmt(3)
        mock_ticker = _make_mock_ticker(VALID_INFO, income_stmt=income_stmt)
        provider = YFinanceProvider()
        with patch(
            "finrobot.engine.data.providers.yfinance_provider.yf.Ticker",
            return_value=mock_ticker,
        ):
            result = await provider.fetch("AAPL", "financials", years=3)
        assert isinstance(result, DataResult)
        assert "yearly_data" in result.data
        yearly = result.data["yearly_data"]
        assert len(yearly) == 3
        # Most recent year first
        assert yearly[0]["revenue"] == 400e9
        assert yearly[1]["revenue"] == 390e9
        assert yearly[2]["revenue"] == 380e9

    @pytest.mark.asyncio
    async def test_multi_year_extracts_margins(self):
        """Each year entry includes computed margins."""
        income_stmt = self._build_income_stmt(2)
        mock_ticker = _make_mock_ticker(VALID_INFO, income_stmt=income_stmt)
        provider = YFinanceProvider()
        with patch(
            "finrobot.engine.data.providers.yfinance_provider.yf.Ticker",
            return_value=mock_ticker,
        ):
            result = await provider.fetch("AAPL", "financials", years=2)
        yearly = result.data["yearly_data"]
        # gross_margin = Gross Profit / Total Revenue
        expected_gm = 170e9 / 400e9
        assert abs(yearly[0]["gross_margin"] - expected_gm) < 1e-6
        # operating_margin = Operating Income / Total Revenue
        expected_om = 120e9 / 400e9
        assert abs(yearly[0]["operating_margin"] - expected_om) < 1e-6

    @pytest.mark.asyncio
    async def test_multi_year_includes_fiscal_year(self):
        """Each yearly entry includes the fiscal_year string."""
        income_stmt = self._build_income_stmt(2)
        mock_ticker = _make_mock_ticker(VALID_INFO, income_stmt=income_stmt)
        provider = YFinanceProvider()
        with patch(
            "finrobot.engine.data.providers.yfinance_provider.yf.Ticker",
            return_value=mock_ticker,
        ):
            result = await provider.fetch("AAPL", "financials", years=2)
        yearly = result.data["yearly_data"]
        assert yearly[0]["fiscal_year"] == "2024-09-30"
        assert yearly[1]["fiscal_year"] == "2023-09-30"

    @pytest.mark.asyncio
    async def test_multi_year_caps_at_available_columns(self):
        """If years > available columns, return only available data."""
        income_stmt = self._build_income_stmt(2)
        mock_ticker = _make_mock_ticker(VALID_INFO, income_stmt=income_stmt)
        provider = YFinanceProvider()
        with patch(
            "finrobot.engine.data.providers.yfinance_provider.yf.Ticker",
            return_value=mock_ticker,
        ):
            result = await provider.fetch("AAPL", "financials", years=5)
        assert len(result.data["yearly_data"]) == 2

    @pytest.mark.asyncio
    async def test_multi_year_empty_income_stmt_falls_back(self):
        """If income_stmt is empty, fall back to single-year from info."""
        mock_ticker = _make_mock_ticker(VALID_INFO, income_stmt=pd.DataFrame())
        provider = YFinanceProvider()
        with patch(
            "finrobot.engine.data.providers.yfinance_provider.yf.Ticker",
            return_value=mock_ticker,
        ):
            result = await provider.fetch("AAPL", "financials", years=3)
        # Falls back to single-year: no yearly_data key, has revenue directly
        assert "revenue" in result.data
        assert result.data["revenue"] == 385_000_000_000

    @pytest.mark.asyncio
    async def test_years_one_uses_single_year_path(self):
        """years=1 should use single-year (info dict) path."""
        mock_ticker = _make_mock_ticker(VALID_INFO)
        provider = YFinanceProvider()
        with patch(
            "finrobot.engine.data.providers.yfinance_provider.yf.Ticker",
            return_value=mock_ticker,
        ):
            result = await provider.fetch("AAPL", "financials", years=1)
        assert "revenue" in result.data
        assert "yearly_data" not in result.data

    @pytest.mark.asyncio
    async def test_no_years_kwarg_uses_single_year(self):
        """No years kwarg → single-year path (backward compatible)."""
        mock_ticker = _make_mock_ticker(VALID_INFO)
        provider = YFinanceProvider()
        with patch(
            "finrobot.engine.data.providers.yfinance_provider.yf.Ticker",
            return_value=mock_ticker,
        ):
            result = await provider.fetch("AAPL", "financials")
        assert "revenue" in result.data
        assert "yearly_data" not in result.data


class TestFetchHistoricalFinancialsFullSchema:
    """门一 Step 2: yfinance historical yearly_data must carry the SAME rich
    per-year schema as FMP (cash-flow trio + D&A + EPS + SGA + absolutes), so
    that when historical_extractor routes through DataLayer and FMP is down,
    the yfinance fallback still yields a complete HistoricalMetrics instead of
    silently degrading DCF to industry medians."""

    def _build_ticker(self, years: int = 3):
        income = TestFetchHistoricalFinancials._build_income_stmt(years)
        cashflow = TestFetchHistoricalFinancials._build_cashflow(years)
        return _make_mock_ticker(VALID_INFO, income_stmt=income, cashflow=cashflow)

    async def _fetch_yearly(self, years: int = 3):
        provider = YFinanceProvider()
        with patch(
            "finrobot.engine.data.providers.yfinance_provider.yf.Ticker",
            return_value=self._build_ticker(years),
        ):
            result = await provider.fetch("AAPL", "financials", years=years)
        return result.data["yearly_data"]

    @pytest.mark.asyncio
    async def test_income_statement_absolutes_and_eps_sga(self):
        y = await self._fetch_yearly(3)
        assert y[0]["gross_profit"] == 170e9
        assert y[0]["operating_income"] == 120e9
        assert y[0]["eps"] == pytest.approx(6.15)
        assert y[0]["sga_expense"] == 25e9

    @pytest.mark.asyncio
    async def test_cash_flow_statement_populated(self):
        y = await self._fetch_yearly(3)
        assert y[0]["operating_cash_flow"] == 110e9
        assert y[0]["investing_cash_flow"] == -8e9
        assert y[0]["financing_cash_flow"] == -95e9
        assert y[0]["depreciation_amortization"] == pytest.approx(11e9)
        assert y[0]["change_in_working_capital"] == pytest.approx(-2e9)

    @pytest.mark.asyncio
    async def test_capex_sign_normalized_to_positive(self):
        """CapEx is negative in raw yfinance (outflow); provider stores it as a
        positive magnitude so DCF capex/revenue ratios compute directly."""
        y = await self._fetch_yearly(3)
        assert y[0]["capital_expenditure"] == 10e9
        assert all(yr["capital_expenditure"] >= 0 for yr in y)

    @pytest.mark.asyncio
    async def test_empty_cashflow_yields_none_cf_fields_not_crash(self):
        """Missing cash-flow statement → CF fields are None (consumer zero-fills),
        income-statement fields still populate."""
        income = TestFetchHistoricalFinancials._build_income_stmt(2)
        mock_ticker = _make_mock_ticker(VALID_INFO, income_stmt=income, cashflow=pd.DataFrame())
        provider = YFinanceProvider()
        with patch(
            "finrobot.engine.data.providers.yfinance_provider.yf.Ticker",
            return_value=mock_ticker,
        ):
            result = await provider.fetch("AAPL", "financials", years=2)
        y = result.data["yearly_data"]
        assert y[0]["revenue"] == 400e9
        assert y[0]["operating_cash_flow"] is None
        assert y[0]["capital_expenditure"] is None


class TestCostOfRevenueAndEquityLegs:
    """Owner review of the EHC deep-dive — two annual-series defects.

    * The newest fiscal year's ``Cost Of Revenue`` / ``Selling General And
      Administration`` are crossed ON THE SOURCE (Yahoo's own frame: 254.4M is the
      real SG&A magnitude, 3411.1M the real cost of revenue), so the derived gross
      margin printed 95.7% against 43.9% TTM. The provider emits the raw legs —
      including the previously unread ``cost_of_revenue`` row the downstream
      plausibility guard needs — and leaves the repair to ``historical_extractor``.
    * ``total_equity`` was never read, so ``historical_metrics.shareholders_equity``
      shipped all-null while the balance sheet carried the parent equity.
    """

    @staticmethod
    def _crossed_frame() -> tuple[pd.DataFrame, pd.DataFrame]:
        newest, prior = pd.Timestamp("2025-12-31"), pd.Timestamp("2024-12-31")
        income = pd.DataFrame(
            {
                newest: {
                    "Total Revenue": 5_935_200_000.0,
                    "Cost Of Revenue": 254_400_000.0,  # crossed: the real SG&A
                    "Gross Profit": 5_680_800_000.0,  # revenue − 254.4M
                    "Selling General And Administration": 3_411_100_000.0,  # real COGS
                },
                prior: {
                    "Total Revenue": 5_373_200_000.0,
                    "Cost Of Revenue": 3_140_000_000.0,
                    "Gross Profit": 2_233_200_000.0,
                    "Selling General And Administration": 266_500_000.0,
                },
            }
        )
        balance = pd.DataFrame(
            {
                newest: {"Stockholders Equity": 2_438_200_000.0},
                prior: {"Stockholders Equity": 2_067_000_000.0},
            }
        )
        return income, balance

    @pytest.mark.asyncio
    async def test_cost_of_revenue_and_equity_legs_are_emitted(self):
        income, balance = self._crossed_frame()
        mock_ticker = _make_mock_ticker(VALID_INFO, income_stmt=income, balance_sheet=balance)
        with patch(
            "finrobot.engine.data.providers.yfinance_provider.yf.Ticker",
            return_value=mock_ticker,
        ):
            result = await YFinanceProvider().fetch("EHC", "financials", years=2)
        newest, prior = result.data["yearly_data"]
        assert newest["fiscal_year"] == "2025-12-31"
        # Raw source values, uncorrected — the guard (not the mapping) repairs them.
        assert newest["cost_of_revenue"] == 254_400_000.0
        assert newest["gross_profit"] == 5_680_800_000.0
        assert newest["sga_expense"] == 3_411_100_000.0
        assert newest["gross_margin"] == pytest.approx(0.9571, abs=1e-4)
        assert newest["total_equity"] == 2_438_200_000.0
        assert prior["total_equity"] == 2_067_000_000.0

    @pytest.mark.asyncio
    async def test_total_equity_is_none_when_the_row_is_absent(self):
        income, _balance = self._crossed_frame()
        mock_ticker = _make_mock_ticker(VALID_INFO, income_stmt=income)
        with patch(
            "finrobot.engine.data.providers.yfinance_provider.yf.Ticker",
            return_value=mock_ticker,
        ):
            result = await YFinanceProvider().fetch("EHC", "financials", years=2)
        assert result.data["yearly_data"][0]["total_equity"] is None


class TestTtmWindowMetadata:
    """Owner review: the forecast years were labelled from the wrong base — the
    DCF's ``revenue_base`` is the TTM window while the chart labels came from the
    last fiscal year, so projection year 1 rendered as "2026E" although it is the
    twelve months ending mid-2027. The snapshot must carry the TTM window end and
    its constituent quarter ends (it shipped ``fiscal_period_end=None`` /
    ``ttm_quarter_ends=[]`` before).
    """

    @staticmethod
    def _quarterly_sheet() -> pd.DataFrame:
        return pd.DataFrame(
            {
                pd.Timestamp(col): {"Stockholders Equity": 1.0}
                for col in ("2026-06-30", "2026-03-31", "2025-12-31", "2025-09-30", "2025-06-30")
            }
        )

    @pytest.mark.asyncio
    async def test_snapshot_carries_the_ttm_window_end_and_quarters(self):
        info = dict(VALID_INFO, mostRecentQuarter=1782777600)  # 2026-06-30T00:00Z
        mock_ticker = _make_mock_ticker(info, quarterly_balance_sheet=self._quarterly_sheet())
        with patch(
            "finrobot.engine.data.providers.yfinance_provider.yf.Ticker",
            return_value=mock_ticker,
        ):
            result = await YFinanceProvider().fetch("EHC", "financials")
        assert result.data["fiscal_year"] == "2026-06-30"
        assert result.data["ttm_quarter_ends"] == [
            "2026-06-30",
            "2026-03-31",
            "2025-12-31",
            "2025-09-30",
        ]

    @pytest.mark.asyncio
    async def test_window_end_falls_back_to_the_quarterly_frame(self):
        """``info.mostRecentQuarter`` is the preferred source; the quarterly
        frame's newest column is the fallback when Yahoo omits it."""
        mock_ticker = _make_mock_ticker(VALID_INFO, quarterly_balance_sheet=self._quarterly_sheet())
        with patch(
            "finrobot.engine.data.providers.yfinance_provider.yf.Ticker",
            return_value=mock_ticker,
        ):
            result = await YFinanceProvider().fetch("EHC", "financials")
        assert result.data["fiscal_year"] == "2026-06-30"

    @pytest.mark.asyncio
    async def test_annual_sheet_never_fabricates_quarter_ends(self):
        """An annual column date is a fiscal-YEAR end: publishing it as a TTM
        quarter end would make the non-overlap audit "pass" on a non-window."""
        mock_ticker = _make_mock_ticker(
            VALID_INFO, balance_sheet=_sheet({"Stockholders Equity": 1.0}, column="2025-12-31")
        )
        with patch(
            "finrobot.engine.data.providers.yfinance_provider.yf.Ticker",
            return_value=mock_ticker,
        ):
            result = await YFinanceProvider().fetch("EHC", "financials")
        assert result.data["ttm_quarter_ends"] == []
        assert result.data["fiscal_year"] is None

    @pytest.mark.asyncio
    async def test_ttm_window_is_empty_when_no_statement_is_available(self):
        mock_ticker = _make_mock_ticker(VALID_INFO)
        with patch(
            "finrobot.engine.data.providers.yfinance_provider.yf.Ticker",
            return_value=mock_ticker,
        ):
            result = await YFinanceProvider().fetch("EHC", "financials")
        assert result.data["fiscal_year"] is None
        assert result.data["ttm_quarter_ends"] == []


class TestTtmStatementLines:
    """The six income-statement lines + CapEx the flat ``info`` snapshot cannot
    supply, read off the TTM frames.

    Live evidence (NFLX, 2026-10-14): ``info`` carried no operatingIncome /
    incomeTaxExpense / depreciation / researchDevelopment /
    sellingGeneralAdministrative / interestExpense key AT ALL, so the report
    published ``null (not provided)`` for all six lines while Yahoo's own
    ``ttm_income_stmt`` held every one of them on the TTM basis the flat snapshot
    already claims. The same frame's CapEx row also replaced a sign-inverted,
    16x-too-large derivation (see ``_ttm_capex``).
    """

    @staticmethod
    def _ttm_income() -> pd.DataFrame:
        return pd.DataFrame(
            {
                pd.Timestamp("2026-06-30"): {
                    "Operating Income": 14_354_517_000.0,
                    "Tax Provision": 2_843_181_000.0,
                    "Reconciled Depreciation": 17_668_603_000.0,
                    "Research And Development": 3_711_255_000.0,
                    "Selling General And Administration": 5_692_918_000.0,
                    "Interest Expense": 847_451_000.0,
                }
            }
        )

    @staticmethod
    def _ttm_cashflow() -> pd.DataFrame:
        return pd.DataFrame(
            {
                pd.Timestamp("2026-06-30"): {
                    "Capital Expenditure": -818_828_000.0,
                    "Operating Cash Flow": 11_970_833_000.0,
                }
            }
        )

    @pytest.mark.asyncio
    async def test_six_income_lines_capex_and_beta_land_in_the_snapshot(self):
        mock_ticker = _make_mock_ticker(
            dict(VALID_INFO, beta=1.613),
            ttm_income_stmt=self._ttm_income(),
            ttm_cashflow=self._ttm_cashflow(),
        )
        with patch(
            "finrobot.engine.data.providers.yfinance_provider.yf.Ticker", return_value=mock_ticker
        ):
            result = await YFinanceProvider().fetch("NFLX", "financials")
        assert result.data["operating_income"] == 14_354_517_000.0
        assert result.data["income_tax_expense"] == 2_843_181_000.0
        assert result.data["depreciation_amortization"] == 17_668_603_000.0
        assert result.data["rd_expense"] == 3_711_255_000.0
        assert result.data["sga_expense"] == 5_692_918_000.0
        assert result.data["interest_expense"] == 847_451_000.0
        # POSITIVE magnitude — the convention ``multiples`` and ``dcf_seed``
        # assume (the annual builder emits abs(capex_raw) too).
        assert result.data["capital_expenditure"] == 818_828_000.0
        assert result.data["beta"] == 1.613
        # EBITDA on the operating caliber the projection recomputes — NOT
        # VALID_INFO's opaque 130e9 scalar, which used to leave the published
        # income table reading "EBIT + D&A = 32.0B" beside "EBITDA 14.7B".
        assert result.data["ebitda"] == 14_354_517_000.0 + 17_668_603_000.0
        # Declared basis: without it normalize_financials stamps
        # DEGRADED_PERIOD_BASIS_UNKNOWN on every yfinance run while publishing "ttm".
        assert result.data["period_basis"] == "ttm"

    @pytest.mark.asyncio
    async def test_ebitda_keeps_the_info_scalar_when_a_leg_is_missing(self):
        """Both legs or the provider's own field — never a fabricated sum."""
        mock_ticker = _make_mock_ticker(VALID_INFO)
        with patch(
            "finrobot.engine.data.providers.yfinance_provider.yf.Ticker", return_value=mock_ticker
        ):
            result = await YFinanceProvider().fetch("AAPL", "financials")
        assert result.data["ebitda"] == 130_000_000_000

    @pytest.mark.asyncio
    async def test_annual_frames_never_substitute_for_the_ttm_frames(self):
        """An annual leg inside a statement the canonical labels ``ttm`` is the
        period-mixing defect the report contract exists to prevent: the read is
        TTM-frames-only, and an absent TTM frame stays an honest None."""
        mock_ticker = _make_mock_ticker(
            VALID_INFO,
            income_stmt=pd.DataFrame(
                {pd.Timestamp("2025-12-31"): {"Operating Income": 13_326_603_000.0}}
            ),
            cashflow=pd.DataFrame(
                {pd.Timestamp("2025-12-31"): {"Capital Expenditure": -688_220_000.0}}
            ),
            ttm_income_stmt=pd.DataFrame(),
            ttm_cashflow=pd.DataFrame(),
        )
        with patch(
            "finrobot.engine.data.providers.yfinance_provider.yf.Ticker", return_value=mock_ticker
        ):
            result = await YFinanceProvider().fetch("NFLX", "financials")
        assert result.data["operating_income"] is None
        assert result.data["capital_expenditure"] is None

    @pytest.mark.asyncio
    async def test_six_lines_are_present_as_none_when_no_frame_is_available(self):
        """Keys are always present (the canonical maps them unconditionally), so
        the audit can tell "issuer does not report it" from "we never looked"."""
        mock_ticker = _make_mock_ticker(VALID_INFO)
        with patch(
            "finrobot.engine.data.providers.yfinance_provider.yf.Ticker", return_value=mock_ticker
        ):
            result = await YFinanceProvider().fetch("AAPL", "financials")
        for key in (
            "operating_income",
            "income_tax_expense",
            "depreciation_amortization",
            "rd_expense",
            "sga_expense",
            "interest_expense",
            "capital_expenditure",
        ):
            assert result.data[key] is None

    @pytest.mark.asyncio
    async def test_rate_limited_ttm_frame_does_not_fail_the_fetch(self):
        from yfinance.exceptions import YFRateLimitError

        mock_ticker = _make_mock_ticker(VALID_INFO, ttm_raises=YFRateLimitError)
        with patch(
            "finrobot.engine.data.providers.yfinance_provider.yf.Ticker", return_value=mock_ticker
        ):
            result = await YFinanceProvider().fetch("AAPL", "financials")
        assert result.data["revenue"] == 385_000_000_000
        assert result.data["operating_income"] is None
        assert result.data["capital_expenditure"] is None

    @pytest.mark.asyncio
    async def test_capex_falls_back_to_the_derivation_when_it_is_self_consistent(self):
        """No frame: ``OCF − freeCashflow`` is the pre-existing derivation and is
        still used while it is coherent (FCF ≤ OCF, i.e. capex ≥ 0)."""
        info = dict(VALID_INFO, operatingCashflow=100_000_000_000.0, freeCashflow=60_000_000_000.0)
        mock_ticker = _make_mock_ticker(info)
        with patch(
            "finrobot.engine.data.providers.yfinance_provider.yf.Ticker", return_value=mock_ticker
        ):
            result = await YFinanceProvider().fetch("AAPL", "financials")
        assert result.data["capital_expenditure"] == 40_000_000_000.0

    @pytest.mark.asyncio
    async def test_incoherent_yahoo_free_cashflow_publishes_no_capex(self):
        """Regression (live NFLX 2026-10-14): ``info.freeCashflow`` was
        25,387,552,768 against an ``operatingCashflow`` of 11,970,833,408 — Yahoo's
        own flat FCF larger than the OCF it is supposedly net of — so the old
        ``OCF − FCF`` derivation published CapEx of -13,416,719,360: sign-inverted
        (breaking the positive-magnitude convention) and 16x the statement's own
        -818,828,000, which handed ``multiples`` an FCF of +25.4B."""
        info = dict(
            VALID_INFO,
            operatingCashflow=11_970_833_408.0,
            freeCashflow=25_387_552_768.0,
        )
        mock_ticker = _make_mock_ticker(info)
        with patch(
            "finrobot.engine.data.providers.yfinance_provider.yf.Ticker", return_value=mock_ticker
        ):
            result = await YFinanceProvider().fetch("NFLX", "financials")
        assert result.data["capital_expenditure"] is None


# ---------------------------------------------------------------------------
# Integration tests (real yfinance — run manually with -m integration)
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestYFinanceIntegration:
    @pytest.mark.asyncio
    async def test_fetch_financials_real(self):
        result = await YFinanceProvider().fetch("AAPL", "financials")
        assert result.data.get("revenue") is not None
        assert result.data["revenue"] > 0

    @pytest.mark.asyncio
    async def test_fetch_price_real(self):
        result = await YFinanceProvider().fetch("AAPL", "price")
        assert len(result.data["price_history"]) > 0

    @pytest.mark.asyncio
    async def test_fetch_news_real(self):
        result = await YFinanceProvider().fetch("AAPL", "news")
        assert isinstance(result.data["news_items"], list)

    @pytest.mark.asyncio
    async def test_invalid_ticker_raises_real(self):
        with pytest.raises(ProviderError):
            await YFinanceProvider().fetch("INVALID_TICKER_XYZ_999", "financials")


class TestFlatMarginCaliber:
    """The flat snapshot's margins must come from the rows they sit beside.

    GMED 2026-10-14 published ``operating_margin`` 24.76% (Yahoo's ``info``
    operatingMargins scalar) in a snapshot whose own ``operating_income``
    673,764,000 over revenue 3,144,934,000 is 21.42% — a 3.3-point contradiction
    inside one income block, with the same shape on gross margin (68.97% scalar vs
    68.55% from the frame's own Gross Profit). Yahoo computes its margin scalars on
    a basis that is neither the same period nor the same numerator as the statement
    rows beside them, so the snapshot derives them instead.
    """

    def _frame(self) -> pd.DataFrame:
        return pd.DataFrame(
            {
                pd.Timestamp("2026-06-30"): {
                    "Total Revenue": 3_144_934_000.0,
                    "Gross Profit": 2_155_789_000.0,
                    "Operating Income": 673_764_000.0,
                    "Reconciled Depreciation": 279_913_000.0,
                }
            }
        )

    @pytest.mark.asyncio
    async def test_margins_are_derived_from_the_ttm_frame(self):
        info = dict(VALID_INFO, totalRevenue=3_144_933_888.0, grossMargins=0.68974996)
        info["operatingMargins"] = 0.24755
        mock_ticker = _make_mock_ticker(info, ttm_income_stmt=self._frame())
        with patch(
            "finrobot.engine.data.providers.yfinance_provider.yf.Ticker", return_value=mock_ticker
        ):
            result = await YFinanceProvider().fetch("GMED", "financials")
        assert result.data["operating_margin"] == pytest.approx(673_764_000.0 / 3_144_934_000.0)
        assert result.data["gross_margin"] == pytest.approx(2_155_789_000.0 / 3_144_934_000.0)
        # The published revenue stays the info scalar — only the ratios changed basis.
        assert result.data["revenue"] == 3_144_933_888.0
        # EBITDA is still the operating caliber recomputed from the same frame.
        assert result.data["ebitda"] == 673_764_000.0 + 279_913_000.0

    @pytest.mark.asyncio
    async def test_margins_fall_back_to_the_info_scalars_without_a_frame(self):
        """Gross margin may fall back to the ``info`` scalar (and is MARKED as
        provider-scalar); operating margin may NOT — without the frame's own
        Operating Income row there is no numerator-consistent margin, so it is
        withheld rather than publishing Yahoo's differently-based scalar."""
        mock_ticker = _make_mock_ticker(VALID_INFO)
        with patch(
            "finrobot.engine.data.providers.yfinance_provider.yf.Ticker", return_value=mock_ticker
        ):
            result = await YFinanceProvider().fetch("AAPL", "financials")
        assert result.data["operating_margin"] is None
        assert result.data["operating_margin_basis"] == "withheld_no_operating_income_row"
        assert result.data["gross_margin"] == 0.44
        assert result.data["gross_margin_basis"] == "provider_scalar"
        assert any("info.grossMargins scalar" in w for w in result.warnings)
        assert any("operating_margin withheld" in w for w in result.warnings)

    @pytest.mark.asyncio
    async def test_operating_margin_withheld_when_frame_lacks_operating_income(self):
        """F6(a) THC: the TTM frame carried Gross Profit + Revenue but no Operating
        Income, so the snapshot published Yahoo's 18.2% operatingMargins scalar
        beside an unreported ``operating_income``. The row-derived gross margin is
        published, the operating margin is withheld, and both bases are marked."""
        frame = pd.DataFrame(
            {
                pd.Timestamp("2026-06-30"): {
                    "Total Revenue": 22_638_000_000.0,
                    "Gross Profit": 18_752_000_000.0,
                }
            }
        )
        info = dict(
            VALID_INFO,
            totalRevenue=22_638_000_000.0,
            grossMargins=0.41661,
            operatingMargins=0.18159,
        )
        info.pop("sharesOutstanding", None)
        mock_ticker = _make_mock_ticker(info, ttm_income_stmt=frame)
        with patch(
            "finrobot.engine.data.providers.yfinance_provider.yf.Ticker", return_value=mock_ticker
        ):
            result = await YFinanceProvider().fetch("THC", "financials")
        assert result.data["gross_margin"] == pytest.approx(18_752_000_000.0 / 22_638_000_000.0)
        assert result.data["gross_margin_basis"] == "row"
        assert result.data["operating_margin"] is None
        assert result.data["operating_margin_basis"] == "withheld_no_operating_income_row"

    @pytest.mark.asyncio
    async def test_nci_earnings_read_from_the_ttm_frame(self):
        """F2: the NCI share of TTM earnings is read off the same income frame
        (consolidated − parent), so the SEC-vs-provider net-income gap can be named
        as a caliber difference. THC: 3,174 − 2,241 = 933M."""
        frame = pd.DataFrame(
            {
                pd.Timestamp("2026-06-30"): {
                    "Total Revenue": 22_638_000_000.0,
                    "Net Income Including Noncontrolling Interests": 3_174_000_000.0,
                    "Net Income Common Stockholders": 2_241_000_000.0,
                    "Minority Interests": -933_000_000.0,
                }
            }
        )
        mock_ticker = _make_mock_ticker(VALID_INFO, ttm_income_stmt=frame)
        with patch(
            "finrobot.engine.data.providers.yfinance_provider.yf.Ticker", return_value=mock_ticker
        ):
            result = await YFinanceProvider().fetch("THC", "financials")
        assert result.data["nci_earnings"] == pytest.approx(933_000_000.0)
        assert any("noncontrolling" in w and "parent" in w for w in result.warnings)

    @pytest.mark.asyncio
    async def test_beta_retried_once_when_info_omits_it(self):
        """F6(b) THC: the first ``info`` page carried no beta while the source
        reports 1.199. One retry recovers it; otherwise beta stays None."""
        info_without_beta = dict(VALID_INFO)
        info_without_beta.pop("beta", None)
        info_with_beta = dict(VALID_INFO, beta=1.199)
        read = iter([info_without_beta, info_with_beta])

        class _BetaTicker(MagicMock):
            # A real property on a LOCAL subclass — a property set on MagicMock
            # itself would leak across the whole test session.
            @property
            def info(self) -> dict:
                return next(read, info_with_beta)

        mock_ticker = _BetaTicker()
        with patch(
            "finrobot.engine.data.providers.yfinance_provider.yf.Ticker", return_value=mock_ticker
        ):
            result = await YFinanceProvider().fetch("THC", "financials")
        assert result.data["beta"] == pytest.approx(1.199)
