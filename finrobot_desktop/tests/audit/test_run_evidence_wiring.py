"""A completed run must leave all three side records the persist boundary now writes.

Each piece is unit-tested on its own (seal, chain, PIT store, truncation guard). This
test exists because the *wiring* is what decays: a refactor can leave every helper green
while nothing calls it — the "declared but inert" failure this repo keeps finding in its
own surfaces (inert gates, unreferenced prompt assets, a tier router nothing consumes).
So it drives a real `Pipeline.execute` and then asserts on what landed on disk.

Everything is written under a monkeypatched home, so the run touches a tmp directory and
never the operator's `~/.finrobot`.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from finrobot import paths
from finrobot.artifact.models import (
    Artifact,
    ArtifactAssumptions,
    ArtifactComputeVersion,
    ArtifactInputs,
    ArtifactMeta,
    ArtifactOutputs,
)
from finrobot.artifact.seal import verify_seal
from finrobot.artifact.store import ArtifactStore
from finrobot.audit_chain import default_ledger_path, verify_chain
from finrobot.engine.compute.operators.narrative_integrity import TRUNCATION_MARKER
from finrobot.engine.data.pit_store import PitStore, default_pit_root
from finrobot.engine.models.financial import StepOutput
from finrobot.engine.pipelines.base import Pipeline, PipelineStep, TextValidator
from finrobot.engine.pipelines.validators import validate_is_non_empty

UTC = timezone.utc
_CUT_TEXT = "The company's operating margin expanded to twenty four point three percent,"


def _artifact(ticker: str, fetched_at: datetime) -> Artifact:
    return Artifact(
        id=f"art_{fetched_at.isoformat()}_{ticker}_equity_research",
        ticker=ticker,
        cross_tickers=[],
        type="equity_research",
        inputs=ArtifactInputs(
            data_source="yfinance", data_fetched_at=fetched_at, raw_data={"market": {"px": 1.0}}
        ),
        assumptions=ArtifactAssumptions(parameters={}),
        compute_version=ArtifactComputeVersion(version="0.1.0", formula_id="x"),
        outputs=ArtifactOutputs(structured={}, llm_narrative={}, summary_text="s"),
        meta=ArtifactMeta(created_at=fetched_at, source="test"),
    )


@pytest.mark.asyncio
async def test_completed_run_writes_seal_chain_row_and_pit_snapshot(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path / ".finrobot"
    monkeypatch.setattr(paths, "FINROBOT_HOME", home)
    monkeypatch.setattr(paths, "LOGS_DIR", home / "logs")

    fetched_at = datetime.now(UTC)
    store = ArtifactStore(base_dir=tmp_path / "artifacts")

    async def truncated_step(
        _agent: object,
        _deps: object,
        _prompt: str,
        _structured_context: dict[str, object],
        _ticker: str,
        **_kwargs: object,
    ) -> StepOutput:
        return StepOutput(text=_CUT_TEXT)

    def builder(_result: object, ticker: str, _deps: object) -> Artifact:
        return _artifact(ticker, fetched_at)

    pipeline = Pipeline(
        steps=[
            PipelineStep(
                name="thesis",
                agent=MagicMock(),
                validator=TextValidator(validate_is_non_empty),
                executor=truncated_step,
            )
        ],
        artifact_builder=builder,
    )
    deps = MagicMock()
    deps.skill_runtime = None
    deps.artifact_store = store
    deps.run_semaphore = None

    try:
        result = await pipeline.execute(deps, "NVDA")
        assert result.artifact_id is not None

        # 1. The truncation guard fired at the single choke point.
        assert TRUNCATION_MARKER in result.steps["thesis"]
        assert any("truncated" in w for w in result.warnings)

        # 2. The stored payload is sealed and verifies.
        loaded = await store.get(result.artifact_id)
        assert loaded is not None
        assert loaded.seal is not None
        assert verify_seal(loaded) == []

        # 3. The ledger carries exactly one verifiable row, linked to the artifact.
        ledger = default_ledger_path()
        assert ledger.exists()
        report = verify_chain(ledger)
        assert report.ok is True
        assert report.n_entries == 1
        row = json.loads(ledger.read_text(encoding="utf-8").strip().splitlines()[0])
        assert row["payload"]["artifact_id"] == result.artifact_id
        assert row["payload"]["artifact_sha256"] == loaded.seal.artifact_sha256

        # 4. The PIT snapshot is readable at its own date and INVISIBLE before it —
        #    the lookahead mask, proven through the write path the run actually uses.
        pit = PitStore(default_pit_root())
        view = pit.read_as_of("NVDA", fetched_at.date())
        assert view is not None
        assert view["artifact_id"] == result.artifact_id
        assert pit.read_as_of("NVDA", fetched_at.date() - timedelta(days=1)) is None
        # An unmeasured symbol is unknown, never assumed listed.
        assert pit.membership("NVDA", fetched_at.date()) == "unknown"
    finally:
        await store.close()


@pytest.mark.asyncio
async def test_run_evidence_survives_an_unwritable_home(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The side records must never fail a completed run: a run whose home directory
    cannot be created still returns, because the artifact is the record of the run —
    and the persist block maps any escaping exception to "run failed"."""
    blocker = tmp_path / "blocked"
    blocker.write_text("not a directory", encoding="utf-8")
    monkeypatch.setattr(paths, "FINROBOT_HOME", blocker / ".finrobot")
    monkeypatch.setattr(paths, "LOGS_DIR", blocker / ".finrobot" / "logs")

    store = ArtifactStore(base_dir=tmp_path / "artifacts2")

    async def ok_step(
        _agent: object,
        _deps: object,
        _prompt: str,
        _structured_context: dict[str, object],
        _ticker: str,
        **_kwargs: object,
    ) -> StepOutput:
        return StepOutput(text="Revenue grew 12% year over year, driven by cloud demand.")

    def builder(_result: object, ticker: str, _deps: object) -> Artifact:
        return _artifact(ticker, datetime.now(UTC))

    pipeline = Pipeline(
        steps=[
            PipelineStep(
                name="thesis",
                agent=MagicMock(),
                validator=TextValidator(validate_is_non_empty),
                executor=ok_step,
            )
        ],
        artifact_builder=builder,
    )
    deps = MagicMock()
    deps.skill_runtime = None
    deps.artifact_store = store
    deps.run_semaphore = None
    try:
        result = await asyncio.wait_for(pipeline.execute(deps, "MSFT"), timeout=60)
        assert result.artifact_id is not None
    finally:
        await store.close()
