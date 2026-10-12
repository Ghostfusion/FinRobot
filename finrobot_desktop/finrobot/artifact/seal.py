"""Artifact sealing — content hash, decision hash, identity, expiry.

A stored artifact is the product's evidence: it says "these inputs, these assumptions,
this code version, this call". Until now nothing in the payload let a reader check that
the bytes they are reading are the bytes that were written, or ask whether two artifacts
represent the same call, or tell when the report stopped being current. This module adds
those four pieces as one seal, applied by the store as the last step before persisting.

Three decisions worth stating, because each has an easy wrong version:

* **The hashes exclude the seal.** ``artifact_sha256`` covers the body minus the seal and
  ``decision_hash`` covers the decision subset alone, so sealing is idempotent: re-sealing
  a re-read artifact reproduces the same two hashes rather than hashing a document that
  contains its own hash.
* **The version requirement is additive and version-keyed.** A future payload change adds
  a field to ``_REQUIRED_FROM`` for the version that introduced it (see
  :func:`required_fields`) instead of tightening the model and rejecting every artifact
  ever stored. And the requirement applies to a *sealed* artifact only: a payload written
  before versioning existed cannot retroactively satisfy it, so it is reported as
  ``no_seal`` (a state), never as a missing field.
* **Expiry errs early, never late.** :func:`next_session_expiry` models weekends but not
  exchange holidays, because this layer has no calendar. The consequence is named rather
  than hidden: an artifact can be marked stale up to one session early, and is never
  claimed current past a session it should have expired in.

Layering: ``artifact/`` may import ``engine/**`` (red line 10 forbids only the reverse).
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta

from finrobot.artifact.models import ARTIFACT_SCHEMA_VERSION, Artifact, ArtifactSeal

__all__ = [
    "ARTIFACT_SCHEMA_VERSION",
    "artifact_sha256",
    "decision_hash",
    "decision_subset",
    "idempotency_key",
    "next_session_expiry",
    "parse_version",
    "required_fields",
    "seal_artifact",
    "verify_seal",
]

_REQUIRED_FROM: tuple[tuple[str, tuple[str, ...]], ...] = (("1.0.0", ("schema_version", "seal")),)
"""``(version, fields required from that version onward)``, ascending.

