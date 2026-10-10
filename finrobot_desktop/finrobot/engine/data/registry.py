# finrobot/engine/data/registry.py
"""Provider registry: id → module/class + credential env var + build policy.

One row per data provider. :func:`build_provider_chain` instantiates the
available ones (key present / gateway reachable / keyless) in a deterministic
global order; the *per-request* order comes from
:data:`finrobot.engine.data.categories.PRIORITY`.

See ``docs/DATA_PROVIDERS_V3_DESIGN.md`` §5.
"""

from __future__ import annotations

import importlib
import logging
from dataclasses import dataclass
from typing import Any, Callable, cast

from finrobot.engine.data.categories import PRIORITY
from finrobot.engine.data.interface import DataProvider
from finrobot.env import ENV_BY_PROVIDER

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProviderSpec:
    """How to build one provider.

    ``kind``: ``keyed`` (needs an API key), ``keyless`` (no credential),
    ``identity`` (SEC User-Agent identity, not a secret), ``gateway`` (local
    OpenD-style gateway reached by host/port).
    """

    id: str
    module: str
    class_name: str
    kind: str = "keyed"

    @property
    def env_var(self) -> str | None:
        """Credential env-var name from the canonical map (None = keyless)."""
        return ENV_BY_PROVIDER.get(self.id)


def _spec(provider_id: str, module: str, class_name: str, kind: str = "keyed") -> ProviderSpec:
    return ProviderSpec(provider_id, module, class_name, kind)


_P = "finrobot.engine.data.providers"

#: Providers referenced by the owner's priority table, plus the keyed providers
#: present in ``.env`` that the table does not list (fmp, massive) and the
#: pre-existing adanos. Unlisted providers are registered but appear in no
#: priority list, so they are reachable only when a category names them.
REGISTRY: dict[str, ProviderSpec] = {
    # ── table providers ──────────────────────────────────────────────────
    "eodhd": _spec("eodhd", f"{_P}.eodhd_provider", "EODHDProvider"),
    "moomoo": _spec("moomoo", f"{_P}.moomoo_provider", "MoomooProvider", "gateway"),
    "yfinance": _spec("yfinance", f"{_P}.yfinance_provider", "YFinanceProvider", "keyless"),
    "tiingo": _spec("tiingo", f"{_P}.tiingo_provider", "TiingoProvider"),
    "twelvedata": _spec("twelvedata", f"{_P}.twelvedata_provider", "TwelveDataProvider"),
    "stockdata": _spec("stockdata", f"{_P}.stockdata_provider", "StockDataProvider"),
    "benzinga": _spec("benzinga", f"{_P}.benzinga_provider", "BenzingaProvider"),
    "finnhub": _spec("finnhub", f"{_P}.finnhub_provider", "FinnhubProvider"),
    "alpha_vantage": _spec("alpha_vantage", f"{_P}.alpha_vantage_provider", "AlphaVantageProvider"),
    "newsapi": _spec("newsapi", f"{_P}.newsapi_provider", "NewsApiProvider"),
    "fred": _spec("fred", f"{_P}.fred_provider", "FredProvider"),
    "polymarket": _spec("polymarket", f"{_P}.polymarket_provider", "PolymarketProvider", "keyless"),
    "gdelt": _spec("gdelt", f"{_P}.gdelt_provider", "GdeltProvider", "keyless"),
    "sec_edgar": _spec("sec_edgar", f"{_P}.edgar_provider", "EdgarToolsProvider", "identity"),
    "federal_reserve": _spec(
        "federal_reserve", f"{_P}.federal_reserve_provider", "FederalReserveProvider", "keyless"
    ),
    "cboe": _spec("cboe", f"{_P}.cboe_provider", "CboeProvider", "keyless"),
    # ── keyed providers present in .env but unlisted by the table ─────────
    "fmp": _spec("fmp", f"{_P}.fmp_provider", "FMPProvider"),
    "massive": _spec("massive", f"{_P}.massive_provider", "MassiveProvider"),
    "adanos": _spec("adanos", f"{_P}.adanos_provider", "AdanosProvider"),
    # Legacy composed news provider (yfinance headlines + optional Alpha Vantage
    # sentiment). Unlisted by the priority table, so it never outranks a listed
    # news source — but it keeps the always-on free headlines reachable.
    "news_aggregator": _spec(
        "news_aggregator", f"{_P}.news_aggregator", "NewsAggregatorProvider", "composite"
    ),
}


