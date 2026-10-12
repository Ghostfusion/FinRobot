"""Unit tests for the machine audit hash chain (``finrobot/audit_chain.py``).

Every case asserts on the *observable* ledger file: rows are written through the
public API and then re-read and re-parsed from disk, so an implementation that
keeps the in-memory API green while writing a different file still fails. The
tamper cases rewrite the file with plain text and plain line operations — no
private helpers, no monkeypatching — because that is literally what an editor or
a stray script does, and detecting exactly that is the whole point of the chain.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from finrobot.audit_chain import (
    GENESIS,
    ChainReport,
    append_entry,
    entry_hash,
    verify_chain,
)


def _read_rows(path: Path) -> list[dict[str, object]]:
    """Re-read the ledger from disk the way an auditor would."""
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _parsable_rows(path: Path) -> list[dict[str, object]]:
    """The rows of a ledger that deliberately contains an unparsable fragment."""
    rows: list[dict[str, object]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def _rewrite(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Writing and linking
# ---------------------------------------------------------------------------


def test_appended_rows_link_to_genesis_and_to_each_other(tmp_path: Path) -> None:
    path = tmp_path / "ledger.jsonl"
    returned = [append_entry(path, {"artifact": f"a{i}", "severity": "warn"}) for i in range(3)]

    rows = _read_rows(path)
    assert [row["seq"] for row in rows] == [0, 1, 2]
    assert rows[0]["prev_hash"] == GENESIS
    for index in range(1, len(rows)):
        assert rows[index]["prev_hash"] == rows[index - 1]["hash"]
    # The returned hash is the one on disk, and each row's hash reproduces from
    # the row's own stored payload + link (i.e. the file is self-consistent).
    assert returned == [row["hash"] for row in rows]
    for row in rows:
        assert entry_hash(row["prev_hash"], row["payload"]) == row["hash"]


def test_append_to_a_missing_file_starts_from_genesis(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "ledger.jsonl"  # parent directory does not exist yet

    new_hash = append_entry(path, {"artifact": "a0"})

    rows = _read_rows(path)
    assert len(rows) == 1
    assert rows[0]["seq"] == 0
    assert rows[0]["prev_hash"] == GENESIS
    assert rows[0]["hash"] == new_hash


def test_hash_is_order_independent_and_survives_a_json_round_trip(tmp_path: Path) -> None:
    # Same document, keys inserted in a different order: one chain, one digest.
    assert entry_hash(GENESIS, {"b": [1, 2], "a": {"nested": True}}) == entry_hash(
        GENESIS, {"a": {"nested": True}, "b": [1, 2]}
    )

    # A tuple and a date-shaped object are canonicalized identically on both
    # sides of the round-trip, so the row still verifies after being read back.
    path = tmp_path / "ledger.jsonl"
    append_entry(path, {"pair": (1, 2), "note": "cap", "seen": 3})

    assert _read_rows(path)[0]["payload"] == {"pair": [1, 2], "note": "cap", "seen": 3}
    assert verify_chain(path).ok is True


def test_hash_covers_the_chain_link_and_not_only_the_payload() -> None:
    # If the link were outside the hash, a rewritten row could be re-linked to
    # any predecessor at no cryptographic cost — the case this pins.
    payload = {"artifact": "a0"}
    assert entry_hash(GENESIS, payload) != entry_hash("f" * 64, payload)


# ---------------------------------------------------------------------------
# Verification of untouched and missing ledgers
# ---------------------------------------------------------------------------


def test_untouched_chain_verifies_ok(tmp_path: Path) -> None:
    path = tmp_path / "ledger.jsonl"
    for index in range(4):
        append_entry(path, {"artifact": f"a{index}"})

    report = verify_chain(path)

    assert isinstance(report, ChainReport)
    assert report.ok is True
    assert report.n_entries == 4
    assert report.first_bad_seq is None
    assert report.reason is None


def test_missing_and_empty_ledgers_verify_as_an_empty_chain(tmp_path: Path) -> None:
    missing = verify_chain(tmp_path / "never-written.jsonl")
    assert missing.ok is True
    assert missing.n_entries == 0
    assert missing.reason is None

    empty = tmp_path / "empty.jsonl"
    empty.write_text("", encoding="utf-8")
    assert verify_chain(empty).ok is True
    assert verify_chain(empty).n_entries == 0


# ---------------------------------------------------------------------------
# Tampering
# ---------------------------------------------------------------------------


def test_edited_payload_is_reported_as_hash_mismatch(tmp_path: Path) -> None:
    path = tmp_path / "ledger.jsonl"
    for index in range(4):
        append_entry(path, {"artifact": f"a{index}", "value": index})

    lines = path.read_text(encoding="utf-8").splitlines()
    tampered = json.loads(lines[2])
    tampered["payload"]["value"] = 999  # same shape, different number
    lines[2] = json.dumps(tampered)
    _rewrite(path, lines)

    report = verify_chain(path)

    assert report.ok is False
    assert report.reason == "hash_mismatch"
    assert report.first_bad_seq == 2
    assert report.n_entries == 3  # the row it stopped on was read


def test_deleted_middle_row_is_reported_as_prev_hash_mismatch(tmp_path: Path) -> None:
    path = tmp_path / "ledger.jsonl"
    for index in range(4):
        append_entry(path, {"artifact": f"a{index}"})

    lines = path.read_text(encoding="utf-8").splitlines()
    del lines[1]
    _rewrite(path, lines)

    report = verify_chain(path)

    assert report.ok is False
    # The row that used to follow row 1 now carries row 1's hash as its link,
    # so it fails the link check against row 0 before its own seq is examined.
    assert report.reason == "prev_hash_mismatch"
    assert report.first_bad_seq == 2
    assert report.n_entries == 2


def test_dropping_the_first_row_is_caught_by_the_genesis_link(tmp_path: Path) -> None:
    path = tmp_path / "ledger.jsonl"
    for index in range(3):
        append_entry(path, {"artifact": f"a{index}"})

    lines = path.read_text(encoding="utf-8").splitlines()
    del lines[0]
    _rewrite(path, lines)

    report = verify_chain(path)

    assert report.ok is False
    assert report.reason == "prev_hash_mismatch"
    assert report.first_bad_seq == 1
    assert report.n_entries == 1


def test_renumbered_row_is_reported_as_seq_gap(tmp_path: Path) -> None:
    path = tmp_path / "ledger.jsonl"
    for index in range(3):
        append_entry(path, {"artifact": f"a{index}"})

    lines = path.read_text(encoding="utf-8").splitlines()
    # The hash covers the payload and the link but not ``seq``, so a row that is
    # renumbered in place is invisible to the hash check and only the seq column
    # reveals it — which is exactly why verification checks it separately.
    tampered = json.loads(lines[2])
    tampered["seq"] = 7
    lines[2] = json.dumps(tampered)
    _rewrite(path, lines)

    report = verify_chain(path)

    assert report.ok is False
    assert report.reason == "seq_gap"
    assert report.first_bad_seq == 7
    assert report.n_entries == 3


def test_truncated_tail_row_is_malformed_without_raising(tmp_path: Path) -> None:
    path = tmp_path / "ledger.jsonl"
    for index in range(3):
        append_entry(path, {"artifact": f"a{index}"})
    with path.open("a", encoding="utf-8") as handle:
        handle.write('{"seq": 3, "prev_hash": "deadbeef", "payl')  # torn write

    report = verify_chain(path)

    assert report.ok is False
    assert report.reason == "malformed_row"
    assert report.first_bad_seq == 3
    assert report.n_entries == 4


def test_a_line_that_is_not_a_row_is_malformed(tmp_path: Path) -> None:
    path = tmp_path / "ledger.jsonl"
    path.write_text("not a row at all\n", encoding="utf-8")

    report = verify_chain(path)

    assert report.reason == "malformed_row"
    assert report.first_bad_seq == 0
    assert report.n_entries == 1


# ---------------------------------------------------------------------------
# Recovery from a torn write
# ---------------------------------------------------------------------------


def test_append_after_a_torn_tail_links_to_the_last_complete_row(tmp_path: Path) -> None:
    path = tmp_path / "ledger.jsonl"
    append_entry(path, {"artifact": "a0"})
    append_entry(path, {"artifact": "a1"})
    good_hash = _read_rows(path)[1]["hash"]
    with path.open("a", encoding="utf-8") as handle:
        handle.write('{"seq": 2, "prev_hash": "partial')  # no trailing newline

    new_hash = append_entry(path, {"artifact": "a2"})

    raw_lines = path.read_text(encoding="utf-8").splitlines()
    assert len(raw_lines) == 4  # the torn fragment is still its own line
    rows = _parsable_rows(path)
    assert [row["seq"] for row in rows] == [0, 1, 2]
    assert rows[2]["prev_hash"] == good_hash
    assert rows[2]["hash"] == new_hash
    # The fragment was NOT silently deleted: the ledger stays honest and the
    # operator is told to look at it rather than being handed a clean verdict.
    assert verify_chain(path).reason == "malformed_row"


# ---------------------------------------------------------------------------
# Report contract
# ---------------------------------------------------------------------------


def test_report_rejects_a_reason_outside_the_closed_vocabulary() -> None:
    with pytest.raises(ValueError, match="closed vocabulary"):
        ChainReport(ok=False, n_entries=1, first_bad_seq=0, reason="bitrot")


def test_report_rejects_a_failure_without_a_reason() -> None:
    with pytest.raises(ValueError, match="must carry a reason"):
        ChainReport(ok=False, n_entries=1, first_bad_seq=0)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def test_cli_verify_audit_exits_zero_on_an_intact_chain(tmp_path: Path) -> None:
    from click.testing import CliRunner

    from finrobot.cli import cli

    path = tmp_path / "ledger.jsonl"
    append_entry(path, {"artifact": "a0"})
    append_entry(path, {"artifact": "a1"})

    result = CliRunner().invoke(cli, ["verify-audit", "--path", str(path)])

    assert result.exit_code == 0
    assert "OK" in result.output
    assert "2 entries" in result.output


def test_cli_verify_audit_exits_one_on_a_broken_chain(tmp_path: Path) -> None:
    from click.testing import CliRunner

    from finrobot.cli import cli

    path = tmp_path / "ledger.jsonl"
    append_entry(path, {"artifact": "a0"})
    append_entry(path, {"artifact": "a1"})
    lines = path.read_text(encoding="utf-8").splitlines()
    tampered = json.loads(lines[0])
    tampered["payload"]["artifact"] = "forged"
    lines[0] = json.dumps(tampered)
    _rewrite(path, lines)

    result = CliRunner().invoke(cli, ["verify-audit", "--path", str(path)])

    assert result.exit_code == 1
    assert "hash_mismatch" in result.output
