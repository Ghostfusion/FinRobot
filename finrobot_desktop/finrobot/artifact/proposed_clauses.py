"""Proposed output-contract clauses — the PROMOTION STAGING AREA for the gate.

Nothing in the run path imports this module. ``contract.py``'s
``CONTRACT_CLAUSES`` is untouched, so the live persist gate
(``enforce_artifact_contract`` at ``runner.py``) behaves exactly as before; these
clauses are exercised only by ``scripts/scan_artifact_contract.py --proposed`` and
by the fixtures in ``tests/artifact/``. Promotion is a separate, reviewable diff
that appends them to ``CONTRACT_CLAUSES`` — see
``docs/REPORT_INVARIANT_CLOSURE_DESIGN.md`` §7 (quantify before promoting) and §9
(the locked decisions).

Same doctrine as ``contract.py``: pure ``check(artifact) -> Finding | None``, zero
I/O, no ``compute/`` / ``data/`` / ``pipelines/`` imports, no bare calibrated
threshold literal (structural zeros such as "a price must be positive" are
commented as such), and a violation never raises — a clause that raises would
blank the run.

The catch list quoted in each docstring is MEASURED over the stored corpus
(``~/.finrobot/artifacts.db``, 2026-10-14, read-only) per §7.5; the store is live,
so each is an as-of count with its span.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from finrobot.artifact.contract import ContractClause
from finrobot.engine.models.numeric_claim import Finding

if TYPE_CHECKING:
    from finrobot.artifact.models import Artifact

# The disclosures that assert "there was no second opinion". C6 (live) matches the
# same phrasings; C6b below compares them against the cross-checks the payload
# actually prints.
_NO_CROSS_CHECK_PHRASES = ("no cross-check", "no cross-validation")

#: The only two directions that make a claim about price. A HOLD claims no side,
#: so a band that sits entirely below the tape cannot contradict it.
_DIRECTIONAL_VERDICTS = ("BUY", "SELL")


def _structured(artifact: "Artifact") -> dict[str, Any]:
    structured = artifact.outputs.structured
    return structured if isinstance(structured, dict) else {}


def _synthesis(structured: dict[str, Any]) -> dict[str, Any]:
    synthesis = structured.get("valuation_synthesis")
    return synthesis if isinstance(synthesis, dict) else {}


def _cross_checks(synthesis: dict[str, Any]) -> list[dict[str, Any]]:
    checks = synthesis.get("cross_checks")
    if not isinstance(checks, list):
        return []
    return [c for c in checks if isinstance(c, dict)]


def _bounds(check: dict[str, Any]) -> tuple[float, float, float] | None:
    """(low, mid, high) as floats, or None when any leg is missing/non-numeric."""
    legs: list[float] = []
    for key in ("low", "mid", "high"):
        value = check.get(key)
        if not isinstance(value, int | float) or isinstance(value, bool):
            return None
        legs.append(float(value))
    return legs[0], legs[1], legs[2]


def _band_label(check: dict[str, Any]) -> str:
    return str(check.get("name") or check.get("label") or "cross-check")


def _is_usable(check: dict[str, Any]) -> bool:
    """A band C9 has already rejected is not evidence, so C8 must not read it."""
    bounds = _bounds(check)
    if bounds is None:
        return False
    low, mid, high = bounds
    # Structural, not calibrated: a fundamental band for a positive-price equity
    # cannot start at or below zero, or be empty/inverted.
    return low > 0 and high > low and low <= mid <= high


def _clause_c8_verdict_vs_cross_checks(artifact: "Artifact") -> Finding | None:
    """H — the directional verdict may not contradict the report's OWN published
    cross-checks.

    The gap this closes: no live clause reads ``cross_checks`` against the
    direction, so an artifact can print a band entirely the other side of the tape
    and still ship its call. A band that BRACKETS the price claims no side; one
    corroborating check pointing the same way vetoes the violation; a single
    uncorroborated contradicting band is enough (measured: every corpus instance
    carries exactly one cross-check entry, so an ">=2 must agree" guard would have
    fired on none of them). Unusable bands (C9's) are not read.

    MEASURED CATCH LIST 8 — HMY x3 (`…00:07:54`, `…16:34:07`, `…16:38:42`), NFLX
    (`…00:16:20`), SKM (`…16:44:09`), THC x2 (`…16:31:36`, `…20:27:40`), UTHR
    (`…06:06:44`); each prints a BUY whose only band sits below the tape.
    """
    structured = _structured(artifact)
    thesis = structured.get("thesis")
    synthesis = _synthesis(structured)
    if not isinstance(thesis, dict):
        return None
    recommendation = thesis.get("recommendation")
    if recommendation not in _DIRECTIONAL_VERDICTS:
        return None
    price = synthesis.get("current_price")
    if not isinstance(price, int | float) or isinstance(price, bool) or price <= 0:
        return None
    checks = [c for c in _cross_checks(synthesis) if _is_usable(c)]
    if not checks:
        return None

    contradicting: list[str] = []
    for check in checks:
        bounds = _bounds(check)
        if bounds is None:  # pragma: no cover — _is_usable already rejected these
            continue
        low, mid, high = bounds
        if low <= price <= high:
            return None  # a band that spans the tape takes no side
        same_side = mid > price if recommendation == "BUY" else mid < price
        if same_side:
            return None  # corroborated: one check pointing the call's way vetoes
        contradicting.append(f"{_band_label(check)} {low:.2f}..{mid:.2f}..{high:.2f}")

    return Finding(
        field_key="thesis.recommendation",
        check="contract_c8_verdict_vs_cross_checks",
        severity="blocked_field",
        evidence=(
            f"{recommendation} at {price:.2f} contradicts every published cross-check "
            f"({'; '.join(contradicting)}) — none brackets the price and none points the "
            f"call's way"
        ),
    )


def _clause_c9_degenerate_band(artifact: "Artifact") -> Finding | None:
    """H — a cross-check that is not evidence must not be published as evidence.

    A fundamental band for a positive-price equity must start above zero, run
    low < high, and be monotone; the payload already carries ``band_break_caveat``
    (``null`` everywhere observed) and this is what should populate it. Claim
    scope: the band entries are dropped, not the headline target.

    MEASURED CATCH LIST 1 — SKM (`…16:44:09`), band `-2.97 .. -1.70 .. -1.23`
    against a $34.42 price. HMY's `1.22 .. 2.55 .. 3.74` is positive, monotone and
    fully sampled, so it is a C8 instance, not a C9 one.
    """
    synthesis = _synthesis(_structured(artifact))
    for check in _cross_checks(synthesis):
        bounds = _bounds(check)
        if bounds is None:
            return Finding(
                field_key="valuation_synthesis.cross_checks",
                check="contract_c9_degenerate_band",
                severity="blocked_field",
                evidence=(
                    f"published cross-check {_band_label(check)!r} is missing a numeric "
                    f"low/mid/high and cannot be read as evidence"
                ),
            )
        low, mid, high = bounds
        problems: list[str] = []
        # Structural, not calibrated — see _is_usable.
        if low <= 0:
            problems.append(f"low {low:.2f} is not positive")
        if high <= low:
            problems.append(f"high {high:.2f} does not exceed low {low:.2f}")
        if not low <= mid <= high:
            problems.append(f"mid {mid:.2f} is outside [{low:.2f}, {high:.2f}]")
        if problems:
            return Finding(
                field_key="valuation_synthesis.cross_checks",
                check="contract_c9_degenerate_band",
                severity="blocked_field",
                evidence=f"published cross-check {_band_label(check)!r} is unusable: "
                + "; ".join(problems),
            )
    return None


def _clause_c11_mirrored_withheld_slot(artifact: "Artifact") -> Finding | None:
    """H — one quantity, one definition.

    ``valuation_withheld`` is written by two independent paths: the report root
    (``outputs.structured.valuation_withheld``) and the synthesis block
    (``…valuation_synthesis.valuation_withheld``). The two writers must use ONE
    convention: either both emit the flag, or neither does — and when both emit it
    the values must be equal.

    Presence parity is the load-bearing half. An earlier predicate read "mirrored
    slots must be equal, or one of them must be ABSENT" and measured zero
    violations, because absence is precisely the shape this defect takes: the root
    writer emits nothing when it is not withholding while the synthesis writer
    always emits a bool, so a consumer reading the omitted slot gets "no opinion"
    where the other says "not withheld". A reader that must know an implicit
    present-else-false convention is the duplication, not the reconciliation.

    MEASURED CATCH LIST 63 of 98 equity artifacts — always the same shape: the
    root key is OMITTED while the synthesis writes ``false``; 32 artifacts agree
    (both write ``true``) and 3 agree (neither writes). Instance B is one of the
    63. The divergence never changed a verdict, which is why no reader caught it.
    """
    structured = _structured(artifact)
    synthesis = _synthesis(structured)
    root_present = "valuation_withheld" in structured
    synthesis_present = "valuation_withheld" in synthesis
    if root_present != synthesis_present:
        if root_present:
            emitter, omitter, value = (
                "outputs.structured",
                "valuation_synthesis",
                structured["valuation_withheld"],
            )
        else:
            emitter, omitter, value = (
                "valuation_synthesis",
                "outputs.structured",
                synthesis["valuation_withheld"],
            )
        return Finding(
            field_key="valuation_withheld",
            check="contract_c11_mirrored_withheld_slot",
            severity="blocked_field",
            evidence=(
                f"two writers of valuation_withheld use different conventions: {emitter} "
                f"emits it ({value!r}) while {omitter} omits the slot entirely — a reader "
                f"of the omitted slot has no opinion where the other states one"
            ),
        )
    if not root_present:
        return None  # neither writer emitted it — one convention, nothing to reconcile
    root = structured["valuation_withheld"]
    emitted_value = synthesis["valuation_withheld"]
    if root == emitted_value:
        return None
    return Finding(
        field_key="valuation_withheld",
        check="contract_c11_mirrored_withheld_slot",
        severity="blocked_field",
        evidence=(
            f"two writers disagree on valuation_withheld: "
            f"outputs.structured={root!r} vs valuation_synthesis={emitted_value!r}"
        ),
    )


def _clause_c6b_note_vs_cross_checks(artifact: "Artifact") -> Finding | None:
    """S — the no-cross-check disclosure must be derived from the evidence, not
    from the method count.

    Live C6 concludes "no cross-validation" from the ABSENCE OF A SECOND METHOD,
    so a single-method report that DOES print a cross-check asserts it had none
    (instance B: *"single method dcf with no cross-validation — band widened"*
    beside `cross_checks[0] = 70.16 … 255.26`). This clause reads the disclosure
    against the printed evidence (count, names, whether any brackets the price) —
    the reading §4.8 says C6's derivation should use. On promotion it REPLACES
    C6's evidence string rather than shipping beside it.

    MEASURED CATCH LIST 27 / 12 tickers, span `…20:52:12` … `…20:27:40` (live: the
    last instance is instance B itself).
    """
    structured = _structured(artifact)
    thesis = structured.get("thesis")
    synthesis = _synthesis(structured)
    if not isinstance(thesis, dict):
        return None
    methods = synthesis.get("methods")
    method_count = len(methods) if isinstance(methods, list) else 0
    checks = _cross_checks(synthesis)
    if method_count >= 2 or not checks:
        return None
    note = " ".join(
        str(synthesis.get(key) or "") for key in ("degradation_note", "confidence_note")
    )
    lowered = note.lower()
    if not any(phrase in lowered for phrase in _NO_CROSS_CHECK_PHRASES):
        return None
    price = synthesis.get("current_price")
    labels = ", ".join(_band_label(c) for c in checks)
    brackets = ""
    if isinstance(price, int | float) and not isinstance(price, bool):
        spans = [c for c in checks if _is_usable(c) and (b := _bounds(c)) and b[0] <= price <= b[2]]
        brackets = (
            f"; {len(spans)} of them brackets the {price:.2f} tape"
            if spans
            else f"; none brackets the {price:.2f} tape"
        )
    return Finding(
        field_key="valuation_synthesis.degradation_note",
        check="contract_c6b_note_vs_cross_checks",
        severity="review",
        evidence=(
            f"the report claims it had no cross-validation while publishing "
            f"{len(checks)} cross-check(s) ({labels}){brackets} — the note is derived from "
            f"the method count, not from the evidence"
        ),
    )


#: The staged clause set. Append to ``contract.CONTRACT_CLAUSES`` to promote —
#: after re-running ``scripts/scan_artifact_contract.py --proposed`` (§7.1).
PROPOSED_CLAUSES: list[ContractClause] = [
    ContractClause(id="C8", severity="H", check=_clause_c8_verdict_vs_cross_checks),
    ContractClause(id="C9", severity="H", check=_clause_c9_degenerate_band),
    ContractClause(id="C11", severity="H", check=_clause_c11_mirrored_withheld_slot),
    ContractClause(id="C6b", severity="S", check=_clause_c6b_note_vs_cross_checks),
]
