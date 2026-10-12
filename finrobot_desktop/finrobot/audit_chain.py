"""Tamper-evident append-only ledger for machine audit records.

One row per saved report artifact, carrying that artifact's numeric-audit
findings (which output-contract assertions were raised and how each was
resolved). Those rows are the evidence behind a published report: an analyst who
comes back to a number six months later must be able to show that the row
describing it has not been edited since it was written. A plain JSONL file
cannot show that — anyone, or any script, with write access to ``~/.finrobot/``
can rewrite a number in place and nothing marks it.

So each row carries the hash of the row before it, and its own hash covers BOTH
that link and its payload::

    hash_i = sha256(canonical({"prev_hash": hash_{i-1}, "payload": payload_i}))

with the first row pointing at the documented :data:`GENESIS` sentinel. Bundling
the link into the hash is what makes the forger's job cost grow: editing row *i*
invalidates row *i*'s own hash, and because row *i+1*'s hash covers row *i*'s
hash, the forgery must be pushed through every later row to the end of the file.
:func:`verify_chain` reports the first row that fails to reproduce, so the cost
of a convincing forgery is rewriting the whole tail.

The failure vocabulary is closed and each code names a different physical act:

* ``hash_mismatch`` — a payload was edited in place.
* ``prev_hash_mismatch`` — a row was removed, reordered, or the head truncated
  (the surviving row still hashes, but its link no longer matches the row above
  it; a missing first row is caught by the link "matching" ``GENESIS``).
* ``seq_gap`` — the ``seq`` column does not continue, so a row was renumbered
  or relocated (``seq`` is deliberately *not* inside the hash — the link and the
  payload are what must be immutable — so the column needs its own check).
* ``malformed_row`` — the line does not parse as a row at all (a torn write, or
  a hand-inserted line).

WHY this module is ``finrobot/audit_chain.py`` and NOT ``finrobot/audit/…``:
``finrobot.audit`` already means "per-session chat transcripts"
(``transcript.py`` / ``persistence.py``) — an append-only *human* log whose whole
identity is untrusted prose with secrets scrubbed out of it. This ledger is a
*machine* record with an integrity contract and no free text, so it is
deliberately a sibling of ``run_store.py`` at the package top level, and
deliberately does not reuse the ``audit`` package name: a reader looking for
"the audit log" must land on the transcript package, and a reader looking for
"the audit hash chain" must land here. Folding this file into ``audit/`` would
make one plausible-looking import (``from finrobot.audit import ...``) resolve to
the wrong log — the exact collision this module's placement avoids.

WHY canonicalization matters: the hash must survive dict ordering and a JSON
round-trip, or a row written by :func:`append_entry` would not verify after
:func:`verify_chain` read it back, and two callers building the same payload with
keys in a different order would produce different chains. Every payload is
therefore serialized exactly once, canonically —

``json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
default=str)``

— and the hash is taken over that string's UTF-8 bytes. The same rule maps
tuples to lists and non-JSON scalars (``datetime``, ``Decimal``, enums) to
``str`` identically on both sides of the round-trip, which is what makes
"write, then verify" stable instead of accidentally order- or type-dependent.

WHY the file format is JSONL: the same format as the session transcripts, so it
is greppable, tail-able and append-only without a database, and a partial tail
from a crash is recoverable (see :func:`append_entry`) rather than fatal.
"""

from __future__ import annotations

import hashlib
import io
import json
import logging
import os
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import cast

logger = logging.getLogger(__name__)

#: Predecessor hash of the first row. A hex-format sentinel rather than ``""``
#: so every value in the ``prev_hash`` column is a well-formed digest — a chain
#: whose head was dropped then fails the ordinary link check instead of needing
#: a special case.
GENESIS = "0" * 64

