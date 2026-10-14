"""Metric-authority registry — ONE declared owner per published number.

The defect this closes is the class that produced the EV-bridge caveat
(``engine/compute/operators/audit/ev_bridge.py``): a number that reaches a report
with no declared owner. Two calibers can each claim to supply ``preferred_stock``
and nothing in the tree says which one is the producer of record, so a disagreement
between them cannot be *classified* — it can only be averaged away or ignored. The
same shape recurs wherever a metric can arrive from more than one place (FMP vs
yfinance vs SEC XBRL for a balance-sheet claim; a vendor field vs a computed
operator for ``enterprise_value``).

The model is borrowed from a sibling system's ``strategies/metric_authority.py``
(one ``MetricRow`` per measured metric, a ``resolve_metric`` resolver, a fail-closed
publication switch) and adapted to FinRobot's reality, which differs in one
important way: FinRobot's numbers come from **two kinds** of producer — a
deterministic operator, and a vendor statement read — so the row records which kind
it is and the ``implementation_ref`` points at the code symbol that owns the read in
either case. What is deliberately NOT borrowed is that system's second tolerance
(1% here vs 5% in its ``data_quality`` module): FinRobot keeps exactly one
``METRIC_TOLERANCE_PCT`` so there is one answer to "how far is a disagreement?".

Invariants enforced here (see the constructor, which refuses to build an unsound
row rather than trusting a reviewer to notice):

1. **One owner.** An ``ok`` row names a ``producer_id`` (a stable *semantic* owner,
   never a code path) plus a resolvable ``implementation_ref``
   (``"<module>::<symbol>"``). ``tests/unit/test_metric_authority.py`` resolves every
   ref against the live tree, so renaming a producer breaks a test instead of
   silently orphaning a metric.
2. **A refusal is a declaration too.** A row that cannot be owned is
   ``status="declined"`` and MUST carry a closed-vocabulary ``reason_code`` plus a
   ``citation`` — and MUST NOT carry a producer, a basis, a caliber list or a
   fallback list. That is the honest alternative to omitting the row: "no reachable
   producer states this" is a claim a reader can check, an absent row is not.
3. **``None`` is not ``0`` and not a default.** ``resolve_metric`` returns
   ``value=None`` with a status that says *why* — never ``0.0``, never a neutral
   fallback. A metric with no value from its producer of record is
   ``unavailable`` even when some *other* source quoted a number, because a
   fallback is not an authority.
4. **A disagreement is published, not reconciled.** The canonical value is always
   published; every other source outside ``tolerance_pct`` becomes a
   ``MetricConflict`` row carrying its own deviation. Nothing here averages two
   sources, and nothing picks a winner by argument order — the canonical is found
   by producer *identity*, so a caller cannot influence it by re-ordering a dict.

Leaf layer (ADR-0005): stdlib only, importable by ``engine/data`` (where two
calibers can disagree), ``engine/compute`` and ``artifact`` alike.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Literal, Mapping, Sequence

from finrobot.engine.models.measurement import Measure, Present, Proxy, Unavailable, Withheld

MetricKind = Literal["computed", "vendor"]
"""How the number is produced: by a deterministic operator, or read from a vendor
statement. Both are legitimate producers; the distinction matters because a vendor
read is caliber-dependent and a computed value is not."""

MetricStatus = Literal["ok", "declined"]
"""``ok`` — this metric has a producer of record. ``declined`` — it does not, and
the row names the reason instead of pretending."""

ResolutionStatus = Literal["ok", "conflict", "unavailable", "unknown", "declined"]
"""Outcome of one resolution.

``ok``           canonical value present, no other source disagreeing beyond tolerance
``conflict``     canonical value present, at least one source disagreeing
``unavailable``  the metric is declared but no producer-of-record value was supplied
``unknown``      the metric is not in the registry at all (a registry gap, not a
                 data gap — that distinction is the whole point of ``require_authority``)
