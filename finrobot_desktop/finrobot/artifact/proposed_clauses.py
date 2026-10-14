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

STAGED SEVERITY. ``C6b``/``C8``/``C9``/``C11`` carry the severity §9 locks for
them. The ``C10``/``C12``/``C14`` families are staged ``S``/annotate even though
§9 locks them ``H``, because their locked shape is not a per-artifact veto: `C10`
and `C12` are count-thresholded (``error_if`` when the offending figure was
PUBLISHED, ``warn_if`` when it only populated a catalogue or a display field), and
`C14`'s locked remediation is "delete the sentence, never rewrite it" — which
``enforce_artifact_contract`` cannot do, since it withholds VALUES and stamps the
narrative rather than editing prose. Those mechanisms arrive with
``ContractClause.warn_if``/``error_if`` (§9.2). Arming ``H`` before them would
withhold a headline for a defect whose locked remediation is not a withhold, so
each docstring says what its promotion still needs.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
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


# ── readers the C10–C14 clauses share ────────────────────────────────────────

#: (numerator, ratio) pairs whose ratio cannot mean anything without its
#: numerator. Structural, not calibrated: a margin IS numerator / revenue, so a
#: published margin with a null numerator is a number nobody can check, re-derive
#: or replay.
_RATIO_OPERANDS: tuple[tuple[str, str], ...] = (
    ("operating_income", "operating_margin"),
    ("revenue", "gross_margin"),
    ("ebitda", "ebitda_margin"),
)

#: (left operand, right operand, ratio) — the conclusion ratios whose two sides
#: must come from ONE provider and period. Structural: a ratio of two providers'
#: figures is a caliber mix, not a measurement of either.
_OPERAND_PAIRS: tuple[tuple[str, str, str], ...] = (
    ("revenue", "operating_income", "operating_margin"),
    ("revenue", "ebitda", "ev_ebitda"),
    ("net_income", "operating_income", "net_income_vs_operating_income"),
)

#: The three us-gaap tags the ``Assets − Liabilities = equity`` identity needs.
#: The snapshot keeps them as independent leaves, which is exactly why the
#: identity has to be recorded rather than left to whoever reads them next.
_IDENTITY_TAGS: tuple[str, ...] = (
    "us-gaap:Assets",
    "us-gaap:Liabilities",
    "us-gaap:StockholdersEquity",
)

#: The identity record's own arithmetic. A float-representation tolerance, NOT a
#: calibrated band — the components round-trip through JSON at full precision, so
#: anything past float noise is a real inconsistency.
_IDENTITY_EPS = 1e-6

#: Direction words attached to an insider-flow amount (boolean = the word claims
#: a positive flow). Vocabulary, not a threshold — the same shape C6's disclosure
#: phrases already use.
_FLOW_WORDS: tuple[tuple[str, bool], ...] = (
    ("net seller", False),
    ("net buyer", True),
    ("net sell", False),
    ("net buy", True),
)

#: The producer's placeholder for a prose amount the withheld-target scrubber
#: removed (``equity_research._reconcile_narrative_targets``).
_PLACEHOLDER = "[target withheld]"

#: A sentence that names an insider-flow quantity is the one whose amount the
#: scrubber must not have taken: the flow is a PUBLISHED leaf, so washing it out
#: leaves the sentence asserting a figure the report prints elsewhere.
_FLOW_CUES = ("insider", "open-market", "net seller", "net buyer")

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def _raw(artifact: "Artifact") -> dict[str, Any]:
    raw = artifact.inputs.raw_data
    return raw if isinstance(raw, dict) else {}


def _num(value: Any) -> float | None:
    """A float for a real number, None for anything else — bool is NOT a number."""
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return float(value)


def _decisions(raw: dict[str, Any]) -> list[dict[str, Any]]:
    authority = raw.get("data_authority")
    if not isinstance(authority, dict):
        return []
    decisions = authority.get("decisions")
    if not isinstance(decisions, list):
        return []
    return [d for d in decisions if isinstance(d, dict)]