Additive by design: a new payload requirement is a new row here, so artifacts at an
older version keep validating against the rules that existed when they were written.
"""


def parse_version(raw: str) -> tuple[int, ...]:
    """``"1.2.3"`` → ``(1, 2, 3)``. A non-numeric segment is a hard error: silently
    comparing a malformed version as ``(0,)`` would make every requirement look unmet."""
    parts: list[int] = []
    for chunk in raw.split("."):
        try:
            parts.append(int(chunk))
        except ValueError as exc:
            raise ValueError(f"not a numeric version: {raw!r} (segment {chunk!r})") from exc
    if not parts:
        raise ValueError(f"empty version: {raw!r}")
    return tuple(parts)


def required_fields(version: str) -> tuple[str, ...]:
    """Fields an artifact at *version* must carry. Unknown/newer versions return the
    highest declared requirement set, so a payload from a future writer is validated
    against the strictest rules we know rather than the loosest."""
    parsed = parse_version(version)
    applicable = [
        fields for declared, fields in _REQUIRED_FROM if parse_version(declared) <= parsed
    ]
    return applicable[-1] if applicable else ()


def _canonical(document: object) -> str:
    """One serialization for every hash here: sorted keys, compact separators, no ASCII
    escaping. ``default=str`` so a datetime in the payload hashes as its ISO form rather
    than raising — the seal is not the place to discover a non-JSON field."""
    return json.dumps(
        document, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str
    )


def _digest(document: object) -> str:
    return hashlib.sha256(_canonical(document).encode("utf-8")).hexdigest()


def _ensure_utc(value: datetime) -> datetime:
    """Treat a naive stamp as UTC (JSON round-trips drop tzinfo), so an aware and a naive
    form of the same instant hash and expire identically."""
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def decision_subset(artifact: Artifact) -> dict[str, object]:
    """The fields that constitute this artifact's CALL.

    Identity plus the rating contract (recommendation / verdict / price target / target
    date), read defensively out of ``outputs.structured`` and the narrative mirror —
    different artifact types populate different keys, and a missing key stays an explicit
    ``None`` so the shape itself is stable.

    Scope note: for a compute-only artifact (dcf / comps / lbo) the substantive result is
    a value inside ``structured``, which this subset does NOT claim to cover — its
    tamper-evidence is ``artifact_sha256``. The decision hash answers "same call?" for the
    artifacts that carry a rating, and says nothing it cannot back.
    """
    structured = artifact.outputs.structured or {}
    thesis = structured.get("thesis")
    thesis = thesis if isinstance(thesis, dict) else {}
    synthesis = structured.get("valuation_synthesis")
    synthesis = synthesis if isinstance(synthesis, dict) else {}
    target_date = thesis.get("target_date")
    return {
        "ticker": artifact.ticker,
        "cross_tickers": list(artifact.cross_tickers),
        "type": artifact.type,
        "recommendation": thesis.get("recommendation"),
        "verdict": synthesis.get("verdict"),
        "price_target": thesis.get("price_target"),
        "target_date": None if target_date is None else str(target_date),
    }


_MUTABLE_META_FIELDS: tuple[str, ...] = ("archived", "last_viewed_at")
"""``meta`` fields the store owns in its COLUMNS and re-derives into the payload at read
time (``SqliteArtifactStore.get`` realigns them, because a column-only archive never
rewrites the payload). They are excluded from the content hash for that reason: hashing
them would report every archived artifact as tampered. Everything else in ``meta`` —
``created_at``, ``source``, ``language``, ``parent_artifact_id`` — is content and IS
hashed."""

_DERIVED_OUTPUT_FIELDS: tuple[str, ...] = ("llm_narrative",)
"""Payload fields that are MIRRORS of another payload field rather than content of their
own. ``outputs.llm_narrative`` says so in its own docstring ("a mirror of
structured.thesis.* fields ... structured.thesis remains the source of truth"), and the
store re-derives it at read time when it is empty. Hashing a field the reader itself
regenerates would make a clean artifact look tampered the first time it is opened —
so the hash covers the source of truth (``structured``, where a real edit IS detected)
and not its projection."""


def body_for_hash(artifact: Artifact) -> dict[str, object]:
    """The hashed body: the payload minus the seal, minus the mutable lifecycle mirrors
    and minus the derived narrative projection.

    Exposed so a caller can show *what* was hashed rather than guess, and so the
    exclusions are auditable in one place instead of being implied by two call sites.
    """
    body = artifact.model_dump(mode="json", exclude={"seal"})
    meta = body.get("meta")
    if isinstance(meta, dict):
        for field in _MUTABLE_META_FIELDS:
            meta.pop(field, None)
    outputs = body.get("outputs")
    if isinstance(outputs, dict):
        for field in _DERIVED_OUTPUT_FIELDS:
            outputs.pop(field, None)
    return body


def artifact_sha256(artifact: Artifact) -> str:
    """Hash of :func:`body_for_hash` — every content byte, and no lifecycle byte."""
    return _digest(body_for_hash(artifact))


def decision_hash(artifact: Artifact) -> str:
    """Hash of :func:`decision_subset` — two re-emits of the same call agree even when
    their prose was regenerated."""
    return _digest(decision_subset(artifact))


def idempotency_key(artifact: Artifact) -> str:
    """Stable identity for one run's artifact.

    Keyed on ``meta.created_at`` because that is what distinguishes a *re-emit* of the
    same run (same instant → same key, so the store's upsert is a no-op identity, not a
    second signal) from a genuine *re-run* (new instant → new key). ``parent_artifact_id``
    is deliberately excluded: a re-run must not collide with the artifact it iterates on.
    """
    return _digest(
        {
            "ticker": artifact.ticker,
            "type": artifact.type,
            "created_at": _ensure_utc(artifact.meta.created_at).isoformat(),
            "data_source": artifact.inputs.data_source,
        }
    )


def next_session_expiry(created_at: datetime) -> datetime:
    """When this report stops being current: the next weekday boundary after it.

    Weekends are modelled, exchange holidays are not (no calendar in this layer), so the
    bound can land up to one session early and never late — an artifact is never presented
    as current past a session it should have expired in.
    """
    day = (_ensure_utc(created_at) + timedelta(days=1)).date()
    while day.weekday() >= 5:  # Sat = 5, Sun = 6
        day += timedelta(days=1)
    return datetime(day.year, day.month, day.day, tzinfo=UTC)


def seal_artifact(artifact: Artifact, *, now: datetime | None = None) -> Artifact:
    """Return a copy carrying a fresh seal. The store calls this immediately before
    persisting, so it must be the last mutation of the payload.

    Idempotent on the two hashes (they exclude the seal), while ``sealed_at`` — a
    wall-clock stamp, not part of either hash — records when the seal was applied.
    """
    sealed_at = _ensure_utc(now) if now is not None else datetime.now(UTC)
    return artifact.model_copy(
        update={
            "schema_version": ARTIFACT_SCHEMA_VERSION,
            "seal": ArtifactSeal(
                artifact_sha256=artifact_sha256(artifact),
                decision_hash=decision_hash(artifact),
                idempotency_key=idempotency_key(artifact),
                sealed_at=sealed_at,
                expires_at=next_session_expiry(artifact.meta.created_at),
            ),
        }
    )


def verify_seal(artifact: Artifact) -> list[str]:
    """Recompute the seal and return every problem found, in a closed vocabulary.

    ``no_seal`` means the payload was never sealed (a legacy stored artifact, or one built
    in-process and never persisted) — a *state*, never inferred as either valid or
    tampered. Any other entry is a real mismatch: ``artifact_sha256_mismatch`` (the body
    was edited), ``decision_hash_mismatch``, ``idempotency_key_mismatch``,
    ``missing_required_field:<name>``.

    Never raises: the read path calls this on artifacts of unknown age, and a verification
    failure must degrade to a warning, not a 500.
    """
    seal = artifact.seal
    if seal is None:
        return ["no_seal"]

    problems: list[str] = []
    for name, expected in (
        ("artifact_sha256", artifact_sha256(artifact)),
        ("decision_hash", decision_hash(artifact)),
        ("idempotency_key", idempotency_key(artifact)),
    ):
        if getattr(seal, name) != expected:
            problems.append(f"{name}_mismatch")

    for field in required_fields(artifact.schema_version):
        if getattr(artifact, field, None) is None:
            problems.append(f"missing_required_field:{field}")
    return problems
