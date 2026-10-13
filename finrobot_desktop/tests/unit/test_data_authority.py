"""Tests for the data-layer metric-authority adapters (authority / authority_log).

These defend the JOIN between provider payloads and the leaf reconciliation engine:

1. **The adapter maps a payload to observations correctly** — provider keys → registry
   metric names 1:1, currency/period read from the payload, ``retrieved_at`` from the
   result's timestamp, and the shares-rederivation lineage marked so a count computed
   from ``market_cap/price`` can never confirm its own parents.
2. **The bridge preserves the disagreement** — two same-period providers agree with no
   prose; a period gap is a ``definition_mismatch_period`` and never a numeric conflict;
   an over-tolerance revenue gap is a ``conflict`` naming both numbers, and the metric
   is reported through the structured KEY-divergence channel.
3. **Propagation** — the report reaches ``DataResult.reconciliation`` and the normalized
   contract, and a written decision line round-trips through ``disagreement_summary``.
4. **Best-effort logging** — a write failure never propagates.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from finrobot.engine.data import authority_log
from finrobot.engine.data.authority import (
    observations_from_financials,
    observations_from_price,
    reconcile_results,
)
from finrobot.engine.data.cache import DataCache
from finrobot.engine.data.interface import DataProvider, DataResult
from finrobot.engine.data.layer import DataLayer
from finrobot.engine.data.normalize import NormalizedFinancials, NormalizedPrice
from finrobot.engine.data.types import DataType
from finrobot.engine.data.validator import (
    authority_key_field_divergences,
    authority_reconciliation,
)

_UTC = timezone.utc
_NOW = datetime(2026, 10, 13, 12, 0, tzinfo=_UTC)


def _fin_result(
    provider: str, data: dict[str, object], *, timestamp: datetime = _NOW
) -> DataResult:
    return DataResult(
        data=data,
        provider=provider,
        ticker="AAPL",
        data_type=DataType.FINANCIALS,
        timestamp=timestamp,
    )


def _price_result(provider: str, data: dict[str, object]) -> DataResult:
    return DataResult(
        data=data,
        provider=provider,
        ticker="AAPL",
        data_type=DataType.PRICE,
        timestamp=_NOW,
    )


# ---------------------------------------------------------------------------
# observations_from_financials / observations_from_price
# ---------------------------------------------------------------------------


def test_financials_observations_map_keys_and_provenance() -> None:
    result = _fin_result(
        "fmp",
        {
            "revenue": 5_000.0,
            "market_cap": 7_000.0,
            "financial_currency": "twd",
            "quote_currency": "usd",
            "period_end": "2025-12-31",
            "period_basis": "ttm",
        },
    )
    by_metric = {obs.metric: obs for obs in observations_from_financials(result)}

    assert set(by_metric) == {"revenue", "market_cap"}
    revenue = by_metric["revenue"]
    assert revenue.source == "fmp"
    assert revenue.value == 5_000.0
    assert revenue.unit == "USD"  # the registry row's unit
    assert revenue.currency == "TWD"  # statement item → reporting currency
    assert revenue.period_end == date(2025, 12, 31)
    assert revenue.period_basis == "ttm"
    assert revenue.retrieved_at == _NOW  # the result's timestamp
    # market_cap is a point-in-time market item: quote currency, no flow basis.
    market_cap = by_metric["market_cap"]
    assert market_cap.currency == "USD"
    assert market_cap.period_basis is None


def test_financials_observation_skips_absent_and_none_metrics() -> None:
    result = _fin_result("fmp", {"revenue": None, "net_income": "n/a", "total_cash": 10.0})
    metrics = {obs.metric for obs in observations_from_financials(result)}
    assert metrics == {"total_cash"}


def test_shares_outstanding_marked_derived_only_when_rederived() -> None:
    rederived = _fin_result(
        "fmp",
        {"market_cap": 1_000_000.0, "current_price": 100.0, "shares_outstanding": 10_000.0},
    )
    shares = next(
        obs for obs in observations_from_financials(rederived) if obs.metric == "shares_outstanding"
    )
    assert shares.derived_from == ("market_cap", "current_price")

    independent = _fin_result(
        "yfinance",
        {"market_cap": 1_000_000.0, "current_price": 100.0, "shares_outstanding": 12_000.0},
    )
    shares2 = next(
        obs
        for obs in observations_from_financials(independent)
        if obs.metric == "shares_outstanding"
    )
    assert shares2.derived_from == ()


def test_quality_flags_carried_verbatim() -> None:
    result = _fin_result("fmp", {"revenue": 1.0})
    result = result.model_copy(
        update={
            "key_field_divergences": ["revenue"],
            "price_field_divergences": ["current_price"],
            "circuit_open_providers": ["finnhub"],
        }
    )
    revenue = observations_from_financials(result)[0]
    assert revenue.quality_flags == ("revenue", "current_price", "finnhub")


def test_price_observation_reads_current_price_and_quote_currency() -> None:
    result = _price_result(
        "fmp",
        {
            "current_price": 311.23,
            "quote_currency": "usd",
            "price_history": [{"date": "2026-10-10", "close": 310.0}],
            "quote_timestamp": 1_700_000_000,
        },
    )
    observation = observations_from_price(result)[0]
    assert observation.metric == "current_price"
    assert observation.value == 311.23
    assert observation.currency == "USD"
    assert observation.period_basis == "session"
    assert observation.period_end == date(2026, 10, 10)  # the bar session date
    assert observation.effective_at is not None  # from the quote timestamp


def test_price_observation_falls_back_to_quote_price_key() -> None:
    result = DataResult(
        data={"price": 42.0},
        provider="yfinance",
        ticker="AAPL",
        data_type=DataType.QUOTE,
        timestamp=_NOW,
    )
    observation = observations_from_price(result)[0]
    assert observation.metric == "current_price"
    assert observation.value == 42.0


# ---------------------------------------------------------------------------
# reconcile_results + the validator bridge
# ---------------------------------------------------------------------------


def test_same_period_agreement_is_accepted_and_silent() -> None:
    common = {"period_end": "2025-12-31", "period_basis": "ttm", "financial_currency": "USD"}
    fmp = _fin_result("fmp", {"revenue": 1_000.0, **common})
    yfinance = _fin_result("yfinance", {"revenue": 1_000.0, **common})

    report = reconcile_results([fmp, yfinance])
    decision = report.decision("revenue")
    assert decision is not None
    assert decision.status == "accepted"
    assert decision.reason_code == "sources_agree"
    assert decision.is_authoritative is True
    assert authority_reconciliation([fmp, yfinance]) == []


def test_period_mismatch_is_a_definition_mismatch_not_a_numeric_conflict() -> None:
    fmp = _fin_result(
        "fmp",
        {"revenue": 1_000.0, "period_end": "2025-12-31", "period_basis": "ttm"},
    )
    yfinance = _fin_result(
        "yfinance",
        {"revenue": 1_000.0, "period_end": "2025-09-30", "period_basis": "ttm"},
    )

    decision = reconcile_results([fmp, yfinance]).decision("revenue")
    assert decision is not None
    assert decision.status == "accepted"  # the owner's number still stands
    yf_candidate = next(c for c in decision.candidates if c.source == "yfinance")
    assert yf_candidate.eligible is False
    assert yf_candidate.reason_code == "definition_mismatch_period"
    # The mismatch is NEVER compared numerically → no conflict reason anywhere.
    assert all(
        candidate.reason_code != "above_tolerance_published_flagged"
        for candidate in decision.candidates
    )
    assert authority_key_field_divergences([fmp, yfinance]) == []


def test_over_tolerance_revenue_gap_is_a_conflict_naming_both_numbers() -> None:
    fmp = _fin_result("fmp", {"revenue": 1_000.0})
    yfinance = _fin_result("yfinance", {"revenue": 1_200.0})

    decision = reconcile_results([fmp, yfinance]).decision("revenue")
    assert decision is not None
    assert decision.status == "conflict"
    assert decision.reason_code == "above_tolerance_published_flagged"
    assert decision.disagreement_pct is not None

    lines = authority_reconciliation([fmp, yfinance])
    assert len(lines) == 1
    line = lines[0]
    assert line.startswith("Data authority: revenue conflict")
    assert "1,000" in line and "1,200" in line
    assert "fmp" in line and "yfinance" in line

    assert authority_key_field_divergences([fmp, yfinance]) == ["revenue"]


def test_single_provider_is_accepted_with_the_owner_or_a_named_alternative() -> None:
    owner = reconcile_results([_fin_result("fmp", {"revenue": 1_000.0})]).decision("revenue")
    assert owner is not None
    assert owner.status == "accepted"
    assert owner.selected_source == "fmp"
    assert owner.reason_code == "within_tolerance"  # a lone eligible owner needs no agreement
    assert owner.is_authoritative is True

    alternative = reconcile_results([_fin_result("yfinance", {"revenue": 1_000.0})]).decision(
        "revenue"
    )
    assert alternative is not None
    assert alternative.status == "accepted"
    assert alternative.selected_source == "yfinance"
    assert alternative.reason_code == "owner_absent_alternative_selected"
    assert alternative.is_authoritative is False


def test_reconcile_results_is_deterministic_and_sorted_by_metric() -> None:
    fmp = _fin_result("fmp", {"revenue": 1_000.0, "net_income": 100.0})
    yfinance = _fin_result("yfinance", {"revenue": 1_200.0, "net_income": 100.0})
    first = reconcile_results([fmp, yfinance], clock=_NOW)
    second = reconcile_results([yfinance, fmp], clock=_NOW)
    assert first.decisions == second.decisions
    assert [d.metric for d in first.decisions] == ["net_income", "revenue"]


# ---------------------------------------------------------------------------
# propagation through the layer
# ---------------------------------------------------------------------------


class _Provider(DataProvider):
    def __init__(self, name_: str, caps: list[str], result: DataResult) -> None:
        self._name = name_
        self._caps = caps
        self._result = result

    @property
    def name(self) -> str:
        return self._name

    def capabilities(self) -> list[str | DataType]:
        return self._caps

    async def fetch(self, ticker: str, data_type: str | DataType, **kwargs: object) -> DataResult:
        return self._result


@pytest.fixture
async def cache(tmp_path: Path):
    c = DataCache(db_path=str(tmp_path / "authority.db"))
    try:
        yield c
    finally:
        await c.close()


async def test_report_reaches_data_result_and_normalized_contract(cache: DataCache) -> None:
    fmp = _Provider("fmp", ["financials"], _fin_result("fmp", {"revenue": 1_000.0}))
    yfinance = _Provider("yfinance", ["financials"], _fin_result("yfinance", {"revenue": 1_200.0}))
    layer = DataLayer([fmp, yfinance], cache)

    raw = await layer.fetch("financials", "AAPL")
    assert raw.reconciliation is not None
    decision = raw.reconciliation.decision("revenue")
    assert decision is not None and decision.status == "conflict"
    assert raw.key_field_divergences == ["revenue"]
    assert any(line.startswith("Data authority: revenue conflict") for line in raw.warnings)

    normalized = await layer.fetch_canonical("financials", "AAPL")
    assert isinstance(normalized, NormalizedFinancials)
    assert normalized.reconciliation is not None
    assert normalized.reconciliation.decision("revenue") is not None


async def test_price_report_reaches_normalized_price(cache: DataCache) -> None:
    primary = _Provider(
        "fmp",
        ["price", "quote"],
        _price_result("fmp", {"current_price": 100.0, "price_history": []}),
    )
    secondary = _Provider(
        "yfinance",
        ["price", "quote"],
        DataResult(
            data={"price": 50.0},
            provider="yfinance",
            ticker="AAPL",
            data_type=DataType.QUOTE,
            timestamp=_NOW,
        ),
    )
    layer = DataLayer([primary, secondary], cache)

    normalized = await layer.fetch_canonical("price", "AAPL")
    assert isinstance(normalized, NormalizedPrice)
    assert normalized.reconciliation is not None
    decision = normalized.reconciliation.decision("current_price")
    assert decision is not None and decision.status == "conflict"


async def test_stale_single_price_observation_is_unavailable_without_a_marker(
    cache: DataCache,
) -> None:
    """A lone PRICE observation past the row's freshness bound is ``unavailable``
    (nothing eligible), NOT a divergence: ``price_divergence`` means two sources
    drew different numbers, and stamping it here would be a false statement. The
    report is still attached so the reason code rides the artifact."""
    stale_epoch = int((datetime.now(tz=_UTC) - timedelta(days=10)).timestamp())
    primary = _Provider(
        "fmp",
        ["price", "quote"],
        _price_result(
            "fmp",
            {"current_price": 100.0, "price_history": [], "quote_timestamp": stale_epoch},
        ),
    )
    layer = DataLayer([primary], cache)

    raw = await layer.fetch_price("AAPL")

    assert raw.price_field_divergences == []  # no price_divergence marker
    assert raw.reconciliation is not None
    decision = raw.reconciliation.decision("current_price")
    assert decision is not None
    assert decision.status == "unavailable"
    assert decision.reason_code == "stale_beyond_freshness_policy"


# ---------------------------------------------------------------------------
# append-only log
# ---------------------------------------------------------------------------


def test_written_decision_line_round_trips_through_disagreement_summary(
    tmp_path: Path,
) -> None:
    report = reconcile_results(
        [_fin_result("fmp", {"revenue": 1_000.0}), _fin_result("yfinance", {"revenue": 1_200.0})]
    )
    authority_log.record_decisions("AAPL", report, root=tmp_path)

    log_file = tmp_path / "AAPL.jsonl"
    assert log_file.exists()
    assert log_file.read_text(encoding="utf-8").count("\n") == 1  # one object per line

    summary = authority_log.disagreement_summary(root=tmp_path)
    assert summary == [
        {
            "metric": "revenue",
            "sources": "fmp|yfinance",
            "count": 1,
            "max_deviation_pct": report.decision("revenue").disagreement_pct,
        }
    ]


def test_disagreement_summary_orders_by_count_then_metric(tmp_path: Path) -> None:
    for _ in range(2):
        report = reconcile_results(
            [
                _fin_result("fmp", {"revenue": 1_000.0}),
                _fin_result("yfinance", {"revenue": 1_200.0}),
            ]
        )
        authority_log.record_decisions("AAPL", report, root=tmp_path)
    report_once = reconcile_results(
        [
            _fin_result("fmp", {"net_income": 100.0}),
            _fin_result("yfinance", {"net_income": 200.0}),
        ]
    )
    authority_log.record_decisions("AAPL", report_once, root=tmp_path)

    summary = authority_log.disagreement_summary(root=tmp_path)
    assert summary[0]["metric"] == "revenue"
    assert summary[0]["count"] == 2
    assert summary[1]["metric"] == "net_income"


def test_record_decisions_never_propagates_a_write_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    report = reconcile_results(
        [_fin_result("fmp", {"revenue": 1_000.0}), _fin_result("yfinance", {"revenue": 1_200.0})]
    )

    def _boom(*args: object, **kwargs: object) -> object:
        raise OSError("disk full")

    monkeypatch.setattr(Path, "open", _boom)
    # Must not raise, and must not write anything.
    assert authority_log.record_decisions("AAPL", report, root=tmp_path) is None
    assert not (tmp_path / "AAPL.jsonl").exists()


def test_record_decisions_rejects_an_escaping_symbol(tmp_path: Path) -> None:
    report = reconcile_results([_fin_result("fmp", {"revenue": 1.0})])
    assert authority_log.record_decisions("../evil", report, root=tmp_path) is None
    assert list(tmp_path.glob("*.jsonl")) == []


# ---------------------------------------------------------------------------
# layer boundaries
# ---------------------------------------------------------------------------


def test_authority_respects_layer_boundaries() -> None:
    import finrobot.engine.data.authority as authority_module
    import finrobot.engine.models.metric_authority as leaf

    authority_src = Path(authority_module.__file__).read_text(encoding="utf-8")
    for forbidden in ("import pydantic", "engine.compute", "engine.models.financial"):
        assert forbidden not in authority_src, f"authority.py must not import {forbidden!r}"

    leaf_src = Path(leaf.__file__).read_text(encoding="utf-8")
    assert "engine.data.authority" not in leaf_src
    assert "engine.data import authority" not in leaf_src
