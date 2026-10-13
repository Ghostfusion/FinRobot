"""Run-concurrency policy over the provider registry facts (Coverage re-run-all).

The Coverage Desk's "re-run all reports" fans the research pipeline across many
tickers at once. How many may run in parallel is not really the desktop's
decision — it is whichever upstream data provider throttles first. This module
turns the per-provider
:class:`~finrobot.engine.data.registry.ConcurrencyLimit` declarations into one
plan: the effective ``limit`` (never above the desktop LLM ceiling, never above
the tightest declared provider), which provider is the binder, and the full
audit trail the Coverage UI shows the user.

Pure policy: it imports only the provider registry, never routes or the data
layer, so the same plan backs both the HTTP layer and its unit tests (ADR-0012
layering — orchestration-only modules stay importable without a live app).
Sibling of :mod:`finrobot.ratelimit`, which owns the orthogonal inbound
token-bucket guard.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from finrobot.engine.data.categories import PRIORITY
from finrobot.engine.data.registry import REGISTRY, provider_registry_id


def primary_slot_ids() -> frozenset[str]:
    """Registry ids owning the TOP slot of at least one category chain.

    Only a primary-slot provider may cap a batch, because a declared
    *concurrent-connection* ceiling is only meaningful for what a run actually
    fans out to. A provider that appears nowhere but deep in a fallback tail is
    reached when a primary fails, its calls are then few, and the adapter's own
    pacing/retry path still applies — so letting its small budget cap EVERY batch
    would throttle a desk that mostly never calls it. (Concretely, in the live
    table ``alpha_vantage``/``newsapi`` are first in NO category, while ``moomoo``
    is first in 15 and ``sec_edgar`` owns ``sec_filings``.) The top entry of each
    ``PRIORITY`` list is the steady-state provider for that category; the table's
    own order is the authority, so this can never drift from it.
    """
    return frozenset(ids[0] for ids in PRIORITY.values() if ids)


# The desktop's own LLM concurrency budget. Kept here as the single source of
# truth — ``server._MAX_CONCURRENT_RUNS`` now re-exports this value. A provider's
# declared ceiling may LOWER the effective cap but can never raise it above this:
# beyond it the desktop's own model calls are the bottleneck, not the provider.
RUN_CEILING = 4


@dataclass(frozen=True)
class ProviderLimitView:
    """One declared provider limit as the UI sees it.

    ``provider`` is the runtime name (the vocabulary ``provider_status()`` and the
    data-source panel already use), so a declared ``sec_edgar`` reports
    ``edgar_tools``. ``binding`` is True on the one provider that set the plan's
    effective limit.
    """

    provider: str
    max_concurrency: int | None
    source: str | None
    declared: bool
    binding: bool


@dataclass(frozen=True)
class RunConcurrencyPlan:
    """The resolved concurrency cap plus the reasoning behind it.

    ``providers`` lists ONLY the declared providers (each carrying its ceiling,
    source, and ``binding`` flag); ``undeclared_count`` counts the remaining
    live-chain names — the self-paced providers that impose no ceiling of their
    own. ``binding_reason`` names whoever actually set the limit: the binding
    provider's own source, or the desktop LLM ceiling when no provider is tighter.
    """

    limit: int
    ceiling: int
    binding_provider: str | None
    binding_reason: str
    providers: list[ProviderLimitView]
    undeclared_count: int


def resolve_run_concurrency(
    runtime_names: Iterable[str], *, ceiling: int = RUN_CEILING
) -> RunConcurrencyPlan:
    """Resolve the effective run cap from the live providers' declared limits.

    ``runtime_names`` are the health-available provider names from the live chain
    (``DataLayer.provider_status()``); unknown names never lower the limit (they
    simply count as undeclared). Only a **primary-slot** provider's ceiling can
    lower it (see :func:`primary_slot_ids`) — a fallback-tail provider is still
    REPORTED, so the user can see it declared one, but it never throttles a batch
    it will barely be called for. The effective ``limit`` is therefore
    ``min(ceiling, every primary-slot declared max_concurrency)``. The binder is
    the primary-slot provider whose ceiling equals that limit — so a configured
    ``moomoo`` at 4 reports ``moomoo``; when the desktop ceiling is the tighter
    bound instead, no provider matches and ``binding_provider`` is None with
    ``binding_reason`` naming the ceiling. Duplicate names are de-duplicated;
    input order is kept so the plan is deterministic.
    """
    primaries = primary_slot_ids()
    declared: list[tuple[str, int, str, bool]] = []
    undeclared_count = 0
    seen: set[str] = set()
    for name in runtime_names:
        if name in seen:
            continue
        seen.add(name)
        registry_id = provider_registry_id(name)
        spec = REGISTRY.get(registry_id)
        limit = spec.limit if spec is not None else None
        if limit is None:
            undeclared_count += 1
            continue
        declared.append((name, limit.max_concurrency, limit.source, registry_id in primaries))

    effective = ceiling
    for _, max_concurrency, _, is_primary in declared:
        if is_primary:
            effective = min(effective, max_concurrency)

    # The binder is the primary-slot provider whose ceiling equals the effective
    # limit. When the LLM ceiling is the tighter of the two, no provider value
    # matches, so we fall through and name the ceiling in the reason instead.
    binding_provider: str | None = None
    binding_reason = (
        f"desktop LLM concurrency ceiling: {ceiling} concurrent runs "
        "(no primary-slot provider declares a lower limit)"
    )
    for name, max_concurrency, source, is_primary in declared:
        if is_primary and max_concurrency == effective:
            binding_provider = name
            binding_reason = source
            break

    providers = [
        ProviderLimitView(
            provider=name,
            max_concurrency=max_concurrency,
            source=source,
            declared=True,
            binding=name == binding_provider,
        )
        for name, max_concurrency, source, _ in declared
    ]
    return RunConcurrencyPlan(
        limit=effective,
        ceiling=ceiling,
        binding_provider=binding_provider,
        binding_reason=binding_reason,
        providers=providers,
        undeclared_count=undeclared_count,
    )
