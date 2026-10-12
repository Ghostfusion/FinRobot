"""The equity_research builder must persist ``structured.credit_risk``.

Chapter 11 (Credit & Default Risk) reads ``outputs.structured.credit_risk`` and
renders four states out of it. The builder whitelists the keys it freezes, so
dropping this one would silently regress the chapter to its "predates the step"
gap state for every future report — no error, no warning, just a missing
chapter — while the pipeline kept computing the block. These tests lock the
passthrough, the never-fabricated-when-absent rule, and the fact that a
non-computed state travels with its reason (the reader-facing explanation).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, cast

from finrobot.artifact.builders import build_equity_research_artifact
from finrobot.engine.compute.coordinators.credit_payload import CreditRisk
from finrobot.engine.models.financial import (
    BalanceSheet,
    FinancialData,
    IncomeStatement,
    MarketData,
    ValuationMetrics,
)
from finrobot.engine.pipelines.base import PipelineResult

UTC = timezone.utc


def _financial_data() -> FinancialData:
    return FinancialData(
        ticker="MSFT",
        timestamp=datetime(2026, 10, 12, 10, 0, 0, tzinfo=UTC),
        income=IncomeStatement(revenue=331_839_000_000, ebitda=131_720_000_000),
        balance=BalanceSheet(total_debt=131_000_000_000, total_cash=94_000_000_000),
        market=MarketData(
            market_cap=4_100_000_000_000,
            shares_outstanding=7_430_000_000,
            current_price=551.0,
        ),
        valuation=ValuationMetrics(),
        data_source="fake",
    )


def _result(credit: CreditRisk | None) -> PipelineResult:
    structured: dict[str, Any] = {"data_collection": _financial_data()}
    if credit is not None:
        structured["credit_risk"] = credit
    return PipelineResult(steps={"data_collection": "ok"}, structured_data=structured)


def _computed() -> CreditRisk:
    return CreditRisk(
        state="computed",
        horizon_years=1.0,
        equity_value=4_100_000_000_000,
        debt_barrier=131_000_000_000,
        barrier_basis="total_debt",
        asset_value=4_131_290_422_455.171,
        asset_volatility=0.31843559060275395,
        equity_volatility=0.3282389185846557,
        volatility_bars=251,
        risk_free_rate=0.043,
        distance_to_default=10.866622089230477,
        default_probability=8.312114224863827e-28,
        debt_to_value=0.03113784732957519,
        implied_credit_spread=4.163336342344337e-17,
        iterations=2,
        converged=True,
        warnings=["debt barrier = total debt: the KMV convention ..."],
    )


def test_computed_reading_reaches_the_artifact() -> None:
    artifact = build_equity_research_artifact(_result(_computed()), "MSFT", cast(Any, None))

    block = artifact.outputs.structured["credit_risk"]
    assert block["state"] == "computed"
    assert block["distance_to_default"] == 10.866622089230477
    assert block["default_probability"] == 8.312114224863827e-28
    assert block["barrier_basis"] == "total_debt"
    assert block["warnings"], "the barrier-basis caveat must travel with the numbers"


def test_an_uncomputed_state_travels_with_its_reason() -> None:
    """A bank must reach the reader as 'not applicable' + why, not as a blank."""
    bank = CreditRisk(
        state="not_applicable",
        horizon_years=1.0,
        warnings=["structural credit risk not applicable: this is a balance-sheet financial"],
    )
    artifact = build_equity_research_artifact(_result(bank), "JPM", cast(Any, None))

    block = artifact.outputs.structured["credit_risk"]
    assert block["state"] == "not_applicable"
    assert "balance-sheet financial" in block["warnings"][0]
    assert block["distance_to_default"] is None


def test_no_key_at_all_when_the_step_did_not_run() -> None:
    """A run without the step (legacy / pre-step artifact) carries no key at all —
    the chapter then renders its 'predates the step' state rather than zeros."""
    artifact = build_equity_research_artifact(_result(None), "MSFT", cast(Any, None))

    assert "credit_risk" not in artifact.outputs.structured
