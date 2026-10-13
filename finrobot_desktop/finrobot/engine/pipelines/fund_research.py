"""Fund research pipeline — ETFs, mutual funds and closed-end funds.

4 steps:
  1. fund_data        — deterministic: fetch the canonical fund profile + price
                        series and project them into ``FundData`` (critical).
  2. fund_assessment  — deterministic: NAV risk/return statistics, expense cost
                        drag, portfolio concentration and duration sensitivity
                        via the pure ``fund_metrics`` operators.
  3. fund_narrative   — LLM (report agent) narrates the assessment.
  4. fund_report      — LLM (report agent) assembles the final report.

A fund files no income statement, so the equity pipelines (DCF / DDM / comps)
are undefined for it — see ``engine.data.instrument`` for the classification and
``engine.compute.coordinators.extractor`` for the fail-fast guard that routes a
fund here. Every number in the report is computed by code from real provider
data; the LLM only narrates it.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic_ai import Agent

from finrobot.engine.compute.coordinators.fund_profile import assess_fund, build_fund_data
from finrobot.engine.data.interface import ProviderError
from finrobot.engine.data.types import DataType
from finrobot.engine.deps import FinRobotDeps
from finrobot.engine.models.financial import StepOutput
from finrobot.engine.models.fund import FundAssessment, FundData
from finrobot.engine.pipelines.base import (
    Pipeline,
    PipelineStep,
    StructuredValidator,
    TextValidator,
)
from finrobot.engine.pipelines.validators import (
    validate_fund_assessment,
    validate_fund_profile,
    validate_is_non_empty,
    validate_report_format,
)

logger = logging.getLogger(__name__)


def _fund_data_narrative(data: FundData) -> str:
    """Deterministic one-paragraph description of the fund snapshot."""
    parts: list[str] = [f"{data.ticker} — {data.name or 'fund'}"]
    if data.category:
        parts.append(f"category {data.category}")
    if data.total_net_assets is not None:
        parts.append(f"total net assets ${data.total_net_assets / 1e9:,.1f}B")
    if data.nav_per_share is not None:
        parts.append(f"NAV/share ${data.nav_per_share:,.2f}")
    if data.market_price is not None:
        parts.append(f"market price ${data.market_price:,.2f}")
    if data.net_expense_ratio is not None:
        parts.append(f"net expense ratio {data.net_expense_ratio:.2%}")
    if data.distribution_yield is not None:
        parts.append(f"distribution yield {data.distribution_yield:.2%}")
    return "Fund profile: " + "; ".join(parts) + "."


def _assessment_narrative(data: FundData, assessment: FundAssessment) -> str:
    """Deterministic one-paragraph summary of the computed metrics."""
    bits: list[str] = [f"{data.ticker} fund assessment"]
    cagr_1y = assessment.returns.get("cagr_1y")
    if cagr_1y is not None:
        bits.append(f"1y NAV CAGR {cagr_1y:.2%}")
    if assessment.volatility is not None:
        bits.append(f"annualized volatility {assessment.volatility:.2%}")
    if assessment.max_drawdown is not None:
        bits.append(f"max drawdown {assessment.max_drawdown:.2%}")
    if assessment.sharpe is not None:
        bits.append(f"Sharpe {assessment.sharpe:.2f}")
    if assessment.premium_discount is not None:
        bits.append(f"premium/discount to NAV {assessment.premium_discount:+.2%}")
    drag = assessment.cost_drag.get("expense_drag_usd_per_10k")
    horizon = assessment.cost_drag.get("horizon_years")
    if drag is not None and horizon is not None:
        bits.append(f"expense drag ${drag:,.0f} per $10,000 over {horizon:.0f}y")
    if assessment.portfolio_source is not None:
        when = (
            f" as of {assessment.portfolio_as_of.isoformat()}"
            if assessment.portfolio_as_of is not None
            else ""
        )
        positions = (
            f" ({assessment.portfolio_holding_count} positions)"
            if assessment.portfolio_holding_count
            else ""
        )
        bits.append(f"portfolio source {assessment.portfolio_source}{when}{positions}")
    return "; ".join(bits) + "."


async def _execute_fund_data(
    agent: Agent[Any, Any],  # noqa: ARG001 — kept for executor signature; unused
    deps: FinRobotDeps,
    prompt: str,  # noqa: ARG001 — kept for executor signature; unused
    structured_context: dict[str, object],  # noqa: ARG001 — kept for signature; unused
    ticker: str,
    **_kwargs: object,
) -> StepOutput:
    """Deterministic: fetch the canonical fund profile + price series.

    A ``ProviderError`` here means no provider could serve a fund profile — the
    symbol is an operating company (the fund providers refuse one) or every fund
    provider failed. Re-raised as an actionable ``ValueError`` so the run fails
    with "not a fund / use the equity pipeline" instead of a generic provider
    error, and the critical step aborts the pipeline honestly.
    """
    try:
        fund_data = await build_fund_data(ticker, deps.data_layer)
    except ProviderError as exc:
        raise ValueError(
            f"No investment-fund profile could be retrieved for '{ticker}'. The fund "
            "pipeline (key 'fund_research') supports ETFs, mutual funds and closed-end "
            "funds only — an operating company has no fund profile. For a company, run an "
            f"equity pipeline instead (e.g. `finrobot research {ticker}`). Provider said: {exc}"
        ) from exc
    return StepOutput(text=_fund_data_narrative(fund_data), structured=fund_data)


async def _execute_fund_assessment(
    agent: Agent[Any, Any],  # noqa: ARG001 — kept for executor signature; unused
    deps: FinRobotDeps,  # noqa: ARG001 — kept for executor signature; unused
    prompt: str,  # noqa: ARG001 — kept for executor signature; unused
    structured_context: dict[str, object],
    ticker: str,  # noqa: ARG001 — kept for executor signature; unused
    **_kwargs: object,
) -> StepOutput:
    """Deterministic: compute the fund metrics from the ``fund_data`` snapshot."""
    fund_data = structured_context.get("fund_data")
    if not isinstance(fund_data, FundData):
        raise ValueError(
            "fund_assessment requires FundData from the fund_data step but received: "
            + type(fund_data).__name__
        )
    assessment = assess_fund(fund_data)
    return StepOutput(text=_assessment_narrative(fund_data, assessment), structured=assessment)


def create_fund_research_pipeline(agents: dict[str, Agent]) -> Pipeline:
    """4-step fund research pipeline factory (ETF / mutual fund / closed-end fund)."""
    from finrobot.artifact.builders import build_fund_research_artifact

    return Pipeline(
        artifact_builder=build_fund_research_artifact,
        steps=[
            PipelineStep(
                name="fund_data",
                skill_section=None,
                agent=agents["data"],
                required_data=[DataType.FUND_PROFILE, DataType.PRICE],
                validator=StructuredValidator(validate_fund_profile, validate_is_non_empty),
                executor=_execute_fund_data,
                # Deterministic fetch + projection — no LLM call.
                deterministic=True,
                # fund_assessment reads this FundData — abort if the fetch fails.
                critical=True,
            ),
            PipelineStep(
                name="fund_assessment",
                skill_section=None,
                agent=agents["modeling"],
                required_data=[],
                validator=StructuredValidator(validate_fund_assessment, validate_is_non_empty),
                executor=_execute_fund_assessment,
                # Deterministic assess_fund — ignores the re-prompt (BUG-059).
                deterministic=True,
            ),
            PipelineStep(
                name="fund_narrative",
                skill_section=None,
                # Fund-specific report editor, NOT the equity `report` agent: the
                # equity instructions make the model emit company sections (peer
                # multiples, a price target) that a fund cannot have — the live IEI
                # report carried a "Peer Analysis — none provided" heading and a
                # "price target: none" block before this role existed.
                agent=agents["fund_report"],
                required_data=[],
                validator=TextValidator(validate_is_non_empty),
            ),
            PipelineStep(
                name="fund_report",
                skill_section=None,
                agent=agents["fund_report"],
                required_data=[],
                validator=TextValidator(validate_report_format),
            ),
        ],
    )
