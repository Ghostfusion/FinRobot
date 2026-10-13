"""Fund holdings (SEC N-PORT) — provider key mapping, fraction convention, degrade.

No network: the provider arm's SEC lookups (``find_fund`` / ``search_filings`` /
``FundReport``) are monkeypatched, and the crafted N-PORT frame carries OBSERVED
values from the live filings probed 2026-10-12, so the unit conversions are pinned
to real magnitudes, not invented ones:

* ``pct_value`` is a PERCENT NUMBER. Live Vanguard Total Stock Market (VTSAX)
  NPORT-P (filed 2026-08-28, period 2026-06-30, 3,546 positions, net assets
  $2,297,839,156,548) reported its largest position at ``pctValue`` 6.3554 —
  i.e. 6.3554% of net assets, and ``value_usd / net_assets`` reconciled to
  0.063554 exactly. The contract stores 0.063554 (a FRACTION), so the provider
  divides by 100.
* A blank debt ticker arrives as pandas ``NaN`` or the literal ``None`` /
  ``"N/A"`` (live: IEI's Argentine/US-Treasury rows) → ``symbol`` is ``None``.
* The frame columns observed on a real ``FundReport.investment_data()`` are
  ``name / ticker / pct_value / value_usd / asset_category`` (+ many others).

The crafted frame uses those observed cell shapes; ``net_assets`` is chosen so
``value_usd / net_assets`` equals ``pct_value / 100`` for every row, mirroring the
live reconciliation.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from types import SimpleNamespace

import pandas as pd
import pytest

from finrobot.artifact.builders import build_fund_research_artifact
from finrobot.engine.compute.coordinators.fund_profile import (
    assess_fund,
    build_fund_data,
    project_fund_data,
)
from finrobot.engine.data.interface import DataResult, ProviderError
from finrobot.engine.data.normalize.contracts import (
    NormalizedFundHoldings,
    NormalizedFundProfile,
    PriceBar,
    Provenance,
)
from finrobot.engine.data.normalize.fund_holdings import normalize_fund_holdings
from finrobot.engine.data.providers import edgar_provider
from finrobot.engine.data.providers.edgar_provider import EdgarToolsProvider
from finrobot.engine.data.types import DataType
from finrobot.engine.models.fund import FundAssessment, FundData
from finrobot.engine.pipelines.result import PipelineResult

NOW = datetime(2026, 10, 12, tzinfo=timezone.utc)

#: Chosen so ``value_usd / net_assets == pct_value / 100`` for every crafted row.
_NET_ASSETS = 10_000_000_000.0


# ---------------------------------------------------------------------------
# Fakes for the SEC lookups (no network)
# ---------------------------------------------------------------------------


def _crafted_frame() -> pd.DataFrame:
    """A real-shaped N-PORT frame; values are the observed live magnitudes."""
    return pd.DataFrame(
        [
            {
                "name": "NVIDIA Corp",
                "ticker": "NVDA",
                "pct_value": 6.3554,
                "value_usd": 635_540_000.0,  # 0.063554 × net assets
                "asset_category": "EC",
            },
            {
                "name": "Vanguard Market Liquidity Fund",
                "ticker": float("nan"),  # blank cell → NaN on a real frame
                "pct_value": 2.551085902269,
                "value_usd": 255_108_590.23,
                "asset_category": "STIV",
            },
            {
                "name": "Argentina Republic Government International Bonds",
                "ticker": None,  # a debt row's ticker cell
                "pct_value": 0.789207157543,
                "value_usd": 78_920_715.75,
                "asset_category": "DBT",
            },
        ]
    )


class _FakeGeneralInfo:
    series_name = "VANGUARD TOTAL STOCK MARKET INDEX FUND"
    series_id = "S000002848"


class _FakeFundInfo:
    def __init__(self, net_assets: float) -> None:
        self.net_assets = net_assets


class _FakeReport:
    def __init__(
        self, series_id: str, frame: pd.DataFrame, *, net_assets: float = _NET_ASSETS
    ) -> None:
        self.series_id = series_id
        self.reporting_period = "2026-06-30"
        self.general_info = _FakeGeneralInfo()
        self.fund_info = _FakeFundInfo(net_assets)
        self._frame = frame

    def investment_data(self, **_kwargs: object) -> pd.DataFrame:
        return self._frame


class _FakeFiling:
    def __init__(self, report: _FakeReport, filing_date: str = "2026-08-28") -> None:
        self.form = "NPORT-P"
        self.filing_date = filing_date
        self.report = report


class _FakeCandidate:
    def __init__(self, filed: str, filing: _FakeFiling) -> None:
        self.filed = filed
        self._filing = filing

    def get_filing(self) -> _FakeFiling:
        return self._filing


class _FakeSearch:
    def __init__(self, results: list[_FakeCandidate]) -> None:
        self.results = results
        self.total = len(results)

    def fetch_more(self, _n: int) -> "_FakeSearch":
        return self


class _FakeFundReport:
    """Stands in for edgartools' ``FundReport`` (only ``from_filing`` is used)."""

    @staticmethod
    def from_filing(filing: _FakeFiling) -> _FakeReport:
        return filing.report


