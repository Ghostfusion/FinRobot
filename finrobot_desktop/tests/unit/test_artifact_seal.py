"""Artifact seal tests.

The seal is only worth having if each of its four parts answers a question nobody can
answer by reading the payload:

* did these bytes change since they were written (``artifact_sha256``);
* is this the same *call*, even when the prose was regenerated (``decision_hash``);
* is this the same run, and not a second record of it (``idempotency_key``);
* when did it stop being current (``expires_at``).

The load-bearing case is the store's own read path: it rewrites ``meta.archived`` and
``meta.last_viewed_at`` from its COLUMNS on every read, so a hash covering those fields
would call every archived artifact tampered. That exclusion is tested explicitly.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from finrobot.artifact.models import (
    ARTIFACT_SCHEMA_VERSION,
    Artifact,
    ArtifactAssumptions,
    ArtifactComputeVersion,
    ArtifactInputs,
    ArtifactMeta,
    ArtifactOutputs,
)
from finrobot.artifact.seal import (
    artifact_sha256,
    decision_hash,
    decision_subset,
    idempotency_key,
    next_session_expiry,
    parse_version,
    required_fields,
    seal_artifact,
    verify_seal,
)

UTC_TZ = timezone.utc
# 2026-05-01 is a Friday, which makes the expiry cases readable.
FRIDAY = datetime(2026, 5, 1, 14, 30, tzinfo=UTC_TZ)


def _artifact(
    *,
    created_at: datetime = FRIDAY,
    ticker: str = "NVDA",
    type_: str = "equity_research",
    structured: dict | None = None,
    narrative: dict | None = None,
    data_source: str = "yfinance",
) -> Artifact:
    return Artifact(
        id=f"art_{created_at.isoformat()}_{ticker}_{type_}",
        ticker=ticker,
        cross_tickers=[],
        type=type_,  # type: ignore[arg-type]
        inputs=ArtifactInputs(
            data_source=data_source, data_fetched_at=created_at, raw_data={"market": {}}
        ),
        assumptions=ArtifactAssumptions(parameters={}),
        compute_version=ArtifactComputeVersion(version="0.1.0", formula_id="x"),
        outputs=ArtifactOutputs(
            structured=structured or {}, llm_narrative=narrative or {}, summary_text="head"
        ),
        meta=ArtifactMeta(created_at=created_at, source="pipeline:equity_research"),
    )


def _decision_artifact(**overrides: object) -> Artifact:
    structured = {
        "thesis": {
            "recommendation": "BUY",
            "price_target": 920.0,
            "target_date": "2027-05-01",
        },
        "valuation_synthesis": {"verdict": "HOLD"},
    }
    return _artifact(structured=structured, **overrides)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Version contract
# ---------------------------------------------------------------------------


def test_parse_version_reads_each_segment() -> None:
    assert parse_version("1.2.3") == (1, 2, 3)
    assert parse_version("2") == (2,)


@pytest.mark.parametrize("bad", ["", "1.x", "one.two", "1..2"])
def test_parse_version_refuses_a_non_numeric_version(bad: str) -> None:
    """Comparing a malformed version as (0,) would silently make every requirement
    unmet — the failure mode is a wrong answer, not a crash, so it must raise here."""
    with pytest.raises(ValueError):
        parse_version(bad)


def test_required_fields_grows_with_the_version_and_never_shrinks() -> None:
    assert required_fields(ARTIFACT_SCHEMA_VERSION) == ("schema_version", "seal")
    # A payload from a future writer is validated against the strictest rules we know,
    # not the loosest.
    assert required_fields("99.0.0") == ("schema_version", "seal")
    assert required_fields("0.1.0") == ()


# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------


def test_sealing_sets_version_and_both_hashes() -> None:
    sealed = seal_artifact(_decision_artifact())
    assert sealed.schema_version == ARTIFACT_SCHEMA_VERSION
    assert sealed.seal is not None
    assert len(sealed.seal.artifact_sha256) == 64
    assert len(sealed.seal.decision_hash) == 64
    assert verify_seal(sealed) == []


def test_resealing_is_stable_on_both_hashes() -> None:
    """The hashes exclude the seal, so a re-read-and-reseal reproduces them instead of
    hashing a document that contains its own hash."""
    first = seal_artifact(_decision_artifact(), now=FRIDAY)
    second = seal_artifact(first, now=FRIDAY + timedelta(hours=3))
    assert first.seal is not None and second.seal is not None
    assert first.seal.artifact_sha256 == second.seal.artifact_sha256
    assert first.seal.decision_hash == second.seal.decision_hash
    # sealed_at is a wall-clock stamp outside both hashes, so it does move.
    assert first.seal.sealed_at != second.seal.sealed_at


def test_content_change_breaks_the_artifact_hash() -> None:
    sealed = seal_artifact(_decision_artifact())
    tampered = sealed.model_copy(deep=True)
    tampered.outputs.summary_text = "edited"
    assert "artifact_sha256_mismatch" in verify_seal(tampered)


def test_mutable_lifecycle_mirrors_are_not_hashed() -> None:
    """The store realigns `meta.archived` / `meta.last_viewed_at` from its columns at
    read time. Hashing them would report every archived artifact as tampered."""
    sealed = seal_artifact(_decision_artifact())
    moved = sealed.model_copy(deep=True)
    moved.meta.archived = True
    moved.meta.last_viewed_at = FRIDAY + timedelta(days=2)
    assert artifact_sha256(moved) == artifact_sha256(sealed)
    assert verify_seal(moved) == []


def test_content_meta_fields_are_still_hashed() -> None:
    sealed = seal_artifact(_decision_artifact())
    tampered = sealed.model_copy(deep=True)
    tampered.meta.language = "en"
    assert "artifact_sha256_mismatch" in verify_seal(tampered)


# ---------------------------------------------------------------------------
# Decision hash
# ---------------------------------------------------------------------------


def test_decision_hash_ignores_regenerated_prose() -> None:
    """'Same call' must survive a narrative rewrite, or every re-emit looks like a new
    decision."""
    first = seal_artifact(_decision_artifact(narrative={"tagline": "one"}))
    second = seal_artifact(_decision_artifact(narrative={"tagline": "totally different"}))
    assert first.seal is not None and second.seal is not None
    assert first.seal.decision_hash == second.seal.decision_hash


def test_narrative_is_a_projection_so_the_content_hash_ignores_it() -> None:
    """``outputs.llm_narrative`` is declared a mirror of ``structured.thesis.*`` and the
    store re-derives it at read time when it is empty. Hashing a field the reader itself
    regenerates would make a clean artifact look tampered the moment it is opened — so
    the hash covers the source of truth, and an edit to THAT is still caught (see
    ``test_content_change_breaks_the_artifact_hash``)."""
    first = seal_artifact(_decision_artifact(narrative={"tagline": "one"}))
    second = seal_artifact(_decision_artifact(narrative={"tagline": "different"}))
    assert first.seal is not None and second.seal is not None
    assert first.seal.artifact_sha256 == second.seal.artifact_sha256
    # The prose is still covered by the *source of truth*, which is what an edited
    # thesis has to change.
    edited = second.model_copy(deep=True)
    edited.outputs.structured = {"thesis": {"recommendation": "SELL"}}
    assert "artifact_sha256_mismatch" in verify_seal(edited)


def test_decision_hash_moves_when_the_call_moves() -> None:
    base = _decision_artifact()
    moved = _artifact(
        structured={
            "thesis": {
                "recommendation": "SELL",
                "price_target": 920.0,
                "target_date": "2027-05-01",
            },
            "valuation_synthesis": {"verdict": "HOLD"},
        }
    )
    assert decision_hash(base) != decision_hash(moved)


def test_decision_subset_is_a_stable_shape() -> None:
    """A type with no rating must still produce the same keys with None values, so the
    hash of an absence is not the hash of a different document."""
    dcf = decision_subset(_artifact(type_="dcf", structured={"implied_price": 185.4}))
    assert dcf["recommendation"] is None
    assert dcf["verdict"] is None
    assert dcf["price_target"] is None
    assert set(dcf) == set(decision_subset(_decision_artifact()))


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


def test_idempotency_key_identifies_the_run_not_the_bytes() -> None:
    """A re-emit of the same run keeps its key (the store's upsert is then an identity,
    not a second signal); a genuine re-run does not."""
    same_run = _artifact()
    regenerated = _artifact(narrative={"tagline": "different"})
    assert idempotency_key(same_run) == idempotency_key(regenerated)

    later = _artifact(created_at=FRIDAY + timedelta(hours=1))
    assert idempotency_key(later) != idempotency_key(same_run)


# ---------------------------------------------------------------------------
# Expiry
# ---------------------------------------------------------------------------


def test_expiry_is_the_next_weekday_boundary() -> None:
    assert next_session_expiry(FRIDAY) == datetime(2026, 5, 4, tzinfo=UTC_TZ)  # Monday
    # Saturday -> Monday, Sunday -> Monday: the weekend is skipped, never counted.
    assert next_session_expiry(datetime(2026, 5, 2, 9, tzinfo=UTC_TZ)) == datetime(
        2026, 5, 4, tzinfo=UTC_TZ
    )
    assert next_session_expiry(datetime(2026, 5, 3, 23, tzinfo=UTC_TZ)) == datetime(
        2026, 5, 4, tzinfo=UTC_TZ
    )
    # Mid-week rolls one day forward, not to the end of the week.
    assert next_session_expiry(datetime(2026, 5, 5, 6, tzinfo=UTC_TZ)) == datetime(
        2026, 5, 6, tzinfo=UTC_TZ
    )


def test_expiry_treats_a_naive_stamp_as_utc() -> None:
    naive = datetime(2026, 5, 1, 14, 30)
    assert next_session_expiry(naive) == next_session_expiry(FRIDAY)


def test_expiry_is_strictly_after_creation() -> None:
    assert next_session_expiry(FRIDAY) > FRIDAY


# ---------------------------------------------------------------------------
# Verification states
# ---------------------------------------------------------------------------


def test_unsealed_is_a_named_state_not_a_verdict() -> None:
    """A payload built in-process (or written before versioning) has no seal; that must
    read as 'unknown', never as valid and never as tampered."""
    assert verify_seal(_artifact()) == ["no_seal"]


def test_tampering_the_call_flags_both_hashes() -> None:
    sealed = seal_artifact(_decision_artifact())
    tampered = sealed.model_copy(deep=True)
    thesis = dict(tampered.outputs.structured["thesis"])
    thesis["price_target"] = 1.0
    tampered.outputs.structured = {**tampered.outputs.structured, "thesis": thesis}
    problems = verify_seal(tampered)
    assert "artifact_sha256_mismatch" in problems
    assert "decision_hash_mismatch" in problems


def test_stored_and_reloaded_artifact_verifies_clean(tmp_path) -> None:
    """End-to-end through the store: save seals, get verifies, and a column-only
    lifecycle change in between does not look like tampering."""
    import asyncio

    from finrobot.artifact.store import ArtifactStore

    async def scenario() -> None:
        store = ArtifactStore(base_dir=tmp_path)
        try:
            artifact = _decision_artifact()
            await store.save(artifact)
            loaded = await store.get(artifact.id)
            assert loaded is not None
            assert loaded.seal is not None
            assert verify_seal(loaded) == []
            assert loaded.seal.expires_at == next_session_expiry(FRIDAY)

            # Archive is a COLUMN-only update; the payload's mirror moves on read.
            archived = await store.archive_stale(hours=0)
            assert archived >= 1
            reread = await store.get(artifact.id)
            assert reread is not None
            assert verify_seal(reread) == []
        finally:
            await store.close()

    asyncio.run(scenario())
