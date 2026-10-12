"""Unit tests for compute_calibration + GET /api/dashboard/calibration.

The calibration table exists so the engine stops grading its own homework: a hit
rate is only readable against the engine's own base rate, and a bucket below the
closed-event floor must report None rather than a fabricated 0.0 or a neutral
0.5. These tests pin those rules — the floor boundary at N-1/N/N+1, the lift
definition (bucket rate minus overall rate), the "unknown" bucket, and the
`n_closed == 0` / `watching` exclusions — plus the endpoint's
degrade-don't-500 contract on an empty store.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from finrobot.artifact.models import (
    Artifact,
    ArtifactAssumptions,
    ArtifactComputeVersion,
    ArtifactInputs,
    ArtifactMeta,
    ArtifactOutputs,
)
from finrobot.artifact.store import ArtifactStore
from finrobot.engine.aggregations.calibration import (
    CALIBRATION_BUCKETS,
    MIN_CLOSED_EVENTS,
    CalibrationRow,
    compute_calibration,
)
from finrobot.engine.compute.operators.signal import ClosedReturn, Signal
from finrobot.engine.data.interface import DataResult, ProviderError
from finrobot.engine.data.types import DataType
from finrobot.routes.dashboard import router as dashboard_router

UTC = timezone.utc
NOW = datetime(2026, 5, 22, 12, 0, 0, tzinfo=UTC)


# ─────────────────────────────────────────────────────────────────────────────
# Pure aggregation
# ─────────────────────────────────────────────────────────────────────────────


def _row(
    confidence: str | None,
    signal: Signal | None,
    *,
    returns: tuple[float, float] | None = None,
    verdict: str | None = "BUY",
) -> CalibrationRow:
    closed = (
        ClosedReturn(ticker_return=returns[0], sp500_return=returns[1])
        if returns is not None
        else None
    )
    return CalibrationRow(
        confidence=confidence, verdict=verdict, signal=signal, closed_return=closed
    )


def _closed(count: int, *, hits: int, confidence: str | None) -> list[CalibrationRow]:
    """`count` closed rows for one tier, the first `hits` of them hits."""
    return [_row(confidence, "hit" if i < hits else "failed") for i in range(count)]


def test_empty_input_yields_every_bucket_insufficient() -> None:
    overview = compute_calibration([])
    assert set(overview.by_confidence) == set(CALIBRATION_BUCKETS)
    assert overview.overall.n_total == 0
    assert overview.overall.hit_rate is None
    assert overview.status == "insufficient"
    assert overview.min_closed == MIN_CLOSED_EVENTS
    for bucket in overview.by_confidence.values():
        assert bucket.status == "insufficient"
        assert bucket.hit_rate is None
        assert bucket.lift_vs_overall is None


@pytest.mark.parametrize("n_closed, measured", [(2, False), (3, True), (4, True)])
def test_floor_boundary_at_n_minus_one_n_and_n_plus_one(n_closed: int, measured: bool) -> None:
    """min_closed=3: 2 closed rows is insufficient, 3 and 4 are measured."""
    overview = compute_calibration(_closed(n_closed, hits=1, confidence="high"), min_closed=3)
    bucket = overview.by_confidence["high"]
    assert bucket.n_closed == n_closed
    assert (bucket.status == "measured") is measured
    if measured:
        assert bucket.hit_rate == pytest.approx(1 / n_closed)
    else:
        assert bucket.hit_rate is None


def test_bucket_below_floor_reports_insufficient_with_none_rate() -> None:
    overview = compute_calibration(_closed(4, hits=3, confidence="high"), min_closed=5)
    bucket = overview.by_confidence["high"]
    assert bucket.status == "insufficient"
    assert bucket.hit_rate is None
    assert bucket.n_closed == 4
    assert bucket.n_hit == 3


def test_lift_is_bucket_rate_minus_overall_rate() -> None:
    rows = [*_closed(3, hits=3, confidence="high"), *_closed(3, hits=0, confidence="low")]
    overview = compute_calibration(rows, min_closed=3)
    # overall: 6 closed, 3 hits → 0.5 (the base rate the lifts are against).
    assert overview.overall.hit_rate == pytest.approx(0.5)
    assert overview.by_confidence["high"].hit_rate == pytest.approx(1.0)
    assert overview.by_confidence["high"].lift_vs_overall == pytest.approx(0.5)
    # A measured all-failed bucket is a real 0.0 — only UNMEASURED rates are None.
    assert overview.by_confidence["low"].hit_rate == pytest.approx(0.0)
    assert overview.by_confidence["low"].lift_vs_overall == pytest.approx(-0.5)


def test_lift_is_none_when_the_overall_base_rate_is_unmeasured() -> None:
    # 4 closed rows < floor 5 → the base rate itself is unmeasured, so no lift is
    # readable even though the bucket holds exactly the same rows.
    overview = compute_calibration(_closed(4, hits=2, confidence="high"), min_closed=5)
    assert overview.overall.hit_rate is None
    assert overview.by_confidence["high"].lift_vs_overall is None


def test_bucket_below_floor_has_no_lift_while_overall_is_measured() -> None:
    rows = [*_closed(2, hits=1, confidence="high"), *_closed(4, hits=2, confidence="medium")]
    overview = compute_calibration(rows, min_closed=3)
    assert overview.status == "measured"
    assert overview.by_confidence["high"].lift_vs_overall is None
    assert overview.by_confidence["medium"].lift_vs_overall is not None


def test_unknown_confidence_lands_in_its_own_bucket() -> None:
    rows = [
        _row("high", "hit"),
        _row(None, "hit"),
        _row("", "hit"),
        _row("EXTREME", "hit"),
        _row(" High ", "hit"),
    ]
    overview = compute_calibration(rows, min_closed=1)
    # None / blank / out-of-vocabulary → "unknown"; case + whitespace normalise.
    assert overview.by_confidence["unknown"].n_total == 3
    assert overview.by_confidence["high"].n_total == 2
    assert sum(b.n_total for b in overview.by_confidence.values()) == len(rows)


def test_no_closed_rows_yields_none_rate_even_with_many_rows() -> None:
    overview = compute_calibration([_row("high", "watching") for _ in range(10)], min_closed=1)
    bucket = overview.by_confidence["high"]
    assert bucket.n_total == 10
    assert bucket.n_closed == 0
    assert bucket.hit_rate is None
    assert bucket.status == "insufficient"


def test_watching_never_counts_as_closed() -> None:
    rows = [_row("high", "hit"), *[_row("high", "watching") for _ in range(5)]]
    bucket = compute_calibration(rows, min_closed=2).by_confidence["high"]
    assert bucket.n_total == 6
    assert bucket.n_closed == 1
    assert bucket.hit_rate is None


def test_unjudgeable_rows_count_toward_total_only() -> None:
    rows = [_row("high", None), _row("high", None), _row("high", "hit")]
    bucket = compute_calibration(rows, min_closed=1).by_confidence["high"]
    assert bucket.n_total == 3
    assert bucket.n_closed == 1
    assert bucket.n_hit == 1
    assert bucket.hit_rate == pytest.approx(1.0)


def test_avg_excess_return_uses_only_closed_rows() -> None:
    rows = [
        _row("high", "hit", returns=(0.10, 0.05)),
        _row("high", "failed", returns=(-0.10, 0.05)),
        # Too young to judge / unjudgeable: their realised returns must not reach
        # the mean (a non-outcome would otherwise be averaged as one).
        _row("high", "watching", returns=(1.0, 0.0)),
        _row("high", None, returns=(1.0, 0.0)),
    ]
    bucket = compute_calibration(rows, min_closed=2).by_confidence["high"]
    assert bucket.n_closed == 2
    assert bucket.avg_excess_return == pytest.approx(-0.05)


def test_min_closed_floor_must_be_positive() -> None:
    with pytest.raises(ValueError):
        compute_calibration([], min_closed=0)


# ─────────────────────────────────────────────────────────────────────────────
# Route — GET /api/dashboard/calibration
# ─────────────────────────────────────────────────────────────────────────────


class _FakeQuoteLayer:
    """Minimal DataLayer stand-in for the QUOTE path the aggregation uses."""

    def __init__(self, prices: dict[str, float]) -> None:
        self._prices = {k.upper(): v for k, v in prices.items()}

    async def fetch_quote(self, ticker: str) -> DataResult:
        price = self._prices.get(ticker.upper())
        if price is None:
            raise ProviderError(f"no quote for {ticker}")
        return DataResult(
            data={"price": price, "quote_currency": "USD"},
            provider="fake",
            ticker=ticker,
            data_type=DataType.QUOTE,
            timestamp=NOW,
        )

    async def fx_rate_to_usd(self, currency: str) -> float:
        if currency.upper() != "USD":
            raise ProviderError(f"no FX rate for {currency}")
        return 1.0


def _make_artifact(
    *,
    artifact_id: str,
    ticker: str,
    confidence: str,
    entry_price: float = 100.0,
    target_price: float = 130.0,
    days_ago: int = 30,
) -> Artifact:
    ts = NOW - timedelta(days=days_ago)
    return Artifact(
        id=artifact_id,
        ticker=ticker,
        type="equity_research",
        inputs=ArtifactInputs(
            data_source="yfinance",
            data_fetched_at=ts,
            raw_data={"market": {"current_price": entry_price}},
        ),
        assumptions=ArtifactAssumptions(parameters={}),
        compute_version=ArtifactComputeVersion(
            version="0.1.0", git_commit="abcd1234", formula_id="equity_v1"
        ),
        outputs=ArtifactOutputs(
            structured={
                "thesis": {"price_target": target_price, "recommendation": "BUY"},
                "valuation_synthesis": {"confidence": confidence},
            },
            summary_text=f"BUY thesis on {ticker}",
            warnings=[],
        ),
        meta=ArtifactMeta(created_at=ts, source="pipeline:equity_research", user_id="local"),
    )


def _build_app(tmp_path: Path, prices: dict[str, float]) -> tuple[FastAPI, ArtifactStore]:
    app = FastAPI()
    app.include_router(dashboard_router)
    store = ArtifactStore(base_dir=tmp_path / "artifacts")
    app.state.deps = SimpleNamespace(artifact_store=store, data_layer=_FakeQuoteLayer(prices))
    return app, store


@pytest.fixture(autouse=True)
def _clear_calibration_cache() -> Iterator[None]:
    """The endpoint's TTL cache is module-global — a populated run must not leak
    its response into a later test's (e.g. the empty-store) assertion."""
    from finrobot.routes import dashboard as dashboard_mod

    dashboard_mod._CALIBRATION_CACHE.clear()
    yield
    dashboard_mod._CALIBRATION_CACHE.clear()


