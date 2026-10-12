"""Unit tests for finrobot.engine.compute.coordinators.credit_payload.

The state machine is the contract a reader depends on: a payload must never show a
default probability the data cannot support, and must never say "not applicable"
when the real reason is a missing input. Each test drives ONE state and asserts
(a) the state itself, (b) that an uncomputed state carries its reason, and (c) that
no number is fabricated in place of the missing one.

Prices are supplied through a stub data layer (``load_price_history`` calls
``fetch_price_range``), so nothing here touches a provider.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from finrobot.engine.compute.coordinators.credit_payload import (
    BARRIER_BASIS_TOTAL_DEBT,
    BARRIER_BASIS_WARNING,
    DEBT_NOT_REPORTED_WARNING,
    NOT_APPLICABLE_WARNING,
    NO_DEBT_WARNING,
    CreditRisk,
    build_credit_risk,
)
from finrobot.engine.compute.operators.credit_risk import annualized_equity_volatility

MARKET_CAP = 3.0e12
TOTAL_DEBT = 1.0e11
RISK_FREE = 0.043

# A spread the bank/insurer classifier recognizes (industry-driven, per
# primitives/industry.py — FMP tags every financial sector the same way).
BANK_INDUSTRY = "Banks - Diversified"
BANK_SECTOR = "Financial Services"


class _Bar:
    def __init__(self, day: date, close: float) -> None:
        self.date = day
        self.close = close


class _StubDataLayer:
    """Minimal price-range door: ``load_price_history`` reads exactly this."""

    def __init__(self, bars: list[_Bar]) -> None:
        self.bars = bars
        self.calls: list[str] = []

    async def fetch_price_range(self, ticker: str, _start: str, _end: str) -> list[_Bar]:
        self.calls.append(ticker)
        return self.bars


def _bars(count: int = 250, step: float = 0.011) -> list[_Bar]:
    """``count`` daily closes ending today whose simple returns alternate ±step —
    a series with a known, non-degenerate volatility."""
    today = date.today()
    closes = [100.0]
    for i in range(count - 1):
        sign = 1.0 if i % 2 == 0 else -1.0
        closes.append(closes[-1] * (1.0 + sign * step))
    return [_Bar(today - timedelta(days=count - 1 - i), close) for i, close in enumerate(closes)]


async def _build(**overrides: object) -> CreditRisk:
    params: dict[str, object] = dict(
        market_cap=MARKET_CAP,
        total_debt=TOTAL_DEBT,
        risk_free_rate=RISK_FREE,
        data_layer=_StubDataLayer(_bars()),
        industry="Software - Infrastructure",
        sector="Technology",
    )
    params.update(overrides)
    return await build_credit_risk("TEST", **params)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# computed
# ---------------------------------------------------------------------------


async def test_computes_the_full_reading_for_a_levered_non_financial() -> None:
    payload = await _build()

    assert payload.state == "computed"
    assert payload.equity_value == MARKET_CAP
    assert payload.debt_barrier == TOTAL_DEBT
    assert payload.barrier_basis == BARRIER_BASIS_TOTAL_DEBT
    assert payload.distance_to_default is not None
    assert payload.distance_to_default > 0.0
    assert payload.default_probability is not None
    assert 0.0 < payload.default_probability < 1.0
    assert payload.asset_value is not None and payload.asset_value > MARKET_CAP
    assert payload.converged is True
    # The basis caveat ships with every computed reading — a conservative barrier
    # is a fact about the number, not a footnote.
    assert BARRIER_BASIS_WARNING in payload.warnings


async def test_the_reported_volatility_is_the_report_wide_estimator() -> None:
    bars = _bars()
    payload = await _build(data_layer=_StubDataLayer(bars))

    assert payload.volatility_bars == len(bars)
    assert payload.equity_volatility == pytest.approx(
        annualized_equity_volatility([b.close for b in bars])
    )


async def test_more_debt_lowers_distance_to_default_end_to_end() -> None:
    light = await _build(total_debt=5.0e10)
    heavy = await _build(total_debt=1.5e12)

    assert light.distance_to_default is not None and heavy.distance_to_default is not None
    assert heavy.distance_to_default < light.distance_to_default
    assert heavy.default_probability > light.default_probability  # type: ignore[operator]
    assert heavy.debt_to_value > light.debt_to_value  # type: ignore[operator]


async def test_is_deterministic_for_identical_inputs() -> None:
    assert await _build() == await _build()


# ---------------------------------------------------------------------------
# no_debt — a report, not an absence
# ---------------------------------------------------------------------------


async def test_a_debt_free_balance_sheet_is_no_debt_not_not_computable() -> None:
    payload = await _build(total_debt=0.0)

    assert payload.state == "no_debt"
    assert payload.debt_barrier == 0.0
    assert payload.distance_to_default is None
    assert payload.default_probability is None
    assert payload.warnings == [NO_DEBT_WARNING]


async def test_no_debt_survives_a_missing_market_cap() -> None:
    """Debt-free is the whole story; a missing cap must not reclassify it."""
    payload = await _build(total_debt=0.0, market_cap=None)

    assert payload.state == "no_debt"
    assert payload.equity_value is None


# ---------------------------------------------------------------------------
# not_applicable — the category error dominates every other reason
# ---------------------------------------------------------------------------


async def test_a_balance_sheet_financial_is_not_applicable() -> None:
    payload = await _build(industry=BANK_INDUSTRY, sector=BANK_SECTOR)

    assert payload.state == "not_applicable"
    assert payload.warnings == [NOT_APPLICABLE_WARNING]
    assert payload.distance_to_default is None
    assert payload.default_probability is None


async def test_a_bank_with_unreported_debt_still_reads_not_applicable() -> None:
    """The category error is the stronger truth than the missing input."""
    payload = await _build(industry=BANK_INDUSTRY, sector=BANK_SECTOR, total_debt=None)

    assert payload.state == "not_applicable"


# ---------------------------------------------------------------------------
# not_computable — the reason is always attached, never a zero
# ---------------------------------------------------------------------------


async def test_unreported_debt_is_not_treated_as_zero() -> None:
    payload = await _build(total_debt=None)

    assert payload.state == "not_computable"
    assert payload.warnings == [DEBT_NOT_REPORTED_WARNING]
    assert payload.debt_barrier is None
    assert payload.distance_to_default is None


async def test_short_price_history_blocks_the_volatility() -> None:
    payload = await _build(data_layer=_StubDataLayer(_bars(count=10)))

    assert payload.state == "not_computable"
    assert payload.distance_to_default is None
    assert "10 daily closes" in payload.warnings[0]


async def test_missing_market_cap_blocks_the_reading() -> None:
    for cap in (None, 0.0, -1.0):
        payload = await _build(market_cap=cap)

        assert payload.state == "not_computable"
        assert "market capitalization" in payload.warnings[0]


async def test_missing_risk_free_rate_blocks_the_reading() -> None:
    payload = await _build(risk_free_rate=None)

    assert payload.state == "not_computable"
    assert "risk-free rate" in payload.warnings[0]


async def test_a_non_usd_ledger_without_the_fx_chokepoint_is_refused() -> None:
    """A barrier in TWD over equity in USD is a meaningless leverage ratio."""
    payload = await _build(reporting_currency="TWD", usd_normalized=False)

    assert payload.state == "not_computable"
    assert "TWD" in payload.warnings[0]
    assert payload.debt_to_value is None


async def test_a_non_usd_ledger_past_the_fx_chokepoint_is_computed() -> None:
    """Post-chokepoint the line items ARE USD — the currency tag is a label, not
    a unit, so an ADR must not be refused for its reporting currency alone."""
    payload = await _build(reporting_currency="TWD", usd_normalized=True)

    assert payload.state == "computed"


async def test_every_non_computed_state_explains_itself() -> None:
    """The chapter renders the reason verbatim; an empty one is a blank card."""
    for payload in (
        await _build(total_debt=0.0),
        await _build(industry=BANK_INDUSTRY),
        await _build(total_debt=None),
        await _build(market_cap=None),
        await _build(risk_free_rate=None),
        await _build(data_layer=_StubDataLayer(_bars(count=10))),
    ):
        assert payload.state != "computed"
        assert payload.warnings, f"{payload.state} carried no reason"
