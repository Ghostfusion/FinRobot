"""Metric-authority registry tests.

Two things are being defended here.

1. **Every declared owner actually exists.** ``implementation_ref`` is a string that
   only resolves if the code still exists, so the registry cannot rot into a list of
   plausible-looking names after a refactor. This is the test that makes
   ``MetricRow`` a contract rather than documentation.
2. **The resolver never invents a value.** The whole point of the module is that an
   un-owned number does not get published: a fallback is not an authority, ``None``
   is not ``0``, and a disagreement is reported rather than averaged.

The constructor cases use ``dataclasses.replace`` over one valid row, so each case
proves exactly one rule — and if a rule is later removed the corresponding case
fails instead of silently widening what the registry accepts.
"""

from __future__ import annotations

import dataclasses
import importlib
import math
import re

from finrobot.engine.models.measurement import Present, Proxy, Unavailable, Withheld
from datetime import date, datetime, timedelta, timezone

import pytest

from finrobot.engine.models.metric_authority import (
    COMPARABILITY_CLASSES,
    CONSUMER_IDS,
    DECISION_REASON_CODES,
    DECISION_STATUSES,
    DECLINED_REASON_CODES,
    METRIC_REGISTRY,
    METRIC_REGISTRY_BY_NAME,
    METRIC_TOLERANCE_PCT,
    POLICY_VERSION,
    MetricDecision,
    MetricObservation,
    MetricRow,
    ReconciliationReport,
    canonical_source_id,
    compared_fields,
    duplicate_metric_names,
    key_fields,
    resolve_metric,
    resolve_metric_observations,
)

_UTC = timezone.utc

_VALID: dict[str, object] = {
    "metric": "unit_test_metric",
    "definition": "A metric that exists only for these tests.",
    "definition_version": "v1",
    "unit": "USD",
    "kind": "computed",
    "producer_id": "tests.owns_this",
    "implementation_ref": "finrobot.engine.models.metric_authority::duplicate_metric_names",
    "basis": "the sum of two ones",
}

_REF_SEPARATOR = "::"


def _row(**overrides: object) -> MetricRow:
    return MetricRow(**{**_VALID, **overrides})  # type: ignore[arg-type]


def _declined(**overrides: object) -> MetricRow:
    """A valid declined row; each test case overrides exactly one field."""
    base: dict[str, object] = {
        "status": "declined",
        "producer_id": None,
        "implementation_ref": None,
        "basis": None,
        "reason_code": "no_reachable_producer",
        "citation": "checked every caliber on 2026-10-12; none states it",
    }
    base.update(overrides)
    return _row(**base)


# ---------------------------------------------------------------------------
# The shipped registry
# ---------------------------------------------------------------------------


def test_every_implementation_ref_resolves_against_the_live_tree() -> None:
    """The registry's refs are resolved, not trusted.

    A renamed operator symbol must break this test rather than leave a metric
    silently un-owned — that is the difference between a registry and a comment.
    """
    unresolved: list[str] = []
    for row in METRIC_REGISTRY:
        if row.implementation_ref is None:  # declined rows carry none by construction
            continue
        module_path, _, symbol = row.implementation_ref.partition(_REF_SEPARATOR)
        try:
            module = importlib.import_module(module_path)
        except ImportError as exc:  # pragma: no cover - only on a broken ref
            unresolved.append(f"{row.metric}: cannot import {module_path} ({exc})")
            continue
        if not hasattr(module, symbol):
            unresolved.append(f"{row.metric}: {module_path} has no {symbol!r}")
    assert unresolved == []


def test_shipped_registry_has_no_duplicate_keys() -> None:
    assert duplicate_metric_names(METRIC_REGISTRY) == []
    assert len(METRIC_REGISTRY_BY_NAME) == len(METRIC_REGISTRY)


def test_every_ok_row_names_owner_ref_and_basis() -> None:
    for row in METRIC_REGISTRY:
        if row.status == "declined":
            continue
        assert row.producer_id, row.metric
        assert row.implementation_ref, row.metric
        assert row.basis, row.metric
        assert math.isfinite(row.tolerance_pct) and row.tolerance_pct > 0, row.metric


def test_every_declined_row_cites_its_refusal() -> None:
    """A refusal is a claim a reader can check, so it must carry both a closed
    reason code and a citation — an empty refusal is indistinguishable from an
    oversight."""
    declined = [row for row in METRIC_REGISTRY if row.status == "declined"]
    assert declined, "the registry must keep at least one recorded refusal"
    for row in declined:
        assert row.reason_code in DECLINED_REASON_CODES, row.metric
        assert (row.citation or "").strip(), row.metric
        assert row.producer_id is None
        assert row.implementation_ref is None


def test_registry_declares_both_producer_kinds() -> None:
    """FinRobot gets numbers from operators AND from vendor statement reads; a
    registry that only knew one kind would misdescribe half the report."""
    kinds = {row.kind for row in METRIC_REGISTRY if row.status == "ok"}
    assert kinds == {"computed", "vendor"}


# ---------------------------------------------------------------------------
# Constructor refusals — one case per rule
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("overrides", "reason"),
    [
        ({"metric": "has space"}, "bare key"),
        ({"metric": ""}, "bare key"),
        ({"definition": "   "}, "definition"),
        ({"definition_version": ""}, "definition_version"),
        ({"unit": ""}, "unit"),
        ({"tolerance_pct": 0.0}, "tolerance"),
        ({"tolerance_pct": float("nan")}, "tolerance"),
        ({"producer_id": None}, "producer_id"),
        ({"producer_id": "a::b"}, "code path"),
        ({"producer_id": "modules/thing.py"}, "code path"),
        ({"implementation_ref": None}, "implementation_ref"),
        ({"implementation_ref": "finrobot.engine.models.metric_authority"}, "<module>::<symbol>"),
        (
            {"implementation_ref": "finrobot.engine.models.metric_authority::a::b"},
            "<module>::<symbol>",
        ),
        ({"implementation_ref": "other.thing::symbol"}, "finrobot"),
        ({"basis": None}, "basis"),
        ({"kind": "vendor", "calibers": ()}, "caliber"),
    ],
)
def test_unsound_rows_are_refused(overrides: dict[str, object], reason: str) -> None:
    with pytest.raises(ValueError, match=reason):
        _row(**overrides)


