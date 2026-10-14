"""Output-contract total gate — the one invariant check between a fully assembled
artifact and the store.

Every upstream gate sees a fragment: the data-health gate sees a
``ValuationSynthesis``, the numeric audit sees a ``FinancialData`` snapshot, the
narrative reconcile sees one prose field. None of them ever sees the assembled
artifact — headline, basis, narrative, currency all in one object. ``runner.py``
persists at a single boundary (builder output → ``store.save``); this contract
runs in the gap and asserts whole-artifact invariants the fragment gates are
structurally blind to:

  · C1 — the headline target/MARKET ratio must sit in the calibrated divergence
    band (single-method [1/2x, 2x], multi-method [1/4x, 4x]). Catches the MU
    $2172 = 2.5x-$864 accident no matter how the upstream gate mis-calibrated.
  · C1b — the surviving methods must corroborate EACH OTHER (max/min mid ≤ the
    leaf corroboration span). The backstop C1 is blind to: a target in-band vs the
    market while the methods are 7x apart (MU 0.69x-of-market case).
  · C2 — a ``$``-anchored amount with two decimal points ($2172.062.06) is a
    string-concatenation artifact the narrative reconcile produced *after* every
    upstream gate ran; withhold (a malformed amount cannot be safely repaired).
  · C6b–C14b — the §4 closure family, promoted 2026-10-14 from the staged module
    the design doc's §7.1 kept them in while each was quantified over the stored
    corpus. Their docstrings carry each rule's measured catch list and the
    severity they actually ship at: ``C8`` and ``C11`` withhold; the other thirteen
    annotate, because their locked remediation — a count threshold per §9.2, a
    sentence the gate cannot rewrite, or (``C9``'s case) a claim-scope withhold that
    drops the offending band entries rather than the headline target — is not a
    per-artifact value-withhold.

Every `MEASURED CATCH LIST` below is an AS-OF reading over a live store — the corpus grows
as runs land. The `H` families are frozen (their defect classes have shipped fixes, so a
count that does not move is the expected result); the `S` families keep finding new
artifacts, so their counts rise with the corpus and a later reading is a later date, never a
contradiction. §9.3 carries the readings themselves.

A violated HARD clause is a VALUE-withhold: it degrades through the existing
withhold machinery — null the target slot(s) + ``valuation_withheld`` +
``[CONTRACT/*]`` warning — while PRESERVING the directional verdict (corrupt /
out-of-band data withholds the price, never the judgment; there is no "REVIEW"
refuse-to-rate state any more). It never raises (an exception would blank the
whole run; an analyst would rather see the full report and know which number is
suspect). A SOFT clause only annotates.

Design contract (the gate stays dumb — see ADR): zero I/O, never imports
``compute/`` / ``data/`` / ``pipelines/``, holds no bare threshold literal (the
bands are imported calibrated constants from the leaf), and each clause is a pure
``check(artifact) -> Finding | None``. It verifies the *result*; it never re-runs
the computation.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Literal

from finrobot.artifact.summary_extractor import extract_entry_price, extract_target_price
from finrobot.engine.models.numeric_claim import Finding
from finrobot.engine.models.reconcile_tolerances import NARRATIVE_DRIFT_TOLERANCE
from finrobot.engine.models.valuation_thresholds import (
    MARKET_DIVERGENCE_RATIO_K,
    METHOD_CORROBORATION_SPAN_K,
    SINGLE_METHOD_DIVERGENCE_RATIO_K,
)
from finrobot.engine.models.withhold_reason import (
    WithholdReason,
    as_withhold_reason,
    withhold_reason,
)

if TYPE_CHECKING:
    from finrobot.artifact.models import Artifact

ClauseSeverity = Literal["H", "S"]

# When a clause withholds, the POINT-target conclusion (the tagline) is
# neutralised but the directional verdict and the analysis body are preserved
# verbatim, with a provenance stamp telling the reader the price target was
# withheld after the narrative was written. EN placeholder (single-locale ship);
# revisit copy when the cover badge wording is finalised.
_WITHHELD_NARRATIVE_STAMP = (
    "Price target withheld by the output contract; the directional verdict still "
    "stands and the analysis below was written before the withhold."
)


@dataclass(frozen=True)
class ContractClause:
    """One whole-artifact invariant. ``severity`` H → violation withholds the
    headline TARGET + sets ``valuation_withheld`` (the directional verdict is
    preserved); S → violation only appends a note. ``check`` is a pure function
    returning the violation as a :class:`Finding`, or None when the invariant
    holds (or does not apply to this artifact's shape)."""

    id: str
    severity: ClauseSeverity  # H → violation withholds the TARGET (verdict kept); S → note only.
    check: Callable[["Artifact"], Finding | None]
    # surface=False → an INTERNAL invariant (C7's no-resurrection scrub): it still
    # withholds + scrubs, but its evidence is engineering plumbing ("nulling so it
    # cannot resurrect downstream"), so it is emitted under a non-surfacing
    # "[CONTRACT/<id>/internal]" tag the report UI skips. The analyst-facing clauses
    # (C1–C4) keep the default and drive the audit banner / cover withhold reason.
    surface: bool = True
    #: A renderable name for the rule, so a human-review surface (the scanner's catch
    #: lists today; the reason-code registry of design §9.6 later) names the rule
    #: instead of only its id. It lives HERE and nowhere else — a title duplicated in
    #: a consumer is the same drift class §4.4 is about.
    title: str = ""
    #: One imperative line saying what the clause requires, for the same surfaces.
    #: Deliberately terse: the spec is design §4, and a second full copy here would
    #: be a second truth to keep in sync.
    doc: str = ""
    #: The withhold reason this clause files when it FIRES (design §9.6). Declared here, beside
    #: the title, so the vocabulary has one home and a code is never spelled at a call site; the
    #: string must exist in ``WITHHOLD_CODES`` (a test asserts that for every H clause, since only
    #: H clauses withhold a value). Empty for an annotating clause: it withholds nothing.
    reason_code: str = ""
    #: Count thresholds (design §9.2, dbt's ``severity: error|warn`` +
    #: ``error_if``/``warn_if`` shape): a clause can be over-broad while it is
    #: calibrated, so it should be able to ANNOTATE up to some number of offending
    #: items and WITHHOLD past it instead of being all-or-nothing. ``None`` = the
    #: clause has one severity for every violation.
    #:
    #: DECLARED, NOT YET CONSUMED (design §9.8 declares the addition additive and
    #: behaviour-preserving, which is why it lands here ahead of its first user).
    #: ``enforce_artifact_contract`` reads only ``severity`` / ``check`` / ``surface``,
    #: and no clause sets these, so the live gate is unchanged by their presence —
    #: ``tests/artifact/test_contract_fixtures.py``'s verdict oracle is the proof.
    #: What they still need is the count itself: a ``check`` returns at most ONE
    #: :class:`Finding`, and the offending-item count a clause like `C10d` already
    #: prints in its evidence has nowhere structured to live yet. That carrier is
    #: :class:`~finrobot.engine.models.numeric_claim.NumericClaim`'s
    #: ``basis``/``is_proxy``/``derivation`` addition (design §6/§9.5), so the
    #: thresholds become readable in the same change.
    warn_if: int | None = None
    error_if: int | None = None


# ── C1: headline upside band ─────────────────────────────────────────────────


def _clause_c1_upside_band(artifact: "Artifact") -> Finding | None:
    """target/entry must sit in the calibrated divergence band. Band selection is
    type-agnostic: a corroborated estimate (``valuation_synthesis.weighted_price``
    present = ≥2 methods agreed) gets the wider multi-method band; a lone method
    (no synthesis block, or weighted_price None) gets the tighter single-method
    band — its only cross-check is the market price itself."""
    target = extract_target_price(artifact)
    entry = extract_entry_price(artifact)
    if target is None or entry is None or entry <= 0:
        return None  # no per-share headline to check (lbo / comps / ic_memo)

    ratio = target / entry
    synthesis = artifact.outputs.structured.get("valuation_synthesis")
    corroborated = isinstance(synthesis, dict) and synthesis.get("weighted_price") is not None
    k = MARKET_DIVERGENCE_RATIO_K if corroborated else SINGLE_METHOD_DIVERGENCE_RATIO_K
    lo, hi = 1.0 / k, k
    if lo <= ratio <= hi:
        return None

    band = "multi-method" if corroborated else "single-method"
    return Finding(
        field_key="thesis.price_target",
        check="contract_c1_upside_band",
        severity="blocked_field",
        evidence=(
            f"headline target {target:.2f} is {ratio:.2g}x the entry price {entry:.2f}, "
            f"outside the {band} corroboration band [{lo:.2g}x, {hi:.2g}x]"
        ),
    )


# ── C1b: method-vs-method corroboration span ─────────────────────────────────


def _clause_c1b_method_span(artifact: "Artifact") -> Finding | None:
    """The method-disagreement backstop C1 is structurally blind to. C1 compares
    the headline to the MARKET; a target can sit comfortably in the market band
    (e.g. MU 0.69x of market) while the surviving methods are 7x apart from EACH
    OTHER — no honest blended point exists, so the POINT must be withheld (the
    directional verdict still ships). Reads the dumped ``valuation_synthesis.methods``
    mids and fires when max/min exceeds the shared leaf corroboration span; a
    value-withhold, never a refuse-to-rate. Every read is guarded — methods may be
    absent, a non-list, or (in unit fixtures) a list of bare names with no mid."""
    target = extract_target_price(artifact)
    if target is None or target <= 0:
        return None  # no per-share headline to withhold
    synthesis = artifact.outputs.structured.get("valuation_synthesis")
    if not isinstance(synthesis, dict):
        return None
    methods = synthesis.get("methods")
    if not isinstance(methods, list):
        return None

    mids: list[float] = []
    for method in methods:
        if not isinstance(method, dict):
            continue  # a bare method name carries no mid — nothing to span
        mid = method.get("mid")
        if isinstance(mid, bool):  # True == 1 must not masquerade as a mid
            continue
        if isinstance(mid, (int, float)) and mid > 0:
            mids.append(float(mid))
    if len(mids) <= 1:
        return None  # a single (or zero) mid can't disagree with itself

    lo, hi = min(mids), max(mids)
    span = hi / lo
    if span <= METHOD_CORROBORATION_SPAN_K:
        return None

    return Finding(
        field_key="thesis.price_target",
        check="contract_c1b_method_span",
        severity="blocked_field",
        evidence=(
            f"valuation methods span {span:.2g}x (min ${lo:.2f}, max ${hi:.2f}) — "
            f"above the {METHOD_CORROBORATION_SPAN_K:.0f}x corroboration limit; "
            f"no honest blended point exists, withholding the target {target:.2f}"
        ),
    )


# ── C2: double-decimal malformation ──────────────────────────────────────────

# A ``$``-anchored amount carrying TWO decimal points is a concatenation artifact
# ($2172.062.06, $1,234.562.06). The ``$`` anchor + double-point is what keeps it
# off the high-frequency LEGAL financial decimals a naive ``\d\.\d{2}\d`` mauled:
# beta 1.085, FX 7.234, R² 0.987, a fractional strike $1.875, a percentage 0.025.
# Trailing ``\d+`` (vs the spec's single ``\d``) captures the WHOLE malformed run
# so the evidence names the real token ($2172.062.06), not a truncated prefix —
# detection semantics are unchanged (a match still needs $ + two decimal points).
_DOUBLE_DECIMAL_RE = re.compile(r"\$\d[\d,]*\.\d{2}\d*\.\d+")


def _clause_c2_double_decimal(artifact: "Artifact") -> Finding | None:
    for text in _iter_narrative_strings(artifact):
        match = _DOUBLE_DECIMAL_RE.search(text)
        if match is not None:
            return Finding(
                field_key="narrative",
                check="contract_c2_double_decimal",
                severity="blocked_field",
                evidence=f"malformed amount '{match.group(0)}' (two decimal points) in narrative",
            )
    return None


def _iter_narrative_strings(artifact: "Artifact") -> Iterator[str]:
    """Every analyst-facing string: structured (incl. the thesis prose), the
    llm_narrative mirror (a dict — ⟦复核⟧ must be traversed, not str()'d), and
    summary_text. NOT warnings — those carry the contract's own [CONTRACT/*]
    evidence, scanning them would re-trip C2 on its own output."""
    outputs = artifact.outputs
    yield from _iter_strings(outputs.structured)
    yield from _iter_strings(outputs.llm_narrative)
    if outputs.summary_text:
        yield outputs.summary_text


def _iter_strings(obj: Any) -> Iterator[str]:
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for value in obj.values():
            yield from _iter_strings(value)
    elif isinstance(obj, (list, tuple)):
        for value in obj:
            yield from _iter_strings(value)


# ── C3: basis conclusion amount == headline ──────────────────────────────────

# Same shape as equity_research.py:710 `_DOLLAR_RE` (group 1 = numeric body, with
# optional thousands separators / decimals). Replicated here, not imported, to
# keep the contract off the pipeline layer (Q4 red line); it is a regex literal,
# not a numeric threshold.
_DOLLAR_RE = re.compile(r"\$\s?(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)")

# A conclusion cue immediately preceding a $-amount marks it as the BASIS's stated
# conclusion (vs a per-method mid the basis merely cites). Only a cue-anchored
# amount is compared to the headline — this is the false-positive guard: no cue,
# no comparison (we never guess which of several cited $-amounts is the verdict).
_CONCLUSION_CUE_RE = re.compile(
    r"(?:→|price\s+target|target|目标价|目标)\s*[:：]?\s*\$\s?"
    r"(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)",
    re.IGNORECASE,
)


def _clause_c3_basis_matches_headline(artifact: "Artifact") -> Finding | None:
    """A cue-anchored conclusion $-amount in the basis / valuation_overview must
    equal the headline price_target (relative tolerance). CONSERVATIVE: fires ONLY
    on a clear contradiction — a $-amount that directly follows a conclusion cue
    (→ / target / 目标). No cue-anchored amount → NO-OP (cited per-method mids are
    not guessed to be the verdict). Catches a table-vs-prose desync the upstream
    narrative reconcile could itself have produced."""
    target = extract_target_price(artifact)
    if target is None or target <= 0:
        return None
    thesis = artifact.outputs.structured.get("thesis")
    if not isinstance(thesis, dict):
        return None

    for field_name in ("price_target_basis", "valuation_overview"):
        text = thesis.get(field_name)
        if not isinstance(text, str):
            continue
        for match in _CONCLUSION_CUE_RE.finditer(text):
            try:
                amount = float(match.group(1).replace(",", ""))
            except ValueError:
                continue
            if abs(amount - target) <= abs(target) * NARRATIVE_DRIFT_TOLERANCE:
                continue
            return Finding(
                field_key=f"thesis.{field_name}",
                check="contract_c3_basis_headline_desync",
                severity="blocked_field",
                evidence=(
                    f"basis conclusion amount ${amount:.2f} (after '{match.group(0).strip()}') "
                    f"contradicts the headline price_target {target:.2f}"
                ),
            )
    return None


# ── C4: currency / unit caliber ──────────────────────────────────────────────

# audit_currency_caliber (compute/operators/audit/currency_caliber) emits this
# check id for a cross-currency ratio. The contract matches the id (or the
# "currency" family) on the already-dumped numeric_audit findings — it does not
# re-run the auditor.
_CURRENCY_CHECK = "cross_currency_ratio"


def _clause_c4_currency_caliber(artifact: "Artifact") -> Finding | None:
    """Backstop for a currency-caliber miss. Fires when a per-share headline still
    survives AND either: (a) numeric_audit carries a currency-family blocked_field
    finding (the type-agnostic missed-withhold — mixed-currency P/E on SAP / TSM /
    TM), or (b) a currency block is present but missing quote_currency /
    reporting_currency (the caliber tags never resolved). Every read is guarded —
    numeric_audit is absent on plain dcf/ddm, currency absent on non-equity."""
    target = extract_target_price(artifact)
    if target is None or target <= 0:
        return None
    structured = artifact.outputs.structured

    numeric_audit = structured.get("numeric_audit")
    if isinstance(numeric_audit, dict):
        findings = numeric_audit.get("findings")
        if isinstance(findings, list):
            for finding in findings:
                if not isinstance(finding, dict):
                    continue
                if finding.get("severity") != "blocked_field":
                    continue
                check = finding.get("check")
                if not isinstance(check, str):
                    continue
                if check == _CURRENCY_CHECK or "currency" in check:
                    return Finding(
                        field_key="thesis.price_target",
                        check="contract_c4_currency_caliber",
                        severity="blocked_field",
                        evidence=(
                            f"currency-caliber finding '{check}' on "
                            f"{finding.get('field_key', '?')} blocked but headline "
                            f"{target:.2f} survived — withholding mixed-currency target"
                        ),
                    )

    currency = structured.get("currency")
    if isinstance(currency, dict):
        for key in ("quote_currency", "reporting_currency"):
            if not currency.get(key):
                return Finding(
                    field_key="currency",
                    check="contract_c4_currency_caliber",
                    severity="blocked_field",
                    evidence=(
                        f"per-share headline {target:.2f} present but currency "
                        f"caliber is incomplete (missing {key}) — cannot label the "
                        f"amount's currency"
                    ),
                )
    return None


# ── C6: single-method no-cross-check disclosure (SOFT) ───────────────────────

# The basis must admit it lacks a second opinion. Any of these phrasings counts
# (case-insensitive); upstream resolve_canonical_thesis writes "no cross-check
# available" — C6 re-checks new paths didn't drop it.
_CROSS_CHECK_DISCLOSURES = (
    "no cross-check",
    "no cross check",
    "single-method",
    "single method",
    "无交叉",
    "单一方法",
)


def _clause_c6_single_method_disclosure(artifact: "Artifact") -> Finding | None:
    """SOFT: when only one method survived (valuation_synthesis.weighted_price is
    None) and a live headline exists, the basis MUST disclose it has no
    cross-check. Missing → a note (severity review) — the target still ships, the
    analyst is just told it has no second opinion. Never withholds."""
    target = extract_target_price(artifact)
    if target is None or target <= 0:
        return None
    structured = artifact.outputs.structured
    synthesis = structured.get("valuation_synthesis")
    if not isinstance(synthesis, dict) or synthesis.get("weighted_price") is not None:
        return None  # multi-method (corroborated) or no synthesis block → not C6's case

    thesis = structured.get("thesis")
    basis = thesis.get("price_target_basis") if isinstance(thesis, dict) else None
    haystack = basis.lower() if isinstance(basis, str) else ""
    if any(phrase in haystack for phrase in _CROSS_CHECK_DISCLOSURES):
        return None

    return Finding(
        field_key="thesis.price_target_basis",
        check="contract_c6_single_method_disclosure",
        severity="review",
        evidence=(
            f"single-method headline {target:.2f} (no weighted cross-check) but the "
            f"basis does not disclose it lacks corroboration"
        ),
    )


# ── C7: withheld must not resurrect ──────────────────────────────────────────

# Raw fallback slots a withheld headline can hide in. extract_target_price is
# thesis-authoritative and ignores them, but other consumers (coverage list,
# signal lamp) read them directly — so C7 scans the RAW slots, not the extractor.
_FALLBACK_HEADLINE_SLOTS: tuple[tuple[str, str | None], ...] = (
    ("price_target", "thesis"),
    ("target_price", "thesis"),
    ("implied_price", None),
    ("equity_value_per_share", None),
    ("target_price", None),
    ("implied_price", "financial_modeling"),
    ("implied_price", "dcf_result"),
)


def _is_withheld(artifact: "Artifact") -> bool:
    """The withhold judge for C7: True when the published thesis is withholding its
    POINT target. The verdict/target decoupling (commit ③) made the target
    withhold its own signal — ``thesis.price_target is None`` while the
    recommendation is directional (BUY/HOLD/SELL) — replacing the deleted
    recommendation=='REVIEW' sentinel. The explicit ``valuation_withheld`` flag
    (set by every withhold producer) is also honoured. A legacy stored artifact
    may still carry recommendation=='REVIEW' (read-only back-compat — never
    written any more): treat it as withheld so C7 keeps scrubbing old artifacts.
    Either signal must drive C7 so a fallback $-slot can't resurrect the target."""
    structured = artifact.outputs.structured
    if structured.get("valuation_withheld") is True:
        return True
    thesis = structured.get("thesis")
    if not isinstance(thesis, dict):
        return False
    if thesis.get("recommendation") == "REVIEW":  # legacy artifacts only
        return True
    # The published withhold signal: a directional verdict with no point target.
    recommendation = thesis.get("recommendation")
    if recommendation in ("BUY", "HOLD", "SELL") and thesis.get("price_target") is None:
        return True
    return False


def _clause_c7_no_resurrection(artifact: "Artifact") -> Finding | None:
    """When the artifact is withholding its target (directional verdict, no point),
    NO headline value may survive in ANY fallback slot. Scans the RAW slots (not
    extract_target_price, which already early-returns on a thesis) — the TSLA bug
    was financial_modeling.implied_price = 20.35 riding naked on a thesis whose own
    price_target was withheld. Any positive number found → fire (the _withhold
    scrub then nulls every slot).

    INTERNAL clause (``surface=False``): the finding is recorded as a non-surfacing
    ``[CONTRACT/C7/internal]`` warning for the audit trail but never reaches the
    analyst UI — its evidence is plumbing ("nulling so it cannot resurrect
    downstream"), not a withhold REASON. The real reason rides the analyst-facing
    clauses (C1–C4) or the method-spread warnings."""
    if not _is_withheld(artifact):
        return None
    structured = artifact.outputs.structured
    for slot, parent_key in _FALLBACK_HEADLINE_SLOTS:
        container = structured.get(parent_key) if parent_key is not None else structured
        if not isinstance(container, dict):
            continue
        value = container.get(slot)
        if isinstance(value, bool):  # avoid True == 1 surviving as a "headline"
            continue
        if isinstance(value, (int, float)) and value > 0:
            where = f"{parent_key}.{slot}" if parent_key else slot
            return Finding(
                field_key=where,
                check="contract_c7_no_resurrection",
                severity="blocked_field",
                evidence=(
                    f"withheld-target artifact still carries a headline {value} in "
                    f"{where} — nulling so it cannot resurrect downstream"
                ),
            )
    return None


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


def _consulted(check: dict[str, Any]) -> bool:
    """Whether the DECISION had this cross-check row when it was written (§5).

    ``consulted_by_verdict`` is False only for the audit BACK-FILL: a row published
    after the verdict, from the technical chapter's frozen band, because the
    synthesis' own band fetch came back empty (instance B `99cdca`: the band held 0
    samples pre-verdict and 948 eight minutes later, so the report printed a
    cross-check its own call had never read). Such a row is display-only, and only
    the tag makes it distinguishable from a synthesis row — the two are otherwise the
    same band applied to the same EBITDA, so inferring from the shape would misfile
    every synthesis row that lost its method row.

    Absent tag = the pre-2026-10-14 archive. Read as consulted, which keeps every
    clause's historical reading unchanged (§9.3: the archive is annotated on read,
    never rewritten).
    """
    return check.get("consulted_by_verdict") is not False


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

    A DISPLAY-ONLY row is not evidence against the call (§5, ``_consulted``): a row
    published after the verdict is one the decision never had, so it cannot be the
    thing the decision ignored. The exclusion is tag-only, and every one of the 7
    instances above is pre-fix and untagged — so this clause reads the archive exactly
    as it did before the tag existed (43 of the 49 stored rows are back-fill-shaped,
    all 7 instances included, but the shape alone cannot decide it). Artifacts written
    from 2026-10-14 onward carry the tag, and the 6 C8-only instances stay withheld
    until §5's precondition lands.
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
    checks = [c for c in _cross_checks(synthesis) if _is_usable(c) and _consulted(c)]
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
    """S — a cross-check that is not evidence must not be published as evidence.

    A fundamental band for a positive-price equity must start above zero, run
    low < high, and be monotone; the payload already carries ``band_break_caveat``
    (``null`` everywhere observed) and this is what should populate it. Claim
    scope: the band entries are dropped, not the headline target.

    ENTERED AT `S` (2026-10-14) although §4.2 locks `H`, for the same reason the
    `C10`/`C12`/`C14` families did: the locked claim scope is not expressible here.
    ``_withhold`` scrubs the HEADLINE slots and cannot drop a list entry, so an `H`
    arming would take the target off SKM for a defect §4.2 says must NOT withhold the
    target — and it would not even remove the nonsense band, which stays in
    ``cross_checks`` either way. So the arming would be both heavier and less
    effective than the locked remedy. It annotates until the gate grows a claim-scope
    withhold (the mechanism §9.2 specifies, which the numeric-audit path already has).

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

    MEASURED CATCH LIST 29 artifacts / 14 tickers, span `…10-13T20:52:12` …
    `…10-14T22:20:15` — LIVE: the newest instance was written *after* the clause was
    armed, so this is a defect class still being produced, not a closed one. (Counts
    in these docstrings are as-of readings over a live store; §7.5's convention.)

    The single-method test reads the synthesis' own aggregate (``weighted_price is
    None``) rather than re-deriving a method count — the same signal C1 and C6 use, so
    the rules cannot drift apart. Both forms agree on every stored artifact (measured
    2026-10-14 over 116: 29 either way, **0** disagreements), which is why the swap is
    behaviour-preserving rather than a re-calibration.
    """
    structured = _structured(artifact)
    thesis = structured.get("thesis")
    synthesis = _synthesis(structured)
    if not isinstance(thesis, dict):
        return None
    # Single-method is read the way the REST of the gate reads it — the synthesis'
    # own aggregate (``weighted_price is None`` ⇒ fewer than two methods, see
    # ``ValuationSynthesis``) rather than a re-derived method count. Same signal C1
    # and C6 use, so the rules cannot drift apart (one quantity, one definition,
    # §4.4), and it keeps a bare method-count threshold out of this module.
    checks = _cross_checks(synthesis)
    if synthesis.get("weighted_price") is not None or not checks:
        return None
    note = " ".join(
        str(synthesis.get(key) or "") for key in ("degradation_note", "confidence_note")
    )
    lowered = note.lower()
    if not any(phrase in lowered for phrase in _NO_CROSS_CHECK_PHRASES):
        return None
    # C6b reads what the report PRINTS, so a display-only row counts (§5): the
    # reader sees the row and the note denying it, whatever the decision saw. When
    # every printed row is display-only, the note is TRUE of the decision and the
    # publication is the thing that needs the qualifier — say which.
    provenance = (
        ""
        if any(_consulted(c) for c in checks)
        else " (every printed row is display-only: published after the call, so the "
        "disclosure is true of the decision and the PUBLICATION is what needs the "
        "qualifier)"
    )
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
            f"the method count, not from the evidence{provenance}"
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

    MEASURED CATCH LIST 24 / 15 tickers, span `…10-14T06:2x` … `…10-14T22:5x` — LIVE and
    RISING, which is the point: it read 10 over 5 tickers at the promotion and 24 over 15
    at the 120-artifact reading, because this defect class is still being produced. The
    count is a date (see the as-of note above), and the payload already carries the
    disclosure in two shapes.
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


# ── Registry + enforcement ───────────────────────────────────────────────────

CONTRACT_CLAUSES: list[ContractClause] = [
    ContractClause(
        id="C1",
        severity="H",
        check=_clause_c1_upside_band,
        title="Headline upside band",
        doc="target/entry must sit inside the calibrated divergence band.",
        reason_code="TARGET_OUT_OF_BAND",
    ),
    ContractClause(
        id="C1b",
        severity="H",
        check=_clause_c1b_method_span,
        title="Method-vs-method corroboration span",
        doc="the method disagreement must sit inside the span C1 is structurally blind to.",
        reason_code="METHODS_DIVERGENT",
    ),
    ContractClause(
        id="C2",
        severity="H",
        check=_clause_c2_double_decimal,
        title="Double-decimal malformation",
        doc="a $-anchored amount may not carry two decimal points.",
        reason_code="MALFORMED_AMOUNT",
    ),
    ContractClause(
        id="C3",
        severity="H",
        check=_clause_c3_basis_matches_headline,
        title="Basis conclusion matches the headline",
        doc="a cue-anchored conclusion amount must equal the published headline target.",
        reason_code="BASIS_CONTRADICTS_HEADLINE",
    ),
    ContractClause(
        id="C4",
        severity="H",
        check=_clause_c4_currency_caliber,
        title="Currency and unit caliber",
        doc="a per-share headline requires a complete currency caliber.",
        reason_code="CALIBER_MISMATCH",
    ),
    ContractClause(
        id="C6",
        severity="S",
        check=_clause_c6_single_method_disclosure,
        title="Single-method disclosure",
        doc="a single-method headline must disclose that it has no cross-check.",
    ),
    ContractClause(
        id="C7",
        severity="H",
        check=_clause_c7_no_resurrection,
        surface=False,
        title="Withheld target must not resurrect",
        doc="a withheld target may not survive in any fallback slot.",
        reason_code="HEADLINE_SLOT_RESURRECTED",
    ),
    # ── §4 closure family, promoted 2026-10-14 (§7.1) ────────────────────────
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
        reason_code="VERDICT_VS_CROSS_CHECKS",
        doc="a directional verdict may not contradict the report's own published cross-checks.",
    ),
    ContractClause(
        id="C9",
        severity="S",
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
        reason_code="SPLIT_WRITER_CONVENTION",
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


def enforce_artifact_contract(artifact: "Artifact") -> "Artifact":
    """Run every clause at the persist boundary. Hard violations degrade the
    artifact through the existing withhold machinery; soft violations annotate.
    Returns the (possibly degraded) artifact — never raises, never blanks a run.
    A compliant artifact is returned untouched."""
    hard: list[tuple[ContractClause, Finding]] = []
    for clause in CONTRACT_CLAUSES:
        finding = clause.check(artifact)
        if finding is None:
            continue
        if clause.severity == "H":
            hard.append((clause, finding))
        else:
            _append_warning(artifact, f"[CONTRACT/{clause.id}/note] {finding.evidence}")

    if hard:
        _withhold(artifact, hard)
    return artifact


def _scrub_headline_slots(structured: dict[str, Any]) -> None:
    """Null EVERY slot a headline TARGET can hide in — the authoritative thesis
    target, the flat per-share slots a plain dcf/ddm dumps, AND the nested fallback
    slots (``financial_modeling.implied_price`` / ``dcf_result.implied_price``) that
    a withheld-target thesis leaves naked in structured. The directional
    ``recommendation`` is PRESERVED — a hard clause withholds the VALUE, not the
    verdict (绝不编数字: don't ship a fabricated/out-of-band number; do still judge).
    Every hard withhold calls this, so the C7 invariant — withheld ⇒ no headline
    survives in ANY slot — holds for C1/C1b/C2/C3/C4/C7 alike (TSLA $20.35
    resurrection)."""
    thesis = structured.get("thesis")
    if isinstance(thesis, dict):
        thesis["price_target"] = None
    # Flat headline slots (plain dcf `implied_price`, plain ddm `equity_value_per_share`)
    # — absent for equity_research, so this is a no-op there.
    for slot in ("implied_price", "equity_value_per_share", "target_price"):
        if structured.get(slot) is not None:
            structured[slot] = None
    # Nested fallback slots other consumers resurrected from (extract_target_price
    # is thesis-authoritative and ignores them, but the coverage list / signal lamp
    # read them directly — null them so the withhold is terminal everywhere).
    for parent_key in ("financial_modeling", "dcf_result"):
        parent = structured.get(parent_key)
        if isinstance(parent, dict) and parent.get("implied_price") is not None:
            parent["implied_price"] = None


#: C7's code, and the one thing the contract can file that is a CONSEQUENCE rather than a cause:
#: the scrub nulls a headline slot that survived a withhold. A reason record that names only this
#: is the lossiness §9.6 measured, so it is never promoted over a real cause (see `_withhold`).
_SCRUB_REASON_CODE = "HEADLINE_SLOT_RESURRECTED"


def _preserve_reason(existing: Any, metadata: dict[str, str]) -> "WithholdReason | None":
    """The upstream cause, with this gate's act merged into its metadata.

    ``None`` when no producer upstream named a cause (or the stored shape is unreadable, which is
    a payload problem the gate must not turn into a missing reason)."""
    record = as_withhold_reason(existing)
    if record is None:
        return None
    return record.model_copy(update={"metadata": {**record.metadata, **metadata}})


def _withhold(artifact: "Artifact", violations: list[tuple[ContractClause, Finding]]) -> None:
    """Degrade exactly as the numeric-audit gate does (builders.py): null the
    headline TARGET so it cannot resurrect, set valuation_withheld, and record
    machine evidence as [CONTRACT/*] warnings. The directional VERDICT is
    PRESERVED — a hard clause withholds the value, never the judgment (no "REVIEW"
    state any more). Type-agnostic: scrubs the authoritative thesis target, the flat
    per-share slots, and the nested fallback slots, so extract_target_price AND
    every direct consumer see None afterwards (the C7 invariant)."""
    structured = artifact.outputs.structured
    ids = [clause.id for clause, _ in violations]

    _scrub_headline_slots(structured)

    structured["valuation_withheld"] = True
    # Sync the synthesis' mirrored slot too. This gate is the LAST writer of the
    # signal — it runs at the persist boundary, after the builders' mirror — so
    # writing only the root would leave the two slots disagreeing: a C11 violation
    # the gate inflicted on itself (it would fire on the next read, and on every
    # re-enforcement), and a stale ``has_anchor_target`` for the readers of the
    # synthesis slot (``technical_payload`` reads ``valuation_synthesis``' copy).
    synthesis_block = structured.get("valuation_synthesis")
    if isinstance(synthesis_block, dict):
        synthesis_block["valuation_withheld"] = True

    # WHY the target is gone, structured (design §9.6). This gate is the LAST writer at the
    # persist boundary, and writing the reason slot unconditionally is exactly what the store
    # measured: 38 of its 43 withheld artifacts read `contract_C7` — the no-resurrection SCRUB,
    # an internal invariant — and named no cause a reader could act on. So an upstream cause (the
    # dial's, the numeric audit's) STANDS, with this gate's own act recorded beside it; only when
    # nothing upstream spoke does a firing clause's code become the cause, and it is the first one
    # in registry order — the registry's order IS the priority.
    metadata = {"clause_ids": "+".join(ids)}
    structured["withhold_reason"] = _preserve_reason(
        structured.get("withhold_reason"), metadata
    ) or withhold_reason(
        next(
            (
                clause.reason_code
                for clause, _ in violations
                if clause.reason_code and clause.reason_code != _SCRUB_REASON_CODE
            ),
            _SCRUB_REASON_CODE,
        ),
        metadata=metadata,
    )

    # The point-target conclusion is the tagline (a ≤60-char headline call that
    # often quotes the number) — neutralise it since the target is withheld. The
    # directional `recommendation` mirror is PRESERVED (verdict still ships); the
    # analysis body is untouched.
    narrative = artifact.outputs.llm_narrative
    if isinstance(narrative, dict):
        if "tagline" in narrative:
            narrative["tagline"] = None

    numeric_audit = structured.get("numeric_audit")
    if isinstance(numeric_audit, dict):
        numeric_audit["artifact_status"] = "caveated"

    for clause, finding in violations:
        # Internal-invariant clauses (C7's no-resurrection scrub) record evidence for
        # the audit trail but must NOT reach the analyst UI — the "/internal" sub-tag
        # makes the report parser skip them, exactly like "/note" and "/withheld".
        tag = clause.id if clause.surface else f"{clause.id}/internal"
        _append_warning(artifact, f"[CONTRACT/{tag}] {finding.evidence}")
    _append_warning(artifact, f"[CONTRACT/withheld] {_WITHHELD_NARRATIVE_STAMP}")


def _append_warning(artifact: "Artifact", warning: str) -> None:
    """Idempotent append — re-running the contract must not double-stamp."""
    if warning not in artifact.outputs.warnings:
        artifact.outputs.warnings.append(warning)
