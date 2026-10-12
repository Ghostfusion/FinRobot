"""Unit tests for the append-only point-in-time snapshot store.

The store exists so a dated read cannot see a later snapshot and so an
unmeasured/delisted name is never silently treated as listed or flat. Each test
pins one of those guarantees against a real ``tmp_path`` file, including the
tolerance for a torn (crashed-append) JSONL line.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from finrobot.engine.data.pit_store import PitStore

D1 = date(2026, 1, 1)
D2 = date(2026, 6, 1)
D3 = date(2026, 12, 1)


@pytest.fixture
def store(tmp_path: Path) -> PitStore:
    return PitStore(tmp_path)


# ---------------------------------------------------------------------------
# The read mask: nothing later than the query date, newest wins
# ---------------------------------------------------------------------------


def test_later_dated_row_is_invisible_while_equal_is_visible(store: PitStore) -> None:
    store.store_snapshot("AAPL", D2, {"close": 2.0})

    assert store.read_as_of("AAPL", D1) is None
    assert store.read_as_of("AAPL", D2) == {"close": 2.0}


def test_newest_qualifying_row_wins(store: PitStore) -> None:
    store.store_snapshot("AAPL", D1, {"close": 1.0})
    store.store_snapshot("AAPL", D2, {"close": 2.0})
    store.store_snapshot("AAPL", D3, {"close": 3.0})

    assert store.read_as_of("AAPL", D3) == {"close": 3.0}
    assert store.read_as_of("AAPL", D2) == {"close": 2.0}
    assert store.read_as_of("AAPL", D1) == {"close": 1.0}


def test_same_date_resolves_last_write_wins(store: PitStore) -> None:
    store.store_snapshot("AAPL", D2, {"close": 1.0})
    store.store_snapshot("AAPL", D2, {"close": 2.0})

    assert store.read_as_of("AAPL", D2) == {"close": 2.0}


def test_missing_symbol_reads_none_not_empty_dict(store: PitStore) -> None:
    assert store.read_as_of("GHOST", D3) is None


def test_non_iso_as_of_is_rejected(store: PitStore) -> None:
    """The mask is a lexicographic compare — a non-canonical key mis-orders."""
    with pytest.raises(ValueError):
        store.store_snapshot("AAPL", "2026/01/01", {})  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        store.store_snapshot("AAPL", "20260101", {})  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        store.store_snapshot(
            "AAPL",
            datetime(2026, 1, 1, 12, tzinfo=timezone.utc),
            {},  # type: ignore[arg-type]
        )


def test_non_iso_read_key_is_rejected_too(store: PitStore) -> None:
    with pytest.raises(ValueError):
        store.read_as_of("AAPL", "2026-1-1")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Membership: survivorship-free, unknown is not "listed"
# ---------------------------------------------------------------------------


def test_membership_is_unknown_when_the_symbol_is_unmeasured(store: PitStore) -> None:
    store.store_snapshot("AAPL", D1, {"close": 100.0})

    assert store.membership("AAPL", D1) == "unknown"
    assert store.membership("GHOST", D1) == "unknown"


def test_membership_from_explicit_listing_bounds(store: PitStore) -> None:
    store.store_snapshot("ZZZ", D1, {"listed_from": "2026-03-01", "listed_to": "2026-09-01"})

    assert store.membership("ZZZ", date(2026, 2, 1)) == "not_yet_listed"
    assert store.membership("ZZZ", date(2026, 3, 1)) == "listed"  # first listed day
    assert store.membership("ZZZ", date(2026, 9, 1)) == "listed"  # last listed day
    assert store.membership("ZZZ", date(2026, 9, 2)) == "delisted"


def test_membership_survives_a_later_exit_mark(store: PitStore) -> None:
    """An exit mark measures no listing bound, so it must not erase the bounds."""
    store.store_snapshot("ZZZ", D1, {"listed_from": "2026-02-01"})
    store.store_exit_mark("ZZZ", D2, -1.0)

    assert store.membership("ZZZ", D3) == "listed"


# ---------------------------------------------------------------------------
# Exit marks: unknown is absent, not flat
# ---------------------------------------------------------------------------


def test_exit_mark_is_absent_without_a_mark(store: PitStore) -> None:
    assert store.exit_mark("WIPE", D3) is None


def test_exit_mark_with_unknown_return_is_none_not_zero(store: PitStore) -> None:
    store.store_exit_mark("WIPE", D2, None)

    assert store.exit_mark("WIPE", D2) is None


def test_exit_mark_with_total_loss_is_negative_not_zero(store: PitStore) -> None:
    store.store_exit_mark("WIPE", D2, -1.0)

    assert store.exit_mark("WIPE", D2) == -1.0


def test_exit_mark_is_invisible_before_its_date(store: PitStore) -> None:
    store.store_exit_mark("WIPE", D3, -1.0)

    assert store.exit_mark("WIPE", D2) is None


def test_exit_mark_same_date_resolves_last_write_wins(store: PitStore) -> None:
    store.store_exit_mark("WIPE", D2, -0.4)
    store.store_exit_mark("WIPE", D2, -1.0)

    assert store.exit_mark("WIPE", D2) == -1.0


# ---------------------------------------------------------------------------
# File format: append-only JSONL, torn lines tolerated, file errors loud
# ---------------------------------------------------------------------------


def test_rows_are_append_only_and_carry_the_declared_schema(
    store: PitStore, tmp_path: Path
) -> None:
    store.store_snapshot("AAPL", D1, {"close": 1.5})
    path = tmp_path / "AAPL.jsonl"
    after_first = path.read_bytes()

    store.store_snapshot("AAPL", D2, {"close": 2.5})

    # Never rewritten: the first row's bytes are still the prefix of the file.
    assert path.read_bytes().startswith(after_first)

    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    first = json.loads(lines[0])
    assert first["symbol"] == "AAPL"
    assert first["as_of"] == "2026-01-01"
    assert first["payload"] == {"close": 1.5}
    assert datetime.fromisoformat(first["stored_at"]).tzinfo is not None


def test_truncated_or_shapeless_lines_are_skipped_not_raised(
    store: PitStore, tmp_path: Path
) -> None:
    store.store_snapshot("AAPL", D1, {"close": 1.0})
    path = tmp_path / "AAPL.jsonl"
    with path.open("ab") as handle:
        handle.write(b'{"symbol": "AAPL", "as_of": "2026-06-01", "stored_')  # torn append
        handle.write(b"\n")
        handle.write(b'{"symbol": "AAPL"}\n')  # valid JSON, but no as_of
        handle.write(b"\xff\xfe not json at all\n")  # not even utf-8 / json
    store.store_snapshot("AAPL", D3, {"close": 3.0})

    assert store.read_as_of("AAPL", D3) == {"close": 3.0}
    assert store.read_as_of("AAPL", D2) == {"close": 1.0}


def test_unicode_payload_round_trips_verbatim(store: PitStore, tmp_path: Path) -> None:
    store.store_snapshot("AAPL", D1, {"name": "腾讯", "note": "café"})

    assert store.read_as_of("AAPL", D1) == {"name": "腾讯", "note": "café"}
    assert "腾讯" in (tmp_path / "AAPL.jsonl").read_text(encoding="utf-8")


def test_a_file_level_error_propagates(store: PitStore, tmp_path: Path) -> None:
    """An unreadable store is a real failure, not an absent row — never swallowed."""
    (tmp_path / "AAPL.jsonl").mkdir()

    with pytest.raises(OSError):
        store.read_as_of("AAPL", D1)