@pytest.mark.parametrize(
    "overrides",
    [
        {"reason_code": "made_up_code"},
        {"reason_code": None},
        {"citation": "   "},
        {"citation": None},
        {"producer_id": "someone.else"},
        {"implementation_ref": "finrobot.engine.models.metric_authority::resolve_metric"},
        {"basis": "some basis"},
        {"calibers": ("fmp",)},
        {"fallbacks": ("yfinance.x",)},
    ],
)
def test_declined_rows_refuse_an_owner_or_a_missing_reason(
    overrides: dict[str, object],
) -> None:
    """A refusal that also claims an owner (or lists a fallback) is two answers to
    one question, and the weaker one always wins in a reader's head."""
    with pytest.raises(ValueError):
        _declined(**overrides)


def test_duplicate_metric_names_reports_each_repeat() -> None:
    rows = (
        _row(metric="dup"),
        _row(metric="unique"),
        _row(metric="dup"),
    )
    assert duplicate_metric_names(rows) == ["dup"]


# ---------------------------------------------------------------------------
# resolve_metric — the canonical is found by identity, never by position
# ---------------------------------------------------------------------------


def test_canonical_is_found_by_producer_identity_not_dict_order() -> None:
    row = METRIC_REGISTRY_BY_NAME["preferred_stock"]
    assert row.producer_id is not None
    forward = resolve_metric(
        "preferred_stock",
        {
            row.producer_id: 15_348_000_000.0,
            "yfinance.balance_sheet.preferred_stock": 15_348_000_000.0,
        },
    )
    backward = resolve_metric(
        "preferred_stock",
        {
            "yfinance.balance_sheet.preferred_stock": 15_348_000_000.0,
            row.producer_id: 15_348_000_000.0,
        },
    )
    assert forward.value == backward.value == 15_348_000_000.0
    assert forward.producer_id == backward.producer_id == row.producer_id
    assert forward.status == backward.status == "ok"


def test_a_fallback_is_never_promoted_to_canonical() -> None:
    """The motive for the whole module: yfinance can supply the row, but it is not
    the producer of record, so its number alone does not make the metric publishable.
    """
    resolution = resolve_metric(
        "preferred_stock",
        {"yfinance.balance_sheet.preferred_stock": 15_348_000_000.0},
    )
    assert resolution.value is None
    assert resolution.status == "unavailable"
    assert resolution.reason_code == "no_reachable_producer"
    assert "fallback is not an authority" in (resolution.citation or "")
    assert resolution.is_publishable is False


def test_absent_owner_value_is_none_never_zero() -> None:
    row = METRIC_REGISTRY_BY_NAME["noncontrolling_interest"]
    assert row.producer_id is not None
    resolution = resolve_metric("noncontrolling_interest", {row.producer_id: None})
    assert resolution.value is None
    assert resolution.status == "unavailable"
    assert resolution.conflicts == ()


def test_disagreement_is_published_with_its_deviation_and_the_canonical_stands() -> None:
    row = METRIC_REGISTRY_BY_NAME["enterprise_value"]
    assert row.producer_id is not None
    resolution = resolve_metric(
        "enterprise_value",
        {
            row.producer_id: 414_900_000_000.0,
            "unknown.caliber": 420_000_000_000.0,
        },
    )
    # 5.1B / 420B ≈ 1.2% > the 1% band: reportable, not reconcilable.
    assert resolution.status == "conflict"
    assert resolution.value == 414_900_000_000.0
    assert resolution.is_publishable is True
    assert [c.source for c in resolution.conflicts] == ["unknown.caliber"]
    assert resolution.spread_pct == pytest.approx(0.01214, rel=1e-3)
    assert resolution.basis == row.basis


def test_agreement_inside_tolerance_is_not_a_conflict() -> None:
    row = METRIC_REGISTRY_BY_NAME["enterprise_value"]
    assert row.producer_id is not None
    resolution = resolve_metric(
        "enterprise_value",
        {row.producer_id: 100.0, "close.caliber": 100.5},
    )
    assert resolution.status == "ok"
    assert resolution.conflicts == ()
    assert resolution.spread_pct is None


def test_tolerance_boundary_is_exclusive() -> None:
    row = METRIC_REGISTRY_BY_NAME["wacc"]
    assert row.producer_id is not None
    # deviation = |other - 0.09| / max(other, 0.09); at 1% the value is exact, so the
    # boundary case must be built from the same formula the resolver uses.
    at_band = 0.09 * (1 + METRIC_TOLERANCE_PCT)
    just_over = 0.09 * (1 + METRIC_TOLERANCE_PCT * 1.5)
    assert resolve_metric("wacc", {row.producer_id: 0.09, "x": at_band}).status == "ok"
    assert resolve_metric("wacc", {row.producer_id: 0.09, "x": just_over}).status == "conflict"


def test_non_finite_sources_are_treated_as_absent() -> None:
    """NaN comparisons are all False, so an unguarded NaN would pass every
    tolerance test and print as if it agreed."""
    row = METRIC_REGISTRY_BY_NAME["ev_ebitda"]
    assert row.producer_id is not None
    assert resolve_metric("ev_ebitda", {row.producer_id: float("inf")}).value is None
    assert resolve_metric("ev_ebitda", {row.producer_id: float("nan")}).value is None
    resolution = resolve_metric("ev_ebitda", {row.producer_id: 12.0, "x": float("nan")})
    assert resolution.status == "ok"
    assert resolution.conflicts == ()


