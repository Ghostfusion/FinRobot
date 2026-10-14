"""Output-contract total gate (ArtifactContract) — persist-boundary invariants.

The contract runs at the single auto-persist boundary (runner.py, between the
builder output and the store.save). It asserts whole-artifact invariants the
upstream point gates structurally cannot — they each see one object (a
ValuationSynthesis, a FinancialData snapshot, one prose field), never the
assembled artifact's headline/basis/narrative together. MVP clauses:

  C1  headline upside band  — target/entry must sit in the calibrated band
      (single-method [0.5x, 2x], multi-method [0.25x, 4x]). Catches the MU
      $2172 = 2.5x-$864 accident (lone comps_pe on a memory cyclical's peak EPS)
      regardless of how the upstream gate mis-calibrated.
  C2  double-decimal malformation — a $-anchored amount with two decimal points
      ($2172.062.06) is a concatenation artifact; withhold (can't auto-repair).

The tests assert the GATE CAUGHT IT (withhold + REVIEW + evidence), not that the
number is "right" — the contract definition is itself the oracle. Accident
specimens ($2172/$864, $2172.062.06) are the documented bug numbers from
valuation_synthesis.py:77-79 and the narrative-reconcile regression, not live
quotes.
"""

from __future__ import annotations

import copy
from datetime import datetime, timezone

import pytest

from finrobot.artifact.contract import CONTRACT_CLAUSES, enforce_artifact_contract
from finrobot.artifact.models import (
    Artifact,
    ArtifactAssumptions,
    ArtifactComputeVersion,
    ArtifactInputs,
    ArtifactMeta,
    ArtifactOutputs,
)
from finrobot.artifact.summary_extractor import extract_target_price

UTC = timezone.utc
CREATED = datetime(2026, 6, 8, tzinfo=UTC)


def _artifact(
    *,
    raw_data: dict | None = None,
    structured: dict | None = None,
    llm_narrative: dict | None = None,
    summary_text: str = "head",
    warnings: list[str] | None = None,
    type_: str = "equity_research",
) -> Artifact:
    return Artifact(
        id="art_2026-06-08T00:00:00_MU_equity_research",
        ticker="MU",
        cross_tickers=[],
        type=type_,  # type: ignore[arg-type]
        inputs=ArtifactInputs(
            data_source="yfinance",
            data_fetched_at=CREATED,
            raw_data=raw_data or {},
        ),
        assumptions=ArtifactAssumptions(parameters={}),
        compute_version=ArtifactComputeVersion(version="0.1.0", formula_id="x"),
        outputs=ArtifactOutputs(
            structured=structured or {},
            llm_narrative=llm_narrative or {},
            summary_text=summary_text,
            warnings=list(warnings or []),
        ),
        meta=ArtifactMeta(created_at=CREATED, source="pipeline:equity_research"),
    )


def _warnings(art: Artifact) -> list[str]:
    return art.outputs.warnings


# ── Step 0: skeleton no-op ───────────────────────────────────────────────────


def test_clean_artifact_passes_through_unchanged() -> None:
    """A compliant artifact (in-band target, no malformed amounts) must come out
    byte-for-byte identical — the contract only ever degrades on a real
    violation, never touches a healthy artifact."""
    art = _artifact(
        raw_data={"market": {"current_price": 100.0}},
        structured={
            "thesis": {"price_target": 130.0, "recommendation": "BUY"},
            "valuation_synthesis": {"weighted_price": 128.0},
        },
        llm_narrative={"recommendation": "BUY", "tagline": "fairly valued"},
    )
    before = art.model_dump()
    out = enforce_artifact_contract(art)
    assert out.model_dump() == before


def test_registry_is_a_list_of_clauses() -> None:
    assert isinstance(CONTRACT_CLAUSES, list)
    assert CONTRACT_CLAUSES, "MVP ships C1 + C2"
    assert {c.id for c in CONTRACT_CLAUSES} >= {"C1", "C2"}


# ── C1: headline upside band ─────────────────────────────────────────────────


def _mu_2172_artifact() -> Artifact:
    """The MU accident: lone comps_pe → $2172 target = 2.5x the $864 market,
    shipped as a confident +151% BUY. Single method (weighted_price None)."""
    return _artifact(
        raw_data={"market": {"current_price": 864.0}},
        structured={
            "thesis": {
                "price_target": 2172.0,
                "recommendation": "BUY",
                "price_target_basis": "comps_pe 36.9x → $2172",
            },
            "valuation_synthesis": {"weighted_price": None, "methods": ["comps_pe"]},
        },
        llm_narrative={
            "recommendation": "BUY",
            "tagline": "memory super-cycle, +151% upside",
            "company_overview": "Micron is a memory maker.",
        },
    )


def test_c1_withholds_single_method_target_out_of_band() -> None:
    art = enforce_artifact_contract(_mu_2172_artifact())
    structured = art.outputs.structured
    assert structured["thesis"]["price_target"] is None
    # Value-withhold, NOT a refuse-to-rate: the directional verdict is preserved.
    assert structured["thesis"]["recommendation"] == "BUY"
    assert structured["valuation_withheld"] is True
    assert structured["withheld_reason"] == "contract_C1"
    assert extract_target_price(art) is None  # C7 invariant: truly gone
    assert any(w.startswith("[CONTRACT/C1]") for w in _warnings(art))


def test_c1_neutralises_narrative_conclusion_keeps_body() -> None:
    """Withhold neutralises the point-target conclusion (tagline) but PRESERVES
    the directional verdict + the analysis body verbatim + stamps provenance."""
    art = enforce_artifact_contract(_mu_2172_artifact())
    narrative = art.outputs.llm_narrative
    assert narrative["recommendation"] == "BUY"  # verdict preserved, never REVIEW
    assert narrative["tagline"] is None
    assert narrative["company_overview"] == "Micron is a memory maker."  # body untouched
    assert any(w.startswith("[CONTRACT/withheld]") for w in _warnings(art))


def test_c1_passes_target_inside_single_method_band() -> None:
    art = _artifact(
        raw_data={"market": {"current_price": 100.0}},
        structured={
            # 1.8x < 2x; single-method basis discloses no cross-check so C6 is
            # silent and this stays a clean C1-only pass-through.
            "thesis": {
                "price_target": 180.0,
                "recommendation": "BUY",
                "price_target_basis": "comps_pe — single-method, no cross-check available",
            },
            "valuation_synthesis": {"weighted_price": None},
        },
    )
    before = art.model_dump()
    out = enforce_artifact_contract(art)
    assert out.model_dump() == before


def test_c1_multi_method_band_is_wider_than_single() -> None:
    """A 3x target survives the multi-method [0.25x, 4x] band (weighted_price
    present = corroborated) but would trip the single-method [0.5x, 2x] band."""
    art = _artifact(
        raw_data={"market": {"current_price": 100.0}},
        structured={
            "thesis": {"price_target": 300.0, "recommendation": "BUY"},  # 3x
            "valuation_synthesis": {"weighted_price": 295.0},  # corroborated
        },
    )
    out = enforce_artifact_contract(art)
    assert out.outputs.structured["thesis"]["price_target"] == 300.0  # survives
    assert "valuation_withheld" not in out.outputs.structured


def test_c1_noop_when_type_has_no_per_share_headline() -> None:
    """comps / lbo carry no per-share target (extract_target_price -> None), so
    C1 is structurally a no-op — never a spurious withhold."""
    art = _artifact(
        raw_data={"market": {"current_price": 100.0}},
        structured={"median_pe": 18.5},  # PeerComps shape, no headline
        type_="comps",
    )
    before = art.model_dump()
    out = enforce_artifact_contract(art)
    assert out.model_dump() == before


