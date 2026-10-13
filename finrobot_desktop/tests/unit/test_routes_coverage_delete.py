"""DELETE /api/coverage/groups/{group_id}/members/{ticker} — the card's "X".

Deleting a card is a desk-level removal: the ticker leaves the group AND its
stored reports (archived rows included) are purged, so the wall never shows a
card whose reports no longer exist. The removal is idempotent for a non-member
ticker (the artifacts still go, ``removed_from_group: false``) and the ticker's
global ``owned`` flag survives — ownership is a portfolio fact, not membership.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from finrobot.artifact.models import ArtifactSummary
from finrobot.coverage.sqlite_store import CoverageStore
from finrobot.routes.coverage import _OVERVIEW_CACHE, router

UTC = timezone.utc
NOW = datetime(2026, 5, 1, tzinfo=UTC)
ENTRY = NOW - timedelta(days=30)


def _summary(ticker: str, n: int = 1) -> ArtifactSummary:
    return ArtifactSummary(
        id=f"art_{ticker}_{n}",
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


class _StubArtifactStore:
    """Just enough store for the route: ``delete_by_ticker`` + a peek."""

    def __init__(self, by_ticker: dict[str, list[ArtifactSummary]]) -> None:
        self._by_ticker = {k.upper(): list(v) for k, v in by_ticker.items()}

    async def delete_by_ticker(self, ticker: str) -> list[str]:
        return [s.id for s in self._by_ticker.pop(ticker.upper(), [])]

    def has(self, ticker: str) -> bool:
        return ticker.upper() in self._by_ticker


class _RecordingRunStore:
    """Records the per-artifact link cleanup the route fans out."""

    def __init__(self) -> None:
        self.unlinked: list[str] = []

    async def remove_artifact_links(self, artifact_id: str) -> int:
        self.unlinked.append(artifact_id)
        return 1


@pytest.fixture
async def client(tmp_path: Path):
    _OVERVIEW_CACHE.clear()
    app = FastAPI()
    app.include_router(router)
    store = CoverageStore(db_path=tmp_path / "coverage.db")
    app.state.coverage_store = store
    app.state.run_store = _RecordingRunStore()
    app.state.artifact_store = _StubArtifactStore(
        {
            "AAPL": [_summary("AAPL", 1), _summary("AAPL", 2)],
            "MSFT": [_summary("MSFT", 1)],
        }
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac._app = app  # type: ignore[attr-defined]
        yield ac
    _OVERVIEW_CACHE.clear()
    await store.close()


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


async def test_delete_member_removes_membership_and_artifacts(client: AsyncClient) -> None:
    gid = await _seed_studied_group(client, "AAPL", "MSFT")

    r = await client.delete(f"/api/coverage/groups/{gid}/members/aapl")

    assert r.status_code == 200
    body = r.json()
    assert body["ticker"] == "AAPL"
    assert body["removed_from_group"] is True
    assert body["artifacts_deleted"] == 2
    assert set(body["artifact_ids"]) == {"art_AAPL_1", "art_AAPL_2"}

    store: CoverageStore = client._app.state.coverage_store  # type: ignore[attr-defined]
    detail = await store.get_group(gid)
    assert detail is not None
    assert [m.ticker for m in detail.members] == ["MSFT"]

    artifact_store = client._app.state.artifact_store  # type: ignore[attr-defined]
    assert artifact_store.has("AAPL") is False
    assert artifact_store.has("MSFT") is True


async def test_delete_member_drops_run_artifact_links(client: AsyncClient) -> None:
    gid = await _seed_studied_group(client, "AAPL")

    r = await client.delete(f"/api/coverage/groups/{gid}/members/AAPL")

    assert r.status_code == 200
    run_store = client._app.state.run_store  # type: ignore[attr-defined]
    assert set(run_store.unlinked) == set(r.json()["artifact_ids"])


async def test_delete_member_is_idempotent_for_non_member(client: AsyncClient) -> None:
    # MSFT is the member; AAPL's artifacts exist but AAPL was never added.
    gid = await _seed_studied_group(client, "MSFT")

    first = await client.delete(f"/api/coverage/groups/{gid}/members/AAPL")
    assert first.status_code == 200
    assert first.json()["removed_from_group"] is False
    assert first.json()["artifacts_deleted"] == 2
    artifact_store = client._app.state.artifact_store  # type: ignore[attr-defined]
    assert artifact_store.has("AAPL") is False

    # Re-firing the cleanup is a clean no-op, not a 404 halfway through.
    second = await client.delete(f"/api/coverage/groups/{gid}/members/AAPL")
    assert second.status_code == 200
    assert second.json() == {
        "ticker": "AAPL",
        "removed_from_group": False,
        "artifacts_deleted": 0,
        "artifact_ids": [],
    }

    store: CoverageStore = client._app.state.coverage_store  # type: ignore[attr-defined]
    detail = await store.get_group(gid)
    assert detail is not None
    assert [m.ticker for m in detail.members] == ["MSFT"]


async def test_delete_member_unknown_group_404(client: AsyncClient) -> None:
    r = await client.delete("/api/coverage/groups/cov_nope/members/AAPL")

    assert r.status_code == 404
    # The 404 short-circuits before any destructive work.
    artifact_store = client._app.state.artifact_store  # type: ignore[attr-defined]
    assert artifact_store.has("AAPL") is True


async def test_delete_member_invalid_ticker_422(client: AsyncClient) -> None:
    gid = await _seed_studied_group(client, "AAPL")

    r = await client.delete(f"/api/coverage/groups/{gid}/members/苹果")

    assert r.status_code == 422
    artifact_store = client._app.state.artifact_store  # type: ignore[attr-defined]
    assert artifact_store.has("AAPL") is True


async def test_delete_member_invalidates_only_this_group_overview(
    client: AsyncClient,
) -> None:
    gid = await _seed_studied_group(client, "AAPL")
    sentinel = object()
    _OVERVIEW_CACHE[(gid, True)] = (0.0, sentinel)  # type: ignore[assignment]
    _OVERVIEW_CACHE[(gid, False)] = (0.0, sentinel)  # type: ignore[assignment]
    _OVERVIEW_CACHE[("cov_other", True)] = (0.0, sentinel)  # type: ignore[assignment]

    r = await client.delete(f"/api/coverage/groups/{gid}/members/AAPL")

    assert r.status_code == 200
    # This group's L1 (both phases) is dropped; another group's key is untouched.
    assert set(_OVERVIEW_CACHE) == {("cov_other", True)}


async def test_delete_member_keeps_owned_flag(client: AsyncClient) -> None:
    gid = await _seed_studied_group(client, "AAPL")
    await client.put("/api/coverage/owned/AAPL", json={"owned": True})

    r = await client.delete(f"/api/coverage/groups/{gid}/members/AAPL")

    assert r.status_code == 200
    assert r.json()["removed_from_group"] is True

    store: CoverageStore = client._app.state.coverage_store  # type: ignore[attr-defined]
    # Ownership is a portfolio fact, not desk membership — it survives the delete
    # so re-opening the ticker (the documented auto-add) restores the checkbox.
    assert await store.owned_tickers() == {"AAPL"}