def test_unregistered_metric_is_unknown_until_authority_is_required() -> None:
    permissive = resolve_metric("not_a_metric", {"anyone": 1.0})
    assert permissive.status == "unknown"
    assert permissive.value is None

    strict = resolve_metric("not_a_metric", {"anyone": 1.0}, require_authority=True)
    assert strict.status == "unavailable"
    assert strict.value is None


def test_declined_metric_keeps_its_reason_and_downgrades_when_authority_is_required() -> None:
    declined = resolve_metric("sec_xbrl_preferred_stock_fill", {}, require_authority=False)
    assert declined.status == "declined"
    assert declined.value is None
    assert declined.reason_code == "owner_decision_unwired"
    assert "recency" in (declined.citation or "")

    strict = resolve_metric("sec_xbrl_preferred_stock_fill", {}, require_authority=True)
    assert strict.status == "unavailable"
    assert strict.reason_code == declined.reason_code
    assert strict.citation == declined.citation


def test_resolution_echoes_the_declaration_so_a_consumer_need_not_relook_it_up() -> None:
    resolution = resolve_metric("ttm_fcf", {"multiples.compute_ttm_fcf": 1.0})
    assert resolution.definition_version == METRIC_REGISTRY_BY_NAME["ttm_fcf"].definition_version
    assert resolution.unit == "USD"
    assert resolution.implementation_ref is not None


def test_row_is_immutable() -> None:
    row = METRIC_REGISTRY_BY_NAME["wacc"]
    with pytest.raises(dataclasses.FrozenInstanceError):
        row.metric = "renamed"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# The new fields on MetricRow — closed vocabularies and refusals
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("overrides", "reason"),
    [
        ({"comparability": "nonsense"}, "comparability"),
        ({"consumers": ("marketing",)}, "consumer"),
        ({"consumers": ("valuation", "made_up")}, "consumer"),
        ({"tolerance_abs": 0.0}, "tolerance_abs"),
        ({"tolerance_abs": float("nan")}, "tolerance_abs"),
        ({"tolerance_abs": -0.5}, "tolerance_abs"),
        ({"freshness_max_age_s": 0.0}, "freshness_max_age_s"),
        ({"freshness_max_age_s": float("inf")}, "freshness_max_age_s"),
    ],
)
def test_new_field_refusals(overrides: dict[str, object], reason: str) -> None:
    with pytest.raises(ValueError, match=reason):
        _row(**overrides)


@pytest.mark.parametrize(
    "overrides",
    [
        {"consumers": ("audit",)},
        {"key_field": True},
        {"tolerance_abs": 0.01},
        {"cross_validated": True},
    ],
)
def test_declined_rows_refuse_the_dependency_graph(overrides: dict[str, object]) -> None:
    """An unowned number has no consumer graph, no key divergence and no band."""
    with pytest.raises(ValueError, match="declined row must not carry"):
        _declined(**overrides)


def test_vocabularies_are_closed_tuples() -> None:
    assert set(COMPARABILITY_CLASSES) == {
        "exact",
        "as_reported_period",
        "balance_period",
        "session_price",
        "caliber_divergent",
    }
    assert set(DECISION_STATUSES) == {
        "accepted",
        "fallback",
        "conflict",
        "unavailable",
        "definition_mismatch",
    }
    assert "non_independent_agreement" in DECISION_REASON_CODES
    assert set(CONSUMER_IDS) == {"valuation", "technical", "narrative", "screening", "audit"}
    assert POLICY_VERSION == "metric_authority_v1"


# ---------------------------------------------------------------------------
# The new registry rows — declared, resolvable, and consistent
# ---------------------------------------------------------------------------


_NEW_ROWS = (
    "revenue",
    "net_income",
    "total_cash",
    "market_cap",
    "current_price",
    "shares_outstanding",
    "ebitda",
    "total_debt",
    "gross_margin",
)


def test_new_rows_declare_the_contract_fields() -> None:
    expected = {
        # metric: (unit, comparability, tolerance_pct, tolerance_abs, positive, key_field)
        "revenue": ("USD", "as_reported_period", 0.15, None, False, True),
        "net_income": ("USD", "as_reported_period", 0.15, None, False, True),
        "total_cash": ("USD", "balance_period", 0.10, None, False, False),
        "market_cap": ("USD", "exact", 0.05, None, True, False),
        "current_price": ("USD", "session_price", 0.05, 0.01, True, False),
        "shares_outstanding": ("shares", "balance_period", 0.05, None, True, False),
        "ebitda": ("USD", "caliber_divergent", 0.15, None, False, False),
        "total_debt": ("USD", "caliber_divergent", 0.20, None, False, False),
        "gross_margin": ("ratio", "caliber_divergent", 0.10, None, False, False),
    }
    for metric, (unit, comparability, tol, tol_abs, positive, key) in expected.items():
        row = METRIC_REGISTRY_BY_NAME[metric]
        assert row.unit == unit, metric
        assert row.comparability == comparability, metric
        assert row.tolerance_pct == tol, metric
        assert row.tolerance_abs == tol_abs, metric
        assert row.positive is positive, metric
        assert row.key_field is key, metric
        assert row.status == "ok" and row.producer_id and row.implementation_ref, metric
        assert row.definition_version == f"{metric}_1", metric
        assert row.basis, metric

    assert METRIC_REGISTRY_BY_NAME["current_price"].freshness_max_age_s == 5 * 24 * 3600


def test_every_consumer_id_is_declared() -> None:
    for row in METRIC_REGISTRY:
        for consumer in row.consumers:
            assert consumer in CONSUMER_IDS, f"{row.metric}: {consumer}"