def test_c1_withholds_plain_dcf_flat_headline() -> None:
    """A plain DCF dumps implied_price FLAT (no thesis). An out-of-band flat
    headline must still be withheld so it can't resurrect via extract_target_price."""
    art = _artifact(
        raw_data={"market": {"current_price": 100.0}},
        structured={"implied_price": 350.0},  # 3.5x, single method, no synthesis block
        type_="dcf",
    )
    out = enforce_artifact_contract(art)
    assert out.outputs.structured["implied_price"] is None
    assert out.outputs.structured["valuation_withheld"] is True
    assert extract_target_price(out) is None


# ── C2: double-decimal malformation ──────────────────────────────────────────


def test_c2_catches_double_decimal_in_thesis_prose() -> None:
    art = _artifact(
        raw_data={"market": {"current_price": 100.0}},
        structured={
            "thesis": {
                "price_target": 130.0,
                "recommendation": "BUY",
                "price_target_basis": "DCF implies $2172.062.06 per share",
            },
            "valuation_synthesis": {"weighted_price": 128.0},
        },
    )
    out = enforce_artifact_contract(art)
    assert out.outputs.structured["valuation_withheld"] is True
    assert out.outputs.structured["withheld_reason"] == "contract_C2"
    assert any(w.startswith("[CONTRACT/C2]") for w in _warnings(out))
    assert "$2172.062.06" in " ".join(_warnings(out))


def test_c2_catches_double_decimal_inside_llm_narrative_dict() -> None:
    """⟦复核⟧ llm_narrative is a dict, not a str — C2 must traverse its values."""
    art = _artifact(
        raw_data={"market": {"current_price": 100.0}},
        structured={
            "thesis": {"price_target": 130.0, "recommendation": "BUY"},
            "valuation_synthesis": {"weighted_price": 128.0},
        },
        llm_narrative={"valuation_overview": "Fair value $1,234.562.06 on our DCF."},
    )
    out = enforce_artifact_contract(art)
    assert out.outputs.structured["valuation_withheld"] is True
    assert any(w.startswith("[CONTRACT/C2]") for w in _warnings(out))


def test_c2_ignores_legal_three_decimal_numbers() -> None:
    """The corrected $-anchored double-point regex must NOT fire on the most
    common legal financial decimals: beta 1.085, R² 0.987, FX 7.234, a fractional
    strike $1.875, a percentage 0.025. (The naive \\d\\.\\d{2}\\d regex mauled
    all of these — see spec C2 ⟦复核⟧.)"""
    prose = (
        "beta 1.085, R² 0.987, USDTWD 7.234, strike $1.875, 0.025 of revenue, "
        "fair value $1,234.56 today"
    )
    art = _artifact(
        raw_data={"market": {"current_price": 100.0}},
        structured={
            "thesis": {
                "price_target": 130.0,
                "recommendation": "BUY",
                "price_target_basis": prose,
            },
            "valuation_synthesis": {"weighted_price": 128.0},
        },
        llm_narrative={"valuation_overview": prose},
        summary_text=prose,
    )
    before = art.model_dump()
    out = enforce_artifact_contract(art)
    assert out.model_dump() == before  # nothing tripped


def test_enforce_is_idempotent_on_a_withheld_artifact() -> None:
    """Running the contract twice must not double-stamp or change the verdict —
    a withheld artifact re-enforced stays withheld with no extra mutation beyond
    the already-appended warnings. The withheld-target signal (verdict directional,
    price_target None) is stable, so the second run re-detects it (via C7) without
    mutating anything further."""
    once = enforce_artifact_contract(_mu_2172_artifact())
    snapshot = copy.deepcopy(once.model_dump())
    twice = enforce_artifact_contract(once)
    # target stays None, verdict stays directional (BUY); warnings carry the evidence.
    assert twice.outputs.structured["thesis"]["price_target"] is None
    assert twice.outputs.structured["thesis"]["recommendation"] == "BUY"
    assert twice.model_dump()["outputs"]["structured"] == snapshot["outputs"]["structured"]


# ── Step 2 oracle: C1 band 3-point boundary tests ────────────────────────────


def _single_method_target_artifact(target: float, *, entry: float = 100.0) -> Artifact:
    return _artifact(
        raw_data={"market": {"current_price": entry}},
        structured={
            "thesis": {"price_target": target, "recommendation": "BUY"},
            "valuation_synthesis": {"weighted_price": None},  # single method
        },
    )


def _multi_method_target_artifact(target: float, *, entry: float = 100.0) -> Artifact:
    return _artifact(
        raw_data={"market": {"current_price": entry}},
        structured={
            "thesis": {"price_target": target, "recommendation": "BUY"},
            "valuation_synthesis": {"weighted_price": target - 1.0},  # corroborated
        },
    )


def test_c1_single_method_just_under_2x_passes() -> None:
    """1.99x sits inside the single-method [0.5x, 2x] band → survives."""
    out = enforce_artifact_contract(_single_method_target_artifact(199.0))
    assert out.outputs.structured["thesis"]["price_target"] == 199.0
    assert "valuation_withheld" not in out.outputs.structured


def test_c1_single_method_exactly_2x_passes() -> None:
    """The 2.0x boundary is INCLUSIVE (lo <= ratio <= hi) → survives."""
    out = enforce_artifact_contract(_single_method_target_artifact(200.0))
    assert out.outputs.structured["thesis"]["price_target"] == 200.0
    assert "valuation_withheld" not in out.outputs.structured


def test_c1_single_method_just_over_2x_trips() -> None:
    """2.01x is outside the single-method band → withheld."""
    out = enforce_artifact_contract(_single_method_target_artifact(201.0))
    assert out.outputs.structured["thesis"]["price_target"] is None
    assert out.outputs.structured["valuation_withheld"] is True
    assert any(w.startswith("[CONTRACT/C1]") for w in _warnings(out))


def test_c1_multi_method_exactly_4x_passes_just_over_trips() -> None:
    """Multi-method band boundary: 4.0x inclusive passes, 4.01x trips."""
    on_edge = enforce_artifact_contract(_multi_method_target_artifact(400.0))
    assert on_edge.outputs.structured["thesis"]["price_target"] == 400.0
    over = enforce_artifact_contract(_multi_method_target_artifact(401.0))
    assert over.outputs.structured["thesis"]["price_target"] is None
    assert over.outputs.structured["valuation_withheld"] is True


# ── Step 2 oracle: C2 regex fuzz table ───────────────────────────────────────

_C2_LEGAL = ["1.085", "0.987", "$1.875", "7.234", "$1,234.56"]
_C2_MALFORMED = ["$2172.062.06", "$1,234.562.06", "$50.001.2"]


@pytest.mark.parametrize("amount", _C2_LEGAL)
def test_c2_fuzz_legal_amounts_never_caught(amount: str) -> None:
    art = _artifact(
        raw_data={"market": {"current_price": 100.0}},
        structured={
            "thesis": {
                "price_target": 130.0,
                "recommendation": "BUY",
                "price_target_basis": f"value is {amount} here",
            },
            "valuation_synthesis": {"weighted_price": 128.0},
        },
    )
    before = art.model_dump()
    out = enforce_artifact_contract(art)
    assert out.model_dump() == before  # legal amount, nothing tripped


@pytest.mark.parametrize("amount", _C2_MALFORMED)
def test_c2_fuzz_malformed_amounts_all_caught(amount: str) -> None:
    art = _artifact(
        raw_data={"market": {"current_price": 100.0}},
        structured={
            "thesis": {
                "price_target": 130.0,
                "recommendation": "BUY",
                "price_target_basis": f"DCF implies {amount} per share",
            },
            "valuation_synthesis": {"weighted_price": 128.0},
        },
    )
    out = enforce_artifact_contract(art)
    assert out.outputs.structured["valuation_withheld"] is True
    assert any(w.startswith("[CONTRACT/C2]") for w in _warnings(out))


# ── C7: withheld must not resurrect ──────────────────────────────────────────


