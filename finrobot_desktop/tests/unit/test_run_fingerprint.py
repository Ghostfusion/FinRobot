"""Input-fingerprint lineage gate for runs (run_store + routes/runs).

The defect these tests pin: a re-run (or a reattach after a desktop restart)
silently inherited the version lineage of the report it was triggered from. The
new artifact's ``meta.parent_artifact_id`` points at the source artifact, the
desktop's diff view compares the two versions, and the new report ends up
attributed to a lineage whose inputs have since changed — so the diff compares
two different worlds as if they were gate-to-gate comparable.

The mechanism is a CONTENT fingerprint (``input_fingerprint``): a sha256 over a
canonical sorted-key JSON of the run's input set, stamped on the row at creation
and re-derived by ``RunStore.verify_lineage`` from that same row. Three verdicts:
``match`` (nothing moved), ``mismatch`` (the stored inputs no longer fingerprint
to the recorded digest — refused with 409 on the re-run path), and
``unavailable`` (no digest recorded on a legacy row, or no such run — an honest
unknown, which must PROCEED, never be reported as ``match``).

Covered here: digest stability under key order / dict rebuilding, sensitivity to
every single field, round-trip through the DB, the column migration against a
pre-fingerprint DB file (legacy rows stay NULL, never ""), the three verdicts,
and the route behaviour (409 on mismatch; legacy NULL and unreachable sources
both proceed).
"""

from __future__ import annotations

import asyncio
import sqlite3
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from finrobot.llm_probe import LlmProbeGate
from finrobot.routes.runs import router as runs_router
from finrobot.run_store import RunStore, input_fingerprint

# ---------------------------------------------------------------------------
# input_fingerprint — the pure helper
# ---------------------------------------------------------------------------


def _fp(**overrides: Any) -> str:
    """Fingerprint of a complete input set with ``overrides`` applied.

    Relies on the same key spelling the store uses, so the tests read as "this
    input set" rather than repeating five keywords at every call.
    """
    fields: dict[str, Any] = {
        "ticker": "AAPL",
        "pipeline_type": "dcf",
        "language": "en",
        "source_artifact_id": "art_prev_AAPL_dcf",
        "source_decision_hash": "0" * 64,
    }
    fields.update(overrides)
    return input_fingerprint(**fields)


def test_fingerprint_is_stable_across_key_order_and_dict_recreation() -> None:
    """Same inputs → same digest, regardless of dict order or when it is built.

    This is what makes the digest usable as a lineage check at all: it must be a
    function of content only. A wall-clock or insertion-order dependency would
    make every recomputation "mismatch" and the gate would be pure noise.
    """
    base = {
        "ticker": "AAPL",
        "pipeline_type": "dcf",
        "language": "en",
        "source_artifact_id": "art_prev_AAPL_dcf",
        "source_decision_hash": "0" * 64,
    }
    reversed_keys = {k: base[k] for k in reversed(list(base))}
    assert input_fingerprint(**reversed_keys) == input_fingerprint(**base)
    # Re-created dict, separately, at a different moment → identical.
    assert input_fingerprint(**dict(base)) == input_fingerprint(**base)
    # sha256 hex contract: lowercase, 64 chars.
    digest = input_fingerprint(**base)
    assert len(digest) == 64
    assert digest == digest.lower()
    assert all(c in "0123456789abcdef" for c in digest)


@pytest.mark.parametrize(
    ("field", "changed"),
    [
        ("ticker", "MSFT"),
        ("pipeline_type", "lbo"),
        ("language", "zh"),
        ("language", None),
        ("source_artifact_id", "art_prev_AAPL_lbo"),
        ("source_artifact_id", None),
        ("source_decision_hash", None),
        ("source_decision_hash", "1" * 64),
    ],
)
def test_fingerprint_changes_when_any_single_input_changes(field: str, changed: Any) -> None:
    """Every field participates: one changed input moves the digest.

    Includes the None cases — a fresh run (no source artifact) and a re-run must
    never collide, and an explicit digests-free call must differ from a hashed
    source decision.
    """
    assert _fp() != _fp(**{field: changed})


# ---------------------------------------------------------------------------
# Persistence: stamp at creation, round-trip through the DB
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stored_run_round_trips_its_fingerprint(tmp_path: Any) -> None:
    """The digest stamped at creation is what every read path returns.

    The ticker is passed lower-case to prove the digest is taken over the value
    actually persisted (upper-cased) — otherwise recomputation over the stored
    row would "mismatch" every run forever.
    """
    store = RunStore(tmp_path / "runs.db")
    try:
        record = await store.create_run("dcf", "aapl", language="en")
        expected = input_fingerprint(
            ticker="AAPL",
            pipeline_type="dcf",
            language="en",
            source_artifact_id=None,
        )
        assert record.input_fingerprint == expected
        loaded = await store.get_run(record.run_id)
        assert loaded is not None
        assert loaded.ticker == "AAPL"
        assert loaded.input_fingerprint == expected
        listed = await store.list_runs()
        assert [r.input_fingerprint for r in listed] == [expected]
        # A re-run carries the source artifact in its input set → different digest.
        rerun = await store.create_run("dcf", "AAPL", language="en", source_artifact_id="art_prev")
        assert rerun.input_fingerprint is not None
        assert rerun.input_fingerprint != expected
    finally:
        await store.close()