#: Closed reason vocabulary of :class:`ChainReport`. One constant per physical
#: failure mode (see the module docstring); consumers branch on these strings.
HASH_MISMATCH = "hash_mismatch"
PREV_HASH_MISMATCH = "prev_hash_mismatch"
SEQ_GAP = "seq_gap"
MALFORMED_ROW = "malformed_row"

REASONS: frozenset[str] = frozenset({HASH_MISMATCH, PREV_HASH_MISMATCH, SEQ_GAP, MALFORMED_ROW})

_FIELD_SEQ = "seq"
_FIELD_PREV = "prev_hash"
_FIELD_PAYLOAD = "payload"
_FIELD_HASH = "hash"

#: Filename of the ledger under ``FINROBOT_HOME``. Kept here rather than in
#: ``finrobot/paths.py`` because the constants in that module are storage slots
#: shared by several modules; this file has exactly one owner.
LEDGER_FILENAME = "audit_chain.jsonl"

#: How many tail bytes :func:`_iter_lines_reversed` decodes per step. Rows are
#: small (one per artifact), so a single chunk covers the common case; the chunk
#: only bounds how far a torn tail can force the walk-back to loop.
_TAIL_CHUNK_SIZE = 64 * 1024


def default_ledger_path() -> Path:
    """The ledger :func:`verify_chain` checks when no path is supplied.

    Resolved at *call* time, not import time, for the same reason
    ``persistence._default_dir`` is: the home directory is relocatable (tests
    monkeypatch it) and ``ensure_home()`` must run before the first append so
    ``~/.finrobot/`` exists.
    """
    from finrobot.paths import ensure_home

    return ensure_home() / LEDGER_FILENAME


@dataclass(frozen=True)
class ChainReport:
    """Outcome of one :func:`verify_chain` walk.

    Frozen and validated: a report is handed to callers as evidence about a
    specific file, so it must not be mutated after the fact, and an ``ok`` report
    can never carry a stale failure code (the closed vocabulary is enforced in
    :meth:`__post_init__`).

    Attributes:
        ok: ``True`` iff every row of the ledger verified.
        n_entries: rows read. A failing row is counted (it *was* read), so on a
            clean chain this is the entry count and on a broken one it is the
            position of the failure in rows, not in good entries.
        first_bad_seq: ``seq`` recorded on the first failing row, or ``None``.
        reason: one of :data:`REASONS` when ``ok`` is ``False``, else ``None``.
    """

    ok: bool
    n_entries: int
    first_bad_seq: int | None = None
    reason: str | None = None

    def __post_init__(self) -> None:
        if self.reason is not None and self.reason not in REASONS:
            raise ValueError(
                f"reason {self.reason!r} is not in the closed vocabulary {sorted(REASONS)}"
            )
        if self.ok and self.reason is not None:
            raise ValueError("an ok ChainReport carries no reason")
        if not self.ok and self.reason is None:
            raise ValueError("a failed ChainReport must carry a reason")
        if self.ok and self.first_bad_seq is not None:
            raise ValueError("an ok ChainReport carries no first_bad_seq")
        if not self.ok and self.first_bad_seq is None:
            raise ValueError("a failed ChainReport must name the first bad seq")


def _canonical(document: Mapping[str, object]) -> str:
    """Serialize ``document`` so equal documents always produce equal strings."""
    return json.dumps(
        document,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )


def entry_hash(prev_hash: str, payload: Mapping[str, object]) -> str:
    """Hash of one row: the chain link *and* the payload it points at.

    ``sha256`` (hex) over the canonical serialization of
    ``{"prev_hash": prev_hash, "payload": payload}`` — see the module docstring
    for why the link is inside the hash and why the serialization is canonical
    (key order and JSON round-trips therefore cannot change the digest).
    """
    document: dict[str, object] = {_FIELD_PREV: prev_hash, _FIELD_PAYLOAD: payload}
    return hashlib.sha256(_canonical(document).encode("utf-8")).hexdigest()


