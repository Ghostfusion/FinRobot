"""FX normalisation of the historical-band loader (W3-A路 · Bug B).

Foreign ADRs (TSM/SONY/BABA) have FMP report their yearly statements in the
native currency (financial_currency=TWD/JPY) while the ADR trades — and the
band's price history is fetched — in the quote currency (USD). The yearly
EBITDA / net-debt must therefore be converted to the quote currency BEFORE they
meet the USD price in ``_compute_multiple``; otherwise EV/EBITDA mixes
currencies and collapses (TSM live band came out ~0.05x instead of ~23x).

These tests pin the conversion using FMP's real TSM payload shape and confirm
the same-currency (US issuer) path is left untouched.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from types import SimpleNamespace

import pytest

from finrobot.engine.data.historical_loaders import (
    load_yearly_financials,
    resolve_band_shares,
)
from finrobot.engine.data.interface import DataResult, ProviderError
from finrobot.engine.primitives.historical_valuation import PricePoint, YearlyFinancials


class _FXStubLayer:
    """fetch_historical returns native-currency financials + a quote currency.

    Mirrors the FMP TSM payload: statements in TWD, ADR quoted in USD. Records
    the (reporting, quote) pairs requested so the test can assert the loader
    converts exactly once.
    """

    def __init__(self, *, fin_ccy: str, quote_ccy: str, rate: float) -> None:
        self._fin_ccy = fin_ccy
        self._quote_ccy = quote_ccy
        self._rate = rate
        self.rate_calls: list[tuple[str, str]] = []

    async def fetch_historical(self, data_type: str, ticker: str, years: int) -> list[DataResult]:
        return [
            DataResult(
                data={
                    "fiscal_year": "2024-12-31",
                    "ebitda": 2_752_481_885_000,  # native (TWD for TSM)
                    "total_debt": 1_064_582_700_000,
                    "total_cash": 3_128_297_700_000,
                    "shares_outstanding": 5_180_000_000,
                    "financial_currency": self._fin_ccy,
                    "quote_currency": self._quote_ccy,
                },
                provider="stub",
                ticker=ticker,
                data_type=data_type,
                timestamp=datetime.now(tz=timezone.utc),
            )
        ]

    async def reporting_to_quote_rate(self, reporting_ccy: str, quote_ccy: str) -> float:
        self.rate_calls.append((reporting_ccy, quote_ccy))
        return self._rate


@pytest.mark.asyncio
async def test_load_yearly_financials_fx_normalizes_adr_to_quote_currency():
    rate = 0.0312  # 1 TWD ≈ 0.0312 USD
    layer = _FXStubLayer(fin_ccy="TWD", quote_ccy="USD", rate=rate)

    out = await load_yearly_financials("TSM", layer, years=3)

    assert len(out) == 1
    yf, shares = out[0]
    # EBITDA must be the USD-converted figure, not the raw TWD trillions.
    assert yf.ebitda == pytest.approx(2_752_481_885_000 * rate)
    # net_debt = (total_debt − total_cash) also converted to the quote currency.
    assert yf.net_debt == pytest.approx((1_064_582_700_000 - 3_128_297_700_000) * rate)
    # Share count is currency-neutral — never scaled.
    assert shares == 5_180_000_000
    # Rate fetched exactly once (per ticker, not per year).
    assert layer.rate_calls == [("TWD", "USD")]


@pytest.mark.asyncio
async def test_load_yearly_financials_no_fx_for_same_currency():
    # US issuer: financial_currency == quote_currency → no FX call, raw values kept.
    layer = _FXStubLayer(fin_ccy="USD", quote_ccy="USD", rate=0.5)

    out = await load_yearly_financials("AAPL", layer, years=3)

    yf, _ = out[0]
    assert yf.ebitda == pytest.approx(2_752_481_885_000)  # untouched (rate not applied)
    assert layer.rate_calls == []


class _SharesFallbackLayer:
    """Yearly rows WITHOUT a shares key, plus a canonical FINANCIALS payload.

    That is the production shape whenever FMP is unavailable: only FMP's yearly
    builder emits ``shares_outstanding`` (newest year only), so yfinance's and the
    SEC companyfacts builder's rows are shares-less and the band used to be
    withheld entirely. Live 2026-10-12 on NFLX: P/E bands AND both Football-Field
    reverse multiples dropped although the canonical count (4.16B) was one call
    away.
    """

    def __init__(self, *, canonical_shares: float | None) -> None:
        self._canonical_shares = canonical_shares
        self.canonical_calls = 0

    async def fetch_canonical(self, data_type, ticker):  # type: ignore[no-untyped-def]
        self.canonical_calls += 1
        if self._canonical_shares is None:
            raise ProviderError("canonical financials unavailable")
        return SimpleNamespace(shares_outstanding=self._canonical_shares)


def _yearly_with(shares: float | None) -> list[tuple[YearlyFinancials, float | None]]:
    return [
        (
            YearlyFinancials(
                fiscal_date=date(2024, 12, 31),
                ebitda=10_000_000.0,
                free_cash_flow=8_000_000.0,
                net_debt=0.0,
            ),
            shares,
        )
    ]


async def test_band_shares_prefers_the_per_year_count():
    """A per-year count is the honest input: no fallback call, no disclosure."""
    layer = _SharesFallbackLayer(canonical_shares=9_000_000_000.0)
    shares, disclosure = await resolve_band_shares("VZ", _yearly_with(4_200_000_000.0), layer)

    assert shares == 4_200_000_000.0
    assert disclosure is None
    assert layer.canonical_calls == 0


async def test_band_shares_does_not_fetch_without_optin():
    """A band call must not add I/O the caller did not ask for: the preloaded
    pipeline context asserts the layer is never touched, so the canonical lookup is
    opt-in (`allow_fetch`) or supplied by the caller (`override`). Without either,
    the band keeps its pre-fallback behaviour — withheld, warning intact."""
    layer = _SharesFallbackLayer(canonical_shares=4_163_939_676.0)
    shares, disclosure = await resolve_band_shares("NFLX", _yearly_with(None), layer)

    assert (shares, disclosure) == (None, None)
    assert layer.canonical_calls == 0


async def test_band_shares_prefers_the_callers_own_count_without_fetching():
    """The pipeline passes the DCF's share count: same number as the report's other
    panels, no fetch, and the approximation is still disclosed."""
    layer = _SharesFallbackLayer(canonical_shares=9_999_999_999.0)
    shares, disclosure = await resolve_band_shares(
        "NFLX", _yearly_with(None), layer, override=4_163_939_676.0
    )

    assert shares == pytest.approx(4_163_939_676.0)
    assert layer.canonical_calls == 0
    assert disclosure is not None
    assert "the run's own share count" in disclosure


async def test_band_shares_ignores_a_non_numeric_override():
    """A test double (MagicMock) must not be compared or trusted as a count."""
    layer = _SharesFallbackLayer(canonical_shares=4_163_939_676.0)
    shares, disclosure = await resolve_band_shares(
        "NFLX",
        _yearly_with(None),
        layer,
        override=object(),  # type: ignore[arg-type]
    )

    assert (shares, disclosure) == (None, None)
    assert layer.canonical_calls == 0


async def test_band_shares_fetches_only_when_the_caller_opts_in():
    layer = _SharesFallbackLayer(canonical_shares=4_163_939_676.0)
    shares, disclosure = await resolve_band_shares(
        "NFLX", _yearly_with(None), layer, allow_fetch=True
    )

    assert shares == pytest.approx(4_163_939_676.0)
    assert layer.canonical_calls == 1
    # The reader must see WHICH count priced the band, and why it is approximate.
    assert "4,163,939,676" in disclosure
    assert "current share count" in disclosure
    assert "buyback or issuance history makes the earlier multiples approximate" in disclosure


async def test_band_shares_gives_up_when_the_fetch_finds_nothing():
    layer = _SharesFallbackLayer(canonical_shares=None)
    shares, disclosure = await resolve_band_shares(
        "ZZZZ", _yearly_with(None), layer, allow_fetch=True
    )

    assert shares is None
    assert disclosure is None


async def test_bands_compute_on_the_supplied_count_and_disclose_it(monkeypatch):
    """The NFLX shape end to end: shares-less yearly rows + the caller's count must
    produce a band (not an empty one) that carries the disclosure — with no fetch."""
    from finrobot.engine.data import historical_loaders as loaders

    async def fake_yearly(ticker, data_layer, years):
        return _yearly_with(None)

    async def fake_prices(ticker, data_layer, years):
        return [PricePoint(sample_date=date(2024, 12, 31), close=100.0)]

    monkeypatch.setattr(loaders, "load_yearly_financials", fake_yearly)
    monkeypatch.setattr(loaders, "load_price_history", fake_prices)

    layer = _SharesFallbackLayer(canonical_shares=4_163_939_676.0)
    band = await loaders.compute_bands_via_data_layer(
        "NFLX", "ev_ebitda", 5, layer, shares_override=4_163_939_676.0
    )

    assert band.sample_count > 0
    assert layer.canonical_calls == 0
    assert any("share count" in w for w in band.warnings), band.warnings


class _FXFailLayer(_FXStubLayer):
    async def reporting_to_quote_rate(self, reporting_ccy: str, quote_ccy: str) -> float:
        from finrobot.engine.data.interface import ProviderError

        raise ProviderError("FX provider down")


@pytest.mark.asyncio
async def test_load_yearly_financials_fx_unavailable_refuses_band():
    """FX due but unavailable must NOT silently apply 1.0: the band's multiple
    mixes the native financial leg with the USD price leg in one number — the
    ~0.05x TSM garbage. The loader refuses (empty → no band) instead, honoring
    fx.py's 'never fall back to 1.0' contract (the canonical path's sibling)."""
    layer = _FXFailLayer(fin_ccy="TWD", quote_ccy="USD", rate=0.0)

    out = await load_yearly_financials("TSM", layer, years=3)

    assert out == []


class _MissingBalanceLayer(_FXStubLayer):
    async def fetch_historical(self, data_type: str, ticker: str, years: int) -> list[DataResult]:
        rows = await super().fetch_historical(data_type, ticker, years)
        # Simulate a year whose balance rows failed to align: debt/cash absent.
        del rows[0].data["total_debt"]
        del rows[0].data["total_cash"]
        return rows


@pytest.mark.asyncio
async def test_load_yearly_financials_missing_balance_leg_keeps_net_debt_none():
    """None ≠ 0: a missing balance leg means UNKNOWN net debt — filling 0
    fabricated a debt-free EV (band skewed low for levered issuers). The year
    keeps net_debt=None and the EV/EBITDA sample for it is skipped by
    _compute_multiple."""
    layer = _MissingBalanceLayer(fin_ccy="USD", quote_ccy="USD", rate=1.0)

    out = await load_yearly_financials("AAPL", layer, years=3)

    yf, _ = out[0]
    assert yf.net_debt is None


# ---------------------------------------------------------------------------
# fetch_reverse_multiple_band — the door that revives the EV/EBITDA reverse row.
# Pins: a real band yields (p25, p75) + sample_count; a too-thin band is withheld
# (no degenerate point); a degenerate/non-positive band is withheld.
# ---------------------------------------------------------------------------


def _band(*, p25, p75, sample_count, current=24.0):
    from finrobot.engine.primitives.historical_valuation import HistoricalBand

    return HistoricalBand(
        metric="ev_ebitda",
        current=current,
        median=(p25 + p75) / 2 if p25 and p75 else None,
        p25=p25,
        p75=p75,
        p90=p75,
        timeline=[],
        sample_count=sample_count,
        warnings=[],
    )


@pytest.mark.asyncio
async def test_fetch_reverse_multiple_band_returns_spread(monkeypatch):
    from finrobot.engine.data import historical_loaders as hl

    async def _fake(ticker, metric, years, data_layer, *, current_override=None):
        return _band(p25=20.0, p75=30.0, sample_count=900)

    monkeypatch.setattr(hl, "compute_bands_via_data_layer", _fake)
    spread = await hl.fetch_reverse_multiple_band("AAPL", "ev_ebitda", object())
    assert spread is not None
    assert (spread.p25, spread.p75, spread.sample_count) == (20.0, 30.0, 900)


@pytest.mark.asyncio
async def test_fetch_reverse_multiple_band_withholds_thin_history(monkeypatch):
    """Below the sample floor the band carries no distribution — p25/p75 would
    echo one multiple dressed as a range. Withhold rather than emit a fake range."""
    from finrobot.engine.data import historical_loaders as hl

    async def _fake(ticker, metric, years, data_layer, *, current_override=None):
        return _band(p25=23.0, p75=23.0, sample_count=hl._MIN_BAND_SAMPLES - 1)

    monkeypatch.setattr(hl, "compute_bands_via_data_layer", _fake)
    assert await hl.fetch_reverse_multiple_band("IPO", "ev_ebitda", object()) is None


@pytest.mark.asyncio
async def test_fetch_reverse_multiple_band_withholds_nonpositive_band(monkeypatch):
    from finrobot.engine.data import historical_loaders as hl

    async def _fake(ticker, metric, years, data_layer, *, current_override=None):
        return _band(p25=None, p75=None, sample_count=900)

    monkeypatch.setattr(hl, "compute_bands_via_data_layer", _fake)
    assert await hl.fetch_reverse_multiple_band("X", "ev_ebitda", object()) is None


@pytest.mark.asyncio
async def test_fetch_reverse_multiple_band_none_layer_returns_none():
    from finrobot.engine.data import historical_loaders as hl

    assert await hl.fetch_reverse_multiple_band("X", "ev_ebitda", None) is None
