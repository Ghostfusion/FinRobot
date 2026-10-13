"""PUT /api/coverage/owned/{ticker} — the card's owned checkbox.

Ownership is per-ticker and GLOBAL, so the write must clear the WHOLE overview
cache (not just one group's key), and the overview must surface the flag.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

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


def _summary(ticker: str) -> ArtifactSummary:
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
        verdict="BUY",
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
    async def fetch_canonical(self, data_type, ticker, **_):
        return _price(ticker) if data_type == DataType.PRICE else _fin(ticker)

    async def read_canonical_cached(self, data_type, ticker, **_):
        norm = _price(ticker) if data_type == DataType.PRICE else _fin(ticker)
        return norm, False


@pytest.fixture
async def client(tmp_path: Path):
    _OVERVIEW_CACHE.clear()
    app = FastAPI()
    app.include_router(router)
    store = CoverageStore(db_path=tmp_path / "coverage.db")
    run_store = RunStore(db_path=tmp_path / "runs.db")
    app.state.coverage_store = store
    app.state.run_store = run_store
    app.state.run_tasks = {}
    app.state.coverage_batches = {}
    app.state.artifact_store = _StubArtifactStore({"AAPL": [_summary("AAPL")]})
    app.state.deps = SimpleNamespace(data_layer=_StubDataLayer())
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac._app = app  # type: ignore[attr-defined]
        yield ac
    _OVERVIEW_CACHE.clear()
    await store.close()
    await run_store.close()


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


async def test_set_owned_true_and_false(client: AsyncClient) -> None:
    r = await client.put("/api/coverage/owned/nflx", json={"owned": True})
    assert r.status_code == 200
    assert r.json() == {"ticker": "NFLX", "owned": True}

    store: CoverageStore = client._app.state.coverage_store  # type: ignore[attr-defined]
    assert await store.owned_tickers() == {"NFLX"}

    r = await client.put("/api/coverage/owned/NFLX", json={"owned": False})
    assert r.status_code == 200
    assert r.json() == {"ticker": "NFLX", "owned": False}
    assert await store.owned_tickers() == set()


async def test_set_owned_invalid_ticker_422(client: AsyncClient) -> None:
    r = await client.put("/api/coverage/owned/苹果", json={"owned": True})
    assert r.status_code == 422


async def test_set_owned_clears_the_whole_overview_cache(client: AsyncClient) -> None:
    # Seed both cache phases for two different groups.
    sentinel = object()
    _OVERVIEW_CACHE[("cov_a", True)] = (0.0, sentinel)  # type: ignore[assignment]
    _OVERVIEW_CACHE[("cov_b", False)] = (0.0, sentinel)  # type: ignore[assignment]
    r = await client.put("/api/coverage/owned/AAPL", json={"owned": True})
    assert r.status_code == 200
    assert _OVERVIEW_CACHE == {}


async def test_overview_reports_owned_flag(client: AsyncClient) -> None:
    gid = await _seed_studied_group(client, "AAPL", "MSFT")

    body = (await client.get(f"/api/coverage/groups/{gid}/overview")).json()
    by_ticker = {row["ticker"]: row for row in body["rows"]}
    assert by_ticker["AAPL"]["owned"] is False
    assert by_ticker["MSFT"]["owned"] is False

    await client.put("/api/coverage/owned/aapl", json={"owned": True})

    body = (await client.get(f"/api/coverage/groups/{gid}/overview")).json()
    by_ticker = {row["ticker"]: row for row in body["rows"]}
    assert by_ticker["AAPL"]["owned"] is True
    assert by_ticker["MSFT"]["owned"] is False
