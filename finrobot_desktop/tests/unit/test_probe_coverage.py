"""Probe coverage for the providers that used to declare no endpoint catalog.

``probe_all`` iterates ``endpoint_catalog()`` keys, which are built from each
provider module's module-level ``ENDPOINTS``; a provider without one is
invisible to the probe even when ``categories.PRIORITY`` routes to it. That was
true of ``fmp`` (first choice for ``core_stock_apis``/``fundamental_data``),
``finnhub`` and ``sec_edgar`` (the only provider for ``sec_filings``).

The credential never reaches a ``ProbeResult``: it is substituted into request
params/headers only, so these tests assert its presence on the wire and its
absence from the emitted record — using a sentinel that must never be rendered
into a failure message.
"""

from __future__ import annotations

import dataclasses

import httpx
import pytest

from finrobot.config import FinRobotSettings
from finrobot.engine.data.catalog import endpoint_catalog
from finrobot.probe import _render, probe_all, probe_provider

#: Providers that previously declared no catalog rows; all three are routed by
#: ``categories.PRIORITY``.
_NEWLY_PROBED = ("fmp", "finnhub", "sec_edgar")

_SENTINEL = "SENTINEL-CREDENTIAL-DO-NOT-LEAK"


def _settings() -> FinRobotSettings:
    return FinRobotSettings(
        fmp_api_key=_SENTINEL, finnhub_api_key=_SENTINEL, sec_user_agent=_SENTINEL
    )


def _mock_transport(monkeypatch: pytest.MonkeyPatch) -> list[httpx.Request]:
    """Replace the probe's HTTP client with one that records and answers 200."""
    seen: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={})

    def _client() -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=httpx.MockTransport(handler))

    monkeypatch.setattr("finrobot.probe._make_client", _client)
    return seen


def test_catalog_includes_fmp_finnhub_and_sec_edgar() -> None:
    catalog = endpoint_catalog()

    for provider_id in _NEWLY_PROBED:
        assert provider_id in catalog, provider_id
        assert catalog[provider_id], provider_id


def test_every_new_row_renders_a_non_empty_url() -> None:
    catalog = endpoint_catalog()

    for provider_id in _NEWLY_PROBED:
        for spec in catalog[provider_id].values():
            url, _params, _headers = _render(spec, "k", "AAPL")
            assert url
            assert "$KEY" not in url
            assert "{" not in url


def test_render_puts_the_credential_in_params_or_headers_only() -> None:
    catalog = endpoint_catalog()

    for provider_id in _NEWLY_PROBED:
        for spec in catalog[provider_id].values():
            url, params, headers = _render(spec, _SENTINEL, "AAPL")
            carried = _SENTINEL in params.values() or _SENTINEL in headers.values()
            assert carried, provider_id
            assert _SENTINEL not in url, provider_id
            assert spec.auth_header is None or _SENTINEL in headers.values(), provider_id


async def test_identity_provider_probes_with_its_user_agent_not_a_data_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``sec_edgar`` is kind ``identity``: its credential is the SEC identity,
    which ``settings.data_key()`` does not map — the keyed path must resolve it
    from ``sec_user_agent`` or SEC reports a false "no_key"."""
    seen = _mock_transport(monkeypatch)

    results = await probe_provider("sec_edgar", _settings())

    assert [r.code for r in results] == ["ok"]
    assert seen and seen[0].headers["User-Agent"] == _SENTINEL


async def test_probe_record_never_carries_the_credential(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen = _mock_transport(monkeypatch)

    results = await probe_all(_settings(), providers=list(_NEWLY_PROBED))

    assert results
    assert all(r.ok for r in results)
    on_the_wire = any(_SENTINEL in str(r.url) for r in seen) or any(
        _SENTINEL in value for r in seen for value in r.headers.values()
    )
    assert on_the_wire
    leaked = [r for r in results if any(_SENTINEL in str(v) for v in dataclasses.astuple(r))]
    assert not leaked, "a ProbeResult carried the credential"
