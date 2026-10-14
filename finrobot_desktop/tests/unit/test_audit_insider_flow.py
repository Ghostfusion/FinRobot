"""The insider-flow attribution verifier (NVDA 2026-10-13 report defect).

The audited report's Key Takeaways read "insiders were net sellers of $967.6M over 90
days ($259.87 of purchases vs $967.6M of sales)" while the same report's Risks section
read "$0 of open-market purchases against $967.6M of sales" and the computed leaves were
`insider_buy_value = 0.0`, `insider_sell_value = 967,599,313.46`. `$259.87` is the DCF
price target — a computed leaf of its own — so the drift detector's membership test
passed it. These tests pin the RELATIONSHIP check that catches it, and the guards that
keep it from accusing legitimate prose.
"""

from __future__ import annotations

from typing import Any

from finrobot.engine.compute.operators.audit.insider_flow import (
    _NET_FLOW_RE,
    attach_insider_flow_findings,
    correct_insider_flow_claims,
    insider_flow_amount_findings,
)

# The real leaves behind the audited report.
_OWNERSHIP: dict[str, Any] = {
    "insider_net_flow": -967599313.4594998,
    "insider_buy_value": 0.0,
    "insider_sell_value": 967599313.4594998,
    "insider_window_days": 90,
    "insider_largest_sale": {
        "name": "Mark A Stevens",
        "position": "Director",
        "value": 297942896.4,
    },
}

_KEY_TAKEAWAY = (
    "Ownership signals are mixed-to-soft: insiders were net sellers of $967.6M over "
    "90 days ($259.87 of purchases vs $967.6M of sales), while 13F rows on file cover "
    "only 5.4% of shares outstanding."
)
_RISK = (
    "Insider distribution: 90-day net insider flow of -$967.6M, with $0 of open-market "
    "purchases against $967.6M of sales and a largest single sale of $297.9M."
)


class TestShippedDefect:
    def test_flags_the_target_price_written_as_a_purchase_figure(self) -> None:
        findings = insider_flow_amount_findings([_KEY_TAKEAWAY], _OWNERSHIP)
        assert len(findings) == 1
        finding = findings[0]
        assert finding.check == "insider_flow_amount_mismatch"
        assert finding.severity == "review"
        assert finding.field_key == "ownership_governance.insider_buy_value"
        # The evidence must name BOTH the printed figure and the computed one.
        assert "$259.87" in finding.evidence
        assert "$0" in finding.evidence
        assert "90-day" in finding.evidence

    def test_sales_leg_in_the_same_sentence_is_not_flagged(self) -> None:
        """$967.6M IS the sale leg — only the purchases figure is misattributed."""
        findings = insider_flow_amount_findings([_KEY_TAKEAWAY], _OWNERSHIP)
        assert [f.field_key for f in findings] == ["ownership_governance.insider_buy_value"]

    def test_correct_zero_purchase_claim_passes(self) -> None:
        assert insider_flow_amount_findings([_RISK], _OWNERSHIP) == []

    def test_attach_annotates_and_is_idempotent(self) -> None:
        structured: dict[str, Any] = {
            "numeric_audit": {"findings": [], "artifact_status": "publishable"},
            "ownership_governance": _OWNERSHIP,
        }
        warnings = attach_insider_flow_findings(structured, [_KEY_TAKEAWAY])
        assert len(warnings) == 1 and warnings[0].startswith("[NUMERIC-AUDIT/review]")
        assert structured["numeric_audit"]["artifact_status"] == "caveated"
        assert len(structured["numeric_audit"]["findings"]) == 1

        assert attach_insider_flow_findings(structured, [_KEY_TAKEAWAY]) == []
        assert len(structured["numeric_audit"]["findings"]) == 1


class TestWrongSalesFigureToo:
    def test_a_mismatched_sale_aggregate_is_flagged(self) -> None:
        findings = insider_flow_amount_findings(
            ["Insiders were net sellers: $500M of sales over the window."], _OWNERSHIP
        )
        assert [f.field_key for f in findings] == ["ownership_governance.insider_sell_value"]
        assert "$500,000,000.00" in findings[0].evidence


