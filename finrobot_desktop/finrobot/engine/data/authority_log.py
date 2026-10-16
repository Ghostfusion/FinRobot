"""Append-only cross-run log of metric-authority decisions.

WHY this exists: the per-run :class:`ReconciliationReport` rides the canonical
contract into one artifact, but the question "how often do two vendors disagree on
``revenue``, and between which pair?" is *cross-run* — it needs history, not one
snapshot. One append-only JSONL file per symbol — ``<root>/<SYMBOL>.jsonl`` — with
one JSON object per fetch, never rewritten. Appending only means a reader can never
observe a torn update of an existing row, and the file is a full audit trail of what
the reconciler decided and when.

One file per symbol mirrors :mod:`finrobot.engine.data.pit_store`: the same
path/root discipline (a call-time default root so tests can monkeypatch the home
directory and ``ensure_home()`` runs before the first write; never read an
environment variable directly) and the same "skip a malformed line, never lose the
good rows above it" read policy.

Failure policy: writing is BEST-EFFORT. A decision log is diagnostic, never a
correctness dependency, so :func:`record_decisions` swallows exactly ``OSError`` /
``ValueError`` / ``TypeError`` (the failures a filesystem or a JSON serializer
raises) and never propagates — a full disk must not fail a research run. Any other
exception type is not expected and is left to surface.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from finrobot.engine.models.metric_authority import (
    MetricCandidate,
    MetricDecision,
    ReconciliationReport,
)

logger = logging.getLogger(__name__)

__all__ = ["default_authority_root", "disagreement_summary", "record_decisions"]


def default_authority_root() -> Path:
    """Where the running system keeps its metric-authority decision logs.

    Resolved at *call* time for the same reason ``pit_store.default_pit_root`` is:
    the home directory is relocatable (tests monkeypatch it) and ``ensure_home()``
    must run before the first write. Never reads an env var — the home path is the
    one source of truth.
    """
    from finrobot.paths import ensure_home

    root = ensure_home() / "metric_authority"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _safe_stem(symbol: str) -> str:
    """The symbol as an uppercase file stem, refusing anything that could escape root.

    Mirrors ``pit_store._validate_symbol``: ``..``/separators would let one symbol
    append to another file (or outside ``root``); a ``:`` is a drive-relative path on
    Windows; a NUL truncates the name; surrounding whitespace makes a stem nobody can
    find again.
    """
    if (
        not symbol
        or symbol in {".", ".."}
        or any(char in symbol for char in ("/", "\\", ":", "\x00"))
        or symbol.strip() != symbol
    ):
        raise ValueError(f"invalid authority_log symbol {symbol!r}")
    return symbol.upper()


def _candidate_to_dict(candidate: MetricCandidate) -> dict[str, object]:
    return {
        "source": candidate.source,
        "value": candidate.value,
        "eligible": candidate.eligible,
        "deviation_pct": candidate.deviation_pct,
        "deviation_abs": candidate.deviation_abs,
        "reason_code": candidate.reason_code,
        "non_independent": candidate.non_independent,
        # The instant this candidate's value is stamped for (``None`` = the payload
        # stamped none), so a logged disagreement stays readable as "different
        # number" vs "different measurement" after the fact.
        "period_end": candidate.period_end.isoformat() if candidate.period_end else None,
        "period_basis": candidate.period_basis,
    }


def _decision_to_dict(decision: MetricDecision) -> dict[str, object]:
    return {
        "metric": decision.metric,
        "status": decision.status,
        "value": decision.value,
        "unit": decision.unit,
        "currency": decision.currency,
        "selected_source": decision.selected_source,
        "is_authoritative": decision.is_authoritative,
        # The typed measurement (design §6): what kind of provenance this value has, so a
        # consumer switches on `kind` instead of re-inferring it from `is_authoritative`.
        "measure": decision.measure.model_dump(mode="json") if decision.measure else None,
        "reason_code": decision.reason_code,
        "policy_version": decision.policy_version,
        "definition_version": decision.definition_version,
        "comparability": decision.comparability,
        "tolerance_pct": decision.tolerance_pct,
        "tolerance_abs": decision.tolerance_abs,
        "disagreement_pct": decision.disagreement_pct,
        "period_end": decision.period_end.isoformat() if decision.period_end else None,
        "period_basis": decision.period_basis,
        "agreement_is_independent": decision.agreement_is_independent,
        "candidates": [_candidate_to_dict(candidate) for candidate in decision.candidates],
    }


def _report_to_dict(ticker: str, report: ReconciliationReport) -> dict[str, object]:
    return {
        "ticker": ticker,
        "policy_version": report.policy_version,
        "run_as_of": report.run_as_of.isoformat() if report.run_as_of is not None else None,
        "clock": report.clock.isoformat(),
        "decisions": [_decision_to_dict(decision) for decision in report.decisions],
    }


def record_decisions(
    ticker: str, report: ReconciliationReport, *, root: Path | None = None
) -> None:
    """Append ``report`` for ``ticker`` as one JSON object line. Never raises.

    Best-effort by design: the log is diagnostic, so a filesystem or serialization
    failure is swallowed (``OSError`` / ``ValueError`` / ``TypeError`` only) rather
    than failing the fetch that produced the report.
    """
    try:
        stem = _safe_stem(ticker)
        base = root if root is not None else default_authority_root()
        path = base / f"{stem}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(_report_to_dict(stem, report), ensure_ascii=False)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    except (OSError, ValueError, TypeError):
        logger.warning("authority_log: could not record decisions for %s", ticker, exc_info=True)


def _parse_row(line: str) -> dict[str, object] | None:
    """One JSON-object row, or ``None`` for a line to skip (malformed / not a row)."""
    try:
        parsed: object = json.loads(line)
    except json.JSONDecodeError:
        logger.warning("authority_log: skipping malformed JSONL line")
        return None
    if not isinstance(parsed, dict):
        logger.warning("authority_log: skipping non-object JSONL line")
        return None
    return {str(key): value for key, value in parsed.items()}


def _read_rows(path: Path) -> list[dict[str, object]]:
    """Every parsable row in ``path``, in file order. Skipped/corrupt lines warned."""
    try:
        raw = path.read_bytes()
    except FileNotFoundError:
        return []
    except OSError:
        logger.warning("authority_log: cannot read decision file %s", path)
        return []
    rows: list[dict[str, object]] = []
    for line in raw.split(b"\n"):
        if not line.strip():
            continue
        # Decode per line with replacement: a crash mid-append can truncate a
        # multi-byte character, and a strict decode would sink the whole file over
        # one torn line. The line then simply fails to parse and is skipped.
        row = _parse_row(line.decode("utf-8", errors="replace"))
        if row is not None:
            rows.append(row)
    return rows


def _conflict_pairs(row: dict[str, object]) -> list[tuple[str, str, float | None]]:
    """``(metric, provider-pair, deviation)`` for every over-tolerance conflict in a
    stored report row. The pair is the selected source and the disagreeing source,
    ordered so ``a|b`` and ``b|a`` bucket together."""
    decisions = row.get("decisions")
    if not isinstance(decisions, list):
        return []
    pairs: list[tuple[str, str, float | None]] = []
    for decision in decisions:
        if not isinstance(decision, dict) or decision.get("status") != "conflict":
            continue
        metric = decision.get("metric")
        selected = decision.get("selected_source")
        candidates = decision.get("candidates")
        if not isinstance(metric, str) or not isinstance(selected, str):
            continue
        if not isinstance(candidates, list):
            continue
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            if candidate.get("reason_code") != "above_tolerance_published_flagged":
                continue
            source = candidate.get("source")
            if not isinstance(source, str):
                continue
            pair = "|".join(sorted((selected, source)))
            deviation = candidate.get("deviation_pct")
            dev = float(deviation) if isinstance(deviation, (int, float)) else None
            pairs.append((metric, pair, dev))
    return pairs


def disagreement_summary(root: Path | None = None, *, limit: int = 20) -> list[dict[str, object]]:
    """Top metric + provider-pair conflict counts across every logged run.

    Rows are ``{"metric", "sources", "count", "max_deviation_pct"}`` sorted by
    descending count, then metric, then source pair — deterministic, so two reads of
    the same log give the same summary. ``limit`` caps the returned rows (``<= 0``
    returns none).
    """
    base = root if root is not None else default_authority_root()
    counts: dict[tuple[str, str], int] = {}
    widest: dict[tuple[str, str], float] = {}
    try:
        paths = sorted(base.glob("*.jsonl"))
    except OSError:
        logger.warning("authority_log: cannot list decision dir %s", base)
        return []
    for path in paths:
        for row in _read_rows(path):
            for metric, pair, deviation in _conflict_pairs(row):
                key = (metric, pair)
                counts[key] = counts.get(key, 0) + 1
                if deviation is not None:
                    prior = widest.get(key)
                    widest[key] = deviation if prior is None else max(prior, deviation)
    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0][0], item[0][1]))
    summary: list[dict[str, object]] = []
    for (metric, pair), count in ordered[:limit]:
        summary.append(
            {
                "metric": metric,
                "sources": pair,
                "count": count,
                "max_deviation_pct": widest.get((metric, pair)),
            }
        )
    return summary
