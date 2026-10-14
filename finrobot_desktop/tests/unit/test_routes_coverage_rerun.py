"""POST /api/coverage/groups/{id}/rerun + GET /api/coverage/batches/{id}.

The route builds the batch from the live provider chain's health-available
names, then runs it in the background. ``spawn_run`` is faked to create and
immediately complete a run in a real RunStore, so the background queue drains
deterministically inside the test.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from finrobot.artifact.models import ArtifactSummary
from finrobot.coverage.sqlite_store import CoverageStore
from finrobot.engine.data.interface import DataResult
from finrobot.engine.data.normalize.financials import normalize_financials
from finrobot.engine.data.normalize.price import normalize_price
from finrobot.engine.data.types import DataType
from finrobot.routes.coverage import _OVERVIEW_CACHE, router
from finrobot.run_store import RunStore

UTC = timezone.utc
NOW = datetime(2026, 5, 1, tzinfo=UTC)
ENTRY = NOW - timedelta(days=30)


def _summary(ticker: str, verdict: str | None) -> ArtifactSummary:
    return ArtifactSummary(
        id=f"art_{ticker}",
        ticker=ticker,
        cross_tickers=[],
        type="equity_research",
        created_at=ENTRY,
        headline="x",
        source="pipeline:equity_research",
        archived=False,
        entry_price=180.0,
        target_price=240.0,
        target_date=ENTRY + timedelta(days=365),
        signal=None,
        verdict=verdict,
    )


def _fin(ticker: str):
    return normalize_financials(
        DataResult(
            data=dict(
                revenue=100e9,
                ebitda=35e9,
                net_income=20e9,
                gross_margin=0.47,
                operating_margin=0.28,
                pe_ratio=28.5,
                market_cap=3e12,
                shares_outstanding=15e9,
                current_price=200.0,
                total_debt=50e9,
                total_cash=20e9,
            ),
            provider="yfinance",
            ticker=ticker,
            data_type="financials",
            timestamp=NOW,
        )
    )


def _price(ticker: str):
    return normalize_price(
        DataResult(
            data={
                "current_price": 200.0,
                "price_history": [
                    {"date": "2025-06-01", "close": 180.0},
                    {"date": "2026-03-01", "close": 200.0},
                ],
            },
            provider="yfinance",
            ticker=ticker,
            data_type="price",
            timestamp=NOW,
        )
    )


class _StubArtifactStore:
    def __init__(self, by_ticker: dict[str, list[ArtifactSummary]]) -> None:
        self._by_ticker = {k.upper(): v for k, v in by_ticker.items()}

    async def list_by_ticker(self, ticker=None, type=None, include_archived=False, limit=100):  # noqa: A002
        if ticker is None:
            flat = [s for lst in self._by_ticker.values() for s in lst]
        else:
            flat = list(self._by_ticker.get(ticker.upper(), []))
        flat.sort(key=lambda s: s.created_at, reverse=True)
        return flat[:limit]

    async def get(self, artifact_id: str):
        return None


class _StubDataLayer:
    def __init__(self, providers: list[tuple[str, bool, Any]] | None = None) -> None:
        self._providers = providers if providers is not None else []

    def provider_status(self) -> list[tuple[str, bool, Any]]:
        return self._providers

    async def fetch_canonical(self, data_type, ticker, **_):
        return _price(ticker) if data_type == DataType.PRICE else _fin(ticker)

    async def read_canonical_cached(self, data_type, ticker, **_):
        norm = _price(ticker) if data_type == DataType.PRICE else _fin(ticker)
        return norm, False


class _DenyLimiter:
    def allow_runs(self, count: int = 1) -> bool:
        return False


def _make_app(tmp_path: Path) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.state.coverage_store = CoverageStore(db_path=tmp_path / "coverage.db")
    app.state.run_store = RunStore(db_path=tmp_path / "runs.db")
    app.state.run_tasks = {}
    app.state.coverage_batches = {}
    app.state.artifact_store = _StubArtifactStore(
        {"AAPL": [_summary("AAPL", "BUY")], "MSFT": [_summary("MSFT", "HOLD")]}
    )
    # moomoo (4) and edgar_tools (10) declare limits; yfinance none. Only the
    # health-available names reach the resolver.
    app.state.deps = SimpleNamespace(
        data_layer=_StubDataLayer(
            [
                ("moomoo", True, None),
                ("yfinance", True, None),
                ("edgar_tools", True, None),
                ("eodhd", False, None),
            ]
        )
    )
    return app


@pytest.fixture
async def client(tmp_path: Path):
    _OVERVIEW_CACHE.clear()
    app = _make_app(tmp_path)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac._app = app  # type: ignore[attr-defined]
        yield ac
    _OVERVIEW_CACHE.clear()
    await app.state.coverage_store.close()
    await app.state.run_store.close()


async def _seed_studied_group(client: AsyncClient, *tickers: str) -> str:
    first, *rest = tickers or ("AAPL",)
    body = (
        await client.post("/api/coverage/studied-tickers/members", json={"ticker": first})
    ).json()
    gid: str = body["id"]
    if rest:
        store: CoverageStore = client._app.state.coverage_store  # type: ignore[attr-defined]
        await store.add_members(gid, list(rest))
    return gid


async def _wait_until(predicate, timeout: float = 5.0) -> None:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while not predicate():
        assert loop.time() < deadline, "condition not met before timeout"
        await asyncio.sleep(0)


async def _drain(client: AsyncClient) -> None:
    """Wait until every live batch has finished, so teardown never races a task."""
    app = client._app  # type: ignore[attr-defined]
    await _wait_until(
        lambda: all(b.progress().state == "completed" for b in app.state.coverage_batches.values())
    )


@pytest.fixture
def fake_spawn(monkeypatch):
    """Replace spawn_run with one that creates + completes a real run record."""

    async def _fake(request, pipeline_type, ticker, **kw):
        record = await request.app.state.run_store.create_run(pipeline_type, ticker)
        await request.app.state.run_store.update_run(record.run_id, status="completed")
        return record

    monkeypatch.setattr("finrobot.routes.runs.spawn_run", _fake)
    return _fake


async def test_rerun_builds_batch_from_live_provider_chain(client: AsyncClient, fake_spawn) -> None:
    gid = await _seed_studied_group(client, "AAPL", "MSFT")

    r = await client.post(f"/api/coverage/groups/{gid}/rerun", json={})
    assert r.status_code == 200
    body = r.json()
    assert body["batch_id"].startswith("cb_")
    assert body["group_id"] == gid
    assert body["pipeline_type"] == "research"
    assert body["total"] == 2
    # moomoo's declared 4 ties the ceiling → it binds; edgar_tools (10) is
    # declared but not binding; yfinance is undeclared. eodhd is unhealthy → skipped.
    assert body["limit"] == 4
    assert body["ceiling"] == 4
    assert body["binding_provider"] == "moomoo"
    assert (
        body["binding_reason"]
        == "moomoo OpenAPI gateway: 4 concurrent connections (owner-declared)"
    )
    assert {v["provider"] for v in body["providers"]} == {"moomoo", "edgar_tools"}
    assert body["undeclared_count"] == 1

    bid = body["batch_id"]
    await _wait_until(
        lambda: client._app.state.coverage_batches[bid].progress().state == "completed"  # type: ignore[attr-defined]
    )
    prog = (await client.get(f"/api/coverage/batches/{bid}")).json()
    assert prog["state"] == "completed"
    assert prog["completed"] == 2
    assert prog["failed"] == 0
    assert {item["ticker"] for item in prog["items"]} == {"AAPL", "MSFT"}
    assert all(item["run_id"] for item in prog["items"])


async def test_rerun_unknown_group_404(client: AsyncClient) -> None:
    r = await client.post("/api/coverage/groups/cov_nope/rerun", json={})
    assert r.status_code == 404


async def test_rerun_429_when_rate_limited(client: AsyncClient) -> None:
    gid = await _seed_studied_group(client, "AAPL")
    client._app.state.run_rate_limiter = _DenyLimiter()  # type: ignore[attr-defined]
    r = await client.post(f"/api/coverage/groups/{gid}/rerun", json={})
    assert r.status_code == 429


async def test_rerun_503_when_engine_not_ready(client: AsyncClient) -> None:
    gid = await _seed_studied_group(client, "AAPL")
    client._app.state.engine_ready = False  # type: ignore[attr-defined]
    r = await client.post(f"/api/coverage/groups/{gid}/rerun", json={})
    assert r.status_code == 503


async def test_rerun_503_when_data_layer_absent(client: AsyncClient) -> None:
    gid = await _seed_studied_group(client, "AAPL")
    client._app.state.deps = SimpleNamespace(data_layer=None)  # type: ignore[attr-defined]
    r = await client.post(f"/api/coverage/groups/{gid}/rerun", json={})
    assert r.status_code == 503


async def test_rerun_503_when_run_store_absent(client: AsyncClient) -> None:
    gid = await _seed_studied_group(client, "AAPL")
    app = client._app  # type: ignore[attr-defined]
    run_store = app.state.run_store
    del app.state.run_store
    try:
        r = await client.post(f"/api/coverage/groups/{gid}/rerun", json={})
        assert r.status_code == 503
    finally:
        app.state.run_store = run_store


async def test_rerun_empty_selection_is_200_total_zero(client: AsyncClient, fake_spawn) -> None:
    gid = await _seed_studied_group(client, "AAPL", "MSFT")
    # Both names are BUY/HOLD → filtering to SELL selects nothing.
    r = await client.post(f"/api/coverage/groups/{gid}/rerun", json={"ratings": ["SELL"]})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 0
    assert body["items"] == []
    await _drain(client)


async def test_rerun_rating_filter_selects_matching_rows(client: AsyncClient, fake_spawn) -> None:
    gid = await _seed_studied_group(client, "AAPL", "MSFT")
    r = await client.post(f"/api/coverage/groups/{gid}/rerun", json={"ratings": ["BUY"]})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert [item["ticker"] for item in body["items"]] == ["AAPL"]
    await _drain(client)


async def test_rerun_owned_filter_selects_owned_rows(client: AsyncClient, fake_spawn) -> None:
    gid = await _seed_studied_group(client, "AAPL", "MSFT")
    await client.put("/api/coverage/owned/MSFT", json={"owned": True})

    r = await client.post(f"/api/coverage/groups/{gid}/rerun", json={"owned": True})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert [item["ticker"] for item in body["items"]] == ["MSFT"]
    await _drain(client)


async def test_rerun_ticker_set_runs_only_the_selected_cards(
    client: AsyncClient, fake_spawn
) -> None:
    gid = await _seed_studied_group(client, "AAPL", "MSFT", "TSLA")
    r = await client.post(f"/api/coverage/groups/{gid}/rerun", json={"tickers": ["AAPL", "TSLA"]})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 2
    assert {item["ticker"] for item in body["items"]} == {"AAPL", "TSLA"}
    await _drain(client)


async def test_rerun_empty_ticker_set_is_total_zero_not_the_whole_group(
    client: AsyncClient, fake_spawn
) -> None:
    """A cleared selection must never degrade into "re-run everything"."""
    gid = await _seed_studied_group(client, "AAPL", "MSFT")
    r = await client.post(f"/api/coverage/groups/{gid}/rerun", json={"tickers": []})
    assert r.status_code == 200
    assert r.json()["total"] == 0
    await _drain(client)


async def test_rerun_ticker_set_drops_non_members(client: AsyncClient, fake_spawn) -> None:
    gid = await _seed_studied_group(client, "AAPL")
    r = await client.post(f"/api/coverage/groups/{gid}/rerun", json={"tickers": ["AAPL", "ZZZZ"]})
    assert r.status_code == 200
    assert [item["ticker"] for item in r.json()["items"]] == ["AAPL"]
    await _drain(client)


async def test_get_unknown_batch_404(client: AsyncClient) -> None:
    assert (await client.get("/api/coverage/batches/cb_nope")).status_code == 404


async def test_batches_pruned_to_newest_20(client: AsyncClient, fake_spawn) -> None:
    gid = await _seed_studied_group(client, "AAPL")
    ids: list[str] = []
    for _ in range(22):
        r = await client.post(f"/api/coverage/groups/{gid}/rerun", json={})
        assert r.status_code == 200
        ids.append(r.json()["batch_id"])
    batches = client._app.state.coverage_batches  # type: ignore[attr-defined]
    assert len(batches) == 20
    # The two oldest were dropped; the newest is present.
    assert ids[0] not in batches and ids[1] not in batches
    assert ids[-1] in batches
    await _drain(client)
