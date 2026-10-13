"""The published-target-vs-own-multiple-band audit verifier.

Owner review 2026-10-13: EHC's $225.91 target implied ~17x TTM EBITDA against an
issuer whose own 5-year EV/EBITDA p90 was 12.2x, and nothing in the report said
so. These tests pin the implied-multiple math, when the finding fires (above p90,
below p25), when it must stay silent (inside the band, missing inputs), and the
artifact adapter/wiring that puts the finding into ``structured.numeric_audit``.
"""

from __future__ import annotations

from finrobot.engine.compute.operators.audit.valuation_band import (
    attach_target_multiple_band_findings,
    audit_target_multiple_band,
    publish_band_cross_check,
    target_multiple_band_findings_from_structured,
)

# EHC-like inputs (the owner-review case).
_EHC = {
    "target_price": 225.91,
    "shares_outstanding": 98_653_384.0,
    "net_debt": 2_842_299_904.0 - 107_700_000.0,
    "preferred_stock": None,
    "noncontrolling_interest": 863_400_000.0,
    "ttm_ebitda": 1_463_500_032.0,
    "band_p25": 9.975651894724482,
    "band_p90": 12.164236111867318,
    "window_years": 5,
}


def _run(**overrides: object):
    kwargs = dict(_EHC)
    kwargs.update(overrides)
    return audit_target_multiple_band("EHC", **kwargs)  # type: ignore[arg-type]


class TestOutsideTheBandFinding:
    def test_implied_multiple_math_and_evidence(self):
        """implied = (target × shares + net debt + NCI) / TTM EBITDA."""
        findings = _run()
        assert len(findings) == 1
        finding = findings[0]
        expected = (
            _EHC["target_price"] * _EHC["shares_outstanding"]
            + _EHC["net_debt"]
            + _EHC["noncontrolling_interest"]
        ) / _EHC["ttm_ebitda"]
        assert finding.severity == "review"
        assert finding.field_key == "thesis.price_target"
        assert finding.check == "target_multiple_outside_band"
        assert f"{expected:.1f}x" in finding.evidence
        assert "$225.91" in finding.evidence
        assert "12.2x" in finding.evidence
        assert "5-year p90" in finding.evidence
        assert "above its own historical multiple range" in finding.evidence

    def test_fires_above_p90_and_below_p25_and_is_silent_inside(self):
        above = _run(target_price=225.91)
        horizon = _run(target_price=120.0)  # implied ≈ 10.5x → inside [p25, p90]
        below = _run(target_price=95.0)  # implied ≈ 8.9x → under p25
        assert len(above) == 1 and "p90" in above[0].evidence
        assert horizon == []
        assert len(below) == 1 and "p25" in below[0].evidence
        assert "below its own historical multiple range" in below[0].evidence

    def test_silent_without_a_band_or_a_denominator(self):
        assert _run(band_p90=None) == []
        assert _run(band_p25=None) == []
        assert _run(ttm_ebitda=None) == []
        assert _run(target_price=None) == []
        assert _run(shares_outstanding=None) == []
        assert _run(net_debt=None) == []

    def test_preferred_and_nci_are_subtracted_from_the_implied_multiple(self):
        """A target's implied multiple includes the ENTIRE EV bridge — dropping
        the NCI would understate the implied multiple by ~0.6x on EHC."""
        with_nci = _run()[0].evidence
        without_nci = _run(noncontrolling_interest=None)[0].evidence
        assert with_nci != without_nci


def _structured_and_raw() -> tuple[dict, dict]:
    structured = {
        "thesis": {"price_target": 225.91},
        "technical_analysis": {
            "historical_bands": {
                "metric": "ev_ebitda",
                "p25": _EHC["band_p25"],
                "median": 10.590751147845076,
                "p75": 11.401397804210033,
                "p90": _EHC["band_p90"],
                "window_years": 5,
                "sample_count": 947,
            }
        },
        "numeric_audit": {
            "findings": [
                {
                    "field_key": "enterprise_value",
                    "check": "ev_bridge_unverified",
                    "severity": "review",
                    "evidence": "existing",
                }
            ],
            "artifact_status": "caveated",
            "withhold_valuation": False,
        },
    }
    raw = {
        "ticker": "EHC",
        "income": {"ebitda": _EHC["ttm_ebitda"]},
        "balance": {
            "total_debt": 2_842_299_904.0,
            "total_cash": 107_700_000.0,
            "preferred_stock": None,
            "noncontrolling_interest": _EHC["noncontrolling_interest"],
        },
        "market": {"shares_outstanding": _EHC["shares_outstanding"]},
    }
    return structured, raw