@pytest.mark.asyncio
async def test_calibration_endpoint_empty_store_is_insufficient(tmp_path: Path) -> None:
    app, store = _build_app(tmp_path, {})
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/dashboard/calibration")
    finally:
        await store.close()

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "insufficient"
    assert body["window"] == "all"
    assert body["min_closed"] == MIN_CLOSED_EVENTS
    assert body["overall"] == {
        "n_total": 0,
        "n_closed": 0,
        "n_hit": 0,
        "hit_rate": None,
        "avg_excess_return": None,
        "lift_vs_overall": None,
        "status": "insufficient",
    }
    assert set(body["by_confidence"]) == {"high", "medium", "low", "very_low", "unknown"}


@pytest.mark.asyncio
async def test_calibration_endpoint_rejects_unknown_window(tmp_path: Path) -> None:
    app, store = _build_app(tmp_path, {})
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/dashboard/calibration?window=7d")
    finally:
        await store.close()

    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_calibration_endpoint_buckets_by_confidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from finrobot import paths
    from finrobot.engine.data import quote_batch

    # Keep the QuoteCache L1/L2 on a per-test file: the endpoint cold-fetches
    # through the fake layer and the cache must not touch the real user db.
    monkeypatch.setattr(paths, "QUOTES_DB", tmp_path / "quotes.db")
    quote_batch.reset_quote_cache_singleton()

    # AAPL 100→130 quoted at 128 = hit; MSFT 100→130 quoted at 60 = failed.
    app, store = _build_app(tmp_path, {"AAPL": 128.0, "MSFT": 60.0})
    try:
        for i in range(5):
            await store.save(
                _make_artifact(artifact_id=f"art_hit_{i}", ticker="AAPL", confidence="high")
            )
        await store.save(_make_artifact(artifact_id="art_fail", ticker="MSFT", confidence="low"))

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/dashboard/calibration")
    finally:
        await store.close()

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "measured"
    assert body["overall"]["n_total"] == 6
    assert body["overall"]["n_closed"] == 6
    assert body["overall"]["n_hit"] == 5
    assert body["overall"]["hit_rate"] == pytest.approx(5 / 6)

    high = body["by_confidence"]["high"]
    assert high["n_total"] == 5
    assert high["n_closed"] == 5
    assert high["status"] == "measured"
    assert high["hit_rate"] == pytest.approx(1.0)
    assert high["lift_vs_overall"] == pytest.approx(1 - 5 / 6)

    # One closed row is below the floor: null rate, no lift — not a 1.0 or 0.0.
    low = body["by_confidence"]["low"]
    assert low["n_closed"] == 1
    assert low["status"] == "insufficient"
    assert low["hit_rate"] is None
    assert low["lift_vs_overall"] is None