def test_c7_nulls_resurrected_financial_modeling_implied_price_on_withheld_target() -> None:
    """The real bug, verdict now preserved: a SELL thesis whose own price_target is
    withheld (None) yet financial_modeling.implied_price=20.35 rides naked in
    structured. C7 scans the RAW slot, nulls it, fires [CONTRACT/C7]. The withheld
    signal is (directional verdict + price_target None), not the deleted REVIEW."""
    art = _artifact(
        raw_data={"market": {"current_price": 18.0}},
        structured={
            "thesis": {"price_target": None, "recommendation": "SELL"},
            "financial_modeling": {"implied_price": 20.35},
        },
    )
    out = enforce_artifact_contract(art)
    assert out.outputs.structured["financial_modeling"]["implied_price"] is None
    assert out.outputs.structured["valuation_withheld"] is True
    assert out.outputs.structured["withheld_reason"] == "contract_C7"
    # The directional verdict is preserved un-scrubbed.
    assert out.outputs.structured["thesis"]["recommendation"] == "SELL"
    assert any(w.startswith("[CONTRACT/C7/internal]") for w in _warnings(out))


def test_c7_evidence_is_internal_tag_not_surfaced_to_analyst() -> None:
    """C7 is an INTERNAL scrub invariant — its evidence is engineering plumbing
    ("nulling so it cannot resurrect downstream" + a raw float), not a withhold
    REASON. It must NOT surface to the analyst UI: the report parser renders only
    `[CONTRACT/Cn] …` (tag immediately closed), so C7 emits the non-surfacing
    `[CONTRACT/C7/internal] …`. Regression lock for the MU leak where C7's plumbing
    showed as the cover withhold reason + the top audit banner."""
    art = _artifact(
        raw_data={"market": {"current_price": 18.0}},
        structured={
            "thesis": {"price_target": None, "recommendation": "HOLD"},
            "financial_modeling": {"implied_price": 188.12},
        },
    )
    warnings = _warnings(enforce_artifact_contract(art))
    # Recorded for the audit trail under the non-surfacing /internal sub-tag …
    assert any(w.startswith("[CONTRACT/C7/internal] ") for w in warnings)
    # … and NEVER under the analyst-facing surfaced format the report UI parses
    # (`[CONTRACT/C7] …` with the tag closed immediately after the clause id).
    assert not any(w.startswith("[CONTRACT/C7] ") for w in warnings)


def test_c7_judges_withheld_via_directional_verdict_with_null_target() -> None:
    """The withheld signal is a directional verdict (BUY/HOLD/SELL) with
    price_target None — NOT a pre-set valuation_withheld. C7 must still fire and
    must NOT touch the verdict."""
    art = _artifact(
        raw_data={"market": {"current_price": 18.0}},
        structured={
            "thesis": {"price_target": None, "recommendation": "HOLD"},
            "dcf_result": {"implied_price": 99.0},
        },
    )
    out = enforce_artifact_contract(art)
    assert out.outputs.structured["dcf_result"]["implied_price"] is None
    assert out.outputs.structured["thesis"]["recommendation"] == "HOLD"
    assert any(w.startswith("[CONTRACT/C7/internal]") for w in _warnings(out))


def test_c7_still_judges_legacy_review_recommendation() -> None:
    """Back-compat: an OLD stored artifact may carry recommendation=='REVIEW' (the
    deleted verdict). C7 must still treat it as withheld so legacy fallback slots
    are scrubbed. The contract never WRITES 'REVIEW' — it only reads it here."""
    art = _artifact(
        raw_data={"market": {"current_price": 18.0}},
        structured={
            "thesis": {"price_target": None, "recommendation": "REVIEW"},
            "financial_modeling": {"implied_price": 20.35},
        },
    )
    out = enforce_artifact_contract(art)
    assert out.outputs.structured["financial_modeling"]["implied_price"] is None
    assert any(w.startswith("[CONTRACT/C7/internal]") for w in _warnings(out))


def test_c7_noop_when_withheld_and_all_slots_already_null() -> None:
    """A clean withheld artifact (directional verdict, no target, no resurrected
    slots) must pass through unchanged — C7 only fires on a SURVIVING headline."""
    art = _artifact(
        raw_data={"market": {"current_price": 18.0}},
        structured={
            "thesis": {"price_target": None, "recommendation": "SELL"},
            "financial_modeling": {"implied_price": None},
        },
    )
    before = art.model_dump()
    out = enforce_artifact_contract(art)
    assert out.model_dump() == before


def test_c7_noop_on_a_buy_with_live_fallback_slots() -> None:
    """A compliant BUY (not REVIEW) keeps its financial_modeling.implied_price —
    C7 only governs WITHHELD artifacts; it must not null a healthy fallback."""
    art = _artifact(
        raw_data={"market": {"current_price": 100.0}},
        structured={
            "thesis": {"price_target": 130.0, "recommendation": "BUY"},
            "valuation_synthesis": {"weighted_price": 128.0},
            "financial_modeling": {"implied_price": 129.0},
        },
    )
    before = art.model_dump()
    out = enforce_artifact_contract(art)
    assert out.model_dump() == before


def test_c7_scrub_runs_on_every_hard_withhold() -> None:
    """The _withhold refactor: ANY hard withhold (here C2) must scrub the nested
    financial_modeling.implied_price too, so the C7 invariant holds for every hard
    clause — not just C7's own path."""
    art = _artifact(
        raw_data={"market": {"current_price": 100.0}},
        structured={
            "thesis": {
                "price_target": 130.0,
                "recommendation": "BUY",
                "price_target_basis": "DCF implies $2172.062.06 per share",  # trips C2
            },
            "valuation_synthesis": {"weighted_price": 128.0},
            "financial_modeling": {"implied_price": 129.0},
        },
    )
    out = enforce_artifact_contract(art)
    assert out.outputs.structured["financial_modeling"]["implied_price"] is None
    assert out.outputs.structured["thesis"]["price_target"] is None
    assert extract_target_price(out) is None


def test_withheld_sell_thesis_passes_contract_verdict_unscrubbed() -> None:
    """Item-7 invariant: a thesis that honestly withholds its POINT target
    (price_target None) while still shipping a directional SELL verdict — with NO
    resurrected fallback slots — passes the contract un-scrubbed of its verdict
    (no C7 mutation, recommendation stays SELL). The value-integrity guardrails
    only withhold the VALUE; they never refuse the judgment.

    The slate carries BOTH writers' slots since 2026-10-14: the run path writes one
    convention (root + synthesis), so a fixture that emits the root alone is itself
    a C11 violation — which is the point of that clause, not a false positive."""
    art = _artifact(
        raw_data={"market": {"current_price": 50.0}},
        structured={
            "thesis": {
                "price_target": None,
                "recommendation": "SELL",
                "price_target_basis": "single-method DCF, no cross-check available",
            },
            "valuation_withheld": True,
            "valuation_synthesis": {
                "weighted_price": None,
                "methods": [],
                "valuation_withheld": True,
            },
        },
        llm_narrative={"recommendation": "SELL", "company_overview": "body"},
    )
    out = enforce_artifact_contract(art)
    assert out.outputs.structured["thesis"]["recommendation"] == "SELL"  # verdict ships
    assert out.outputs.structured["thesis"]["price_target"] is None  # value honestly absent
    assert out.outputs.llm_narrative["recommendation"] == "SELL"  # mirror preserved
    # No fallback slot to resurrect, nothing tripped → no new [CONTRACT/*] warnings.
    assert not any(w.startswith("[CONTRACT/") for w in _warnings(out))


# ── C1b: method-vs-method corroboration span ─────────────────────────────────


def _method(name: str, mid: float) -> dict:
    return {"name": name, "low": mid * 0.9, "mid": mid, "high": mid * 1.1, "source": "x"}