class TestArtifactAdapterAndWiring:
    def test_adapter_reads_the_frozen_artifact(self):
        structured, raw = _structured_and_raw()
        findings = target_multiple_band_findings_from_structured(structured, raw)
        assert len(findings) == 1
        assert "17." in findings[0].evidence

    def test_adapter_silent_on_a_non_ev_band(self):
        structured, raw = _structured_and_raw()
        structured["technical_analysis"]["historical_bands"]["metric"] = "p_fcf"
        assert target_multiple_band_findings_from_structured(structured, raw) == []

    def test_adapter_silent_when_the_target_is_withheld(self):
        structured, raw = _structured_and_raw()
        structured["thesis"]["price_target"] = None
        assert target_multiple_band_findings_from_structured(structured, raw) == []

    def test_attach_appends_finding_and_keeps_the_existing_ones(self):
        structured, raw = _structured_and_raw()
        warnings = attach_target_multiple_band_findings(structured, raw)
        checks = [f["check"] for f in structured["numeric_audit"]["findings"]]
        assert checks == ["ev_bridge_unverified", "target_multiple_outside_band"]
        assert structured["numeric_audit"]["artifact_status"] == "caveated"
        # review annotates — it never withholds the target.
        assert structured["numeric_audit"]["withhold_valuation"] is False
        assert len(warnings) == 1
        assert warnings[0].startswith("[NUMERIC-AUDIT/review]")
        assert "thesis.price_target" in warnings[0]

    def test_attach_is_idempotent_and_a_noop_without_a_numeric_audit_block(self):
        structured, raw = _structured_and_raw()
        attach_target_multiple_band_findings(structured, raw)
        assert attach_target_multiple_band_findings(structured, raw) == []
        assert len(structured["numeric_audit"]["findings"]) == 2

        bare: dict = {}
        assert attach_target_multiple_band_findings(bare, raw) == []
        assert "numeric_audit" not in bare

    def test_inside_band_attaches_nothing(self):
        structured, raw = _structured_and_raw()
        structured["thesis"]["price_target"] = 120.0
        assert attach_target_multiple_band_findings(structured, raw) == []
        assert len(structured["numeric_audit"]["findings"]) == 1


class TestPublishBandCrossCheck:
    """The row the review asked to see in the football field: the issuer's own
    band applied to the run's TTM EBITDA, published from the technical chapter's
    frozen band when the synthesis' own band fetch came back empty."""

    def test_publishes_the_row_from_the_frozen_chapter_band(self):
        structured, raw = _structured_and_raw()
        structured["valuation_synthesis"] = {"current_price": 124.42, "cross_checks": []}
        assert publish_band_cross_check(structured, raw) is True
        rows = structured["valuation_synthesis"]["cross_checks"]
        assert len(rows) == 1
        assert rows[0]["name"] == "ev_ebitda_band"
        # (10.5908 × 1,463.5M − 2,734.6M − 863.4M) / 98,653,384 = 120.64
        assert rows[0]["mid"] == 120.64020773758054

    def test_never_replaces_a_row_the_synthesis_already_built(self):
        structured, raw = _structured_and_raw()
        mine = {"name": "ev_ebitda_band", "mid": 999.0}
        structured["valuation_synthesis"] = {"cross_checks": [mine]}
        assert publish_band_cross_check(structured, raw) is False
        assert structured["valuation_synthesis"]["cross_checks"] == [mine]

    def test_without_a_usable_band_nothing_is_published(self):
        structured, raw = _structured_and_raw()
        structured["technical_analysis"] = {}
        structured["valuation_synthesis"] = {"cross_checks": []}
        assert publish_band_cross_check(structured, raw) is False
        assert structured["valuation_synthesis"]["cross_checks"] == []
