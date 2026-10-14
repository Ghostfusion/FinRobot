"""FastAPI routes for the artifact store.

Endpoints:
  GET    /api/artifacts                        — list/filter all artifacts
  GET    /api/artifacts/{id}                   — fetch full artifact
  GET    /api/artifacts/{id}/audit-badge       — re-read it under today's clauses
  DELETE /api/artifacts/{id}                   — remove artifact
  GET    /api/artifacts/{a_id}/diff/{b_id}     — field-level diff
  POST   /api/artifacts/{id}/view              — update last_viewed_at
  GET    /api/artifacts/by-ticker/{ticker}/timeline — timeline for a ticker
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from starlette.requests import Request

from finrobot.artifact.audit_badge import AuditBadge, derive_audit_badge
from finrobot.artifact.semantic_diff import SemanticDelta, build_semantic_delta
from finrobot.artifact.models import Artifact, ArtifactSummary, ArtifactType
from finrobot.artifact.store import ArtifactStore
from finrobot.engine.data.layer import DataLayer
from finrobot.routes._artifact_signal import attach_signals

router = APIRouter(prefix="/api/artifacts", tags=["artifacts"])


def _store(request: Request) -> ArtifactStore:
    """Extract ArtifactStore from app state; raise 503 if not configured."""
    store: ArtifactStore | None = getattr(request.app.state, "artifact_store", None)
    if store is None:
        raise HTTPException(status_code=503, detail="Artifact store not initialised")
    return store


async def _load_artifact_or_raise(store: ArtifactStore, artifact_id: str) -> Artifact:
    """Load a full artifact, mapping the two distinct miss cases honestly.

    ``store.get() is None`` covers two different realities: the id was never
    stored (a plain 404), or the row EXISTS but its payload no longer
    deserialises after schema drift — previously an indistinguishable 404 on a
    report the list had just shown, with no cleanup path (the ghost-row bug).
    The store self-archives unreadable rows on detection, so the list stops
    showing them; this helper completes the contract by answering the click
    that found the ghost with a 410 + explanation instead of a lying 404.
    """
    artifact = await store.get(artifact_id)
    if artifact is not None:
        return artifact
    if await store.exists(artifact_id):
        raise HTTPException(
            status_code=410,
            detail=(
                f"研报 {artifact_id} 由旧版本格式存储，当前版本无法读取，已自动归档并从列表隐藏。"
                "如不再需要，可直接删除该条目。"
            ),
        )
    raise HTTPException(status_code=404, detail=f"Artifact not found: {artifact_id}")


def _data_layer(request: Request) -> DataLayer | None:
    """Best-effort DataLayer for lazy signal compute; None when unavailable."""
    deps = getattr(request.app.state, "deps", None)
    return getattr(deps, "data_layer", None) if deps is not None else None


@router.get("", response_model=list[ArtifactSummary])
async def list_artifacts(
    request: Request,
    ticker: str | None = None,
    type: ArtifactType | None = None,
    archived: bool = False,
    limit: int = Query(100, ge=1, le=500),
) -> list[ArtifactSummary]:
    """List artifact summaries, optionally filtered by ticker and/or type.

    Args:
        ticker: Filter by ticker symbol (case-insensitive). Omit for all tickers.
        type: Filter by analysis type (e.g. "dcf", "lbo"). Omit for all types.
        archived: Include archived (stale) artifacts. Default False.
        limit: Maximum results to return. Default 100.

    Returns:
        List of ArtifactSummary sorted by created_at descending.
    """
    store = _store(request)
    summaries = await store.list_by_ticker(
        ticker=ticker.upper() if ticker else None,
        type=type,
        include_archived=archived,
        limit=limit,
    )
    data_layer = _data_layer(request)
    if data_layer is not None:
        summaries = await attach_signals(summaries, data_layer)
    return summaries


@router.get("/by-ticker/{ticker}/timeline", response_model=list[ArtifactSummary])
async def ticker_timeline(
    ticker: str,
    request: Request,
    limit: int = Query(50, ge=1, le=1000),
    include_signals: bool = Query(True),
) -> list[ArtifactSummary]:
    """Return all artifacts for a ticker, newest first.

    This endpoint exists as a convenience alias for
    ``GET /api/artifacts?ticker=AAPL&include_archived=true``.
    It shows the full history including archived entries so users can
    compare across time.

    Args:
        ticker: The ticker symbol (e.g. "AAPL").
        limit: Maximum results to return. Default 50.
        include_signals: When True (default) each summary's ``signal``
            (hit/watching/failed) is computed against a LIVE quote per ticker
            — a synchronous ``fetch_canonical(PRICE)`` that bolts market-data
            latency onto what is otherwise a local-DB read. Surfaces that don't
            render the lamp (the workspace report-history preview) pass False to
            return the local history instantly; surfaces that do (the report
            detail page's version rail) keep the default.

    Returns:
        List of ArtifactSummary (all types) for the ticker, newest first.
    """
    store = _store(request)
    summaries = await store.list_by_ticker(
        ticker=ticker.upper(),
        include_archived=True,
        limit=limit,
    )
    if include_signals:
        data_layer = _data_layer(request)
        if data_layer is not None:
            summaries = await attach_signals(summaries, data_layer)
    return summaries


@router.get("/{artifact_id}", response_model=Artifact)
async def get_artifact(artifact_id: str, request: Request) -> Artifact:
    """Return the full Artifact including inputs, assumptions, outputs, and meta.

    Args:
        artifact_id: The artifact id (e.g. "art_2026-05-13T14:32:18_AAPL_dcf").

    Returns:
        The full Artifact.

    Raises:
        404: If the artifact was never stored.
        410: If the row exists but its payload is unreadable (schema drift) —
            the store archives it on detection so it leaves default lists.
    """
    store = _store(request)
    return await _load_artifact_or_raise(store, artifact_id)


@router.get("/{artifact_id}/audit-badge", response_model=AuditBadge)
async def get_audit_badge(artifact_id: str, request: Request) -> AuditBadge:
    """Re-read the STORED payload under today's output-contract clauses (design §9.3).

    The persist gate judges an artifact once, on the way in; this is the other
    reading — what today's registry makes of a payload already in the store — so the
    reader can see a defect a rule armed *after* the report was written. It is
    deliberately its own endpoint rather than a field on ``GET /{artifact_id}``: the
    record's bytes stay exactly as stored (nothing derived can be round-tripped back
    into the archive by a writer that re-posts what it fetched), and the response is
    small enough to fetch beside the report.

    The payload returned carries BOTH readings — ``would_withhold`` /
    ``would_annotate`` from the re-read, and the record's own ``shipped_*`` state — so
    a surface can never show one without the other to qualify it.

    Args:
        artifact_id: The artifact id, exactly as ``GET /{artifact_id}`` takes it.

    Returns:
        The badge: the clauses that would fire today, plus the shipped state.

    Raises:
        404: If the artifact was never stored.
        410: If the row exists but its payload is unreadable (schema drift).
    """
    store = _store(request)
    artifact = await _load_artifact_or_raise(store, artifact_id)
    return derive_audit_badge(artifact)


@router.delete("/{artifact_id}")
async def delete_artifact(artifact_id: str, request: Request) -> dict[str, str]:
    """Permanently delete an artifact and remove it from the index.

    Args:
        artifact_id: The artifact id to delete.

    Returns:
        ``{"status": "deleted", "id": artifact_id}``

    Raises:
        404: If the artifact is not found.
    """
    store = _store(request)
    deleted = await store.delete(artifact_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Artifact not found: {artifact_id}")
    # The canonical artifact is gone — drop the run_artifacts link rows in
    # runs.db too, or GET /api/runs/{run_id} keeps listing a ghost whose
    # open-report path 404s forever. Absent run_store (router mounted bare in
    # tests) just means there are no links to clean.
    run_store = getattr(request.app.state, "run_store", None)
    if run_store is not None:
        await run_store.remove_artifact_links(artifact_id)
    # Removing an artifact changes the landing hit-rate buckets and may drop a
    # ticker card off the recent-research strip — bust the dashboard TTL caches
    # so it reflects the deletion immediately (BUG-20260602-030). Local import
    # keeps the routes.dashboard ← routes.artifacts edge lazy/one-directional.
    from finrobot.routes.dashboard import invalidate_dashboard_caches

    invalidate_dashboard_caches()
    return {"status": "deleted", "id": artifact_id}


@router.get("/{a_id}/diff/{b_id}", response_model=SemanticDelta)
async def diff_two(a_id: str, b_id: str, request: Request) -> SemanticDelta:
    """Return an analyst-grade semantic delta between two artifact versions.

    ``a_id`` is the older/base version, ``b_id`` the newer/compare version. The
    response answers "why did the conclusion change" — rating / target / fair
    value moves, deterministic single-factor attribution of the DCF fair-value
    change, the driver assumptions that moved, and a comparability gate that
    suppresses deltas (or disables attribution) when the two versions aren't
    like-for-like (different formula / data source / earnings season). All
    numbers arrive pre-formatted with backend-owned units — see
    ``finrobot.artifact.semantic_diff`` and ``field_registry``.

    Args:
        a_id: The "before" (base) artifact id.
        b_id: The "after" (compare) artifact id.

    Returns:
        A SemanticDelta.

    Raises:
        404: If either artifact was never stored.
        410: If either row exists but is unreadable (schema drift).
    """
    store = _store(request)
    a = await _load_artifact_or_raise(store, a_id)
    b = await _load_artifact_or_raise(store, b_id)
    return build_semantic_delta(a, b)


@router.post("/{artifact_id}/view")
async def mark_viewed(artifact_id: str, request: Request) -> dict[str, str]:
    """Record that this artifact was viewed now.

    Updating the last_viewed_at timestamp prevents the artifact from being
    automatically archived by the stale-archive background task.

    Args:
        artifact_id: The artifact id to mark as viewed.

    Returns:
        ``{"status": "ok", "id": artifact_id}``

    Raises:
        404: If the artifact was never stored.
        410: If the row exists but is unreadable (schema drift) — returning
            before ``mark_viewed`` also keeps the un-archive side effect from
            resurrecting a self-archived ghost into the default lists.
    """
    store = _store(request)
    artifact = await _load_artifact_or_raise(store, artifact_id)
    was_archived = artifact.meta.archived
    await store.mark_viewed(artifact_id)
    # mark_viewed un-archives the artifact (store sets archived=False). When it
    # was archived, viewing it brings it back into the dashboard's
    # include_archived=False window, so the landing caches must drop or the
    # resurrected report stays invisible for up to 60s (BUG-20260602-030). We
    # gate on was_archived: the desktop shell fires /view on every report open,
    # and busting the cache on already-active artifacts would defeat it for no
    # behavioural change (the strip sorts by created_at, not last_viewed_at).
    if was_archived:
        from finrobot.routes.dashboard import invalidate_dashboard_caches

        invalidate_dashboard_caches()
    return {"status": "ok", "id": artifact_id}
