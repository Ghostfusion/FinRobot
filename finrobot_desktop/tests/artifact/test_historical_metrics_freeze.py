"""The equity_research builder must FREEZE the pipeline's multi-year
HistoricalMetrics into outputs.structured.historical_metrics, so the report's
financial-trend charts render from the snapshot instead of a live ['historical']
refetch.

Why this matters (report-internal consistency, not storage): the narrative's
growth / multi-year-trend claims are COMPUTED from these series. If the chart
re-fetched live at export time, a new fiscal year landing or a restatement would
drift the chart endpoints out of sync with the frozen prose — the report would
contradict itself. So the series must be pinned to the same snapshot as the
narrative.

The series ride INSIDE outputs.structured (a generic JSON dict) — no Artifact
model schema change; simply absent on legacy artifacts (the frontend deriver
maps a missing key to null, no crash).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, cast

from finrobot.artifact.builders import build_equity_research_artifact
from finrobot.engine.compute.coordinators.historical_extractor import (
    EBITDA_CALIBER_LABEL,
    EBITDA_CALIBER_SAME_LABEL,
    ebitda_caliber_label,
)
from finrobot.engine.models.financial import (
    BalanceSheet,
    FinancialData,
    HistoricalMetrics,
    IncomeStatement,
    MarketData,
    ValuationMetrics,
)
from finrobot.engine.pipelines.base import PipelineResult

UTC = timezone.utc


def _financial_data() -> FinancialData:
    return FinancialData(
        ticker="AAPL",
        timestamp=datetime(2026, 5, 13, 10, 0, 0, tzinfo=UTC),
        income=IncomeStatement(revenue=391_000_000_000, ebitda=131_000_000_000),
        balance=BalanceSheet(total_debt=100_000_000_000, total_cash=60_000_000_000),
        market=MarketData(
            market_cap=3_000_000_000_000,
            shares_outstanding=15_000_000_000,
            current_price=200.0,
        ),
        valuation=ValuationMetrics(),
        data_source="fake",
    )


def _historical() -> HistoricalMetrics:
    # Three fiscal years; only the series the chart adapters actually read need
    # real values, but every required field is populated so the model validates.
    return HistoricalMetrics(
        years=[2022, 2023, 2024],
        revenue=[394_000_000_000, 383_000_000_000, 391_000_000_000],
        revenue_growth_yoy=[None, -0.028, 0.021],
        cogs=[None, None, None],
        gross_profit=[None, None, None],
        gross_margin=[0.43, 0.44, 0.46],
        sga=[0.0, 0.0, 0.0],
        sga_ratio=[None, None, None],
        ebitda=[130_000_000_000, 125_000_000_000, 131_000_000_000],
        ebitda_margin=[0.33, 0.33, 0.34],
        operating_income=[119_000_000_000, 114_000_000_000, 123_000_000_000],
        operating_margin=[0.30, 0.30, 0.31],
        net_income=[99_000_000_000, 97_000_000_000, 93_000_000_000],
        eps=[6.11, 6.13, 6.08],
        pe_ratio=[None, None, None],
        cagr_revenue=-0.004,
        ticker="AAPL",
        operating_cash_flow=[122_000_000_000, 110_000_000_000, 118_000_000_000],
        investing_cash_flow=[-22_000_000_000, -10_000_000_000, -2_000_000_000],
        financing_cash_flow=[-110_000_000_000, -108_000_000_000, -94_000_000_000],
    )


def test_equity_research_freezes_historical_metrics() -> None:
    result = PipelineResult(
        steps={"data_collection": "ok"},
        structured_data={
            "data_collection": _financial_data(),
            "historical_metrics": _historical(),
        },
    )
    artifact = build_equity_research_artifact(result, "AAPL", cast(Any, None))

    hm = artifact.outputs.structured["historical_metrics"]
    assert hm["years"] == [2022, 2023, 2024]
    assert hm["revenue"][-1] == 391_000_000_000
    assert hm["eps"] == [6.11, 6.13, 6.08]
    # Every series the four chart adapters consume must be present in the frozen
    # snapshot (revenue/EBITDA, margins, cash-flow, EPS).
    for key in (
        "gross_margin",
        "ebitda_margin",
        "operating_margin",
        "operating_cash_flow",
        "investing_cash_flow",
        "financing_cash_flow",
    ):
        assert key in hm, f"frozen historical_metrics missing chart series {key!r}"


def test_frozen_historical_payload_labels_the_ebitda_caliber() -> None:
    """The frozen payload carries a caliber label so the chart chapter can disclose
    what it is comparing the TTM figure against — a definitional disclosure, never an
    invented number. This fixture has no D&A series, so the label is the conservative
    mixed-caliber one; the same-caliber case is pinned below."""
    result = PipelineResult(
        steps={"data_collection": "ok"},
        structured_data={
            "data_collection": _financial_data(),
            "historical_metrics": _historical(),
        },
    )
    artifact = build_equity_research_artifact(result, "AAPL", cast(Any, None))

    hm = artifact.outputs.structured["historical_metrics"]
    assert hm["ebitda_caliber"] == EBITDA_CALIBER_LABEL
    assert "operating income + D&A" in hm["ebitda_caliber"]


def test_historical_metrics_absent_when_pipeline_lacks_it() -> None:
    # A degraded / legacy run with no historical step → the key is simply absent.
    # The frontend deriver maps a missing key to null (no chart, no crash); the
    # builder must NOT fabricate an empty block.
    result = PipelineResult(
        steps={"data_collection": "ok"},
        structured_data={"data_collection": _financial_data()},
    )
    artifact = build_equity_research_artifact(result, "AAPL", cast(Any, None))

    assert "historical_metrics" not in artifact.outputs.structured


# ---------------------------------------------------------------------------
# The caliber disclosure must be TRUE for the history it labels. Whether the annual
# bars share the TTM figure's caliber is a fact about the series, not a constant:
# the report puts them side by side and asks the reader to compare them.
# ---------------------------------------------------------------------------


def test_caliber_label_is_same_when_the_newest_bar_is_ebit_plus_da() -> None:
    """GMED 2026-10-14: the frozen payload called it "two different D&A calibers"
    while its newest annual bar (814,033,000) was 537,191,000 + 276,842,000 to the
    dollar — the same formula the TTM figure uses."""
    label = ebitda_caliber_label(
        [304_503_000.0, 346_942_000.0, 472_776_000.0, 814_033_000.0],
        [236_251_000.0, 201_416_000.0, 219_387_000.0, 537_191_000.0],
        [68_252_000.0, 145_526_000.0, 253_389_000.0, 276_842_000.0],
    )
    assert label == EBITDA_CALIBER_SAME_LABEL


def test_caliber_label_stays_mixed_when_the_bars_imply_other_da() -> None:
    """NVDA FY2026: the provider's annual bar implied ~$14B of D&A against $3.7B in
    the TTM figure — a definitional difference the label must keep claiming."""
    label = ebitda_caliber_label([50.0e9, 100.0e9], [20.0e9, 40.0e9], [3.7e9, 14.0e9])
    assert label == EBITDA_CALIBER_LABEL


def test_caliber_label_is_mixed_when_a_leg_is_missing() -> None:
    """The conservative claim: a history that cannot be checked warns rather than
    reassures."""
    assert ebitda_caliber_label([100.0], [90.0], []) == EBITDA_CALIBER_LABEL
    assert ebitda_caliber_label([], [90.0], [10.0]) == EBITDA_CALIBER_LABEL
    assert ebitda_caliber_label([100.0, None], [90.0, None], [10.0, None]) == EBITDA_CALIBER_LABEL


def test_frozen_payload_labels_the_same_caliber_for_a_consistent_history() -> None:
    hist = _historical().model_copy(update={"depreciation_amortization": [11.0e9, 11.0e9, 8.0e9]})
    result = PipelineResult(
        steps={"data_collection": "ok"},
        structured_data={"data_collection": _financial_data(), "historical_metrics": hist},
    )
    artifact = build_equity_research_artifact(result, "AAPL", cast(Any, None))

    hm = artifact.outputs.structured["historical_metrics"]
    # ebitda[-1] 131.0e9 == operating_income[-1] 123.0e9 + D&A[-1] 8.0e9.
    assert hm["ebitda_caliber"] == EBITDA_CALIBER_SAME_LABEL
