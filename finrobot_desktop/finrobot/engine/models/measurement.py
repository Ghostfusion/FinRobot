"""One typed measurement — HOW a number was obtained (design §6, leaf layer ADR-0005).

Eight disclosure vocabularies exist in this tree, none of them machine-readable: the
``*_basis`` strings, ``data_authority.decisions[].basis``, ``withheld_reason``,
``degradation_note``, ``warnings[]``, the numeric-audit findings, the drift findings and the
mirrored ``valuation_withheld`` slots. This is the type they converge on, and it is deliberately
about PROVENANCE rather than about value: a number is only usable by a decision that knows
whether it was measured, stood in for, or deliberately not published.

    Present(value, source, period, as_of, derivation)  — measured, from the named source
    Proxy(value, proxy_of, disclosure)                 — a stand-in, with the reader's sentence
    Withheld(reason_code, evidence)                    — knowably not publishable, and why
    Unavailable(reason_code)                           — never obtained, and why

The hand-written precursors this replaces are already in the tree: ``None ≠ 0``, the
"industry levered beta proxy" label, ``withheld_no_operating_income_row`` and the margin
``basis`` strings (``row`` / ``provider_scalar``).

``use_proxy()`` is the point of the type. A consumer that wants a Proxy's NUMBER must call it
and name itself, which logs the disclosure — so a substitution cannot be silent: it leaves a
trail, and the alternative (reading ``.value`` off any measure) is not offered here. Producers
construct the Proxy at the point of substitution, where the disclosure is known.
"""

from __future__ import annotations

import logging
from typing import Annotated, Literal

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class Present(BaseModel):
    """The number was measured, and the measurement named its source."""

    kind: Literal["present"] = "present"
    value: float
    source: str = Field(
        description="Who produced it, in the reader's words (not a vendor id alone)."
    )
    period: str | None = Field(default=None, description="TTM / NTM / FY — None when not stated.")
    as_of: str | None = None
    derivation: list[str] = Field(
        default_factory=list,
        description="The inputs it was computed from, in order. Empty when none are declared.",
    )


class Proxy(BaseModel):
    """The number STANDS IN for the thing the report names — a sector multiple, an industry
    beta, a provider scalar computed on a basis the statement rows do not share.

    ``disclosure`` is the sentence a reader is owed; ``proxy_of`` names the field it stands in
    for. A consumer must read the value through :func:`use_proxy`, which records both.
    """

    kind: Literal["proxy"] = "proxy"
    value: float
    proxy_of: str = Field(description="The field this stands in for (e.g. ``gross_margin``).")
    disclosure: str = Field(
        description="Plain-language statement of the substitution, for the reader."
    )


class Withheld(BaseModel):
    """The number is knowably not publishable, and the reason is named.

    Not the same as a missing value: a withheld number was considered and refused, and the
    reason is what a reader needs to know whether to trust the rest of the block.
    """

    kind: Literal["withheld"] = "withheld"
    reason_code: str = Field(
        description=(
            "The code from the schema's one vocabulary, VERBATIM (design §9.6 fixes the shape; "
            "the live registry is lower_snake, and re-spelling it here would mint a second code "
            "for one cause — the normalization is §9.6's, in one pass over the vocabulary)."
        )
    )
    evidence: str = Field(description="The reader-facing sentence behind the code.")


class Unavailable(BaseModel):
    """The number was never obtained, and the reason is named."""

    kind: Literal["unavailable"] = "unavailable"
    reason_code: str = Field(description="The record's own code, verbatim — as above.")


#: The union. Additive changes only: every member carries a ``kind`` discriminator, so both the
#: payload and the TypeScript side can switch exhaustively on it.
Measure = Annotated[Present | Proxy | Withheld | Unavailable, Field(discriminator="kind")]


def use_proxy(measure: Proxy, *, consumer: str) -> float:
    """Read a Proxy's value, ACKNOWLEDGING the substitution.

    The only supported way for a consumer to get the number out of a :class:`Proxy`: it names
    itself, and the disclosure is logged, so "silent substitution" leaves a trail instead of
    being a missing warning. ``consumer`` is the module or surface doing the reading — not a
    person's name, and not free prose.
    """
    logger.warning(
        "proxy value used: %s substituted for %s (disclosure: %s) — consumer %s",
        measure.value,
        measure.proxy_of,
        measure.disclosure,
        consumer,
    )
    return measure.value