class TestNoFalsePositives:
    def test_single_transaction_figures_stay_out_of_scope(self) -> None:
        """A singular "sale" is one transaction, not the gross aggregate."""
        text = "Director Mark A Stevens reported a single sale of $297.9M on 2026-09-22."
        assert insider_flow_amount_findings([text], _OWNERSHIP) == []

    def test_institutional_statements_are_not_insider_flow(self) -> None:
        text = "Vanguard's purchases of $12.4B and sales of $3.1B were reported this quarter."
        assert insider_flow_amount_findings([text], _OWNERSHIP) == []

    def test_share_repurchases_are_not_insider_flow(self) -> None:
        text = "The board approved $150B of repurchases, against $967.6M of insider sales."
        findings = insider_flow_amount_findings([text], _OWNERSHIP)
        assert findings == []

    def test_rounding_of_the_computed_leg_passes(self) -> None:
        text = "Insiders were net sellers with $967.6M of sales over 90 days."
        assert insider_flow_amount_findings([text], _OWNERSHIP) == []

    def test_zero_purchases_stated_as_zero_passes(self) -> None:
        text = "Insiders made purchases of $0 while sales reached $967.6M."
        assert insider_flow_amount_findings([text], _OWNERSHIP) == []


class TestCorrection:
    """The wrong figure must not ship at all — a caveat still prints it."""

    def test_misattributed_purchase_figure_is_replaced_with_the_computed_leg(self) -> None:
        # The live 2026-10-14 run repeated the defect with the new target.
        text = (
            "Flows argue against adding here: insiders were net sellers at -$967,599,313 "
            "over 90 days with $231.38 of open-market purchases, 13F coverage is only 5.4%."
        )
        corrected, notes = correct_insider_flow_claims(text, _OWNERSHIP)
        assert "$0 of open-market purchases" in corrected
        assert "$231.38" not in corrected
        assert len(notes) == 1 and "corrected" in notes[0]

    def test_the_audited_sentence_loses_only_the_target_price(self) -> None:
        corrected, notes = correct_insider_flow_claims(_KEY_TAKEAWAY, _OWNERSHIP)
        assert "$259.87" not in corrected
        assert "$0 of purchases" in corrected
        # The sale leg and the net flow are untouched.
        assert "$967.6M of sales" in corrected and "$967.6M over" in corrected
        assert len(notes) == 1

    def test_correct_text_is_returned_unchanged(self) -> None:
        corrected, notes = correct_insider_flow_claims(_RISK, _OWNERSHIP)
        assert corrected == _RISK and notes == []

    def test_nothing_is_corrected_where_nothing_is_checkable(self) -> None:
        text = "Director Mark A Stevens reported a single sale of $297.9M."
        assert correct_insider_flow_claims(text, _OWNERSHIP) == (text, [])
        assert correct_insider_flow_claims(text, None) == (text, [])

    def test_a_sales_leg_mismatch_is_corrected_to_the_sale_leg(self) -> None:
        text = "Insiders reported $500M of sales over the window."
        corrected, notes = correct_insider_flow_claims(text, _OWNERSHIP)
        assert "$967,599,313 of sales" in corrected
        assert len(notes) == 1 and "sales" in notes[0]


class TestLargestSaleAndAmbiguity:
    """The 2026-10-14 live run misattributed the target into "largest single sale",
    and a naive rewrite could move a figure that was legitimately another leg."""

    def test_largest_single_sale_figure_is_checked_and_corrected(self) -> None:
        text = (
            "Flow is the negative tell: 90-day net insider flow of -$967,599,313, with "
            "$0 of open-market purchases against $967,599,313 of sales (largest single "
            "sale $231.38), while 13F rows cover only 5.4% of shares."
        )
        findings = insider_flow_amount_findings([text], _OWNERSHIP)
        assert [f.field_key for f in findings] == ["ownership_governance.insider_largest_sale"]
        corrected, notes = correct_insider_flow_claims(text, _OWNERSHIP)
        assert "largest single sale $297,942,896" in corrected
        assert "$231.38" not in corrected
        assert len(notes) == 1

    def test_a_correct_largest_sale_is_untouched(self) -> None:
        text = "Insiders sold $967,599,313 in aggregate; the largest single sale was $297,942,896."
        assert insider_flow_amount_findings([text], _OWNERSHIP) == []
        assert correct_insider_flow_claims(text, _OWNERSHIP) == (text, [])

    def test_a_figure_that_is_another_leg_is_reported_not_rewritten(self) -> None:
        """The live run's false rewrite: the SALE leg printed next to "purchases"."""
        text = "Insiders showed $967,600,000.00 of purchases and $967,599,313 of sales."
        findings = insider_flow_amount_findings([text], _OWNERSHIP)
        assert findings, "the mismatch is still reported"
        corrected, notes = correct_insider_flow_claims(text, _OWNERSHIP)
        assert corrected == text, "an ambiguous figure is never rewritten"
        assert notes == []

    def test_a_sentence_naming_both_nouns_is_not_rewritten(self) -> None:
        text = "Insiders reported $231.38 across purchases and sales over the 90-day window."
        corrected, notes = correct_insider_flow_claims(text, _OWNERSHIP)
        assert corrected == text and notes == []


