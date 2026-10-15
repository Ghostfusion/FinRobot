"""The band C10e judges against is the one the published figures' own DECLARED PRECISION
allows — XBRL's rounded fact value interval (Calculations 1.1 §5.2.3-5.2.4), not a taste
for round numbers.

Why that matters, measured over the stored corpus (2026-10-15, 142 artifacts,
``scripts/sweep_identities.py``): at the old flat 1% band, 48 of 609 bound checks were
flagged; at the declared-precision band, 63. The 15 extra are not noise — they are
sub-1% caliber mismatches the coarse band excused (a KGC operating margin published
0.8179% off ``operating_income / revenue``; ten pre-fix P/E rows whose provider ratio rode
a different denominator). A band that cannot name what it is derived from cannot tell a
rounded provider figure from a contradicting one, so these tests pin all three
behaviours: a rounding-level difference passes, a sub-1% contradiction is caught, and an
identity whose leaves declare no precision says so instead of pretending.
"""

from __future__ import annotations

import datetime as dt

import pytest

from finrobot.artifact.contract import _clause_c10e_quantity_contradicts_derivation
from finrobot.artifact.models import (
    Artifact,
    ArtifactAssumptions,
    ArtifactComputeVersion,
    ArtifactInputs,
    ArtifactMeta,
    ArtifactOutputs,
)
from finrobot.engine.models import identities
from finrobot.engine.models.identities import (
    checked_identities,
    identity_tolerance,
    leaf_digits,
    leaf_kind,
    leaf_paths,
)
from finrobot.engine.models.reconcile_tolerances import IDENTITY_RESIDUAL_TOLERANCE

CREATED = dt.datetime(2026, 10, 15, tzinfo=dt.UTC)

# The CF block's own figures: operating_income / revenue = 0.3908773840352058, published
# as the failing 0.49325 in the audited report.
REVENUE = 7_738_999_808.0
OPERATING_INCOME = 3_025_000_000.0
TRUE_MARGIN = OPERATING_INCOME / REVENUE


def _artifact(raw_data: dict) -> Artifact:
    return Artifact(
        id="art_2026-10-15T00:00:00_CF_equity_research",
        ticker="CF",
        cross_tickers=[],
        type="equity_research",
        inputs=ArtifactInputs(data_source="yfinance", data_fetched_at=CREATED, raw_data=raw_data),
        assumptions=ArtifactAssumptions(parameters={}),
        compute_version=ArtifactComputeVersion(version="0.1.0", formula_id="x"),
        outputs=ArtifactOutputs(structured={}, llm_narrative={}, summary_text="head", warnings=[]),
        meta=ArtifactMeta(created_at=CREATED, source="pipeline:equity_research"),
    )


def _margin_artifact(published: float) -> Artifact:
    return _artifact(
        {
            "income": {
                "revenue": REVENUE,
                "operating_income": OPERATING_INCOME,
                "operating_margin": published,
            }
        }
    )


def _margin_finding(published: float):
    return _clause_c10e_quantity_contradicts_derivation(_margin_artifact(published))


# ── the declaration is complete ──────────────────────────────────────────────


def test_every_leaf_an_enforced_identity_reads_declares_its_kind() -> None:
    """An undeclared leaf is an identity that silently falls back to the coarse band.

    ``ev_ebitda`` was doing exactly that: its divisor ``valuation.ebitda_operating`` was
    absent from ``LEAF_KINDS``, so the one identity with a dollar-amount divisor was the
    only checked identity whose band came from the fallback — invisible except by
    measuring which identities used it.
    """
    for spec in checked_identities():
        for operand, path in leaf_paths(spec.id):
            assert leaf_kind(path) is not None, (
                f"{spec.id}: operand {operand} -> {path} declares no kind"
            )
        assert spec.total_path is not None
        assert leaf_kind(spec.total_path) is not None, (
            f"{spec.id}: {spec.total_path} declares no kind"
        )


def test_every_leaf_an_enforced_identity_reads_declares_its_precision() -> None:
    """Kind and precision are declared together; one without the other is half a declaration."""
    for spec in checked_identities():
        for path in [*dict(leaf_paths(spec.id)).values(), spec.total_path or ""]:
            assert leaf_digits(path) is not None, f"{spec.id}: {path} declares no precision"


