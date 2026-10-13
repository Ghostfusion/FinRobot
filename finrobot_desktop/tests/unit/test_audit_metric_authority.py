"""The data-authority (metric reconciliation) audit verifier.

The data layer publishes ONE canonical value per metric but records every vendor
it saw (`FinancialData.data_authority` → `raw_data["data_authority"]`). These
tests pin that the verifier turns the non-clean decisions (`conflict` /
`unavailable` / `definition_mismatch`) into `review` findings — annotating the
artifact (`caveated`) without ever withholding the canonical value — that it is
idempotent and a no-op without the block, and that a built equity-research
artifact surfaces the finding through the normal numeric-audit sink.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, cast

from finrobot.artifact.builders import build_equity_research_artifact
from finrobot.engine.compute.operators.audit.metric_authority import (
    attach_metric_authority_findings,
    metric_authority_findings,
)
from finrobot.engine.models.financial import FinancialData, IncomeStatement, MarketData
from finrobot.engine.models.metric_authority import (
    MetricCandidate,
    MetricDecision,
    ReconciliationReport,
)
from finrobot.engine.pipelines.base import PipelineResult

UTC = timezone.utc
_CLOCK = datetime(2026, 6, 6, 10, 0, 0, tzinfo=UTC)


def _decision(status: str, **overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "metric": "revenue",
        "status": status,
        "value": 1_000.0,
        "unit": "USD",
        "currency": "USD",
        "selected_source": "fmp",
        "is_authoritative": True,
        "reason_code": "authoritative_selected",
        "policy_version": "metric_authority_v1",
        "definition_version": "revenue_1",
        "basis": "as-reported TTM revenue",
        "comparability": "as_reported_period",
        "tolerance_pct": 0.15,
        "tolerance_abs": None,
        "period_end": None,
        "period_basis": "ttm",
        "disagreement_pct": None,
        "agreement_is_independent": True,
        "candidates": [
            {
                "source": "fmp",
                "value": 1_000.0,
                "eligible": True,
                "deviation_pct": None,
                "deviation_abs": None,
                "reason_code": "authoritative_selected",
                "non_independent": False,
            }
        ],
        "reconciled_at": "2026-06-06T10:00:00+00:00",
    }
    base.update(overrides)
    return base


def _raw(*decisions: dict[str, Any]) -> dict[str, Any]:
    return {
        "data_authority": {
            "policy_version": "metric_authority_v1",
            "run_as_of": None,
            "clock": "2026-06-06T10:00:00+00:00",
            "decisions": list(decisions),
        }
    }


def _structured() -> dict[str, Any]:
    return {
        "thesis": {"price_target": 100.0},
        "numeric_audit": {
            "findings": [],
            "artifact_status": "publishable",
            "withhold_valuation": False,
        },
    }


class TestFindings:
    def test_clean_decisions_produce_no_finding(self):
        raw = _raw(
            _decision("accepted"),
            _decision("fallback", reason_code="canonical_value_invalid_fallback_selected"),
        )
        assert metric_authority_findings(raw) == []

    def test_conflict_finding_names_metric_sources_deviation_reason_policy(self):
        conflicting = _decision(
            "conflict",
            reason_code="above_tolerance_published_flagged",
            disagreement_pct=0.18,
            candidates=[
                {
                    "source": "fmp",
                    "value": 1_000.0,
                    "eligible": True,
                    "deviation_pct": None,
                    "deviation_abs": None,
                    "reason_code": "authoritative_selected",
                    "non_independent": False,
                },
                {
                    "source": "yfinance",
                    "value": 1_180.0,
                    "eligible": True,
                    "deviation_pct": 0.18,
                    "deviation_abs": 180.0,
                    "reason_code": "above_tolerance_published_flagged",
                    "non_independent": False,
                },
            ],
        )
        findings = metric_authority_findings(_raw(conflicting))
        assert len(findings) == 1
        finding = findings[0]
        assert finding.check == "metric_authority_conflict"
        assert finding.field_key == "data_authority.revenue"
        assert finding.severity == "review"
        evidence = finding.evidence
        assert "revenue" in evidence
        assert "fmp" in evidence and "1,000.00" in evidence
        assert "yfinance" in evidence and "1,180.00" in evidence
        assert "18.0%" in evidence
        assert "above_tolerance_published_flagged" in evidence
        assert "metric_authority_v1" in evidence

    def test_unavailable_and_definition_mismatch_map_to_their_ids(self):
        unavailable = _decision(
            "unavailable",
            value=None,
            selected_source=None,
            is_authoritative=False,
            reason_code="no_eligible_observation",
            candidates=[
                {
                    "source": "fmp",
                    "value": None,
                    "eligible": False,
                    "deviation_pct": None,
                    "deviation_abs": None,
                    "reason_code": "non_finite_value",
                    "non_independent": False,
                }
            ],
        )
        mismatch = _decision(
            "definition_mismatch",
            reason_code="definition_mismatch_period",
        )
        by_check = {f.check: f for f in metric_authority_findings(_raw(unavailable, mismatch))}
        assert "metric_authority_unavailable" in by_check
        assert "metric_authority_definition_mismatch" in by_check
        assert by_check["metric_authority_unavailable"].severity == "review"
        assert "n/a" in by_check["metric_authority_unavailable"].evidence

    def test_no_block_is_a_noop_and_never_raises(self):
        assert metric_authority_findings({}) == []
        assert metric_authority_findings({"data_authority": None}) == []
        assert metric_authority_findings({"data_authority": {"decisions": "not-a-list"}}) == []
        assert metric_authority_findings(cast(Any, "not-a-dict")) == []


class TestAttach:
    def test_clean_attaches_nothing_and_keeps_publishable(self):
        structured = _structured()
        warnings = attach_metric_authority_findings(structured, _raw(_decision("accepted")))
        assert warnings == []
        assert structured["numeric_audit"]["findings"] == []
        assert structured["numeric_audit"]["artifact_status"] == "publishable"

    def test_conflict_caveats_but_never_withholds(self):
        structured = _structured()
        warnings = attach_metric_authority_findings(
            structured,
            _raw(_decision("conflict", reason_code="above_tolerance_published_flagged")),
        )
        audit = structured["numeric_audit"]
        assert len(audit["findings"]) == 1
        assert audit["findings"][0]["check"] == "metric_authority_conflict"
        assert audit["artifact_status"] == "caveated"
        # review annotates — it never withholds the canonical value.
        assert audit["withhold_valuation"] is False
        assert structured["thesis"]["price_target"] == 100.0
        assert "valuation_withheld" not in structured
        assert len(warnings) == 1
        assert warnings[0].startswith("[NUMERIC-AUDIT/review]")
        assert warnings[0].startswith("[NUMERIC-AUDIT/review] data_authority.revenue")

    def test_second_attach_is_a_noop(self):
        structured = _structured()
        raw = _raw(_decision("conflict"))
        attach_metric_authority_findings(structured, raw)
        assert attach_metric_authority_findings(structured, raw) == []
        assert len(structured["numeric_audit"]["findings"]) == 1

    def test_noop_without_block_or_numeric_audit(self):
        structured = _structured()
        assert attach_metric_authority_findings(structured, {}) == []
        assert structured["numeric_audit"]["findings"] == []
        bare: dict[str, Any] = {}
        assert attach_metric_authority_findings(bare, _raw(_decision("conflict"))) == []
        assert "numeric_audit" not in bare


def _report() -> ReconciliationReport:
    decision = MetricDecision(
        metric="revenue",
        status="conflict",
        value=1_000.0,
        unit="USD",
        currency="USD",
        selected_source="fmp",
        is_authoritative=True,
        reason_code="above_tolerance_published_flagged",
        policy_version="metric_authority_v1",
        definition_version="revenue_1",
        basis="as-reported TTM revenue",
        comparability="as_reported_period",
        tolerance_pct=0.15,
        tolerance_abs=None,
        period_end=None,
        period_basis="ttm",
        disagreement_pct=0.18,
        agreement_is_independent=True,
        candidates=(
            MetricCandidate("fmp", 1_000.0, True, None, None, "authoritative_selected"),
            MetricCandidate(
                "yfinance", 1180.0, True, 0.18, 180.0, "above_tolerance_published_flagged"
            ),
        ),
        reconciled_at=_CLOCK,
    )
    return ReconciliationReport("metric_authority_v1", None, _CLOCK, (decision,))


def _fd() -> FinancialData:
    return FinancialData(
        ticker="X",
        timestamp=_CLOCK,
        income=IncomeStatement(revenue=100e9, net_income=20e9),
        market=MarketData(market_cap=500e9, shares_outstanding=5e9, current_price=100.0),
        data_source="fake",
        data_authority=_report(),
    )


def test_built_artifact_surfaces_the_conflict_finding():
    result = PipelineResult(
        steps={"data_collection": "ok", "thesis": "Price target $100"},
        structured_data={
            "data_collection": _fd(),
            "thesis": {"recommendation": "BUY", "price_target": 100.0, "tagline": "t"},
        },
    )
    art = build_equity_research_artifact(result, "X", cast(Any, None))
    structured = art.outputs.structured
    checks = [f["check"] for f in structured["numeric_audit"]["findings"]]
    assert "metric_authority_conflict" in checks
    assert structured["numeric_audit"]["artifact_status"] == "caveated"
    assert structured["numeric_audit"]["withhold_valuation"] is False
    assert any(
        w.startswith("[NUMERIC-AUDIT/review] data_authority.revenue") for w in art.outputs.warnings
    )
    # The canonical value stayed published: the target is not withheld.
    assert structured["thesis"]["price_target"] == 100.0
    assert structured.get("valuation_withheld") is not True
    assert "data_authority" in art.inputs.raw_data
