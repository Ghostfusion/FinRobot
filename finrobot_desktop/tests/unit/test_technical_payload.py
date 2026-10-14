"""Unit tests for engine.compute.technical_payload.

Covers the three branches (Monte Carlo + Sniper + Historical Bands) and
their graceful degradation when individual data sources are missing.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from finrobot.engine.compute.coordinators.technical_payload import (
    HistoricalBandSnapshot,
    TechnicalAnalysis,
    build_technical_analysis,
)
from finrobot.engine.data.interface import DataResult
from finrobot.engine.data.normalize.contracts import NormalizedPrice, PriceBar, Provenance
from finrobot.engine.data.types import DataType
from finrobot.engine.models.financial import DCFInputs


def _dcf_inputs() -> DCFInputs:
    """A realistic 5y growth profile that yields a stable MC distribution."""
    return DCFInputs(
        revenue_base=400_000_000_000.0,
        revenue_growth_rates=[0.06, 0.05, 0.04, 0.04, 0.03],
        ebitda_margin=0.30,
        capex_pct_revenue=0.06,
        nwc_pct_revenue=0.02,
        da_pct_revenue=0.05,
        tax_rate=0.21,
        risk_free_rate=0.04,
        beta=1.2,
        equity_risk_premium=0.05,
        cost_of_debt=0.04,
        debt_ratio=0.25,
        terminal_growth_rate=0.025,
        shares_outstanding=15_500_000_000.0,
        net_debt=60_000_000_000.0,
    )


class _StubDataLayer:
    """Returns deterministic price + historical-financials payloads."""

    def __init__(self, *, with_price: bool = True, with_history: bool = True) -> None:
        self.with_price = with_price
        self.with_history = with_history

    async def fetch(self, data_type: str, ticker: str) -> DataResult:
        if data_type == "price" and self.with_price:
            history = [{"date": f"2025-{m:02d}-01", "close": 150.0 + m} for m in range(1, 13)]
            return DataResult(
                data={"current_price": 162.0, "price_history": history},
                provider="stub",
                ticker=ticker,
                data_type="price",
                timestamp=datetime.now(tz=timezone.utc),
            )
        return DataResult(
            data={},
            provider="stub",
            ticker=ticker,
            data_type=data_type,
            timestamp=datetime.now(tz=timezone.utc),
        )

    async def fetch_canonical(self, data_type: DataType | str, ticker: str) -> NormalizedPrice:
        if DataType(data_type) != DataType.PRICE:
            raise ValueError(f"unsupported canonical type: {data_type}")
        raw = await self.fetch(DataType.PRICE.value, ticker)
        timestamp = raw.timestamp
        if not self.with_price:
            return NormalizedPrice(
                ticker=ticker,
                current_price=0.0,
                bars=[],
                provenance=Provenance(provider="stub", as_of=timestamp, fetched_at=timestamp),
            )
        bars = [
            PriceBar(
                date=datetime.fromisoformat(str(row["date"])).date(), close=float(row["close"])
            )
            for row in raw.data["price_history"]
        ]
        return NormalizedPrice(
            ticker=ticker,
            current_price=float(raw.data["current_price"]),
            bars=bars,
            provenance=Provenance(provider="stub", as_of=timestamp, fetched_at=timestamp),
        )

    async def fetch_price_range(self, ticker: str, start: str, end: str) -> list[PriceBar]:
        if not self.with_price:
            return []
        raw = await self.fetch(DataType.PRICE.value, ticker)
        return [
            PriceBar(
                date=datetime.fromisoformat(str(row["date"])).date(), close=float(row["close"])
            )
            for row in raw.data["price_history"]
        ]

    async def fetch_historical(self, data_type: str, ticker: str, years: int) -> list[DataResult]:
        if not self.with_history:
            return []
        years_back = [2020, 2021, 2022, 2023, 2024]
        rows = []
        for yr in years_back:
            rows.append(
                DataResult(
                    data={
                        "fiscal_year": f"{yr}-12-31",
                        "ebitda": 100_000_000_000 + yr * 1_000_000_000,
                        "operating_cash_flow": 90_000_000_000,
                        "capital_expenditure": -30_000_000_000,
                        "total_debt": 120_000_000_000,
                        "total_cash": 60_000_000_000,
                        "shares_outstanding": 15_500_000_000,
                    },
                    provider="stub",
                    ticker=ticker,
                    data_type=data_type,
                    timestamp=datetime.now(tz=timezone.utc),
                )
            )
        return rows


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_technical_analysis_populates_all_three_branches():
    payload = await build_technical_analysis(
        ticker="AAPL",
        dcf_inputs=_dcf_inputs(),
        dcf_target=200.0,
        current_price=162.0,
        data_layer=_StubDataLayer(),
    )

    assert isinstance(payload, TechnicalAnalysis)
    assert payload.monte_carlo is not None
    assert payload.sniper is not None
    assert payload.historical_bands is not None
    assert payload.warnings == []


@pytest.mark.asyncio
async def test_monte_carlo_branch_returns_distribution_stats():
    payload = await build_technical_analysis(
        ticker="AAPL",
        dcf_inputs=_dcf_inputs(),
        dcf_target=200.0,
        current_price=162.0,
        data_layer=_StubDataLayer(),
    )

    mc = payload.monte_carlo
    assert mc is not None
    assert mc.n_valid >= 100
    # Histogram has matching bin/count cardinality
    assert len(mc.histogram_bins) == len(mc.histogram_counts) + 1
    # Standard percentile keys present
    assert set(mc.percentiles.keys()) >= {"5", "50", "95"}
    # Current price percentile is bounded
    assert 0.0 <= mc.current_price_percentile <= 100.0


@pytest.mark.asyncio
async def test_sniper_branch_uses_historical_prices():
    payload = await build_technical_analysis(
        ticker="AAPL",
        dcf_inputs=_dcf_inputs(),
        dcf_target=200.0,
        current_price=162.0,
        data_layer=_StubDataLayer(),
    )

    sn = payload.sniper
    assert sn is not None
    # Take profit equals the dcf target verbatim
    assert sn.take_profit == 200.0
    # Stop loss is below current; ideal buy is below target
    assert sn.stop_loss < 162.0
    assert sn.ideal_buy < 200.0
    # Support / resistance bracket the recent close window
    assert sn.support_level <= sn.resistance_level


@pytest.mark.asyncio
async def test_historical_bands_branch_classifies_position():
    payload = await build_technical_analysis(
        ticker="AAPL",
        dcf_inputs=_dcf_inputs(),
        dcf_target=200.0,
        current_price=162.0,
        data_layer=_StubDataLayer(),
    )

    hb = payload.historical_bands
    assert isinstance(hb, HistoricalBandSnapshot)
    assert hb.metric == "ev_ebitda"
    assert hb.sample_count > 0
    assert hb.classification in {"expensive", "fair", "cheap", "unknown"}
    # Timeline rows serialize to (iso-string, float)
    for d, v in hb.timeline:
        assert isinstance(d, str) and len(d) == 10  # YYYY-MM-DD
        assert isinstance(v, float)


# ---------------------------------------------------------------------------
# Degraded inputs — each branch must skip without bringing down the others
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sniper_skips_when_no_price_history():
    payload = await build_technical_analysis(
        ticker="AAPL",
        dcf_inputs=_dcf_inputs(),
        dcf_target=200.0,
        current_price=162.0,
        data_layer=_StubDataLayer(with_price=False),
    )

    assert payload.sniper is None
    assert any("sniper" in w for w in payload.warnings)
    # Monte Carlo is independent of price history and still runs.
    assert payload.monte_carlo is not None
    # Bands also need the price stream, so they degrade alongside sniper.
    assert payload.historical_bands is None
    # The compute layer emits diagnostics like "price 历史为空" or "shares_outstanding 不可得".
    # At least one warning must be present (exact text depends on compute layer path taken).
    assert len(payload.warnings) >= 2  # at least sniper + historical_bands diagnostic


@pytest.mark.asyncio
async def test_monte_carlo_skips_when_current_price_zero():
    payload = await build_technical_analysis(
        ticker="AAPL",
        dcf_inputs=_dcf_inputs(),
        dcf_target=200.0,
        current_price=0.0,
        data_layer=_StubDataLayer(),
    )

    assert payload.monte_carlo is None
    assert any("monte_carlo" in w for w in payload.warnings)


@pytest.mark.asyncio
async def test_historical_bands_skip_when_no_historical_financials():
    payload = await build_technical_analysis(
        ticker="AAPL",
        dcf_inputs=_dcf_inputs(),
        dcf_target=200.0,
        current_price=162.0,
        data_layer=_StubDataLayer(with_history=False),
    )

    assert payload.historical_bands is None
    # Compute layer emits its own diagnostics (e.g. "financials 历史为空").
    # Pre-fix: technical_payload swallowed these with a generic string.
    # Post-fix: band.warnings are passed through verbatim.
    assert len(payload.warnings) >= 1


@pytest.mark.asyncio
async def test_historical_bands_warnings_passthrough_from_band():
    """band.warnings are propagated verbatim; the generic fallback message is
    only used when band.warnings is empty.

    We use _StubDataLayer(with_history=False) which returns zero financials rows,
    causing compute_historical_band to emit its own warning into band.warnings.
    The fix in technical_payload.py must not replace those with the generic string.

    Implementation note: with_history=False returns [] from fetch_historical,
    so _safe_historical_bands calls compute_historical_band with an empty yearly list.
    HistoricalBand.warnings will contain "financials 历史为空" (or similar).
    We assert warnings is non-empty AND that the generic fallback is NOT the only message
    if the compute layer already provided a diagnostic.
    """
    payload = await build_technical_analysis(
        ticker="AAPL",
        dcf_inputs=_dcf_inputs(),
        dcf_target=200.0,
        current_price=162.0,
        data_layer=_StubDataLayer(with_history=False),
    )

    assert payload.historical_bands is None
    # Compute layer emits its own diagnostics; at least one warning must be present.
    # The stub has no shares_outstanding → "shares_outstanding 不可得" path fires first.
    assert len(payload.warnings) >= 1, (
        f"Expected >=1 warning from band compute layer, got: {payload.warnings}"
    )
    # The warning must NOT be the generic fallback (it should be the compute layer's own text).
    # Any non-empty band.warnings from compute_historical_band are now passed through verbatim.
    assert not all(w == "historical_bands skipped: no valid samples" for w in payload.warnings)


# ---------------------------------------------------------------------------
# Structural-break disclosure carried into the published payload (l1)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_historical_bands_carry_the_structural_break_disclosure(monkeypatch):
    """The band's EBITDA-regime break must reach the artifact so the UI can caveat
    the CHEAP/FAIR/EXPENSIVE badge computed over a mixed window.

    Live 2026-10-13 NVDA: the window opened on the pre-ramp FY2023 base
    ($5.99B EBITDA) and FY2024 stepped 5.9x to $35.58B, so p25 37.76x / p90 183.34x
    drove a CHEAP badge (current 27.06x). The classification is published unchanged
    — the caveat travels with it.
    """
    from datetime import date as _date

    from finrobot.engine.compute.coordinators import technical_payload as tp
    from finrobot.engine.primitives.historical_valuation import (
        EbitdaStructuralBreak,
        HistoricalBand,
    )

    band = HistoricalBand(
        metric="ev_ebitda",
        current=27.06280742897459,
        median=58.67400134895877,
        p25=37.76125330964162,
        p75=98.53028879769617,
        p90=183.34108904109593,
        timeline=[(_date(2023, 1, 31), 79.83875542933512)],
        sample_count=900,
        warnings=["band-level warning"],
        structural_break=EbitdaStructuralBreak(
            from_fiscal_date=_date(2023, 1, 31),
            to_fiscal_date=_date(2024, 1, 31),
            from_ebitda=5.986e9,
            to_ebitda=35.583e9,
            step_multiple=5.944,
        ),
    )

    async def _fake_bands(ticker, metric, years, data_layer, **kwargs):
        return band

    monkeypatch.setattr(tp, "compute_bands_via_data_layer", _fake_bands)

    payload = await build_technical_analysis(
        ticker="NVDA",
        dcf_inputs=_dcf_inputs(),
        dcf_target=259.87,
        current_price=228.52,
        data_layer=_StubDataLayer(),
    )

    hb = payload.historical_bands
    assert hb is not None
    assert hb.classification == "cheap"  # 27.06x <= p25 37.76x — unchanged
    assert hb.structural_break is not None
    assert hb.structural_break.from_fiscal_year == "2023-01-31"
    assert hb.structural_break.to_fiscal_year == "2024-01-31"
    assert hb.structural_break.step_multiple == pytest.approx(5.944)
    assert hb.structural_break.to_ebitda == pytest.approx(35.583e9)
    # The badge caveat is a STRING the UI renders next to the classification.
    assert hb.classification_caveat is not None
    assert hb.classification_caveat.startswith(
        "the band's cheap/fair/expensive classification is computed on a window"
    )
    assert "directional only" in hb.classification_caveat
    # the band's own warning still rides along
    assert "band-level warning" in hb.warnings


@pytest.mark.asyncio
async def test_historical_bands_without_a_break_publish_no_caveat(monkeypatch):
    from datetime import date as _date

    from finrobot.engine.compute.coordinators import technical_payload as tp
    from finrobot.engine.primitives.historical_valuation import HistoricalBand

    band = HistoricalBand(
        metric="ev_ebitda",
        current=20.0,
        median=18.0,
        p25=15.0,
        p75=22.0,
        p90=25.0,
        timeline=[(_date(2025, 6, 1), 20.0)],
        sample_count=900,
        warnings=[],
    )

    async def _fake_bands(ticker, metric, years, data_layer, **kwargs):
        return band

    monkeypatch.setattr(tp, "compute_bands_via_data_layer", _fake_bands)

    payload = await build_technical_analysis(
        ticker="AAPL",
        dcf_inputs=_dcf_inputs(),
        dcf_target=200.0,
        current_price=162.0,
        data_layer=_StubDataLayer(),
    )

    hb = payload.historical_bands
    assert hb is not None
    assert hb.structural_break is None
    assert hb.classification_caveat is None