def _provider() -> EdgarToolsProvider:
    """A provider instance WITHOUT ``__init__`` (no identity / network needed)."""
    return EdgarToolsProvider.__new__(EdgarToolsProvider)


def _install_sec_fakes(
    monkeypatch: pytest.MonkeyPatch,
    *,
    search_results: list[_FakeCandidate],
    series_id: str = "S000002848",
) -> None:
    series = edgar_provider.FundSeries(series_id=series_id, name="VTSAX series")
    klass = edgar_provider.FundClass(class_id="C000007806", ticker="VTSAX", series=series)
    monkeypatch.setattr(edgar_provider, "find_fund", lambda _ticker: klass)
    monkeypatch.setattr(
        edgar_provider, "search_filings", lambda **_kwargs: _FakeSearch(search_results)
    )
    monkeypatch.setattr(edgar_provider, "FundReport", _FakeFundReport)


# ---------------------------------------------------------------------------
# Phase 1 — the provider arm: key mapping + fraction convention
# ---------------------------------------------------------------------------


class TestProviderArm:
    def test_payload_keys_and_fraction_convention(self, monkeypatch):
        report = _FakeReport("S000002848", _crafted_frame())
        candidate = _FakeCandidate("2026-08-28", _FakeFiling(report))
        _install_sec_fakes(monkeypatch, search_results=[candidate])

        data, warnings = _provider()._fetch_fund_holdings_sync("VTSAX")

        assert set(data) == {
            "ticker",
            "as_of",
            "filing_date",
            "form",
            "series_name",
            "series_id",
            "class_id",
            "total_net_assets",
            "holding_count",
            "coverage",
            "holdings",
            "fees",
            "warnings",
        }
        assert data["ticker"] == "VTSAX"
        assert data["as_of"] == "2026-06-30"
        assert data["filing_date"] == "2026-08-28"
        assert data["form"] == "NPORT-P"
        assert data["series_id"] == "S000002848"
        assert data["class_id"] == "C000007806"
        assert data["series_name"] == "VANGUARD TOTAL STOCK MARKET INDEX FUND"
        assert data["total_net_assets"] == _NET_ASSETS
        assert data["fees"] is None
        assert warnings == data["warnings"]

        holdings = data["holdings"]
        assert data["holding_count"] == len(holdings) == 3
        # Descending by weight.
        assert [h["name"] for h in holdings] == [
            "NVIDIA Corp",
            "Vanguard Market Liquidity Fund",
            "Argentina Republic Government International Bonds",
        ]
        # pct_value 6.3554 is a PERCENT → weight is the FRACTION 0.063554.
        assert holdings[0]["weight"] == pytest.approx(0.063554)
        assert holdings[0]["symbol"] == "NVDA"
        assert holdings[0]["value_usd"] == pytest.approx(635_540_000.0)
        assert holdings[0]["asset_type"] == "EC"
        # A blank debt ticker (NaN / None) is never a literal symbol.
        assert holdings[1]["symbol"] is None
        assert holdings[2]["symbol"] is None
        # coverage is the FRACTION sum of the weights.
        assert data["coverage"] == pytest.approx((6.3554 + 2.551085902269 + 0.789207157543) / 100.0)

    def test_fraction_weight_reconciles_with_value_over_net_assets(self, monkeypatch):
        report = _FakeReport("S000002848", _crafted_frame())
        candidate = _FakeCandidate("2026-08-28", _FakeFiling(report))
        _install_sec_fakes(monkeypatch, search_results=[candidate])

        data, _ = _provider()._fetch_fund_holdings_sync("VTSAX")
        for holding in data["holdings"]:
            assert holding["weight"] == pytest.approx(
                holding["value_usd"] / data["total_net_assets"]
            )

    def test_unresolvable_ticker_raises_provider_error(self, monkeypatch):
        def _boom(_ticker: str) -> object:
            raise edgar_provider.CompanyNotFoundError("Company not found: 'ZZZZ'")

        monkeypatch.setattr(edgar_provider, "find_fund", _boom)
        with pytest.raises(ProviderError) as excinfo:
            _provider()._fetch_fund_holdings_sync("ZZZZ")
        assert "ZZZZ" in str(excinfo.value)

    def test_company_without_series_raises_provider_error(self, monkeypatch):
        # find_fund falls back to a fund COMPANY for an ETF absent from the
        # mutual-fund ticker file (e.g. SPY) — no series ⇒ no portfolio.
        monkeypatch.setattr(edgar_provider, "find_fund", lambda _t: object())
        with pytest.raises(ProviderError) as excinfo:
            _provider()._fetch_fund_holdings_sync("SPY")
        assert "series" in str(excinfo.value).lower()

    def test_no_matching_series_filing_raises_provider_error(self, monkeypatch):
        other = _FakeReport("S000099999", _crafted_frame())
        candidate = _FakeCandidate("2026-08-28", _FakeFiling(other))
        _install_sec_fakes(monkeypatch, search_results=[candidate])
        with pytest.raises(ProviderError) as excinfo:
            _provider()._fetch_fund_holdings_sync("VTSAX")
        assert "no N-PORT filing" in str(excinfo.value)

    def test_empty_filing_raises_instead_of_empty_payload(self, monkeypatch):
        empty = pd.DataFrame(columns=["name", "ticker", "pct_value", "value_usd"])
        report = _FakeReport("S000002848", empty)
        candidate = _FakeCandidate("2026-08-28", _FakeFiling(report))
        _install_sec_fakes(monkeypatch, search_results=[candidate])
        with pytest.raises(ProviderError) as excinfo:
            _provider()._fetch_fund_holdings_sync("VTSAX")
        assert "no parseable positions" in str(excinfo.value)


