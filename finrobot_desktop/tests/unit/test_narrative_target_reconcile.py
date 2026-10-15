"""BUG-016 guard: free-text narrative $-amounts must reconcile with the
canonical (deterministic) price target.

After the override block forces `price_target` to the confidence-weighted
canonical value, the headline-bearing prose fields from the SAME LLM call can
still print a contradicting $ amount (table says $276.43, prose says "约 $280").
`_reconcile_narrative_targets` is the code-only post-run guard that neutralizes
the drifting token to the canonical value — no second LLM call.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from finrobot.engine.compute.operators.valuation_synthesis import CanonicalThesis
from finrobot.engine.compute.operators.audit.insider_flow import insider_flow_amount_findings
from finrobot.engine.models.financial import (
    BalanceSheet,
    FinancialData,
    IncomeStatement,
    MarketData,
    ThesisResult,
    ValuationMethod,
    ValuationMetrics,
    ValuationSynthesis,
)
from finrobot.engine.models.identities import leaves_of_kind
from finrobot.engine.pipelines.equity_research import (
    _published_leaf_snapshot,
    _reconcile_narrative_targets,
    apply_canonical_override,
)


def _thesis(**overrides: object) -> ThesisResult:
    base: dict[str, object] = {
        "recommendation": "HOLD",
        "price_target": 276.43,
        "price_target_basis": "Confidence-weighted synthesis.",
        "catalysts": ["iPhone refresh cycle"],
        "risks": ["China demand softness"],
        "narrative": "Apple remains a quality compounder.",
    }
    base.update(overrides)
    return ThesisResult(**base)  # type: ignore[arg-type]


def test_drifting_prose_amount_is_neutralized_to_canonical(
    caplog: object,
) -> None:
    thesis = _thesis(
        valuation_overview=(
            "Weighting DCF and comps, we arrive at a fair value of roughly $280, "
            "implying modest upside from current levels."
        ),
    )

    with caplog.at_level(logging.WARNING):  # type: ignore[attr-defined]
        out, drift = _reconcile_narrative_targets(
            thesis, canonical_target=276.43, allowed_mids=[260.0, 295.0]
        )

    assert drift is True
    assert out.valuation_overview is not None
    assert "$280" not in out.valuation_overview
    assert "$276.43" in out.valuation_overview
    # Sentence structure preserved (least-invasive token swap).
    assert "implying modest upside" in out.valuation_overview
    # A drift warning was logged.
    assert any(  # type: ignore[attr-defined]
        "narrative target drift" in rec.message or "narrative target drift" in rec.getMessage()
        for rec in caplog.records  # type: ignore[attr-defined]
    )


def test_magnitude_suffixed_amounts_are_never_rewritten() -> None:
    """$3.41T / $391.0B / $3.4 billion are market-cap/EV-scale facts, not
    per-share targets. The reconciler used to match only the numeric body
    ("$3.41"), fail the whitelist, and rewrite it to the canonical target —
    shipping "$276.43T". Suffixed amounts are out of scope entirely (the
    report-level drift scanner owns them)."""
    thesis = _thesis(
        competitor_analysis=(
            "Versus megacap peers (market_cap=$3.41T) and an EV of $391.0B, "
            "the segment generates $3.4 billion in services revenue and "
            "carries $150B of net cash; smaller rival sits at $920.5M."
        ),
    )

    out, drift = _reconcile_narrative_targets(
        thesis, canonical_target=276.43, allowed_mids=[260.0, 295.0]
    )

    assert drift is False
    assert out.competitor_analysis == thesis.competitor_analysis


def test_minus_prefixed_amounts_are_never_rewritten() -> None:
    """-$1.20 (loss-quarter EPS / negative FCF per share) is categorically not a
    restatement of the positive canonical target. The reconciler used to match
    only the "$1.20" span, fail the whitelist, and rewrite it — shipping the
    sign-corrupted "-$276.43". Minus-prefixed amounts are out of scope (the
    report-level drift scanner validates them sign-aware against all leaves)."""
    thesis = _thesis(
        valuation_overview=("FY1 EPS of -$1.20 and FCF/share of −$0.85 keep the DCF inapplicable."),
    )

    out, drift = _reconcile_narrative_targets(
        thesis, canonical_target=276.43, allowed_mids=[260.0, 295.0]
    )

    assert drift is False
    assert out.valuation_overview == thesis.valuation_overview


def test_unsuffixed_total_is_never_rewritten() -> None:
    """An un-suffixed comma-form TOTAL is not a drifted per-share target.

    CF 2026-10-14: the thesis and the valuation chapter read "46.8% of the $80.69
    enterprise value landing in the terminal period" — the prose's own
    $15,783,943,454 EV rewritten to the canonical target, while the risk bullets on
    the SAME report still printed $15,783,943,454 (they are not scanned). The
    sourceless magnitude rules covered "$3.41T" but not the comma form, so a correct
    sentence was corrupted into two answers for one enterprise value.
    """
    thesis = _thesis(
        valuation_overview=(
            "The DCF lands at $75.85, with 46.8% of the $15,783,943,454 enterprise "
            "value arriving in the terminal period."
        ),
    )

    out, drift = _reconcile_narrative_targets(
        thesis,
        canonical_target=80.69,
        allowed_mids=[75.85, 86.40],
        current_price=119.46,
    )

    assert drift is False
    assert out.valuation_overview == thesis.valuation_overview
    assert "$15,783,943,454" in (out.valuation_overview or "")


def test_total_above_the_headroom_of_every_per_share_reference_is_kept() -> None:
    """The relative branch: >10× BOTH the target and the tape cannot be a per-share
    restatement even below the absolute floor — a debt/cash total on a low-priced
    name must survive."""
    thesis = _thesis(
        price_target=1.2,
        narrative="Total debt of $20,000 and $4,500 of cash leave the equity thin.",
    )

    out, drift = _reconcile_narrative_targets(
        thesis, canonical_target=1.2, allowed_mids=[], current_price=1.05
    )

    assert drift is False
    assert out.narrative == thesis.narrative


def test_a_plausible_drift_on_a_low_priced_name_is_still_neutralized() -> None:
    """The total gate must not blunt the guard: $1.35 against a $1.20 target is a
    per-share claim and is still rewritten."""
    thesis = _thesis(
        price_target=1.2,
        valuation_overview="Fair value of $1.35 on the trough multiple.",
    )

    out, drift = _reconcile_narrative_targets(
        thesis, canonical_target=1.2, allowed_mids=[], current_price=1.05
    )

    assert drift is True
    assert out.valuation_overview is not None
    assert "$1.20 on the trough multiple." in out.valuation_overview


def test_unsuffixed_total_survives_the_withheld_path() -> None:
    """With a withheld point, an un-suffixed total is data — not a smuggled target —
    and must not become a ``[target withheld]`` marker.

    With no per-share reference left the relative branch has nothing to compare
    against, so the absolute floor is what protects the figure here.
    """
    thesis = _thesis(
        narrative="The DCF's $15,783,943,454 enterprise value is 46.8% terminal perpetuity.",
    )

    out = apply_canonical_override(thesis, _thc_withheld_canonical(), _thc_withheld_vs())

    narrative = out.narrative or ""
    assert "$15,783,943,454" in narrative
    assert "[target withheld]" not in narrative


def test_plain_drift_amount_followed_by_word_still_rewritten() -> None:
    """The optional-suffix group must not swallow ordinary words: "$280 Buyback"
    is still a plain drifting per-share amount (B is followed by word chars, so
    the \\b suffix boundary fails) and must be neutralized."""
    thesis = _thesis(
        valuation_overview="Fair value near $280 Buyback support adds a floor.",
    )

    out, drift = _reconcile_narrative_targets(thesis, canonical_target=276.43, allowed_mids=[])

    assert drift is True
    assert out.valuation_overview is not None
    assert "$276.43 Buyback" in out.valuation_overview


def test_happy_path_matching_amount_is_untouched() -> None:
    overview = "Our weighted target of $276.43 reflects a balanced DCF/comps blend."
    thesis = _thesis(valuation_overview=overview)

    out, drift = _reconcile_narrative_targets(
        thesis, canonical_target=276.43, allowed_mids=[260.0, 295.0]
    )

    assert drift is False
    assert out.valuation_overview == overview


def test_within_tolerance_amount_is_untouched() -> None:
    # $277 is within 2% of $276.43 — not drift.
    overview = "We see fair value near $277, broadly in line with our weighted target."
    thesis = _thesis(valuation_overview=overview)

    out, drift = _reconcile_narrative_targets(thesis, canonical_target=276.43, allowed_mids=[])

    assert drift is False
    assert out.valuation_overview == overview


def test_per_method_mid_is_whitelisted_not_drift() -> None:
    # Quoting a per-method mid ("DCF $260, comps $295, they disagree") is the
    # honest narrative — must NOT be neutralized even though it != target.
    overview = "DCF implies $260 while comps imply $295; the blend lands at $276.43."
    thesis = _thesis(valuation_overview=overview)

    out, drift = _reconcile_narrative_targets(
        thesis, canonical_target=276.43, allowed_mids=[260.0, 295.0]
    )

    assert drift is False
    assert out.valuation_overview == overview


def test_per_method_band_bounds_are_whitelisted_not_drift() -> None:
    """A method's OWN low/high band is published prose, not drift.

    Owner review 2026-10-13: the canonical basis prints "DCF $151.38 (own range
    $121.10–$181.66)"; leaving the bounds out of the whitelist had the scrubber
    rewrite them to the target, so the published basis read "own range
    $151.38–$151.38" — a "low" and a "high" that were both the target.
    """
    basis = "Blend of 1 method: DCF $151.38 (own range $121.10–$181.66, wt 0.85) → $151.38."
    thesis = _thesis(price_target_basis=basis)

    vs = ValuationSynthesis(
        methods=[
            ValuationMethod(
                name="dcf",
                low=121.10,
                mid=151.38,
                high=181.66,
                confidence=0.85,
                source="implied_price ± 20%",
            )
        ],
        current_price=124.42,
        confidence="medium",
        weighted_price=None,
        upside_downside=0.216,
        target_low=113.54,
        target_high=189.23,
    )
    canonical = CanonicalThesis(
        verdict="HOLD",
        target=151.38,
        basis=basis,
        upside=0.216,
        valuation_withheld=False,
        confidence="medium",
    )

    out = apply_canonical_override(thesis, canonical, vs)

    assert out.price_target_basis == basis
    assert "$121.10" in out.price_target_basis
    assert "$181.66" in out.price_target_basis


def test_drift_scanned_across_tagline_and_takeaways() -> None:
    thesis = _thesis(
        tagline="AAPL · fair value ~$280, room to run",
        key_takeaways=[
            "Services margin expansion intact",
            "Our $280 target implies single-digit upside",
        ],
    )

    out, drift = _reconcile_narrative_targets(thesis, canonical_target=276.43, allowed_mids=[])

    assert drift is True
    assert out.tagline is not None and "$280" not in out.tagline
    assert "$276.43" in out.tagline
    assert out.key_takeaways is not None
    assert all("$280" not in tk for tk in out.key_takeaways)
    assert any("$276.43" in tk for tk in out.key_takeaways)


def test_four_digit_target_amount_not_truncated_and_doubled() -> None:
    """BUG (MU 2026-06-07): ``_DOLLAR_RE`` truncated a bare 4+ digit $-amount to
    its first 3 digits — ``$2172.06`` matched only ``$217`` — so the reconciler
    saw ``217 != 2172.06`` = drift and rewrote ``$217`` → ``$2172.06``, leaving
    the orphan ``2.06`` tail → ``$2172.062.06`` (the exact garbage in the shipped
    basis string). A $-amount equal to the canonical target must round-trip
    untouched regardless of magnitude — no comma, four+ digits, and all.
    """
    overview = "Our comps target of $2172.06 reflects peer forward multiples."
    thesis = _thesis(price_target=2172.06, valuation_overview=overview)

    out, drift = _reconcile_narrative_targets(
        thesis, canonical_target=2172.06, allowed_mids=[2172.06], current_price=864.01
    )

    assert drift is False
    assert out.valuation_overview == overview
    assert "$2172.062.06" not in (out.valuation_overview or "")


def test_four_digit_drift_amount_neutralized_to_full_token() -> None:
    """A contradicting bare 4-digit prose amount is rewritten to the WHOLE
    canonical token, never a truncated fragment: ``$5000`` → ``$2172.06`` (and
    never ``$2172.060`` from a partial ``$500`` match)."""
    overview = "We peg fair value near $5000, well above current levels."
    thesis = _thesis(price_target=2172.06, valuation_overview=overview)

    out, drift = _reconcile_narrative_targets(thesis, canonical_target=2172.06, allowed_mids=[])

    assert drift is True
    assert "$5000" not in (out.valuation_overview or "")
    assert "$2172.06" in (out.valuation_overview or "")
    # No orphaned digit tail from a truncated match.
    assert "$2172.060" not in (out.valuation_overview or "")


def test_comma_grouped_thousands_amount_still_matches() -> None:
    """The fix (require ≥1 comma group in the separated alternative) must NOT
    regress the comma path: ``$2,172.06`` stays whitelisted as the canonical
    target and is left untouched."""
    overview = "The weighted target of $2,172.06 anchors our view."
    thesis = _thesis(price_target=2172.06, valuation_overview=overview)

    out, drift = _reconcile_narrative_targets(thesis, canonical_target=2172.06, allowed_mids=[])

    assert drift is False
    assert out.valuation_overview == overview


def test_drift_scanned_across_all_narrative_fields() -> None:
    # BUG-087 ③: the guard previously only scanned valuation_overview / tagline /
    # key_takeaways — an injected fake $ in company_overview / competitor_analysis
    # / news_summary / narrative survived into the artifact. Now all are scanned.
    thesis = _thesis(
        narrative="Bottom line, we peg fair value at $280.",
        company_overview="Apple's segments support a $280 valuation.",
        competitor_analysis="Versus peers, AAPL warrants $280.",
        news_summary="Headlines hint the Street sees $280.",
    )

    out, drift = _reconcile_narrative_targets(thesis, canonical_target=276.43, allowed_mids=[])

    assert drift is True
    for field in ("narrative", "company_overview", "competitor_analysis", "news_summary"):
        value = getattr(out, field)
        assert value is not None
        assert "$280" not in value, f"{field} still contains the injected $280"
        assert "$276.43" in value, f"{field} was not neutralized to canonical"


def test_published_value_band_bounds_survive_withheld_path_scrub() -> None:
    """撤点≠撤区间: the published value-band bounds (target_low/high — e.g. a bank's
    residual-income band [RI@trailing, RI@forward]) appear in the DETERMINISTIC
    canonical basis but are NOT per-method mids. On the withheld path the narrative
    scrubber must NOT erase them to "[target withheld]" — they are published values
    the basis is meant to show.

    Regression for the JPM bug: a withheld-point bank report shipped
    ``price_target_basis`` reading "... value band [[target withheld], [target
    withheld]]" while structured ``valuation_synthesis`` still carried the real
    [$263.24, $356.15] band, because ``allowed_mids`` was built from method mids
    only and the scrubber ate the band the basis publishes.
    """
    methods = [
        ValuationMethod(
            name="comps_pb", low=250, mid=266.96, high=285, confidence=0.6, source="PB"
        ),
        ValuationMethod(
            name="comps_pe", low=255, mid=269.79, high=288, confidence=0.8, source="PE"
        ),
        ValuationMethod(
            name="residual_income", low=263.24, mid=300.04, high=356.15, confidence=0.7, source="RI"
        ),
    ]
    vs = ValuationSynthesis(
        methods=methods,
        weighted_price=None,
        current_price=334.14,
        upside_downside=None,
        confidence="high",
        target_low=263.24,
        target_high=356.15,
        anchor_method="residual_income",
        valuation_withheld=True,
    )
    # The deterministic canonical basis the bank RI-band path emits (the bounds are
    # NOT method mids: $263.24 is 1.4% off comps_pb $266.96, $356.15 is 18.7% off
    # the nearest mid $300.04 — both fail the per-mid whitelist before the fix).
    basis = (
        "FAIRLY VALUED: price $334.14 sits within the residual-income fair-value band "
        "[$263.24, $356.15] (RI at trailing ROE → at FY1 consensus ROE), so there is no "
        "margin of safety either way — verdict HOLD. Methods: comps_pb=$266.96, "
        "comps_pe=$269.79, residual_income=$300.04."
    )
    canonical = CanonicalThesis(
        target=None,
        verdict="HOLD",
        basis=basis,
        upside=None,
        valuation_withheld=True,
        confidence="high",
    )
    thesis = _thesis(recommendation="HOLD", price_target=None, price_target_basis="(LLM draft)")

    out = apply_canonical_override(thesis, canonical, vs)

    assert out.price_target_basis is not None
    assert "[target withheld]" not in out.price_target_basis, (
        "published value-band bounds were washed to the withheld marker — 撤点≠撤区间 reverted"
    )
    assert "$263.24" in out.price_target_basis
    assert "$356.15" in out.price_target_basis


def test_withheld_path_keeps_a_zero_amount() -> None:
    """A ``$0`` amount is a datum, not a smuggled target — and erasing it forges a finding.

    GMED 2026-10-14: the withheld-point scrubber erased the ``$0`` in "with $0 of
    open-market purchases", so the thesis AND the summary read "[target withheld] of
    open-market purchases". That wrecked the prose and, worse, handed the insider-flow
    verifier a clause whose only remaining amount was the net flow: it then reported
    "the narrative states $4,413,467.00 as the 90-day insider purchases figure; the
    computed value is $0" — a false finding on a sentence that was correct before the
    scrubber touched it. One corrupted token, two published defects.
    """
    sentence = (
        "Conviction is capped by evidence quality, not by the thesis: 90-day insider net "
        "flow of -$4,413,467 with $0 of open-market purchases, and only 2.0% "
        "institutional coverage on file."
    )
    methods = [
        ValuationMethod(
            name="dcf",
            low=174.49,
            mid=218.12,
            high=261.74,
            confidence=0.85,
            source="implied_price ± 20%",
        )
    ]
    vs = ValuationSynthesis(
        methods=methods,
        weighted_price=None,
        current_price=76.32,
        upside_downside=None,
        confidence="very_low",
        target_low=163.59,
        target_high=272.64,
        anchor_method=None,
        valuation_withheld=True,
    )
    canonical = CanonicalThesis(
        target=None,
        verdict="BUY",
        basis="POINT TARGET WITHHELD (confidence=very_low)",
        upside=None,
        valuation_withheld=True,
        confidence="very_low",
    )
    thesis = _thesis(
        recommendation="BUY",
        price_target=None,
        price_target_basis="(LLM draft)",
        key_takeaways=[sentence],
    )

    out = apply_canonical_override(thesis, canonical, vs)

    text = (out.key_takeaways or [""])[0]
    assert "$0" in text, "a zero amount was washed to the withheld marker"
    assert "[target withheld]" not in text
    # The surviving clause no longer accuses the narrative of a purchases figure it
    # never claimed (ownership leaves as the GMED run had them).
    ownership = {
        "insider_net_flow": -4413467.0,
        "insider_buy_value": 0.0,
        "insider_sell_value": 4413467.0,
        "insider_window_days": 90,
        "insider_largest_sale": {"value": 2237502.0},
    }
    assert insider_flow_amount_findings([text], ownership) == []


def _thc_withheld_vs() -> ValuationSynthesis:
    """The THC 2026-10-14 shape: one far-from-market DCF, point withheld."""
    return ValuationSynthesis(
        methods=[
            ValuationMethod(
                name="dcf",
                low=585.66,
                mid=732.07,
                high=878.49,
                confidence=0.85,
                source="implied_price ± 20%",
            )
        ],
        current_price=266.91,
        confidence="very_low",
        weighted_price=None,
        upside_downside=None,
        target_low=549.05,
        target_high=915.09,
        valuation_withheld=True,
        degradation_note="single method dcf $732 is 2.7x the market price",
    )


def _thc_withheld_canonical() -> CanonicalThesis:
    return CanonicalThesis(
        verdict="HOLD",
        target=None,
        basis="DIRECTION WITHHELD — the lone DCF $732.07 …",
        upside=None,
        valuation_withheld=True,
        confidence="very_low",
    )


def test_published_data_figures_survive_the_withheld_scrub() -> None:
    """A withheld POINT must not censor the report's own published data.

    THC 2026-10-14 (owner audit): the withheld-path scrubber erased the insider
    flow figures from the narrative — "insiders were net sellers of [target
    withheld] … with [target withheld] of open-market purchases, anchored by a
    [target withheld] sale by CEO Saumya Sutaria" — while the risk bullets on the
    same report quoted $49,991,274 and $10,223,358 for exactly those figures. The
    marker is for a smuggled POINT TARGET, not for data the artifact publishes.
    """
    thesis = _thesis(
        narrative=(
            "Insiders were net sellers of $49,991,274 over 90 days with $0 of "
            "open-market purchases, anchored by a $10,223,358 sale by CEO Saumya Sutaria."
        )
    )

    out = apply_canonical_override(
        thesis,
        _thc_withheld_canonical(),
        _thc_withheld_vs(),
        published_amounts=[49_991_273.96, 0.0, 49_991_273.96, 10_223_358.4],
    )

    narrative = out.narrative or ""
    assert "[target withheld]" not in narrative
    assert "$49,991,274" in narrative
    assert "$10,223,358" in narrative


def test_a_smuggled_point_target_is_still_erased_alongside_data_figures() -> None:
    """Whitelisting published data must not open the door for a fabricated point."""
    thesis = _thesis(valuation_overview="Our fair value is $742.11 per share, well above the tape.")

    out = apply_canonical_override(
        thesis,
        _thc_withheld_canonical(),
        _thc_withheld_vs(),
        published_amounts=[49_991_273.96],
    )

    overview = out.valuation_overview or ""
    assert "$742.11" not in overview
    assert "[target withheld]" in overview


# --------------------------------------------------------------------------------------
# Declared leaf kinds (identities.LEAF_KINDS) — the CF 2026-10-14 audit
# --------------------------------------------------------------------------------------


def _snapshot_raw(
    *,
    enterprise_value: float | None = 15_783_943_454.0,
    total_debt: float = 3_100_000_000.0,
    total_cash: float = 1_900_000_000.0,
    market_cap: float = 21_000_000_000.0,
    shares_outstanding: float = 175_000_000.0,
    current_price: float = 119.46,
) -> dict[str, Any]:
    """The run's own ``FinancialData`` snapshot in the artifact ``raw_data`` shape.

    Built through the production reader (``_published_leaf_snapshot`` →
    ``FinancialData.model_dump(mode="json")``) so the test asserts the shape the
    scrubber actually receives: the paths ``identities.LEAF_KINDS`` keys.
    """
    fd = FinancialData(
        ticker="CF",
        company_name="CF Industries Holdings, Inc.",
        timestamp=datetime(2026, 10, 14, tzinfo=timezone.utc),
        income=IncomeStatement(revenue=6_133_000_000.0),
        balance=BalanceSheet(total_debt=total_debt, total_cash=total_cash),
        market=MarketData(
            market_cap=market_cap,
            shares_outstanding=shares_outstanding,
            current_price=current_price,
        ),
        valuation=ValuationMetrics(enterprise_value=enterprise_value, ev_ebitda=7.2),
    )
    raw = _published_leaf_snapshot({"data_collection": fd})
    assert raw is not None  # a real FinancialData snapshot always dumps
    return raw


def test_published_total_leaf_is_left_exactly_as_written() -> None:
    """CF 2026-10-14: prose restating the run's OWN published total is not drift.

    The audited report printed "46.8% of the $80.69 enterprise value" because the
    scrubber recognised an amount only by MAGNITUDE, so the prose's own
    $15,783,943,454 enterprise value was rewritten to the canonical per-share target
    while the same artifact's risk bullets still printed the real EV — a TOTAL
    restated as a PER-SHARE figure. ``valuation.enterprise_value`` is declared a
    ``total_amount`` leaf, so the amount is recognised as a restatement of that
    published number and the sentence survives byte for byte.
    """
    raw = _snapshot_raw()
    # The shape claim the whole change rests on: the snapshot's own path IS the
    # declared leaf path, read through identities.LEAF_KINDS.
    assert leaves_of_kind(raw, "total_amount")["valuation.enterprise_value"] == 15_783_943_454.0
    overview = (
        "The DCF lands at $75.85, with 46.8% of the $15,783,943,454 enterprise value "
        "arriving in the terminal period."
    )
    thesis = _thesis(price_target=80.69, valuation_overview=overview)

    out, drift = _reconcile_narrative_targets(
        thesis,
        canonical_target=80.69,
        allowed_mids=[75.85, 86.40],
        current_price=119.46,
        published_raw=raw,
    )

    assert drift is False
    assert out.valuation_overview == overview
    assert "$15,783,943,454" in (out.valuation_overview or "")


def test_published_total_leaf_survives_the_override_call_site() -> None:
    """The same sentence survives the real entry point: ``apply_canonical_override``
    fed the run's snapshot via ``_published_leaf_snapshot(structured_context)`` (the
    ``data_collection`` key ``_execute_thesis`` reads)."""
    raw = _snapshot_raw()
    overview = (
        "46.8% of the $15,783,943,454 enterprise value arrives in the terminal period, "
        "so the DCF's $75.85 is terminal-heavy."
    )
    thesis = _thesis(price_target=80.69, valuation_overview=overview)
    vs = ValuationSynthesis(
        methods=[
            ValuationMethod(
                name="dcf", low=75.85, mid=75.85, high=75.85, confidence=0.5, source="DCF"
            ),
            ValuationMethod(
                name="comps", low=86.40, mid=86.40, high=86.40, confidence=0.5, source="comps"
            ),
        ],
        current_price=119.46,
        confidence="medium",
        weighted_price=80.69,
        upside_downside=-0.32,
        valuation_withheld=False,
    )
    canonical = CanonicalThesis(
        verdict="HOLD",
        target=80.69,
        basis="Blend of 2 methods: DCF $75.85, comps $86.40 → $80.69.",
        upside=-0.32,
        valuation_withheld=False,
        confidence="medium",
    )

    out = apply_canonical_override(thesis, canonical, vs, published_raw=raw)

    assert out.valuation_overview == overview
    assert "$15,783,943,454" in (out.valuation_overview or "")


def test_per_share_drift_is_still_rewritten_with_leaves_declared() -> None:
    """Declaring the leaves must not blunt the guard: a drifting per-share claim
    matches no published non-per-share leaf and no allowed mid, so it is still
    neutralized to the canonical target."""
    raw = _snapshot_raw()
    thesis = _thesis(
        price_target=80.69,
        valuation_overview="Fair value of $280 on trough multiples.",
    )

    out, drift = _reconcile_narrative_targets(
        thesis,
        canonical_target=80.69,
        allowed_mids=[75.85],
        current_price=119.46,
        published_raw=raw,
    )

    assert drift is True
    assert out.valuation_overview == "Fair value of $80.69 on trough multiples."


def test_undeclared_amount_still_falls_back_to_the_magnitude_rule() -> None:
    """The magnitude heuristic is the FALLBACK for an amount no declaration covers.

    $20,000 / $4,500 match no declared leaf of this snapshot, so the old rule still
    applies — orders of magnitude above every per-share reference — and the totals
    survive even with a full declaration on hand.
    """
    raw = _snapshot_raw(enterprise_value=None, current_price=1.05)
    narrative = "Total debt of $20,000 and $4,500 of cash leave the equity thin."
    thesis = _thesis(price_target=1.2, narrative=narrative)

    out, drift = _reconcile_narrative_targets(
        thesis,
        canonical_target=1.2,
        allowed_mids=[],
        current_price=1.05,
        published_raw=raw,
    )

    assert drift is False
    assert out.narrative == narrative


def test_declared_total_survives_the_withheld_scrub_without_the_heuristic() -> None:
    """The strictly load-bearing case for the kind lookup.

    On the withheld path with no synthesis there is no canonical target and no market
    price, so the magnitude heuristic has nothing to compare against (its
    $1,000,000 floor is all that is left) — a published total BELOW that floor used to
    be erased to "[target withheld]", contradicting the risk bullets that only the
    reconcile's scan covers. The run declares it a ``total_amount`` leaf, so the amount
    is recognised as its own published number and kept.
    """
    raw = _snapshot_raw(
        enterprise_value=None,
        total_debt=850_000.0,
        total_cash=120_000.0,
        market_cap=900_000.0,
        shares_outstanding=1_000_000.0,
        current_price=1.05,
    )
    narrative = "Total debt of $850,000 against $120,000 of cash leaves little room."
    thesis = _thesis(price_target=None, narrative=narrative)

    out = apply_canonical_override(thesis, _thc_withheld_canonical(), vs=None, published_raw=raw)

    assert "[target withheld]" not in (out.narrative or "")
    assert "$850,000" in (out.narrative or "")
    assert "$120,000" in (out.narrative or "")