class TestRobustness:
    def test_absent_or_empty_ownership_never_raises(self) -> None:
        assert insider_flow_amount_findings([_KEY_TAKEAWAY], None) == []
        assert insider_flow_amount_findings([_KEY_TAKEAWAY], {}) == []
        assert insider_flow_amount_findings([_KEY_TAKEAWAY], {"insider_sell_value": None}) == []

    def test_non_text_and_empty_narratives_are_skipped(self) -> None:
        assert insider_flow_amount_findings(["", "   "], _OWNERSHIP) == []
        assert insider_flow_amount_findings([None], _OWNERSHIP) == []  # type: ignore[list-item]

    def test_attach_no_ops_without_a_numeric_audit_block(self) -> None:
        structured: dict[str, Any] = {"ownership_governance": _OWNERSHIP}
        assert attach_insider_flow_findings(structured, [_KEY_TAKEAWAY]) == []


class TestNetFlowLeg:
    """GMED 2026-10-14: "insiders were net sellers of $90.61 over the last 90 days
    with $0 of open-market purchases" — the price target written as the net insider
    flow. The plural-aggregate rule cannot see it (its noun is "sellers"), and the
    target reconciler ENFORCED it rather than questioning it, because $90.61 IS the
    canonical target it rewrites drifting amounts TO.
    """

    _SENTENCE = (
        "The ownership tape is unfavorable: insiders were net sellers of $90.61 over the "
        "last 90 days with $0 of open-market purchases (largest single sale $2,237,502)."
    )
    _GMED: dict[str, Any] = {
        "insider_net_flow": -4413467.0,
        "insider_buy_value": 0.0,
        "insider_sell_value": 4413467.0,
        "insider_window_days": 90,
        "insider_largest_sale": {"value": 2237502.0},
    }

    def test_target_price_written_as_the_net_flow_is_flagged_and_corrected(self) -> None:
        findings = insider_flow_amount_findings([self._SENTENCE], self._GMED)
        assert [f.field_key for f in findings] == ["ownership_governance.insider_net_flow"]
        assert "$90.61" in findings[0].evidence
        corrected, notes = correct_insider_flow_claims(self._SENTENCE, self._GMED)
        assert "$90.61" not in corrected
        assert "$4,413,467" in corrected
        assert notes and "net flow" in notes[0]

    def test_the_true_net_flow_sentence_passes(self) -> None:
        text = (
            "Insider supply: the 90-day insider net flow is -$4,413,467 with $0 of "
            "open-market purchases, and the largest single sale was $2,237,502."
        )
        assert insider_flow_amount_findings([text], self._GMED) == []

    def test_the_net_phrase_never_claims_a_revenue_line(self) -> None:
        # "net sales" is a revenue metric, not an insider-flow leg: the phrase requires
        # a flow verb/noun ("net sellers", "net flow"), never the bare "net sales".
        assert _NET_FLOW_RE.search("net sales of $2.9bn") is None
        assert _NET_FLOW_RE.search("insiders were net sellers of $90.61") is not None
        assert _NET_FLOW_RE.search("90-day net insider flow of -$4,413,467") is not None

    def test_an_aggregate_leg_owns_its_token_over_the_net_phrase(self) -> None:
        """One token, one claim: "net sellers: $500M of sales" is a SALES claim, so the
        net phrase must not add a second finding for the same figure (it is a fallback
        for amounts no aggregate noun covers)."""
        findings = insider_flow_amount_findings(
            ["Insiders were net sellers: $500M of sales over the window."], self._GMED
        )
        assert [f.field_key for f in findings] == ["ownership_governance.insider_sell_value"]
