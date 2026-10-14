"""Numeric-audit verifier: a flow figure must be the COMPUTED flow, not a neighbour.

The narrative whitelist supplies the insider-flow leaves — the 90-day net flow plus
its gross purchase and sale legs (`ownership_governance.insider_buy_value` /
`insider_sell_value`) — and the drift detector (`report_drift`) accepts any amount
written in the report that matches ANY computed leaf. So the 2026-10-13 NVDA report
shipped "insiders were net sellers of $967.6M over 90 days ($259.87 of purchases vs
$967.6M of sales)" and passed every numeric check: `$259.87` is the DCF price target,
a leaf in its own right. Every token matched a real value — just the WRONG one.

A membership test cannot see that; it is a relationship error. This verifier checks
the relationship: an AGGREGATE flow statement ("purchases" / "sales", plural — a
single-transaction figure stays out of scope on purpose) written in an insider
context must carry the computed leg for that direction. `insider_buy_value == 0`
means any nonzero purchase amount is wrong, which is exactly the shipped defect.

Findings are ``review``. When the builder calls
:func:`correct_insider_flow_claims` the misattributed figure is REPLACED by the computed
leg (never a guess) and the substitution is reported, so the wrong number cannot ship
inside a caveat. Pure — reads the frozen narrative and the frozen ownership block, no
I/O, no LLM.
"""

from __future__ import annotations

import re
from typing import Any, Iterable, NamedTuple

from finrobot.engine.models.numeric_claim import Finding

__all__ = [
    "attach_insider_flow_findings",
    "correct_insider_flow_claims",
    "correction_findings",
    "insider_flow_amount_findings",
    "insider_flow_corrections",
]

#: Plural AGGREGATE flow nouns only. A singular "sale"/"purchase" is one transaction
#: (NVDA's "$297.9M largest single sale"), which no computed aggregate can contradict.
_FLOW_RE = re.compile(r"\b(?P<word>purchases|sales)\b", re.IGNORECASE)

#: The NET flow leg, claimed by its own phrase because the direction lives in the
#: words, not in the amount's sign ("net sellers of $4.41M"). "sales"/"purchases" are
#: deliberately absent — they are already covered by ``_FLOW_RE``, and a "net sales of
#: $2.9B" revenue line inside a management sentence must never be read as insider flow.
_NET_FLOW_RE = re.compile(
    r"\bnet\s+(?:insider\s+)?(?:sellers?|buyers?|selling|buying|flow)\b", re.IGNORECASE
)

#: Dollar amounts, with the usual magnitude suffix. The suffix — and the space before
#: it — is part of the match ONLY when a suffix letter is really there, so a bare
#: "$259.87 of purchases" matches exactly "$259.87" and a correction cannot eat the
#: space that follows it.
_AMOUNT_RE = re.compile(
    r"\$\s?(?P<num>\d[\d,]*(?:\.\d+)?)(?:\s?(?P<suffix>[KMBT])(?![A-Za-z]))?",
    re.IGNORECASE,
)
_SUFFIX_SCALE = {"k": 1e3, "m": 1e6, "b": 1e9, "t": 1e12}

#: A flow claim is only checkable when the sentence is about INSIDERS. "Vanguard's
#: purchases" or "13F rows show sales" are institutional/registry statements whose
#: numbers this module has no computed counterpart for.
_INSIDER_CONTEXT_RE = re.compile(
    r"\b(insiders?|officers?|directors?|executives?|management|board|form\s?4|open-market)\b",
    re.IGNORECASE,
)

#: Share repurchases are a corporate action, not insider flow — "repurchases" would
#: otherwise match on its "purchases" substring.
_REPURCHASE_RE = re.compile(r"\b(?:re|share)\s?purchases?\b|\bbuybacks?\b", re.IGNORECASE)

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")

#: How far an amount may sit from its flow word ("$259.87 of purchases",
#: "purchases of $259.87", "purchases: $0") and still be read as its figure.
_WINDOW = 40
_ROUNDING_TOLERANCE = 0.02

