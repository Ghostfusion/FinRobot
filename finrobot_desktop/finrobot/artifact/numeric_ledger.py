"""The artifact-layer numeric ledger (design §6).

One :class:`NumericClaim` per field a verifier filed a finding against, carrying what the
payload DECLARES about that number: its value, source, period and as_of, the report's own
basis for it, whether the value is non-authoritative (a proxy), and the lineage it was
selected under. The findings come from the artifact's own record, in the two places it keeps
them:

  · ``structured.numeric_audit.findings`` — the numeric-audit verifiers' verdicts, as stored;
  · the output-contract clauses, re-run exactly as ``derive_audit_badge`` re-runs them
    (``CONTRACT_CLAUSES`` is the single definition of every rule, doctrine 1).

WHY THE FINDINGS ARE THE SPINE AND THE CALIBER IS NOT. Measured over the stored corpus
(2026-10-14): of 204 numeric-audit findings over 16 distinct ``field_key``s, exactly **1**
names a registered :class:`~finrobot.artifact.field_registry.FieldCaliber`; of the 13
``field_key``s the contract clauses emit, **none** do. The registry keys by the version-diff's
DISPLAY fields (``wacc``, ``terminal_growth``, …) while findings key by payload path or rule
subject (``data_authority.ebitda``, ``thesis.price_target``, ``valuation_withheld``). So a
claim exists whenever a verifier filed, and the caliber is joined in only where one is
registered — it still contributes what only it knows (which currency a unit is quoted in, and
the period the field is defined over).

Pure and read-time, like the badge: a view of the stored payload under the live rule set,
never a mutation of the record (the archive keeps its bytes, §9.3).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import TypeAdapter

from finrobot.artifact.contract import CONTRACT_CLAUSES
from finrobot.artifact.field_registry import REGISTRY, FieldCaliber
from finrobot.engine.models.measurement import Measure, Proxy, Withheld, use_proxy
from finrobot.engine.models.identities import leaf_kind
from finrobot.engine.models.numeric_claim import Finding, NumericClaim

if TYPE_CHECKING:
    from finrobot.artifact.models import Artifact

#: The data-authority decision record keys a metric by its NAME (``ebitda``), while the
#: findings against it key by path (``data_authority.ebitda``). One prefix, one strip.
_DECISION_PREFIX = "data_authority."


def build_numeric_ledger(artifact: Artifact) -> list[NumericClaim]:
    """One claim per field that carries a finding, sorted by ``field_key``. Pure."""
    structured = _structured(artifact)
    grouped: dict[str, list[Finding]] = {}
    for finding in _stored_audit_findings(structured):
        grouped.setdefault(finding.field_key, []).append(finding)
    for clause in CONTRACT_CLAUSES:
        if not clause.surface:
            continue
        found = clause.check(artifact)
        if found is not None:
            grouped.setdefault(found.field_key, []).append(found)

    return [
        _claim(artifact, field_key, findings) for field_key, findings in sorted(grouped.items())
    ]


def _structured(artifact: Artifact) -> dict[str, Any]:
    structured = artifact.outputs.structured
    return structured if isinstance(structured, dict) else {}


def _raw(artifact: Artifact) -> dict[str, Any]:
    raw = artifact.inputs.raw_data
    return raw if isinstance(raw, dict) else {}


def _stored_audit_findings(structured: dict[str, Any]) -> list[Finding]:
    """The artifact's own numeric-audit findings, re-validated (a legacy payload may
    predate a severity or a field)."""
    block = structured.get("numeric_audit")
    if not isinstance(block, dict):
        return []
    out: list[Finding] = []
    for row in block.get("findings") or []:
        if isinstance(row, dict):
            try:
                out.append(Finding.model_validate(row))
            except (TypeError, ValueError):  # pragma: no cover - defensive on legacy rows
                continue
    return out


def _decision(artifact: Artifact, field_key: str) -> dict[str, Any] | None:
    """The data-authority decision for this field, when the field names one."""
    if not field_key.startswith(_DECISION_PREFIX):
        return None
    metric = field_key[len(_DECISION_PREFIX) :]
    decisions = (_raw(artifact).get("data_authority") or {}).get("decisions")
    if not isinstance(decisions, list):
        return None
    for row in decisions:
        if isinstance(row, dict) and row.get("metric") == metric:
            return row
    return None


def _provenance(artifact: Artifact) -> dict[str, Any]:
    provenance = _raw(artifact).get("provenance")
    return provenance if isinstance(provenance, dict) else {}


def _caliber(field_key: str) -> FieldCaliber | None:
    caliber = REGISTRY.get(field_key)
    return caliber if isinstance(caliber, FieldCaliber) else None


def _declared_measure(decision: dict[str, Any] | None) -> Measure | None:
    """The decision's own typed measurement (design §6), when the payload carries one."""
    if decision is None:
        return None
    row = decision.get("measure")
    if not isinstance(row, dict):
        return None
    try:
        return TypeAdapter(Measure).validate_python(row)
    except ValueError:  # pragma: no cover - defensive on a future member
        return None