def test_c1b_withholds_when_methods_span_above_corroboration_limit() -> None:
    """The MU 0.69x-of-market case C1 is blind to: the headline (130 vs 188 market =
    in-band) survives C1, but the surviving method mids are 7x apart ($30 vs $210)
    — no honest blended point exists, so C1b withholds the TARGET (verdict kept)."""
    art = _artifact(
        raw_data={"market": {"current_price": 188.0}},
        structured={
            "thesis": {"price_target": 130.0, "recommendation": "SELL"},
            "valuation_synthesis": {
                "weighted_price": 120.0,  # corroborated band → C1 passes
                "methods": [_method("dcf", 30.0), _method("comps_pe", 210.0)],  # 7x apart
            },
        },
        llm_narrative={"recommendation": "SELL"},
    )
    out = enforce_artifact_contract(art)
    assert out.outputs.structured["thesis"]["price_target"] is None
    assert out.outputs.structured["thesis"]["recommendation"] == "SELL"  # verdict kept
    assert out.outputs.structured["valuation_withheld"] is True
    assert "C1b" in out.outputs.structured["withheld_reason"]
    assert any(w.startswith("[CONTRACT/C1b]") for w in _warnings(out))


def test_c1b_passes_when_methods_corroborate_within_2x() -> None:
    """Methods within the 2x corroboration span (max/min = 1.5x) → C1b silent."""
    art = _artifact(
        raw_data={"market": {"current_price": 100.0}},
        structured={
            "thesis": {"price_target": 130.0, "recommendation": "BUY"},
            "valuation_synthesis": {
                "weighted_price": 128.0,
                "methods": [_method("dcf", 120.0), _method("comps_pe", 180.0)],  # 1.5x
            },
        },
    )
    before = art.model_dump()
    out = enforce_artifact_contract(art)
    assert out.model_dump() == before


def test_c1b_noop_on_single_method_or_bare_names() -> None:
    """C1b needs ≥2 numeric mids to measure a span: a single method, or method
    entries that are bare names (no mid), are a no-op (never a spurious withhold)."""
    single = _artifact(
        raw_data={"market": {"current_price": 100.0}},
        structured={
            "thesis": {
                "price_target": 150.0,
                "recommendation": "BUY",
                "price_target_basis": "comps_pe — single-method, no cross-check available",
            },
            "valuation_synthesis": {"weighted_price": None, "methods": [_method("dcf", 150.0)]},
        },
    )
    before_single = single.model_dump()
    assert enforce_artifact_contract(single).model_dump() == before_single

    bare = _artifact(
        raw_data={"market": {"current_price": 100.0}},
        structured={
            "thesis": {
                "price_target": 150.0,
                "recommendation": "BUY",
                "price_target_basis": "comps_pe — single-method, no cross-check available",
            },
            "valuation_synthesis": {"weighted_price": None, "methods": ["dcf", "comps_pe"]},
        },
    )
    before_bare = bare.model_dump()
    assert enforce_artifact_contract(bare).model_dump() == before_bare


def test_c1b_noop_when_no_per_share_headline() -> None:
    """No target (lbo / comps / withheld) → C1b is structurally a no-op."""
    art = _artifact(
        raw_data={"market": {"current_price": 100.0}},
        structured={
            "valuation_synthesis": {
                "weighted_price": None,
                "methods": [_method("dcf", 30.0), _method("comps_pe", 210.0)],  # 7x but no target
            },
        },
        type_="comps",
    )
    before = art.model_dump()
    out = enforce_artifact_contract(art)
    assert out.model_dump() == before


# ── C4: currency caliber ─────────────────────────────────────────────────────


def test_c4_withholds_on_currency_family_blocked_finding_with_surviving_target() -> None:
    """A cross_currency_ratio blocked_field finding survived in numeric_audit yet a
    headline target still rides — withhold (the type-agnostic missed-withhold
    backstop for mixed-currency P/E like SAP / TSM / TM)."""
    art = _artifact(
        raw_data={"market": {"current_price": 100.0}},
        structured={
            "thesis": {"price_target": 130.0, "recommendation": "BUY"},
            "valuation_synthesis": {"weighted_price": 128.0},
            "currency": {"quote_currency": "USD", "reporting_currency": "EUR"},
            "numeric_audit": {
                "findings": [
                    {
                        "field_key": "pe_ratio",
                        "check": "cross_currency_ratio",
                        "severity": "blocked_field",
                        "evidence": "pe_ratio formed across USD/EUR",
                    }
                ]
            },
        },
    )
    out = enforce_artifact_contract(art)
    assert out.outputs.structured["thesis"]["price_target"] is None
    assert out.outputs.structured["valuation_withheld"] is True
    assert any(w.startswith("[CONTRACT/C4]") for w in _warnings(out))


def test_c4_noop_when_currency_finding_is_only_review_severity() -> None:
    """A review-severity currency finding does NOT block — C4 only withholds on a
    blocked_field; a review caliber note is left to flow as-is."""
    art = _artifact(
        raw_data={"market": {"current_price": 100.0}},
        structured={
            "thesis": {"price_target": 130.0, "recommendation": "BUY"},
            "valuation_synthesis": {"weighted_price": 128.0},
            "currency": {"quote_currency": "USD", "reporting_currency": "EUR"},
            "numeric_audit": {
                "findings": [
                    {
                        "field_key": "pe_ratio",
                        "check": "cross_currency_ratio",
                        "severity": "review",
                        "evidence": "advisory only",
                    }
                ]
            },
        },
    )
    before = art.model_dump()
    out = enforce_artifact_contract(art)
    assert out.model_dump() == before


def test_c4_fires_on_currency_block_missing_caliber_keys() -> None:
    """A per-share headline exists and a currency dict is present but missing
    quote/reporting → a caliber gap (the tags weren't resolved) → withhold."""
    art = _artifact(
        raw_data={"market": {"current_price": 100.0}},
        structured={
            "thesis": {"price_target": 130.0, "recommendation": "BUY"},
            "valuation_synthesis": {"weighted_price": 128.0},
            "currency": {"quote_currency": "USD"},  # reporting_currency missing
        },
    )
    out = enforce_artifact_contract(art)
    assert out.outputs.structured["thesis"]["price_target"] is None
    assert any(w.startswith("[CONTRACT/C4]") for w in _warnings(out))


def test_c4_noop_when_no_numeric_audit_and_currency_complete() -> None:
    """dcf / ddm carry no numeric_audit currency findings and a complete currency
    block (or none) → C4 is a no-op, never a spurious withhold."""
    art = _artifact(
        raw_data={"market": {"current_price": 100.0}},
        structured={
            "thesis": {"price_target": 130.0, "recommendation": "BUY"},
            "valuation_synthesis": {"weighted_price": 128.0},
            "currency": {"quote_currency": "USD", "reporting_currency": "USD"},
        },
    )
    before = art.model_dump()
    out = enforce_artifact_contract(art)
    assert out.model_dump() == before


# ── C6: single-method no-cross-check disclosure (SOFT) ───────────────────────


def test_c6_notes_single_method_basis_without_disclosure() -> None:
    """Single method survived (weighted_price None) + live target, but the basis
    fails to disclose it lacks a cross-check → SOFT [CONTRACT/C6/note]. Target is
    NOT withheld — the analyst still gets the number, just told it has no second
    opinion."""
    art = _artifact(
        raw_data={"market": {"current_price": 100.0}},
        structured={
            "thesis": {
                "price_target": 150.0,
                "recommendation": "BUY",
                "price_target_basis": "comps_pe 18x on FY1 EPS",  # no disclosure
            },
            "valuation_synthesis": {"weighted_price": None},  # single method
        },
    )
    out = enforce_artifact_contract(art)
    assert out.outputs.structured["thesis"]["price_target"] == 150.0  # NOT withheld
    assert "valuation_withheld" not in out.outputs.structured
    assert any(w.startswith("[CONTRACT/C6/note]") for w in _warnings(out))