def _parse_row(line: str) -> dict[str, object] | None:
    """``line`` as a row dict, or ``None`` when it is not a JSON object."""
    try:
        parsed = json.loads(line)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    return cast("dict[str, object]", parsed)


def _iter_lines_reversed(path: Path) -> Iterator[str]:
    """Yield ``path``'s lines newest-first, decoding only the tail at a time.

    :func:`append_entry` reads the ledger on every artifact save, and it only
    needs the *last* row. Slurping a ledger that has grown for years to find one
    line would make the cost of a save grow with the history behind it, so the
    file is walked back one chunk at a time and the walk stops as soon as a
    parsable row is found. Splitting on ``b"\\n"`` is safe for UTF-8 because a
    newline byte can never be part of a multi-byte sequence; the final element
    of the file is decoded with ``errors="replace"`` so a torn write cannot raise
    here either.
    """
    with open(path, "rb") as fh:
        offset = fh.seek(0, io.SEEK_END)
        carry = b""
        # The very first segment is what follows the file's last newline. When
        # the file ends with a newline that segment is empty and is a formatting
        # artifact, not a blank line — do not report it as a skipped row.
        at_tail = True
        while offset > 0:
            read_size = min(_TAIL_CHUNK_SIZE, offset)
            offset -= read_size
            fh.seek(offset)
            parts = (fh.read(read_size) + carry).split(b"\n")
            carry = parts[0]
            for part in reversed(parts[1:]):
                if at_tail and part == b"":
                    at_tail = False
                    continue
                at_tail = False
                yield part.decode("utf-8", errors="replace")
        if carry:
            yield carry.decode("utf-8", errors="replace")


def _last_parsable_row(path: Path) -> tuple[dict[str, object] | None, int]:
    """Newest row that parses, plus how many newer lines were skipped to find it.

    The skipped count is normally 0. It is non-zero only when the tail holds a
    partially-written line — a crash between ``write`` and ``flush``, or a
    process killed mid-line — and in that case the count is the evidence the
    caller needs to say so out loud instead of silently mis-linking.
    """
    skipped = 0
    for line in _iter_lines_reversed(path):
        if not line.strip():
            skipped += 1
            continue
        row = _parse_row(line)
        if (
            row is None
            or not isinstance(row.get(_FIELD_HASH), str)
            or not isinstance(row.get(_FIELD_SEQ), int)
        ):
            skipped += 1
            continue
        return row, skipped
    return None, skipped


def _ends_with_newline(path: Path) -> bool:
    """True iff ``path`` is empty or its last byte is ``\\n``."""
    with open(path, "rb") as fh:
        if fh.seek(0, io.SEEK_END) == 0:
            return True
        fh.seek(-1, io.SEEK_END)
        return fh.read(1) == b"\n"


