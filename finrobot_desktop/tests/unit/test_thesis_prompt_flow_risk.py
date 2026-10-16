"""Thesis prompt: reverse-DCF wording, insider flow, and payor risk.

Owner review 2026-10-13:
  * the market-implied WACC was appended inside the SAME sentence as the implied
    growth, so the model narrated two separate one-variable solves as one joint
    market forecast;
  * the 90-day insider net was never supplied to the prompt (it existed only
    client-side), so an "accumulation" claim went unchallenged;
  * payor reimbursement risk was omitted from the bear case even though the
    report's own overview names Medicare / managed-care payors as the revenue base.
"""

from __future__ import annotations

from datetime import datetime, timezone

from finrobot.engine.compute.operators.audit import audit_narrative_numeric_grounding
from finrobot.engine.compute.operators.valuation_synthesis import (
    resolve_canonical_thesis,
    synthesize_valuations,
)
from finrobot.engine.models.financial import (
    CatalystAnalysis,
    CatalystEvent,
    CompanyFinancials,
    DCFInputs,
    DCFResult,
    FinancialData,
    IncomeStatement,
    MarketData,
    MarketImpliedCheck,
    PeerComps,
    ThesisResult,
    ValuationMethod,
)
from finrobot.engine.models.sec import InsiderSale, OwnershipGovernanceAnalysis
from finrobot.engine.pipelines._thesis_prompt import (
    build_thesis_prompt,
    ensure_payor_reimbursement_risk,
)


def _methods() -> list[ValuationMethod]:
    return [
        ValuationMethod(name="dcf", low=200.0, mid=246.0, high=295.0, confidence=0.85, source="DCF")
    ]


def _prompt(extra_context: dict[str, object] | None = None, ticker: str = "EHC") -> str:
    vs = synthesize_valuations(_methods(), current_price=124.42)
    canonical = resolve_canonical_thesis(vs, ticker)
    context: dict[str, object] = {"valuation_synthesis": vs}
    if extra_context:
        context.update(extra_context)
    return build_thesis_prompt("BASE PROMPT", context, canonical)


def _dcf(market_implied: MarketImpliedCheck) -> DCFResult:
    inputs = DCFInputs(
        revenue_base=6.206e9,
        revenue_growth_rates=[0.11, 0.09, 0.07, 0.05, 0.03],
        ebitda_margin=0.236,
        capex_pct_revenue=0.06,
        nwc_pct_revenue=0.01,
        da_pct_revenue=0.05,
        tax_rate=0.24,
        risk_free_rate=0.042,
        beta=0.80,
        equity_risk_premium=0.055,
        cost_of_debt=0.055,
        debt_ratio=0.35,
        terminal_growth_rate=0.03,
        shares_outstanding=98_653_384.0,
        net_debt=2_734_599_904.0,
    )
    return DCFResult(
        cost_of_equity=0.086,
        wacc=0.06971583960763642,
        projection_years=5,
        projected_revenue=[6.9e9, 7.5e9, 8.0e9, 8.4e9, 8.7e9],
        projected_ebitda=[1.6e9, 1.8e9, 1.9e9, 2.0e9, 2.1e9],
        projected_fcf=[0.8e9, 0.9e9, 1.0e9, 1.1e9, 1.2e9],
        terminal_value=40.35e9,
        pv_terminal=30.0e9,
        pv_fcf_total=5.0e9,
        enterprise_value=25.02e9,
        equity_value=22.29e9,
        implied_price=225.91,
        market_implied=market_implied,
        inputs=inputs,
    )


def _financial_data(*, industry: str, sector: str, revenue: float = 6.206e9) -> FinancialData:
    return FinancialData(
        ticker="EHC",
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        income=IncomeStatement(revenue=revenue),
        market=MarketData(
            market_cap=12.27e9,
            shares_outstanding=98_653_384.0,
            current_price=124.42,
            industry=industry,
            sector=sector,
        ),
    )


def _ownership() -> OwnershipGovernanceAnalysis:
    return OwnershipGovernanceAnalysis(
        generated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        insider_net_flow=-26_430_022.85,
        insider_buy_value=0.0,
        insider_sell_value=26_430_022.85,
        insider_window_days=90,
        insider_largest_sale=InsiderSale(
            name="Mark J Tarr", position="President & CEO", value=21_525_046.74
        ),
        institutional_shares_listed=5_267_149,
        institutional_coverage_pct=5.34,
    )