def test_c6_silent_when_disclosure_present() -> None:
    """When the basis already discloses 'no cross-check available' (upstream
    resolve_canonical_thesis writes it), C6 is silent."""
    art = _artifact(
        raw_data={"market": {"current_price": 100.0}},
        structured={
            "thesis": {
                "price_target": 150.0,
                "recommendation": "BUY",
                "price_target_basis": "comps_pe 18x — single-method, no cross-check available",
            },
            "valuation_synthesis": {"weighted_price": None},
        },
    )
    before = art.model_dump()
    out = enforce_artifact_contract(art)
    assert out.model_dump() == before


def test_c6_silent_when_multi_method() -> None:
    """A corroborated multi-method target (weighted_price present) doesn't need the
    single-method disclosure → C6 silent."""
    art = _artifact(
        raw_data={"market": {"current_price": 100.0}},
        structured={
            "thesis": {
                "price_target": 150.0,
                "recommendation": "BUY",
                "price_target_basis": "DCF + comps weighted",
            },
            "valuation_synthesis": {"weighted_price": 148.0},
        },
    )
    before = art.model_dump()
    out = enforce_artifact_contract(art)
    assert out.model_dump() == before


# ── C3: basis conclusion amount == headline ──────────────────────────────────


def test_c3_withholds_when_basis_conclusion_contradicts_headline() -> None:
    """basis 'comps_pe 36.9x → $999' but headline price_target=130 — the cue-
    anchored conclusion amount ($999, after '→') contradicts the headline → withhold."""
    art = _artifact(
        raw_data={"market": {"current_price": 100.0}},
        structured={
            "thesis": {
                "price_target": 130.0,
                "recommendation": "BUY",
                "price_target_basis": "comps_pe 36.9x → $999",
            },
            "valuation_synthesis": {"weighted_price": 128.0},
        },
    )
    out = enforce_artifact_contract(art)
    assert out.outputs.structured["thesis"]["price_target"] is None
    assert out.outputs.structured["valuation_withheld"] is True
    assert any(w.startswith("[CONTRACT/C3]") for w in _warnings(out))


def test_c3_noop_when_conclusion_equals_headline() -> None:
    """basis conclusion amount == headline (within tolerance) → no contradiction."""
    art = _artifact(
        raw_data={"market": {"current_price": 100.0}},
        structured={
            "thesis": {
                "price_target": 130.0,
                "recommendation": "BUY",
                "price_target_basis": "comps_pe 18x → target $130.00",
            },
            "valuation_synthesis": {"weighted_price": 128.0},
        },
    )
    before = art.model_dump()
    out = enforce_artifact_contract(art)
    assert out.model_dump() == before


def test_c3_noop_within_rounding_tolerance() -> None:
    """A rounded restatement ('$276' against headline 276.43) is inside the shared
    NARRATIVE_DRIFT_TOLERANCE → not a contradiction."""
    art = _artifact(
        raw_data={"market": {"current_price": 200.0}},
        structured={
            "thesis": {
                "price_target": 276.43,
                "recommendation": "BUY",
                "price_target_basis": "DCF → target $276",
            },
            "valuation_synthesis": {"weighted_price": 270.0},
        },
    )
    before = art.model_dump()
    out = enforce_artifact_contract(art)
    assert out.model_dump() == before


def test_c3_noop_when_dollar_amounts_have_no_conclusion_cue() -> None:
    """THE FALSE-POSITIVE GUARD: the basis cites per-method mids ($5.88, $19.54)
    with NO conclusion cue (no →, no 'target'/'目标') — C3 must NOT guess one of
    them is the conclusion. Headline 130 differs from both, yet C3 is a NO-OP."""
    art = _artifact(
        raw_data={"market": {"current_price": 100.0}},
        structured={
            "thesis": {
                "price_target": 130.0,
                "recommendation": "BUY",
                "price_target_basis": "DCF says $5.88, comps say $19.54, they disagree",
            },
            "valuation_synthesis": {"weighted_price": 128.0},
        },
    )
    before = art.model_dump()
    out = enforce_artifact_contract(art)
    assert out.model_dump() == before


# ── §4 closure family (§7.2–§7.5, promoted 2026-10-14) ───────────────────────
#
# §7.4: one payload that passes and one that violates, per clause, plus the
# invariant that a violation NEVER raises — a clause that raised at the persist
# boundary would blank the run. These fifteen clauses were staged inert and
# quantified over the stored corpus (``scan_artifact_contract.py``, §7.1/§7.5)
# before being appended to ``CONTRACT_CLAUSES``, so they now run in the live gate;
# ``test_the_closure_family_runs_in_the_live_registry`` and the two
# ``…_at_the_persist_boundary`` tests below pin that they are armed, at the
# severity §9 locks, and that the gate acts on them.
#
# The payloads below are the shapes the corpus actually carries, reduced to the
# paths each clause reads. The corpus-wide fixtures that prove the SAME predicates
# against whole stored payloads — including instance B (99cdca), where the root
# OMITS ``valuation_withheld`` while the synthesis writes ``false`` — are §7.2's
# job and live in ``tests/artifact/``.

#: The fifteen §4 closure clauses, named so that a registry that lost one shows up
#: here as a missing key rather than as silently fewer parametrized cases.
_CLOSURE_IDS = (
    "C6b",
    "C8",
    "C9",
    "C10a",
    "C10b",
    "C10c",
    "C10d",
    "C11",
    "C12a",
    "C12b",
    "C12c",
    "C13b",
    "C13c",
    "C14a",
    "C14b",
)
_CLOSURE = {c.id: c for c in CONTRACT_CLAUSES if c.id in _CLOSURE_IDS}
assert len(_CLOSURE) == len(_CLOSURE_IDS), "the closure family is not fully registered"


def _closure_finding(clause_id: str, art: Artifact):
    """Assert the clause fired, and that the finding is reportable."""
    finding = _CLOSURE[clause_id].check(art)
    assert finding is not None, f"{clause_id} did not fire"
    assert finding.check.startswith("contract_")
    assert finding.field_key
    assert finding.evidence.strip()
    return finding


def _closure_soft_artifact() -> Artifact:
    """One artifact that trips several SOFT closure clauses and no HARD one."""
    return _artifact(
        raw_data={
            "income": {"operating_margin": 0.18159},
            "market": {"current_price": 271.6},
            "data_authority": {
                "decisions": [
                    {
                        "metric": "ebitda",
                        "status": "accepted",
                        "selected_source": "yfinance",
                        "comparability": "caliber_divergent",
                        "agreement_is_independent": False,
                    }
                ]
            },
        },
        structured={
            "thesis": {
                "recommendation": "HOLD",
                "narrative": "Insiders were net sellers of [target withheld].",
            },
            # Both writers present and equal, so C11 (HARD) stays quiet and this
            # payload isolates the SOFT annotations.
            "valuation_withheld": False,
            "valuation_synthesis": {
                "valuation_withheld": False,
                "methods": [{"name": "dcf"}],
                "cross_checks": [
                    {"name": "ev_ebitda_band", "low": 70.0, "mid": 219.8, "high": 255.3}
                ],
                "current_price": 271.6,
                "degradation_note": "single method dcf with no cross-validation",
            },
            "ownership_governance": {"insider_net_flow": 49_991_274.0},
            "catalyst_analysis": {
                "news_window": {"count": 0, "sources": [], "provider": None},
                "overall_sentiment": "neutral",
            },
            "technical_analysis": {
                "monte_carlo": {"assumptions_used": {"centered_on": "base-case DCF assumptions"}}
            },
            "xbrl_facts_snapshot": {
                "us-gaap:Assets": [{"value": 30_676_000_000.0}],
                "us-gaap:Liabilities": [{"value": 21_976_000_000.0}],
                "us-gaap:StockholdersEquity": [{"value": 4_658_000_000.0}],
            },
        },
    )