# DDL as it shipped BEFORE the fingerprint column (same CHECK, same
# language/source_artifact_id columns), so this test exercises exactly the new
# _RUN_COLUMN_MIGRATIONS entry with nothing else in play.
_LEGACY_RUNS_DDL = """
CREATE TABLE runs (
    run_id        TEXT PRIMARY KEY,
    pipeline_type TEXT NOT NULL,
    ticker        TEXT NOT NULL,
    status        TEXT NOT NULL CHECK (status IN ('created', 'running', 'completed', 'failed', 'cancelled')),
    created_at    TEXT NOT NULL,
    completed_at  TEXT,
    duration_s    REAL,
    result_text   TEXT,
    result_json   TEXT,
    error         TEXT,
    language      TEXT,
    source_artifact_id TEXT
)
"""


def _build_pre_fingerprint_db(db_path: Any) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(_LEGACY_RUNS_DDL)
        conn.execute(
            "INSERT INTO runs (run_id, pipeline_type, ticker, status, created_at, "
            "language, source_artifact_id) VALUES "
            "('run_legacy1', 'dcf', 'AAPL', 'completed', "
            "'2026-01-01T00:00:00+00:00', 'en', NULL)"
        )
        conn.commit()
    finally:
        conn.close()


@pytest.mark.asyncio
async def test_column_migration_adds_fingerprint_and_legacy_row_stays_null(tmp_path: Any) -> None:
    """Opening a pre-fingerprint DB file ALTERs the column in; legacy rows are NULL.

    NULL — not "" — because "no digest was ever recorded" is the ``unavailable``
    verdict. Coercing it to an empty string would make an unverifiable legacy row
    read as a digest that never matches anything (and, if a caller normalised
    falsy → match, as one that always matches).
    """
    db_path = tmp_path / "runs.db"
    _build_pre_fingerprint_db(db_path)

    store = RunStore(db_path)
    try:
        legacy = await store.get_run("run_legacy1")
        assert legacy is not None
        assert legacy.input_fingerprint is None
        # A run created on the migrated DB gets a real digest (proves the column
        # is writable, not just present).
        fresh = await store.create_run("lbo", "MSFT", language="zh")
        fresh_digest = input_fingerprint(
            ticker="MSFT",
            pipeline_type="lbo",
            language="zh",
            source_artifact_id=None,
        )
        assert fresh.input_fingerprint == fresh_digest
    finally:
        await store.close()

    conn = sqlite3.connect(db_path)
    try:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(runs)").fetchall()}
        legacy_raw = conn.execute(
            "SELECT input_fingerprint FROM runs WHERE run_id = 'run_legacy1'"
        ).fetchone()[0]
        fresh_raw = conn.execute(
            "SELECT input_fingerprint FROM runs WHERE run_id = ?", (fresh.run_id,)
        ).fetchone()[0]
    finally:
        conn.close()
    assert "input_fingerprint" in columns
    # NULL, not "" — see the docstring: an empty string would be a digest that
    # never matches anything (and a falsy value a careless caller could read as
    # "fine"), where NULL is honestly "never recorded".
    assert legacy_raw is None
    assert fresh_raw == fresh_digest

    # Re-opening (the idempotency of the migration) must not blow up on a
    # duplicate-column ALTER.
    reopened = RunStore(db_path)
    try:
        assert (await reopened.get_run("run_legacy1")) is not None
    finally:
        await reopened.close()


# ---------------------------------------------------------------------------
# verify_lineage — match / mismatch / unavailable
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_verify_lineage_match_for_untouched_run(tmp_path: Any) -> None:
    store = RunStore(tmp_path / "runs.db")
    try:
        record = await store.create_run("dcf", "AAPL", language="en")
        verdict = await store.verify_lineage(record.run_id)
        assert verdict.status == "match"
        assert verdict.recorded == record.input_fingerprint
        assert verdict.current == record.input_fingerprint
        assert verdict.reason is None
    finally:
        await store.close()