# ---------------------------------------------------------------------------
# Phase 2 — the canonical door
# ---------------------------------------------------------------------------


def _payload() -> dict[str, object]:
    return {
        "ticker": "VTSAX",
        "as_of": "2026-06-30",
        "filing_date": "2026-08-28",
        "form": "NPORT-P",
        "series_name": "VANGUARD TOTAL STOCK MARKET INDEX FUND",
        "series_id": "S000002848",
        "class_id": "C000007806",
        "total_net_assets": _NET_ASSETS,
        "holding_count": 3,
        "coverage": 0.09695693059812,
        "holdings": [
            {
                "symbol": "NVDA",
                "name": "NVIDIA Corp",
                "weight": 0.063554,
                "value_usd": 635_540_000.0,
                "asset_type": "EC",
            },
            {
                "symbol": None,
                "name": "Vanguard Market Liquidity Fund",
                "weight": 0.02551085902269,
                "value_usd": 255_108_590.23,
                "asset_type": "STIV",
            },
            {
                "symbol": None,
                "name": "Argentina Republic Government Bonds",
                "weight": 0.00789207157543,
                "value_usd": 78_920_715.75,
                "asset_type": "DBT",
            },
        ],
        "fees": None,
        "warnings": [],
    }


def _result(payload: dict[str, object]) -> DataResult:
    return DataResult(
        data=payload,
        provider="edgar_tools",
        ticker="VTSAX",
        data_type=DataType.FUND_HOLDINGS,
        timestamp=NOW,
    )