``declined``     the metric is declared as unownable, with a cited reason
"""

DECLINED_REASON_CODES: frozenset[str] = frozenset(
    {
        "no_reachable_producer",
        "owner_decision_unwired",
        "provider_capability_absent",
        "stale_beyond_recency_policy",
    }
)
"""Closed vocabulary for why a metric is declined. Closed deliberately: a free-text
reason cannot be counted, and "why do we not state this number?" is a question that
gets asked in aggregate."""

METRIC_TOLERANCE_PCT = 0.01
"""Default relative-deviation tolerance (1%). Chosen to match the tolerance the
numeric-audit reconcile path already uses, so the registry cannot become a *third*
opinion about whether two numbers agree. Wide "keep the peace" tolerances are
exactly the silent reconciliation this module exists to prevent — a metric whose two
sources genuinely differ on basis needs two rows, not a looser band."""

COMPARABILITY_CLASSES: tuple[str, ...] = (
    "exact",  # numeric identity; unit+currency+period key must match
    "as_reported_period",  # as-reported flow (revenue, net_income, ebitda_reported…)
    "balance_period",  # balance-sheet point (total_cash, shares_outstanding…)
    "session_price",  # market price: bar session + quote currency
    "caliber_divergent",  # sources measure DIFFERENT things BY CONSTRUCTION
)
"""Closed vocabulary for WHAT two numbers must share before a numeric comparison
means anything. ``caliber_divergent`` is the honest class for EBITDA
(operating-vs-reported), total_debt (lease conventions) and vendor margins: an
alternative reading is recorded, never compared."""

DECISION_STATUSES: tuple[str, ...] = (
    "accepted",
    "fallback",
    "conflict",
    "unavailable",
    "definition_mismatch",
)
"""Closed vocabulary for the outcome of one reconciliation decision."""

DECISION_REASON_CODES: tuple[str, ...] = (
    "authoritative_selected",
    "sources_agree",
    "within_tolerance",
    "canonical_value_invalid_fallback_selected",
    "owner_absent_alternative_selected",
    "above_tolerance_published_flagged",
    "no_eligible_observation",
    "definition_mismatch_period",
    "definition_mismatch_currency",
    "definition_mismatch_unit",
    "definition_mismatch_caliber",
    "non_finite_value",
    "non_positive_value",
    "stale_beyond_freshness_policy",
    "after_run_as_of",
    "non_independent_agreement",
)
"""Closed vocabulary for WHY a decision came out the way it did. Closed so the
reasons can be counted in aggregate — "how often is the owner silent?" is a query,
"the numbers looked weird" is not."""

CONSUMER_IDS: tuple[str, ...] = ("valuation", "technical", "narrative", "screening", "audit")
"""Closed vocabulary of downstream consumers a metric feeds (the dependency graph)."""

POLICY_VERSION = "metric_authority_v1"
"""Version of the reconciliation policy. Bump when the RULES change (not when a
row is added): a stored decision must be readable against the policy that made it."""

_REF_SEPARATOR = "::"


def _validate_ref(ref: str) -> str:
    """Return ``ref`` if it is a resolvable ``"<module>::<symbol>"`` shape, else raise.

    Shape only — existence is checked against the live tree by the test, which is the
    only place that can import the module without turning a leaf model into an
    importer of the whole engine.
    """
    module, _, symbol = ref.partition(_REF_SEPARATOR)
    if not module or not symbol or _REF_SEPARATOR in symbol:
        raise ValueError(
            f"implementation_ref must be '<module>{_REF_SEPARATOR}<symbol>', got {ref!r}"
        )
    if module.endswith(".py") or "/" in module or "\\" in module:
        raise ValueError(
            f"implementation_ref must be a dotted module path, not a file path: {ref!r}"
        )
    if not module.startswith("finrobot."):
        raise ValueError(f"implementation_ref must name finrobot code, got {ref!r}")
    return ref


@dataclass(frozen=True)
class MetricRow:
    """One declaration: what a metric is, who owns it, and how far two sources may
    disagree before the difference is reportable.

    ``__post_init__`` is the enforcement point. An unsound row is a programming
    error, not a data condition, so it raises at import rather than degrading a
    report later.
    """

    metric: str
    """Canonical metric key, e.g. ``"enterprise_value"``. Unique across the registry."""

    definition: str
    """What the number IS, in words — the thing two sources must agree on before
    their disagreement means anything."""

    definition_version: str
    """Bumped when ``definition`` changes meaning (not when a producer is renamed),
    so a stored conflict can be read against the definition that produced it."""

    unit: str
    """e.g. ``"USD"`` / ``"ratio"`` / ``"pct"``. A source quoting a different unit is
    not a tolerable deviation — it is a different number (see ``unit_mismatch``)."""

    kind: MetricKind

    status: MetricStatus = "ok"

    producer_id: str | None = None
    """Stable SEMANTIC owner, e.g. ``"fmp.balance_sheet.preferred_stock"``. Never a
    code path — the code can be refactored, the ownership cannot move."""

    implementation_ref: str | None = None
    """``"<dotted.module>::<symbol>"`` — the code that produces it, resolved against
    the live tree in the test."""

    basis: str | None = None
    """The stated basis, e.g. ``"market_cap + total_debt + preferred + nci - cash"``.
    Published WITH the canonical value so a reader can tell a real disagreement from
    two sources measuring different things."""

    calibers: tuple[str, ...] = ()
    """Data calibers that can legitimately supply this metric (vendor kind). Named so
    a ``values`` mapping keyed by caliber resolves to the right owner."""

    fallbacks: tuple[str, ...] = ()
    """Recognized *non-canonical* sources. A fallback value is compared and reported,
    never promoted: a fallback is not an authority."""

    tolerance_pct: float = METRIC_TOLERANCE_PCT

    comparability: str = "exact"
    """Which semantic key two observations must share before a numeric comparison
    is meaningful (membership in :data:`COMPARABILITY_CLASSES`). Defaults to
    ``"exact"`` so every pre-existing row keeps today's behaviour."""

    consumers: tuple[str, ...] = ()
    """Downstream consumers that depend on this number (membership in
    :data:`CONSUMER_IDS`). The dependency graph §9 — empty when undeclared."""

    tolerance_abs: float | None = None
    """A MINIMUM-PROVABILITY FLOOR for the conflict test: a gap is a conflict only
    when the relative band is exceeded AND ``|a - b| > tolerance_abs``. This is the
    owner's "greater of one tick or 0.05%" rule for prices — a 2-cent gap on a
    $0.50 stock is inside the relative band and below the floor, so it is NOT
    flagged. ``None`` means the relative band alone decides."""

    freshness_max_age_s: float | None = None
    """Staleness bound: ``clock - observation.effective_at`` over this many seconds
    makes an observation ineligible. ``None`` = no freshness gate."""

    positive: bool = False
    """When ``True`` a value ``<= 0`` is ineligible with ``non_positive_value`` — a
    share count or a market cap of zero is not a small number, it is a wrong one."""

    key_field: bool = False
    """When ``True`` an over-tolerance candidate is a KEY divergence (surfaced as a
    structured ``degraded`` marker, not only prose)."""

    cross_validated: bool = False
    """When ``True`` this metric is part of the cross-provider PROSE-WARNING set the
    validator compares (income/balance items whose two providers report the same
    caliber). Distinct from ``key_field``: a metric can be cross-validated without
    being a KEY divergence, and (as with ``preferred_stock``) can have a decision
    record without ever producing a warning."""

    reason_code: str | None = None
    citation: str | None = None

    def __post_init__(self) -> None:
        if not self.metric or any(ch.isspace() for ch in self.metric):
            raise ValueError(f"metric must be a bare key, got {self.metric!r}")
        if not self.definition.strip():
            raise ValueError(f"{self.metric}: definition must not be empty")
        if not self.definition_version.strip():
            raise ValueError(f"{self.metric}: definition_version must not be empty")
        if not self.unit.strip():
            raise ValueError(f"{self.metric}: unit must not be empty")
        if not math.isfinite(self.tolerance_pct) or self.tolerance_pct <= 0:
            raise ValueError(f"{self.metric}: tolerance_pct must be finite and > 0")
        if self.comparability not in COMPARABILITY_CLASSES:
            raise ValueError(
                f"{self.metric}: comparability must be one of "
                f"{list(COMPARABILITY_CLASSES)}, got {self.comparability!r}"
            )
        unknown_consumers = [c for c in self.consumers if c not in CONSUMER_IDS]
        if unknown_consumers:
            raise ValueError(
                f"{self.metric}: unknown consumer id(s) {unknown_consumers}; expected "
                f"members of {list(CONSUMER_IDS)}"
            )
        if self.tolerance_abs is not None and (
            not math.isfinite(self.tolerance_abs) or self.tolerance_abs <= 0
        ):
            raise ValueError(f"{self.metric}: tolerance_abs must be finite and > 0")
        if self.freshness_max_age_s is not None and (
            not math.isfinite(self.freshness_max_age_s) or self.freshness_max_age_s <= 0
        ):
            raise ValueError(f"{self.metric}: freshness_max_age_s must be finite and > 0")

        if self.status == "declined":
            if self.reason_code not in DECLINED_REASON_CODES:
                raise ValueError(
                    f"{self.metric}: a declined row needs a reason_code from "
                    f"{sorted(DECLINED_REASON_CODES)}, got {self.reason_code!r}"
                )
            if not (self.citation or "").strip():
                raise ValueError(
                    f"{self.metric}: a declined row must cite where the refusal comes from"
                )
            for name, value in (
                ("producer_id", self.producer_id),
                ("implementation_ref", self.implementation_ref),
                ("basis", self.basis),
            ):
                if value:
                    raise ValueError(
                        f"{self.metric}: a declined row must not carry {name} — a refusal "
                        f"that also claims an owner is two answers to one question"
                    )
            if self.calibers or self.fallbacks:
                raise ValueError(
                    f"{self.metric}: a declined row must not list calibers/fallbacks — "
                    f"naming a fallback would imply a number is available"
                )
            if (
                self.consumers
                or self.key_field
                or self.tolerance_abs is not None
                or self.cross_validated
            ):
                raise ValueError(
                    f"{self.metric}: a declined row must not carry "
                    f"consumers/key_field/tolerance_abs/cross_validated — an unowned "
                    f"number has no dependency graph, no key divergence, no band to "
                    f"measure it, and nothing to cross-validate"
                )
            return

        producer_id = (self.producer_id or "").strip()
        if not producer_id:
            raise ValueError(f"{self.metric}: an ok row must name its producer_id")
        for forbidden in ("::", ".py", "/", "\\"):
            if forbidden in producer_id:
                raise ValueError(
                    f"{self.metric}: producer_id is a semantic owner, not a code path "
                    f"— found {forbidden!r} in {producer_id!r}"
                )
        implementation_ref = self.implementation_ref or ""
        if not implementation_ref:
            raise ValueError(f"{self.metric}: an ok row must name its implementation_ref")
        _validate_ref(implementation_ref)
        if not (self.basis or "").strip():
            raise ValueError(f"{self.metric}: an ok row must state the basis of its number")
        if self.kind == "vendor" and not self.calibers:
            raise ValueError(
                f"{self.metric}: a vendor-sourced metric must name at least one caliber"
            )


@dataclass(frozen=True)
class MetricConflict:
    """One source disagreeing with the producer of record, beyond tolerance."""

    source: str
    value: float
    deviation_pct: float
    """``|other - canonical| / max(|other|, |canonical|, 1e-9)`` — relative, so the
    same band reads the same on a $2B and a $200B balance sheet."""