def test_every_decision_constant_is_used_by_a_row_or_vocabulary() -> None:
    """The rows' comparability classes come from the vocabulary, never free text."""
    for row in METRIC_REGISTRY:
        assert row.comparability in COMPARABILITY_CLASSES, row.metric


def test_compared_fields_is_the_cross_provider_view() -> None:
    """This set IS the validator's ``_RELATIVE_FIELDS`` table — byte-for-byte the
    pre-reconciliation values, so warning coverage cannot drift."""
    compared = compared_fields()
    assert set(compared) == {"revenue", "net_income", "total_cash", "market_cap"}
    assert {metric: row.tolerance_pct for metric, row in compared.items()} == {
        "revenue": 0.15,
        "net_income": 0.15,
        "total_cash": 0.10,
        "market_cap": 0.05,
    }
    # Comparability-in-principle rows that are NOT in the warning table still get
    # decision records, but never a prose warning.
    for excluded in (
        "preferred_stock",
        "noncontrolling_interest",
        "shares_outstanding",
        "ebitda",
        "total_debt",
        "gross_margin",
        "current_price",
        "enterprise_value",
    ):
        assert excluded not in compared


def test_key_fields_are_the_key_divergence_metrics_sorted() -> None:
    assert key_fields() == ("net_income", "revenue")


def test_current_price_owner_tracks_the_core_stock_apis_priority_leader() -> None:
    """The registry may not contradict the priority table it is authoritative about.

    ``engine.data`` is imported INSIDE the test body — the leaf itself must not import
    it (ADR-0005 leaf rule) — so the registry can never silently drift from
    ``categories.PRIORITY``: with FMP as owner, every live price decision read "the
    producer of record never spoke" (EHC log: eodhd 124.33 →
    ``owner_absent_alternative_selected``).
    """
    from finrobot.engine.data.categories import PRIORITY, Category

    chain = PRIORITY[Category.CORE_STOCK_APIS]
    row = METRIC_REGISTRY_BY_NAME["current_price"]
    assert row.producer_id is not None
    assert row.producer_id.startswith(f"{chain[0]}.")
    assert row.calibers == chain[: len(row.calibers)]
    assert row.calibers == ("eodhd", "moomoo", "fmp", "yfinance")


def test_only_the_chain_leader_is_the_price_owner() -> None:
    """Listing the whole chain must not make every provider an owner."""
    decision = resolve_metric_observations(
        "current_price",
        [_obs(metric="current_price", source="eodhd", value=124.33, period_basis="session")],
        clock=_clock(),
    )
    assert decision.status == "accepted"
    assert decision.is_authoritative is True
    assert decision.reason_code == "within_tolerance"


def test_a_non_leader_price_source_is_not_the_owner() -> None:
    decision = resolve_metric_observations(
        "current_price",
        [_obs(metric="current_price", source="fmp", value=124.33, period_basis="session")],
        clock=_clock(),
    )
    assert decision.status == "accepted"
    assert decision.is_authoritative is False
    assert decision.reason_code == "owner_absent_alternative_selected"


# ---------------------------------------------------------------------------
# canonical_source_id — collapse cache variants and map runtime names
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("fmp", "fmp"),
        ("fmp:provider-cache", "fmp"),
        ("fmp:cache", "fmp"),
        ("fmp-cache", "fmp"),
        ("fmp:some-other-variant", "fmp"),
        ("  yfinance  ", "yfinance"),
    ],
)
def test_canonical_source_id_collapses_variants(raw: str, expected: str) -> None:
    assert canonical_source_id(raw) == expected


def test_canonical_source_id_maps_through_the_supplied_registry_view() -> None:
    mapped = {"yahoo": "yfinance", "fmp": "fmp"}
    assert canonical_source_id("yahoo:cache", registry_name_by_id=mapped) == "yfinance"
    assert canonical_source_id("fmp", registry_name_by_id=mapped) == "fmp"


# ---------------------------------------------------------------------------
# resolve_metric_observations — the rules, in order
# ---------------------------------------------------------------------------


def _obs(**overrides: object) -> MetricObservation:
    """A valid revenue observation (owner source ``fmp``); each test overrides one axis."""
    base: dict[str, object] = {
        "metric": "revenue",
        "source": "fmp",
        "value": 100.0,
        "unit": "USD",
        "currency": "USD",
        "period_end": date(2025, 12, 31),
        "period_basis": "ttm",
    }
    base.update(overrides)
    return MetricObservation(**base)  # type: ignore[arg-type]


def _clock() -> datetime:
    return datetime(2026, 1, 20, tzinfo=_UTC)


def test_the_owner_selection_is_a_present_measurement() -> None:
    """``fmp`` owns revenue, so the value is a Present — measured, with its source named. The
    typed twin of the decision's provenance, for a consumer that switches on ``kind``."""
    decision = resolve_metric_observations("revenue", [_obs()], clock=_clock())
    assert decision.is_authoritative is True
    assert isinstance(decision.measure, Present)
    assert decision.measure.value == 100.0
    assert decision.measure.source == "fmp"
    assert decision.measure.period == "ttm"


def test_a_non_owner_selection_is_a_proxy_carrying_its_disclosure() -> None:
    """The live margin shape: no wired source owns the metric, an alternative is selected and
    published. That is a stand-in — a Proxy — and the disclosure says so in the record's own
    terms rather than leaving the reader to infer it from ``is_authoritative``."""
    decision = resolve_metric_observations(
        "revenue",
        [_obs(source="yfinance", value=100.0), _obs(source="sec_edgar", value=101.0)],
        clock=_clock(),
    )
    assert decision.status == "accepted"
    assert isinstance(decision.measure, Proxy)
    assert decision.measure.proxy_of == "revenue"
    assert decision.measure.value == decision.value
    assert "no wired source owns revenue" in decision.measure.disclosure
    # The disclosure names the source the value actually came from — the selected one, not
    # whichever candidate happened to be listed first.
    assert decision.selected_source in decision.measure.disclosure