def test_every_clause_carries_a_renderable_title_and_doc() -> None:
    """§9.8: the registry needs a renderable name per clause so a human-review surface
    (and later the reason-code registry of §9.6) names the rule, not only its id. The
    title lives on the clause and nowhere else — a copy in a consumer is the drift
    class §4.4 exists to catch."""
    for clause in CONTRACT_CLAUSES:
        assert clause.title, f"{clause.id} has no title"
        assert clause.doc, f"{clause.id} has no doc"
        assert len(clause.doc) < 120, f"{clause.id}'s doc is a spec, not a one-liner"


def test_count_thresholds_are_declared_inert() -> None:
    """§9.2/§9.8 declared `warn_if`/`error_if` additive and behaviour-preserving. This
    pins the "inert" half: no clause sets them, and the live gate ignores them, so the
    fixture verdict oracle (tests/artifact/test_contract_fixtures.py) is unchanged by
    their presence. When the first clause arms one, its count carrier arrives with the
    `NumericClaim` fields of §6/§9.5 — that change owns this assertion."""
    for clause in CONTRACT_CLAUSES:
        assert clause.warn_if is None
        assert clause.error_if is None


def test_the_closure_family_runs_in_the_live_registry() -> None:
    """THE PROMOTION PROOF. ``C8``/``C11`` withhold (H) because their locked
    remediation IS a value-withhold; the other thirteen annotate (S) because their
    locked shape — a count threshold, a sentence deletion, or (``C9``) a claim-scope
    drop the gate cannot perform — is not expressible here yet. A clause that lost or
    gained a severity is a silent change in what ships."""
    expected = {
        **dict.fromkeys(("C8", "C11"), "H"),
        **dict.fromkeys(
            (
                "C6b",
                "C9",
                "C10a",
                "C10b",
                "C10c",
                "C10d",
                "C12a",
                "C12b",
                "C12c",
                "C13b",
                "C13c",
                "C14a",
                "C14b",
            ),
            "S",
        ),
    }
    assert {cid: _CLOSURE[cid].severity for cid in _CLOSURE_IDS} == expected


def test_closure_hard_violation_withholds_at_the_persist_boundary() -> None:
    """THE ARMED-HALF PROOF. Instance B's shape — the root OMITS ``valuation_withheld``
    while the synthesis writes ``false`` — now withholds at the persist boundary where
    it used to pass through untouched, and the record names the clause."""
    art = _artifact(structured={"valuation_synthesis": {"valuation_withheld": False}})
    assert _CLOSURE["C11"].check(art) is not None
    out = enforce_artifact_contract(art)
    structured = out.outputs.structured
    assert structured["valuation_withheld"] is True
    assert structured["withheld_reason"] == "contract_C11"
    assert any(w.startswith("[CONTRACT/C11] ") for w in out.outputs.warnings)


def test_closure_soft_violations_only_annotate_at_the_persist_boundary() -> None:
    """THE ARMED-SOFT-HALF PROOF. The same payload that used to come out byte-identical
    is annotated once per SOFT violation and keeps its target: an S clause may add
    evidence, it may never withhold a value (doctrine: a clause withholds a value,
    never flips a verdict)."""
    art = _closure_soft_artifact()
    firing = {c.id for c in CONTRACT_CLAUSES if c.check(art) is not None}
    hard = {cid for cid in firing if _CLOSURE[cid].severity == "H"}
    assert firing & set(_CLOSURE_IDS), "the payload no longer exercises the closure family"
    assert not hard, f"soft payload trips a HARD clause: {sorted(hard)}"
    out = enforce_artifact_contract(art)
    notes = [w for w in out.outputs.warnings if w.startswith("[CONTRACT/") and "/note] " in w]
    assert {note.split("/")[1] for note in notes} == firing
    assert out.outputs.structured.get("valuation_withheld") is not True


@pytest.mark.parametrize("clause_id", sorted(_CLOSURE))
def test_closure_clause_never_raises_on_any_shape(clause_id: str) -> None:
    """A clause must report a violation, never throw one, whatever the payload
    holds — this is the invariant the scanner relies on to sweep the store, and
    the reason the guard is a return value rather than an exception."""
    for art in _degenerate_artifacts():
        _CLOSURE[clause_id].check(art)


def _degenerate_artifacts() -> list[Artifact]:
    """Empty, wrongly-typed and null-valued payloads — every shape a clause reads
    a container from, made hostile."""
    return [
        _artifact(),
        _artifact(structured={}, raw_data={}),
        _artifact(
            structured={
                "thesis": [],
                "valuation_synthesis": "block",
                "ownership_governance": None,
                "catalyst_analysis": {"news_window": [], "sec_8k_staleness_warning": 7},
                "technical_analysis": {"monte_carlo": {"assumptions_used": []}},
                "xbrl_facts_snapshot": {"us-gaap:Assets": "123"},
                "valuation_withheld": None,
            },
            raw_data={
                "income": [],
                "data_authority": {"decisions": "none"},
                "market": {"current_price": "271.6"},
            },
        ),
        _artifact(
            structured={
                "thesis": {"narrative": None, "catalysts": [None, 3]},
                "valuation_synthesis": {
                    "cross_checks": [{"low": None, "mid": "x", "high": True}, []],
                    "methods": None,
                    "valuation_withheld": None,
                },
                "xbrl_facts_snapshot": {"_equity_identity": [{"assets": None}]},
                "technical_analysis": {"monte_carlo": {"assumptions_used": {"centered_on": 5}}},
            },
            raw_data={"data_authority": {"decisions": [None, {"metric": None}]}},
        ),
    ]


# ── C6b / C8 / C9: the cross-check readers ──────────────────────────────────


def test_c6b_fires_when_the_note_denies_the_cross_check_it_publishes() -> None:
    """Instance B's shape: one method, a published cross-check, and a note that
    claims there was no cross-validation."""
    art = _artifact(
        structured={
            "thesis": {"recommendation": "BUY"},
            "valuation_synthesis": {
                "methods": [{"name": "dcf"}],
                "cross_checks": [
                    {"name": "ev_ebitda_band", "low": 70.0, "mid": 219.8, "high": 255.3}
                ],
                "current_price": 271.6,
                "degradation_note": "single method dcf with no cross-validation — band widened.",
            },
        }
    )
    finding = _closure_finding("C6b", art)
    assert "ev_ebitda_band" in finding.evidence
    assert "none brackets" in finding.evidence


def test_c6b_quiet_when_the_note_and_the_evidence_agree() -> None:
    art = _artifact(
        structured={
            "thesis": {"recommendation": "BUY"},
            "valuation_synthesis": {
                "methods": [{"name": "dcf"}],
                "cross_checks": [],
                "degradation_note": "single method dcf with no cross-validation — band widened.",
            },
        }
    )
    assert _CLOSURE["C6b"].check(art) is None


def test_c8_fires_on_a_buy_whose_only_band_sits_below_the_tape() -> None:
    art = _artifact(
        structured={
            "thesis": {"recommendation": "BUY"},
            "valuation_synthesis": {
                "current_price": 271.6,
                "cross_checks": [
                    {"name": "ev_ebitda_band", "low": 70.0, "mid": 219.8, "high": 255.3}
                ],
            },
        }
    )
    finding = _closure_finding("C8", art)
    assert "contradicts" in finding.evidence


def test_c8_quiet_when_a_band_brackets_the_tape() -> None:
    """A band that spans the price claims no side → not a contradiction."""
    art = _artifact(
        structured={
            "thesis": {"recommendation": "BUY"},
            "valuation_synthesis": {
                "current_price": 271.6,
                "cross_checks": [
                    {"name": "ev_ebitda_band", "low": 100.0, "mid": 300.0, "high": 400.0}
                ],
            },
        }
    )
    assert _CLOSURE["C8"].check(art) is None


