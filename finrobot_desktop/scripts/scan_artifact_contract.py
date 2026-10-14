"""Nightly historical scan of the output-contract clauses over EVERY persisted
artifact (spec §6 step 5; §4.5 item 3 / Q3).

Walks the whole ~/.finrobot/artifacts.db, runs each contract clause's pure
``check()`` against every already-stored artifact, and reports — per clause — how
many artifacts in history today's clauses would flag for REVIEW. Two operational
uses:

  1. Before promoting a NEW clause to the live persist gate, quantify how much
     existing stock it would withhold — a clause that REVIEWs 40% of the back
     catalogue is over-broad and gets re-calibrated before it ever ships.
  2. Regression monitoring: a release that spikes the historical violation rate
     is an output-layer regression (the clause set drifted, or an extractor
     changed what the clause reads), caught here rather than in production.

READ-ONLY by construction. The artifact is fetched via the store's public read
API (``list_by_ticker`` + ``get``) and each clause's ``check(artifact)`` is a
PURE function (contract.py design contract: zero I/O, no mutation). The script
NEVER calls ``store.save`` / ``enforce_artifact_contract`` (which mutates) /
``delete`` / ``mark_viewed`` — nothing here writes the db back.

The per-flag rows are the human-review payload, shaped like a dbt
``store_failures`` table: one row per (clause, artifact) violation carrying the
identity + headline/basis snapshot + the clause's own evidence string, grouped
by clause so a reviewer reads one clause's full catch list at a time.

A third use is the archive half of the design's §9.3 decision: the contradicted
artifacts in the back catalogue are **left as they are** — no re-run, no delete, no
in-place edit — and the artifact page derives a badge from the stored payload at read
time. ``--badge`` prints exactly that derivation, one line per artifact, so the badge's
input is auditable and so a reviewer can see which stored artifacts a clause set WOULD
have withheld without touching a single record.

Usage:
    python scripts/scan_artifact_contract.py                # scan all, all clauses
    python scripts/scan_artifact_contract.py --clause C1    # only the C1 catch list
    python scripts/scan_artifact_contract.py --limit 50     # sample the newest 50
    python scripts/scan_artifact_contract.py --badge        # per-artifact read-time badge

The scan always measures the LIVE ``CONTRACT_CLAUSES``: the §7.1 staging area
(``artifact/proposed_clauses.py``) was folded into ``contract.py`` when the §4 closure
family was promoted on 2026-10-14, so there is no second universe to select between.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from dataclasses import dataclass

from finrobot.artifact.contract import CONTRACT_CLAUSES, ContractClause
from finrobot.artifact.models import Artifact, ArtifactSummary
from finrobot.artifact.store import ArtifactStore
from finrobot.artifact.summary_extractor import (
    extract_entry_price,
    extract_target_price,
    extract_verdict,
)

# list_by_ticker caps at ``limit`` rows; an unbounded scan must lift that cap
# above the real row count. count() is itself uncapped, so we derive the page
# size from the live total plus a generous margin — never a bare magic literal
# that silently truncates once the store grows past it.
_LIMIT_MARGIN = 1000


@dataclass(frozen=True)
class Flag:
    """One (clause, artifact) violation — a dbt ``store_failures`` row."""

    clause_id: str
    severity: str
    artifact_id: str
    artifact_type: str
    ticker: str | None
    entry_price: float | None
    target_price: float | None
    verdict: str | None
    evidence: str


async def _enumerate_artifacts(
    store: ArtifactStore, limit: int | None
) -> tuple[list[Artifact], dict[str, bool]]:
    """Every persisted artifact, newest first, INCLUDING archived ones.

    Returns the rehydrated artifacts AND the ``id -> archived`` map: ``archive``
    lives on the SUMMARY (``ArtifactSummary.archived``, a 24h-no-view staleness flag),
    not on the payload the clauses read, so it has to be carried alongside rather than
    found on the artifact.

    A historical scan must see the full back catalogue, so ``include_archived``
    is always True (archive is a UI-staleness flag, not a deletion — an archived
    artifact still shipped a headline and still counts toward "how much stock a
    clause would have caught"). ``list_by_ticker`` returns the lean summaries;
    ``get`` rehydrates the full payload the clauses read. When ``limit`` is set
    we sample only the newest N (list_by_ticker already orders created_at DESC);
    otherwise we lift the page cap above the live total via count().
    """
    if limit is not None:
        page = limit
    else:
        # Uncapped scan: page must exceed the true row count or list_by_ticker
        # silently drops the oldest rows past its LIMIT.
        page = await store.count(include_archived=True) + _LIMIT_MARGIN

    summaries: list[ArtifactSummary] = await store.list_by_ticker(
        include_archived=True, limit=max(page, 1)
    )

    artifacts: list[Artifact] = []
    archived: dict[str, bool] = {}
    for summary in summaries:
        artifact = await store.get(summary.id)
        if artifact is None:
            # Corrupt / unparseable payload — store.get already logged it. Skip
            # rather than crash the whole scan on one bad row.
            print(f"  [skip] {summary.id}: payload unreadable", file=sys.stderr)
            continue
        artifacts.append(artifact)
        archived[summary.id] = bool(summary.archived)
    return artifacts, archived


def _scan(artifacts: list[Artifact], clauses: list[ContractClause]) -> list[Flag]:
    """Run each clause's pure check over each artifact, collecting violations.

    Attributes every flag to the SPECIFIC clause that fired — which is why we
    call ``clause.check`` directly rather than ``enforce_artifact_contract``
    (the latter would (a) mutate and (b) collapse all hard violations into one
    withhold, losing per-clause attribution).
    """
    flags: list[Flag] = []
    for artifact in artifacts:
        for clause in clauses:
            finding = clause.check(artifact)
            if finding is None:
                continue
            flags.append(
                Flag(
                    clause_id=clause.id,
                    severity=clause.severity,
                    artifact_id=artifact.id,
                    artifact_type=artifact.type,
                    ticker=artifact.ticker,
                    entry_price=extract_entry_price(artifact),
                    target_price=extract_target_price(artifact),
                    verdict=extract_verdict(artifact),
                    evidence=finding.evidence,
                )
            )
    return flags


def _fmt_price(value: float | None) -> str:
    return f"${value:,.2f}" if value is not None else "—"


def _report(total: int, clauses: list[ContractClause], flags: list[Flag]) -> None:
    """Stdout report: scan summary, per-clause rate, then grouped catch lists."""
    print("=" * 78)
    print("Output-contract historical scan")
    print("=" * 78)
    print(f"artifacts scanned : {total}")
    print(f"clauses applied   : {', '.join(c.id for c in clauses) or '(none)'}")
    print(f"total flags       : {len(flags)}")
    print()

    if total == 0:
        print("No artifacts in store — nothing to scan.")
        return

    print("Per-clause flag rate")
    print("-" * 78)
    print(f"{'clause':<8}{'sev':<5}{'flags':>7}{'rate':>10}")
    for clause in clauses:
        count = sum(1 for f in flags if f.clause_id == clause.id)
        pct = 100.0 * count / total
        print(f"{clause.id:<8}{clause.severity:<5}{count:>7}{pct:>9.1f}%")
    print()

    if not flags:
        print("No clause flagged any artifact — the back catalogue is clean.")
        return

    print("Catch lists (human-review payload, grouped by clause)")
    print("=" * 78)
    for clause in clauses:
        clause_flags = [f for f in flags if f.clause_id == clause.id]
        if not clause_flags:
            continue
        # Name the RULE, not just its id: the title comes from the clause registry, so
        # the human-review payload reads the same words the registry will serve (§9.6).
        heading = f"{clause.id} — {clause.title}" if clause.title else clause.id
        print(f"\n── {heading} (severity {clause.severity}) — {len(clause_flags)} flag(s) ──")
        if clause.doc:
            print(f"   {clause.doc}")
        for flag in clause_flags:
            ticker = flag.ticker or "(cross)"
            print(f"  • {flag.artifact_id}")
            print(
                f"      type={flag.artifact_type}  ticker={ticker}  verdict={flag.verdict or '—'}"
            )
            print(
                f"      entry={_fmt_price(flag.entry_price)}  "
                f"target={_fmt_price(flag.target_price)}"
            )
            print(f"      evidence: {flag.evidence}")


def _badge_report(artifacts: list[Artifact], flags: list[Flag], archived: dict[str, bool]) -> None:
    """The read-time badge the artifact page renders, one line per artifact (§9.3).

    The locked decision for the back catalogue is *leave the record, annotate on read;
    never rewrite*: the contradicted artifacts keep their bytes and the page derives a
    badge from the payload. This is that derivation, transposed from the per-clause
    catch lists — because the badge's unit is the ARTIFACT, and because a reader needs
    to see which stored artifacts the current clause set WOULD have withheld (an `H`
    clause) as opposed to annotated (`S`), without a re-run, a delete or an edit.

    Order is the enumeration order (newest first), so the archive's shape reads at a
    glance: the old artifacts carry the badges, the new ones do not.
    """
    by_artifact: dict[str, list[Flag]] = {}
    for flag in flags:
        by_artifact.setdefault(flag.artifact_id, []).append(flag)

    withheld = sum(
        1 for art in artifacts if any(f.severity == "H" for f in by_artifact.get(art.id, ()))
    )
    annotated = sum(
        1
        for art in artifacts
        if by_artifact.get(art.id) and not any(f.severity == "H" for f in by_artifact[art.id])
    )
    print("=" * 78)
    print("Read-time artifact badge (design §9.3 — annotate on read, never rewrite)")
    print("=" * 78)
    print(f"artifacts scanned : {len(artifacts)}")
    print(f"would withhold    : {withheld}")
    print(f"would annotate    : {annotated}")
    print(f"clean             : {len(artifacts) - withheld - annotated}")
    print()
    print(f"{'artifact':<52}{'arch':<6}{'verdict':<8}{'badge'}")
    print("-" * 78)
    for art in artifacts:
        found = by_artifact.get(art.id, [])
        hard = [f.clause_id for f in found if f.severity == "H"]
        soft = [f.clause_id for f in found if f.severity != "H"]
        if hard:
            badge = f"WITHHOLD ({', '.join(hard)})"
        elif soft:
            badge = f"REVIEW ({', '.join(soft)})"
        else:
            badge = "clean"
        ticker = f" {art.ticker}" if art.ticker else ""
        print(
            f"{art.id[:50]:<52}{'yes' if archived.get(art.id) else 'no':<6}"
            f"{(extract_verdict(art) or '—'):<8}{badge}{ticker}"
        )
    if flags:
        print()
        print("Evidence for each badge (the clause's own string, newest first):")
        for art in artifacts:
            for flag in by_artifact.get(art.id, ()):
                print(f"  [{flag.clause_id}] {art.id}")
                print(f"      {flag.evidence}")


def _select_clauses(clause_filter: str | None) -> list[ContractClause]:
    """The clause universe, i.e. what the live persist gate would actually run.

    A rate always reads against the set that runs in production, so this is the
    registry itself — never a subset of it. To quantify a clause BEFORE it can
    withhold anything (design §7.1), stage it outside the registry first and add it
    to the universe for the measurement, as ``proposed_clauses.py`` did until the
    §4 closure family was promoted.
    """
    universe = list(CONTRACT_CLAUSES)
    if clause_filter is None:
        return universe
    wanted = clause_filter.upper()
    selected = [c for c in universe if c.id.upper() == wanted]
    if not selected:
        available = ", ".join(c.id for c in universe)
        raise SystemExit(f"unknown clause {clause_filter!r}; available: {available}")
    return selected


async def _run(
    clause_filter: str | None,
    limit: int | None,
    badge: bool = False,
) -> int:
    clauses = _select_clauses(clause_filter)
    store = ArtifactStore()
    try:
        artifacts, archived = await _enumerate_artifacts(store, limit)
    finally:
        await store.close()
    flags = _scan(artifacts, clauses)
    if badge:
        _badge_report(artifacts, flags, archived)
    else:
        _report(len(artifacts), clauses, flags)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run the output-contract clauses over every persisted artifact and "
            "report, per clause, how many would be flagged for REVIEW. READ-ONLY."
        )
    )
    parser.add_argument(
        "--clause",
        metavar="Cn",
        default=None,
        help="Restrict the scan to a single clause id (e.g. C1). Default: all clauses.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        metavar="N",
        default=None,
        help="Sample only the newest N artifacts. Default: scan the whole store.",
    )
    parser.add_argument(
        "--badge",
        action="store_true",
        help=(
            "Print the read-time artifact badge (design §9.3) instead of the per-clause "
            "catch lists: one line per artifact naming the clauses that WOULD withhold it "
            "(severity H) or annotate it (S)."
        ),
    )
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be >= 1")
    return asyncio.run(_run(args.clause, args.limit, args.badge))


if __name__ == "__main__":
    sys.exit(main())