def test_no_eligible_observation_is_unavailable_with_the_records_own_code() -> None:
    decision = resolve_metric_observations("not_a_metric", [_obs(source="anyone")], clock=_clock())
    assert isinstance(decision.measure, Unavailable)
    assert decision.measure.reason_code == "no_eligible_observation"


def test_a_declined_row_is_withheld_not_unavailable() -> None:
    """A declined row is a real number FinRobot chooses not to state, which is a different fact
    from never having obtained one — and the registry row is where the record already says
    which. The decision's own ``status`` is untouched: this is provenance, not a re-decision."""
    decision = resolve_metric_observations("sec_xbrl_preferred_stock_fill", [], clock=_clock())
    assert decision.status == "unavailable"  # unchanged for every existing reader
    assert isinstance(decision.measure, Withheld)
    assert decision.measure.reason_code == "owner_decision_unwired"
    assert decision.measure.reason_code in DECLINED_REASON_CODES
    assert decision.measure.evidence  # the row's own definition of what it would fill


def test_a_measure_code_is_the_registrys_own_spelling() -> None:
    """A code is carried VERBATIM, never re-spelled at the measure site. §9.6 fixes
    UPPER_SNAKE_CASE, but today's live vocabulary is lower_snake — so upper-casing here would
    mint a second code for one cause, and a reader's lookup table would need two keys. The
    normalization is §9.6's to make, in one pass over the whole vocabulary."""
    decision = resolve_metric_observations("not_a_metric", [], clock=_clock())
    assert decision.measure.reason_code == "no_eligible_observation"
    assert not re.search(r"[A-Z]", decision.measure.reason_code)


def test_unknown_and_declined_metrics_are_unavailable_never_a_value() -> None:
    unknown = resolve_metric_observations(
        "not_a_metric", [_obs(metric="not_a_metric", source="anyone")], clock=_clock()
    )
    assert unknown.status == "unavailable"
    assert unknown.reason_code == "no_eligible_observation"
    assert unknown.value is None
    assert unknown.selected_source is None
    assert unknown.candidates == ()

    declined = resolve_metric_observations("sec_xbrl_preferred_stock_fill", [], clock=_clock())
    assert declined.status == "unavailable"
    assert declined.value is None


def test_no_eligible_observation_is_none_never_zero_and_never_an_average() -> None:
    """Two non-owner sources disagree without an owner: pick ONE (named), never its
    mean, and an absent owner is ``None`` — not 0."""
    absent = resolve_metric_observations(
        "revenue", [_obs(source="fmp", value=None)], clock=_clock()
    )
    assert absent.status == "unavailable"
    assert absent.value is None

    two_alt = resolve_metric_observations(
        "revenue",
        [_obs(source="yfinance", value=100.0), _obs(source="sec_edgar", value=110.0)],
        clock=_clock(),
    )
    # Owner absent (never contributed) + eligible alternatives within tolerance:
    # accepted but not authoritative; the value is ONE source's, never the mean.
    assert two_alt.status == "accepted"
    assert two_alt.reason_code == "owner_absent_alternative_selected"
    assert two_alt.value in (100.0, 110.0)
    assert two_alt.value != 105.0  # never the average
    assert two_alt.is_authoritative is False


def test_owner_selected_is_authoritative() -> None:
    decision = resolve_metric_observations("revenue", [_obs()], clock=_clock())
    assert decision.status == "accepted"
    # Rule 3 tags the SELECTED candidate with the authority reason; Rule 5 fixes the
    # decision-level reason (no other eligible source, so within_tolerance).
    assert decision.reason_code == "within_tolerance"
    assert decision.candidates[0].reason_code == "authoritative_selected"
    assert decision.is_authoritative is True
    assert decision.value == 100.0
    assert decision.policy_version == POLICY_VERSION
    assert decision.basis == METRIC_REGISTRY_BY_NAME["revenue"].basis


def test_measured_payload_labels_still_compare_and_surface_the_gap() -> None:
    """Measured live ``financials:v5`` shapes: FMP carries ``period_basis="ttm"`` with
    ``fiscal_year`` 2026-07-03; yfinance has NO ``period_basis`` key and 2026-06-30
    (3 days apart). A strict key equality would call every such pair a
    ``definition_mismatch_period`` and silently disable the BUG-007 divergence
    channel — so an 18% revenue gap must come out as a CONFLICT."""
    decision = resolve_metric_observations(
        "revenue",
        [
            _obs(source="fmp", value=1_000.0, period_end=date(2026, 7, 3), period_basis="ttm"),
            _obs(source="yfinance", value=1_180.0, period_end=date(2026, 6, 30), period_basis=None),
        ],
        clock=_clock(),
    )
    assert decision.status == "conflict"
    assert decision.reason_code == "above_tolerance_published_flagged"
    assert all(c.reason_code != "definition_mismatch_period" for c in decision.candidates)
    alternative = next(c for c in decision.candidates if c.source == "yfinance")
    assert alternative.eligible is True
    assert alternative.reason_code == "above_tolerance_published_flagged"


def test_a_genuinely_different_period_is_a_definition_mismatch() -> None:
    """Adjacent periods are >= ~84 days apart, so 45 days separates "same period,
    different label" from two providers reporting different fiscal periods."""
    decision = resolve_metric_observations(
        "revenue",
        [
            _obs(source="fmp", value=1_000.0, period_end=date(2026, 6, 30)),
            _obs(source="yfinance", value=1_000.0, period_end=date(2025, 12, 31)),
        ],
        clock=_clock(),
    )
    assert decision.status == "accepted"
    assert (
        next(c for c in decision.candidates if c.source == "yfinance").reason_code
        == "definition_mismatch_period"
    )


