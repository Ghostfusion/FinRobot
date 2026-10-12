"""Append-only point-in-time (PIT) snapshot store — survivorship-free reads.

WHY this exists: a historical backtest that re-reads the *current* snapshot of a
symbol is quietly trading on tomorrow's information, and it keeps only the
winners. The classic failure is a delisted name: read today, the vendor no longer
serves it (or serves its last print), so the universe the backtest sees has lost
every name that died — survivorship bias, invisible in the numbers. This store
keeps every snapshot stamped with the semantic instant it belongs to (``as_of`` —
the same vocabulary as ``Provenance.as_of``, *not* the wall-clock ``fetched_at``),
so a read pinned to a date sees exactly what was knowable then and nothing later.

One append-only JSONL file per symbol — ``<root>/<SYMBOL>.jsonl`` — with rows
``{"symbol", "as_of", "stored_at", "payload"}``, one per line, never rewritten.
Appending only means a reader can never observe a torn update of an existing
row, and the file is a full audit trail of what was known when. Because the read
mask is a lexicographic string compare over ``as_of``, ``as_of`` is *enforced* to
be fixed-width ``YYYY-MM-DD`` on the way in (see :func:`_iso_date`): a
``datetime`` or a ``2026/01/01`` string would compare in the wrong order and
silently serve a snapshot from the wrong date.

Listing bounds live in the payload as explicit ``listed_from`` / ``listed_to``
``YYYY-MM-DD`` strings. A symbol with neither key is ``"unknown"``, never
assumed ``"listed"`` — an unmeasured name must not silently rejoin the universe
(the whole point of the store). Likewise an unknown exit return is absent
(``None``), never ``0.0``: a wiped-out position must not read as flat.

Failure policy: a malformed/truncated JSONL line is SKIPPED with a warning. A
half-written final line is what a crashed append leaves behind and was never a
validly committed row, so letting it abort the read would throw away every good
row above it. A *file-level* error (``OSError`` other than ``FileNotFoundError``,
which merely means "no snapshot yet") is NOT swallowed — it propagates, because
an unreadable store is a real failure, not an absent row.
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)

__all__ = ["Membership", "PitStore", "default_pit_root"]

#: Listing status derived from an explicit ``listed_from`` / ``listed_to`` pair in
#: the governing payload. ``"unknown"`` is the honest default: a symbol nobody
#: measured is not thereby listed.
Membership = Literal["listed", "delisted", "not_yet_listed", "unknown"]

_LISTED_FROM = "listed_from"
_LISTED_TO = "listed_to"
_DELISTING_RETURN = "delisting_return"


def default_pit_root() -> Path:
    """Where the running system keeps its point-in-time snapshots.

    Resolved at *call* time for the same reason ``audit_chain.default_ledger_path`` and
    ``audit.persistence._default_dir`` are: the home directory is relocatable (tests
    monkeypatch it) and ``ensure_home()`` must run before the first write.
    """
    from finrobot.paths import ensure_home

    root = ensure_home() / "pit"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


def _iso_date(value: object) -> str:
    """The canonical ``YYYY-MM-DD`` for a PIT key, or ``ValueError``.

    The read mask is a lexicographic string compare over the stored ``as_of``
    column, so the ONLY safe shape is fixed-width, zero-padded ISO. A
    ``datetime`` (it carries a time), a non-canonical string (``2026/01/01``,
    ``20260101``, ISO-week form) or any other type would compare wrongly and
    silently mis-order snapshots — so refuse it at the edge rather than store or
    query something the mask cannot honor.
    """
    if isinstance(value, datetime):
        raise ValueError(
            f"pit_store as_of must be a bare date, got datetime {value!r}; pass value.date()"
        )
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str):
        try:
            parsed = date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(f"pit_store as_of must be YYYY-MM-DD, got {value!r}") from exc
        if parsed.isoformat() != value:
            raise ValueError(f"pit_store as_of must be YYYY-MM-DD, got {value!r}")
        return parsed.isoformat()
    raise ValueError(f"pit_store as_of must be a date or YYYY-MM-DD string, got {value!r}")


def _validate_symbol(symbol: str) -> str:
    """The symbol becomes a file stem, so refuse anything that could escape root.

    ``..``/separators would let one symbol read or append to another file (or
    outside ``root`` entirely); a ``:`` is a drive-relative path on Windows; a
    NUL truncates the name; and surrounding whitespace makes a stem nobody can
    find again. Everything else is taken verbatim — this store is not a ticker
    validator.
    """
    if (
        not symbol
        or symbol in {".", ".."}
        or any(char in symbol for char in ("/", "\\", ":", "\x00"))
        or symbol.strip() != symbol
    ):
        raise ValueError(f"invalid pit_store symbol {symbol!r}")
    return symbol


def _parse_row(line: str, path: Path) -> dict[str, object] | None:
    """One JSON-object row, or ``None`` for a line to skip (malformed / not a row)."""
    try:
        parsed: object = json.loads(line)
    except json.JSONDecodeError:
        logger.warning("pit_store: skipping malformed JSONL line in %s", path)
        return None
    if not isinstance(parsed, dict):
        logger.warning("pit_store: skipping non-object JSONL line in %s", path)
        return None
    if not isinstance(parsed.get("as_of"), str):
        logger.warning("pit_store: skipping JSONL row without an as_of date in %s", path)
        return None
    return {str(key): value for key, value in parsed.items()}


def _row_payload(row: dict[str, object]) -> dict[str, object] | None:
    """The row's ``payload`` object, or ``None`` when it is missing/not an object."""
    value = row.get("payload")
    if isinstance(value, dict):
        return {str(key): item for key, item in value.items()}
    return None