def _is_proxy(decision: dict[str, Any] | None) -> bool:
    """Whether the record DECLARES this value a stand-in (design §6).

    The typed declaration is authoritative whenever it is present. Decisions stored before the
    measure shipped carry none, and for those the same signal is read from ``is_authoritative``
    — the archive is never rewritten (§9.3), so a legacy payload keeps its legacy reading.
    """
    if decision is None:
        return False
    declared = _declared_measure(decision)
    if declared is not None:
        return isinstance(declared, Proxy)
    return decision.get("is_authoritative") is False


def _resolve(artifact: Artifact, field_key: str) -> float | None:
    """The number the payload publishes at ``field_key``, read as a dotted path.

    ``structured`` first (where the report's own numbers live), then ``raw_data`` (where the
    data-authority decisions mirror the canonicals). A bool is never a number here —
    ``valuation_withheld`` is a flag, not a claim."""
    for source in (_structured(artifact), _raw(artifact)):
        node: Any = source
        for part in field_key.split("."):
            if not isinstance(node, dict) or part not in node:
                node = None
                break
            node = node[part]
        if isinstance(node, int | float) and not isinstance(node, bool):
            return float(node)
    return None


def _basis(artifact: Artifact, field_key: str, decision: dict[str, Any] | None) -> str | None:
    """The report's own words for how the number was produced, when it declares them: the
    decision's ``basis``, else the field's ``*_basis`` sibling (``thesis.price_target`` →
    ``thesis.price_target_basis`` — the same string the cover prints)."""
    measure = _declared_measure(decision)
    if isinstance(measure, Proxy):
        return measure.disclosure
    if isinstance(measure, Withheld):
        return measure.evidence
    if decision is not None:
        declared = decision.get("basis")
        if isinstance(declared, str) and declared:
            return declared
    head, _, leaf = field_key.rpartition(".")
    structured = _structured(artifact)
    container = structured.get(head) if head else structured
    if isinstance(container, dict):
        declared = container.get(f"{leaf}_basis")
        if isinstance(declared, str) and declared:
            return declared
    return None


def _derivation(decision: dict[str, Any] | None) -> list[str]:
    """The declared lineage — source, definition and policy version, in the order the
    record states them. Empty when the payload declares none, which is the absence the
    ledger measures rather than hides."""
    if decision is None:
        return []
    lineage = [
        ("source", decision.get("selected_source")),
        ("definition", decision.get("definition_version")),
        ("policy", decision.get("policy_version")),
    ]
    return [f"{label}:{value}" for label, value in lineage if isinstance(value, str) and value]


def _currency(
    artifact: Artifact, decision: dict[str, Any] | None, caliber: FieldCaliber | None
) -> str | None:
    """Quote currency for a per-share amount, reporting currency for a statement amount —
    the caliber says which when the field is registered; the decision's own unit says it
    when it is not."""
    raw = _raw(artifact)
    market = raw.get("market") if isinstance(raw.get("market"), dict) else {}
    if caliber is not None and caliber.currency_source == "reporting":
        reporting = raw.get("reporting_currency")
        return reporting if isinstance(reporting, str) else None
    if decision is not None:
        decided = decision.get("currency")
        if isinstance(decided, str):
            return decided
    quote = (market or {}).get("quote_currency") or raw.get("quote_currency")
    return quote if isinstance(quote, str) else None


def _period(artifact: Artifact, caliber: FieldCaliber | None) -> str | None:
    if caliber is not None and caliber.period is not None:
        return caliber.period
    declared = _provenance(artifact).get("period_basis")
    return declared.upper() if isinstance(declared, str) else None


def _claim(artifact: Artifact, field_key: str, findings: list[Finding]) -> NumericClaim:
    decision = _decision(artifact, field_key)
    caliber = _caliber(field_key)
    provenance = _provenance(artifact)
    value = _resolve(artifact, field_key)
    if value is None and decision is not None:
        decided = decision.get("value")
        value = float(decided) if isinstance(decided, int | float) else None
    measure = _declared_measure(decision)
    if isinstance(measure, Proxy):
        # A proxied number is read THROUGH the declaration (§6): it carries the value, and
        # use_proxy records which consumer took the substitution.
        value = use_proxy(measure, consumer="artifact.numeric_ledger")
    source = None
    if decision is not None and isinstance(decision.get("selected_source"), str):
        source = decision["selected_source"]
    elif isinstance(provenance.get("provider"), str):
        source = provenance["provider"]
    as_of = provenance.get("as_of")
    return NumericClaim(
        field_key=field_key,
        value=value,
        # The DECLARED kind of this field (identities.LEAF_KINDS), not an inference from
        # its magnitude: 46.8% of a $15.8B enterprise value is a total, and a consumer
        # that cannot tell that from a share price will restate one as the other.
        kind=leaf_kind(field_key),
        currency=_currency(artifact, decision, caliber),
        period=_period(artifact, caliber),
        source=source,
        as_of=as_of if isinstance(as_of, str) else None,
        findings=findings,
        basis=_basis(artifact, field_key, decision),
        is_proxy=_is_proxy(decision),
        derivation=_derivation(decision),
    )