def test_unknown_basis_and_a_near_period_end_are_comparable() -> None:
    decision = resolve_metric_observations(
        "net_income",
        [
            _obs(metric="net_income", source="fmp", value=100.0, period_basis="ttm"),
            _obs(
                metric="net_income",
                source="yfinance",
                value=104.0,
                period_basis=None,
                period_end=date(2025, 12, 27),
            ),
        ],
        clock=_clock(),
    )
    assert decision.status == "accepted"
    assert decision.reason_code == "sources_agree"
    assert all(c.eligible for c in decision.candidates)


@pytest.mark.parametrize(
    "override",
    [
        {"period_end": date(2025, 9, 30)},
        {"period_basis": "annual"},
    ],
)
def test_differing_period_is_a_definition_mismatch_that_leaves_status_accepted(
    override: dict[str, object],
) -> None:
    decision = resolve_metric_observations(
        "revenue", [_obs(), _obs(source="yfinance", **override)], clock=_clock()
    )
    assert decision.status == "accepted"
    other = next(c for c in decision.candidates if c.source == "yfinance")
    assert other.eligible is False
    assert other.reason_code == "definition_mismatch_period"


def test_unit_and_currency_mismatches_are_named_in_order() -> None:
    unit = resolve_metric_observations(
        "revenue", [_obs(), _obs(source="yfinance", unit="EUR")], clock=_clock()
    )
    assert next(c for c in unit.candidates if c.source == "yfinance").reason_code == (
        "definition_mismatch_unit"
    )
    currency = resolve_metric_observations(
        "revenue", [_obs(), _obs(source="yfinance", currency="EUR")], clock=_clock()
    )
    assert next(c for c in currency.candidates if c.source == "yfinance").reason_code == (
        "definition_mismatch_currency"
    )
    both = resolve_metric_observations(
        "revenue", [_obs(), _obs(source="yfinance", currency="EUR", unit="EUR")], clock=_clock()
    )
    assert next(c for c in both.candidates if c.source == "yfinance").reason_code == (
        "definition_mismatch_currency"
    )


def test_caliber_divergent_never_reports_conflict() -> None:
    """EBITDA operating vs reported: an eligible alternative is recorded as a
    caliber mismatch, so a 60% gap can never masquerade as a conflict."""
    decision = resolve_metric_observations(
        "ebitda",
        [
            _obs(metric="ebitda", value=1_000.0),
            _obs(metric="ebitda", source="yfinance", value=1_600.0),
        ],
        clock=_clock(),
    )
    assert decision.status == "accepted"
    assert decision.reason_code == "within_tolerance"
    assert decision.is_authoritative is True
    assert all(c.reason_code != "above_tolerance_published_flagged" for c in decision.candidates)
    alternative = next(c for c in decision.candidates if c.source == "yfinance")
    assert alternative.eligible is False
    assert alternative.reason_code == "definition_mismatch_caliber"


@pytest.mark.parametrize(
    ("metric", "unit", "value"),
    [
        ("ebitda", "USD", 1_463_500_032.0),
        ("gross_margin", "ratio", 0.43865),
        ("total_debt", "USD", 2_842_299_904.0),
    ],
)
def test_lone_alternative_on_a_caliber_divergent_row_is_a_value_not_an_absence(
    metric: str, unit: str, value: float
) -> None:
    """Live EHC run: FMP never answered, only yfinance did. The report DID publish an
    EBITDA / gross margin / total debt, so a caliber caveat must not masquerade as an
    ``unavailable`` value. ``caliber_divergent`` forbids comparing a gap against a
    SELECTED observation — it does not mean a lone reading supplies nothing."""
    decision = resolve_metric_observations(
        metric,
        [_obs(metric=metric, source="yfinance", unit=unit, value=value)],
        clock=_clock(),
    )
    assert decision.status == "accepted"
    assert decision.is_authoritative is False
    assert decision.reason_code == "owner_absent_alternative_selected"
    assert decision.value == value
    assert decision.disagreement_pct is None
    assert decision.comparability == "caliber_divergent"
    candidate = decision.candidates[0]
    assert candidate.eligible is True
    assert candidate.reason_code != "definition_mismatch_caliber"


def test_caliber_divergent_row_with_no_observation_is_unavailable() -> None:
    decision = resolve_metric_observations("ebitda", [], clock=_clock())
    assert decision.status == "unavailable"
    assert decision.reason_code == "no_eligible_observation"
    assert decision.value is None


@pytest.mark.parametrize(
    "owner_override",
    [
        {"value": float("nan")},
        {"value": 0.0},  # market_cap is positive=True
    ],
)
def test_invalid_owner_with_a_fresh_alternative_falls_back_and_names_it(
    owner_override: dict[str, object],
) -> None:
    decision = resolve_metric_observations(
        "market_cap",
        [
            _obs(metric="market_cap", **owner_override),
            _obs(metric="market_cap", source="yfinance", value=2_000_000_000.0),
        ],
        clock=_clock(),
    )
    assert decision.status == "fallback"
    assert decision.is_authoritative is False
    assert decision.reason_code == "canonical_value_invalid_fallback_selected"
    assert decision.value == 2_000_000_000.0
    assert decision.selected_source == "yfinance"


def test_stale_owner_falls_back_to_a_fresh_alternative() -> None:
    clock = _clock()
    owner = _obs(
        metric="current_price",
        source="eodhd",
        value=100.0,
        period_basis="session",
        period_end=date(2026, 1, 19),
        effective_at=clock - timedelta(days=10),
    )
    alternative = _obs(
        metric="current_price",
        source="yfinance",
        value=101.0,
        period_basis="session",
        period_end=date(2026, 1, 19),
        effective_at=clock,
    )
    decision = resolve_metric_observations("current_price", [owner, alternative], clock=clock)
    assert decision.status == "fallback"
    assert decision.value == 101.0
    assert decision.selected_source == "yfinance"
    stale = next(c for c in decision.candidates if c.source == "eodhd")
    assert stale.reason_code == "stale_beyond_freshness_policy"