class TestReverseDcfSolvesAreSeparate:
    def test_each_solve_names_what_it_holds_fixed(self):
        dcf = _dcf(
            MarketImpliedCheck(
                horizon_years=10,
                implied_growth=0.012280273,
                implied_wacc=0.09101318,
                growth_unreachable=False,
            )
        )
        prompt = _prompt({"financial_modeling": dcf})
        assert "SEPARATE single-variable solves" in prompt
        assert "NOT a joint market forecast" in prompt
        # WACC solve: growth fade held fixed, with the gap to the model's own WACC
        # injected as a COMPUTED number (9.1013% - 6.97% = 213bp) so the narrative
        # never re-derives it from rounded rates (NVDA 2026-10-16 read "132bp").
        assert "Holding the model's growth fade fixed, the current price implies a ~9.10%" in prompt
        assert "213bp above the model's 6.97% WACC" in prompt
        # growth solve: the MODEL's WACC (6.97%) held fixed
        assert "Holding the model's 6.97% WACC fixed, the current price implies ~1.2%/yr" in prompt
        # the old conflating shape is gone
        assert "(implied WACC ~9.1%)" not in prompt

    def test_whitelist_labels_the_two_solves(self):
        dcf = _dcf(
            MarketImpliedCheck(horizon_years=10, implied_growth=0.01228, implied_wacc=0.09101)
        )
        prompt = _prompt({"financial_modeling": dcf})
        assert "implied annual growth, solved with the model's WACC held fixed" in prompt
        assert "implied discount rate, solved with the model's growth fade held fixed" in prompt

    def test_growth_only_read_is_still_stated(self):
        dcf = _dcf(MarketImpliedCheck(horizon_years=10, implied_growth=0.01228))
        prompt = _prompt({"financial_modeling": dcf})
        assert "Holding the model's 6.97% WACC fixed" in prompt
        assert "Holding the model's growth fade fixed" not in prompt


class TestInsiderFlowInPrompt:
    def test_net_flow_and_largest_sale_are_whitelisted(self):
        prompt = _prompt({"ownership_governance_analysis": _ownership()})
        assert "insider_net_flow" in prompt
        assert "$-26,430,023" in prompt
        assert "90-day" in prompt
        assert "largest single insider sale: Mark J Tarr, President & CEO, $21,525,047" in prompt
        assert "institutional_coverage_pct" in prompt

    def test_flow_rule_forbids_accumulation_over_a_net_sale(self):
        prompt = _prompt({"ownership_governance_analysis": _ownership()})
        assert "OWNERSHIP FLOW RULE" in prompt
        assert "do NOT call the pattern accumulation" in prompt
        assert "say the insiders were net sellers" in prompt
        assert "do NOT assert holder concentration" in prompt

    def test_no_ownership_section_adds_no_flow_rule(self):
        prompt = _prompt()
        assert "OWNERSHIP FLOW RULE" not in prompt
        assert "insider_net_flow" not in prompt


