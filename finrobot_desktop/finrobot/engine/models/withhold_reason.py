"""Why a value is withheld — one enumerated vocabulary (design §9.6, leaf layer).

Mirrors ``google.rpc.ErrorInfo`` (AIP-193): a stable ``reason_code``, the ``domain`` that groups
it, and ``metadata`` for every dynamic number. The structure exists because one string cannot
carry two facts, and the store proves it: of the 43 artifacts that ship withheld, **38 read
``contract_C7`` and not one of them records a cause a reader can act on** (measured 2026-10-14).
C7 is the no-resurrection SCRUB — an internal invariant, not a reason — and the last writer held
the only slot. A structured reason lets the CAUSE and the scrubs that followed it coexist.

Three rules, each enforced by a test rather than by good intentions:
  · a code is UPPER_SNAKE_CASE, ≤63 characters, and STABLE FOREVER — a reader's audit trail may
    key on it, so renaming one is a breaking change, not an edit;
  · ``(reason_code, domain)`` names exactly one logical cause — a code is never reused for
    another, and the vocabulary below is the only place one is spelled;
  · dynamic numbers live in ``metadata``, never in the code.
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field, ValidationError, field_validator

#: The domains a reason can belong to: the output-contract gate, the numeric audit, the data
#: layer's canonical selection, and the valuation synthesis' own dial. §9.6 names the first three
#: and treats the set as the grouping rule; the dial is a producer in its own right (it withholds
#: a point target without any clause firing), so it gets its own domain rather than being filed
#: under a gate it never ran.
WithholdDomain = Literal["audit", "contract", "data_authority", "valuation"]

#: THE enumerated vocabulary: code → the domain it belongs to. Declared once, here. Producers
#: name the constant they mean; a caller that spells a code itself has no way to be wrong quietly,
#: because :func:`withhold_reason` checks membership below.
WITHHOLD_CODES: dict[str, WithholdDomain] = {
    # — the output-contract gate (one code per H clause, declared on the clause itself) —
    "TARGET_OUT_OF_BAND": "contract",
    "METHODS_DIVERGENT": "contract",
    "MALFORMED_AMOUNT": "contract",
    "BASIS_CONTRADICTS_HEADLINE": "contract",
    "CALIBER_MISMATCH": "contract",
    "HEADLINE_SLOT_RESURRECTED": "contract",
    "VERDICT_VS_CROSS_CHECKS": "contract",
    "SPLIT_WRITER_CONVENTION": "contract",
    # — the producers that withhold without a clause firing —
    "NUMERIC_AUDIT_BLOCKED_FIELD": "audit",
    "VALUATION_DIAL_WITHHELD": "valuation",
}

#: §9.6's shape rule, verbatim: ``[A-Z][A-Z0-9_]+[A-Z0-9]``, 63 characters at most.
_CODE_RE = re.compile(r"[A-Z][A-Z0-9_]+[A-Z0-9]")
_CODE_MAX = 63


class WithholdReason(BaseModel):
    """The structured reason a value is withheld.

    ``reason_code`` is the CAUSE — what a reader can act on — and ``metadata`` carries the
    dynamic facts about *this* artifact (the clauses that fired, the counts, the source that was
    refused), so the code never has to grow a suffix to stay truthful.
    """

    reason_code: str = Field(
        description="Stable UPPER_SNAKE_CASE code from WITHHOLD_CODES; the cause, not the prose."
    )
    domain: WithholdDomain = Field(description="Which subsystem's vocabulary this code belongs to.")
    metadata: dict[str, str] = Field(
        default_factory=dict,
        description="Dynamic facts (clause ids, counts, refused sources) — never in the code.",
    )
    help_url: str | None = Field(
        default=None, description="Documentation for the code, when one exists (AIP-193's Help)."
    )

    @field_validator("reason_code")
    @classmethod
    def _code_shape(cls, value: str) -> str:
        if not _CODE_RE.fullmatch(value) or len(value) > _CODE_MAX:
            raise ValueError(
                f"reason_code must match {_CODE_RE.pattern!r} and be ≤{_CODE_MAX} chars "
                f"(got {value!r}) — §9.6 makes the code a stable public identifier"
            )
        return value


def as_withhold_reason(value: object) -> WithholdReason | None:
    """Read a reason however it is currently HELD — the model in memory, the dict a stored
    payload round-trips, or ``None`` when it is neither.

    One reader for every consumer, because the two shapes are the same fact at different moments:
    a producer writes the model into the in-memory ``structured`` dict, pydantic serialises it on
    save, and a stored payload therefore reads back as a dict. A consumer that accepts only one of
    them silently loses the reason — which is the failure mode that produced the 38 artifacts
    §9.6 measured, arriving a second time through a type instead of through an overwrite.
    """
    if isinstance(value, WithholdReason):
        return value
    if isinstance(value, dict):
        try:
            return WithholdReason.model_validate(value)
        except ValidationError:
            return None
    return None


def withhold_reason(
    reason_code: str,
    *,
    domain: WithholdDomain | None = None,
    metadata: dict[str, str] | None = None,
) -> WithholdReason:
    """Build a reason for a DECLARED code, or fail loudly.

    The single constructor producers use: it checks the code against the vocabulary (so a typo is
    an error, not a second code) and, when ``domain`` is omitted, takes the domain the code was
    declared with — the ``(reason_code, domain)`` pair can therefore never be assembled wrongly.
    """
    declared = WITHHOLD_CODES.get(reason_code)
    if declared is None:
        raise ValueError(
            f"{reason_code!r} is not a declared withhold reason code — add it to WITHHOLD_CODES "
            f"(a code spelled at a call site is how one cause ends up with two names)"
        )
    if domain is not None and domain != declared:
        raise ValueError(
            f"{reason_code!r} is declared in domain {declared!r}, not {domain!r} — one cause, "
            f"one (reason_code, domain) pair"
        )
    return WithholdReason(reason_code=reason_code, domain=declared, metadata=dict(metadata or {}))
