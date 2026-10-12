"""_run_pipeline must bind run_id so downstream logs carry it.

The original check read ``"bind_run(run_id)" in inspect.getsource(_run_pipeline)`` —
a source-text pin: it passes for a commented-out call, fails on a rename that keeps
the behaviour, and says nothing about the ordering it exists to protect. It is
replaced by a behavioural test: the body must *observe* the run_id in the trace
context, and the context must be restored when the task ends.
"""

from __future__ import annotations

import pytest

import finrobot.routes.runs as runs_mod
from finrobot.obs.context import bind_run, current_trace


@pytest.mark.asyncio
async def test_run_pipeline_binds_run_id_around_the_body(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[str] = []

    async def fake_impl(_run_id: str, _request: object) -> None:
        # Read from inside the body: this is what "bind_run(run_id)" is FOR. The
        # request is never touched by the stub, so None is passed deliberately.
        seen.append(current_trace()["run_id"])

    monkeypatch.setattr(runs_mod, "_run_pipeline_impl", fake_impl)
    assert current_trace()["run_id"] == "-"
    await runs_mod._run_pipeline("r_trace_test", None)  # type: ignore[arg-type]
    assert seen == ["r_trace_test"], "the pipeline body did not see its own run_id"
    assert current_trace()["run_id"] == "-", "the binding leaked past the task"


def test_bind_run_sets_trace() -> None:
    rec_run = current_trace()["run_id"]
    assert rec_run == "-"
    with bind_run("r_xyz"):
        assert current_trace()["run_id"] == "r_xyz"
    assert current_trace()["run_id"] == "-"
