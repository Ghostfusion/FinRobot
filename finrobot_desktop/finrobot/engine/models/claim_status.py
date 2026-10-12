"""Claim-status vocabulary — a closed set of verdicts for a section's numbers.

FinRobot already detects the hard cases: ``report_drift`` classifies every monetary
token in a narrative against the computed leaf registry (matched / within the
approximation band / orphan), and ``audit_narrative_numeric_grounding`` catches a
paragraph that cites no figure at all. What was missing is a *name* for the outcome —
each detector reported in its own vocabulary (a warning string here, a token list
there), so nothing downstream could state, or count, what a section's numeric standing
actually was. This module supplies that name and nothing else: it computes no
tolerance, matches no token, and owns no threshold. The bands belong to
``report_drift``; this is the vocabulary they are reported in.

Borrowed from a sibling system's report verifier, which publishes
``GROUNDED / UNSUPPORTED / CONTRADICTED / MISQUOTED / INTERNAL_CONFLICT`` per claim and
never lets a missing verdict read as a pass. Adapted to what FinRobot can actually
*witness*: states no detector can reach are not declared, because a vocabulary with
unreachable members is a promise the code does not keep. Three of the sibling's
semantics are kept verbatim because they are the ones that were hard-won:

1. **A weak or absent result is INCONCLUSIVE, never a refutation.** "We could not
   measure it" and "we measured it and it failed" are different statements, and
   collapsing them is how an unquantified section gets read as a clean one.
2. **Unknown is a state, not a pass.** Evidence that could not be assembled leaves the
   claim ``unknown``; it never falls back to ``grounded``, and ``unknown`` is never the
   best status in a rollup.
3. **Nothing here refuses a verdict.** A status annotates a report; it does not gate
   the rating, the target or the confidence (the same contract the narrative backstops
   follow).

Leaf layer (ADR-0005): stdlib only, importable by compute / pipeline / artifact alike.
"""

from __future__ import annotations

from typing import Literal

ClaimStatus = Literal["grounded", "approximate", "unsupported", "inconclusive", "unknown"]
"""How one section's numbers stand.

``grounded``      every monetary citation matched a computed value within the tight band
``approximate``   no unverifiable citation, but at least one is a legitimate rounding
                  (inside the approximation band) — printed as such, never silently
                  promoted to ``grounded``
``unsupported``   at least one citation matched no computed value: the fabrication class
``inconclusive``  the section cites no checkable figure at all — the defect the grounding
                  audit exists for (unquantified, verdict-only rhetoric)
``unknown``       the check could not be run (no evidence leaves were assembled), so the
                  section's standing is *unmeasured*
"""

Materiality = Literal["supported", "refuted", "inconclusive"]
"""The three-way reading of a status, for callers that must state an outcome. A weak or
unmeasured result is ``inconclusive`` — never ``refuted``, and never a silent
``supported``."""

#: Precedence for :func:`rollup_claim_status`. Higher = stronger signal, and the
#: ordering is deliberate: an unverifiable figure outranks a rounded one, which outranks
#: a section with no figures at all, which outranks "we could not check". The last
#: placement matters — ``unknown`` must never out-rank a *content* finding, or a report
#: with a broken evidence set would look cleaner than one whose prose simply cites
#: nothing.
_PRECEDENCE: dict[ClaimStatus, int] = {
    "unsupported": 4,
    "approximate": 3,
    "inconclusive": 2,
    "unknown": 1,
    "grounded": 0,
}

_MATERIALITY: dict[ClaimStatus, Materiality] = {
    "grounded": "supported",
    "approximate": "supported",
    "unsupported": "refuted",
    "inconclusive": "inconclusive",
    "unknown": "inconclusive",
}


def rollup_claim_status(statuses: list[ClaimStatus]) -> ClaimStatus:
    """Reduce per-section statuses to one report-level status (worst wins).

    An **empty** list is ``unknown``, not ``grounded``: "no section reported a status"
    means the check did not run, and returning the clean state for an unrun check is the
    exact inversion this module exists to prevent.
    """
    if not statuses:
        return "unknown"
    return max(statuses, key=lambda status: _PRECEDENCE[status])


def status_materiality(status: ClaimStatus) -> Materiality:
    """Map a status to the three-way outcome a caller states in prose."""
    return _MATERIALITY[status]


def is_verified(status: ClaimStatus) -> bool:
    """True only for the statuses that assert every citation was checked and matched.

    Callers must use this rather than ``status != "unsupported"``: that spelling would
    treat ``unknown`` (unmeasured) and ``inconclusive`` (nothing cited) as verified.
    """
    return status in ("grounded", "approximate")


CLAIM_STATUS_DEFINITION_VERSION = "1"
"""Version of the *meanings* above. Bump it when a status starts to mean something
different (e.g. a band moves), not when a status is added — the number exists so a
status recorded in an old artifact can be read against the definition that produced it."""

CLAIM_STATUSES: tuple[ClaimStatus, ...] = (
    "grounded",
    "approximate",
    "unsupported",
    "inconclusive",
    "unknown",
)
"""Every status, in vocabulary order. Exposed so a caller (or a gate) can iterate the
closed set instead of re-listing it and drifting."""
