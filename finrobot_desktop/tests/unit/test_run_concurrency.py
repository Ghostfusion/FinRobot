"""``run_concurrency`` — the provider-cap policy and the registry drift guard.

The policy turns per-provider declared limits into the effective run cap for the
Coverage "re-run all" control. Values are pinned to the registry declarations
(one source of truth) so a change there flows straight through.
"""

from __future__ import annotations

import importlib

from finrobot.engine.data.registry import (
    REGISTRY,
    provider_registry_id,
    provider_runtime_name,
)
from finrobot.run_concurrency import (
    RUN_CEILING,
    primary_slot_ids,
    resolve_run_concurrency,
)


def _source(provider_id: str) -> str:
    limit = REGISTRY[provider_id].limit
    assert limit is not None
    return limit.source


def _max(provider_id: str) -> int:
    limit = REGISTRY[provider_id].limit
    assert limit is not None
    return limit.max_concurrency


def test_primary_provider_below_the_ceiling_binds_and_is_named() -> None:
    # No primary-slot provider declares below 4 in the shipped table, so raise the
    # ceiling: moomoo's 4 is then the strictly tighter bound and must be named.
    plan = resolve_run_concurrency(["moomoo"], ceiling=8)
    assert plan.limit == 4
    assert plan.ceiling == 8
    assert plan.binding_provider == "moomoo"
    assert plan.binding_reason == _source("moomoo")
    assert plan.undeclared_count == 0
    (view,) = plan.providers
    assert view.provider == "moomoo"
    assert view.declared is True and view.binding is True


def test_moomoo_at_the_ceiling_binds() -> None:
    # moomoo == 4 == the ceiling, so it ties and is the binder (the contract's
    # "a configured moomoo at 4 reports moomoo").
    plan = resolve_run_concurrency(["moomoo"])
    assert plan.limit == RUN_CEILING == 4
    assert plan.binding_provider == "moomoo"
    assert plan.binding_reason == _source("moomoo")


def test_nothing_declared_ceiling_binds_with_no_provider() -> None:
    plan = resolve_run_concurrency(["yfinance", "finnhub"])
    assert plan.limit == RUN_CEILING
    assert plan.binding_provider is None
    assert str(RUN_CEILING) in plan.binding_reason
    assert plan.providers == []
    assert plan.undeclared_count == 2


def test_unknown_runtime_name_never_lowers_the_limit() -> None:
    plan = resolve_run_concurrency(["totally_unknown_vendor"])
    assert plan.limit == RUN_CEILING
    assert plan.binding_provider is None
    assert plan.providers == []
    assert plan.undeclared_count == 1


def test_sec_edgar_alias_resolves_from_runtime_name() -> None:
    # The live chain reports "edgar_tools"; the limit is declared under the
    # registry id "sec_edgar". The inverse map must bridge the two.
    plan = resolve_run_concurrency(["edgar_tools"])
    (view,) = plan.providers
    assert view.provider == "edgar_tools"
    assert view.max_concurrency == _max("sec_edgar")
    assert view.source == _source("sec_edgar")
    # 10 is above the desktop ceiling, so the ceiling binds and no provider does.
    assert plan.limit == RUN_CEILING
    assert plan.binding_provider is None


def test_ceiling_caps_a_higher_provider_limit_and_lower_one_wins() -> None:
    plan = resolve_run_concurrency(["edgar_tools", "moomoo"])
    assert plan.limit == 4
    assert plan.undeclared_count == 0
    # moomoo's 4 ties the effective limit; edgar's 10 does not.
    assert plan.binding_provider == "moomoo"
    binding = [v for v in plan.providers if v.binding]
    assert [v.provider for v in binding] == ["moomoo"]


def test_fallback_tail_declaration_is_reported_but_never_lowers_the_limit() -> None:
    """A declared limit on a provider that owns NO primary slot must not bind.

    alpha_vantage/newsapi sit at the tail of every chain they appear in and are
    reached only when a primary fails; letting their 1-request budget cap EVERY
    batch would throttle a desk that mostly never calls them. They still appear in
    the payload (the user is told what they declared) — with ``binding=False``.
    """
    plan = resolve_run_concurrency(["moomoo", "alpha_vantage", "edgar_tools"])
    assert plan.limit == 4  # moomoo, NOT alpha_vantage's 1
    assert plan.binding_provider == "moomoo"
    by_name = {v.provider: v for v in plan.providers}
    assert by_name["alpha_vantage"].max_concurrency == 1
    assert by_name["alpha_vantage"].declared is True
    assert by_name["alpha_vantage"].binding is False
    assert sum(1 for v in plan.providers if v.binding) == 1


def test_fallback_tail_alone_leaves_the_ceiling_binding() -> None:
    plan = resolve_run_concurrency(["alpha_vantage", "newsapi"])
    assert plan.limit == RUN_CEILING
    assert plan.binding_provider is None
    assert "primary-slot" in plan.binding_reason
    assert {v.provider for v in plan.providers} == {"alpha_vantage", "newsapi"}
    assert all(v.declared and not v.binding for v in plan.providers)


def test_primary_slot_rule_matches_the_priority_table() -> None:
    """The rule's INPUT is the live priority table — pin the coupling.

    moomoo leads 15 categories and sec_edgar owns ``sec_filings``, so their
    declarations can cap a batch; neither fallback-tail vendor leads any category,
    so theirs cannot. Editing PRIORITY to lead with one of them changes the cap and
    must fail here first.
    """
    primaries = primary_slot_ids()
    assert {"moomoo", "sec_edgar"} <= primaries
    assert "alpha_vantage" not in primaries
    assert "newsapi" not in primaries


def test_custom_ceiling_can_bind_without_a_provider() -> None:
    plan = resolve_run_concurrency(["edgar_tools"], ceiling=2)
    assert plan.limit == 2
    assert plan.ceiling == 2
    assert plan.binding_provider is None
    assert "2" in plan.binding_reason


def test_duplicate_names_are_deduplicated() -> None:
    plan = resolve_run_concurrency(["moomoo", "moomoo", "moomoo"])
    assert plan.undeclared_count == 0
    assert len(plan.providers) == 1


def test_declared_limits_name_a_real_runtime_name() -> None:
    """Drift guard: every declared limit must correspond to a runtime name that a
    registered provider actually reports as its ``.name`` (so the resolver's
    registry-id → runtime-name mapping can never silently stop matching)."""
    declared_ids = [pid for pid, spec in REGISTRY.items() if spec.limit is not None]
    # The four owner-declared rows the contract fixes.
    assert set(declared_ids) == {"moomoo", "sec_edgar", "alpha_vantage", "newsapi"}
    for provider_id in declared_ids:
        spec = REGISTRY[provider_id]
        cls = getattr(importlib.import_module(spec.module), spec.class_name)
        reported = getattr(cls, "name").fget(None)
        assert reported == provider_runtime_name(provider_id)
        assert provider_registry_id(reported) == provider_id
