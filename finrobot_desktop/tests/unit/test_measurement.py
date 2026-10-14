"""The typed measurement (design §6).

Four facts about a number, and the type says which one holds: measured (Present), stood in for
(Proxy), refused (Withheld), or never obtained (Unavailable). The tests below pin the union's
discriminator, a Present's own provenance, and the one rule the type exists for — a Proxy's value
is read THROUGH ``use_proxy``, which records who took the substitution.
"""

from __future__ import annotations

import logging

from finrobot.engine.models.measurement import Present, Proxy, Unavailable, Withheld, use_proxy


def test_every_member_carries_its_own_kind() -> None:
    """The discriminator is what lets a payload and the TypeScript side switch exhaustively."""
    members = [
        (Present(value=1.0, source="TTM statement rows", period="TTM"), "present"),
        (Proxy(value=1.0, proxy_of="gross_margin", disclosure="a provider scalar"), "proxy"),
        (Withheld(reason_code="NO_OPERATING_INCOME_ROW", evidence="no numerator row"), "withheld"),
        (Unavailable(reason_code="NO_ELIGIBLE_OBSERVATION"), "unavailable"),
    ]
    for member, kind in members:
        assert member.kind == kind
        assert member.model_dump()["kind"] == kind  # survives the payload round-trip


def test_a_present_carries_its_own_provenance() -> None:
    present = Present(
        value=0.208,
        source="TTM statement frame rows",
        period="TTM",
        as_of="2026-06-30",
        derivation=["operating_income / revenue"],
    )
    assert present.value == 0.208
    assert present.source == "TTM statement frame rows"
    assert present.period == "TTM"
    assert present.derivation == ["operating_income / revenue"]


def test_use_proxy_returns_the_value_and_records_who_took_it(caplog) -> None:
    """The type's whole point: a consumer cannot get a Proxy's number without naming itself,
    and the disclosure it acknowledged goes to the log. A silent substitution leaves a trail."""
    proxy = Proxy(
        value=0.6854,
        proxy_of="gross_margin",
        disclosure="taken from the provider's info.grossMargins scalar",
    )
    with caplog.at_level(logging.WARNING):
        value = use_proxy(proxy, consumer="tests.unit.test_measurement")

    assert value == 0.6854
    assert "gross_margin" in caplog.text
    assert "info.grossMargins scalar" in caplog.text
    assert "tests.unit.test_measurement" in caplog.text