#: What joins a figure to its flow noun in a possessive statement: the genitive "of",
#: a colon, or the aggregation verbs real prose uses ("sales reached $967.6M",
#: "purchases were $0"). Anything else with a real word in it ("purchases vs $967.6M")
#: is NOT the noun's own figure.
_CONNECTOR_RE = re.compile(
    r"\bof\b|:|\b(?:reached|totall?ed|total(?:ing)?|were|was|hit|amounted|worth|at)\b",
    re.IGNORECASE,
)

#: "largest (single) sale" — the phrase names WHICH figure follows it, so an amount
#: attached to it is attributable without the ambiguity a bare plural noun carries.
_LARGEST_SALE_RE = re.compile(r"\blargest\b[^.;]{0,30}?\bsales?\b", re.IGNORECASE)


def _scale(match: re.Match[str]) -> float:
    value = float(match.group("num").replace(",", ""))
    suffix = match.group("suffix")
    return value * (_SUFFIX_SCALE[suffix.lower()] if suffix else 1.0)


def _flow_amount_match(
    noun: re.Match[str], amounts: list[re.Match[str]], text: str
) -> re.Match[str] | None:
    """The amount token the flow noun owns.

    Neither direction alone works on real prose: "$259.87 of purchases" puts the figure
    BEFORE the noun while "purchases of $0" puts it after — and both shapes appear in the
    same audited clause ("insiders were net sellers of $967.6M over 90 days ($259.87 of
    purchases vs $967.6M of sales)"), where a right-first rule would hand the $967.6M
    sales figure to "purchases" and report the wrong number in the evidence.

    So candidates on both sides are scored: a figure joined to the noun by a connector
    ("of" / ":") beats one merely adjacent, and among equals the nearer wins. "…of
    purchases vs $967.6M of sales" therefore resolves correctly on both nouns. The MATCH
    is returned (not the value) so a caller can rewrite exactly those characters.
    """
    best: tuple[bool, int, re.Match[str]] | None = None
    for match in amounts:
        if 0 <= match.start() - noun.end() <= _WINDOW:
            gap = text[noun.end() : match.start()]
        elif 0 <= noun.start() - match.end() <= _WINDOW:
            gap = text[match.end() : noun.start()]
        else:
            continue
        candidate = (bool(_CONNECTOR_RE.search(gap)), -abs(match.start() - noun.start()), match)
        if best is None or candidate[:2] > best[:2]:
            best = candidate
    return best[2] if best is not None else None


def _matches(actual: float, expected: float) -> bool:
    if expected == 0:
        return actual == 0
    return abs(actual - expected) / abs(expected) <= _ROUNDING_TOLERANCE


def _snippet(sentence: str) -> str:
    """A short, single-line quote of the offending sentence for triage."""
    flat = " ".join(sentence.split())
    return flat if len(flat) <= 160 else f"{flat[:157]}..."


class FlowMismatch(NamedTuple):
    """One aggregate flow figure that contradicts its computed leg.

    ``ambiguous`` marks a figure that cannot be SAFELY rewritten: the sentence names
    both aggregate nouns, or the printed value is itself another insider leaf (so the
    prose may legitimately be about that metric). Such a mismatch is reported, never
    edited — the report shows it rather than silently moving a number that might be
    correct.
    """

    start: int
    end: int
    noun: str
    actual: float
    expected: float
    sentence: str
    ambiguous: bool = False


def _largest_sale_mismatches(text: str, ownership: dict[str, Any]) -> list[FlowMismatch]:
    """The "largest (single) sale $X" figure must be the computed largest sale.

    The same misattribution that hit the aggregate purchase figure also hit this one in
    the 2026-10-14 run: the narrative wrote "(largest single sale $231.38)" — the DCF
    target — where the computed largest sale is $297,942,896. The phrase is explicit
    about which figure it names, so this association is unambiguous where a bare plural
    noun's is not.
    """
    largest = ownership.get("insider_largest_sale")
    expected = largest.get("value") if isinstance(largest, dict) else None
    if not isinstance(expected, (int, float)):
        return []
    found: list[FlowMismatch] = []
    for phrase in _LARGEST_SALE_RE.finditer(text):
        after = [m for m in _AMOUNT_RE.finditer(text) if 0 <= m.start() - phrase.end() <= _WINDOW]
        if not after:
            continue
        match = after[0]
        actual = _scale(match)
        if _matches(actual, float(expected)):
            continue
        found.append(
            FlowMismatch(
                start=match.start(),
                end=match.end(),
                noun="largest single sale",
                actual=actual,
                expected=float(expected),
                sentence=text[phrase.start() : match.end()],
            )
        )
    return found