@dataclass(frozen=True)
class MetricResolution:
    """The answer for one metric: the canonical value WITH its basis, plus whatever
    disagreed. Immutable and fully serialisable — this is what a consumer publishes
    or renders; it never re-derives a number."""

    metric: str
    status: ResolutionStatus
    value: float | None
    producer_id: str | None = None
    implementation_ref: str | None = None
    basis: str | None = None
    definition: str | None = None
    definition_version: str | None = None
    unit: str | None = None
    spread_pct: float | None = None
    """Widest deviation among the conflicts — the one number a banner needs."""
    conflicts: tuple[MetricConflict, ...] = ()
    reason_code: str | None = None
    citation: str | None = None

    @property
    def is_publishable(self) -> bool:
        """True when the canonical value may be printed. A ``conflict`` is still
        publishable on purpose: the canonical is the owner's number, and hiding it
        would remove the very value the conflict is measured against."""
        return self.value is not None and self.status in ("ok", "conflict")


@dataclass(frozen=True)
class _Sources:
    canonical_key: str | None
    others: tuple[tuple[str, float], ...] = field(default_factory=tuple)


def _resolution(
    row: MetricRow,
    *,
    status: ResolutionStatus,
    value: float | None,
    reason_code: str | None = None,
    citation: str | None = None,
    conflicts: tuple[MetricConflict, ...] = (),
    spread_pct: float | None = None,
) -> MetricResolution:
    """Build a resolution that always echoes the row's declaration.

    Every resolution carries the definition, ownership, basis and unit it was
    resolved against, so a consumer renders provenance without a second registry
    lookup and a *stored* resolution stays readable if the registry later changes.
    """
    return MetricResolution(
        metric=row.metric,
        status=status,
        value=value,
        producer_id=row.producer_id,
        implementation_ref=row.implementation_ref,
        basis=row.basis,
        definition=row.definition,
        definition_version=row.definition_version,
        unit=row.unit,
        spread_pct=spread_pct,
        conflicts=conflicts,
        reason_code=reason_code,
        citation=citation,
    )


def _finite(value: float | None) -> float | None:
    """A non-finite quote is not a value — treat it as absent rather than letting
    NaN propagate into a deviation (NaN comparisons are all False, so a NaN would
    silently pass every tolerance test)."""
    if value is None:
        return None
    return value if math.isfinite(value) else None


def _relative_deviation(other: float, canonical: float) -> float:
    return abs(other - canonical) / max(abs(other), abs(canonical), 1e-9)


def _split_sources(row: MetricRow, values: Mapping[str, float | None]) -> _Sources:
    """Partition caller-supplied values into (canonical key, comparable others).

    The canonical is chosen by producer IDENTITY — ``producer_id`` first, then
    ``implementation_ref`` — so a caller cannot change the answer by re-ordering the
    mapping. Everything else with a finite value is compared, including a key the
    registry does not know: an unrecognized source's number disagreeing with the
    owner is exactly the signal worth surfacing.
    """
    canonical_key: str | None = None
    for candidate in (row.producer_id, row.implementation_ref):
        if candidate is not None and _finite(values.get(candidate)) is not None:
            canonical_key = candidate
            break

    others: list[tuple[str, float]] = []
    for source, raw in values.items():
        if source == canonical_key:
            continue
        valued = _finite(raw)
        if valued is not None:
            others.append((source, valued))
    return _Sources(canonical_key=canonical_key, others=tuple(others))


def _row_stamp(row: MetricRow, **overrides: object) -> dict[str, object]:
    """The fields every resolution echoes so a consumer never has to look the row up
    again to render provenance."""
    base: dict[str, object] = {
        "metric": row.metric,
        "producer_id": row.producer_id,
        "implementation_ref": row.implementation_ref,
        "basis": row.basis,
        "definition": row.definition,
        "definition_version": row.definition_version,
        "unit": row.unit,
    }
    base.update(overrides)
    return base


def resolve_metric(
    metric: str,
    values: Mapping[str, float | None],
    *,
    require_authority: bool = False,
) -> MetricResolution:
    """Resolve one metric against its producer of record.

    Args:
        metric: Registry key (``"enterprise_value"``).
        values: ``{source_id: value | None}`` — source ids are producer ids,
            implementation refs, caliber names or fallback names. A source the
            registry does not recognize is still compared (it is a disagreement, not
            noise).
        require_authority: The fail-closed switch. ``False`` (default) preserves the
            honest-but-permissive reading: an unregistered metric is ``unknown`` and a
            declined metric is ``declined``, and both still name themselves. ``True``
            turns "nobody owns this" into ``unavailable`` — the state in which a
            consumer must NOT publish a number — which is what a caller wiring this
            into publication wants.

    Returns:
        A :class:`MetricResolution`. ``value`` is ``None`` unless the producer of
        record supplied a finite value: a fallback's or a second caliber's number
        never becomes the canonical answer.
    """
    row = METRIC_REGISTRY_BY_NAME.get(metric)

    if row is None:
        return MetricResolution(
            metric=metric,
            status="unavailable" if require_authority else "unknown",
            value=None,
            reason_code="no_reachable_producer",
            citation=(
                "not declared in engine/models/metric_authority.py — no producer of "
                "record, so no number may be published as authoritative"
            ),
        )

    if row.status == "declined":
        return MetricResolution(
            metric=metric,
            status="unavailable" if require_authority else "declined",
            value=None,
            definition=row.definition,
            definition_version=row.definition_version,
            unit=row.unit,
            reason_code=row.reason_code,
            citation=row.citation,
        )

    sources = _split_sources(row, values)
    canonical_value = (
        _finite(values.get(sources.canonical_key)) if sources.canonical_key is not None else None
    )

    if canonical_value is None:
        # The owner was silent. A number from somewhere else is not a substitute:
        # publishing a fallback as the metric's value is exactly the un-owned number
        # this registry exists to stop.
        return _resolution(
            row,
            status="unavailable",
            value=None,
            reason_code="no_reachable_producer",
            citation=(
                f"producer of record {row.producer_id!r} supplied no value"
                + (
                    f"; {len(sources.others)} other source(s) did, but a fallback is "
                    f"not an authority"
                    if sources.others
                    else ""
                )
            ),
        )

    conflicts = tuple(
        MetricConflict(
            source=source,
            value=other,
            deviation_pct=_relative_deviation(other, canonical_value),
        )
        for source, other in sorted(sources.others)
        if _relative_deviation(other, canonical_value) > row.tolerance_pct
    )

    return _resolution(
        row,
        status="conflict" if conflicts else "ok",
        value=canonical_value,
        spread_pct=max((c.deviation_pct for c in conflicts), default=None),
        conflicts=conflicts,
    )