@pytest.mark.asyncio
async def test_verify_lineage_mismatch_when_stored_inputs_changed(tmp_path: Any) -> None:
    """The row's inputs move after the digest was taken → mismatch.

    Stands in for any backfill/migration/out-of-band edit that rewrites an input
    column (here: the language a re-run would be rendered in). The verdict must
    name BOTH digests so a caller can report what drifted.
    """
    db_path = tmp_path / "runs.db"
    store = RunStore(db_path)
    try:
        record = await store.create_run("dcf", "AAPL", language="en")
    finally:
        await store.close()

    conn = sqlite3.connect(db_path)
    try:
        conn.execute("UPDATE runs SET language='zh' WHERE run_id=?", (record.run_id,))
        conn.commit()
    finally:
        conn.close()

    reopened = RunStore(db_path)
    try:
        verdict = await reopened.verify_lineage(record.run_id)
        assert verdict.status == "mismatch"
        assert verdict.recorded == record.input_fingerprint
        assert verdict.current == input_fingerprint(
            ticker="AAPL",
            pipeline_type="dcf",
            language="zh",
            source_artifact_id=None,
        )
        assert verdict.current != verdict.recorded
        assert verdict.reason
    finally:
        await reopened.close()


@pytest.mark.asyncio
async def test_verify_lineage_unavailable_for_legacy_null_row(tmp_path: Any) -> None:
    """No recorded digest → unavailable. Never "match" (nothing was verified)."""
    db_path = tmp_path / "runs.db"
    _build_pre_fingerprint_db(db_path)
    store = RunStore(db_path)
    try:
        verdict = await store.verify_lineage("run_legacy1")
        assert verdict.status == "unavailable"
        assert verdict.recorded is None
        # The recomputed digest is still reported (it describes the row we could
        # not check), but it is NOT presented as a verification.
        assert verdict.current == input_fingerprint(
            ticker="AAPL",
            pipeline_type="dcf",
            language="en",
            source_artifact_id=None,
        )
        assert verdict.reason
    finally:
        await store.close()


@pytest.mark.asyncio
async def test_verify_lineage_unavailable_for_unknown_run(tmp_path: Any) -> None:
    """A lookup miss is not a mismatch — nothing to compare, nothing to refuse."""
    store = RunStore(tmp_path / "runs.db")
    try:
        verdict = await store.verify_lineage("run_does_not_exist")
        assert verdict.status == "unavailable"
        assert verdict.recorded is None
        assert verdict.current is None
        assert verdict.reason
    finally:
        await store.close()


@pytest.mark.asyncio
async def test_rerun_digest_differs_from_the_fresh_run_it_continues(tmp_path: Any) -> None:
    """The re-run's own digest covers its source artifact — not just ticker/pipeline.

    Guards the store side of the attribution problem: a continuing run and the
    run it continues can never share a digest, or verify_lineage could not tell
    which lineage a report belongs to.
    """
    store = RunStore(tmp_path / "runs.db")
    try:
        original = await store.create_run("dcf", "AAPL", language="en")
        await store.add_artifact(
            original.run_id,
            artifact_type="dcf",
            format="json",
            file_path="/api/artifacts/art_prev_AAPL_dcf",
        )
        continuation = await store.create_run(
            "dcf", "AAPL", language="en", source_artifact_id="art_prev_AAPL_dcf"
        )
        assert (await store.verify_lineage(original.run_id)).status == "match"
        assert (await store.verify_lineage(continuation.run_id)).status == "match"
        assert continuation.input_fingerprint != original.input_fingerprint
        # …and the produced artifact resolves back to the run that made it.
        found = await store.find_run_by_artifact_id("art_prev_AAPL_dcf")
        assert found is not None and found.run_id == original.run_id
        assert await store.find_run_by_artifact_id("art_never_linked") is None
    finally:
        await store.close()


# ---------------------------------------------------------------------------
# Route: the refusal is surfaced, not just recorded
# ---------------------------------------------------------------------------


def _make_app(store: RunStore) -> FastAPI:
    """Runs-router app over a REAL RunStore (the fingerprint path must be exercised)."""
    app = FastAPI()
    app.include_router(runs_router)
    app.state.run_store = store
    app.state.run_tasks = {}
    app.state.startup_error = None
    deps = MagicMock()
    deps.settings.is_model_configured = True
    # "test:" providers never make a live probe call (see LlmProbeGate.ensure).
    deps.settings.model_name = "test:stub"
    app.state.deps = deps
    app.state.llm_probe_gate = LlmProbeGate()
    return app