class TestCanonicalNormalize:
    def test_round_trip_preserves_the_fraction_convention(self):
        normalized = normalize_fund_holdings(_result(_payload()))
        assert isinstance(normalized, NormalizedFundHoldings)
        assert normalized.ticker == "VTSAX"
        assert normalized.as_of == date(2026, 6, 30)
        assert normalized.filing_date == date(2026, 8, 28)
        assert normalized.form == "NPORT-P"
        assert normalized.series_id == "S000002848"
        assert normalized.class_id == "C000007806"
        assert normalized.total_net_assets == _NET_ASSETS
        assert normalized.holding_count == 3
        assert normalized.coverage == pytest.approx(0.09695693059812)
        assert normalized.holdings[0].weight == pytest.approx(0.063554)
        assert normalized.holdings[0].symbol == "NVDA"

        # JSON round-trip is lossless across the canonical boundary.
        again = NormalizedFundHoldings.model_validate_json(normalized.model_dump_json())
        assert again == normalized

    def test_drops_negative_and_non_finite_weights(self):
        payload = _payload()
        payload["holdings"] = [
            {"name": "Good", "weight": 0.05, "value_usd": 1.0},
            {"name": "Short/derivative", "weight": -0.01, "value_usd": -1.0},
            {"name": "NaN", "weight": float("nan"), "value_usd": 1.0},
            {"name": "Missing weight"},
        ]
        normalized = normalize_fund_holdings(_result(payload))
        assert normalized.holding_count == 1
        assert normalized.holdings[0].name == "Good"
        # coverage/holding_count are recomputed from the surviving rows.
        assert normalized.coverage == pytest.approx(0.05)
        assert any("dropped" in w for w in normalized.warnings)

    def test_missing_data_stays_none(self):
        normalized = normalize_fund_holdings(_result({"ticker": "VTSAX"}))
        assert normalized.as_of is None
        assert normalized.filing_date is None
        assert normalized.form is None
        assert normalized.total_net_assets is None
        assert normalized.holding_count == 0
        assert normalized.coverage is None
        assert normalized.holdings == []
        assert normalized.fees is None


# ---------------------------------------------------------------------------
# Phase 3 — the coordinator consumes it, degrading
# ---------------------------------------------------------------------------


def _profile() -> NormalizedFundProfile:
    return NormalizedFundProfile(
        ticker="VTSAX",
        name="Vanguard Total Stock Market Index Fund Admiral Shares",
        category="Large Blend",
        quote_type="MUTUALFUND",
        currency="USD",
        as_of=NOW,
        total_net_assets=2_322_096_979_968.0,
        market_price=185.72,
        net_expense_ratio=0.0004,
        top_holdings=[],  # the vendor excerpt is deliberately empty here
        provenance=Provenance(provider="yfinance", as_of=NOW, fetched_at=NOW),
    )


def _bars() -> list[PriceBar]:
    return [
        PriceBar(date=date(2026, 9, 30), close=100.0),
        PriceBar(date=date(2026, 10, 1), close=101.0),
    ]


class _LayerWithHoldings:
    """Fake layer: profile + bars + a canonical FUND_HOLDINGS result."""

    def __init__(self, holdings: NormalizedFundHoldings | Exception) -> None:
        self._holdings = holdings

    async def fetch_canonical(self, data_type: str | DataType, ticker: str) -> object:
        if data_type == DataType.FUND_PROFILE:
            return _profile()
        if data_type == DataType.FUND_HOLDINGS:
            if isinstance(self._holdings, Exception):
                raise self._holdings
            return self._holdings
        raise AssertionError(f"unexpected data_type {data_type}")

    async def fetch_price_range(
        self, ticker: str, start: str, end: str, interval: str = "1d"
    ) -> list[PriceBar]:
        return _bars()


