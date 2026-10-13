"""CoverageStore (coverage/sqlite_store.py) — persistence round-trips.

The store now exposes only the single ``Studied Tickers`` workspace: the
system group is the sole creation primitive (``get_or_create_system_group``);
members are added via ``add_members``, removed via ``remove_members``, and read
back via ``get_group`` / ``get_system_group`` / ``list_groups``. There is no
multi-group management (create / rename / delete of groups).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from finrobot.coverage.sqlite_store import CoverageStore


@pytest.fixture
async def store(tmp_path: Path):
    s = CoverageStore(db_path=tmp_path / "coverage.db")
    yield s
    await s.close()


async def test_get_or_create_and_get_group(store: CoverageStore) -> None:
    g = await store.get_or_create_system_group("Studied Tickers", "My research universe")
    assert g.id.startswith("cov_")
    assert g.name == "Studied Tickers"
    assert g.is_system is True

    fetched = await store.get_group(g.id)
    assert fetched is not None
    assert fetched.name == "Studied Tickers"
    assert fetched.description == "My research universe"
    assert fetched.members == []


async def test_get_missing_group_returns_none(store: CoverageStore) -> None:
    assert await store.get_group("cov_nope") is None


async def test_add_members_upper_cased_and_idempotent(store: CoverageStore) -> None:
    g = await store.get_or_create_system_group("Studied Tickers")
    await store.add_members(g.id, ["nvda", "AMD"])
    detail = await store.add_members(g.id, ["nvda"])  # dup → no-op
    assert detail is not None
    tickers = sorted(m.ticker for m in detail.members)
    assert tickers == ["AMD", "NVDA"]


async def test_add_members_to_missing_group_returns_none(store: CoverageStore) -> None:
    assert await store.add_members("cov_nope", ["AAPL"]) is None


# ── remove_members ───────────────────────────────────────────────────────────


async def test_remove_members_removes_only_named_and_reports_count(
    store: CoverageStore,
) -> None:
    g = await store.get_or_create_system_group("Studied Tickers")
    await store.add_members(g.id, ["AAPL", "MSFT", "NVDA"])

    removed = await store.remove_members(g.id, ["AAPL"])

    assert removed == 1
    detail = await store.get_group(g.id)
    assert detail is not None
    assert sorted(m.ticker for m in detail.members) == ["MSFT", "NVDA"]


async def test_remove_members_dedupes_and_upper_cases(store: CoverageStore) -> None:
    g = await store.get_or_create_system_group("Studied Tickers")
    await store.add_members(g.id, ["AAPL", "MSFT"])

    # One symbol passed twice, lower-cased — de-duplicated to a single row.
    assert await store.remove_members(g.id, ["aapl", "AAPL"]) == 1

    detail = await store.get_group(g.id)
    assert detail is not None
    assert [m.ticker for m in detail.members] == ["MSFT"]


async def test_remove_members_non_member_is_a_noop(store: CoverageStore) -> None:
    g = await store.get_or_create_system_group("Studied Tickers")
    await store.add_members(g.id, ["MSFT"])

    assert await store.remove_members(g.id, ["AAPL"]) == 0

    detail = await store.get_group(g.id)
    assert detail is not None
    assert [m.ticker for m in detail.members] == ["MSFT"]


async def test_remove_members_unknown_group_returns_zero(store: CoverageStore) -> None:
    assert await store.remove_members("cov_nope", ["AAPL"]) == 0


async def test_list_groups_carries_member_count(store: CoverageStore) -> None:
    g = await store.get_or_create_system_group("Studied Tickers")
    await store.add_members(g.id, ["AAPL", "MSFT"])
    groups = await store.list_groups()
    counts = {grp.name: grp.member_count for grp in groups}
    assert counts == {"Studied Tickers": 2}


async def test_count_groups(store: CoverageStore) -> None:
    assert await store.count_groups() == 0
    await store.get_or_create_system_group("Studied Tickers")
    # The single system group is find-or-create — a second call is a no-op.
    await store.get_or_create_system_group("Studied Tickers")
    assert await store.count_groups() == 1


async def test_system_group_flag_persists(store: CoverageStore) -> None:
    g = await store.get_or_create_system_group("Studied Tickers")
    fetched = await store.get_group(g.id)
    assert fetched is not None
    assert fetched.is_system is True


async def test_get_system_group_none_when_absent(store: CoverageStore) -> None:
    assert await store.get_system_group() is None


async def test_get_system_group_finds_seeded(store: CoverageStore) -> None:
    sys_g = await store.get_or_create_system_group("Studied Tickers")
    await store.add_members(sys_g.id, ["AAPL"])
    found = await store.get_system_group()
    assert found is not None
    assert found.id == sys_g.id
    assert found.is_system is True
    assert [m.ticker for m in found.members] == ["AAPL"]


async def test_get_or_create_system_group_idempotent(store: CoverageStore) -> None:
    # The safe entry point: concurrent/repeat cold-start calls resolve to the
    # single surviving row instead of raising or duplicating (BUG-088).
    a = await store.get_or_create_system_group("Studied Tickers", "desc")
    b = await store.get_or_create_system_group("Studied Tickers", "desc")
    assert a.id == b.id
    assert a.is_system is True
    # Exactly one system group ever — the partial unique index guarantees it.
    systems = [g for g in await store.list_groups() if g.is_system]
    assert len(systems) == 1


# ── Ownership ────────────────────────────────────────────────────────────────


async def test_owned_tickers_empty_by_default(store: CoverageStore) -> None:
    assert await store.owned_tickers() == set()


async def test_set_owned_upper_cases_and_returns_stored(store: CoverageStore) -> None:
    assert await store.set_owned("nflx", True) is True
    assert await store.owned_tickers() == {"NFLX"}


async def test_set_owned_upsert_toggles(store: CoverageStore) -> None:
    assert await store.set_owned("NFLX", True) is True
    # Re-setting the same ticker updates the flag rather than inserting a dup.
    assert await store.set_owned("nflx", False) is False
    assert await store.owned_tickers() == set()
    # And back on again.
    assert await store.set_owned("NFLX", True) is True
    assert await store.owned_tickers() == {"NFLX"}


async def test_owned_tickers_only_lists_owned(store: CoverageStore) -> None:
    await store.set_owned("AAPL", True)
    await store.set_owned("MSFT", True)
    await store.set_owned("TSLA", False)
    assert await store.owned_tickers() == {"AAPL", "MSFT"}


async def test_owned_persists_across_reopen(tmp_path: Path) -> None:
    first = CoverageStore(db_path=tmp_path / "coverage.db")
    await first.set_owned("AAPL", True)
    await first.close()
    reopened = CoverageStore(db_path=tmp_path / "coverage.db")
    try:
        assert await reopened.owned_tickers() == {"AAPL"}
    finally:
        await reopened.close()
