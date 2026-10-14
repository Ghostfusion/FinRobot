"""The withhold-reason vocabulary (design §9.6).

A code is a stable public identifier and a ``(reason_code, domain)`` pair names exactly one
logical cause, so these tests defend the two things that would let a second name for one cause
appear: the code's shape, and the vocabulary being the only place a code is spelled.
"""

from __future__ import annotations

import re

import pytest

from finrobot.engine.models.withhold_reason import (
    WITHHOLD_CODES,
    WithholdReason,
    as_withhold_reason,
    withhold_reason,
)


def test_every_declared_code_matches_the_shape_section_9_6_fixes() -> None:
    """UPPER_SNAKE_CASE, ≤63 characters — a reader's audit trail may key on it, so the shape is a
    contract with everything downstream, not a style preference."""
    assert WITHHOLD_CODES  # the vocabulary is not empty
    for code, domain in WITHHOLD_CODES.items():
        assert re.fullmatch(r"[A-Z][A-Z0-9_]+[A-Z0-9]", code), code
        assert len(code) <= 63, code
        assert domain, code


def test_a_code_cannot_be_reused_across_domains() -> None:
    """One code, one domain: the pair is the identity, so a code filed under two subsystems would
    make ``(reason_code, domain)`` stop naming one cause."""
    seen: dict[str, str] = {}
    for code, domain in WITHHOLD_CODES.items():
        assert seen.setdefault(code, domain) == domain


def test_building_a_reason_checks_the_code_against_the_vocabulary() -> None:
    """A code spelled at a call site is how one cause gets two names, so an undeclared one is an
    error rather than a new code."""
    with pytest.raises(ValueError, match="not a declared withhold reason code"):
        withhold_reason("NOT_A_DECLARED_CODE")

    reason = withhold_reason("TARGET_OUT_OF_BAND", metadata={"clause_ids": "C1"})
    assert reason.reason_code == "TARGET_OUT_OF_BAND"
    assert reason.domain == "contract"  # taken from the declaration, not restated by the caller
    assert reason.metadata == {"clause_ids": "C1"}


def test_building_a_reason_refuses_a_domain_that_contradicts_the_declaration() -> None:
    with pytest.raises(ValueError, match="one cause"):
        withhold_reason("TARGET_OUT_OF_BAND", domain="audit")
    # The declared domain is accepted explicitly, which is what a producer migrating a code does.
    assert withhold_reason("TARGET_OUT_OF_BAND", domain="contract").domain == "contract"


class TestCodeShape:
    @pytest.mark.parametrize("code", ["lower_case", "1LEADING_DIGIT", "TRAILING_", "HAS SPACE", ""])
    def test_a_malformed_code_is_rejected(self, code: str) -> None:
        with pytest.raises(ValueError, match="reason_code must match"):
            WithholdReason(reason_code=code, domain="contract")

    def test_an_over_long_code_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="reason_code must match"):
            WithholdReason(reason_code="A" * 64, domain="contract")


class TestReading:
    def test_the_model_and_the_stored_dict_are_the_same_fact(self) -> None:
        """A producer writes the model into the in-memory payload; pydantic serialises it on save,
        so a stored payload reads back as a dict. A consumer must accept both or it loses the
        reason on one side of the boundary — §9.6's own failure mode, arriving via a type."""
        model = withhold_reason("VALUATION_DIAL_WITHHELD")
        stored = model.model_dump()

        assert as_withhold_reason(model) == model
        assert as_withhold_reason(stored) == model

    def test_anything_else_reads_as_no_reason(self) -> None:
        assert as_withhold_reason(None) is None
        assert as_withhold_reason("valuation_synthesis_dial") is None  # the legacy STRING
        assert as_withhold_reason({"reason_code": "lowercase", "domain": "contract"}) is None
        assert as_withhold_reason({"domain": "contract"}) is None