METRIC_REGISTRY: tuple[MetricRow, ...] = (
    # --- computed: a deterministic operator owns the number -------------------
    MetricRow(
        metric="enterprise_value",
        definition="Market value of the operating business: equity + debt + preferred + NCI - cash.",
        definition_version="ev_1",
        unit="USD",
        kind="computed",
        producer_id="multiples.calculate_ev",
        implementation_ref="finrobot.engine.compute.operators.multiples::calculate_ev",
        basis="market_cap + total_debt + preferred_stock + noncontrolling_interest - cash",
    ),
    MetricRow(
        metric="ev_ebitda",
        definition="Enterprise value over trailing-twelve-month EBITDA.",
        definition_version="ev_ebitda_1",
        unit="ratio",
        kind="computed",
        producer_id="multiples.current_ev_ebitda",
        implementation_ref="finrobot.engine.compute.operators.multiples::current_ev_ebitda",
        basis="enterprise_value / ttm_ebitda (None when either leg is absent)",
    ),
    MetricRow(
        metric="wacc",
        definition="Weighted average cost of capital used as the DCF discount rate.",
        definition_version="wacc_1",
        unit="pct",
        kind="computed",
        producer_id="wacc.calculate_wacc",
        implementation_ref="finrobot.engine.compute.operators.wacc::calculate_wacc",
        basis="capm cost of equity weighted by market-value debt/equity mix",
    ),
    MetricRow(
        metric="ttm_fcf",
        definition="Free cash flow over the trailing twelve months.",
        definition_version="ttm_fcf_1",
        unit="USD",
        kind="computed",
        producer_id="multiples.compute_ttm_fcf",
        implementation_ref="finrobot.engine.compute.operators.multiples::compute_ttm_fcf",
        basis="sum of the last four reported operating cash flow less capex quarters",
    ),
    MetricRow(
        metric="dcf_value_per_share",
        definition="Per-share intrinsic value from the discounted-cash-flow model.",
        definition_version="dcf_1",
        unit="USD",
        kind="computed",
        producer_id="dcf.calculate_dcf",
        implementation_ref="finrobot.engine.compute.operators.dcf::calculate_dcf",
        basis="projected FCF discounted at WACC, terminal value, less net debt, per share",
    ),
    # --- vendor: a caliber-dependent statement read owns the number -----------
    MetricRow(
        metric="preferred_stock",
        definition="Carrying value of preferred equity outstanding (a claim ranking ahead of common).",
        definition_version="preferred_stock_1",
        unit="USD",
        kind="vendor",
        producer_id="fmp.balance_sheet.preferred_stock",
        implementation_ref="finrobot.engine.data.providers.fmp_provider::FMPProvider",
        basis="issuer balance sheet, latest reported period",
        calibers=("fmp", "yfinance", "sec_edgar"),
        fallbacks=(
            "yfinance.balance_sheet.preferred_stock",
            "sec_edgar.xbrl.PreferredStockValue",
        ),
    ),
    MetricRow(
        metric="noncontrolling_interest",
        definition="Carrying value of noncontrolling (minority) interests in consolidated subsidiaries.",
        definition_version="noncontrolling_interest_1",
        unit="USD",
        kind="vendor",
        producer_id="fmp.balance_sheet.minority_interest",
        implementation_ref="finrobot.engine.data.providers.fmp_provider::FMPProvider",
        basis="issuer balance sheet, latest reported period",
        calibers=("fmp", "yfinance"),
        fallbacks=("yfinance.balance_sheet.minority_interest",),
    ),
    # --- vendor: cross-provider comparable fundamentals -----------------------
    #
    # Tolerance calibration moved INTO the registry from engine/data/validator.py's
    # module docstring — the registry is the ONE home of the band, and the validator
    # reads it back through compared_fields()/key_fields() instead of restating it.
    # Evidence (dates + measured numbers) lives on each row below; the validator
    # docstring keeps its prose but is no longer the source of truth for a number.
    #
    # revenue / net_income: 15% relative, chosen to cover ONE QUARTER of timing drift
    #   between two providers' fiscal periods; as-reported in both, genuine
    #   like-for-like checks (KEY fields — an over-tolerance hit is a structured
    #   Provenance.degraded marker, not just prose).
    # total_cash: 10% relative, re-enabled 2026-06-08 once FMP adopted the
    #   cash + short-term-investments caliber that matches yfinance's ``total_cash``
    #   (a divergence is now a genuine period/classification signal).
    # market_cap: 5% relative — real-time vs delayed should still be close.
    MetricRow(
        metric="revenue",
        definition="Total revenue (as-reported top line) for the stated fiscal period.",
        definition_version="revenue_1",
        unit="USD",
        kind="vendor",
        producer_id="fmp.income_statement.revenue",
        implementation_ref="finrobot.engine.data.providers.fmp_provider::FMPProvider",
        basis="as-reported income statement, trailing twelve months",
        calibers=("fmp",),
        fallbacks=(
            "yfinance.income_statement.revenue",
            "sec_edgar.xbrl.RevenueFromContractWithCustomerExcludingAssessedTax",
        ),
        comparability="as_reported_period",
        consumers=("valuation", "narrative", "audit"),
        tolerance_pct=0.15,
        key_field=True,
        cross_validated=True,
    ),
    MetricRow(
        metric="net_income",
        definition="Net income attributable to the issuer for the stated fiscal period.",
        definition_version="net_income_1",
        unit="USD",
        kind="vendor",
        producer_id="fmp.income_statement.net_income",
        implementation_ref="finrobot.engine.data.providers.fmp_provider::FMPProvider",
        basis="as-reported income statement, trailing twelve months",
        calibers=("fmp",),
        fallbacks=("yfinance.income_statement.net_income", "sec_edgar.xbrl.NetIncomeLoss"),
        comparability="as_reported_period",
        consumers=("valuation", "narrative", "audit"),
        tolerance_pct=0.15,
        key_field=True,
        cross_validated=True,
    ),
    MetricRow(
        metric="total_cash",
        definition=(
            "Cash and near-cash: cash & equivalents PLUS short-term investments "
            "(the EV-net-of-cash caliber)."
        ),
        definition_version="total_cash_1",
        unit="USD",
        kind="vendor",
        producer_id="fmp.balance_sheet.total_cash",
        implementation_ref="finrobot.engine.data.providers.fmp_provider::FMPProvider",
        basis="as-reported balance sheet, cash + short-term investments, latest period",
        calibers=("fmp",),
        fallbacks=(
            "yfinance.balance_sheet.total_cash",
            "sec_edgar.xbrl.CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
        ),
        comparability="balance_period",
        consumers=("valuation", "audit"),
        tolerance_pct=0.10,
        cross_validated=True,
    ),
    MetricRow(
        metric="market_cap",
        definition="Market value of common equity outstanding.",
        definition_version="market_cap_1",
        unit="USD",
        kind="vendor",
        producer_id="fmp.profile.market_cap",
        implementation_ref="finrobot.engine.data.providers.fmp_provider::FMPProvider",
        basis="live profile quote-currency market cap at the snapshot instant",
        calibers=("fmp",),
        fallbacks=("yfinance.quote.market_cap", "finnhub.profile.market_cap"),
        comparability="exact",
        consumers=("valuation", "screening", "audit"),
        tolerance_pct=0.05,
        positive=True,
        cross_validated=True,
    ),
    # current_price's owner is the LEADER of the price chain, not the vendor we
    # happened to route to first. ``categories.PRIORITY[Category.core_stock_apis]`` is
    # ``("eodhd", "moomoo", "fmp", "yfinance", ...)`` — owner policy 2026-10-12:
    # "FMP's free quota is exhausted in practice — every quote/price fetch 429s —
    # while EODHD's plan serves prices and moomoo's gateway serves quotes, so the
    # previous FMP-first order burned a timeout per call before falling through".
    # The registry must not contradict the priority table it is authoritative about:
    # with FMP as owner, EVERY live price decision read "the producer of record never
    # spoke" (logged EHC run: eodhd 124.33 → owner_absent_alternative_selected),
    # noise rather than signal. calibers lists the chain IN ORDER; its first entry is
    # the producer of record.
    MetricRow(
        metric="current_price",
        definition="Last-traded price for the bar session, in the quote currency.",
        definition_version="current_price_1",
        unit="USD",
        kind="vendor",
        producer_id="eodhd.quote.current_price",
        implementation_ref="finrobot.engine.data.providers.eodhd_provider::EODHDProvider",
        basis="delayed quote / last daily bar close, quote currency",
        calibers=("eodhd", "moomoo", "fmp", "yfinance"),
        fallbacks=(
            "moomoo.quote.current_price",
            "fmp.quote.current_price",
            "yfinance.quote.current_price",
        ),
        comparability="session_price",
        consumers=("valuation", "technical", "narrative", "audit"),
        tolerance_pct=0.05,
        tolerance_abs=0.01,
        freshness_max_age_s=5 * 24 * 3600,
        positive=True,
    ),
    MetricRow(
        metric="shares_outstanding",
        definition="Common shares outstanding as reported by the issuer.",
        definition_version="shares_outstanding_1",
        unit="shares",
        kind="vendor",
        producer_id="fmp.shares_float.shares_outstanding",
        implementation_ref="finrobot.engine.data.providers.fmp_provider::FMPProvider",
        basis="as-reported share count, latest period (FMP may rederive as marketCap/price)",
        calibers=("fmp",),
        fallbacks=("yfinance.balance_sheet.shares_outstanding", "finnhub.profile.shares"),
        comparability="balance_period",
        consumers=("valuation", "audit"),
        tolerance_pct=0.05,
        positive=True,
    ),
    # --- caliber_divergent: a number whose two sources measure DIFFERENT things ---
    #
    # These three are NOT cross-provider comparable BY CONSTRUCTION. They carry a
    # real producer of record; an eligible alternative reading is recorded with
    # definition_mismatch_caliber and NEVER changes the decision status. Putting
    # them in the registry (rather than OMITTING them from the validator, as the
    # docstring did) makes the refusal inspectable: "we serve FMP's caliber" is now
    # a declaration, not an absence.
    #
    # ebitda: FMP path serves OPERATING-caliber EBITDA (EBIT + D&A, our own
    #   derivation); yfinance returns REPORTED-caliber ``info.ebitda``
    #   (NI + tax + interest + D&A). At 15% this is apples-to-oranges — it falsely
    #   "agrees" for cash-rich firms and falsely alarms elsewhere. Live-verified
    #   TSLA: FMP ebitda runs 9–18% ABOVE OI+D&A per year on the bottom-up caliber.
    MetricRow(
        metric="ebitda",
        definition=(
            "Earnings before interest, tax, depreciation and amortisation on the "
            "OPERATING caliber (EBIT + D&A), trailing twelve months."
        ),
        definition_version="ebitda_1",
        unit="USD",
        kind="vendor",
        producer_id="fmp.income_statement.ebitda_operating",
        implementation_ref="finrobot.engine.data.providers.fmp_provider::FMPProvider",
        basis="operating-caliber EBITDA = EBIT + D&A, trailing twelve months",
        calibers=("fmp",),
        fallbacks=("yfinance.info.ebitda",),
        comparability="caliber_divergent",
        consumers=("valuation", "audit"),
        tolerance_pct=0.15,
    ),
    # total_debt: removed 2026-06-06 — the providers mix balance-sheet LEASE
    #   CONVENTIONS. FMP's ``total_debt`` carries bonds + finance leases while
    #   yfinance bundles operating leases too (MSFT: FMP $57B vs yfinance $125B) —
    #   a caliber gap, not a data error, and not arbitrated downstream.
    MetricRow(
        metric="total_debt",
        definition=(
            "Total interest-bearing debt including lease obligations, on the vendor's "
            "declared lease convention."
        ),
        definition_version="total_debt_1",
        unit="USD",
        kind="vendor",
        producer_id="fmp.balance_sheet.total_debt",
        implementation_ref="finrobot.engine.data.providers.fmp_provider::FMPProvider",
        basis="as-reported balance sheet total debt (bonds + finance leases), latest period",
        calibers=("fmp",),
        fallbacks=("yfinance.balance_sheet.total_debt",),
        comparability="caliber_divergent",
        consumers=("valuation", "audit"),
        tolerance_pct=0.20,
    ),
    # gross_margin: removed 2026-06-08 — FMP derives it from its TTM income
    #   statement (gross_profit / revenue) while yfinance uses Yahoo's ``info``
    #   ratio on a latest-period convention. Live probe: MU 48.5% (FMP TTM) vs
    #   67.6% (yfinance) = 19.1pp, KO 29.3% vs 35.1% = 5.7pp — pure caliber gaps.
    #   Banks make it worse: yfinance returns gross_margin 0% for JPM (no COGS in
    #   ``info``), a 60pp phantom alarm. The FMP value ties to SEC TTM at 0.0% on
    #   revenue AND net_income, so the divergence is yfinance's convention.
    MetricRow(
        metric="gross_margin",
        definition="Gross profit over revenue, on the vendor's stated margin caliber.",
        definition_version="gross_margin_1",
        unit="ratio",
        kind="vendor",
        producer_id="fmp.income_statement.gross_margin",
        implementation_ref="finrobot.engine.data.providers.fmp_provider::FMPProvider",
        basis="gross_profit / revenue on FMP's TTM income-statement caliber",
        calibers=("fmp",),
        fallbacks=("yfinance.info.gross_margin",),
        comparability="caliber_divergent",
        consumers=("valuation", "audit"),
        tolerance_pct=0.10,
    ),
    # --- declined: a real number FinRobot chooses not to state, with the reason --
    MetricRow(
        metric="sec_xbrl_preferred_stock_fill",
        definition=(
            "Filling a vendor-silent preferred-stock row from the filer's own XBRL "
            "PreferredStockValue fact."
        ),
        definition_version="sec_fill_1",
        unit="USD",
        kind="vendor",
        status="declined",
        reason_code="owner_decision_unwired",
        citation=(
            "engine/compute/operators/audit/ev_bridge.py docstring: a fact can be years "
            "stale (JPM last filed PreferredStockValue 2009) and _select_latest_fact has "
            "no recency gate, so wiring SEC ahead of a vendor caliber needs an owner "
            "decision plus a recency policy first"
        ),
    ),
)

