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
from typing import Literal, Mapping

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