def _flow_mismatches(text: str, ownership: object) -> list[FlowMismatch]:
    """Every aggregate insider-flow figure in ``text`` the computed legs contradict."""
    if not isinstance(ownership, dict):
        return []
    buy = ownership.get("insider_buy_value")
    sell = ownership.get("insider_sell_value")
    net = ownership.get("insider_net_flow")
    expected: dict[str, float | None] = {
        "purchases": float(buy) if isinstance(buy, (int, float)) else None,
        "sales": float(sell) if isinstance(sell, (int, float)) else None,
        # The net leg is compared on MAGNITUDE: prose states the direction in words
        # ("net sellers of $X"), never in the sign. GMED 2026-10-14 shipped "insiders
        # were net sellers of $90.61 over the last 90 days" — the price target written
        # as the net flow — which escaped the plural-aggregate rule below (its noun is
        # "sellers") AND was enforced rather than questioned by the target reconciler,
        # because $90.61 IS the canonical target it rewrites drifting amounts TO.
        "net flow": abs(float(net)) if isinstance(net, (int, float)) else None,
    }
    found: list[FlowMismatch] = _largest_sale_mismatches(text, ownership)
    if all(value is None for value in expected.values()):
        return found
    # A figure that IS another insider metric may legitimately belong to that metric
    # ("$967.6M of purchases" beside a sales clause is the SALE leg mis-named), so a
    # rewrite must never move it: only a figure that matches no sibling leaf is
    # corrected, and a sentence naming both aggregate nouns is ambiguous by definition.
    sibling_leaves = {
        float(value)
        for value in (
            ownership.get("insider_net_flow"),
            buy,
            sell,
            expected["purchases"],
            expected["sales"],
            (ownership.get("insider_largest_sale") or {}).get("value")
            if isinstance(ownership.get("insider_largest_sale"), dict)
            else None,
        )
        if isinstance(value, (int, float))
    }

    offset = 0
    for sentence in _SENTENCE_SPLIT_RE.split(text):
        start_of_sentence = text.find(sentence, offset)
        offset = start_of_sentence + len(sentence)
        if not _INSIDER_CONTEXT_RE.search(sentence) or _REPURCHASE_RE.search(sentence):
            continue
        amounts = list(_AMOUNT_RE.finditer(sentence))
        if not amounts:
            continue
        # Which token each aggregate noun claims. Two nouns claiming the SAME token is a
        # real collision ("$231.38 across purchases and sales"): one of them is wrong and
        # there is no way to tell which, so neither may be rewritten.
        claimed: dict[tuple[int, int], int] = {}
        per_noun: list[tuple[str, float, re.Match[str], float]] = []
        phrases: list[tuple[str, re.Match[str]]] = [
            (match.group("word").lower(), match) for match in _FLOW_RE.finditer(sentence)
        ]
        phrases += [("net flow", match) for match in _NET_FLOW_RE.finditer(sentence)]
        # Tokens a direction-specific aggregate leg already claimed in this sentence.
        aggregate_claims: set[tuple[int, int]] = set()
        for key, noun in phrases:
            want = expected.get(key)
            if want is None:
                continue
            match = _flow_amount_match(noun, amounts, sentence)
            if match is None:
                continue
            actual = _scale(match)
            if _matches(actual, want):
                continue
            span = (match.start(), match.end())
            # One token, one claim: when an aggregate leg names the same figure, its
            # direction-specific reading is the precise one. "Insiders were net sellers:
            # $500M of sales" is ONE sales claim, not a sales claim plus a net-flow
            # claim — the net phrase is a fallback for figures no aggregate noun covers
            # ("insiders were net sellers of $90.61" with no sales/purchases noun).
            if key == "net flow" and span in aggregate_claims:
                continue
            if key != "net flow":
                aggregate_claims.add(span)
            claimed[span] = claimed.get(span, 0) + 1
            per_noun.append((key, want, match, actual))
        for key, want, match, actual in per_noun:
            collided = claimed[(match.start(), match.end())] > 1
            sibling = any(_matches(actual, leaf) and leaf != want for leaf in sibling_leaves)
            found.append(
                FlowMismatch(
                    start=start_of_sentence + match.start(),
                    end=start_of_sentence + match.end(),
                    noun=key,
                    actual=actual,
                    expected=want,
                    sentence=sentence,
                    ambiguous=collided or sibling,
                )
            )
    return found