def test_live_retrieval_after_the_run_ceiling_is_never_lookahead() -> None:
    """``engine/pipelines/runner.py`` pins the ceiling at the run's START, so every
    live fetch has ``retrieved_at > run_as_of`` by construction. That is when WE
    looked, not what the source knew — it must stay eligible. (Regression: gating on
    ``retrieved_at`` turned all eight decisions of the live EHC artifact
    ``art_2026-10-13T22:36:11_EHC_equity_research_dfa427`` into
    ``unavailable``/``after_run_as_of`` and caveated a healthy fetch.)"""
    clock = _clock()
    run_as_of = clock - timedelta(seconds=5)  # set_run_as_of(now) at run start
    decision = resolve_metric_observations(
        "revenue",
        [_obs(source="fmp", retrieved_at=clock)],
        clock=clock,
        run_as_of=run_as_of,
    )
    assert decision.status == "accepted"
    assert decision.reason_code == "within_tolerance"
    assert decision.candidates[0].eligible is True
    assert decision.candidates[0].reason_code != "after_run_as_of"


def test_published_at_gates_only_when_known_and_later_than_the_ceiling() -> None:
    clock = _clock()
    ceiling = clock - timedelta(days=1)

    late = resolve_metric_observations(
        "revenue",
        [_obs(source="fmp", published_at=clock)],
        clock=clock,
        run_as_of=ceiling,
    )
    assert late.status == "unavailable"
    assert late.reason_code == "after_run_as_of"
    assert late.value is None

    known_before = resolve_metric_observations(
        "revenue",
        [_obs(source="fmp", published_at=ceiling - timedelta(days=1))],
        clock=clock,
        run_as_of=ceiling,
    )
    assert known_before.status == "accepted"
    assert known_before.candidates[0].eligible is True


def test_unknown_published_at_cannot_fire_the_as_of_gate() -> None:
    """A vendor statement read carries ``published_at=None``, so a retrieval after
    the ceiling must not be relabelled as lookahead — only the freshness policy may
    exclude it."""
    clock = _clock()
    decision = resolve_metric_observations(
        "revenue",
        [_obs(source="fmp", published_at=None, retrieved_at=clock + timedelta(days=30))],
        clock=clock,
        run_as_of=clock - timedelta(seconds=1),
    )
    assert decision.status == "accepted"
    assert decision.candidates[0].eligible is True
    assert decision.candidates[0].reason_code != "after_run_as_of"


def test_colineage_agreement_is_flagged_non_independent() -> None:
    decision = resolve_metric_observations(
        "revenue",
        [_obs(source="fmp", value=100.0), _obs(source="fmp:provider-cache", value=100.0)],
        clock=_clock(),
    )
    assert decision.agreement_is_independent is False
    cached = next(c for c in decision.candidates if c.source == "fmp:provider-cache")
    assert cached.non_independent is True
    assert cached.reason_code == "non_independent_agreement"
    # The decision itself still stands on the owner.
    assert decision.status == "accepted"
    assert decision.reason_code == "sources_agree"
    assert decision.selected_source == "fmp"
    owner_candidate = next(c for c in decision.candidates if c.source == "fmp")
    assert owner_candidate.reason_code == "authoritative_selected"


def test_derived_agreement_is_non_independent() -> None:
    decision = resolve_metric_observations(
        "revenue",
        [
            _obs(source="fmp", value=100.0),
            _obs(source="yfinance", value=100.0, derived_from=("fmp", "market_cap")),
        ],
        clock=_clock(),
    )
    assert decision.agreement_is_independent is False
    assert (
        next(c for c in decision.candidates if c.source == "yfinance").reason_code
        == "non_independent_agreement"
    )


def test_independent_agreement_within_tolerance_reports_sources_agree() -> None:
    decision = resolve_metric_observations(
        "revenue",
        [_obs(source="fmp", value=100.0), _obs(source="yfinance", value=100.5)],
        clock=_clock(),
    )
    assert decision.status == "accepted"
    assert decision.reason_code == "sources_agree"
    assert decision.agreement_is_independent is True
    assert decision.disagreement_pct is None


def test_over_tolerance_is_a_conflict_with_the_widest_deviation() -> None:
    decision = resolve_metric_observations(
        "revenue",
        [
            _obs(source="fmp", value=100.0),
            _obs(source="yfinance", value=140.0),
            _obs(source="sec_edgar", value=118.0),
        ],
        clock=_clock(),
    )
    assert decision.status == "conflict"
    assert decision.reason_code == "above_tolerance_published_flagged"
    assert decision.value == 100.0  # the owner's number still stands
    assert decision.disagreement_pct == pytest.approx(40.0 / 140.0, rel=1e-3)
    flagged = {
        c.source
        for c in decision.candidates
        if c.reason_code == "above_tolerance_published_flagged"
    }
    assert flagged == {"yfinance", "sec_edgar"}


def test_absolute_tolerance_is_a_floor_not_an_alternative_band() -> None:
    """The price rule is "greater of one tick or 0.05%": a gap is a conflict only
    when the RELATIVE band AND the absolute floor are both exceeded."""
    clock = _clock()
    common = {"period_basis": "session", "effective_at": clock, "retrieved_at": clock}
    # 2 cents on a $0.50 stock: 3.8% relative (INSIDE the 5% band), 0.02 absolute
    # (over the 0.01 floor) — the vendors agree in every meaningful sense.
    inside_band = resolve_metric_observations(
        "current_price",
        [
            _obs(metric="current_price", source="eodhd", value=0.50, **common),
            _obs(metric="current_price", source="yfinance", value=0.52, **common),
        ],
        clock=clock,
    )
    assert inside_band.status == "accepted"
    assert inside_band.reason_code == "sources_agree"

    # Over BOTH the relative band and the floor -> conflict.
    over_both = resolve_metric_observations(
        "current_price",
        [
            _obs(metric="current_price", source="eodhd", value=100.0, **common),
            _obs(metric="current_price", source="yfinance", value=120.0, **common),
        ],
        clock=clock,
    )
    assert over_both.status == "conflict"
    assert over_both.reason_code == "above_tolerance_published_flagged"


