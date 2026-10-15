"""One declaration per published arithmetic identity — the registry the compute
leaves, the artifact gate, the narrative scrubber and the cache all read.

Why this module exists (2026-10-14, the CF audit): every published number used to be
*recomputed wherever it was used*, and its lineage survived as prose. That is how one
report shipped two answers for one multiple — ``_ev_ebitda_method`` bridged net debt
only while the cross-check printed beside it bridged net debt + preferred + NCI
through ``ev_band_equity_per_share`` — and why the contract family had to grow a fifth
C10 clause to notice that a published ratio did not equal its own operands. The
identity was written out five times (``dcf.equity_bridge_value``,
``multiples.ev_band_equity_per_share``, ``multiples.implied_ev_multiple``,
``multiples.current_ev_ebitda``, ``sotp.compute_sotp_breakdown``) and documented three
ways (``technical_payload``, ``equity_research`` and ``routes/valuation`` still describe
EV/EBITDA as ``(market_cap + net_debt) / EBITDA`` while the code adds preferred and
NCI). A docstring claiming "single authority" is not a structural guarantee; a registry
with one evaluator is.

Design, deliberately boring:

* an identity is DATA — total, kind, form, weighted contributors, divisor — and
  :func:`evaluate` is the single evaluator over that data. No DSL, no codegen, no
  per-identity function that a caller could copy.
* the shape mirrors XBRL's calculation model (Calculations 1.1, total concept +
  contributing concepts + contribution weights), which is the battle-tested version of
  "a published total must equal its own components": see
  https://www.xbrl.org/Specification/calculation-1.1/REC-2023-02-22/calculation-1.1-REC-2023-02-22.html
  §4.2 (structure) and §5.1–5.2 (a calculation is checked only where it BINDS, and the
  tolerance comes from the published precision, not from a taste for round numbers).
* the operand-role vocabulary (component / total / gate) is the artifact-granularity
  version of OpenLineage's column-lineage transformations — DIRECT vs INDIRECT, and
  IDENTITY vs TRANSFORMATION vs AGGREGATION per output field:
  https://openlineage.io/docs/spec/facets/dataset-facets/column_lineage_facet/

``engine/models/`` is the leaf-import family ``artifact/contract.py`` may read
(``reconcile_tolerances`` / ``valuation_thresholds`` / ``numeric_claim``), so the gate
can walk this registry without importing ``compute/``, ``data/`` or ``pipelines/``.

Leaf: zero I/O. Its only non-stdlib import is the sibling tolerance leaf
(``reconcile_tolerances``), itself pure data — no compute, no provider, no artifact.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal

from finrobot.engine.models.reconcile_tolerances import IDENTITY_RESIDUAL_TOLERANCE

#: What KIND of quantity a number is. The distinction the 2026-10-14 CF audit needed:
#: a narrative whisperer rewrote "46.8% of the $15,783,943,454 enterprise value" into
#: "…of the $80.69 enterprise value" because nothing in the pipeline could tell a TOTAL
#: from a PER-SHARE figure — the only signal was a magnitude heuristic.
QuantityKind = Literal["per_share", "total_amount", "ratio", "multiple", "rate", "count"]

#: The role an operand plays in an identity:
#:
#: * ``component`` — summed with its weight: it MOVES the value.
#: * ``total`` — the result of ANOTHER identity. Refused as an operand: the balance-sheet
#:   identity total ``LiabilitiesAndStockholdersEquity`` equals Assets by definition, so
#:   reading it as a liabilities leaf computed NCI = −5,748,000,000 and both arithmetic
#:   checks still closed.
#: * ``gate`` — does not move the value; it decides whether two numbers are comparable at
#:   all (a vintage, a price basis, a period). OpenLineage's INDIRECT transformation.
#: * ``identity`` — the key names ANOTHER registered identity (``net_debt`` is
#:   ``total_debt − total_cash``). A caller that holds the collapsed number passes it
#:   directly; a reader with only the artifact's leaves gets it evaluated from the same
#:   operand mapping, so net debt is declared once instead of once per call site.
OperandRole = Literal["component", "total", "gate", "identity"]

#: How the total relates to its contributors.
IdentityForm = Literal["sum", "ratio", "product"]

#: What to do when an operand is absent (``None``). ``skip`` = the identity cannot bind,
#: so nothing is claimed about the value. ``zero`` = the pipeline's documented
#: assumed-0 (preferred stock and NCI are ``None`` for an issuer that carries neither,
#: and ``calculate_ev`` / the DCF bridge both treat that as 0) — the assumption is
#: already audited by ``operators/audit/ev_bridge.py``, which flags the unverifiable
#: case rather than letting it pass silently.
OnMissing = Literal["skip", "zero"]

#: Whether the artifact contract checks the identity end to end. ``exempt`` identities
#: are still declared (so their arithmetic has one home) but are enforced where the extra
#: context lives, never by the gate — see ``market_cap``.
ClauseCoverage = Literal["check", "exempt"]


@dataclass(frozen=True)
class Contributor:
    """One operand: its key, its contribution weight, its role, and its missing policy."""

    key: str
    weight: float = 1.0
    role: OperandRole = "component"
    on_missing: OnMissing = "skip"


@dataclass(frozen=True)
class Identity:
    """A published arithmetic relationship, declared once.

    ``total_path`` / ``operand_paths`` are the artifact's OWN dotted leaf paths
    (``raw_data`` blocks: ``market``, ``income``, ``balance``, ``valuation``), so the
    contract gate can check an identity against the artifact's own leaves without
    trusting any provenance record. An identity whose paths do not all resolve simply
    does not bind.
    """

    id: str
    total: str
    kind: QuantityKind
    form: IdentityForm
    contributors: tuple[Contributor, ...]
    divisor: str | None = None
    total_path: str | None = None
    operand_paths: tuple[tuple[str, str], ...] = ()
    divisor_path: str | None = None
    clause: ClauseCoverage = "check"
    note: str = ""

    @property
    def operand_keys(self) -> tuple[str, ...]:
        return tuple(c.key for c in self.contributors)


# --------------------------------------------------------------------------------------
# The registry
# --------------------------------------------------------------------------------------

#: EV = market cap + net debt + preferred + NCI. The one place this sum is written;
#: ``calculate_ev``, ``current_ev_ebitda``, the price-implied multiple and the SOTP
#: floor all call it. The debt legs stay collapsed as the ``net_debt`` identity so a
#: caller holding either shape (the pair, or one provider's net-debt figure) reads the
#: same declaration.
_EV_CONTRIBUTORS: tuple[Contributor, ...] = (
    Contributor("market_cap", 1.0),
    Contributor("net_debt", 1.0, role="identity"),
    Contributor("preferred_stock", 1.0, on_missing="zero"),
    Contributor("noncontrolling_interest", 1.0, on_missing="zero"),
)

#: EV → equity (the Damodaran / CFA bridge).
_EQUITY_CONTRIBUTORS: tuple[Contributor, ...] = (
    Contributor("enterprise_value", 1.0),
    Contributor("net_debt", -1.0, role="identity"),
    Contributor("preferred_stock", -1.0, on_missing="zero"),
    Contributor("noncontrolling_interest", -1.0, on_missing="zero"),
)

IDENTITIES: tuple[Identity, ...] = (
    Identity(
        id="net_debt",
        total="net_debt",
        kind="total_amount",
        form="sum",
        contributors=(
            Contributor("total_debt", 1.0),
            Contributor("total_cash", -1.0),
        ),
        operand_paths=(
            ("total_debt", "balance.total_debt"),
            ("total_cash", "balance.total_cash"),
        ),
        note=(
            "Declared so the collapse itself has one home: callers that hold the pair "
            "(the artifact's balance leaves) and callers that hold a provider's net-debt "
            "figure both feed the same EV and equity bridges. The artifact publishes no "
            "net-debt leaf, so these paths are what an identity that NESTS net_debt reads "
            "through (``leaf_paths``) — the fold is declared, never hard-coded per caller."
        ),
    ),
    Identity(
        id="ev_build",
        total="enterprise_value",
        kind="total_amount",
        form="sum",
        contributors=_EV_CONTRIBUTORS,
        total_path="valuation.enterprise_value",
        operand_paths=(
            ("market_cap", "market.market_cap"),
            ("preferred_stock", "balance.preferred_stock"),
            ("noncontrolling_interest", "balance.noncontrolling_interest"),
        ),
        note=(
            "The EV a provider reports was NOT necessarily built from the same instant's "
            "market cap as the run (the financials snapshot embeds its own, older quote). "
            "A residual here is a CLOCK difference, disclosed by the extractor against both "
            "instants — so the gate reports the residual but never treats it as a defect on "
            "its own (see C10e's vintage handling)."
        ),
    ),
    Identity(
        id="ev_to_equity",
        total="equity_value",
        kind="total_amount",
        form="sum",
        contributors=_EQUITY_CONTRIBUTORS,
        note=(
            "The bridge the DCF base case, its sensitivity grid, the reverse kernels, the "
            "Monte Carlo, the multiple band and SOTP all deduct. Before this registry, "
            "sotp.py deducted net debt ONLY: an option-premium name carrying preferred or "
            "NCI published an equity floor — and therefore an implied option premium — on a "
            "bridge that ignored a claim senior to common."
        ),
    ),
    Identity(
        id="ev_ebitda",
        total="ev_ebitda",
        kind="multiple",
        form="ratio",
        contributors=_EV_CONTRIBUTORS,
        divisor="ebitda_operating",
        total_path="valuation.ev_ebitda",
        operand_paths=(
            ("market_cap", "market.market_cap"),
            ("preferred_stock", "balance.preferred_stock"),
            ("noncontrolling_interest", "balance.noncontrolling_interest"),
        ),
        divisor_path="valuation.ebitda_operating",
        note=(
            "Including preferred and NCI settled the CF report's two-answers defect: a "
            "price-implied 4.9x beside a band whose own current point was 5.7x. Any "
            "consumer that rebuilds this ratio from market cap and net debt alone is now "
            "wrong by construction rather than differently opinionated."
        ),
    ),
    Identity(
        id="ev_revenue",
        total="ev_revenue",
        kind="multiple",
        form="ratio",
        contributors=_EV_CONTRIBUTORS,
        divisor="revenue",
        total_path="valuation.ev_revenue",
        operand_paths=(
            ("market_cap", "market.market_cap"),
            ("preferred_stock", "balance.preferred_stock"),
            ("noncontrolling_interest", "balance.noncontrolling_interest"),
        ),
        divisor_path="income.revenue",
    ),
    Identity(
        id="pe_ratio",
        total="pe_ratio",
        kind="multiple",
        form="ratio",
        contributors=(Contributor("market_cap", 1.0),),
        divisor="net_income",
        total_path="market.pe_ratio",
        operand_paths=(("market_cap", "market.market_cap"),),
        divisor_path="income.net_income",
        note=(
            "One net-income authority per report: the trailing P/E is market cap over the "
            "TTM net income the income-statement table prints (``market.pe_basis`` names "
            "that basis). A provider's own ``trailingPE`` rides diluted EPS and is a "
            "different denominator — declared, never mixed in."
        ),
    ),
    Identity(
        id="operating_margin",
        total="operating_margin",
        kind="ratio",
        form="ratio",
        contributors=(Contributor("operating_income", 1.0),),
        divisor="revenue",
        total_path="income.operating_margin",
        operand_paths=(("operating_income", "income.operating_income"),),
        divisor_path="income.revenue",
        note=(
            "C10e's founding case: CF published operating_margin 0.49325 beside "
            "3,025,000,000 / 7,738,999,808 = 0.39088 — above its own gross margin, and "
            "invisible to every provenance check because one provider supplied all three."
        ),
    ),
    Identity(
        id="ebitda_margin",
        total="ebitda_margin",
        kind="ratio",
        form="ratio",
        contributors=(Contributor("ebitda", 1.0),),
        divisor="revenue",
        total_path="income.ebitda_margin",
        operand_paths=(("ebitda", "income.ebitda"),),
        divisor_path="income.revenue",
    ),
    Identity(
        id="market_cap",
        total="market_cap",
        kind="total_amount",
        form="product",
        contributors=(
            Contributor("shares_outstanding", 1.0),
            Contributor("price", 1.0, role="gate"),
        ),
        total_path="market.market_cap",
        operand_paths=(
            ("shares_outstanding", "market.shares_outstanding"),
            ("price", "market.current_price"),
        ),
        clause="exempt",
        note=(
            "EXEMPT from the gate, deliberately: Yahoo derives marketCap = shares x price "
            "and FMP rederives the count as marketCap / price, so a residual here is a "
            "CLOCK difference between two independently cached canons, not an arithmetic "
            "error — CF's cap implied $117.25 against a $119.46 close (1.88%, exactly the "
            "'last session' move the report prints). It is enforced where the vintages are "
            "known: ``coordinators/extractor`` discloses a >1% divergence against the "
            "resolved quote. The price is declared a GATE because it fixes the instant the "
            "product describes."
        ),
    ),
)

#: What kind of quantity each PUBLISHED leaf is, keyed by its artifact path.
#:
#: This is the declaration the audit needed and nothing had. The post-run drift scrubber
#: (``equity_research._reconcile_narrative_targets``) rewrites a prose $-amount to the
#: canonical target unless it recognises the amount, and it recognised only magnitude:
#: "46.8% of the $15,783,943,454 enterprise value" was rewritten to "…of the $80.69
#: enterprise value" — a TOTAL restated as a PER-SHARE figure — while the magnitude
#: heuristic (10x every per-share reference, or >= $1,000,000) let a comma-form total
#: through. With the kind declared, "is this amount a published total?" is a lookup, not
#: a guess; the heuristic stays only for amounts that match no leaf at all.
#:
#: Only kinds that the pipeline actually publishes are listed. An unlisted leaf is
#: ``None`` — unknown, never assumed to be a per-share figure.
LEAF_KINDS: Mapping[str, QuantityKind] = {
    # market — the quote block: prices are per share, aggregates are totals.
    "market.current_price": "per_share",
    "market.price_52w_high": "per_share",
    "market.price_52w_low": "per_share",
    "market.market_cap": "total_amount",
    "market.shares_outstanding": "count",
    "market.pe_ratio": "multiple",
    "market.trailing_1y_return_pct": "rate",
    "market.beta": "rate",
    # income — flows are totals, margins are ratios.
    "income.revenue": "total_amount",
    "income.operating_income": "total_amount",
    "income.net_income": "total_amount",
    "income.ebitda": "total_amount",
    "income.gross_profit": "total_amount",
    "income.cost_of_revenue": "total_amount",
    "income.operating_cash_flow": "total_amount",
    "income.capital_expenditure": "total_amount",
    "income.free_cash_flow": "total_amount",
    "income.income_tax_expense": "total_amount",
    "income.interest_expense": "total_amount",
    "income.sga_expense": "total_amount",
    "income.rd_expense": "total_amount",
    "income.depreciation_amortization": "total_amount",
    "income.gross_margin": "ratio",
    "income.operating_margin": "ratio",
    "income.ebitda_margin": "ratio",
    "income.return_on_equity": "ratio",
    # balance — stocks are totals.
    "balance.total_debt": "total_amount",
    "balance.total_cash": "total_amount",
    "balance.preferred_stock": "total_amount",
    "balance.noncontrolling_interest": "total_amount",
    "balance.book_value_per_share": "per_share",
    # valuation — the derived block.
    "valuation.enterprise_value": "total_amount",
    "valuation.ev_ebitda": "multiple",
    "valuation.ev_ebitda_reported": "multiple",
    # The EBITDA the EV multiples divide by — a dollar amount, and the leaf the
    # `ev_ebitda` identity reads: undeclared, that identity fell back to the coarse
    # tolerance while every sibling was judged on its declared precision.
    "valuation.ebitda_operating": "total_amount",
    "valuation.ev_revenue": "multiple",
    "valuation.book_value_per_share": "per_share",
    # the report's own price level, when it is published into the snapshot.
    "target_price": "per_share",
    "entry_price": "per_share",
}


#: us-gaap (and vendor) tags that ARE an identity's total rather than a component of
#: one. Reading one of these as a component is the defect that published
#: noncontrolling interest of −5,748,000,000 on CF: ``LiabilitiesAndStockholdersEquity``
#: equals Assets BY DEFINITION (it is the balance sheet's own total, tagged twice), so
#: ``assets − liabilities`` collapsed to 0, ``parent + NCI`` collapsed to 0 with it, and
#: the wrong NCI closed every arithmetic check in the contract family.
#:
#: Declared here — beside the identities whose totals they are — so a provider concept
#: list can be validated against it at import instead of by review. The vocabulary is
#: deliberately small and explicit: a tag is listed only when it is DEFINITIONALLY a
#: total, never because a value looked too large.
IDENTITY_TOTAL_CONCEPTS: frozenset[str] = frozenset(
    {
        "LiabilitiesAndStockholdersEquity",
        "LiabilitiesAndStockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
        "us-gaap:LiabilitiesAndStockholdersEquity",
    }
)


def is_identity_total(concept: str) -> bool:
    """Whether ``concept`` is an identity TOTAL and must never be read as a component.

    Accepts the bare us-gaap local name and the namespace-qualified form, because the
    provider arms and the XBRL snapshot disagree about which they carry.
    """
    return concept in IDENTITY_TOTAL_CONCEPTS or concept.removeprefix("us-gaap:") in {
        c.removeprefix("us-gaap:") for c in IDENTITY_TOTAL_CONCEPTS
    }


#: The precision a published value of this KIND carries — XBRL's ``decimals`` attribute:
#: the power of ten the fact is asserted accurate AT (0 = whole units, 2 = the cent,
#: -3 = the thousand). It is what turns a tolerance from a taste for round numbers into
#: the interval the published figures actually denote: a value rounded to ``d`` decimals
#: denotes every number within half a unit of its last digit (Calculations 1.1 §5.2.3-5.2.4,
#: https://www.xbrl.org/Specification/calculation-1.1/REC-2023-02-22/calculation-1.1-REC-2023-02-22.html).
#:
#: The default follows the KIND, because the kind already says what the value IS: a
#: dollar amount reaches us rounded to the dollar (its unit), a quoted price to the cent,
#: and a ratio this pipeline computes itself is stored at full float precision and only
#: ever displayed to the digits the report prints (39.09% = 4 decimals of the fraction).
#: A leaf whose own precision differs from its kind's default gets an entry in
#: :data:`LEAF_DIGITS` rather than a second kind.
DEFAULT_DIGITS: Mapping[QuantityKind, int] = {
    "total_amount": 0,
    "count": 0,
    "per_share": 2,
    "multiple": 2,
    "ratio": 4,
    "rate": 2,
}

#: Leaves whose published precision is NOT their kind's default. Each entry is a claim
#: about the figure as the provider states it, so it carries its reason.
LEAF_DIGITS: Mapping[str, int] = {}


def leaf_kind(path: str) -> QuantityKind | None:
    """The declared kind of a published leaf, ``None`` when nothing declares it."""
    return LEAF_KINDS.get(path)


def leaf_digits(path: str) -> int | None:
    """The declared published precision of a leaf, ``None`` when nothing declares it.

    ``None`` is not "zero decimals" — it is "this leaf's precision is undeclared", and
    every consumer of it must fall back to an explicit band rather than pretend the
    figure is exact.
    """
    if path in LEAF_DIGITS:
        return LEAF_DIGITS[path]
    kind = leaf_kind(path)
    return DEFAULT_DIGITS.get(kind) if kind is not None else None


def leaves_of_kind(raw: Mapping[str, Any], kind: QuantityKind) -> dict[str, float]:
    """Every declared leaf of ``kind`` that the snapshot actually publishes."""
    found: dict[str, float] = {}
    for path, path_kind in LEAF_KINDS.items():
        if path_kind != kind:
            continue
        value = dig(raw, path)
        if value is not None:
            found[path] = value
    return found


_BY_ID: dict[str, Identity] = {i.id: i for i in IDENTITIES}

#: Bump when a declaration CHANGES MEANING (a contributor's weight, a divisor, a form,
#: a missing policy). Stored decisions and cache slots carry it so a value can never be
#: read against a different arithmetic than the one that produced it.
REGISTRY_VERSION = 1


def identity(identity_id: str) -> Identity:
    """The declaration for ``identity_id``; ``KeyError`` when it is not registered."""
    return _BY_ID[identity_id]


def checked_identities() -> tuple[Identity, ...]:
    """The identities the artifact gate can WALK, in declaration order.

    An identity the artifact publishes no total for (``net_debt``, ``ev_to_equity``) is
    enforced where it is used — every consumer calls :func:`evaluate` — but the gate
    cannot resolve it from an artifact's own leaves, so it is not walked here. Declaring
    it into this list produced a row of the measurement that could only ever read "never
    binds"; the nesting (``ev_build`` and ``ev_ebitda`` both read ``net_debt``) is what
    carries it into the gate.
    """
    return tuple(i for i in IDENTITIES if i.clause == "check" and i.total_path is not None)


# --------------------------------------------------------------------------------------
# Evaluation — the ONE implementation of each identity's arithmetic
# --------------------------------------------------------------------------------------


def _require(value: float | None, contributor: Contributor) -> float | None:
    if value is not None:
        return value
    if contributor.on_missing == "zero":
        return 0.0
    return None


def _sum(identity_id: str, operands: Mapping[str, float | None], depth: int) -> tuple[float, bool]:
    """Σ weight x operand. ``False`` when an operand is missing and cannot be assumed 0."""
    total = 0.0
    for contributor in identity(identity_id).contributors:
        if contributor.role == "total":
            raise ValueError(
                f"{identity_id}: operand {contributor.key!r} is the total of another "
                "identity and cannot be read as a component"
            )
        if contributor.role == "gate":
            continue
        if contributor.role == "identity":
            # The caller may hold the collapsed value (a provider's net-debt figure);
            # otherwise it is evaluated from the same mapping — never a second formula.
            value = operands.get(contributor.key)
            if value is None and depth < _MAX_NESTED_DEPTH and contributor.key in _BY_ID:
                value = evaluate(contributor.key, operands, _depth=depth + 1)
        else:
            value = _require(operands.get(contributor.key), contributor)
        if value is None:
            return 0.0, False
        total += contributor.weight * value
    return total, True


#: How deep one identity may nest another (``ev_ebitda`` → ``net_debt``). A guard, not a
#: budget: the registry is a DAG of finite depth, and a cycle is a declaration error.
_MAX_NESTED_DEPTH = 4


def evaluate(
    identity_id: str, operands: Mapping[str, float | None], *, _depth: int = 0
) -> float | None:
    """The identity's value from its operands, or ``None`` when it cannot be computed.

    ``None`` is the fail-closed answer the whole compute layer uses: a missing operand
    is not a zero (``zero``-policy contributors excepted, where the pipeline has already
    decided the assumption is sound and ``audit.ev_bridge`` audits it).

    Arithmetic only — no finiteness gate and no sanity band, because the callers differ
    (the DCF applies this to a NumPy array of enterprise values in the vectorized Monte
    Carlo, and ``math.isfinite`` does not accept an array). Callers that need a scalar
    use :func:`residual` or check ``math.isfinite`` themselves.
    """
    spec = identity(identity_id)
    numerator, ok = _sum(identity_id, operands, _depth)
    if not ok:
        return None
    if spec.form == "sum":
        return numerator
    if spec.form == "ratio":
        denominator = operands.get(spec.divisor or "")
        if denominator is None or denominator == 0:
            return None
        return numerator / denominator
    # product: the contributors multiply (weights are not meaningful here).
    product = 1.0
    for contributor in spec.contributors:
        value = operands.get(contributor.key)
        if value is None:
            return None
        product *= value
    return product


def binds(identity_id: str, operands: Mapping[str, float | None]) -> bool:
    """Whether the artifact supplies enough leaves for the identity to be checked.

    XBRL Calculations 1.1 §5.1 checks a calculation only where it BINDS: the total is
    present and the contributing concepts are. This registry is deliberately STRICTER
    than the specification at the second half — it requires every contributing operand,
    not "at least one" — because a report that publishes a total beside one of its three
    components has not stated arithmetic we can contradict. A residual is only ever
    reported against a complete identity.
    """
    spec = identity(identity_id)
    if spec.total_path is None:
        return False
    return evaluate(identity_id, operands) is not None


def relative_residual(
    identity_id: str,
    operands: Mapping[str, float | None],
    published: float | None,
) -> tuple[float, float] | None:
    """``(residual, expected)`` for a published value against its own operands, or None.

    The residual is RELATIVE to the larger magnitude so one tolerance means the same
    thing for a $0.40 margin and a 40x multiple. ``None`` when the identity does not
    bind, the published value is absent, or the operands are unusable — there is nothing
    to contradict.
    """
    if published is None or not binds(identity_id, operands):
        return None
    expected = evaluate(identity_id, operands)
    if expected is None or not math.isfinite(expected):
        return None
    scale = max(abs(published), abs(expected), 1e-9)
    return abs(published - expected) / scale, expected


def _half_ulp(digits: int) -> float:
    """Half a unit in the last declared digit: the interval a rounded value denotes."""
    return 0.5 * 10.0 ** (-digits)


def _summed_uncertainty(
    identity_id: str, operands: Mapping[str, float | None], depth: int = 0
) -> float | None:
    """Absolute uncertainty of Σ weight × operand, from the leaves' declared precision.

    XBRL accumulates the contributing facts' rounding intervals through the calculation:
    each operand contributes half a unit in its own last declared digit, scaled by
    |weight| (a subtracted operand is rounded exactly as much as an added one), and a
    nested identity contributes its own accumulation — ``net_debt`` is two rounded
    balance leaves, so the EV numerator carries both.

    ``None`` when any operand declares no precision (the caller must then say it used the
    fallback band), or when a nested identity cannot be resolved from the operands it was
    handed. A contributor the CALLER passed collapsed (a provider's own net-debt figure)
    is measured through the same leaf declarations as the derived one: both are dollar
    amounts of the same kind, and a per-caller precision would be a second thing to keep
    in sync.
    """
    spec = identity(identity_id)
    paths = dict(leaf_paths(identity_id))
    total = 0.0
    for contributor in spec.contributors:
        if contributor.role == "gate":
            continue
        if contributor.role == "identity":
            nested = (
                _summed_uncertainty(contributor.key, operands, depth + 1)
                if depth < _MAX_NESTED_DEPTH and contributor.key in _BY_ID
                else None
            )
            if nested is None:
                return None
            total += abs(contributor.weight) * nested
            continue
        path = paths.get(contributor.key)
        digits = leaf_digits(path) if path is not None else None
        if digits is None:
            return None
        total += abs(contributor.weight) * _half_ulp(digits)
    return total


def identity_tolerance(
    identity_id: str, operands: Mapping[str, float | None], published: float | None
) -> tuple[float, Literal["declared_precision", "fallback"]]:
    """``(relative tolerance, where it came from)`` for this identity's residual.

    The band the published figures' own precision allows, rather than a taste for round
    numbers: a total rounded to the dollar standing beside operands rounded to the dollar
    is only determinable to the sum of their half-units, and a ratio accumulates its
    operands' RELATIVE rounding. That is what lets one declaration govern a 5.7x multiple
    and a 0.39 margin alike (XBRL Calculations 1.1 §5.2.3-5.2.4, the rounded fact value
    interval).

    Falls back to ``IDENTITY_RESIDUAL_TOLERANCE`` — and NAMES the fallback, because a
    finding that cites the tolerance it was judged against is the difference between a
    number and an assertion — whenever a leaf the identity reads declares no precision,
    or the propagation is undefined (a zero divisor, an absent published value).

    Relative to the SAME scale :func:`relative_residual` uses (the larger magnitude), so
    the two are directly comparable. Digits are deliberately NOT part of
    :func:`identity_digest`: they judge the check's sensitivity, not what a stored value
    means, and a tolerance tweak must not invalidate cached canonicals.
    """
    fallback: tuple[float, Literal["declared_precision", "fallback"]] = (
        IDENTITY_RESIDUAL_TOLERANCE,
        "fallback",
    )
    spec = identity(identity_id)
    numerator, ok = _sum(identity_id, operands, 0)
    expected = evaluate(identity_id, operands)
    if not ok or expected is None or not math.isfinite(expected):
        return fallback
    numerator_uncertainty = _summed_uncertainty(identity_id, operands)
    if numerator_uncertainty is None:
        return fallback

    # For a SUM the published value IS the total, so its own rounding enters here and
    # must not be added a second time below (a ratio or product publishes a result the
    # operands do not already carry).
    published_counted = False
    if spec.form == "sum":
        total_digits = leaf_digits(spec.total_path or "")
        if total_digits is None or expected == 0:
            return fallback
        absolute = numerator_uncertainty + _half_ulp(total_digits)
        published_counted = True
    elif spec.form == "ratio":
        divisor = operands.get(spec.divisor or "")
        divisor_digits = leaf_digits(spec.divisor_path or "")
        if divisor is None or divisor == 0 or divisor_digits is None or numerator == 0:
            return fallback
        absolute = (numerator_uncertainty / abs(numerator)) * abs(expected) + _half_ulp(
            divisor_digits
        ) / abs(divisor) * abs(expected)
    else:
        # product: the contributors multiply, so their RELATIVE rounding adds.
        paths = dict(leaf_paths(identity_id))
        relative = 0.0
        for contributor in spec.contributors:
            value = operands.get(contributor.key)
            path = paths.get(contributor.key)
            digits = leaf_digits(path) if path is not None else None
            if value is None or value == 0 or digits is None:
                return fallback
            relative += _half_ulp(digits) / abs(value)
        absolute = relative * abs(expected)

    if not published_counted and published is not None and published != 0:
        published_digits = leaf_digits(spec.total_path or "")
        if published_digits is None:
            return fallback
        absolute += _half_ulp(published_digits)
    scale = max(abs(published or 0.0), abs(expected), 1e-9)
    return absolute / scale, "declared_precision"


def dig(raw: Mapping[str, Any], path: str) -> float | None:
    """A float at a dotted path inside an artifact's raw snapshot, None when absent.

    The one implementation of "read a declared leaf": a ratio's two sides live in
    different blocks (``valuation.enterprise_value`` against ``income.revenue``), and a
    report whose block is a list or a string is simply missing the leaf — never coerced
    to a number. ``bool`` is not a number here: ``True`` would otherwise read as 1.0 and
    quietly satisfy an identity.
    """
    node: Any = raw
    for part in path.split("."):
        if not isinstance(node, Mapping):
            return None
        node = node.get(part)
    if isinstance(node, bool) or not isinstance(node, int | float):
        return None
    return float(node)


def leaf_paths(identity_id: str, depth: int = 0) -> tuple[tuple[str, str], ...]:
    """Every leaf an identity needs, including the ones its nested identities declare.

    ``ev_ebitda`` needs ``net_debt``, and ``net_debt`` is two balance leaves — so the
    artifact reader resolves the operand the same way the caller does, from the same
    declaration, instead of hard-coding ``total_debt − total_cash`` a second time.
    """
    spec = identity(identity_id)
    paths: list[tuple[str, str]] = list(spec.operand_paths)
    if spec.divisor is not None and spec.divisor_path is not None:
        paths.append((spec.divisor, spec.divisor_path))
    for contributor in spec.contributors:
        if contributor.role == "identity" and depth < _MAX_NESTED_DEPTH:
            if contributor.key in _BY_ID:
                paths.extend(leaf_paths(contributor.key, depth + 1))
    return tuple(paths)


def artifact_operands(
    identity_id: str, raw: Mapping[str, Any]
) -> tuple[dict[str, float | None], float | None] | None:
    """``(operands, published total)`` for an identity read from an artifact's own leaves.

    ``None`` when the identity declares no artifact paths (a compute-only identity such
    as ``ev_to_equity``) — it is checked where it is used, not from a snapshot. Nested
    operands (``net_debt``) are left ABSENT on purpose, so :func:`evaluate` derives them
    from the leaves it was handed; a caller that supplies the collapsed number always
    wins over the derivation.
    """
    spec = identity(identity_id)
    if spec.total_path is None:
        return None
    operands = {key: dig(raw, path) for key, path in leaf_paths(identity_id)}
    return operands, dig(raw, spec.total_path)


def identity_digest() -> str:
    """A stable digest of the declared arithmetic (id, kind, form, contributors, divisor).

    The identity half of the cache's semantics identity (P4) and the number a
    derivation edge records: a cached row or a stored decision that was made under a
    different arithmetic must not be read as if it were made under this one — the Avro
    rule that data is decoded with the schema that WROTE it, never with whatever the
    reader happens to declare today
    (https://avro.apache.org/docs/1.12.0/specification/).
    """
    payload = [
        {
            "id": i.id,
            "kind": i.kind,
            "form": i.form,
            "divisor": i.divisor,
            "contributors": [(c.key, c.weight, c.role, c.on_missing) for c in i.contributors],
        }
        for i in IDENTITIES
    ]
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:12]