METRIC_REGISTRY_BY_NAME: dict[str, MetricRow] = {row.metric: row for row in METRIC_REGISTRY}
"""Lookup view. Duplicate keys are refused at import (below) because a silent
last-wins dict would make one of two contradictory declarations invisible."""


def duplicate_metric_names(rows: tuple[MetricRow, ...]) -> list[str]:
    """Declaration keys appearing more than once, sorted. Exposed as a function so
    the guard is testable rather than being an untestable import side effect."""
    seen: set[str] = set()
    duplicates: list[str] = []
    for row in rows:
        if row.metric in seen:
            duplicates.append(row.metric)
        seen.add(row.metric)
    return sorted(duplicates)


_DUPLICATES = duplicate_metric_names(METRIC_REGISTRY)
if _DUPLICATES:  # pragma: no cover - import guard against an editing mistake
    raise RuntimeError(f"duplicate metric declarations in METRIC_REGISTRY: {_DUPLICATES}")


# ---------------------------------------------------------------------------
# Observation-level reconciliation (the data-layer half of the policy)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MetricObservation:
    """One provider's reading of one metric, with everything the policy needs to
    decide whether it may be compared, trusted, and known in time.

    This is the provenance atom: the registry says WHO owns a number, this says
    what one source actually reported and when. ``engine/data`` builds these; the
    registry never reaches back for them (leaf rule).
    """

    metric: str
    source: str
    """Provider runtime name, e.g. ``"fmp"`` / ``"edgar_tools"`` / ``"yfinance"``."""

    value: float | None
    unit: str
    currency: str | None = None
    period_end: date | None = None
    """Fiscal period end, or the bar session date for a price."""
    period_basis: str | None = None
    """``"ttm"`` | ``"annual"`` | ``"quarterly"`` | ``"session"`` — the flow/point
    convention a bare period end does not carry."""
    effective_at: datetime | None = None
    """Semantic time of the value (when it was true as of)."""

    retrieved_at: datetime | None = None
    """When WE fetched it — provenance/audit only. It NEVER gates eligibility: the
    knowledge-time gate reads the SOURCE's ``published_at`` (our own retrieval time
    is after the run's start ceiling by construction, so gating on it would exclude
    every live observation)."""

    published_at: datetime | None = None
    """When the SOURCE knew it (filing date). ``None`` = unknown, so it never gates."""

    derived_from: tuple[str, ...] = ()
    """Source ids this value was COMPUTED from — a rederived figure may not be
    allowed to confirm its own parents (see independence)."""

    quality_flags: tuple[str, ...] = ()
    """``Provenance.degraded`` markers, verbatim; carried, never interpreted here."""


@dataclass(frozen=True)
class MetricCandidate:
    """One observation as seen by a decision: whether it was eligible, how far it
    sat from the selected value, and why. Ineligible candidates are published too —
    a silently dropped source is indistinguishable from one that never arrived."""

    source: str
    value: float | None
    eligible: bool
    deviation_pct: float | None
    deviation_abs: float | None
    reason_code: str
    non_independent: bool = False


