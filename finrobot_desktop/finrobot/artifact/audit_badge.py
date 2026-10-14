"""Read-time re-reading of a stored artifact under the live contract registry.

The persist gate (``artifact/contract.py``) judges an artifact ONCE, on the way in.
This module answers the other question design §9.3 draws: what would TODAY's clause
registry make of a payload that is already in the store? It is a READING, never a
verdict on the record — the record keeps its bytes (17 CFR 240.12b-15's amendment
rule is the domain's own answer to a wrong filed report), and the reader is given the
distinction explicitly:

  · ``would_withhold`` — the H clauses that fire on the stored payload. An artifact
    written before a rule was armed fires here, which is exactly the back catalogue's
    case and the badge's reason for existing.
  · ``would_annotate`` — the S clauses that fire: findings that only annotate. This
    is the ONLY reader channel they have: the gate writes them to
    ``outputs.warnings`` under the ``[CONTRACT/<id>/note]`` form, which the report's
    parser drops by design, so no page shows them today.
  · ``shipped_withheld`` / ``shipped_withheld_reason`` — the RECORD's own state, so
    a reader can tell "this report shipped withheld" from "today's rules would
    withhold it". A badge that read only the first half would accuse published
    reports, and §9.3's two readings are the argument for the whole design.

Zero I/O, no new rules: every entry is the registry's own pure
``check(artifact) -> Finding | None``, so there is exactly one definition of each rule
(doctrine 1 — a re-implementation in the API layer or in TypeScript would be a second
one). ``surface=False`` clauses are excluded because their evidence is engineering
plumbing the reader surface must not render (see :class:`ContractClause.surface`);
they still gate the record.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from finrobot.artifact.contract import CONTRACT_CLAUSES

if TYPE_CHECKING:
    from finrobot.artifact.models import Artifact


class AuditBadgeEntry(BaseModel):
    """One clause that fires on the stored payload, as the reader should see it."""

    id: str = Field(description="Clause id, e.g. ``C11``.")
    title: str = Field(
        description="The clause's own renderable title (declared once in the registry)."
    )
    evidence: str = Field(
        description="The finding's evidence for THIS artifact — the instance-level reason.",
    )


class AuditBadge(BaseModel):
    """The stored payload re-read under today's registry (design §9.3)."""

    would_withhold: list[AuditBadgeEntry] = Field(
        default_factory=list,
        description="H clauses that fire on the stored payload (the record is untouched).",
    )
    would_annotate: list[AuditBadgeEntry] = Field(
        default_factory=list,
        description="S clauses that fire — findings that only annotate.",
    )
    shipped_withheld: bool = Field(
        description="The record's own valuation_withheld flag, i.e. what the report shipped as.",
    )
    shipped_withheld_reason: str | None = Field(
        default=None,
        description="The record's own withheld_reason, when it withheld.",
    )


def derive_audit_badge(artifact: Artifact) -> AuditBadge:
    """Re-read ``artifact`` under ``CONTRACT_CLAUSES``. Pure; never mutates."""
    would_withhold: list[AuditBadgeEntry] = []
    would_annotate: list[AuditBadgeEntry] = []
    for clause in CONTRACT_CLAUSES:
        if not clause.surface:
            continue
        finding = clause.check(artifact)
        if finding is None:
            continue
        entry = AuditBadgeEntry(id=clause.id, title=clause.title, evidence=finding.evidence)
        if clause.severity == "H":
            would_withhold.append(entry)
        else:
            would_annotate.append(entry)

    structured = artifact.outputs.structured
    reason = structured.get("withheld_reason")
    return AuditBadge(
        would_withhold=would_withhold,
        would_annotate=would_annotate,
        shipped_withheld=structured.get("valuation_withheld") is True,
        shipped_withheld_reason=reason if isinstance(reason, str) else None,
    )
