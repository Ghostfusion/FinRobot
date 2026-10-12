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

import pytest

from finrobot.engine.models.metric_authority import (
    DECLINED_REASON_CODES,
    METRIC_REGISTRY,
    METRIC_REGISTRY_BY_NAME,
    METRIC_TOLERANCE_PCT,
    MetricRow,
    duplicate_metric_names,
    resolve_metric,
)

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
