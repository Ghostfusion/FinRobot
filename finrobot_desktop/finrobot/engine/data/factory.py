"""Factory for building a DataLayer from runtime settings.

Lives in ``engine/data/`` because assembling the provider chain is a data-layer
concern. It sits ABOVE ``layer`` / ``cache`` (it imports them) and must never be
imported by them, so moving it here introduces no cycle. ``routes/settings.py``,
``server.py``, ``sdk.py`` and ``cli.py`` import ``build_data_layer`` from here.
"""

from __future__ import annotations

import logging
from typing import Any

from finrobot.engine.data.cache import DataCache
from finrobot.engine.data.layer import DataLayer

logger = logging.getLogger(__name__)


def build_provider_chain(settings: Any) -> list[Any]:
    """Build the single failover chain (Data Layer v3).

    Delegates to the provider registry, which instantiates every available
    provider (key present / gateway reachable / keyless) in a deterministic
    global order. The PER-REQUEST order is the category priority table
    (:mod:`finrobot.engine.data.categories`), applied by :class:`DataLayer`
    during its provider walk — see ``docs/DATA_PROVIDERS_V3_DESIGN.md`` §5.
    """
    from finrobot.engine.data.registry import build_provider_chain as _registry_chain

    return list(_registry_chain(settings))


def build_data_layer(settings: Any) -> DataLayer:
    """Assemble the full provider chain + a fresh cache into a DataLayer.

    Used by the CLI / SDK / Settings-rebuild paths. The sidecar boot path instead
    seeds a placeholder DataLayer and calls ``add_providers(build_provider_chain(
    settings))`` on it in a warmup task (see server.lifespan), keeping the ~0.5s of
    provider-module imports off the cold-start critical path.
    """
    cache = DataCache(settings.cache_db_path)
    return DataLayer(providers=build_provider_chain(settings), cache=cache)


async def shutdown_data_layer(data_layer: DataLayer | None = None) -> None:
    """Graceful teardown for a NON-server entrypoint (scripts / one-off tools / SDK
    one-shots) that built a DataLayer via ``build_data_layer``. Closes the layer plus the
    process-level quote-batch and SEC-holdings singletons, so the aiosqlite worker threads
    join and WAL checkpoints — instead of leaking the threads and racing the loop close
    into the "Event loop is closed" hang (observed: _regen / validation scripts blocking
    minutes at exit, 2026-06-24). Mirrors server.py's FastAPI-lifespan teardown for code
    paths that never run that lifespan. Safe when a singleton was never opened (the close
    helpers no-op on an unset singleton)."""
    if data_layer is not None:
        await data_layer.close()
    # Lazy imports keep the cold-import path light and avoid a cycle (both modules sit
    # below factory). Mirror server.py teardown ordering.
    from finrobot.engine.data.quote_batch import close_quote_cache_singleton
    from finrobot.engine.data.sec_holdings_cache import close_singleton as close_sec_holdings

    await close_quote_cache_singleton()
    await close_sec_holdings()