def _payload_date(payload: dict[str, object], key: str) -> str | None:
    """Canonical ISO date for an explicit bound key, ``None`` when absent/malformed.

    A malformed bound reads as *unmeasured* rather than guessed — the caller then
    falls back to an older snapshot or ``"unknown"``, never to ``"listed"``.
    """
    if key not in payload:
        return None
    raw = payload[key]
    if not isinstance(raw, str):
        logger.warning("pit_store: payload %s=%r is not an ISO date string", key, raw)
        return None
    try:
        return _iso_date(raw)
    except ValueError:
        logger.warning("pit_store: payload %s=%r is not a YYYY-MM-DD date", key, raw)
        return None


def _listing_bounds(payload: dict[str, object]) -> tuple[str | None, str | None] | None:
    """``(listed_from, listed_to)`` when the payload states a listing bound.

    ``None`` means the payload measures neither bound — an exit mark or a plain
    price snapshot is not evidence of listing status, so it is not a membership
    candidate at all.
    """
    listed_from = _payload_date(payload, _LISTED_FROM)
    listed_to = _payload_date(payload, _LISTED_TO)
    if listed_from is None and listed_to is None:
        return None
    return listed_from, listed_to


def _as_float(value: object) -> float | None:
    """A stored delisting return as a float, or ``None`` when it is not a number.

    ``bool`` is excluded explicitly (``True`` is an ``int`` in Python and would
    otherwise read as ``1.0`` — a fabricated +100% exit).
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


class PitStore:
    """Append-only, per-symbol point-in-time snapshot store."""

    def __init__(self, root: Path) -> None:
        self._root = Path(root)

    # -- writes ------------------------------------------------------------

    def store_snapshot(self, symbol: str, as_of: date, payload: dict[str, object]) -> None:
        """Append ``payload`` as the snapshot whose semantic instant is ``as_of``.

        ``as_of`` must be exactly ``YYYY-MM-DD`` ISO (``ValueError`` otherwise):
        the read mask is a lexicographic compare, so any other shape silently
        mis-orders. Payload values must be JSON-serializable; listing bounds must
        be ``YYYY-MM-DD`` strings (any other value reads as unmeasured).
        """
        self._append(symbol, as_of, payload)

    def store_exit_mark(self, symbol: str, as_of: date, delisting_return: float | None) -> None:
        """Append an explicit exit mark for ``symbol`` at ``as_of``.

        ``delisting_return=None`` records "exited, return unknown" — :meth:`exit_mark`
        then answers ``None`` (absent), never ``0.0``, so a wiped-out name cannot
        read as flat.
        """
        self._append(symbol, as_of, {_DELISTING_RETURN: delisting_return})

    def _append(self, symbol: str, as_of: date, payload: dict[str, object]) -> None:
        stem = _validate_symbol(symbol)
        row: dict[str, object] = {
            "symbol": stem,
            "as_of": _iso_date(as_of),
            "stored_at": _utcnow().isoformat(),
            "payload": payload,
        }
        path = self._root / f"{stem}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    # -- reads -------------------------------------------------------------

    def read_as_of(self, symbol: str, as_of: date) -> dict[str, object] | None:
        """The newest payload dated on/before ``as_of``, or ``None``.

        A row dated later is invisible. Ties on ``as_of`` resolve last-write-wins
        (the later line in the append-only file). ``None`` — never ``{}``, never a
        default — means nothing qualifies.
        """
        best: tuple[str, dict[str, object]] | None = None
        for row_as_of, payload in self._qualifying_payloads(symbol, _iso_date(as_of)):
            if best is None or row_as_of >= best[0]:
                best = (row_as_of, payload)
        return best[1] if best is not None else None

    def membership(self, symbol: str, as_of: date) -> Membership:
        """Listing status at ``as_of``, from the governing explicit listing bounds.

        The governing row is the newest qualifying snapshot that states a bound;
        a later row that measures neither (an exit mark, a price snapshot) does
        NOT erase the bounds. An unmeasured symbol — or one with no qualifying
        bound — is ``"unknown"``, never assumed listed.
        """
        key = _iso_date(as_of)
        best: tuple[str, tuple[str | None, str | None]] | None = None
        for row_as_of, payload in self._qualifying_payloads(symbol, key):
            bounds = _listing_bounds(payload)
            if bounds is None:
                continue
            if best is None or row_as_of >= best[0]:
                best = (row_as_of, bounds)
        if best is None:
            return "unknown"
        listed_from, listed_to = best[1]
        if listed_from is not None and key < listed_from:
            return "not_yet_listed"
        if listed_to is not None and key > listed_to:
            return "delisted"
        return "listed"

    def exit_mark(self, symbol: str, as_of: date) -> float | None:
        """The newest qualifying delisting return, or ``None`` when unknown.

        Unknown is absent (``None``), never ``0.0``: a delisted name owes the
        book its real (usually total) loss, and a fabricated flat exit would hide
        exactly the survivorship the store exists to prevent.
        """
        key = _iso_date(as_of)
        best: tuple[str, float | None] | None = None
        for row_as_of, payload in self._qualifying_payloads(symbol, key):
            if _DELISTING_RETURN not in payload:
                continue
            if best is None or row_as_of >= best[0]:
                best = (row_as_of, _as_float(payload[_DELISTING_RETURN]))
        return best[1] if best is not None else None

    # -- internals ---------------------------------------------------------

    def _path(self, symbol: str) -> Path:
        return self._root / f"{_validate_symbol(symbol)}.jsonl"

    def _read_rows(self, symbol: str) -> list[dict[str, object]]:
        """Every parsable row, in file (write) order. Skipped/corrupt lines warned."""
        path = self._path(symbol)
        try:
            raw = path.read_bytes()
        except FileNotFoundError:
            return []
        except OSError:
            logger.exception("pit_store: cannot read snapshot file %s", path)
            raise
        rows: list[dict[str, object]] = []
        for line in raw.split(b"\n"):
            if not line.strip():
                continue
            # Decode per line with replacement: a crash mid-append can truncate a
            # multi-byte character, and a strict decode would sink the whole file
            # over one torn line. The line then simply fails to parse and is skipped.
            row = _parse_row(line.decode("utf-8", errors="replace"), path)
            if row is not None:
                rows.append(row)
        return rows

    def _qualifying_payloads(self, symbol: str, key: str) -> list[tuple[str, dict[str, object]]]:
        """``(row_as_of, payload)`` for rows dated on/before ``key``, in write order."""
        qualifying: list[tuple[str, dict[str, object]]] = []
        for row in self._read_rows(symbol):
            row_as_of = row.get("as_of")
            payload = _row_payload(row)
            if isinstance(row_as_of, str) and row_as_of <= key and payload is not None:
                qualifying.append((row_as_of, payload))
        return qualifying