@dataclass(frozen=True)
class MetricDecision:
    """The reconciled answer for one metric at one instant: the selected value WITH
    its provenance, the loss reason, and every candidate that was considered.
    Immutable and serialisable; it never re-derives a number."""

    metric: str
    status: str
    value: float | None
    unit: str
    currency: str | None
    selected_source: str | None
    is_authoritative: bool
    """``True`` only when the selected source IS the registry producer of record —
    a fallback is named, not promoted."""
    reason_code: str
    policy_version: str
    definition_version: str
    basis: str
    comparability: str
    tolerance_pct: float
    tolerance_abs: float | None
    period_end: date | None
    period_basis: str | None
    disagreement_pct: float | None
    """Widest over-tolerance deviation, ``None`` when none."""
    agreement_is_independent: bool
    candidates: tuple[MetricCandidate, ...]
    reconciled_at: datetime

    #: The typed twin of this decision's provenance (design §6): ``Present`` when the producer
    #: of record selected the value, ``Proxy`` when the published value is a STAND-IN selected
    #: without an owner, ``Withheld`` when the record refused the number, ``Unavailable`` when
    #: nothing eligible existed. ``None`` for a decision that is not a measurement. Serialised
    #: into ``data_authority.decisions[].measure`` — one vocabulary, switchable by ``kind`` —
    #: so a consumer reads the KIND rather than re-inferring it from ``is_authoritative``.
    measure: Measure | None = None


@dataclass(frozen=True)
class ReconciliationReport:
    """Every metric decision from one reconciliation pass, sorted by metric so two
    identical inputs produce a byte-identical report."""

    policy_version: str
    run_as_of: datetime | None
    clock: datetime
    decisions: tuple[MetricDecision, ...]

    def decision(self, metric: str) -> MetricDecision | None:
        """The decision for ``metric``, or ``None`` when the pass never saw it."""
        for decision in self.decisions:
            if decision.metric == metric:
                return decision
        return None


_CACHE_SUFFIXES = (":provider-cache", ":cache", "-cache")


def canonical_source_id(
    source: str, *, registry_name_by_id: Mapping[str, str] | None = None
) -> str:
    """Collapse cache/eval variants of ONE vendor to one id.

    Strips a trailing ``:provider-cache`` / ``:cache`` / ``-cache`` segment, keeps
    the part before the first ``:``, and (when the mapping is supplied) maps a
    runtime provider name back to its registry id. Leaf rule: the mapping is an
    ARGUMENT, not an import of ``engine.data``.
    """
    cleaned = source.strip()
    for suffix in _CACHE_SUFFIXES:
        if cleaned.endswith(suffix):
            cleaned = cleaned[: -len(suffix)]
    base = cleaned.split(":", 1)[0]
    if registry_name_by_id is not None:
        return registry_name_by_id.get(base, base)
    return base


def compared_fields() -> dict[str, MetricRow]:
    """The validator's cross-provider PROSE-WARNING set: rows with
    ``cross_validated=True``.

    This set is the ONE home of ``engine/data/validator.py``'s
    ``_RELATIVE_FIELDS`` table and MUST stay identical to it
    (``{revenue: 0.15, net_income: 0.15, total_cash: 0.10, market_cap: 0.05}``) —
    a metric that gains a decided row here without being cross-validated would
    newly flip coverage rows to ``partial``. Rows that are comparable in principle
    but not part of this table (``preferred_stock``, ``noncontrolling_interest``,
    ``shares_outstanding``) still get decision records; they simply never emit a
    prose warning.
    """
    return {
        row.metric: row for row in METRIC_REGISTRY if row.status == "ok" and row.cross_validated
    }


def key_fields() -> tuple[str, ...]:
    """Metrics whose over-tolerance divergence is a KEY divergence, sorted."""
    return tuple(
        sorted(row.metric for row in METRIC_REGISTRY if row.status == "ok" and row.key_field)
    )


def _provider_ids_from_ref(ref: str) -> set[str]:
    """The provider names a ``"<module>::<symbol>"`` ref implicitly claims, e.g.
    ``fmp_provider`` → ``{"fmp_provider", "fmp"}``."""
    module = ref.partition(_REF_SEPARATOR)[0]
    last = module.rsplit(".", 1)[-1]
    stem = last[: -len("_provider")] if last.endswith("_provider") else last
    return {last, stem}


def _is_owner(row: MetricRow, source: str) -> bool:
    """Whether ``source`` resolves to the registry producer of record, by identity:
    ``producer_id`` first, then the ref's module-qualified provider, then the LEADER
    of the declared caliber chain. Never by position or value.

    ``calibers`` is the failover chain in order (``categories.PRIORITY[...]``); only
    its FIRST entry is the producer of record. Listing the whole chain — so a reader
    sees the order — must not turn every provider in it into an owner.
    """
    if not row.producer_id or not row.implementation_ref:
        return False
    if source == row.producer_id:
        return True
    source_id = canonical_source_id(source)
    if source_id == canonical_source_id(row.producer_id):
        return True
    if source_id in _provider_ids_from_ref(row.implementation_ref):
        return True
    return bool(row.calibers) and canonical_source_id(row.calibers[0]) == source_id


_PERIOD_END_MATCH_DAYS = 45
"""How far apart two period ends may be and still be the SAME reported period.

Measured on live ``financials:v5`` rows: the same quarter lands within ~5 days
across vendors (FMP ``fiscal_year="2026-07-03"`` vs yfinance ``"2026-06-30"`` — 3
days), while adjacent quarters are >= ~84 days apart. 45 cleanly separates "same
period, different label" from "two providers report different fiscal periods" (the
policy's genuine definition mismatch)."""


def _comparability_key(row: MetricRow, obs: MetricObservation) -> tuple[object, ...]:
    """The tuple used to GROUP observations (and to order groups deterministically).

    Grouping stays literal; the *comparison* against the reference observation is
    tolerant (:func:`_mismatch_reason`) because real payloads label the same period
    differently and often omit ``period_basis`` entirely.
    """
    if row.comparability == "session_price":
        return (obs.currency, obs.period_end)
    if row.comparability == "balance_period":
        return (obs.unit, obs.currency, obs.period_end)
    return (obs.unit, obs.currency, obs.period_end, obs.period_basis)


def _known_and_different(left: object, right: object) -> bool:
    """True only when BOTH values are known (not ``None``) and differ.

    An unknown on either side is NOT a mismatch: a disagreement cannot be
    classified as a definition mismatch unless both bases are visible."""
    return left is not None and right is not None and left != right


def _period_mismatch(left: date | None, right: date | None) -> bool:
    """Whether two period ends are far enough apart to be different periods."""
    if left is None or right is None:
        return False
    return abs((left - right).days) > _PERIOD_END_MATCH_DAYS


def _basis_mismatch(left: str | None, right: str | None) -> bool:
    """``period_basis`` mismatch only when BOTH are known and differ
    (``"ttm"`` vs ``"annual"`` -> mismatch; ``None`` vs ``"ttm"`` -> comparable)."""
    return _known_and_different(left, right)


def _mismatch_reason(
    row: MetricRow, obs: MetricObservation, reference: MetricObservation
) -> str | None:
    """First comparability mismatch in period → currency → unit order, else ``None``.

    Unknown-tolerant: every component is judged only where BOTH sides are known.
    """
    if row.comparability == "session_price":
        if _period_mismatch(obs.period_end, reference.period_end):
            return "definition_mismatch_period"
        if _known_and_different(obs.currency, reference.currency):
            return "definition_mismatch_currency"
        return None
    if row.comparability == "balance_period":
        if _period_mismatch(obs.period_end, reference.period_end):
            return "definition_mismatch_period"
        if _known_and_different(obs.currency, reference.currency):
            return "definition_mismatch_currency"
        if _known_and_different(obs.unit, reference.unit):
            return "definition_mismatch_unit"
        return None
    if _period_mismatch(obs.period_end, reference.period_end) or _basis_mismatch(
        obs.period_basis, reference.period_basis
    ):
        return "definition_mismatch_period"
    if _known_and_different(obs.currency, reference.currency):
        return "definition_mismatch_currency"
    if _known_and_different(obs.unit, reference.unit):
        return "definition_mismatch_unit"
    return None


