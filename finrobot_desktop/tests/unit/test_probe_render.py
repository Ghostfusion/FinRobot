"""Probe placeholder rendering — a catalog row must never abort the whole run.

``federal_reserve``'s Treasury CSV row ships ``{year}`` in both the path and a
param; rendering it with ``str.format(ticker=…)`` raised ``KeyError`` and killed
``python -m finrobot.probe`` before any provider was reported.
"""

from __future__ import annotations

from datetime import datetime

from finrobot.engine.data.catalog import EndpointSpec
from finrobot.engine.data.categories import Category
from finrobot.probe import _make_client, _render


def test_render_substitutes_year_in_path_and_params() -> None:
    ep = EndpointSpec(
        capability=Category.RISK_FREE_CURVE,
        method="GET",
        url="https://example.test/{year}/all",
        params={"field_tdr_date_value": "{year}", "type": "daily_treasury_yield_curve"},
    )

    url, params, _headers = _render(ep, None, "AAPL")

    year = str(datetime.now().year)
    assert url == f"https://example.test/{year}/all"
    assert params["field_tdr_date_value"] == year
    # Non-placeholder params are passed through untouched.
    assert params["type"] == "daily_treasury_yield_curve"


def test_render_leaves_unfillable_placeholder_verbatim() -> None:
    """moomoo's rows are SDK-shaped, not HTTP: the probe must classify them
    rather than crash on a placeholder it cannot resolve."""
    ep = EndpointSpec(
        capability=Category.CORE_STOCK_APIS, method="GET", url="moomoo://{sdk_method}"
    )

    url, _params, _headers = _render(ep, "secret", "AAPL")

    assert url == "moomoo://{sdk_method}"


def test_probe_client_follows_redirects() -> None:
    """The adapters follow redirects (the cboe adapter documents cdn.cboe.com's
    302 to cdn-api.cboe.com). A probe that does not would report a false failure
    for an endpoint production consumes happily — a probe disagreeing with
    production is worse than no probe."""
    client = _make_client()
    assert client.follow_redirects is True


def test_probe_timeout_is_not_shorter_than_any_adapter() -> None:
    """The probe must not give up sooner than the adapters do.

    It used a fixed 15s while the Treasury CSV needs ~17s, so federal_reserve was
    reported as a failure by the probe *and* could never fetch in production.
    Comparing against the adapters' own ``_TIMEOUT`` keeps the two in step as
    providers are added.
    """
    import importlib

    from finrobot.engine.data.registry import REGISTRY

    worst = max(
        float(getattr(importlib.import_module(spec.module), "_TIMEOUT", 0.0))
        for spec in REGISTRY.values()
    )

    client = _make_client()
    assert client.timeout.read is not None
    assert client.timeout.read >= worst, f"probe timeout {client.timeout.read} < adapter {worst}"


def test_render_substitutes_ticker_and_key() -> None:
    ep = EndpointSpec(
        capability=Category.CORE_STOCK_APIS,
        method="GET",
        url="https://example.test/{ticker}",
        params={"api_token": "$KEY"},
        auth_header="Authorization",
        auth_value="Token $KEY",
    )

    url, params, headers = _render(ep, "k-123", "MSFT")

    assert url == "https://example.test/MSFT"
    assert params["api_token"] == "k-123"
    assert headers["Authorization"] == "Token k-123"
