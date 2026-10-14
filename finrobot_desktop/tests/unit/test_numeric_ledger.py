"""The artifact-layer numeric ledger (design §6).

The ledger's contract: one claim per field a verifier filed against, the findings grouped
under it, and whatever the payload DECLARES about the number — provenance, basis, proxy
status, lineage. It never invents a value or a basis; the tests below pin both halves, and
pin the absence too (a key the payload cannot resolve keeps its findings and reports
``value=None``, which is the fact a consumer needs).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from finrobot.artifact.models import (
    Artifact,
    ArtifactAssumptions,
    ArtifactComputeVersion,
    ArtifactInputs,
    ArtifactMeta,
    ArtifactOutputs,
)
from finrobot.artifact.numeric_ledger import build_numeric_ledger

_TS = datetime(2026, 6, 8, tzinfo=UTC)


def _artifact(*, structured: dict, raw_data: dict | None = None) -> Artifact:
    return Artifact(
        id="art_2026-06-08T00:00:00_MU_equity_research",
        ticker="MU",
        cross_tickers=[],
        type="equity_research",
        inputs=ArtifactInputs(data_source="yfinance", data_fetched_at=_TS, raw_data=raw_data or {}),
        assumptions=ArtifactAssumptions(parameters={}),
        compute_version=ArtifactComputeVersion(version="0.1.0", formula_id="x"),
        outputs=ArtifactOutputs(structured=structured),
        meta=ArtifactMeta(created_at=_TS, source="pipeline:equity_research", user_id="local"),
    )


def _with_decisions(decisions: list[dict], **extra: dict) -> dict:
    """A payload with a data-authority record: the runtime half of the provenance."""
    return {
        "income": {"ebitda": 302_293_000.0, "operating_margin": 0.208},
        "provenance": {"provider": "yfinance", "as_of": "2026-06-30", "period_basis": "ttm"},
        "data_authority": {"decisions": decisions, "run_as_of": "2026-10-14"},
        **extra,
    }


def _decision(metric: str, **over: object) -> dict:
    base = {
        "metric": metric,
        "status": "accepted",
        "value": 302_293_000.0,
        "unit": "USD",
        "currency": "USD",
        "selected_source": "yfinance",
        "is_authoritative": True,
        "reason_code": "single_source",
        "policy_version": "metric_authority_v1",
        "definition_version": f"{metric}_1",
        "basis": f"operating-caliber {metric} = ...",
    }
    base.update(over)
    return base


class TestGrouping:
    def test_one_claim_per_field_that_carries_a_finding(self):
        """Both finding sources land in one vocabulary: the artifact's stored numeric-audit
        rows AND the contract clauses, re-run exactly as the badge re-runs them."""
        art = _artifact(
            structured={
                "numeric_audit": {
                    "artifact_status": "caveated",
                    "findings": [
                        {
                            "field_key": "enterprise_value",
                            "check": "ev_bridge_unverified",
                            "severity": "review",
                            "evidence": "preferred stock not reported",
                        }
                    ],
                },
            }
        )
        ledger = build_numeric_ledger(art)
        keys = [c.field_key for c in ledger]
        assert keys == sorted(keys)  # deterministic order, not dict order
        assert "enterprise_value" in keys

    def test_findings_group_under_their_field(self):
        art = _artifact(
            structured={
                "numeric_audit": {
                    "artifact_status": "caveated",
                    "findings": [
                        {
                            "field_key": "enterprise_value",
                            "check": "a",
                            "severity": "review",
                            "evidence": "first",
                        },
                        {
                            "field_key": "enterprise_value",
                            "check": "b",
                            "severity": "info",
                            "evidence": "second",
                        },
                    ],
                },
            }
        )
        (claim,) = build_numeric_ledger(art)
        assert [f.check for f in claim.findings] == ["a", "b"]
        # The rollup the numeric-audit path already defines, now per claim.
        assert claim.field_status == "review"

    def test_a_contract_clause_finding_is_a_claim_too(self):
        art = _artifact(
            structured={
                "thesis": {"recommendation": "HOLD"},
                "valuation_synthesis": {
                    "methods": [{"name": "ev_ebitda"}],
                    "cross_checks": [
                        {"name": "ev_ebitda_band", "low": 10.44, "mid": 49.07, "high": 80.35}
                    ],
                    "current_price": 55.14,
                    "degradation_note": "single method with no cross-validation.",
                },
            }
        )
        ledger = build_numeric_ledger(art)
        c6b = [c for c in ledger if c.field_key == "valuation_synthesis.degradation_note"]
        assert len(c6b) == 1
        assert [f.check for f in c6b[0].findings] == ["contract_c6b_note_vs_cross_checks"]

    def test_an_artifact_with_no_findings_has_an_empty_ledger(self):
        assert build_numeric_ledger(_artifact(structured={})) == []


class TestDeclaredProvenance:
    def test_the_decision_supplies_basis_source_period_and_lineage(self):
        art = _artifact(
            structured={
                "numeric_audit": {
                    "artifact_status": "caveated",
                    "findings": [
                        {
                            "field_key": "data_authority.ebitda",
                            "check": "caliber_divergent",
                            "severity": "review",
                            "evidence": "operands of different calibers",
                        }
                    ],
                }
            },
            raw_data=_with_decisions([_decision("ebitda")]),
        )
        claim = {c.field_key: c for c in build_numeric_ledger(art)}["data_authority.ebitda"]
        assert claim.value == 302_293_000.0
        assert claim.source == "yfinance"
        assert claim.currency == "USD"
        assert claim.period == "TTM"  # from provenance.period_basis (nothing registered this key)
        assert claim.as_of == "2026-06-30"
        assert claim.basis == "operating-caliber ebitda = ..."
        assert claim.derivation == [
            "source:yfinance",
            "definition:ebitda_1",
            "policy:metric_authority_v1",
        ]
        assert claim.is_proxy is False

    def test_a_non_authoritative_decision_is_declared_a_proxy(self):
        """§6's Proxy: the record itself says no wired source owns the metric."""
        art = _artifact(
            structured={
                "numeric_audit": {
                    "artifact_status": "caveated",
                    "findings": [
                        {
                            "field_key": "data_authority.ebitda",
                            "check": "x",
                            "severity": "review",
                            "evidence": "e",
                        }
                    ],
                }
            },
            raw_data=_with_decisions(
                [
                    _decision(
                        "ebitda",
                        is_authoritative=False,
                        reason_code="owner_absent_alternative_selected",
                    )
                ]
            ),
        )
        claim = {c.field_key: c for c in build_numeric_ledger(art)}["data_authority.ebitda"]
        assert claim.is_proxy is True
        assert claim.source == "yfinance"

    def test_a_field_basis_sibling_is_read_when_no_decision_exists(self):
        """``thesis.price_target`` declares its basis in the report's own field — the same
        string the cover prints (``price_target_basis``). The claim exists because a finding
        named the field: a claim is never conjured for a field nothing filed against."""
        art = _artifact(
            structured={
                "thesis": {"price_target": None, "price_target_basis": "comps_pe 36.9x → $2172"},
                "valuation_withheld": True,
                "withheld_reason": "contract_C7",
                "numeric_audit": {
                    "artifact_status": "caveated",
                    "findings": [
                        {
                            "field_key": "thesis.price_target",
                            "check": "target_multiple_outside_band",
                            "severity": "review",
                            "evidence": "implied 17.7x vs the issuer's own band",
                        }
                    ],
                },
            }
        )
        ledger = {c.field_key: c for c in build_numeric_ledger(art)}
        claim = ledger["thesis.price_target"]
        assert claim.basis == "comps_pe 36.9x → $2172"
        # A withheld target is not a number; the claim keeps the finding, not a value.
        assert claim.value is None
        assert claim.is_proxy is False
        assert claim.derivation == []

    def test_a_declared_proxy_is_read_through_the_declaration(self, caplog):
        """The typed declaration wins over the legacy inference: the claim is a proxy, its basis
        IS the disclosure the reader is owed, and its value is taken through ``use_proxy`` — so
        the acknowledgement is logged rather than assumed."""
        art = _artifact(
            structured={
                "numeric_audit": {
                    "artifact_status": "caveated",
                    "findings": [
                        {
                            "field_key": "data_authority.ebitda",
                            "check": "x",
                            "severity": "review",
                            "evidence": "e",
                        }
                    ],
                }
            },
            raw_data=_with_decisions(
                [
                    _decision(
                        "ebitda",
                        is_authoritative=False,
                        measure={
                            "kind": "proxy",
                            "value": 302_293_000.0,
                            "proxy_of": "ebitda",
                            "disclosure": "published from yfinance although no wired source owns ebitda",
                        },
                    )
                ]
            ),
        )
        with caplog.at_level(logging.WARNING):
            claim = {c.field_key: c for c in build_numeric_ledger(art)}["data_authority.ebitda"]

        assert claim.is_proxy is True
        assert claim.basis == "published from yfinance although no wired source owns ebitda"
        assert claim.value == 302_293_000.0
        assert "artifact.numeric_ledger" in caplog.text  # the acknowledgement

    def test_a_legacy_decision_without_a_measure_still_reads_the_same_proxy(
        self,
    ):
        """Decisions stored before the measure shipped carry none, so the same signal is read
        from ``is_authoritative`` — the archive is never rewritten (§9.3)."""
        art = _artifact(
            structured={
                "numeric_audit": {
                    "artifact_status": "caveated",
                    "findings": [
                        {
                            "field_key": "data_authority.ebitda",
                            "check": "x",
                            "severity": "review",
                            "evidence": "e",
                        }
                    ],
                }
            },
            raw_data=_with_decisions([_decision("ebitda", is_authoritative=False)]),
        )
        claim = {c.field_key: c for c in build_numeric_ledger(art)}["data_authority.ebitda"]
        assert claim.is_proxy is True

    def test_nothing_declared_leaves_the_provenance_empty_rather_than_invented(self):
        art = _artifact(
            structured={
                "numeric_audit": {
                    "artifact_status": "caveated",
                    "findings": [
                        {
                            "field_key": "enterprise_value",
                            "check": "ev_bridge_unverified",
                            "severity": "review",
                            "evidence": "e",
                        }
                    ],
                }
            }
        )
        (claim,) = build_numeric_ledger(art)
        assert claim.basis is None
        assert claim.derivation == []
        assert claim.source is None
        assert claim.value is None
        # The finding is the reason the claim exists — never dropped for lack of provenance.
        assert len(claim.findings) == 1