def _intrinsic_reason(
    row: MetricRow,
    obs: MetricObservation,
    *,
    clock: datetime,
    run_as_of: datetime | None,
) -> str | None:
    """Rule 2 checks that do NOT depend on the reference group: non-finite,
    non-positive, knowledge-time (as-of) and freshness."""
    if obs.value is None or not math.isfinite(obs.value):
        return "non_finite_value"
    if row.positive and obs.value <= 0:
        return "non_positive_value"
    # Knowledge-time (as-of) gate — the SOURCE's clock, never OURS.
    #
    # ``engine/pipelines/runner.py`` publishes the ceiling at the START of every run
    # (``set_run_as_of(datetime.now(UTC))``), so ``current_run_as_of()`` is the run's
    # own start instant and EVERY provider fetch afterwards has
    # ``retrieved_at > ceiling`` by construction. Gating on ``retrieved_at`` therefore
    # excluded all eight decisions of the live EHC run
    # (``art_2026-10-13T22:36:11_EHC_equity_research_dfa427``, all
    # ``unavailable``/``after_run_as_of``), caveating a healthy single-source fetch.
    # ``retrieved_at`` records when WE looked — not evidence the source did not yet
    # know the number — so it never makes an observation ineligible. Only a known
    # ``published_at`` after the ceiling is real lookahead.
    #
    # Honest limit: a vendor statement read carries ``published_at=None``, so for
    # those the gate CANNOT fire. A vendor revision dated after a simulated decision
    # point is not detectable from what we store; using our own retrieval time to
    # pretend otherwise excluded the entire live data set.
    if run_as_of is not None and obs.published_at is not None and obs.published_at > run_as_of:
        return "after_run_as_of"
    if row.freshness_max_age_s is not None and obs.effective_at is not None:
        if (clock - obs.effective_at).total_seconds() > row.freshness_max_age_s:
            return "stale_beyond_freshness_policy"
    return None


def _over_tolerance(
    row: MetricRow, deviation_pct: float | None, deviation_abs: float | None
) -> bool:
    """Conflict iff the RELATIVE band is exceeded AND (no absolute floor is declared
    OR the absolute floor is also exceeded) — the owner's "greater of one tick or
    0.05%" rule, i.e. ``tolerance_abs`` is a minimum-provability FLOOR, not an
    alternative test. When ``tolerance_abs is None`` the relative band alone decides.
    """
    if deviation_pct is None or deviation_pct <= row.tolerance_pct:
        return False
    if row.tolerance_abs is None:
        return True
    return deviation_abs is not None and deviation_abs > row.tolerance_abs


def _non_independent(obs: MetricObservation, selected_source: str) -> bool:
    """Whether ``obs`` cannot INDEPENDENTLY speak about the selected value.

    Two cases: it is co-lineage with the selected source (same canonical id — a
    cache/eval variant of the same vendor), or it is itself a DERIVED value
    (``derived_from`` non-empty). A re-expression of other fields
    (``shares_outstanding`` = ``market_cap / current_price``) carries no information
    about the metric that its own inputs do not already carry, so it can neither
    confirm nor contradict the selection — the False-Validation trap the validator
    documents as ``_SHARES_DERIVED_EPS``.
    """
    if obs.derived_from:
        return True
    return canonical_source_id(obs.source) == canonical_source_id(selected_source)


@dataclass(frozen=True)
class _Assessment:
    observation: MetricObservation
    reason_code: str | None
    is_owner: bool


def _key_order(key: tuple[object, ...]) -> tuple[str, ...]:
    """A total, `None`-safe ordering over comparability keys (for determinism)."""
    return tuple("" if part is None else str(part) for part in key)


def _measure(
    *,
    metric: str,
    status: str,
    value: float | None,
    selected_source: str | None,
    is_authoritative: bool,
    reason_code: str,
    basis: str,
    comparability: str,
    period_basis: str | None,
    row: MetricRow | None,
) -> Measure:
    """The typed twin of a decision's provenance (design §6) — see ``MetricDecision.measure``.

    Derived from the record's own statements and nothing else: an accepted value from the
    producer of record is ``Present``; the same acceptance WITHOUT an owner is ``Proxy`` — the
    report publishes a stand-in for a metric no wired source owns, and the disclosure is what
    the record itself says about it; a DECLINED row is ``Withheld``; anything else with no value
    is ``Unavailable``.

    Withheld and Unavailable are different facts and the registry is where the record already
    draws the line: a declined row is a real number FinRobot chooses not to state
    (``sec_xbrl_preferred_stock_fill``: a fact can be years stale, so wiring it needs an owner
    decision first), while unavailable means nothing eligible was ever obtained. The decision's
    own ``status`` stays what it was — this is the provenance, not a re-decision.

    Reason codes are carried VERBATIM from the record, never re-spelled here. §9.6 fixes
    UPPER_SNAKE_CASE for a code, but today's live vocabulary is lower_snake
    (``owner_decision_unwired``, ``owner_absent_alternative_selected``) — so upper-casing at this
    one site would mint the second spelling of every code, which is the lossiness §9.6 exists to
    end. The migration is §9.6's to make, in one pass over the whole vocabulary.
    """
    if status == "accepted" and value is not None:
        if is_authoritative and selected_source:
            return Present(value=float(value), source=selected_source, period=period_basis)
        disclosure = (
            f"published from {selected_source or 'an unnamed source'} although no wired source "
            f"owns {metric}"
            + (f"; comparability {comparability}" if comparability else "")
            + (f" ({basis})" if basis else "")
        )
        return Proxy(value=float(value), proxy_of=metric, disclosure=disclosure)
    if row is not None and row.status == "declined":
        return Withheld(
            reason_code=row.reason_code or "declined_by_policy",
            evidence=row.definition or basis or "declined by policy",
        )
    return Unavailable(reason_code=reason_code)


def _unavailable_decision(metric: str, row: MetricRow | None, *, clock: datetime) -> MetricDecision:
    """The fail-closed answer when there is no row (or it is declined): never a
    fabricated value, never ``0``."""
    reason_code = "no_eligible_observation"
    return MetricDecision(
        measure=_measure(
            metric=metric,
            status="unavailable",
            value=None,
            selected_source=None,
            is_authoritative=False,
            reason_code=reason_code,
            basis=(row.basis or "") if row is not None else "",
            comparability=row.comparability if row is not None else "",
            period_basis=None,
            row=row,
        ),
        metric=metric,
        status="unavailable",
        value=None,
        unit=row.unit if row is not None else "",
        currency=None,
        selected_source=None,
        is_authoritative=False,
        reason_code=reason_code,
        policy_version=POLICY_VERSION,
        definition_version=row.definition_version if row is not None else "",
        basis=(row.basis or "") if row is not None else "",
        comparability=row.comparability if row is not None else "",
        tolerance_pct=row.tolerance_pct if row is not None else METRIC_TOLERANCE_PCT,
        tolerance_abs=row.tolerance_abs if row is not None else None,
        period_end=None,
        period_basis=None,
        disagreement_pct=None,
        agreement_is_independent=True,
        candidates=(),
        reconciled_at=clock,
    )