class TestPayorReimbursementRisk:
    def _thesis(self, **overrides: object) -> ThesisResult:
        payload: dict[str, object] = {
            "recommendation": "BUY",
            "price_target": 225.91,
            "price_target_basis": "synthesis",
            "catalysts": ["DCF value of $225.91 against the $124.42 price."],
            "risks": ["Single-method concentration: the $225.91 target rests on one DCF."],
            "narrative": "Margin expansion drives a 6.97% WACC re-rating.",
        }
        payload.update(overrides)
        return ThesisResult(**payload)  # type: ignore[arg-type]

    def test_fires_for_a_payor_dependent_provider(self):
        context = {
            "data_collection": _financial_data(
                industry="Medical Care Facilities", sector="Healthcare"
            ),
            "financial_modeling": _dcf(MarketImpliedCheck(horizon_years=10, implied_growth=0.0123)),
        }
        thesis = ensure_payor_reimbursement_risk(self._thesis(), context)
        assert len(thesis.risks) == 2
        risk = thesis.risks[-1]
        assert "Reimbursement / payor-mix risk" in risk
        assert "managed-care payors" in risk
        assert "terminal growth 3.0%" in risk  # the model's own assumption
        assert "6.97% WACC" in risk
        # the entry carries a real figure, so the grounding backstop stays quiet
        assert audit_narrative_numeric_grounding(thesis) is None

    def test_fires_from_the_revenue_base_when_no_dcf_is_present(self):
        context = {
            "data_collection": _financial_data(
                industry="Medical Care Facilities", sector="Healthcare"
            ),
        }
        thesis = ensure_payor_reimbursement_risk(self._thesis(), context)
        assert len(thesis.risks) == 2
        assert "USD 6.21B revenue base" in thesis.risks[-1]

    def test_does_not_fire_for_a_non_payor_issuer(self):
        context = {
            "data_collection": _financial_data(industry="Semiconductors", sector="Technology"),
            "financial_modeling": _dcf(MarketImpliedCheck(horizon_years=10, implied_growth=0.05)),
        }
        thesis = self._thesis()
        assert ensure_payor_reimbursement_risk(thesis, context) is thesis

    def test_is_idempotent_when_a_payor_risk_already_exists(self):
        context = {
            "data_collection": _financial_data(
                industry="Medical Care Facilities", sector="Healthcare"
            ),
        }
        existing = self._thesis(
            risks=["Reimbursement risk: Medicare rate pressure compresses margin."]
        )
        assert ensure_payor_reimbursement_risk(existing, context) is existing

    def test_fires_from_a_healthcare_overview_that_names_payors(self):
        context = {
            "data_collection": _financial_data(industry="Medical Instruments", sector="Healthcare")
        }
        thesis = self._thesis(
            company_overview="Revenue is billed to Medicare, Medicare Advantage and commercial payors."
        )
        assert len(ensure_payor_reimbursement_risk(thesis, context).risks) == 2

    def test_no_healthcare_signal_and_no_mention_never_fires(self):
        context = {
            "data_collection": _financial_data(industry="Semiconductors", sector="Technology")
        }
        thesis = self._thesis(company_overview="We sell GPUs to cloud providers.")
        assert ensure_payor_reimbursement_risk(thesis, context) is thesis


# ── Narrative-labelled prompt discipline (2026-10-13 NVDA) ────────────────────
# Four prose defects in the audited artifact traced to what the prompt did NOT
# say: an insider "purchases" figure back-filled with the DCF target price, the
# missing peer set blamed on the whitelist instead of the failed fetch, the
# market's implied growth called "demanding" without the model's own average next
# to it, and news-category counts read as SEC filing counts.


def _catalyst() -> CatalystAnalysis:
    """One single-source acquisition RUMOUR — the x2 shape the discipline targets."""
    event = CatalystEvent(
        category="acquisition",
        headline="Report: Reflection AI in advanced talks with the company",
        sentiment="positive",
        impact_score=4,
        source_count=1,
        published=datetime(2026, 9, 28, tzinfo=timezone.utc),
        reasoning="a single unverified report of talks",
    )
    return CatalystAnalysis(
        events=[event],
        overall_sentiment="bullish",
        key_catalysts=["x"],
        net_sentiment=0.4,
        category_breakdown={"acquisition": 1, "product_launch": 2},
        top_positive=[event],
        top_negative=[],
    )


def _company(ticker: str, market_cap: float) -> CompanyFinancials:
    return CompanyFinancials(
        ticker=ticker,
        name=ticker,
        revenue=6.2e9,
        ebitda=1.4e9,
        net_income=0.8e9,
        market_cap=market_cap,
        total_debt=4.0e9,
        total_cash=0.5e9,
        gross_margin=0.5,
        operating_margin=0.2,
        pe_ratio=15.3,
        ev_ebitda=11.2,
    )


def _peer_comps() -> PeerComps:
    return PeerComps(
        target=_company("EHC", 12.27e9),
        peers=[_company("UHS", 11.0e9)],
        median_ev_ebitda=10.5,
        median_pe=14.0,
        median_ev_revenue=1.5,
    )