def test_c8_does_not_read_a_band_c9_has_rejected() -> None:
    """SKM's shape: the only cross-check is degenerate, so C9 owns it. C8 must
    return None rather than count the unusable band as evidence — this is why C8
    flags 7 of §1.1's 8 artifacts and the two clauses cover the list only as a
    pair."""
    art = _artifact(
        structured={
            "thesis": {"recommendation": "BUY"},
            "valuation_synthesis": {
                "current_price": 34.42,
                "cross_checks": [
                    {"name": "ev_ebitda_band", "low": -2.97, "mid": -1.70, "high": -1.23}
                ],
            },
        }
    )
    assert _CLOSURE["C8"].check(art) is None
    assert _closure_finding("C9", art) is not None


def test_c8_does_not_read_a_row_the_verdict_never_had() -> None:
    """§5's tag: the SAME band that fires above, marked ``consulted_by_verdict=False``
    — the audit back-fill, published after the call — is display-only. C8's claim is
    that the verdict contradicted evidence it HAD; a row it never had cannot be that."""
    art = _artifact(
        structured={
            "thesis": {"recommendation": "BUY"},
            "valuation_synthesis": {
                "current_price": 271.6,
                "cross_checks": [
                    {
                        "name": "ev_ebitda_band",
                        "low": 70.0,
                        "mid": 219.8,
                        "high": 255.3,
                        "consulted_by_verdict": False,
                    }
                ],
            },
        }
    )
    assert _CLOSURE["C8"].check(art) is None


def _cross_check_slate(*rows: dict, recommendation: str = "BUY", price: float = 200.0) -> Artifact:
    return _artifact(
        structured={
            "thesis": {"recommendation": recommendation},
            "valuation_synthesis": {"current_price": price, "cross_checks": list(rows)},
        }
    )


def _display_only(low: float, mid: float, high: float) -> dict:
    return {
        "name": "ev_ebitda_band",
        "low": low,
        "mid": mid,
        "high": high,
        "consulted_by_verdict": False,
    }


def test_c8_reads_the_consulted_rows_of_a_mixed_slate() -> None:
    """The filter drops display-only rows and NOTHING else: a corroborating row the
    verdict did have still vetoes (below 200 is a BUY's way), and a contradicting one
    it did have still fires even beside a display-only row."""
    corroborated = _cross_check_slate(
        _display_only(10.0, 20.0, 30.0),
        {"name": "ev_ebitda_band", "low": 150.0, "mid": 260.0, "high": 300.0},
    )
    assert _CLOSURE["C8"].check(corroborated) is None

    contradicting = _cross_check_slate(
        _display_only(500.0, 600.0, 700.0),  # ignores display-only: it points the call's way
        {"name": "ev_ebitda_band", "low": 10.0, "mid": 20.0, "high": 30.0},
        price=400.0,
    )
    assert _closure_finding("C8", contradicting) is not None


def test_c6b_names_the_provenance_when_every_printed_row_is_display_only() -> None:
    """C6b reads what the report PRINTS, so a back-filled row still counts — but then
    the note is true of the decision and the PUBLICATION is what needs the qualifier.
    The finding has to say which, or the analyst "fixes" a derivation that is correct."""

    def _with_row(row: dict) -> Artifact:
        return _artifact(
            structured={
                "thesis": {"recommendation": "BUY"},
                "valuation_synthesis": {
                    "methods": [{"name": "dcf"}],
                    "cross_checks": [row],
                    "current_price": 271.6,
                    "degradation_note": (
                        "single method dcf with no cross-validation — band widened."
                    ),
                },
            }
        )

    row = {"name": "ev_ebitda_band", "low": 70.0, "mid": 219.8, "high": 255.3}
    assert (
        "display-only"
        in _closure_finding("C6b", _with_row({**row, "consulted_by_verdict": False})).evidence
    )
    assert "display-only" not in _closure_finding("C6b", _with_row(row)).evidence


def test_c9_fires_on_a_non_positive_band() -> None:
    art = _artifact(
        structured={
            "valuation_synthesis": {
                "cross_checks": [
                    {"name": "ev_ebitda_band", "low": -2.97, "mid": -1.70, "high": -1.23}
                ]
            }
        }
    )
    finding = _closure_finding("C9", art)
    assert "not positive" in finding.evidence


def test_c9_fires_on_a_band_that_is_not_monotone() -> None:
    art = _artifact(
        structured={
            "valuation_synthesis": {
                "cross_checks": [{"name": "ev_ebitda_band", "low": 10.0, "mid": 99.0, "high": 20.0}]
            }
        }
    )
    assert "outside" in _closure_finding("C9", art).evidence


# ── C11: the mirrored slot ──────────────────────────────────────────────────


def test_c11_fires_when_one_writer_omits_the_mirrored_slot() -> None:
    """The corpus shape, and the one the first probe's ``is not None`` guard hid:
    the root OMITS the key while the synthesis writes ``false``."""
    art = _artifact(structured={"valuation_synthesis": {"valuation_withheld": False}})
    finding = _closure_finding("C11", art)
    assert "omits the slot" in finding.evidence


def test_c11_fires_when_the_two_writers_disagree_on_the_value() -> None:
    art = _artifact(
        structured={
            "valuation_withheld": False,
            "valuation_synthesis": {"valuation_withheld": True},
        }
    )
    assert "disagree" in _closure_finding("C11", art).evidence


def test_c11_quiet_when_the_writers_agree_or_both_stay_silent() -> None:
    both_true = _artifact(
        structured={
            "valuation_withheld": True,
            "valuation_synthesis": {"valuation_withheld": True},
        }
    )
    neither = _artifact(structured={"valuation_synthesis": {}})
    assert _CLOSURE["C11"].check(both_true) is None
    assert _CLOSURE["C11"].check(neither) is None


# ── C10a–C10d: conclusion ratios ────────────────────────────────────────────


def test_c10a_fires_on_a_margin_with_no_numerator() -> None:
    art = _artifact(raw_data={"income": {"operating_margin": 0.18159}})
    finding = _closure_finding("C10a", art)
    assert "operating_income" in finding.evidence


def test_c10a_quiet_when_both_operands_are_present() -> None:
    art = _artifact(
        raw_data={"income": {"operating_margin": 0.18159, "operating_income": 4_418_000_000.0}}
    )
    assert _CLOSURE["C10a"].check(art) is None


def test_c10b_fires_when_the_two_operands_come_from_different_sources() -> None:
    art = _artifact(
        raw_data={
            "data_authority": {
                "decisions": [
                    {"metric": "revenue", "status": "accepted", "selected_source": "yfinance"},
                    {
                        "metric": "operating_income",
                        "status": "accepted",
                        "selected_source": "eodhd",
                    },
                ]
            }
        }
    )
    finding = _closure_finding("C10b", art)
    assert "different sources" in finding.evidence


def test_c10b_quiet_when_one_source_serves_both_operands() -> None:
    art = _artifact(
        raw_data={
            "data_authority": {
                "decisions": [
                    {"metric": "revenue", "status": "accepted", "selected_source": "yfinance"},
                    {
                        "metric": "operating_income",
                        "status": "accepted",
                        "selected_source": "yfinance",
                    },
                ]
            }
        }
    )
    assert _CLOSURE["C10b"].check(art) is None


def test_c10c_fires_when_the_identity_is_computable_but_unrecorded() -> None:
    art = _artifact(
        structured={
            "xbrl_facts_snapshot": {
                "us-gaap:Assets": [{"value": 30_676_000_000.0}],
                "us-gaap:Liabilities": [{"value": 21_976_000_000.0}],
                "us-gaap:StockholdersEquity": [{"value": 4_658_000_000.0}],
            }
        }
    )
    assert "not recorded" in _closure_finding("C10c", art).evidence