def _format_leg(value: float) -> str:
    """How the narrative should have written the computed leg."""
    if value == 0:
        return "$0"
    return f"${value:,.0f}"


def insider_flow_corrections(text: str, ownership: object) -> tuple[str, list[FlowMismatch]]:
    """Rewrite unattributable-flow figures and return what was rewritten.

    Same rewrite as :func:`correct_insider_flow_claims`, but reporting the applied
    ``FlowMismatch`` records so a caller can publish a structured finding about the edit
    (the report's caveat surface) instead of only a warning line.
    """
    mismatches = [m for m in _flow_mismatches(text, ownership) if not m.ambiguous]
    if not mismatches:
        return text, []
    applied: list[FlowMismatch] = []
    pieces: list[str] = []
    cursor = 0
    for mismatch in mismatches:
        # An ambiguous mismatch is reported, never edited; two still-overlapping spans
        # would corrupt the sentence, so the first one wins.
        if mismatch.start < cursor:
            continue
        pieces.append(text[cursor : mismatch.start])
        pieces.append(_format_leg(mismatch.expected))
        cursor = mismatch.end
        applied.append(mismatch)
    pieces.append(text[cursor:])
    return "".join(pieces), applied


def correct_insider_flow_claims(text: str, ownership: object) -> tuple[str, list[str]]:
    """Rewrite a misattributed aggregate flow figure to the computed leg, with notes.

    The narrative is the model's prose, but a figure that names the WRONG metric is
    not a matter of style: the 2026-10-13 NVDA Key Takeaways printed the DCF target as
    an insider purchase figure ("$259.87 of purchases" with a computed purchase leg of
    $0), and the prompt rule forbidding it did not hold on the next live run either
    ($231.38 — this time also as the "largest single sale"). The replacement is always
    the computed value, never a guess, and every substitution is reported so the reader
    learns the narrative was edited.

    Returns ``(corrected_text, notes)``; a text with nothing to correct comes back
    unchanged with no notes. Pure.
    """
    corrected, applied = insider_flow_corrections(text, ownership)
    notes = [
        f"the narrative stated ${mismatch.actual:,.2f} as the {mismatch.noun} figure; "
        f"corrected to the computed value {_format_leg(mismatch.expected)}"
        for mismatch in applied
    ]
    return corrected, notes


def _field_key_for(noun: str) -> str:
    """The published leaf a flow figure belongs to."""
    return {
        "purchases": "ownership_governance.insider_buy_value",
        "sales": "ownership_governance.insider_sell_value",
        "net flow": "ownership_governance.insider_net_flow",
    }.get(noun, "ownership_governance.insider_largest_sale")


def correction_findings(applied: Iterable[FlowMismatch]) -> list[Finding]:
    """Findings disclosing a correction the builder applied to the narrative.

    A reader must be able to see that the prose they are reading was edited by the
    pipeline — and the report page renders ``numeric_audit`` findings, not the warning
    list, so the correction has to be a finding to be visible. It does NOT claim the
    shipped number is wrong (it is the computed one); it names what was replaced.
    """
    findings: list[Finding] = []
    seen: set[tuple[str, float]] = set()
    for mismatch in applied:
        key = (mismatch.noun, mismatch.actual)
        if key in seen:
            continue
        seen.add(key)
        findings.append(
            Finding(
                field_key=_field_key_for(mismatch.noun),
                check="insider_flow_amount_corrected",
                severity="review",
                evidence=(
                    f"the narrative stated ${mismatch.actual:,.2f} as the {mismatch.noun} "
                    f"figure; the published text was corrected to the computed value "
                    f"${mismatch.expected:,.0f} (the printed amount belonged to another "
                    f"metric)"
                ),
            )
        )
    return findings


