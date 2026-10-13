"""Unit tests for the EODHD PRICE_RANGE arm (no network).

The arm exists because PRICE is a trailing ~1y window: the fund pipeline needs a
6-year NAV series (a window of N years needs N*252+1 points) and the backtest
engine needs a caller-chosen window, neither of which PRICE can serve. Before
this was declared, every such fetch logged "not supported by EODHD" and fell
through to yfinance although /eod has always accepted from/to.

The rows below are real-shaped EODHD /eod rows
(``date/open/high/low/close/adjusted_close/volume``), and the unit-critical
assertion is that ``close`` is read from ``adjusted_close``: reading the raw
``close`` would hand the caller an unadjusted, split-broken series while every
other provider serves an adjusted one (FMP ``adjClose``, yfinance
``auto_adjust=True``).

Both doors share one bar mapper, so the basis is pinned once here — a split inside
the window must not leak a pre-split price into the series (see TestSplitBasis for
the live 10x that motivated it).
"""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from finrobot.engine.data.interface import DataResult, ProviderError
from finrobot.engine.data.providers.eodhd_provider import EODHDProvider
from finrobot.engine.data.types import DataType

#: Two real-shaped /eod rows. ``close`` and ``adjusted_close`` DIFFER on purpose:
#: 2020-08-31 is Apple's 4:1 split date, where the raw close (129.04) is the
#: pre-split print and the adjusted close (32.26) is the restated one — so a
#: wrong read shows up in the assertion instead of hiding as a small slip.
_ROWS: list[dict[str, object]] = [
    {
        "date": "2020-08-28",
        "open": 126.01,
        "high": 126.44,
        "low": 124.58,
        "close": 124.81,
        "adjusted_close": 124.81,
        "volume": 187_630_000,
    },
    {
        "date": "2020-08-31",
        "open": 127.58,
        "high": 131.0,
        "low": 126.0,
        "close": 129.04,
        "adjusted_close": 32.26,
        "volume": 225_178_000,
    },
]


@contextmanager
def _provider_with(rows: object) -> Generator[tuple[EODHDProvider, AsyncMock]]:
    """Provider whose ``_get`` answers with ``rows`` (no network)."""
    provider = EODHDProvider("test-token")
    response = httpx.Response(
        200,
        request=httpx.Request("GET", "https://eodhd.com/api/eod/AAPL"),
        json=rows,
    )
    mock = AsyncMock(return_value=response)
    with patch.object(provider, "_get", mock):
        yield provider, mock


async def _fetch(provider: EODHDProvider, **kwargs: object) -> DataResult:
    return await provider.fetch(
        "AAPL", DataType.PRICE_RANGE, start="2020-08-01", end="2020-09-01", **kwargs
    )


class TestRequestShape:
    async def test_window_and_period_reach_the_endpoint(self) -> None:
        with _provider_with(_ROWS) as (provider, mock):
            await _fetch(provider)
            assert mock.call_args.args[0] == "/eod/AAPL"
            assert mock.call_args.kwargs["params"] == {
                "from": "2020-08-01",
                "to": "2020-09-01",
                "period": "d",
                "fmt": "json",
            }

    async def test_interval_maps_to_the_vendor_period_code(self) -> None:
        for interval, period in (("1d", "d"), ("1wk", "w"), ("1mo", "m")):
            with _provider_with(_ROWS) as (provider, mock):
                await _fetch(provider, interval=interval)
                assert mock.call_args.kwargs["params"]["period"] == period

    async def test_unsupported_interval_is_refused_without_a_request(self) -> None:
        """Serving a 5-minute request at daily resolution would mislabel the
        series; the arm refuses instead (FMP takes the same position)."""
        with _provider_with(_ROWS) as (provider, mock):
            with pytest.raises(ProviderError, match="intervals"):
                await _fetch(provider, interval="5m")
            mock.assert_not_called()

    async def test_empty_window_is_an_error_not_an_empty_series(self) -> None:
        with _provider_with([]) as (provider, _):
            with pytest.raises(ProviderError, match="no bars"):
                await _fetch(provider)


