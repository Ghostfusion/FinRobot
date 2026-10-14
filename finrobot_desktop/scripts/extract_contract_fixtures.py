"""Capture the pinned artifacts' payloads as output-contract fixtures (§7.2).

The design doc requires the golden fixtures to be stored as PAYLOADS, not as
hand-built objects. The reason is recorded in §7.1: the first C11 probe tested
``a != b`` behind an ``is not None`` guard and therefore missed all 63 divergent
artifacts — the whole defect was a MISSING key. A hand-written fixture would have
carried the same guard, because it would have been written by the same hand that
wrote the probe. A real payload does not.

So each fixture is a verbatim subset of one row of ``~/.finrobot/artifacts.db``:
only the paths the contract clauses read are retained (a full row reaches 3 MB —
``technical_analysis.monte_carlo.implied_prices`` alone carries ~10k simulated
prices), and every retained value is copied byte-for-byte, never recomputed,
reordered or reformatted.

Each fixture also records, measured rather than asserted, the verdict of EVERY
clause on that payload (live and staged). That map is the regression oracle: if a
clause's reading of a stored artifact changes, the fixture diff says so. The
human-written half is ``pinned_for`` — the clauses the payload exists to pin —
which must be a subset of the firing set.

READ-ONLY against the store. Regenerate with::

    uv run --no-sync python scripts/extract_contract_fixtures.py

and REVIEW THE DIFF: a changed fixture means the corpus shape moved, which is
itself the signal this file exists to surface.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from finrobot.artifact.contract import CONTRACT_CLAUSES
from finrobot.artifact.models import (
    Artifact,
    ArtifactAssumptions,
    ArtifactComputeVersion,
    ArtifactInputs,
    ArtifactMeta,
    ArtifactOutputs,
)
from finrobot.artifact.proposed_clauses import PROPOSED_CLAUSES
from finrobot.artifact.store import ArtifactStore

_FIXTURE_DIR = (
    Path(__file__).resolve().parent.parent / "tests" / "artifact" / "fixtures" / "contract"
)

#: ``outputs.structured`` paths the clauses read, live and staged.
_STRUCTURED_KEYS = (
    "thesis",
    "valuation_synthesis",
    "valuation_withheld",
    "withheld_reason",
    "numeric_audit",
    "ownership_governance",
    "catalyst_analysis",
    "summary_text",
    "llm_narrative",
    "currency",
    "xbrl_facts_snapshot",
)

#: Sub-documents whose bulk is not read: the retained keys are the whole clause
#: surface inside them. ``ownership_governance.insider_transactions`` alone is
#: 1 MB of line items (790 rows for UTHR) and no clause reads it.
_STRUCTURED_SUBSETS: dict[str, tuple[str, ...]] = {
    "ownership_governance": (
        "insider_net_flow",
        "insider_buy_value",
        "insider_sell_value",
        "insider_window_days",
        "insider_largest_sale",
        "warnings",
    ),
}

#: ``technical_analysis`` is pruned: ``monte_carlo.implied_prices`` is the whole
#: weight of a row and no clause reads it.
_TECHNICAL_KEYS = ("monte_carlo", "historical_bands")
_MONTE_CARLO_KEYS = (
    "assumptions_used",
    "percentiles",
    "n_valid",
    "mean",
    "std",
    "current_price_percentile",
)

#: ``inputs.raw_data`` paths the clauses read.
_RAW_KEYS = ("income", "balance", "market", "valuation", "data_authority")

#: (artifact id, clauses it is pinned FOR, why it is in the set). The pinned
#: clauses are the ones that must keep firing; every other clause's verdict is
#: recorded from the measurement, so an unrelated regression still shows up.
_PINNED: tuple[tuple[str, tuple[str, ...], str], ...] = (
    (
        "art_2026-10-14T16:31:36_THC_equity_research_8d9bfa",
        ("C8", "C10a", "C10c", "C12c", "C14b"),
        "instance A — a BUY whose target was withheld while its only cross-check sits "
        "~5x below the tape; margin published against a null numerator; the identity "
        "computable but unrecorded; a stale annotated fact; and prose where the "
        "scrubber took an insider-flow amount",
    ),
    (
        "art_2026-10-14T20:27:40_THC_equity_research_99cdca",
        ("C6b", "C8", "C11"),
        "instance B, the ORDERING case: the verdict read no cross-check (the own-history "
        "band resolved to 0 samples) and the cross-check in the payload arrived after the "
        "verdict; the note still claims there was no cross-validation",
    ),
    (
        "art_2026-10-14T20:37:52_THC_equity_research_bab351",
        ("C10d", "C12a", "C12b"),
        "instance C — HOLD, two methods, the equity identity recorded (C10c quiet); the "
        "payload that shows the identity fix and the caliber divergence side by side",
    ),
    (
        "art_2026-10-14T21:12:35_THC_equity_research_c75ac2",
        ("C10d",),
        "the newest stored artifact — the post-fix reference for C10c/C13b, and the "
        "reference for C11 NOT firing (root and synthesis both emit the flag)",
    ),
    (
        "art_2026-10-14T16:44:09_SKM_equity_research_2e8161",
        ("C9",),
        "SKM — the degenerate band (-2.97 .. -1.23 against a $34.42 price). C8 must NOT "
        "read it: this is the payload that makes C8 flag 7 of §1.1's 8, with C9 taking "
        "the eighth",
    ),
    (
        "art_2026-10-14T16:34:07_HMY_equity_research_b86736",
        ("C8",),
        "HMY — a positive, monotone, fully sampled band that still sits ~5x below the "
        "tape: the case that belongs to C8 and not C9",
    ),
    (
        "art_2026-10-14T00:16:20_NFLX_equity_research_f7a3ac",
        ("C8", "C14b"),
        "NFLX — a contradicted BUY, and prose where the scrubber took an insider-flow amount",
    ),
    (
        "art_2026-10-14T06:06:44_UTHR_equity_research_e76485",
        ("C8", "C14b"),
        "UTHR — 'insiders were net sellers to the tune of [target withheld]' beside a "
        "published flow; the largest payload in the set, so it pins the pruning",
    ),
    (
        "art_2026-10-14T06:21:26_TROW_equity_research_8bf448",
        ("C12a",),
        "TROW — the artifact discloses that its 8-K index is stale relative to the news "
        "window and ships the catalyst read anyway",
    ),
    (
        "art_2026-10-14T16:12:39_GMED_equity_research_c9080e",
        ("C14b",),
        "GMED — '[target withheld] of open-market purchases' for a $0 datum: the "
        "placeholder took an amount that is not the target. §4.7 cites this artifact; "
        "the later GMED run (27c788) does not carry the sentence",
    ),
    (
        "art_2026-10-14T19:18:07_GMED_equity_research_27c788",
        ("C6b", "C11"),
        "GMED — the second half of the pair: a single-method note denying the "
        "cross-check it prints, and the root writer omitting valuation_withheld",
    ),
    (
        "art_2026-10-14T19:59:27_AFRM_equity_research_27a9c6",
        ("C10c", "C14b"),
        "AFRM — 'insiders were net sellers of [target withheld]' with a computable "
        "identity never recorded; the last equity artifact before the 20:27 run",
    ),
    (
        "art_2026-10-13T20:18:24_EHC_equity_research_d6d487",
        ("C10a", "C10c", "C11", "C12c"),
        "EHC — the stale-fact class: us-gaap:OperatingIncomeLoss frozen at 2022-12-31 "
        "while every other fact runs to 2026-06-30, annotated by the producer's own "
        "staleness guard",
    ),
    (
        "art_2026-10-14T00:23:00_NVDA_equity_research_9f0889",
        ("C12b",),
        "NVDA — an empty news window (count 0, provider null) carrying a published "
        "overall_sentiment",
    ),
    (
        "art_2026-10-12T21:39:32_AMZN_equity_research_1749e7",
        (),
        "AMZN — the DISCRIMINATION case for C12c: its oldest fact reaches 2009-12-31 "
        "and the producer annotates nothing, because a long history is not a stale fact. "
        "Pinned for no clause firing on it",
    ),
    (
        "art_2026-10-14T16:42:33_SMCI_equity_research_54c0a6",
        (),
        "SMCI — the NEGATIVE case for C14b: the withheld path prints '[target withheld]' "
        "in its own honest disclaimer ('a directional read, not a point estimate'), with "
        "no insider-flow quantity in the sentence. Pinned for C14b staying QUIET: the "
        "coarse token scan flagged this class 27 times",
    ),
)


def _prune_technical(technical: Any) -> dict[str, Any]:
    if not isinstance(technical, dict):
        return {}
    kept: dict[str, Any] = {}
    for key in _TECHNICAL_KEYS:
        if key not in technical:
            continue
        value = technical[key]
        if key == "monte_carlo" and isinstance(value, dict):
            kept[key] = {k: v for k, v in value.items() if k in _MONTE_CARLO_KEYS}
        else:
            kept[key] = value
    return kept


def _subset(source: Any, keys: tuple[str, ...]) -> dict[str, Any]:
    """Every named key that is present, copied verbatim."""
    if not isinstance(source, dict):
        return {}
    return {key: source[key] for key in keys if key in source}


def _prune_structured(structured: Any) -> dict[str, Any]:
    """The declared clause surface of ``outputs.structured``, values untouched."""
    kept = _subset(structured, _STRUCTURED_KEYS)
    for key, sub_keys in _STRUCTURED_SUBSETS.items():
        if isinstance(structured, dict) and key in structured:
            kept[key] = _subset(structured[key], sub_keys)
    technical = _prune_technical(
        structured.get("technical_analysis") if isinstance(structured, dict) else None
    )
    if technical:
        kept["technical_analysis"] = technical
    return kept


def _to_artifact(artifact_id: str, ticker: str | None, type_: str, structured: dict, raw: dict):
    """Rebuild a persisted artifact from the retained paths. The scaffolding fields
    (version, source, created_at) are the ones the store writes; no clause reads
    them."""
    created = datetime.fromisoformat(artifact_id[4:23]).replace(tzinfo=timezone.utc)
    return Artifact(
        id=artifact_id,
        ticker=ticker,
        type=type_,  # type: ignore[arg-type]
        inputs=ArtifactInputs(data_source="yfinance", data_fetched_at=created, raw_data=raw),
        assumptions=ArtifactAssumptions(parameters={}),
        compute_version=ArtifactComputeVersion(version="0.1.0", formula_id="fixture"),
        outputs=ArtifactOutputs(structured=structured, summary_text="", warnings=[]),
        meta=ArtifactMeta(created_at=created, source="fixture:extract_contract_fixtures"),
    )


def _write(fixture: dict[str, Any]) -> Path:
    _FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    # Windows forbids ":" in a filename, so the artifact id is flattened — it stays
    # readable and one-to-one with the row it came from.
    name = fixture["artifact_id"].replace("_equity_research", "").replace(":", "-") + ".json"
    path = _FIXTURE_DIR / name
    path.write_text(
        json.dumps(fixture, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8"
    )
    return path


async def _run(limit: int | None) -> int:
    store = ArtifactStore()
    written: list[tuple[Path, int]] = []
    try:
        for artifact_id, pinned_for, notes in _PINNED[:limit]:
            artifact = await store.get(artifact_id)
            if artifact is None:
                print(f"[missing] {artifact_id}", file=sys.stderr)
                continue
            structured = _prune_structured(artifact.outputs.structured)
            raw = _subset(artifact.inputs.raw_data, _RAW_KEYS)

            rebuilt = _to_artifact(artifact.id, artifact.ticker, artifact.type, structured, raw)
            verdicts: dict[str, bool] = {}
            for clause in (*CONTRACT_CLAUSES, *PROPOSED_CLAUSES):
                verdicts[clause.id] = clause.check(rebuilt) is not None
            firing = {cid for cid, fired in verdicts.items() if fired}
            for clause_id in pinned_for:
                if clause_id not in firing:
                    print(
                        f"[!] {artifact_id}: pinned for {clause_id} but it did NOT fire; "
                        f"firing = {sorted(firing)}",
                        file=sys.stderr,
                    )

            path = _write(
                {
                    "artifact_id": artifact.id,
                    "ticker": artifact.ticker,
                    "type": artifact.type,
                    "extracted_at": datetime.now(timezone.utc).date().isoformat(),
                    "source": "~/.finrobot/artifacts.db",
                    "notes": notes,
                    "pinned_for": list(pinned_for),
                    "verdicts": verdicts,
                    "outputs_structured": structured,
                    "inputs_raw_data": raw,
                }
            )
            written.append((path, path.stat().st_size))
    finally:
        await store.close()

    total = 0
    for path, size in written:
        total += size
        print(f"{size / 1024:8.1f} KB  {path.name}")
    print(f"{total / 1024:8.1f} KB  ({len(written)} fixtures)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Extract the pinned artifacts' payloads into tests/artifact/fixtures/contract/ "
            "as verbatim subsets, with every clause's measured verdict recorded. READ-ONLY "
            "against the store."
        )
    )
    parser.add_argument(
        "--limit",
        type=int,
        metavar="N",
        default=None,
        help="Write only the first N pinned artifacts (debugging). Default: all.",
    )
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be >= 1")
    return asyncio.run(_run(args.limit))


if __name__ == "__main__":
    sys.exit(main())