def attach_correction_findings(
    structured_out: dict[str, Any], applied: Iterable[FlowMismatch]
) -> list[str]:
    """Publish the corrections the builder applied as ``numeric_audit`` findings.

    Same sink and shape as :func:`attach_insider_flow_findings`, and it must be called
    AFTER the numeric-audit block is built (that builder recreates the block). No-op when
    nothing was corrected.
    """
    findings = correction_findings(applied)
    audit = structured_out.get("numeric_audit")
    if not findings or not isinstance(audit, dict):
        return []
    existing = audit.get("findings")
    dumped: list[Any] = existing if isinstance(existing, list) else []
    known = {
        (entry.get("field_key"), entry.get("check")) for entry in dumped if isinstance(entry, dict)
    }
    warnings: list[str] = []
    for finding in findings:
        if (finding.field_key, finding.check) in known:
            continue
        dumped.append(finding.model_dump(mode="json"))
        audit["artifact_status"] = "caveated"
        warnings.append(
            f"[NUMERIC-AUDIT/{finding.severity}] {finding.field_key} "
            f"({finding.check}): {finding.evidence}"
        )
    audit["findings"] = dumped
    return warnings


def insider_flow_amount_findings(
    narrative_texts: Iterable[str], ownership: dict[str, Any] | None
) -> list[Finding]:
    """Findings for aggregate insider-flow figures the computed legs contradict.

    ``ownership`` is the serialised ``OwnershipGovernanceAnalysis`` (the same block
    the narrative prompt reads its leaves from). Returns ``[]`` when the block is
    absent, carries no computed legs, or the narrative makes no checkable claim —
    never raises.
    """
    if not isinstance(ownership, dict):
        return []
    days = ownership.get("insider_window_days")
    window_txt = f"{days}-day" if isinstance(days, int) and days > 0 else "trailing"

    findings: list[Finding] = []
    seen: set[tuple[str, float]] = set()
    for text in narrative_texts:
        if not isinstance(text, str) or not text:
            continue
        for mismatch in _flow_mismatches(text, ownership):
            if (mismatch.noun, mismatch.actual) in seen:
                continue
            seen.add((mismatch.noun, mismatch.actual))
            field_key = _field_key_for(mismatch.noun)
            scale_txt = f"{window_txt} " if mismatch.noun in ("purchases", "sales") else ""
            findings.append(
                Finding(
                    field_key=field_key,
                    check="insider_flow_amount_mismatch",
                    severity="review",
                    evidence=(
                        f"the narrative states ${mismatch.actual:,.2f} as the {scale_txt}"
                        f"insider {mismatch.noun} figure; the computed value is "
                        f"${mismatch.expected:,.0f} (the two cannot both be the same flow — "
                        f"the printed amount appears to come from another metric): "
                        f"{_snippet(mismatch.sentence)}"
                    ),
                )
            )
    return findings


def attach_insider_flow_findings(
    structured_out: dict[str, Any], narrative_texts: Iterable[str]
) -> list[str]:
    """Append the flow-attribution findings to ``structured_out["numeric_audit"]``.

    The single wiring entry point for the artifact builder: it reads the ownership
    block out of ``structured_out`` itself, so a caller passes only the frozen
    narrative fields. Appends in the same shape every other verifier's findings take,
    rolls the artifact status up to ``caveated`` (a ``review`` finding annotates, it
    never withholds), and returns the ``[NUMERIC-AUDIT/...]`` lines. No-op when the
    numeric-audit block is absent, the ownership block carries no computed legs, or
    every flow figure reproduces.
    """
    audit = structured_out.get("numeric_audit")
    if not isinstance(audit, dict):
        return []
    ownership = structured_out.get("ownership_governance")
    findings = insider_flow_amount_findings(
        narrative_texts, ownership if isinstance(ownership, dict) else None
    )
    if not findings:
        return []
    existing = audit.get("findings")
    dumped: list[Any] = existing if isinstance(existing, list) else []
    known = {
        (entry.get("field_key"), entry.get("check")) for entry in dumped if isinstance(entry, dict)
    }
    warnings: list[str] = []
    for finding in findings:
        if (finding.field_key, finding.check) in known:
            continue
        dumped.append(finding.model_dump(mode="json"))
        audit["artifact_status"] = "caveated"
        warnings.append(
            f"[NUMERIC-AUDIT/{finding.severity}] {finding.field_key} "
            f"({finding.check}): {finding.evidence}"
        )
    audit["findings"] = dumped
    return warnings