def resolve_metric_observations(
    metric: str,
    observations: Sequence[MetricObservation],
    *,
    clock: datetime,
    run_as_of: datetime | None = None,
) -> MetricDecision:
    """Reconcile one metric from raw observations, applying the policy's rules 1–6.

    Rules, in order: unknown/declined → ``unavailable``; group by comparability key
    and pick the reference group (owner's group, else the widest eligible group);
    per-observation hard validity (non-finite / non-positive / after-as-of / stale);
    authority (owner if eligible, else a NAMED fallback, else ``unavailable``);
    disagreement published as ``conflict`` (never averaged, never majority-voted);
    independence (co-lineage or derived agreement cannot confirm itself).

    Deterministic: candidates are sorted by source and the reference group is found
    by identity, so the same observations in any input order give an equal decision.
    All datetimes are assumed to share tz-awareness (the data layer supplies tz-aware
    UTC instants).
    """
    row = METRIC_REGISTRY_BY_NAME.get(metric)
    if row is None or row.status == "declined":
        return _unavailable_decision(metric, row, clock=clock)

    if not observations:
        return _unavailable_decision(metric, row, clock=clock)

    groups: dict[tuple[object, ...], list[MetricObservation]] = {}
    for obs in observations:
        groups.setdefault(_comparability_key(row, obs), []).append(obs)

    def _smallest(group: list[MetricObservation]) -> str:
        return min(o.source for o in group)

    owner_keys = [
        key for key, members in groups.items() if any(_is_owner(row, o.source) for o in members)
    ]
    if owner_keys:
        # Owner observation present: ITS group is the reference, even when the owner
        # is intrinsically ineligible (a stale owner still defines the metric's key).
        reference_key = min(owner_keys, key=lambda key: (_smallest(groups[key]), _key_order(key)))
    else:
        intrinsic_eligible = {
            key: sum(
                1
                for o in members
                if _intrinsic_reason(row, o, clock=clock, run_as_of=run_as_of) is None
            )
            for key, members in groups.items()
        }
        reference_key = min(
            groups,
            key=lambda key: (-intrinsic_eligible[key], _smallest(groups[key]), _key_order(key)),
        )

    # The reference OBSERVATION (smallest source in the reference group) is what every
    # other observation is compared against — tolerantly, since the same period is
    # labelled differently across vendors.
    reference_obs = min(groups[reference_key], key=lambda o: o.source)

    # Did the producer of record show up at all? A caliber-divergent row can only
    # refuse an alternative when there is a selection to compare it AGAINST; a lone
    # non-owner observation on an owner-absent row is a legitimate answer, not an
    # absent value.
    owner_observed = any(_is_owner(row, obs.source) for obs in observations)

    assessments: list[_Assessment] = []
    for obs in observations:
        intrinsic = _intrinsic_reason(row, obs, clock=clock, run_as_of=run_as_of)
        reason = intrinsic
        if reason is None:
            reason = _mismatch_reason(row, obs, reference_obs)
        if (
            reason is None
            and owner_observed
            and row.comparability == "caliber_divergent"
            and not _is_owner(row, obs.source)
        ):
            # The owner's number is on the table, so a differently-calibrated
            # alternative may not be compared against it. With no owner observation
            # there is nothing to compare against, so a lone reading stands (the
            # live EHC case: FMP never answered, yfinance did).
            reason = "definition_mismatch_caliber"
        assessments.append(
            _Assessment(observation=obs, reason_code=reason, is_owner=_is_owner(row, obs.source))
        )
    assessments.sort(key=lambda a: a.observation.source)

    eligible = [a for a in assessments if a.reason_code is None]
    owner_eligible = [a for a in eligible if a.is_owner]
    owner_selected = bool(owner_eligible)

    selected: _Assessment | None
    selection_reason: str
    if owner_eligible:
        selected, selection_reason = owner_eligible[0], "authoritative_selected"
        status = "accepted"
    elif eligible and owner_observed:
        # The owner ANSWERED but its value was ineligible (stale/invalid): the
        # preferred value lost, so this is a named, degraded fallback.
        selected, selection_reason = eligible[0], "canonical_value_invalid_fallback_selected"
        status = "fallback"
    elif eligible:
        # The owner contributed NO observation: the chain head (FMP) rate-limited out
        # and a real alternative answered. Not a degraded fallback — but the head
        # never spoke, so it is still not authoritative.
        selected, selection_reason = eligible[0], "owner_absent_alternative_selected"
        status = "accepted"
    else:
        selected, selection_reason = None, "no_eligible_observation"
        status = "unavailable"

    selected_value = selected.observation.value if selected is not None else None
    selected_source = selected.observation.source if selected is not None else None

    over: list[float] = []
    tolerance_exceeded: set[str] = set()
    candidates: list[MetricCandidate] = []
    for assessment in assessments:
        obs = assessment.observation
        deviation_pct: float | None = None
        deviation_abs: float | None = None
        if selected_value is not None and obs.value is not None and math.isfinite(obs.value):
            deviation_abs = abs(obs.value - selected_value)
            deviation_pct = deviation_abs / max(abs(obs.value), abs(selected_value), 1e-9)

        # Non-independence is a property of a CANDIDATE's lineage, never of the
        # selected source itself.
        non_independent = (
            assessment is not selected
            and selected_source is not None
            and _non_independent(obs, selected_source)
        )
        exceeded = _over_tolerance(row, deviation_pct, deviation_abs)
        if exceeded:
            tolerance_exceeded.add(obs.source)

        if assessment is selected:
            reason = selection_reason
        elif assessment.reason_code is not None:
            reason = assessment.reason_code
        elif non_independent:
            # A co-lineage/derived reading can never raise a conflict on its own: it
            # is recorded as considered, set aside (eligible=False), and named — but
            # it neither flips the status nor feeds disagreement_pct.
            reason = "non_independent_agreement"
        elif exceeded:
            reason = "above_tolerance_published_flagged"
            if deviation_pct is not None:
                over.append(deviation_pct)
        else:
            reason = "sources_agree"

        candidates.append(
            MetricCandidate(
                source=obs.source,
                value=obs.value,
                eligible=assessment.reason_code is None and not non_independent,
                deviation_pct=deviation_pct,
                deviation_abs=deviation_abs,
                reason_code=reason,
                non_independent=non_independent,
            )
        )

    disagreement_pct: float | None = None
    reason_code = selection_reason
    if over:
        disagreement_pct = max(over)
        if status == "accepted":
            # Only an accepted decision escalates to conflict; a fallback already
            # says "the preferred value was unusable", so it stays a fallback.
            status = "conflict"
            reason_code = "above_tolerance_published_flagged"
    elif status == "accepted" and owner_selected:
        # Rule 5's within-tolerance reason refines an AUTHORITATIVE selection. An
        # absent-owner acceptance keeps its provenance reason (owner_absent_*) — the
        # fact that FMP never spoke is the point, and must not be hidden behind
        # ``sources_agree``.
        reason_code = "sources_agree" if len(eligible) > 1 else "within_tolerance"

    if status == "unavailable":
        reason_code = assessments[0].reason_code or "no_eligible_observation"

    agreeing = [
        a for a in eligible if a is not selected and a.observation.source not in tolerance_exceeded
    ]
    if selected_source is None or not agreeing:
        agreement_is_independent = True
    else:
        agreement_is_independent = any(
            not _non_independent(a.observation, selected_source) for a in agreeing
        )

    return MetricDecision(
        metric=metric,
        status=status,
        value=selected_value,
        measure=_measure(
            metric=metric,
            status=status,
            value=selected_value,
            selected_source=selected_source,
            is_authoritative=selected is not None and selected.is_owner,
            reason_code=reason_code,
            basis=row.basis or "",
            comparability=row.comparability,
            period_basis=reference_obs.period_basis,
            row=row,
        ),
        unit=row.unit,
        currency=reference_obs.currency,
        selected_source=selected_source,
        is_authoritative=selected is not None and selected.is_owner,
        reason_code=reason_code,
        policy_version=POLICY_VERSION,
        definition_version=row.definition_version,
        basis=row.basis or "",
        comparability=row.comparability,
        tolerance_pct=row.tolerance_pct,
        tolerance_abs=row.tolerance_abs,
        period_end=reference_obs.period_end,
        period_basis=reference_obs.period_basis,
        disagreement_pct=disagreement_pct,
        agreement_is_independent=agreement_is_independent,
        candidates=tuple(candidates),
        reconciled_at=clock,
    )