def _fact_value(entries: Any) -> float | None:
    """The numeric value of an XBRL snapshot leaf (a list of fact entries)."""
    if not isinstance(entries, list):
        return None
    for entry in entries:
        if isinstance(entry, dict):
            value = _num(entry.get("value"))
            if value is not None:
                return value
    return None


def _fact_entries(snapshot: dict[str, Any]) -> Iterator[tuple[str, dict[str, Any]]]:
    """(tag, entry) for every fact in the snapshot, ``_``-prefixed keys included —
    the staleness annotation lives on ordinary facts, the identity record on a
    ``_``-prefixed one."""
    for tag, entries in snapshot.items():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if isinstance(entry, dict):
                yield tag, entry


def _sentences(text: str) -> list[str]:
    return [part for part in _SENTENCE_SPLIT_RE.split(text) if part.strip()]


def _iter_text(value: Any) -> Iterator[str]:
    if isinstance(value, str):
        if value:
            yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _iter_text(item)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_text(item)


def _prose_strings(structured: dict[str, Any]) -> Iterator[tuple[str, str]]:
    """(field path, text) for every analyst-facing string §4.7 names: the thesis
    prose, its catalyst/risk bullets, the summary, and ``llm_narrative``."""
    thesis = structured.get("thesis")
    thesis = thesis if isinstance(thesis, dict) else {}
    for key in ("narrative", "tagline", "price_target_basis"):
        value = thesis.get(key)
        if isinstance(value, str) and value:
            yield f"thesis.{key}", value
    for list_key in ("catalysts", "risks"):
        items = thesis.get(list_key)
        if not isinstance(items, list):
            continue
        for index, item in enumerate(items):
            for text in _iter_text(item):
                yield f"thesis.{list_key}[{index}]", text
    summary = structured.get("summary_text")
    if isinstance(summary, str) and summary:
        yield "summary_text", summary
    narrative = structured.get("llm_narrative")
    if isinstance(narrative, dict):
        for key, value in narrative.items():
            for text in _iter_text(value):
                yield f"llm_narrative.{key}", text


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

    MEASURED CATCH LIST 7 — HMY x3 (`…00:07:54`, `…16:34:07`, `…16:38:42`), NFLX
    (`…00:16:20`), THC x2 (`…16:31:36`, `…20:27:40`), UTHR (`…06:06:44`); each
    prints a BUY whose only band sits below the tape. SKM is the eighth artifact
    the design names and it is NOT here: its band is `-2.97 .. -1.23`, which
    ``_is_usable`` rejects, so ``C9`` owns it. The two clauses cover §1.1's list
    only as a pair.
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

    MEASURED CATCH LIST 63 — and the population makes the mechanism plain. The
    root writer emits the flag ONLY on the withheld path; the synthesis writer
    ALWAYS emits a bool:

        root absent + synthesis false    63   every non-withheld artifact
        root true   + synthesis true     32   every withheld artifact
        root absent + synthesis absent    8
        root true   + synthesis absent    2

    So this clause is not catching an anomaly: it is flagging the NORMAL case
    (nothing was withheld), because one of the two writers is conditional on the
    very outcome it reports. Instance B is one of the 63. The divergence never
    changed a verdict, which is why no reader caught it.

    UNIFY, THEN PROMOTE. Arming `H` before the root writer emits on both paths
    would withhold the headline on every non-withheld report — that is, on every
    ordinary one. And after the unification the STORED corpus still reads 63: the
    archive is annotated on read, never rewritten (§9.3), so this clause's
    promotion criterion is not "the scanner reports 0" but "the catch list's SPAN
    HAS CLOSED — no instance after the writer fix". That is the general rule for
    every clause whose defect class a shipped fix already closed (`C10a` and
    `C10c` likewise: their spans end at 16:44 and 19:59). The end state is a
    single writer, and what remains for this clause is regression — catching a
    second writer re-introduced.

    Scope: a mirrored pair cannot diverge when one side does not exist for the
    artifact type, so an artifact with no synthesis block (a plain ddm/dcf dump) is
    out of scope. An earlier revision counted the 2 such artifacts and read 65.
    """
    structured = _structured(artifact)
    synthesis = structured.get("valuation_synthesis")
    if not isinstance(synthesis, dict):
        return None  # no synthesis block for this artifact type — no pair to mirror
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


def _clause_c10a_ratio_without_numerator(artifact: "Artifact") -> Finding | None:
    """S — §4.3(a), numerator presence: a published ratio must have both operands.

    A margin whose numerator is null is a number nobody can check, re-derive or
    replay; the report states a precision it cannot support. §4.3 locks `C10` at
    `H` / claim scope / count-thresholded, and this is the predicate that
    decision is about — staged `S` because arming it as a per-artifact `H` veto is
    NOT the locked shape (the lock wants `error_if` for a published ratio and
    `warn_if` for a display-only one, and those count fields do not exist yet,
    §9.2). Promote together with that field, not before it.

    MEASURED CATCH LIST 72 / 25 tickers, span `…10-10T21:58` … `…10-14T16:44:09`
    — HISTORICAL: the newest instance is 16:44 and the margin paths now withhold
    (`yfinance_provider` emits `withheld_no_operating_income_row`), so the
    clause's value is regression protection, not a live withhold.
    """
    income = _raw(artifact).get("income")
    if not isinstance(income, dict):
        return None
    for numerator, ratio in _RATIO_OPERANDS:
        value = _num(income.get(ratio))
        if value is None or income.get(numerator) is not None:
            continue
        return Finding(
            field_key=f"income.{ratio}",
            check="contract_c10a_ratio_without_numerator",
            severity="review",
            evidence=(
                f"income.{ratio} = {value:.5f} is published while its numerator "
                f"income.{numerator} is null — the ratio is a conclusion with no "
                f"operand pair, so no reader can verify or replay it"
            ),
        )
    return None


def _clause_c10b_cross_provider_operands(artifact: "Artifact") -> Finding | None:
    """S — §4.3(a), same-source half: a conclusion ratio may not mix providers.

    Two operands selected from different sources are a caliber mix dressed as a
    measurement. The clause reads the resolved `selected_source` per metric (the
    data layer's decision record), not the raw provider payloads.

    MEASURED CATCH LIST 0 — every artifact with decisions selects ONE source
    (36 yfinance, 4 eodhd; 65 artifacts carry no decisions at all). No ratio pair
    crosses sources today, so this is a PREVENTIVE clause: its justification is
    the consistency it would detect, not one it has.
    """
    sources: dict[str, str] = {}
    for decision in _decisions(_raw(artifact)):
        metric, source = decision.get("metric"), decision.get("selected_source")
        if isinstance(metric, str) and isinstance(source, str) and source:
            sources.setdefault(metric, source)
    for left, right, ratio in _OPERAND_PAIRS:
        left_source, right_source = sources.get(left), sources.get(right)
        if left_source and right_source and left_source != right_source:
            return Finding(
                field_key=f"data_authority.decisions[{ratio}]",
                check="contract_c10b_cross_provider_operands",
                severity="review",
                evidence=(
                    f"{ratio} is published from operands selected out of different "
                    f"sources — {left} from {left_source!r} vs {right} from "
                    f"{right_source!r} — so the ratio mixes two calibers"
                ),
            )
    return None


def _clause_c10c_equity_identity_unrecorded(artifact: "Artifact") -> Finding | None:
    """S — §4.3(b): the balance-sheet identity must be recorded, and must hold.

    ``Assets − Liabilities = total equity`` is computable whenever the three tags
    are present, yet the identity is hand-written on one operator path rather than
    published as a claim. Two readings, one clause: the identity is computable but
    was never recorded (the model is then free to state "assets against $X of
    liabilities, leaving $Y of equity", which is WRONG for any issuer carrying a
    noncontrolling interest), or it was recorded and its own arithmetic does not
    close. Staged `S` for the same §9.2 reason as `C10a`.

    MEASURED CATCH LIST 73 / 24 tickers, span `…10-10T21:45` … `…10-14T19:59:27`
    — HISTORICAL: `xbrl_aligned_comps._equity_identity_note` records it
    unconditionally on its three inputs as of the newest build, and the 3
    artifacts produced since (all THC, 20:27 / 20:37 / 21:12) all carry it. The
    "computable but unrecorded" population is therefore pre-fix.

    The recorded case is checked, never re-derived: the clause compares the
    record's own components, it does not recompute the model's equity.
    """
    snapshot = _structured(artifact).get("xbrl_facts_snapshot")
    if not isinstance(snapshot, dict):
        return None
    identity = snapshot.get("_equity_identity")
    record = identity[0] if isinstance(identity, list) and identity else None
    if isinstance(record, dict):
        assets = _num(record.get("assets"))
        liabilities = _num(record.get("liabilities"))
        total = _num(record.get("total_equity"))
        parent = _num(record.get("parent_stockholders_equity"))
        nci = _num(record.get("noncontrolling_interest"))
        if assets is None or liabilities is None or total is None:
            return Finding(
                field_key="xbrl_facts_snapshot._equity_identity",
                check="contract_c10c_equity_identity_unrecorded",
                severity="review",
                evidence=(
                    "the equity identity is recorded without the components that "
                    "make it checkable (assets / liabilities / total_equity) — a "
                    "claim no reader can verify"
                ),
            )
        if parent is None or nci is None:
            return Finding(
                field_key="xbrl_facts_snapshot._equity_identity",
                check="contract_c10c_equity_identity_unrecorded",
                severity="review",
                evidence=(
                    "the equity identity is recorded without the parent / "
                    "noncontrolling-interest split, so the identity cannot "
                    "distinguish total from parent equity"
                ),
            )
        scale = max(1.0, abs(assets), abs(total))
        if abs((assets - liabilities) - total) > _IDENTITY_EPS * scale:
            return Finding(
                field_key="xbrl_facts_snapshot._equity_identity",
                check="contract_c10c_equity_identity_unrecorded",
                severity="review",
                evidence=(
                    f"the recorded equity identity does not close: assets "
                    f"{assets:,.0f} − liabilities {liabilities:,.0f} = "
                    f"{assets - liabilities:,.0f} but total equity is "
                    f"{total:,.0f}"
                ),
            )
        if abs((parent + nci) - total) > _IDENTITY_EPS * scale:
            return Finding(
                field_key="xbrl_facts_snapshot._equity_identity",
                check="contract_c10c_equity_identity_unrecorded",
                severity="review",
                evidence=(
                    f"the recorded equity identity does not close: parent "
                    f"{parent:,.0f} + noncontrolling interest {nci:,.0f} = "
                    f"{parent + nci:,.0f} but total equity is {total:,.0f}"
                ),
            )
        return None

    present = [tag for tag in _IDENTITY_TAGS if _fact_value(snapshot.get(tag)) is not None]
    if len(present) != len(_IDENTITY_TAGS):
        return None
    return Finding(
        field_key="xbrl_facts_snapshot._equity_identity",
        check="contract_c10c_equity_identity_unrecorded",
        severity="review",
        evidence=(
            f"{', '.join(_IDENTITY_TAGS)} are all present, so Assets − Liabilities "
            f"is computable, but the identity is not recorded — any prose that "
            f"subtracts the two leaves is then uncheckable against a published "
            f"claim (and wrong wherever a noncontrolling interest exists)"
        ),
    )


def _clause_c10d_caliber_divergent_accepted(artifact: "Artifact") -> Finding | None:
    """S — §4.3(a), caliber half: an ACCEPTED decision whose comparison is
    ``caliber_divergent`` publishes a ratio on operands measured on different
    calibers. The remediation the design names is to withhold the ratio with
    ``basis="caliber_mismatch"``; until that path exists the clause reports the
    count, which is the input §9.2's `error_if`/`warn_if` fields threshold on.

    MEASURED CATCH LIST 102 accepted caliber-divergent decision rows over 35
    artifacts / 18 tickers, span `…10-13T22:53` … `…10-14T21:12:35` — LIVE. The
    count is in the evidence for exactly that reason.
    """
    offenders: list[str] = []
    for decision in _decisions(_raw(artifact)):
        if decision.get("comparability") != "caliber_divergent":
            continue
        if decision.get("status") != "accepted":
            continue
        metric = decision.get("metric")
        source = decision.get("selected_source")
        offenders.append(f"{metric} ({source})")
    if not offenders:
        return None
    return Finding(
        field_key="data_authority.decisions",
        check="contract_c10d_caliber_divergent_accepted",
        severity="review",
        evidence=(
            f"{len(offenders)} decision(s) were accepted while their comparison is "
            f"caliber_divergent — {', '.join(offenders)} — so the ratios built on "
            f"them are published on operands of different calibers without a "
            f"caliber_mismatch basis"
        ),
    )


def _clause_c12a_stale_8k_index(artifact: "Artifact") -> Finding | None:
    """S — §4.5, recency: the artifact's own staleness disclosure becomes a gate.

    The catalyst chapter already compares the SEC 8-K index against the news
    window and writes ``sec_8k_staleness_warning`` when the index is older; today
    nothing consumes it, so a report can print "the 8-K index is stale" beside a
    catalyst read built on it. Reading the artifact's own admission is the same
    shape `C4` already uses for ``numeric_audit`` findings — the clause verifies
    the result, it does not re-derive the comparison (the claimed window lives in
    the producer's policy, not in the payload).

    MEASURED CATCH LIST 10 / 5 tickers, span `…10-14T06:21` … `…10-14T21:12:35`
    — LIVE, and the payload already carries the disclosure in two shapes.
    """
    catalyst = _structured(artifact).get("catalyst_analysis")
    if not isinstance(catalyst, dict):
        return None
    warning = catalyst.get("sec_8k_staleness_warning")
    if not isinstance(warning, str) or not warning:
        return None
    window = catalyst.get("sec_8k_window")
    window = window if isinstance(window, dict) else {}
    return Finding(
        field_key="catalyst_analysis.sec_8k_staleness_warning",
        check="contract_c12a_stale_8k_index",
        severity="review",
        evidence=(
            f"the artifact discloses that its 8-K index is stale "
            f"({warning!r}; newest filing {window.get('newest')!r}, oldest "
            f"{window.get('oldest')!r}) yet the catalyst read ships on it — the "
            f"disclosure is printed, not acted on"
        ),
    )


def _clause_c12b_empty_news_window(artifact: "Artifact") -> Finding | None:
    """S — §4.5, window closure: an EMPTY window must not carry a populated read.

    ``news_window.count == 0`` with a null provider and no sources means the
    catalyst chapter had nothing to read, yet the artifact still publishes an
    ``overall_sentiment``, a category breakdown and key catalysts. Those fields
    are then ungrounded — the reader cannot tell "no news" from "not loaded".

    MEASURED CATCH LIST 14 / 8 tickers, span `…10-14T00:23` … `…10-14T20:37:52`
    — LIVE, and not THC-specific.
    """
    catalyst = _structured(artifact).get("catalyst_analysis")
    if not isinstance(catalyst, dict):
        return None
    window = catalyst.get("news_window")
    if not isinstance(window, dict) or window.get("count") != 0:
        return None
    sentiment = catalyst.get("overall_sentiment")
    catalysts = catalyst.get("key_catalysts")
    breakdown = catalyst.get("category_breakdown")
    return Finding(
        field_key="catalyst_analysis.news_window",
        check="contract_c12b_empty_news_window",
        severity="review",
        evidence=(
            f"the news window is empty (count 0, provider "
            f"{window.get('provider')!r}, {len(window.get('sources') or [])} sources) "
            f"while the artifact still publishes overall_sentiment="
            f"{sentiment!r} with {len(catalysts or [])} key catalyst(s) and "
            f"{len(breakdown or {})} category bucket(s) — the read is ungrounded"
        ),
    )


def _clause_c12c_stale_fact_published(artifact: "Artifact") -> Finding | None:
    """S — §4.5, dated series: a stale fact must not ship as current fundamentals.

    Zero thresholds, deliberately: the clause reads the producer's OWN staleness
    annotation (``xbrl_aligned_comps._flag_stale_facts`` writes
    ``"stale: latest reported period is X, this fact is Y"`` into the fact's
    ``warning``), so the clause holds no year band and cannot drift from the
    producer's rule. What it adds is the consumer: the annotation was previously
    presentation-only, and an abandoned tag pinned years back could still feed a
    current-fundamentals table looking fresh (EHC's ``us-gaap:OperatingIncomeLoss``
    frozen at 2022-12-31 while every other fact ran to 2026-06-30).

    MEASURED CATCH LIST 15 annotated facts / 6 tickers, span `…10-13T20:18` …
    `…10-14T16:31` — LIVE. A long history is NOT this clause: the 9 artifacts
    whose oldest fact reaches back to 2009–2011 carry no annotation, which is the
    discrimination the producer's one-year rule already makes. The FY2010 class
    §4.5 pins is this same shape and needs per-fact period metadata in the model
    (§6, the ``NumericClaim`` fields) before a clause could judge it without the
    annotation.
    """
    snapshot = _structured(artifact).get("xbrl_facts_snapshot")
    if not isinstance(snapshot, dict):
        return None
    for tag, entry in _fact_entries(snapshot):
        warning = entry.get("warning")
        if isinstance(warning, str) and "stale:" in warning:
            return Finding(
                field_key=f"xbrl_facts_snapshot.{tag}",
                check="contract_c12c_stale_fact_published",
                severity="review",
                evidence=(
                    f"the fact {tag} is annotated as stale and still ships in the "
                    f"current-fundamentals snapshot — {warning!r}"
                ),
            )
    return None


def _clause_c13b_self_centered_monte_carlo(artifact: "Artifact") -> Finding | None:
    """S — §4.6, non-circularity: a distribution centred on the assumptions it
    validates is a sensitivity, not corroboration, and must say so.

    The Monte Carlo perturbs the base-case DCF's own assumptions, so its
    percentiles cannot corroborate the DCF point. ``assumptions_used`` therefore
    publishes ``centered_on`` and ``independent``; the clause fires when a
    declared centering is NOT declared dependent. It reads the declaration, it
    does not judge whether the centering was self-referential — that judgement is
    the producer's, and it is exactly what the two fields record.

    MEASURED CATCH LIST 0 — 48 artifacts declare
    ``centered_on="base-case DCF assumptions"`` WITH ``independent: false``
    (compliant), and 44 pre-fix artifacts declare neither field; the predicate has
    never fired. PREVENTIVE, like `C13c`: its justification is the inconsistency
    it would detect. The 48/44 split §7.1 tabulated is the *declaration rate*
    (adoption of the fields), NOT a catch list — the strict predicate is what
    makes it a gate, and per §7.1 the broader "declares nothing" form would flag
    42% of the catalogue and is over-broad.
    """
    technical = _structured(artifact).get("technical_analysis")
    if not isinstance(technical, dict):
        return None
    monte_carlo = technical.get("monte_carlo")
    if not isinstance(monte_carlo, dict):
        return None
    used = monte_carlo.get("assumptions_used")
    if not isinstance(used, dict):
        return None
    centered = used.get("centered_on")
    if not isinstance(centered, str) or not centered:
        return None
    if used.get("independent") is False:
        return None
    return Finding(
        field_key="technical_analysis.monte_carlo.assumptions_used",
        check="contract_c13b_self_centered_monte_carlo",
        severity="review",
        evidence=(
            f"the Monte Carlo declares centered_on={centered!r} but publishes "
            f"independent={used.get('independent')!r} — a distribution centred on the "
            f"assumptions it would corroborate must declare itself dependent"
        ),
    )


def _clause_c13c_non_independent_corroboration(artifact: "Artifact") -> Finding | None:
    """S — §4.6/§9.4 (locked), the hard case: a non-independent agreement may not
    be the SOLE corroboration for a direction.

    The flag exists in ``data_authority.decisions[].agreement_is_independent`` and
    has no consumer. The clause fires when an accepted decision's agreement is
    declared non-independent and the artifact carries NO independent agreement to
    fall back on — i.e. every corroboration it has is circular.

    MEASURED CATCH LIST 0 — the flag is ``false`` on no row in the corpus.
    PREVENTIVE: §7.1 records it as shipping with no catch list, justified by the
    inconsistency it would detect. This clause is what gives the flag a consumer.
    """
    decisions = _decisions(_raw(artifact))
    accepted = [d for d in decisions if d.get("status") == "accepted"]
    non_independent = [d for d in accepted if d.get("agreement_is_independent") is False]
    if not non_independent:
        return None
    if any(d.get("agreement_is_independent") is True for d in accepted):
        return None
    metrics = ", ".join(str(d.get("metric")) for d in non_independent)
    return Finding(
        field_key="data_authority.decisions",
        check="contract_c13c_non_independent_corroboration",
        severity="review",
        evidence=(
            f"{len(non_independent)} accepted decision(s) declare a non-independent "
            f"agreement ({metrics}) and no accepted decision is independent — the "
            f"artifact's only corroboration is circular"
        ),
    )


def _clause_c14a_direction_vs_sign(artifact: "Artifact") -> Finding | None:
    """S — §4.7: a direction word must agree with the sign of the leaf it names.

    "Net sellers" beside a positive net flow (or "net buyers" beside a negative
    one) is prose contradicting its own datum — the same defect class as the
    reconciled amount that received another metric's number. §4.7 locks the
    remediation at H / claim scope with "delete the sentence, never rewrite it",
    and that remediation has no implementation in the persist gate (``_withhold``
    scrubs target slots and stamps the narrative; it cannot delete a sentence from
    ``thesis.narrative``). Staged `S` until the gate grows sentence-level
    deletion — arming it `H` today would withhold the TARGET for a prose defect,
    which is not the locked remediation.

    MEASURED CATCH LIST 0 — no direction word contradicts its leaf; the shipped
    reconciliation fix holds.
    """
    structured = _structured(artifact)
    governance = structured.get("ownership_governance")
    if not isinstance(governance, dict):
        return None
    net_flow = _num(governance.get("insider_net_flow"))
    if net_flow is None or net_flow == 0:
        return None
    for field, text in _prose_strings(structured):
        lowered = text.lower()
        for word, claims_positive in _FLOW_WORDS:
            if word in lowered and (net_flow > 0) != claims_positive:
                return Finding(
                    field_key=field,
                    check="contract_c14a_direction_vs_sign",
                    severity="review",
                    evidence=(
                        f"{field} says {word!r} while insider_net_flow is "
                        f"{net_flow:,.2f} — the direction word contradicts the sign "
                        f"of the leaf it names"
                    ),
                )
    return None


def _clause_c14b_unresolved_placeholder(artifact: "Artifact") -> Finding | None:
    """S — §4.7: the withheld-target placeholder must not wash a PUBLISHED amount.

    ``equity_research._reconcile_narrative_targets`` replaces a prose amount with
    ``[target withheld]`` when the point target is withheld. That is correct for
    the target and wrong for everything else: the scrubber has taken amounts the
    report publishes elsewhere, leaving the narrative asserting a figure its own
    risk list contradicts (GMED "[target withheld] of open-market purchases" for a
    $0 datum; AFRM "insiders were net sellers of [target withheld]" while
    ``ownership_governance`` carries the flow).

    The predicate is the conjunction the defect needs — the placeholder stands in
    a sentence that also names an insider-flow quantity. The COARSER "token
    anywhere in §4.7's prose" form measures 27 artifacts / 19 tickers / 68
    occurrences and is REJECTED as over-broad by false positive: it fires on the
    legitimate withheld-path disclaimer ("We initiate X at BUY on a directional
    read, not a point estimate"), which is the producer's own honest copy, not a
    defect. §7.1's re-calibrate-first rule applied before promotion.

    MEASURED CATCH LIST 10 / 10 tickers — AFRM, ALL, AMZN, DVN, FOXA, GMED, NFLX,
    PGR, THC, UTHR, span `…10-14T00:*` … `…10-14T19:59` — LIVE. §4.7's locked
    remediation is H / claim scope with sentence deletion, unavailable in the
    persist gate today (see `C14a`), so this is staged `S`.
    """
    structured = _structured(artifact)
    for field, text in _prose_strings(structured):
        for sentence in _sentences(text):
            if _PLACEHOLDER not in sentence:
                continue
            lowered = sentence.lower()
            if not any(cue in lowered for cue in _FLOW_CUES):
                continue
            return Finding(
                field_key=field,
                check="contract_c14b_unresolved_placeholder",
                severity="review",
                evidence=(
                    f"{field} carries {_PLACEHOLDER!r} where an insider-flow amount "
                    f"belongs — the withheld-target scrubber took a figure this "
                    f"report publishes elsewhere: {sentence.strip()[:200]!r}"
                ),
            )
    return None


#: The staged clause set. Append to ``contract.CONTRACT_CLAUSES`` to promote —
#: after re-running ``scripts/scan_artifact_contract.py --proposed`` (§7.1).
PROPOSED_CLAUSES: list[ContractClause] = [
    ContractClause(
        id="C6b",
        severity="S",
        check=_clause_c6b_note_vs_cross_checks,
        title="Disclosure derived from evidence",
        doc="the no-cross-check note must be derived from the cross-checks the payload prints.",
    ),
    ContractClause(
        id="C8",
        severity="H",
        check=_clause_c8_verdict_vs_cross_checks,
        title="Verdict vs published cross-checks",
        doc="a directional verdict may not contradict the report's own published cross-checks.",
    ),
    ContractClause(
        id="C9",
        severity="H",
        check=_clause_c9_degenerate_band,
        title="Cross-check band plausibility",
        doc="a cross-check that is not evidence must not be published as evidence.",
    ),
    ContractClause(
        id="C10a",
        severity="S",
        check=_clause_c10a_ratio_without_numerator,
        title="Ratio without its numerator",
        doc="a published ratio requires both operands to be present.",
    ),
    ContractClause(
        id="C10b",
        severity="S",
        check=_clause_c10b_cross_provider_operands,
        title="Cross-provider operands",
        doc="a conclusion ratio's two operands must come from one source and period.",
    ),
    ContractClause(
        id="C10c",
        severity="S",
        check=_clause_c10c_equity_identity_unrecorded,
        title="Balance-sheet identity",
        doc="Assets − Liabilities = equity must be recorded, and its own arithmetic must close.",
    ),
    ContractClause(
        id="C10d",
        severity="S",
        check=_clause_c10d_caliber_divergent_accepted,
        title="Caliber-divergent accepted decision",
        doc="a ratio may not ship on operands of different calibers without a caliber_mismatch basis.",
    ),
    ContractClause(
        id="C11",
        severity="H",
        check=_clause_c11_mirrored_withheld_slot,
        title="One quantity, one definition",
        doc="the two valuation_withheld writers must use ONE convention.",
    ),
    ContractClause(
        id="C12a",
        severity="S",
        check=_clause_c12a_stale_8k_index,
        title="Stale 8-K index",
        doc="the artifact's own staleness disclosure must be acted on, not merely printed.",
    ),
    ContractClause(
        id="C12b",
        severity="S",
        check=_clause_c12b_empty_news_window,
        title="Empty news window",
        doc="an empty news window may not carry a populated sentiment read.",
    ),
    ContractClause(
        id="C12c",
        severity="S",
        check=_clause_c12c_stale_fact_published,
        title="Stale fact published",
        doc="a fact the producer annotated as stale must not ship as current fundamentals.",
    ),
    ContractClause(
        id="C13b",
        severity="S",
        check=_clause_c13b_self_centered_monte_carlo,
        title="Self-centred Monte Carlo",
        doc="a distribution centred on the assumptions it validates must declare itself dependent.",
    ),
    ContractClause(
        id="C13c",
        severity="S",
        check=_clause_c13c_non_independent_corroboration,
        title="Non-independent corroboration",
        doc="a non-independent agreement may not be the sole corroboration for a direction.",
    ),
    ContractClause(
        id="C14a",
        severity="S",
        check=_clause_c14a_direction_vs_sign,
        title="Direction word vs leaf sign",
        doc="a direction word must agree with the sign of the leaf it names.",
    ),
    ContractClause(
        id="C14b",
        severity="S",
        check=_clause_c14b_unresolved_placeholder,
        title="Unresolved target placeholder",
        doc="the withheld-target placeholder may not replace an amount the report publishes.",
    ),
]