#: One NFLX row from BEFORE its real 10:1 split (2025-11-17), as /eod returns it:
#: the traded close sits beside the split-restated one. The factor is exactly 0.1.
_SPLIT_ROW: dict[str, object] = {
    "date": "2025-11-14",
    "open": 1240.0,
    "high": 1250.0,
    "low": 1230.0,
    "close": 1248.6,
    "adjusted_close": 124.86,
    "volume": 3_000_000,
}


class TestSplitBasis:
    """A split inside the window must not leak a pre-split price into the series.

    Measured live 2026-10-12 on NFLX (10:1 split 2025-11-17): reading the traded
    ``close`` put the canonical PRICE's 52-week high at **1248.60** against a
    split-adjusted 124.86 and published a -94.2% trailing return where the adjusted
    series gives roughly -40%. Both figures come from the same bars, so nothing in
    the run flagged the 10x — it reached the report header unflagged.
    """

    async def test_price_door_serves_the_adjusted_series(self) -> None:
        rows = [
            _SPLIT_ROW,
            {
                "date": "2025-11-17",
                "open": 125.0,
                "high": 126.0,
                "low": 124.0,
                "close": 125.5,
                "adjusted_close": 125.5,
                "volume": 9_000_000,
            },
        ]
        provider = EODHDProvider("test-token")
        response = httpx.Response(
            200,
            request=httpx.Request("GET", "https://eodhd.com/api/eod/NFLX"),
            json=rows,
        )
        with patch.object(provider, "_get", AsyncMock(return_value=response)):
            result = await provider.fetch("NFLX", DataType.PRICE)

        closes = [bar["close"] for bar in result.data["price_history"]]
        assert closes == [124.86, 125.5]
        # A raw read would make the 52-week high 1248.6 — the live failure.
        assert max(closes) < 200

    async def test_split_bar_scales_ohlc_so_the_bar_stays_consistent(self) -> None:
        with _provider_with([_SPLIT_ROW]) as (provider, _):
            result = await _fetch(provider)

        bar = result.data["bars"][0]
        assert bar["close"] == pytest.approx(124.86)
        assert bar["open"] == pytest.approx(124.0)
        assert bar["high"] == pytest.approx(125.0)
        assert bar["low"] == pytest.approx(123.0)
        assert bar["low"] <= bar["close"] <= bar["high"]


class TestBars:
    async def test_close_comes_from_the_adjusted_column(self) -> None:
        with _provider_with(_ROWS) as (provider, _):
            result = await _fetch(provider)
        assert [bar["close"] for bar in result.data["bars"]] == [124.81, 32.26]
        assert result.data["adjusted"] is True
        assert result.data["interval"] == "1d"
        assert result.data["source_provider"] == "eodhd"
        assert result.data_type == DataType.PRICE_RANGE

    async def test_bars_are_ascending_even_when_the_vendor_reverses(self) -> None:
        with _provider_with(list(reversed(_ROWS))) as (provider, _):
            result = await _fetch(provider)
        assert [bar["date"] for bar in result.data["bars"]] == ["2020-08-28", "2020-08-31"]

    async def test_missing_adjusted_column_falls_back_to_raw_close(self) -> None:
        """A symbol with no adjusted column keeps its raw close (the bar is
        retained) and the payload stops claiming to be fully adjusted."""
        with _provider_with([{**_ROWS[0], "adjusted_close": None}]) as (provider, _):
            result = await _fetch(provider)
        assert result.data["bars"][0]["close"] == 124.81
        assert result.data["adjusted"] is False

    async def test_rows_without_a_date_or_close_are_skipped(self) -> None:
        rows: list[object] = [*_ROWS, {"date": "2020-09-02"}, "not-a-row", {"close": 1.0}]
        with _provider_with(rows) as (provider, _):
            result = await _fetch(provider)
        assert len(result.data["bars"]) == 2