#: Registry id → runtime provider ``name``, for the ids where the two differ.
#: ``sec_edgar`` is the registry/env id, but ``EdgarToolsProvider.name`` reports
#: ``"edgar_tools"`` — the long-standing runtime name carried by the UI
#: (``DataSourcesPanel``), ``routes/settings.py``, cache provenance and the
#: provider tests. Category priority tables are written in registry-id
#: vocabulary, so any code that matches *runtime names* must resolve through
#: this map. Without it the ``sec_filings`` entry silently no-ops — invisible
#: while the category has a single vendor, but it would ignore SEC's rank the
#: moment a second filings provider is added.
PROVIDER_NAME_BY_ID: dict[str, str] = {"sec_edgar": "edgar_tools"}


def provider_runtime_name(provider_id: str) -> str:
    """Runtime ``.name`` a provider id registers under (identity by default)."""
    return PROVIDER_NAME_BY_ID.get(provider_id, provider_id)


def _global_order() -> list[str]:
    """Deterministic provider order = first appearance across the priority
    table, then any registry-only ids (registry insertion order).

    This order is what :meth:`DataLayer.provider_status` and cache-slot keys see;
    it is stable across runs so canonical cache slots don't churn.
    """
    seen: list[str] = []
    for providers in PRIORITY.values():
        for pid in providers:
            if pid not in seen:
                seen.append(pid)
    for pid in REGISTRY:
        if pid not in seen:
            seen.append(pid)
    return seen


def _reachable_gateway(host: str, port: int, timeout_s: float = 0.5) -> bool:
    """TCP-connect probe for a local gateway (moomoo OpenD). Never raises."""
    import socket

    try:
        with socket.create_connection((host or "127.0.0.1", int(port or 0)), timeout=timeout_s):
            return True
    except (OSError, ValueError, TypeError):
        return False


def build_provider(provider_id: str, settings: Any) -> DataProvider | None:
    """Instantiate one provider, or None when it should not register.

    None cases: a keyed provider with no key; an identity provider with an
    invalid identity; a gateway provider whose host/port is unreachable.
    """
    spec = REGISTRY.get(provider_id)
    if spec is None:
        return None

    if spec.kind == "keyless":
        return _load(spec)()

    if spec.kind == "composite":
        av_key = getattr(settings, "alpha_vantage_api_key", "") or ""
        return _load(spec)(alpha_vantage_api_key=av_key)

    if spec.kind == "identity":
        user_agent = getattr(settings, "sec_user_agent", "") or ""
        from finrobot.engine.data.providers.edgar_provider import _is_valid_identity

        if not _is_valid_identity(user_agent):
            return None
        return _load(spec)(user_agent=user_agent)

    if spec.kind == "gateway":
        host = getattr(settings, "moomoo_host", "") or ""
        port = getattr(settings, "moomoo_port", 0) or 0
        if not host or not port or not _reachable_gateway(host, port):
            logger.info("moomoo OpenD not reachable at %s:%s — provider skipped", host, port)
            return None
        return _load(spec)(host=host, port=port)

    key = settings.data_key(provider_id) if hasattr(settings, "data_key") else None
    if not key:
        return None
    try:
        return _load(spec)(api_key=key)
    except TypeError:
        # Providers that don't take ``api_key`` (none today) — fail loudly.
        logger.exception("provider %s does not accept api_key", provider_id)
        raise


def _load(spec: ProviderSpec) -> Callable[..., DataProvider]:
    """Import the provider class. Returned as an untyped callable because each
    provider has a different constructor signature."""
    module = importlib.import_module(spec.module)
    cls: Any = getattr(module, spec.class_name)
    return cast(Callable[..., DataProvider], cls)


def build_provider_chain(settings: Any) -> list[DataProvider]:
    """Build the single failover chain: every available provider, in global order."""
    providers: list[DataProvider] = []
    for provider_id in _global_order():
        try:
            provider = build_provider(provider_id, settings)
        except (ImportError, AttributeError, TypeError, ValueError, OSError, RuntimeError):
            logger.exception("failed to build provider %s — skipped", provider_id)
            continue
        if provider is not None:
            providers.append(provider)
    return providers


def order_for_category(category: Any, provider_names: list[str]) -> list[str]:
    """Reorder provider names by ``PRIORITY[category]``; unlisted names keep
    their relative order after the listed ones.

    Priority entries are registry **ids**, which are not always the runtime name
    a provider reports (``sec_edgar`` → ``edgar_tools``), so every id is resolved
    through :func:`provider_runtime_name` before ranking.
    """
    priority = PRIORITY.get(category, ())
    rank = {provider_runtime_name(pid): i for i, pid in enumerate(priority)}
    return sorted(provider_names, key=lambda name: rank.get(name, len(rank)))
