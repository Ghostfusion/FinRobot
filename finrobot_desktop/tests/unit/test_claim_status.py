"""Claim-status vocabulary tests.

The module's whole value is in three inversions it must not allow, so those are what
these tests pin:

* an **unrun check** must not read as a clean report (empty rollup ⇒ ``unknown``);
* an **empty evidence set** must not turn a broken *check* into an accusation against
  the report (⇒ ``unknown``, not ``unsupported``);
* a **weak or absent result** must not be reported as refuted (⇒ ``inconclusive``,
  never ``refuted``, and ``unknown`` is never the best status in a rollup).
"""

from __future__ import annotations

import pytest

from finrobot.engine.compute.operators.audit.claim_anchor import (
    anchor_claim_status,
    claim_status_note,
    overall_claim_status,
)
from finrobot.engine.compute.operators.report_drift import ReportDrift
from finrobot.engine.models.claim_status import (
    CLAIM_STATUSES,
    is_verified,
    rollup_claim_status,
    status_materiality,
)


def _drift(
    *,
    total: int = 3,
    orphan: int = 0,
    approximate: int = 0,
    orphan_tokens: list[str] | None = None,
) -> ReportDrift:
    return ReportDrift(
        total_dollar_amounts=total,
        unmatched_count=orphan,
        approximate_count=approximate,
        orphan_count=orphan,
        orphan_tokens=orphan_tokens
        if orphan_tokens is not None
        else ([] if not orphan else ["$9.99"]),
    )


# ---------------------------------------------------------------------------
# The vocabulary itself
# ---------------------------------------------------------------------------


def test_empty_rollup_is_unknown_not_grounded() -> None:
    """'No section reported a status' means the check did not run — returning the clean
    state for an unrun check is the inversion this vocabulary exists to prevent."""
    assert rollup_claim_status([]) == "unknown"
    assert overall_claim_status([]) == "unknown"


def test_worst_wins_precedence() -> None:
    assert rollup_claim_status(["grounded", "approximate"]) == "approximate"
    assert rollup_claim_status(["inconclusive", "unknown"]) == "inconclusive"
    assert rollup_claim_status(["unknown", "unsupported"]) == "unsupported"
    assert rollup_claim_status(["grounded", "unknown", "approximate"]) == "approximate"


def test_a_rounded_real_figure_outranks_no_figure_at_all() -> None:
    """The one ordering worth arguing about, pinned deliberately.

    ``approximate`` means every cited amount traced to a computed value (at rounding
    precision) — the numbers are real. ``inconclusive`` means nothing checkable was
    cited at all. A report whose figures are traceable-but-rounded stands better than
    one whose prose carries no figures, so ``approximate`` wins the rollup; reversing
    this would make unquantified rhetoric the cleaner state.
    """
    assert rollup_claim_status(["approximate", "inconclusive"]) == "approximate"


def test_unknown_never_outranks_a_content_finding() -> None:
    """A report whose evidence could not be assembled must not look cleaner than one
    whose prose simply cites nothing."""
    for content_status in ("inconclusive", "approximate", "unsupported"):
        assert rollup_claim_status([content_status, "unknown"]) == content_status


@pytest.mark.parametrize("status", CLAIM_STATUSES)
def test_every_declared_status_has_a_precedence_and_is_its_own_rollup(status: str) -> None:
    """Closes the vocabulary against the precedence table: a status added to the
    Literal but not to the table would raise here rather than silently rank."""
    assert rollup_claim_status([status]) == status  # type: ignore[list-item]
    assert rollup_claim_status([status, "grounded"]) == status  # type: ignore[list-item]


def test_is_verified_excludes_the_unmeasured_and_the_empty() -> None:
    """``status != 'unsupported'`` would call both of these verified — the spelling this
    helper exists to replace."""
    assert is_verified("grounded") is True
    assert is_verified("approximate") is True
    assert is_verified("unknown") is False
    assert is_verified("inconclusive") is False
    assert is_verified("unsupported") is False


def test_weak_results_are_inconclusive_never_refuted() -> None:
    assert status_materiality("grounded") == "supported"
    assert status_materiality("approximate") == "supported"
    assert status_materiality("unsupported") == "refuted"
    assert status_materiality("inconclusive") == "inconclusive"
    assert status_materiality("unknown") == "inconclusive"


# ---------------------------------------------------------------------------
# The anchor: drift verdict -> status
# ---------------------------------------------------------------------------


def test_missing_evidence_yields_unknown_even_when_everything_looks_orphaned() -> None:
    """The load-bearing case. With an empty leaf registry every citation reports as
    unmatched; calling that 'unsupported' would blame the report for a check that never
    ran."""
    drift = _drift(total=4, orphan=4, orphan_tokens=["$1.00", "$2.00"])
    assert anchor_claim_status(drift, evidence_available=False) == "unknown"
    assert anchor_claim_status(drift, evidence_available=True) == "unsupported"


def test_orphans_are_unsupported() -> None:
    assert anchor_claim_status(_drift(orphan=1), evidence_available=True) == "unsupported"


def test_no_citations_is_inconclusive_not_grounded() -> None:
    assert anchor_claim_status(_drift(total=0), evidence_available=True) == "inconclusive"


def test_roundings_are_approximate_not_grounded() -> None:
    assert anchor_claim_status(_drift(approximate=2), evidence_available=True) == "approximate"


def test_clean_section_is_grounded() -> None:
    assert anchor_claim_status(_drift(), evidence_available=True) == "grounded"


def test_orphans_outrank_roundings() -> None:
    """A section with both an unverifiable figure and a rounding is unsupported: the
    stronger signal wins, so the rounding does not soften it."""
    assert (
        anchor_claim_status(_drift(orphan=1, approximate=3), evidence_available=True)
        == "unsupported"
    )


# ---------------------------------------------------------------------------
# The note: what a report says about a non-clean section
# ---------------------------------------------------------------------------


def test_grounded_sections_stay_silent() -> None:
    """A clean section adding a line to the warnings channel would train readers to skip
    the channel."""
    assert claim_status_note("grounded", _drift()) is None


def test_notes_name_the_reason_and_the_evidence() -> None:
    unsupported = claim_status_note(
        "unsupported", _drift(orphan=2, orphan_tokens=["$9.99", "$8.88"])
    )
    assert unsupported is not None
    assert "2 cited amount(s)" in unsupported
    assert "$9.99" in unsupported

    assert "unmeasured" in (claim_status_note("unknown", _drift()) or "")
    assert "no checkable figure" in (claim_status_note("inconclusive", _drift(total=0)) or "")
    assert "roundings" in (claim_status_note("approximate", _drift(approximate=1)) or "")


def test_long_orphan_lists_are_truncated_with_a_remainder_count() -> None:
    tokens = [f"${index}.00" for index in range(9)]
    note = claim_status_note("unsupported", _drift(orphan=9, orphan_tokens=tokens))
    assert note is not None
    assert "$4.00" in note
    assert "$5.00" not in note
    assert "(+4 more)" in note