def _stub_pipeline_spawn(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the spawned pipeline task inert: only run creation is under test."""
    monkeypatch.setattr(
        "finrobot.routes.runs.get_pipeline_factories",
        lambda: {"dcf": lambda agents: MagicMock()},
    )
    monkeypatch.setattr("finrobot.routes.runs._run_pipeline", AsyncMock())


async def _seed_source_run_with_artifact(
    db_path: Any, *, artifact_id: str, language: str = "en"
) -> tuple[str, str | None]:
    """Create a source run + its artifact link; return (run_id, recorded digest)."""
    store = RunStore(db_path)
    try:
        source = await store.create_run("dcf", "AAPL", language=language)
        await store.add_artifact(
            source.run_id,
            artifact_type="dcf",
            format="json",
            file_path=f"/api/artifacts/{artifact_id}",
        )
        return source.run_id, source.input_fingerprint
    finally:
        await store.close()


def _mutate(db_path: Any, sql: str, params: tuple[Any, ...] = ()) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(sql, params)
        conn.commit()
    finally:
        conn.close()


async def _drain_spawned_tasks(app: FastAPI) -> None:
    """Cancel + reap the inert pipeline tasks so no task outlives the test loop."""
    tasks = list(app.state.run_tasks.values())
    for task in tasks:
        task.cancel()
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)


@pytest.mark.asyncio
async def test_rerun_route_409_when_source_lineage_mismatched(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A re-run whose source lineage drifted is refused, with both digests.

    The source run's inputs moved after its digest was recorded, so continuing
    its version chain would attribute this report to a world it does not
    describe. The refusal must come BEFORE create_run — no orphan row, no task.
    """
    db_path = tmp_path / "runs.db"
    artifact_id = "art_prev_AAPL_dcf"
    source_run_id, recorded = await _seed_source_run_with_artifact(db_path, artifact_id=artifact_id)
    assert recorded is not None
    _mutate(db_path, "UPDATE runs SET language='zh' WHERE run_id=?", (source_run_id,))

    store = RunStore(db_path)
    try:
        app = _make_app(store)
        _stub_pipeline_spawn(monkeypatch)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/runs",
                json={
                    "pipeline_type": "dcf",
                    "ticker": "AAPL",
                    "language": "en",
                    "source_artifact_id": artifact_id,
                },
            )

        assert resp.status_code == 409, resp.text
        detail = resp.json()["detail"]
        assert detail["code"] == "lineage_mismatch"
        assert detail["source_artifact_id"] == artifact_id
        assert detail["recorded"] == recorded
        assert detail["current"] == input_fingerprint(
            ticker="AAPL",
            pipeline_type="dcf",
            language="zh",
            source_artifact_id=None,
        )
        assert detail["recorded"] != detail["current"]
        # Refused before any row was written.
        assert [r.run_id for r in await store.list_runs()] == [source_run_id]
        assert app.state.run_tasks == {}
    finally:
        await store.close()


@pytest.mark.asyncio
async def test_rerun_route_proceeds_when_source_fingerprint_unavailable(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A legacy source (NULL fingerprint) is an honest unknown → the run proceeds."""
    db_path = tmp_path / "runs.db"
    artifact_id = "art_prev_AAPL_dcf_legacy"
    source_run_id, _ = await _seed_source_run_with_artifact(db_path, artifact_id=artifact_id)
    _mutate(db_path, "UPDATE runs SET input_fingerprint=NULL WHERE run_id=?", (source_run_id,))

    store = RunStore(db_path)
    try:
        assert (await store.verify_lineage(source_run_id)).status == "unavailable"
        app = _make_app(store)
        _stub_pipeline_spawn(monkeypatch)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/runs",
                json={
                    "pipeline_type": "dcf",
                    "ticker": "AAPL",
                    "language": "en",
                    "source_artifact_id": artifact_id,
                },
            )
            assert resp.status_code == 200, resp.text
            assert resp.json()["status"] == "created"
            created = await store.get_run(resp.json()["run_id"])
        assert created is not None
        assert created.source_artifact_id == artifact_id
        # The continuation carries its own digest over the inherited lineage.
        assert created.input_fingerprint == input_fingerprint(
            ticker="AAPL",
            pipeline_type="dcf",
            language="en",
            source_artifact_id=artifact_id,
        )
        await _drain_spawned_tasks(app)
    finally:
        await store.close()


@pytest.mark.asyncio
async def test_rerun_route_proceeds_when_source_artifact_unreachable(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An artifact no run recorded is a lookup MISS, not a mismatch → proceeds."""
    db_path = tmp_path / "runs.db"
    store = RunStore(db_path)
    try:
        app = _make_app(store)
        _stub_pipeline_spawn(monkeypatch)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/runs",
                json={
                    "pipeline_type": "dcf",
                    "ticker": "AAPL",
                    "source_artifact_id": "art_deleted_or_never_linked",
                },
            )
            assert resp.status_code == 200, resp.text
            created = await store.get_run(resp.json()["run_id"])
        assert created is not None and created.source_artifact_id == "art_deleted_or_never_linked"
        await _drain_spawned_tasks(app)
    finally:
        await store.close()