def test_derived_candidate_never_manufactures_a_conflict() -> None:
    """A count rederived as market_cap/price is a re-expression, not a second
    opinion: it must be set aside, not turned into a caveating conflict."""
    decision = resolve_metric_observations(
        "market_cap",
        [
            _obs(metric="market_cap", source="yfinance", value=100.0),
            _obs(
                metric="market_cap",
                source="zprovider",
                value=106.0,
                derived_from=("market_cap", "current_price"),
            ),
        ],
        clock=_clock(),
    )
    assert decision.selected_source == "yfinance"
    assert decision.status == "accepted"
    assert decision.reason_code == "owner_absent_alternative_selected"
    derived = next(c for c in decision.candidates if c.source == "zprovider")
    assert derived.eligible is False
    assert derived.non_independent is True
    assert derived.reason_code == "non_independent_agreement"
    assert decision.disagreement_pct is None
    assert decision.agreement_is_independent is True


def test_derived_selected_with_an_independent_candidate_is_a_real_conflict() -> None:
    """The asymmetry: non-independence is a property of the CANDIDATE. When the
    derived count IS the selected value, an independent count that contradicts it
    is a genuine conflict."""
    decision = resolve_metric_observations(
        "shares_outstanding",
        [
            _obs(
                metric="shares_outstanding",
                source="fmp",
                unit="shares",
                value=100.0,
                derived_from=("market_cap", "current_price"),
            ),
            _obs(
                metric="shares_outstanding",
                source="yfinance",
                unit="shares",
                value=94.0,
            ),
        ],
        clock=_clock(),
    )
    assert decision.selected_source == "fmp"
    assert decision.is_authoritative is True
    assert decision.status == "conflict"
    assert decision.reason_code == "above_tolerance_published_flagged"
    assert decision.disagreement_pct == pytest.approx(0.06, rel=1e-3)
    independent = next(c for c in decision.candidates if c.source == "yfinance")
    assert independent.non_independent is False
    assert independent.eligible is True


def test_decision_is_order_independent() -> None:
    observations = [
        _obs(source="fmp", value=100.0),
        _obs(source="yfinance", value=100.5),
        _obs(source="sec_edgar", value=140.0, period_end=date(2025, 6, 30)),
    ]
    forward = resolve_metric_observations("revenue", observations, clock=_clock())
    backward = resolve_metric_observations("revenue", list(reversed(observations)), clock=_clock())
    assert forward == backward
    assert [c.source for c in forward.candidates] == ["fmp", "sec_edgar", "yfinance"]


def test_owner_absent_is_distinct_from_owner_invalid() -> None:
    """The chain head rate-limiting out is NOT the same as it answering garbage."""
    clock = _clock()
    absent = resolve_metric_observations(
        "revenue", [_obs(source="yfinance", value=100.0)], clock=clock
    )
    assert absent.status == "accepted"
    assert absent.reason_code == "owner_absent_alternative_selected"
    assert absent.is_authoritative is False

    invalid = resolve_metric_observations(
        "revenue",
        [_obs(source="fmp", value=float("nan")), _obs(source="yfinance", value=100.0)],
        clock=clock,
    )
    assert invalid.status == "fallback"
    assert invalid.reason_code == "canonical_value_invalid_fallback_selected"
    assert invalid.is_authoritative is False


def test_owner_absent_with_an_over_tolerance_candidate_becomes_conflict() -> None:
    decision = resolve_metric_observations(
        "revenue",
        [_obs(source="yfinance", value=100.0), _obs(source="sec_edgar", value=140.0)],
        clock=_clock(),
    )
    assert decision.selected_source == "sec_edgar"  # lexicographically smallest
    assert decision.status == "conflict"
    assert decision.reason_code == "above_tolerance_published_flagged"
    assert decision.is_authoritative is False


def test_absent_owner_defers_to_the_lexicographically_smallest_source() -> None:
    decision = resolve_metric_observations(
        "revenue",
        [_obs(source="zprovider", value=100.0), _obs(source="aprovider", value=110.0)],
        clock=_clock(),
    )
    assert decision.status == "accepted"
    assert decision.reason_code == "owner_absent_alternative_selected"
    assert decision.selected_source == "aprovider"
    assert decision.value == 110.0
    assert decision.is_authoritative is False


def test_every_decision_status_and_reason_is_from_the_closed_vocabulary() -> None:
    decision = resolve_metric_observations(
        "revenue", [_obs(source="fmp", value=float("inf"))], clock=_clock()
    )
    assert decision.status in DECISION_STATUSES
    assert decision.reason_code in DECISION_REASON_CODES
    assert decision.value is None


def test_reconciliation_report_indexes_decisions_by_metric() -> None:
    decision = resolve_metric_observations("revenue", [_obs()], clock=_clock())
    report = ReconciliationReport(
        policy_version=POLICY_VERSION,
        run_as_of=None,
        clock=_clock(),
        decisions=(decision,),
    )
    assert report.decision("revenue") is decision
    assert report.decision("net_income") is None


def test_metric_observation_and_decision_are_immutable() -> None:
    observation = _obs()
    with pytest.raises(dataclasses.FrozenInstanceError):
        observation.source = "other"  # type: ignore[misc]
    decision = resolve_metric_observations("revenue", [observation], clock=_clock())
    assert isinstance(decision, MetricDecision)
    with pytest.raises(dataclasses.FrozenInstanceError):
        decision.status = "accepted"  # type: ignore[misc]