def append_entry(path: Path, payload: Mapping[str, object]) -> str:
    """Append one row for ``payload`` and return that row's hash.

    The row is ``{"seq", "prev_hash", "payload", "hash"}`` on a single compact
    JSON line, ``seq`` continuing from the newest complete row (``0`` and
    :data:`GENESIS` when the file is missing or empty). The write is flushed and
    fsynced: a ledger whose whole value is crash-consistency must not report a
    row it did not reach the disk with.

    A partially-written tail line (a torn write) does not abort the append and
    is not deleted — the new row is chained to the newest *complete* row, one
    ``\\n`` is emitted first so the torn fragment stays a line of its own, and a
    warning says how many lines were skipped. The ledger is then honest rather
    than silently repaired: :func:`verify_chain` will report the fragment as
    ``malformed_row``, which is the operator's cue that the file needs attention.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    last_row: dict[str, object] | None = None
    skipped = 0
    if path.exists():
        last_row, skipped = _last_parsable_row(path)
    if skipped:
        logger.warning(
            "audit_chain: skipped %d unparsable tail line(s) of %s (torn write?) — "
            "chaining the new row to the newest complete row; `finrobot verify-audit` "
            "will report the fragment as %s",
            skipped,
            path,
            MALFORMED_ROW,
        )

    if last_row is None:
        prev_hash = GENESIS
        seq = 0
    else:
        prev_hash = cast("str", last_row[_FIELD_HASH])
        seq = cast("int", last_row[_FIELD_SEQ]) + 1

    # Normalize the payload to a plain dict before hashing: ``json`` cannot
    # serialize an arbitrary ``Mapping``, and hashing the normalized copy is
    # what guarantees the digest matches the one recomputed from the parsed row.
    stored_payload = dict(payload)
    new_hash = entry_hash(prev_hash, stored_payload)
    row: dict[str, object] = {
        _FIELD_SEQ: seq,
        _FIELD_PREV: prev_hash,
        _FIELD_PAYLOAD: stored_payload,
        _FIELD_HASH: new_hash,
    }
    line = json.dumps(row, ensure_ascii=False, separators=(",", ":"), default=str)
    torn_tail = path.exists() and path.stat().st_size > 0 and not _ends_with_newline(path)
    with open(path, "ab") as fh:
        if torn_tail:
            fh.write(b"\n")
        fh.write(line.encode("utf-8") + b"\n")
        fh.flush()
        os.fsync(fh.fileno())
    return new_hash


def verify_chain(path: Path) -> ChainReport:
    """Walk ``path`` and report the FIRST row that does not verify.

    Rows are checked in order — shape, then ``hash`` (payload edited), then
    ``prev_hash`` (row removed/reordered/head truncated), then ``seq`` (rows
    relocated) — and the walk stops at the first failure, because every later row
    is unverifiable once the chain is broken and a cascade of failures would only
    bury the one that matters. A missing file and an empty file are both a valid
    empty chain. This never raises: a corrupt ledger is a *result*, exactly like
    a clean one.
    """
    if not path.exists():
        return ChainReport(ok=True, n_entries=0)

    prev_hash = GENESIS
    expected_seq = 0
    n_entries = 0
    with open(path, encoding="utf-8", errors="replace") as fh:
        for raw_line in fh:
            line = raw_line.rstrip("\r\n")
            n_entries += 1
            row = _parse_row(line) if line.strip() else None
            if row is None:
                return ChainReport(
                    ok=False, n_entries=n_entries, first_bad_seq=expected_seq, reason=MALFORMED_ROW
                )

            seq = row.get(_FIELD_SEQ)
            stored_hash = row.get(_FIELD_HASH)
            stored_prev = row.get(_FIELD_PREV)
            payload = row.get(_FIELD_PAYLOAD)
            # A row whose own ``seq`` is unreadable can only be located by where
            # it sits, so report the position we expected it at.
            row_seq = seq if isinstance(seq, int) and not isinstance(seq, bool) else expected_seq
            if (
                not isinstance(seq, int)
                or isinstance(seq, bool)
                or not isinstance(stored_hash, str)
                or not isinstance(stored_prev, str)
                or not isinstance(payload, dict)
            ):
                return ChainReport(
                    ok=False, n_entries=n_entries, first_bad_seq=row_seq, reason=MALFORMED_ROW
                )

            if entry_hash(stored_prev, payload) != stored_hash:
                return ChainReport(
                    ok=False, n_entries=n_entries, first_bad_seq=row_seq, reason=HASH_MISMATCH
                )
            if stored_prev != prev_hash:
                return ChainReport(
                    ok=False, n_entries=n_entries, first_bad_seq=row_seq, reason=PREV_HASH_MISMATCH
                )
            if seq != expected_seq:
                return ChainReport(
                    ok=False, n_entries=n_entries, first_bad_seq=row_seq, reason=SEQ_GAP
                )

            prev_hash = stored_hash
            expected_seq += 1
    return ChainReport(ok=True, n_entries=n_entries)
