"""Fund research pipeline — registration, step order, compute, fail-fast and artifact contract.

No network: the canonical ``NormalizedFundProfile`` / ``NormalizedPrice`` inputs
are constructed from the REAL values measured on the live providers (IEI bond
ETF, VTSAX index mutual fund).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from pydantic_ai import Agent
from pydantic_ai.models.test import TestModel

from finrobot.artifact.builders import build_fund_research_artifact
from finrobot.engine.compute.coordinators.extractor import extract_financial_data
from finrobot.engine.compute.coordinators.fund_profile import (
    assess_fund,
    build_fund_data,
    project_fund_data,
)
from finrobot.engine.data.instrument import FundInstrumentError, is_fund_quote_type
from finrobot.engine.data.interface import ProviderError
from finrobot.engine.data.normalize.contracts import (
    FundHolding,
    NormalizedFinancials,
    NormalizedFundProfile,
    NormalizedPrice,
    PriceBar,
    Provenance,
)
from finrobot.engine.data.types import DataType
from finrobot.engine.deps import FinRobotDeps
from finrobot.engine.models.fund import FundAssessment, FundData
from finrobot.engine.pipelines.fund_research import create_fund_research_pipeline
from finrobot.engine.pipelines.registry import get_pipeline_factories, get_pipeline_spec

NOW = datetime(2026, 10, 12, tzinfo=timezone.utc)

# The artifact's pinned structured keys (the UI slice renders against these).
REQUIRED_STRUCTURED_KEYS = {
    "ticker",
    "instrument",
    "category",
    "fund_family",
    "legal_type",
    "total_net_assets",
    "nav_per_share",
    "market_price",
    "premium_discount",
    "net_expense_ratio",
    "category_avg_expense_ratio",
    "turnover",
    "cost_drag",
    "distribution_yield",
    "returns",
    "volatility",
    "max_drawdown",
    "sharpe",
    "asset_classes",
    "sector_weights",
    "bond_ratings",
    "bond_duration",
    "top_holdings",
    "concentration",
    "warnings",
}


class _AnyRoleAgents(dict):
    """Agents dict that materialises a TestModel agent for any role key."""

    def __missing__(self, key: str) -> Agent:
        agent: Agent = Agent(TestModel(), deps_type=FinRobotDeps, defer_model_check=True)
        self[key] = agent
        return agent


def _provenance() -> Provenance:
    return Provenance(provider="yfinance", as_of=NOW, fetched_at=NOW)


def _spread_dates(count: int, span_days: int) -> list[date]:
    """``count`` bar dates ending today, evenly spread over ``span_days`` calendar days."""
    last = datetime.now(tz=timezone.utc).date()
    first = last - timedelta(days=span_days)
    step = (last - first) / max(count - 1, 1)
    return [first + step * index for index in range(count)]


def _price(
    closes: list[float], ticker: str = "IEI", current_price: float = 113.48
) -> NormalizedPrice:
    """Bars for ``closes`` spread over a ~1-year calendar window (a real 1y series)."""
    dates = _spread_dates(len(closes), 366)
    bars = [PriceBar(date=day, close=close) for day, close in zip(dates, closes, strict=False)]
    return NormalizedPrice(
        ticker=ticker,
        quote_currency="USD",
        bars=bars,
        current_price=current_price,
        provenance=_provenance(),
    )


def _iei_profile() -> NormalizedFundProfile:
    return NormalizedFundProfile(
        ticker="IEI",
        name="iShares 3-7 Year Treasury Bond ETF",
        fund_family="iShares",
        legal_type="Exchange Traded Fund",
        category="Intermediate Government",
        quote_type="ETF",
        inception_date=date(2007, 1, 4),
        currency="USD",
        as_of=NOW,
        total_net_assets=16787430400.0,
        nav_per_share=113.43545,
        market_price=113.48,
        net_expense_ratio=0.0015,
        gross_expense_ratio=0.0015,
        category_avg_expense_ratio=0.005287,
        turnover=0.37,
        distribution_yield=0.0382,
        ytd_return=-0.0254777,
        return_3m=-0.0248268,
        return_3y_annual=0.0352429,
        return_5y_annual=-3.24e-05,
        beta_3y=0.69,
        asset_classes={
            "cash": 0.0085,
            "stock": 0.0,
            "bond": 0.9915,
            "preferred": 0.0,
            "convertible": 0.0,
            "other": 0.0,
        },
        bond_ratings={"us_government": 0.9915, "aa": 1.0},
        bond_duration=3.54,
        bond_maturity=9.356,
        top_holdings=[],
        provenance=_provenance(),
    )


def _vtsax_profile() -> NormalizedFundProfile:
    return NormalizedFundProfile(
        ticker="VTSAX",
        name="Vanguard Total Stock Market Index Fund Admiral Shares",
        fund_family="Vanguard",
        legal_type="Mutual Fund",
        category="Large Blend",
        quote_type="MUTUALFUND",
        inception_date=date(2000, 11, 13),
        currency="USD",
        as_of=NOW,
        total_net_assets=2322096979968.0,
        nav_per_share=None,  # NAV-priced mutual fund: no separate NAV quote
        market_price=185.72,
        net_expense_ratio=0.0004,
        category_avg_expense_ratio=0.007823,
        turnover=0.03,
        distribution_yield=0.0105,
        ytd_return=0.1257772,
        return_3m=0.0135894,
        return_3y_annual=None,
        return_5y_annual=None,
        beta_3y=1.03,
        sector_weights={f"sector_{i}": 0.0909 for i in range(11)},
        equity_pe=24.283632831471586,
        top_holdings=[
            FundHolding(symbol="NVDA", name="NVIDIA Corp", weight=0.068748295),
            FundHolding(symbol="AAPL", name="Apple Inc", weight=0.063032),
            FundHolding(symbol="MSFT", name="Microsoft Corp", weight=0.0510406),
            FundHolding(symbol="AMZN", name="Amazon.com Inc", weight=0.0340635),
        ],
        provenance=_provenance(),
    )


def _one_year_series() -> list[float]:
    """253 closes compounding 10%/yr over the ACTUAL one-year bar dates."""
    dates = _spread_dates(253, 366)
    base = dates[0]
    return [100.0 * (1.10 ** ((day - base).days / 365.25)) for day in dates]


def _project(profile: NormalizedFundProfile, closes: list[float]) -> FundData:
    """``project_fund_data`` with the closes turned into a bar series."""
    return project_fund_data(profile, _price(closes).bars)


class TestPipelineRegistration:
    def test_step_names_and_order(self):
        pipeline = create_fund_research_pipeline(_AnyRoleAgents())
        assert [step.name for step in pipeline.steps] == [
            "fund_data",
            "fund_assessment",
            "fund_narrative",
            "fund_report",
        ]

    def test_deterministic_and_critical_flags(self):
        steps = {s.name: s for s in create_fund_research_pipeline(_AnyRoleAgents()).steps}
        assert steps["fund_data"].deterministic is True
        assert steps["fund_data"].critical is True
        assert steps["fund_assessment"].deterministic is True
        assert steps["fund_assessment"].critical is False
        assert steps["fund_narrative"].deterministic is False
        assert steps["fund_report"].deterministic is False

    def test_registry_exposes_key_and_factory(self):
        factories = get_pipeline_factories()
        assert "fund_research" in factories
        assert factories["fund_research"] is create_fund_research_pipeline

    def test_spec_metadata(self):
        spec = get_pipeline_spec("fund_research")
        assert spec.tool_name == "run_fund_research"
        assert spec.import_path.endswith(":create_fund_research_pipeline")
        lowered = spec.tool_description.lower()
        for keyword in ("etf", "mutual fund", "closed-end", "nav", "expense ratio", "holdings"):
            assert keyword in lowered


class TestFailFastRouting:
    def test_fund_quote_type_is_detected(self):
        assert is_fund_quote_type("ETF") is True
        assert is_fund_quote_type("MUTUALFUND") is True
        assert is_fund_quote_type("EQUITY") is False
        assert is_fund_quote_type(None) is False

    def test_etf_fails_fast_with_actionable_error(self):
        fin = NormalizedFinancials(
            ticker="IEI", as_of=NOW, provenance=_provenance(), quote_type="ETF"
        )
        with pytest.raises(FundInstrumentError) as excinfo:
            extract_financial_data(fin, _price([100.0, 101.0]))
        message = str(excinfo.value)
        assert "IEI" in message
        assert "investment fund" in message
        assert "fund_research" in message
        assert "finrobot fund IEI" in message
        # It is a ValueError subclass so existing handlers still catch it.
        assert isinstance(excinfo.value, ValueError)

    def test_mutual_fund_also_fails_fast(self):
        fin = NormalizedFinancials(
            ticker="VTSAX", as_of=NOW, provenance=_provenance(), quote_type="MUTUALFUND"
        )
        with pytest.raises(FundInstrumentError):
            extract_financial_data(
                fin, _price([100.0, 101.0], ticker="VTSAX", current_price=185.72)
            )

    def test_operating_company_still_reports_missing_revenue(self):
        fin = NormalizedFinancials(
            ticker="AAPL",
            as_of=NOW,
            provenance=_provenance(),
            quote_type="EQUITY",
            revenue=None,
            market_cap=3.5e12,
        )
        with pytest.raises(ValueError) as excinfo:
            extract_financial_data(fin, _price([100.0, 101.0], ticker="AAPL", current_price=290.0))
        assert not isinstance(excinfo.value, FundInstrumentError)
        assert "Missing or zero revenue" in str(excinfo.value)


class TestAssessment:
    def test_iei_real_numbers(self):
        data = _project(_iei_profile(), _one_year_series())
        assert data.ticker == "IEI"
        assert data.instrument == "fund"
        assert data.nav_per_share == 113.43545
        assert data.category_avg_expense_ratio == 0.005287
        assert len(data.nav_closes) == 253

        assessment = assess_fund(data)
        assert assessment.returns["cagr_1y"] == pytest.approx(0.10, rel=1e-9)
        assert assessment.returns["ytd"] == pytest.approx(-0.0254777)
        assert assessment.returns["return_3m"] == pytest.approx(-0.0248268)
        assert assessment.premium_discount == pytest.approx(113.48 / 113.43545 - 1.0)
        assert assessment.cost_drag["fee_vs_category_avg"] == pytest.approx(0.0015 - 0.005287)
        assert assessment.cost_drag["expense_drag_usd_per_10k"] is not None
        assert assessment.duration_sensitivity is not None
        assert assessment.duration_sensitivity["modified_duration"] == pytest.approx(3.54)
        # IEI reports no individual top holdings → concentration stays unmeasured.
        assert assessment.concentration["hhi"] is None

    def test_vtsax_degrades_missing_fields_never_zero(self):
        data = _project(_vtsax_profile(), _one_year_series())
        assessment = assess_fund(data)
        # nav_per_share is legitimately None for this NAV-priced mutual fund.
        assert assessment.premium_discount is None
        assert data.nav_per_share is None
        assert assessment.returns["cagr_3y"] is None
        assert assessment.returns["cagr_5y"] is None
        assert assessment.concentration["top10_weight"] is not None
        assert assessment.concentration["unlisted_remainder"] is not None
        assert any("NAV per share" in w for w in assessment.warnings)

    def test_missing_series_warns_and_leaves_stats_none(self):
        data = _project(_iei_profile(), [])
        assessment = assess_fund(data)
        assert assessment.volatility is None
        assert assessment.max_drawdown is None
        assert assessment.sharpe is None
        assert assessment.cost_drag["expense_drag_usd_per_10k"] is None
        assert any("No NAV/price series" in w for w in assessment.warnings)


class TestArtifactContract:
    def _artifact(self):
        data = _project(_iei_profile(), _one_year_series())
        assessment = assess_fund(data)
        from finrobot.engine.pipelines.result import PipelineResult

        result = PipelineResult(
            steps={
                "fund_data": "Fund profile: IEI.",
                "fund_assessment": "IEI fund assessment.",
                "fund_narrative": "The fund tracks intermediate Treasuries.",
                "fund_report": "Report.",
            },
            structured_data={"fund_data": data, "fund_assessment": assessment},
        )
        deps = SimpleNamespace(settings=SimpleNamespace(language="en"))
        return build_fund_research_artifact(result, "IEI", deps)

    def test_type_source_and_structured_keys(self):
        artifact = self._artifact()
        assert artifact.type == "fund_research"
        assert artifact.meta.source == "pipeline:fund_research"
        structured = artifact.outputs.structured
        missing = REQUIRED_STRUCTURED_KEYS - set(structured)
        assert not missing, f"artifact missing pinned keys: {sorted(missing)}"

    def test_structured_values_are_the_real_computed_ones(self):
        structured = self._artifact().outputs.structured
        assert structured["ticker"] == "IEI"
        assert structured["instrument"] == "fund"
        assert structured["net_expense_ratio"] == 0.0015
        assert structured["category_avg_expense_ratio"] == 0.005287
        assert structured["returns"]["cagr_1y"] == pytest.approx(0.10, rel=1e-9)
        assert structured["cost_drag"]["fee_share_of_gross_return"] == pytest.approx(0.0015 / 0.10)
        assert structured["concentration"]["hhi"] is None
        # The dated series is shipped for the report chart.
        series = structured["nav_series"]
        assert len(series) == 253
        assert set(series[0]) == {"date", "close"}

    def test_missing_fund_data_does_not_crash_builder(self):
        from finrobot.engine.pipelines.result import PipelineResult

        result = PipelineResult(steps={"fund_data": "x"}, structured_data={})
        deps = SimpleNamespace(settings=SimpleNamespace(language="en"))
        artifact = build_fund_research_artifact(result, "IEI", deps)
        assert artifact.type == "fund_research"
        assert artifact.outputs.structured == {"warnings": []}


def test_project_and_assess_types():
    data = _project(_iei_profile(), _one_year_series())
    assert isinstance(data, FundData)
    assert isinstance(assess_fund(data), FundAssessment)


class _FakeLayer:
    """Minimal DataLayer stand-in: fund profile + PRICE_RANGE + PRICE fallback."""

    def __init__(
        self,
        *,
        range_bars: list[PriceBar],
        range_error: Exception | None = None,
        fallback_price: NormalizedPrice | None = None,
    ) -> None:
        self._range_bars = range_bars
        self._range_error = range_error
        self._fallback_price = fallback_price
        self.price_range_calls: list[tuple[str, str]] = []

    async def fetch_canonical(self, data_type: str | DataType, ticker: str) -> object:
        if data_type == DataType.FUND_PROFILE:
            return _iei_profile()
        return self._fallback_price

    async def fetch_price_range(
        self, ticker: str, start: str, end: str, interval: str = "1d"
    ) -> list[PriceBar]:
        self.price_range_calls.append((start, end))
        if self._range_error is not None:
            raise self._range_error
        return self._range_bars


def _range_bars(count: int) -> list[PriceBar]:
    """``count`` bars ending today and spanning five CALENDAR years.

    Five calendar years hold ~1253-1258 US trading sessions — fewer than
    ``5 * 252 + 1`` — which is exactly the case a session-count window rule could
    not measure. Closes compound 10%/yr over the actual dates.
    """
    last = datetime.now(tz=timezone.utc).date()
    try:
        first = last.replace(year=last.year - 5)
    except ValueError:  # Feb-29
        first = last.replace(year=last.year - 5, month=2, day=28)
    # Integer day offsets: the first bar lands EXACTLY on the 5-year anchor and the
    # last EXACTLY on today, which is what the coordinator's range fetch produces.
    # Float arithmetic (``first + step * index``) lands one day short of today
    # (1826/1252 × 1252 = 1825.999…), making the series span 4.9966 years — a series
    # that legitimately cannot carry a 5-year CAGR, so the window came back None.
    span_days = (last - first).days
    dates = [
        first + timedelta(days=round(span_days * index / (count - 1))) for index in range(count)
    ]
    return [
        PriceBar(date=day, close=100.0 * (1.10 ** ((day - first).days / 365.25))) for day in dates
    ]


class TestNavSeriesFetch:
    async def test_five_year_range_series_feeds_all_cagr_windows(self):
        # 1253 bars over five CALENDAR years — FEWER than 5*252 + 1 = 1261, the
        # count a session-based window rule demanded (and thus never satisfied).
        layer = _FakeLayer(range_bars=_range_bars(1253))
        data = await build_fund_data("IEI", layer)  # type: ignore[arg-type]
        assert len(data.nav_closes) == 1253
        assert len(data.nav_closes) < 5 * 252 + 1
        assert layer.price_range_calls, "the PRICE_RANGE door was not used"
        assert not any("falls back" in w for w in data.warnings)

        assessment = assess_fund(data)
        assert assessment.returns["cagr_1y"] == pytest.approx(0.10, rel=1e-6)
        assert assessment.returns["cagr_3y"] == pytest.approx(0.10, rel=1e-6)
        assert assessment.returns["cagr_5y"] == pytest.approx(0.10, rel=1e-6)
        # A full five-year series must NOT warn about a window it cannot span.
        assert not any("too short" in w for w in assessment.warnings)

    async def test_empty_range_falls_back_to_trailing_year_canonical(self):
        price = _price(_one_year_series())
        layer = _FakeLayer(range_bars=[], fallback_price=price)
        data = await build_fund_data("IEI", layer)  # type: ignore[arg-type]
        assert data.nav_closes == [bar.close for bar in price.bars]
        assert any("falls back to the trailing" in w for w in data.warnings)

        assessment = assess_fund(data)
        # 253 points span one trading year: the 1y CAGR computes, 3y/5y cannot.
        assert assessment.returns["cagr_1y"] is not None
        assert assessment.returns["cagr_3y"] is None
        assert assessment.returns["cagr_5y"] is None
        assert any("too short for the 3y, 5y" in w for w in assessment.warnings)

    async def test_range_provider_error_falls_back_with_the_reason(self):
        price = _price(_one_year_series())
        layer = _FakeLayer(
            range_bars=[],
            range_error=ProviderError("no PRICE_RANGE provider"),
            fallback_price=price,
        )
        data = await build_fund_data("IEI", layer)  # type: ignore[arg-type]
        assert data.nav_closes
        assert any("ProviderError" in w for w in data.warnings)
        assert any("falls back to the trailing" in w for w in data.warnings)

    async def test_fund_profile_refusal_still_propagates(self):
        class _RefusingLayer:
            async def fetch_canonical(self, data_type: str | DataType, ticker: str) -> object:
                raise ProviderError(f"Cannot fetch canonical {data_type} for {ticker}")

            async def fetch_price_range(
                self, ticker: str, start: str, end: str, interval: str = "1d"
            ) -> list[PriceBar]:
                raise ProviderError("unreachable")

        with pytest.raises(ProviderError):
            await build_fund_data("AAPL", _RefusingLayer())  # type: ignore[arg-type]