def test_declared_precision_follows_the_kind_and_can_be_overridden() -> None:
    assert leaf_digits("income.revenue") == 0  # whole dollars
    assert leaf_digits("market.current_price") == 2  # the cent
    assert leaf_digits("income.operating_margin") == 4  # the report prints 39.09%
    assert leaf_digits("nowhere.at.all") is None  # undeclared, never assumed exact


# ── the band is derived, not chosen ──────────────────────────────────────────


def test_a_sum_accumulates_every_contributing_half_unit() -> None:
    """EV = cap + net debt + preferred + NCI, all rounded to the dollar, checked against
    an EV rounded to the dollar: three dollars of interval over 1,090 is the band."""
    operands = {
        "market_cap": 1_000.0,
        "net_debt": 60.0,
        "preferred_stock": 10.0,
        "noncontrolling_interest": 20.0,
    }
    tolerance, basis = identity_tolerance("ev_build", operands, 1_090.0)
    # 0.5 (cap) + 0.5 + 0.5 (the two net-debt legs) + 0.5 (preferred) + 0.5 (NCI) + 0.5 (published)
    assert basis == "declared_precision"
    assert tolerance == pytest.approx(3.0 / 1_090.0)


def test_a_ratio_band_is_the_propagated_rounding_of_both_sides() -> None:
    """The margin's own 4 decimals dominate: 0.5e-4 over 0.39088 is 0.0128%, and the
    dollar-rounded operands add ~1e-10 of it."""
    operands = {"operating_income": OPERATING_INCOME, "revenue": REVENUE}
    tolerance, basis = identity_tolerance("operating_margin", operands, TRUE_MARGIN)
    assert basis == "declared_precision"
    assert tolerance == pytest.approx(5.00009e-5 / TRUE_MARGIN, rel=1e-3)
    assert tolerance < IDENTITY_RESIDUAL_TOLERANCE / 50


def test_an_undeclared_precision_names_the_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """No precision on a leaf ⇒ the coarse band, and the caller is TOLD which one it got."""
    monkeypatch.delitem(identities.LEAF_KINDS, "income.revenue")
    operands = {"operating_income": OPERATING_INCOME, "revenue": REVENUE}
    assert identity_tolerance("operating_margin", operands, TRUE_MARGIN) == (
        IDENTITY_RESIDUAL_TOLERANCE,
        "fallback",
    )


# ── the clause: rounding passes, a contradiction is caught ───────────────────


def test_a_margin_rounded_to_its_declared_precision_passes() -> None:
    """The report prints 39.09%; a value rounded there is not a contradiction."""
    assert _margin_finding(0.3909) is None


def test_the_exact_margin_passes() -> None:
    assert _margin_finding(TRUE_MARGIN) is None


def test_a_sub_one_percent_contradiction_is_caught() -> None:
    """The tightening: 0.5% off derived from the same three leaves is a caliber mismatch,
    not rounding — the coarse 1% band excused it, the declared-precision band does not."""
    finding = _margin_finding(0.3928)
    assert finding is not None
    assert finding.field_key == "income.operating_margin"
    assert "their declared precision allows" in finding.evidence


def test_the_audited_cf_margin_is_still_caught() -> None:
    """0.49325 beside 0.390877 — the shipped contradiction, still caught and still naming
    both numbers and the band it failed."""
    finding = _margin_finding(0.49325)
    assert finding is not None
    assert "0.49325" in finding.evidence
    assert "0.390877" in finding.evidence
    # the residual is relative to the larger magnitude: 0.102373 / 0.49325
    assert "20.8% apart" in finding.evidence
    assert "their declared precision allows" in finding.evidence


def test_an_undeclared_leaf_falls_back_and_the_finding_says_so(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With revenue's kind withdrawn, 5% still fires — against the FALLBACK band, which
    the evidence names, so a reader can tell why 0.5% passed a moment ago."""
    monkeypatch.delitem(identities.LEAF_KINDS, "income.revenue")
    finding = _margin_finding(0.41)
    assert finding is not None
    assert "the fallback tolerance allows" in finding.evidence