def _holdings_canonical() -> NormalizedFundHoldings:
    return normalize_fund_holdings(_result(_payload()))


class TestCoordinatorDegrade:
    async def test_sec_holdings_supersede_the_vendor_excerpt(self):
        layer = _LayerWithHoldings(_holdings_canonical())
        data = await build_fund_data("VTSAX", layer)  # type: ignore[arg-type]
        assert isinstance(data, FundData)
        assert data.portfolio_source == "sec_nport"
        assert data.portfolio_as_of == date(2026, 6, 30)
        assert len(data.portfolio_holdings) == 3
        assert [h.symbol for h in data.portfolio_holdings] == ["NVDA", None, None]

        assessment = assess_fund(data)
        assert isinstance(assessment, FundAssessment)
        assert assessment.portfolio_source == "sec_nport"
        assert assessment.portfolio_as_of == date(2026, 6, 30)
        assert assessment.portfolio_holding_count == 3
        # The full portfolio leaves almost nothing unaccounted.
        assert assessment.concentration["holdings_count"] == 3.0
        assert assessment.concentration["unlisted_remainder"] == pytest.approx(
            max(0.0, 1.0 - 0.09695693059812)
        )

    async def test_sec_failure_leaves_the_fund_report_intact(self):
        layer = _LayerWithHoldings(ProviderError("SEC unavailable for VTSAX"))
        data = await build_fund_data("VTSAX", layer)  # type: ignore[arg-type]
        # Absent SEC portfolio ⇒ vendor behaviour is preserved byte-identically.
        assert data.portfolio_holdings == []
        assert data.portfolio_source is None
        assert any("N-PORT" in w for w in data.warnings)

        assessment = assess_fund(data)
        assert assessment.concentration["hhi"] is None  # no vendor holdings either
        assert assessment.portfolio_source == "yfinance"
        assert assessment.portfolio_as_of == NOW.date()

    async def test_absent_sec_portfolio_uses_vendor_top_holdings(self):
        data = project_fund_data(_profile(), _bars(), holdings=None)
        assert data.portfolio_holdings == []
        assert data.portfolio_source is None
        assessment = assess_fund(data)
        assert assessment.portfolio_source == "yfinance"

    async def test_duplicate_position_names_are_not_merged(self):
        # A real SEC portfolio reports DISTINCT positions under a repeated issuer
        # name (IEI: many separate Treasuries all "United States of America").
        # Merging them would collapse the panel — disambiguation keeps each.
        payload = _payload()
        payload["holdings"] = [
            {"name": "United States of America", "weight": 0.02, "value_usd": 1.0},
            {"name": "United States of America", "weight": 0.03, "value_usd": 1.0},
            {"name": "United States of America", "weight": 0.04, "value_usd": 1.0},
        ]
        data = project_fund_data(
            _profile(), _bars(), holdings=normalize_fund_holdings(_result(payload))
        )
        assessment = assess_fund(data)
        assert assessment.concentration["holdings_count"] == 3.0
        assert assessment.concentration["unlisted_remainder"] == pytest.approx(1.0 - 0.09)


# ---------------------------------------------------------------------------
# Artifact — additive keys only (the desktop keeps rendering)
# ---------------------------------------------------------------------------


class TestArtifactAdditiveKeys:
    def test_portfolio_provenance_keys_are_added_beside_the_pinned_ones(self):
        data = project_fund_data(_profile(), _bars(), holdings=_holdings_canonical())
        assessment = assess_fund(data)
        result = PipelineResult(
            steps={"fund_data": "x"},
            structured_data={"fund_data": data, "fund_assessment": assessment},
        )
        artifact = build_fund_research_artifact(
            result, "VTSAX", SimpleNamespace(settings=SimpleNamespace(language="en"))
        )
        structured = artifact.outputs.structured
        assert structured["portfolio_source"] == "sec_nport"
        assert structured["portfolio_as_of"] == "2026-06-30"
        assert structured["portfolio_holding_count"] == 3
        # The previously-pinned keys still render.
        for key in ("ticker", "top_holdings", "concentration", "warnings"):
            assert key in structured