class TestNarrativeLabelDiscipline:
    def test_zero_insider_purchases_is_stated_and_other_numbers_are_barred(self):
        """Defect 1: "$259.87 of purchases" — the DCF target pasted in as the
        purchases figure while the true gross purchases were $0."""
        prompt = _prompt({"ownership_governance_analysis": _ownership()})
        assert "INSIDER PURCHASES = $0" in prompt
        assert "NO open-market insider purchases" in prompt
        assert "PURCHASE FIGURE RULE" in prompt
        # The bar must name the DIRECTIONS the model back-filled from.
        assert "price target" in prompt and "misattribution" in prompt

    def test_purchase_rule_absent_when_there_were_real_purchases(self):
        ownership = _ownership().model_copy(
            update={"insider_buy_value": 5_000_000.0, "insider_net_flow": -21_430_022.85}
        )
        prompt = _prompt({"ownership_governance_analysis": ownership})
        assert "INSIDER PURCHASES = $0" not in prompt
        assert "PURCHASE FIGURE RULE" not in prompt

    def test_peer_absence_names_the_fetch_failure_not_the_whitelist(self):
        """i6: page 6 blamed "this run's whitelist" for the missing peer table
        while the run's warning said the data sources had failed."""
        prompt = _prompt(
            {
                "financial_modeling": _dcf(
                    MarketImpliedCheck(horizon_years=10, implied_growth=0.0123)
                )
            }
        )
        assert "PEER-SET ABSENCE" in prompt
        assert "data fetch returned no usable comp set" in prompt
        assert "peer analysis did not run for this ticker" in prompt
        assert "Do NOT explain the missing peer multiples by blaming this whitelist" in prompt

    def test_peer_absence_note_dropped_when_a_peer_set_is_present(self):
        prompt = _prompt({"peer_analysis": _peer_comps()})
        assert "PEER-SET ABSENCE" not in prompt

    def test_model_average_growth_sits_next_to_the_implied_rate(self):
        """l4: the market's ~20.8% was called a "demanding bar" while the model's
        own fade averages ~21.5%/yr — the prose claimed a bar the model clears."""
        dcf = _dcf(MarketImpliedCheck(horizon_years=10, implied_growth=0.208))
        prompt = _prompt({"financial_modeling": dcf})
        # schedule [0.11, 0.09, 0.07, 0.05, 0.03] → endpoints 11.0% / 3.0%, avg 7.0%
        assert "MODEL's OWN revenue-growth assumption" in prompt
        assert "11.0%/yr in forecast year 1" in prompt
        assert "3.0%/yr in year 5" in prompt
        assert "averaging 7.0%/yr" in prompt
        assert "FADE schedule" in prompt and "a DECLINING rate, not a flat one" in prompt
        assert "flat rate vs a " in prompt and "different constructs" in prompt
        # and it is whitelisted, so a claim checker can match the citation
        assert "average 7.0%/yr over the 5 forecast fiscal years" in prompt

    def test_period_labeling_rule_is_present(self):
        """i5: FY margins and TTM tiles were cited unlabelled."""
        prompt = _prompt()
        assert "PERIOD LABELING RULE" in prompt
        assert "never cite a margin without naming its basis" in prompt

    def test_catalyst_category_breakdown_is_labelled_as_news_not_filings(self):
        """Defect 4 / i6: "2 acquisition-category 8-Ks" read off news counts."""
        prompt = _prompt({"catalyst_analysis": _catalyst()})
        assert "News items by category" in prompt
        assert "acquisition: 1, product_launch: 2" in prompt
        assert "NOT a count of SEC filings" in prompt

    def test_catalyst_event_lines_carry_source_count_and_date(self):
        prompt = _prompt({"catalyst_analysis": _catalyst()})
        assert "source count: 1" in prompt
        assert "published: 2026-09-28" in prompt

    def test_news_impact_discipline_rule_is_present(self):
        """x2: a single-source "advanced talks" report shipped as an impact-4
        acquisition; an already-announced ramp was called a new catalyst."""
        prompt = _prompt()
        assert "NEWS-IMPACT DISCIPLINE" in prompt
        assert "REPORTED / early-stage / unconfirmed" in prompt
        assert "NOT a new catalyst" in prompt
        assert "Source count is 1" in prompt
