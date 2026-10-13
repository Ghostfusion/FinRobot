"""Numeric-audit verifier: the data layer's own record of WHO supplied each number.

The canonical snapshot publishes ONE value per metric, but the data layer saw
several vendors. Reconciliation (`engine/models/metric_authority.py` +
`engine/data/authority.py`) selects the canonical value and records every
alternative, whether it was eligible, and why — that record rides the snapshot
into the artifact as ``raw_data["data_authority"]``. Nothing on the report
surfaced it: a reader could not tell that the printed revenue sat 18% above the
second vendor's, or that a metric failed closed and shipped no value at all.

This verifier turns that record into audit findings — one per decision that is
NOT clean (``conflict`` / ``unavailable`` / ``definition_mismatch``) — at
``review``. It NEVER withholds: the canonical value is already published, which
is exactly what the conflict is measured against, so the finding annotates
(artifact ``caveated``) and the number ships. A metric that failed closed already
shows "not available"; the finding names the reason.

Everything is read from the frozen artifact's ``raw_data`` — no provider call, no
LLM, no re-derivation.
"""

from __future__ import annotations

from typing import Any

from finrobot.engine.models.numeric_claim import Finding

# Decision statuses that are not clean, mapped to their stable check id. Clean
# statuses (``accepted`` / ``fallback``) never produce a finding: a fallback is a
# disclosed, deliberate selection, not a defect.
_STATUS_CHECK: dict[str, str] = {
    "conflict": "metric_authority_conflict",
    "unavailable": "metric_authority_unavailable",
    "definition_mismatch": "metric_authority_definition_mismatch",
}


def _fmt_value(value: Any) -> str:
    """Render a value for the evidence line; ``None`` (a fail-closed metric) is ``n/a``."""
    if isinstance(value, bool) or value is None:
        return "n/a"
    if isinstance(value, (int, float)):
        return f"{value:,.2f}"
    return str(value)


def _fmt_deviation(candidate: dict[str, Any]) -> str:
    """The candidate's distance from the selected value: relative %, else absolute,
    else its own loss reason (an ineligible candidate was never compared)."""
    dev = candidate.get("deviation_pct")
    if isinstance(dev, (int, float)) and not isinstance(dev, bool):
        return f"{dev:.1%}"
    abs_dev = candidate.get("deviation_abs")
    if isinstance(abs_dev, (int, float)) and not isinstance(abs_dev, bool):
        return f"{abs_dev:,.2f}"
    reason = candidate.get("reason_code")
    return str(reason) if reason else "n/a"


def _candidate_line(candidate: dict[str, Any]) -> str:
    return f"{candidate.get('source')} {_fmt_value(candidate.get('value'))} ({_fmt_deviation(candidate)})"


def _evidence(decision: dict[str, Any], status: str, policy_version: str) -> str:
    """Name the metric, the selected source + value, every differing candidate
    (source / value / deviation), the loss reason and the policy version."""
    metric = str(decision.get("metric") or "")
    reason = str(decision.get("reason_code") or "")
    selected_source = decision.get("selected_source")
    selected = selected_source if isinstance(selected_source, str) and selected_source else None

    candidates = decision.get("candidates")
    candidates = candidates if isinstance(candidates, list) else []
    shown = [
        _candidate_line(candidate)
        for candidate in candidates
        if isinstance(candidate, dict) and candidate.get("source") != selected
    ]

    parts = [f"{metric}: {status} ({reason})"]
    if selected is not None:
        parts.append(f"selected {selected} {_fmt_value(decision.get('value'))}")
    if shown:
        lead = "vs" if selected is not None else "considered"
        parts.append(f"{lead} " + ", ".join(shown))
    parts.append(f"policy {policy_version}")
    return "; ".join(parts)


def metric_authority_findings(raw_data: dict[str, Any]) -> list[Finding]:
    """Findings for every non-clean decision in the snapshot's reconciliation record.

    Reads only ``raw_data["data_authority"]`` — the serialised
    ``ReconciliationReport`` the data layer attached to the ``FinancialData``
    snapshot. Returns ``[]`` when the block is absent (a legacy snapshot built
    before reconciliation ran), empty, or malformed; never raises.
    """
    block = raw_data.get("data_authority") if isinstance(raw_data, dict) else None
    if not isinstance(block, dict):
        return []
    decisions = block.get("decisions")
    if not isinstance(decisions, list):
        return []
    block_policy = block.get("policy_version")

    findings: list[Finding] = []
    for decision in decisions:
        if not isinstance(decision, dict):
            continue
        status = decision.get("status")
        if not isinstance(status, str):
            continue
        check = _STATUS_CHECK.get(status)
        if check is None:
            continue
        metric = str(decision.get("metric") or "")
        policy = decision.get("policy_version") or block_policy or ""
        findings.append(
            Finding(
                field_key=f"data_authority.{metric}",
                check=check,
                severity="review",
                evidence=_evidence(decision, status, str(policy)),
            )
        )
    return findings


def attach_metric_authority_findings(
    structured_out: dict[str, Any], raw_data: dict[str, Any]
) -> list[str]:
    """Append the reconciliation findings to ``structured_out["numeric_audit"]``.

    The single wiring entry point for the artifact builder. Appends the findings
    in the same shape every other verifier's findings take, rolls the artifact
    status up to ``caveated`` (a ``review`` finding annotates, it never withholds),
    and returns the ``[NUMERIC-AUDIT/...]`` warning lines. No-op (returns ``[]``)
    when the numeric-audit block is absent, the snapshot carries no
    ``data_authority`` record, or every decision is clean.
    """
    audit = structured_out.get("numeric_audit")
    if not isinstance(audit, dict):
        return []
    findings = metric_authority_findings(raw_data)
    if not findings:
        return []
    existing = audit.get("findings")
    dumped: list[Any] = existing if isinstance(existing, list) else []
    known = {
        (entry.get("field_key"), entry.get("check")) for entry in dumped if isinstance(entry, dict)
    }
    warnings: list[str] = []
    for finding in findings:
        if (finding.field_key, finding.check) in known:
            continue
        dumped.append(finding.model_dump(mode="json"))
        audit["artifact_status"] = "caveated"
        warnings.append(
            f"[NUMERIC-AUDIT/{finding.severity}] {finding.field_key} "
            f"({finding.check}): {finding.evidence}"
        )
    audit["findings"] = dumped
    return warnings
