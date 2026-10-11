# finrobot/engine/data/catalog.py
"""Declarative endpoint catalog for the Data Layer v3 probe.

Each provider module owns its rows (``ENDPOINTS: dict[Category, EndpointSpec]``)
so adding a vendor never edits a shared table. :func:`endpoint_catalog`
aggregates them from :data:`registry.REGISTRY` for the probe.

The catalog is the single source of truth for (a) which categories a provider
claims, (b) the exact request shape, and (c) what the probe exercises.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass, field

from finrobot.engine.data.categories import Category
from finrobot.engine.data.registry import REGISTRY


@dataclass(frozen=True)
class EndpointSpec:
    """One callable endpoint: capability, HTTP shape, and key placement.

    ``params`` values may contain the placeholder ``$KEY`` — the probe
    substitutes the provider's credential there (query-param auth, e.g.
    ``api_token``), while header-auth providers leave it out and set
    :attr:`auth_header` instead.
    """

    capability: Category
    method: str
    url: str
    params: dict[str, str] = field(default_factory=dict)
    auth_header: str | None = None  # e.g. "Authorization" — value from auth_value
    auth_value: str = "$KEY"  # may include a scheme prefix, e.g. "Token $KEY"


def endpoint_catalog() -> dict[str, dict[Category, EndpointSpec]]:
    """Aggregate every provider's ``ENDPOINTS`` declared in its module.

    Providers without a module-level ``ENDPOINTS`` (e.g. the vendored
    yfinance adapter that predates the catalog) are simply absent — the
    probe reports them as "no catalog rows".
    """
    catalog: dict[str, dict[Category, EndpointSpec]] = {}
    for provider_id, spec in REGISTRY.items():
        module = importlib.import_module(spec.module)
        rows = getattr(module, "ENDPOINTS", None)
        if rows:
            catalog[provider_id] = rows
    return catalog
