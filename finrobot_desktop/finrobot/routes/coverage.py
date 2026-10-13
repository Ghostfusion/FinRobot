"""FastAPI routes for Coverage Desk — the user's research coverage universe.

Endpoints:
  GET    /api/coverage/groups                         — list groups (+ counts)
  POST   /api/coverage/studied-tickers/members        — auto-add opened ticker
  GET    /api/coverage/groups/{id}/overview           — Coverage Table payload
  POST   /api/coverage/groups/{id}/runs               — batch-run the group
  PUT    /api/coverage/owned/{ticker}                 — set the owned checkbox
  POST   /api/coverage/groups/{id}/rerun              — re-run all (queued)
  GET    /api/coverage/batches/{batch_id}             — re-run batch progress

Coverage Desk is a single ``Studied Tickers`` workspace — opening a ticker
enrols it, the table renders the universe, and a batch run fans the pipeline
across it. There is no multi-group management surface (no create / rename /
delete / generic member edit).

Orchestration lives in :mod:`finrobot.coverage.service` (the table) and
:mod:`finrobot.coverage.batch` (the queued re-run-all); this layer only wires
HTTP ↔ store/service/batch and owns the short-TTL overview cache (M1). The list
endpoint seeds the State-D ``Studied Tickers`` group on first visit.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator
from starlette.requests import Request

from finrobot.artifact.store import ArtifactStore
from finrobot.coverage.batch import CoverageBatch, CoverageBatchProgress, select_targets
from finrobot.coverage.models import (
    CoverageGroupDetail,
    CoverageGroupSummary,
    CoverageOverview,
)
from finrobot.coverage.service import (
    build_overview,
    ensure_studied_membership,
    ensure_system_group,
)
from finrobot.coverage.sqlite_store import CoverageStore
from finrobot.engine.data.layer import DataLayer
from finrobot.engine.data.ticker import validate_ticker
from finrobot.run_concurrency import resolve_run_concurrency

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/coverage", tags=["coverage"])


# ── Request bodies ───────────────────────────────────────────────────────────


class StudiedMemberRequest(BaseModel):
    """Auto-add one opened ticker to the default ``Studied Tickers`` workspace.

    One ticker per request: this is the write side of "opening /stocks/:ticker
    enrols it", fired once per successful open.
    """

    ticker: str

    @field_validator("ticker")
    @classmethod
    def _validate(cls, v: str) -> str:
        return validate_ticker(v)


class BatchRunRequest(BaseModel):
    # Must be a pipeline-registry key (engine/pipelines/registry.py), NOT an
    # artifact type. "research" → equity research; the artifact it produces is
    # typed "equity_research", but the run key is "research". Defaulting to
    # "equity_research" here used to make every batch run skip with
    # "Invalid pipeline" while still returning 200 (BUG-049).
    tickers: list[str] = Field(min_length=1)
    pipeline_type: str = "research"
    language: Literal["en", "zh"] | None = None


class BatchRunItem(BaseModel):
    ticker: str
    run_id: str


class BatchRunResponse(BaseModel):
    group_id: str
    pipeline_type: str
    runs: list[BatchRunItem]
    skipped: list[dict[str, str]] = Field(default_factory=list)
    """Tickers that couldn't be started (bad symbol / unknown pipeline), each
    {ticker, reason} — the rest still launch."""


class OwnedTickerRequest(BaseModel):
    """Set one ticker's global owned flag from a card's checkbox."""

    owned: bool


class OwnedTickerResponse(BaseModel):
    ticker: str
    owned: bool


class RerunRequest(BaseModel):
    """Filters + pipeline selection for the "re-run all reports" control.

    ``owned`` / ``ratings`` are the same filters the sort/filter UI offers;
    ``None`` means "no filter on this axis". ``ratings`` tokens are the verdicts
    the artifact store records (uppercase) plus ``UNRATED`` for names with no
    verdict yet.
    """

    owned: bool | None = None
    ratings: list[Literal["BUY", "HOLD", "SELL", "UNRATED"]] | None = None
    pipeline_type: str = "research"
    language: Literal["en", "zh"] | None = None


# Newest-N live batches kept on ``app.state.coverage_batches`` for progress
# reads. A user fires at most a handful per session; the cap is pure memory
# hygiene (the runs themselves persist in the run store regardless).
_MAX_BATCHES = 20


# ── Overview L1 cache (M1) ───────────────────────────────────────────────────
# The Coverage Table is the desktop's first screen — opened constantly. One
# overview = an N-ticker canonical fan-out; a short TTL absorbs refresh storms
# while staying live. Keyed by group_id; invalidated on any membership/name
# mutation so an edit is reflected immediately.
# Keyed by (group_id, cache_only) — the instant cache-only paint and the
# network-revalidated table are distinct payloads, cached independently.
_OVERVIEW_CACHE: dict[tuple[str, bool], tuple[float, CoverageOverview]] = {}
# Distinct TTLs per mode. The instant cache-only paint is cheap and reopened
# constantly → a generous 60s dedup. The network-revalidate path backs the
# manual "刷新" button, so it must feel live during market hours: a short 5s
# window still folds React's double-fire and a mashed button, while the
# provider itself is shielded by DataLayer single-flight + the calendar no-op
# (a closed-market refresh costs zero provider calls regardless of this TTL).
_OVERVIEW_TTL_CACHEONLY_S = 60.0
_OVERVIEW_TTL_REFRESH_S = 5.0


def _invalidate(group_id: str) -> None:
    # Drop both phases — a membership/name edit invalidates the cache-only paint
    # and the network table.
    _OVERVIEW_CACHE.pop((group_id, True), None)
    _OVERVIEW_CACHE.pop((group_id, False), None)


# ── Dependency accessors ─────────────────────────────────────────────────────


def _store(request: Request) -> CoverageStore:
    store: CoverageStore | None = getattr(request.app.state, "coverage_store", None)
    if store is None:
        raise HTTPException(status_code=503, detail="Coverage store not initialised")
    return store


def _artifact_store(request: Request) -> ArtifactStore | None:
    return getattr(request.app.state, "artifact_store", None)


def _data_layer(request: Request) -> DataLayer | None:
    deps = getattr(request.app.state, "deps", None)
    return getattr(deps, "data_layer", None) if deps is not None else None


# ── Groups ───────────────────────────────────────────────────────────────────


@router.get("/groups", response_model=list[CoverageGroupSummary])
async def list_groups(request: Request) -> list[CoverageGroupSummary]:
    """List coverage groups with member counts.

    On first visit (no groups yet) seeds a ``Studied Tickers`` group from the
    artifact store so an existing user lands on their real research universe
    rather than an empty desk (State D). The seed is a one-time projection;
    once any group exists this never re-fires.
    """
    store = _store(request)
    artifact_store = _artifact_store(request)
    if artifact_store is not None:
        try:
            await ensure_system_group(store, artifact_store)
        except (RuntimeError, OSError, ValueError) as exc:
            # Seeding is best-effort onboarding — never block the group list.
            logger.warning("System coverage group seeding skipped: %s", exc)
    return await store.list_groups()


# ── Studied Tickers auto-add (search → workspace) ────────────────────────────


@router.post("/studied-tickers/members", response_model=CoverageGroupDetail)
async def add_studied_member(request: Request, body: StudiedMemberRequest) -> CoverageGroupDetail:
    """Enrol a ticker into the default ``Studied Tickers`` workspace.

    Idempotent find-or-create: opening ``/stocks/:ticker`` calls this so the
    name joins the default group (Coverage redesign §2). Re-opening is a no-op;
    a name the user removed re-enters on the next open. Never the batch path —
    one ticker, already validated.
    """
    detail = await ensure_studied_membership(_store(request), body.ticker)
    # A new member changes the studied group's overview — drop its cache so the
    # desk shows the freshly-opened card on next render.
    _invalidate(detail.id)
    return detail


# ── Ownership (per-ticker, global) ───────────────────────────────────────────


@router.put("/owned/{ticker}", response_model=OwnedTickerResponse)
async def set_owned(ticker: str, request: Request, body: OwnedTickerRequest) -> OwnedTickerResponse:
    """Set one ticker's owned flag (the card's checkbox).

    Ownership is per-ticker and global — the flag shows on that name's card in
    EVERY group — so this clears the whole overview cache rather than one
    group's key. The ticker goes through the same ``validate_ticker`` the
    Studied-member body uses, so an invalid symbol returns the same 422.
    """
    store = _store(request)
    try:
        norm = validate_ticker(ticker)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    stored = await store.set_owned(norm, body.owned)
    # Owned shows on every group's rows — a per-group invalidation would leave a
    # stale checkbox on every other group's cards.
    _OVERVIEW_CACHE.clear()
    return OwnedTickerResponse(ticker=norm, owned=stored)


# ── Overview (Coverage Table) ────────────────────────────────────────────────


@router.get("/groups/{group_id}/overview", response_model=CoverageOverview)
async def group_overview(
    group_id: str, request: Request, refresh: bool = False
) -> CoverageOverview:
    """Assembled Coverage Table for a group.

    Needs the data layer + artifact store; per-ticker fetch failures degrade
    individual rows (``partial=true``) rather than failing the request.

    Two modes, both 60s L1-cached under distinct keys (stale-while-revalidate):

    * ``refresh=false`` (default) — **instant first paint**: market cells read
      from the canonical cache (allow-stale), NO network. ~ms at any N (measured
      5ms/6t, 4ms/100t). Rows past their TTL carry ``market_stale=true``; cold
      rows leave market ``None``. This is what the desk opens with — no more
      waiting on the cold provider fan-out (6.6s/6t, >180s/100t).
    * ``refresh=true`` — **network revalidate**: bounded per-ticker fan-out
      repopulates the canonical cache and returns fresh numbers. The client
      fires this in the background after the instant paint, then swaps it in.
    """
    store = _store(request)
    now_ts = time.time()
    cache_only = not refresh
    key = (group_id, cache_only)
    ttl = _OVERVIEW_TTL_CACHEONLY_S if cache_only else _OVERVIEW_TTL_REFRESH_S
    cached = _OVERVIEW_CACHE.get(key)
    if cached and now_ts - cached[0] < ttl:
        return cached[1]

    group = await store.get_group(group_id)
    if group is None:
        raise HTTPException(status_code=404, detail=f"Coverage group not found: {group_id}")

    data_layer = _data_layer(request)
    artifact_store = _artifact_store(request)
    if data_layer is None or artifact_store is None:
        raise HTTPException(status_code=503, detail="Backend deps not initialized")

    overview = await build_overview(
        group,
        artifact_store=artifact_store,
        data_layer=data_layer,
        run_store=getattr(request.app.state, "run_store", None),
        cache_only=cache_only,
        owned_tickers=await store.owned_tickers(),
    )
    _OVERVIEW_CACHE[key] = (now_ts, overview)
    # A network revalidate just rewrote the canonical cache; drop the stale
    # cache-only L1 so the next instant paint re-reads the fresh snapshot
    # rather than serving a pre-revalidate copy for up to 60s.
    if refresh:
        _OVERVIEW_CACHE.pop((group_id, True), None)
    return overview


# ── Batch runs (M4) ──────────────────────────────────────────────────────────


@router.post("/groups/{group_id}/runs", response_model=BatchRunResponse)
async def batch_run(group_id: str, request: Request, body: BatchRunRequest) -> BatchRunResponse:
    """Kick off a pipeline run for each selected ticker in the group.

    Reuses the single-run machinery (``spawn_run`` → same concurrency cap +
    SSE), so the frontend tracks aggregate progress by connecting one SSE
    stream per returned ``run_id``. A bad ticker / pipeline lands in
    ``skipped`` instead of failing the whole batch. The overview's cache is
    invalidated so an in-flight / failed run shows on next render.
    """
    from finrobot.routes.runs import spawn_run

    store = _store(request)
    if await store.get_group(group_id) is None:
        raise HTTPException(status_code=404, detail=f"Coverage group not found: {group_id}")

    # Inbound rate-limit guard (BUG-043): a batch spawns one metered pipeline
    # per ticker. Charge the WHOLE batch atomically — the bucket is sized above
    # the largest legitimate batch, so a normal coverage fan-out passes, but a
    # runaway loop firing batch after batch is throttled. Charging the batch as
    # one unit (not per spawn_run) means we never admit half a batch. Orthogonal
    # to the concurrency cap (run_semaphore, BUG-017).
    limiter = getattr(request.app.state, "run_rate_limiter", None)
    if limiter is not None and not limiter.allow_runs(len(body.tickers)):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded — too many runs started. Retry shortly.",
        )

    runs: list[BatchRunItem] = []
    skipped: list[dict[str, str]] = []
    for ticker in body.tickers:
        try:
            record = await spawn_run(request, body.pipeline_type, ticker, language=body.language)
        except ValueError as exc:
            skipped.append({"ticker": ticker.strip().upper(), "reason": str(exc)})
            continue
        runs.append(BatchRunItem(ticker=record.ticker, run_id=record.run_id))

    _invalidate(group_id)
    return BatchRunResponse(
        group_id=group_id,
        pipeline_type=body.pipeline_type,
        runs=runs,
        skipped=skipped,
    )


# ── Re-run all reports (queued) ──────────────────────────────────────────────


def _batches(request: Request) -> dict[str, CoverageBatch]:
    """The live-batch registry on ``app.state`` (lazily created if unset)."""
    batches: dict[str, CoverageBatch] | None = getattr(request.app.state, "coverage_batches", None)
    if batches is None:
        batches = {}
        request.app.state.coverage_batches = batches
    return batches


@router.post("/groups/{group_id}/rerun", response_model=CoverageBatchProgress)
async def rerun_group(group_id: str, request: Request, body: RerunRequest) -> CoverageBatchProgress:
    """Re-run reports for every selected ticker, throttled to the provider cap.

    Selection runs over the SAME rows the cards show (the instant cache-only
    overview, which already carries the global owned flags) through the shared
    :func:`select_targets` predicate, so "what you filtered" and "what re-runs"
    never disagree. The batch runs in the background at the concurrency the LIVE
    provider chain allows (see :func:`resolve_run_concurrency`); the rest wait in
    its queue. Returns the batch's initial progress (poll
    ``GET /batches/{batch_id}`` for live counts).
    """
    from finrobot.routes.runs import spawn_run

    store = _store(request)
    group = await store.get_group(group_id)
    if group is None:
        raise HTTPException(status_code=404, detail=f"Coverage group not found: {group_id}")

    # Gate on engine_ready: the provider chain is warm-loaded AFTER boot, so on a
    # cold chain ``provider_status()`` is empty and ``resolve_run_concurrency``
    # would silently fall back to the LLM ceiling instead of the real provider
    # limit (e.g. moomoo=4). Refuse until the chain is live.
    if not getattr(request.app.state, "engine_ready", True):
        raise HTTPException(
            status_code=503, detail="Backend engine is still starting — retry in a moment."
        )

    data_layer = _data_layer(request)
    artifact_store = _artifact_store(request)
    run_store = getattr(request.app.state, "run_store", None)
    if data_layer is None or artifact_store is None or run_store is None:
        raise HTTPException(status_code=503, detail="Backend deps not initialized")

    overview = await build_overview(
        group,
        artifact_store=artifact_store,
        data_layer=data_layer,
        run_store=run_store,
        cache_only=True,
        owned_tickers=await store.owned_tickers(),
    )
    selected = select_targets(overview.rows, owned=body.owned, ratings=body.ratings)

    # Inbound rate-limit guard (BUG-043), same shape as the per-ticker batch
    # route: charge the WHOLE selection atomically (one token per run) so a
    # runaway loop never admits half a batch. Orthogonal to the concurrency cap
    # the batch itself enforces.
    limiter = getattr(request.app.state, "run_rate_limiter", None)
    if limiter is not None and not limiter.allow_runs(len(selected)):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded — too many runs started. Retry shortly.",
        )

    # The effective cap comes from the LIVE provider chain (health-available
    # names) resolved against the registry's declared concurrency limits.
    provider_names = [name for name, available, _ in data_layer.provider_status() if available]
    plan = resolve_run_concurrency(provider_names)

    # These closures close over THIS request for the batch's whole lifetime —
    # exactly as the existing batch_run holds its Request across every spawned
    # run. spawn_run reads only ``request.app.state`` after creation, and
    # run_status reads ``request.app.state.run_store``, so the request stays
    # valid for the background batch (Starlette keeps app.state alive for the
    # app's lifetime).
    async def _spawn(ticker: str) -> str:
        record = await spawn_run(request, body.pipeline_type, ticker, language=body.language)
        return record.run_id

    async def _run_status(run_id: str) -> str | None:
        record = await run_store.get_run(run_id)
        return record.status if record is not None else None

    batch = CoverageBatch(
        batch_id=f"cb_{uuid.uuid4().hex[:12]}",
        group_id=group_id,
        pipeline_type=body.pipeline_type,
        tickers=selected,
        plan=plan,
        spawn=_spawn,
        run_status=_run_status,
    )
    batches = _batches(request)
    batches[batch.batch_id] = batch
    # Keep the newest N — dropping the oldest progress handle only forgets its
    # GET endpoint; the runs it started keep running in the run store.
    while len(batches) > _MAX_BATCHES:
        del batches[next(iter(batches))]

    batch.start()
    # Runs started by the batch show their status on the cards — drop this
    # group's L1 so the next render picks up queued/running state.
    _invalidate(group_id)
    return batch.progress()


@router.get("/batches/{batch_id}", response_model=CoverageBatchProgress)
async def get_batch(batch_id: str, request: Request) -> CoverageBatchProgress:
    """Live progress of a re-run-all batch (404 for an unknown id)."""
    batch = _batches(request).get(batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail=f"Batch not found: {batch_id}")
    return batch.progress()
