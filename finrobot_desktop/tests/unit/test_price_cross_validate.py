"""Tests for cross-source current-price validation (ADR-0004 §6 open question H).

Pure-function band tests plus an integration test proving ``fetch_price`` pulls a
SECOND provider's QUOTE on cache-miss and surfaces a divergence warning — while a
secondary failure never blocks the primary price.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from finrobot.engine.data.cache import DataCache
from finrobot.engine.data.interface import DataProvider, DataResult
from finrobot.engine.data.layer import DataLayer
from finrobot.engine.data.normalize.contracts import degraded_price_divergence
from finrobot.engine.data.types import DataType
from finrobot.engine.data.validator import cross_validate_price


def _price_result(
    provider: str, *, current: float | None = None, quote: float | None = None
) -> DataResult:
    data: dict[str, float] = {}
    if current is not None:
        data["current_price"] = current
    if quote is not None:
        data["price"] = quote
    return DataResult(
        data=data,
        provider=provider,
        ticker="AAPL",
        data_type=DataType.PRICE,
        timestamp=datetime.now(tz=timezone.utc),
    )


def test_agreeing_prices_no_warning() -> None:
    # FMP PRICE (current_price) vs yfinance QUOTE (price), within 5%.
    primary = _price_result("fmp", current=311.23)
    secondary = _price_result("yfinance", quote=311.20)
    assert cross_validate_price(primary, secondary) == []


def test_split_unadjusted_divergence_flagged() -> None:
    # ~2× mismatch (one side missed a 2:1 split) → must warn.
    primary = _price_result("fmp", current=311.23)
    secondary = _price_result("yfinance", quote=155.60)
    warns = cross_validate_price(primary, secondary)
    assert len(warns) == 1
    assert "Price discrepancy" in warns[0]
    assert "311.23" in warns[0] and "155.60" in warns[0]


def test_just_within_tolerance_silent() -> None:
    # 4% gap — under the 5% band, tolerate (delayed feed on a volatile session).
    primary = _price_result("fmp", current=100.0)
    secondary = _price_result("yfinance", quote=96.0)
    assert cross_validate_price(primary, secondary) == []


def test_just_over_tolerance_flagged() -> None:
    primary = _price_result("fmp", current=100.0)
    secondary = _price_result("yfinance", quote=93.0)  # 7% gap
    assert len(cross_validate_price(primary, secondary)) == 1


def _priced(provider: str, value: float, *, session: str | None) -> DataResult:
    """A price result, optionally stamped with the bar session it is the close OF.

    ``session=None`` reproduces a bare quote payload (``{"price": …}`` — yfinance's
    ``fast_info.last_price``): no bars, so no session at all.
    """
    data: dict[str, object] = {"current_price": value}
    if session is not None:
        data["price_history"] = [{"date": session, "close": value}]
    return DataResult(
        data=data,
        provider=provider,
        ticker="CRWV",
        data_type=DataType.PRICE,
        timestamp=datetime.now(tz=timezone.utc),
    )


def test_a_dated_close_versus_an_unstamped_quote_is_not_asserted_to_be_a_bad_value() -> None:
    """2026-10-16 CRWV: EODHD served the 2026-10-15 daily-bar close 69.69 (its
    ``/eod`` payload carries the bars) while the yfinance cross-check quote 62.12
    carried no session stamp at all — a live intraday print. Both numbers were
    right; the 11% "discrepancy" line named a suspected split/stale value/mistake
    on a comparison of two different instants. The warning must state each side's
    instant and stop asserting the cause it cannot see."""
    warns = cross_validate_price(
        _priced("eodhd", 69.69, session="2026-10-15"),
        _priced("yfinance", 62.12, session=None),
    )
    assert len(warns) == 1
    assert "the 2026-10-15 session close" in warns[0]
    assert "no session stamp on the quote" in warns[0]
    assert "not established to be the same bar session" in warns[0]
    assert "69.69" in warns[0] and "62.12" in warns[0]
    assert "Possible stale or split-unadjusted price, wrong ticker" not in warns[0]


def test_two_different_session_closes_are_also_not_a_value_disagreement() -> None:
    warns = cross_validate_price(
        _priced("eodhd", 69.69, session="2026-10-15"),
        _priced("yfinance", 58.0, session="2026-10-08"),
    )
    assert len(warns) == 1
    assert "the 2026-10-15 session close" in warns[0]
    assert "the 2026-10-08 session close" in warns[0]
    assert "not established to be the same bar session" in warns[0]


def test_a_same_session_divergence_keeps_the_value_disagreement_wording() -> None:
    """The band's own claim — two values for the SAME session that differ beyond
    tolerance — keeps its sharper reading (the split / stale-feed case)."""
    warns = cross_validate_price(
        _priced("eodhd", 100.0, session="2026-10-15"),
        _priced("yfinance", 90.0, session="2026-10-15"),
    )
    assert len(warns) == 1
    assert "Both sides name the same bar session" in warns[0]
    assert "value disagreement" in warns[0]


def test_two_unstamped_quotes_are_not_declared_the_same_instant() -> None:
    """Two bare quotes still warn (the ~2x split tripwire), but neither is
    established to be the same instant, so the line says that instead of asserting
    which side is wrong."""
    warns = cross_validate_price(
        _priced("eodhd", 311.23, session=None),
        _priced("yfinance", 155.60, session=None),
    )
    assert len(warns) == 1
    assert "no session stamp on the quote" in warns[0]
    assert "not established to be the same bar session" in warns[0]


def test_missing_secondary_price_abstains() -> None:
    primary = _price_result("fmp", current=311.23)
    empty = _price_result("yfinance")
    assert cross_validate_price(primary, empty) == []


def test_nonpositive_price_abstains() -> None:
    primary = _price_result("fmp", current=311.23)
    zero = _price_result("yfinance", quote=0.0)
    assert cross_validate_price(primary, zero) == []


# --- integration: fetch_price wiring ----------------------------------------


class _StubProvider(DataProvider):
    def __init__(
        self, name_: str, caps: list[str], price_val: float, *, quote_raises: bool = False
    ):
        self._name = name_
        self._caps = caps
        self._price = price_val
        self._quote_raises = quote_raises
        self.quote_calls = 0

    @property
    def name(self) -> str:
        return self._name

    def capabilities(self) -> list[str]:
        return self._caps

    async def fetch(self, ticker: str, data_type: str, **kwargs: object) -> DataResult:
        if data_type == DataType.QUOTE:
            self.quote_calls += 1
            if self._quote_raises:
                from finrobot.engine.data.interface import ProviderError

                raise ProviderError("quote down")
            return DataResult(
                data={"price": self._price},
                provider=self._name,
                ticker=ticker,
                data_type=DataType.QUOTE,
                timestamp=datetime.now(tz=timezone.utc),
            )
        return DataResult(
            data={"current_price": self._price, "price_history": []},
            provider=self._name,
            ticker=ticker,
            data_type=DataType.PRICE,
            timestamp=datetime.now(tz=timezone.utc),
        )


@pytest.fixture
async def cache(tmp_path):
    c = DataCache(db_path=str(tmp_path / "price_xval.db"))
    try:
        yield c
    finally:
        await c.close()


async def test_fetch_price_flags_cross_source_divergence(cache) -> None:
    primary = _StubProvider("fmp", [DataType.PRICE, DataType.QUOTE], 311.23)
    secondary = _StubProvider("yfinance", [DataType.PRICE, DataType.QUOTE], 155.60)  # ~2× off
    layer = DataLayer([primary, secondary], cache)
    result = await layer.fetch_price("AAPL")
    assert result.provider == "fmp"  # primary still wins
    assert secondary.quote_calls == 1  # second provider probed via QUOTE only
    assert any("Price discrepancy" in w for w in result.warnings)
    assert result.price_field_divergences == ["current_price"]


async def test_fetch_price_silent_when_sources_agree(cache) -> None:
    primary = _StubProvider("fmp", [DataType.PRICE, DataType.QUOTE], 311.23)
    secondary = _StubProvider("yfinance", [DataType.PRICE, DataType.QUOTE], 311.10)
    layer = DataLayer([primary, secondary], cache)
    result = await layer.fetch_price("AAPL")
    assert not any("Price discrepancy" in w for w in result.warnings)


async def test_fetch_price_survives_secondary_quote_failure(cache) -> None:
    primary = _StubProvider("fmp", [DataType.PRICE, DataType.QUOTE], 311.23)
    secondary = _StubProvider(
        "yfinance", [DataType.PRICE, DataType.QUOTE], 155.60, quote_raises=True
    )
    layer = DataLayer([primary, secondary], cache)
    result = await layer.fetch_price("AAPL")  # must not raise
    assert result.data["current_price"] == 311.23
    assert not any("Price discrepancy" in w for w in result.warnings)


async def test_fetch_canonical_price_uses_validated_price_path(cache) -> None:
    primary = _StubProvider("fmp", [DataType.PRICE, DataType.QUOTE], 311.23)
    secondary = _StubProvider("yfinance", [DataType.PRICE, DataType.QUOTE], 155.60)
    layer = DataLayer([primary, secondary], cache)

    result = await layer.fetch_canonical(DataType.PRICE, "AAPL")

    assert result.provenance.provider == "fmp"
    assert secondary.quote_calls == 1
    assert any("Price discrepancy" in w for w in result.warnings)
    assert degraded_price_divergence("current_price") in result.provenance.degraded
