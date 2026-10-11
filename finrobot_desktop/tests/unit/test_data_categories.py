"""Structural invariants for the category priority table + endpoint catalog.

These guard the routing key of the single failover chain: every id the owner's
priority table names must be a known provider, must resolve to the runtime name
its provider actually registers under, and must either own catalog rows or be on
the documented vendored-adapter exemption list. Regression cover for the
``sec_filings`` bug where the table named the registry id ``sec_edgar`` while
``EdgarToolsProvider`` reports ``edgar_tools``, leaving the entry a silent no-op.
"""

from finrobot.engine.data.catalog import endpoint_catalog
from finrobot.engine.data.categories import PRIORITY_PROVIDER_IDS, Category
from finrobot.engine.data.registry import (
    PROVIDER_NAME_BY_ID,
    REGISTRY,
    order_for_category,
    provider_runtime_name,
)

#: Vendored adapters that predate the declarative catalog and declare no
#: module-level ``ENDPOINTS`` (see ``engine.data.catalog``), so the probe reports
#: them as ``no_catalog``. Documented limitation, not an oversight. ``fmp``,
#: ``finnhub`` and ``sec_edgar`` used to be exempt for this reason; they now
#: declare catalog rows, so only the truly catalog-less adapters remain.
CATALOG_EXEMPT_PROVIDER_IDS = frozenset({"yfinance", "adanos", "news_aggregator"})


def test_every_priority_id_is_a_known_provider():
    unknown = sorted(PRIORITY_PROVIDER_IDS - set(REGISTRY))
    assert not unknown, f"PRIORITY references unknown provider ids: {unknown}"


def test_provider_name_aliases_point_at_real_distinct_ids():
    for provider_id, runtime_name in PROVIDER_NAME_BY_ID.items():
        assert provider_id in REGISTRY, f"alias key {provider_id} is not a registry id"
        assert runtime_name != provider_id, "an alias must differ from its id"


def test_sec_filings_priority_ranks_the_edgar_provider():
    """The table names ``sec_edgar``; the provider registers as ``edgar_tools``.

    Unresolved, the id ranked nothing and the provider kept its chain position
    (``yfinance`` first). It must come first for its own category.
    """
    ordered = order_for_category(Category.SEC_FILINGS, ["yfinance", "edgar_tools", "fmp"])
    assert ordered == ["edgar_tools", "yfinance", "fmp"]


def test_every_priority_id_resolves_to_a_rankable_runtime_name():
    """An id without an alias must already be the runtime name, else the layer
    cannot rank that provider and the category entry silently no-ops."""
    for provider_id in sorted(PRIORITY_PROVIDER_IDS):
        resolved = provider_runtime_name(provider_id)
        assert resolved == provider_id or provider_id in PROVIDER_NAME_BY_ID


def test_priority_providers_have_catalog_rows_or_documented_exemption():
    catalog = endpoint_catalog()
    missing = {pid for pid in PRIORITY_PROVIDER_IDS if pid not in catalog}
    assert missing <= CATALOG_EXEMPT_PROVIDER_IDS, (
        f"priority providers without catalog rows and without an exemption: "
        f"{sorted(missing - CATALOG_EXEMPT_PROVIDER_IDS)}"
    )
