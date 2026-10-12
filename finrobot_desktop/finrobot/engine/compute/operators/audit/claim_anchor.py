"""Claim-status anchor — name a section's numeric standing from the drift verdict.

``report_drift`` already answers the hard question (which monetary citations match a
computed value, which are roundings, which match nothing) and
``narrative_numeric_grounding`` answers the other one (does a paragraph cite any figure
at all). Both report in their own vocabulary; neither states what a *reader* needs,
which is a single name for where a section's numbers stand. This module is that
translation, and it is deliberately the only thing it does — the bands, tolerances and
token matching stay in ``report_drift`` so there is still exactly one definition of
"does this number match" in the tree.

The two rules it enforces, both of which are about not over-claiming:

* **Evidence first.** If the leaf registry was empty, every citation looks unmatched —
  and reporting ``unsupported`` for all of them would turn a broken *check* into an
  accusation against the report. Unmeasurable evidence yields ``unknown``, and the
  orphan counters are then never consulted.
* **No figures is not the same as no problem.** A section that cites nothing is
  ``inconclusive``, never ``grounded`` — the shipped GOOGL/MSFT/KO defect was exactly
  unquantified, verdict-only rhetoric passing an all-green numeric audit.

Leaf layer (ADR-0005): pure, no I/O.
"""

from __future__ import annotations

from finrobot.engine.compute.operators.report_drift import ReportDrift
from finrobot.engine.models.claim_status import ClaimStatus, rollup_claim_status

__all__ = ["anchor_claim_status", "claim_status_note", "overall_claim_status"]


def anchor_claim_status(drift: ReportDrift, *, evidence_available: bool) -> ClaimStatus:
    """Translate one ``ReportDrift`` verdict into the closed claim-status vocabulary.

    Args:
        drift: The detector verdict for one section (or one report text).
        evidence_available: Whether the run assembled any computed leaves at all. When
            false the comparison was impossible, so no citation can be called
            unsupported on this evidence.

    Returns:
        A :data:`~finrobot.engine.models.claim_status.ClaimStatus`.
    """
    if not evidence_available:
        # Checked BEFORE the counters: with an empty leaf registry every citation
        # reports as unmatched, and reading that as "unsupported" would blame the
        # report for a check that never ran.
        return "unknown"
    if drift.orphan_count > 0:
        return "unsupported"
    if drift.total_dollar_amounts == 0:
        return "inconclusive"
    if drift.approximate_count > 0:
        return "approximate"
    return "grounded"


def overall_claim_status(statuses: list[ClaimStatus]) -> ClaimStatus:
    """Report-level status from per-section ones (worst wins).

    Thin pass-through to :func:`~finrobot.engine.models.claim_status.rollup_claim_status`
    so a caller holding a ``ReportDrift`` pipeline does not have to import the vocabulary
    module to close the loop.
    """
    return rollup_claim_status(statuses)


def claim_status_note(status: ClaimStatus, drift: ReportDrift) -> str | None:
    """One human sentence naming the status and its evidence, or ``None`` for a clean
    section.

    ``None`` for ``grounded`` on purpose: a report whose numbers all trace to a
    computation should not carry a line saying so, or every clean section would add
    noise to the warnings channel and the real ones would stop being read.
    """
    if status == "grounded":
        return None
    if status == "unknown":
        return (
            "numeric standing unmeasured: no computed values were available to check "
            f"the {drift.total_dollar_amounts} cited amount(s) against"
        )
    if status == "inconclusive":
        return "no checkable figure cited in this section (unquantified prose)"
    if status == "approximate":
        return (
            f"{drift.approximate_count} cited amount(s) are roundings of a computed "
            f"value rather than exact matches"
        )
    tokens = ", ".join(drift.orphan_tokens[:5])
    more = f" (+{len(drift.orphan_tokens) - 5} more)" if len(drift.orphan_tokens) > 5 else ""
    return f"{drift.orphan_count} cited amount(s) match no computed value: {tokens}{more}"