def test_c10c_verifies_a_recorded_identity_and_quiet_when_it_closes() -> None:
    """THC's record: 30.676 − 21.976 = 8.700 total, of which 4.658 parent and
    4.042 noncontrolling interest."""
    art = _artifact(
        structured={
            "xbrl_facts_snapshot": {
                "_equity_identity": [
                    {
                        "assets": 30_676_000_000.0,
                        "liabilities": 21_976_000_000.0,
                        "total_equity": 8_700_000_000.0,
                        "parent_stockholders_equity": 4_658_000_000.0,
                        "noncontrolling_interest": 4_042_000_000.0,
                    }
                ]
            }
        }
    )
    assert _CLOSURE["C10c"].check(art) is None


def test_c10c_fires_on_a_recorded_identity_that_does_not_close() -> None:
    art = _artifact(
        structured={
            "xbrl_facts_snapshot": {
                "_equity_identity": [
                    {
                        "assets": 30_676_000_000.0,
                        "liabilities": 21_976_000_000.0,
                        "total_equity": 9_000_000_000.0,
                        "parent_stockholders_equity": 4_658_000_000.0,
                        "noncontrolling_interest": 4_042_000_000.0,
                    }
                ]
            }
        }
    )
    assert "does not close" in _closure_finding("C10c", art).evidence


def test_c10d_fires_on_an_accepted_caliber_divergent_decision() -> None:
    art = _artifact(
        raw_data={
            "data_authority": {
                "decisions": [
                    {
                        "metric": "ebitda",
                        "status": "accepted",
                        "selected_source": "yfinance",
                        "comparability": "caliber_divergent",
                    }
                ]
            }
        }
    )
    assert "caliber_divergent" in _closure_finding("C10d", art).evidence


def test_c10d_quiet_when_the_divergent_comparison_was_not_accepted() -> None:
    art = _artifact(
        raw_data={
            "data_authority": {
                "decisions": [
                    {
                        "metric": "ebitda",
                        "status": "rejected",
                        "selected_source": "yfinance",
                        "comparability": "caliber_divergent",
                    }
                ]
            }
        }
    )
    assert _CLOSURE["C10d"].check(art) is None


# ── C12a–C12c: recency and window closure ───────────────────────────────────


def test_c12a_fires_on_the_artifact_s_own_staleness_disclosure() -> None:
    art = _artifact(
        structured={
            "catalyst_analysis": {
                "sec_8k_staleness_warning": "SEC 8-K index is stale relative to the news window",
                "sec_8k_window": {"count": 10, "oldest": "2025-11-24", "newest": "2026-09-22"},
            }
        }
    )
    assert "stale" in _closure_finding("C12a", art).evidence


def test_c12a_quiet_without_the_disclosure() -> None:
    art = _artifact(structured={"catalyst_analysis": {"sec_8k_window": {"count": 10}}})
    assert _CLOSURE["C12a"].check(art) is None


def test_c12b_fires_on_an_empty_news_window_carrying_a_populated_read() -> None:
    art = _artifact(
        structured={
            "catalyst_analysis": {
                "news_window": {"count": 0, "sources": [], "provider": None},
                "overall_sentiment": "neutral",
                "key_catalysts": ["no"],
            }
        }
    )
    finding = _closure_finding("C12b", art)
    assert "news window is empty" in finding.evidence


def test_c12b_quiet_when_the_window_has_news() -> None:
    art = _artifact(structured={"catalyst_analysis": {"news_window": {"count": 3}}})
    assert _CLOSURE["C12b"].check(art) is None


def test_c12c_fires_on_a_fact_the_producer_annotated_as_stale() -> None:
    art = _artifact(
        structured={
            "xbrl_facts_snapshot": {
                "us-gaap:OperatingIncomeLoss": [
                    {
                        "value": 1.0,
                        "period_end": "2022-12-31",
                        "warning": (
                            "stale: latest reported period is 2026-06-30, this fact is 2022-12-31"
                        ),
                    }
                ]
            }
        }
    )
    assert "annotated as stale" in _closure_finding("C12c", art).evidence


def test_c12c_quiet_on_a_derived_quarter_warning() -> None:
    """The other warning the snapshot carries is a caliber caveat, not staleness —
    the clause keys on ``stale:`` and must not collect it."""
    art = _artifact(
        structured={
            "xbrl_facts_snapshot": {
                "us-gaap:Revenues": [
                    {
                        "value": 1.0,
                        "period_end": "2026-07-26",
                        "warning": "Some quarters were derived from YTD or annual facts.",
                    }
                ]
            }
        }
    )
    assert _CLOSURE["C12c"].check(art) is None


# ── C13b / C13c: independence ───────────────────────────────────────────────


def test_c13b_fires_when_a_self_centred_distribution_is_not_declared_dependent() -> None:
    art = _artifact(
        structured={
            "technical_analysis": {
                "monte_carlo": {"assumptions_used": {"centered_on": "base-case DCF assumptions"}}
            }
        }
    )
    assert "independent" in _closure_finding("C13b", art).evidence


def test_c13b_quiet_when_the_declaration_is_present() -> None:
    art = _artifact(
        structured={
            "technical_analysis": {
                "monte_carlo": {
                    "assumptions_used": {
                        "centered_on": "base-case DCF assumptions",
                        "independent": False,
                    }
                }
            }
        }
    )
    assert _CLOSURE["C13b"].check(art) is None


def test_c13c_fires_when_every_agreement_is_non_independent() -> None:
    art = _artifact(
        raw_data={
            "data_authority": {
                "decisions": [
                    {
                        "metric": "ebitda",
                        "status": "accepted",
                        "agreement_is_independent": False,
                    }
                ]
            }
        }
    )
    assert "circular" in _closure_finding("C13c", art).evidence


def test_c13c_quiet_when_an_independent_agreement_exists() -> None:
    art = _artifact(
        raw_data={
            "data_authority": {
                "decisions": [
                    {"metric": "ebitda", "status": "accepted", "agreement_is_independent": False},
                    {"metric": "revenue", "status": "accepted", "agreement_is_independent": True},
                ]
            }
        }
    )
    assert _CLOSURE["C13c"].check(art) is None


# ── C14a / C14b: prose grounding ────────────────────────────────────────────


def test_c14a_fires_when_a_direction_word_contradicts_the_leaf_sign() -> None:
    art = _artifact(
        structured={
            "thesis": {"narrative": "Insiders were net buyers over the quarter."},
            "ownership_governance": {"insider_net_flow": -49_991_274.0},
        }
    )
    assert "contradicts the sign" in _closure_finding("C14a", art).evidence


def test_c14a_quiet_when_the_direction_word_matches() -> None:
    art = _artifact(
        structured={
            "thesis": {"narrative": "Insiders were net sellers over the quarter."},
            "ownership_governance": {"insider_net_flow": -49_991_274.0},
        }
    )
    assert _CLOSURE["C14a"].check(art) is None


def test_c14b_fires_when_the_placeholder_took_a_published_flow() -> None:
    """AFRM's shape: the flow is a published leaf, so the sentence asserting the
    placeholder contradicts the artifact's own numbers."""
    art = _artifact(
        structured={
            "thesis": {
                "narrative": "Over the last 90 days insiders were net sellers of [target withheld]."
            },
            "ownership_governance": {"insider_net_flow": -4_413_467.0},
        }
    )
    assert "insider-flow amount" in _closure_finding("C14b", art).evidence


def test_c14b_quiet_on_the_withheld_path_s_own_disclaimer() -> None:
    """THE FALSE-POSITIVE GUARD. The withheld path legitimately prints the
    placeholder and disclaims the point; the coarse "token anywhere in the prose"
    form flags these 27 artifacts and was rejected for it (re-measured as
    over-broad, §7.1). Only a sentence that also names a flow is a defect."""
    art = _artifact(
        structured={
            "thesis": {
                "narrative": (
                    "We initiate SMCI at BUY on a directional read, not a point estimate: "
                    "the point target is [target withheld]."
                )
            },
            "ownership_governance": {"insider_net_flow": -4_413_467.0},
        }
    )
    assert _CLOSURE["C14b"].check(art) is None
