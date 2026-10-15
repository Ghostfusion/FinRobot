"""P0 — run the identity registry over every stored artifact and report the population.

Two questions, one tool:

* **Inventory.** What arithmetic does this system publish, where is each identity
  declared, and which ones does the contract gate enforce? Printed as a table — the
  "model inventory" a reviewer needs before trusting any of it.
* **Population.** For each enforced identity, how many stored artifacts actually BIND it
  (XBRL §5.1), and how many of those contradict their own operands? A clause that fires
  on nothing is either a defect that is already fixed or a check that never runs; the
  difference is only visible by measuring, which is how C10e was calibrated (22 of 140
  artifacts, 12 tickers, every one the pre-fix scalar).

Read-only: opens ``artifacts.db`` with ``mode=ro``. Idempotent, no writes anywhere.

Usage::

    ./.venv/Scripts/python.exe scripts/sweep_identities.py
    ./.venv/Scripts/python.exe scripts/sweep_identities.py --type equity_research --verbose
    ./.venv/Scripts/python.exe scripts/sweep_identities.py --tolerance 0.01 --top 5
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sqlite3
import sys
from collections import Counter, defaultdict

_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from finrobot.engine.models.identities import (  # noqa: E402
    IDENTITIES,
    REGISTRY_VERSION,
    artifact_operands,
    checked_identities,
    identity_digest,
    relative_residual,
)


def _registry_table() -> None:
    print(
        f"IDENTITY REGISTRY v{REGISTRY_VERSION} (digest {identity_digest()}) — {len(IDENTITIES)} declarations"
    )
    print(f"{'id':<20} {'kind':<13} {'form':<8} {'gate':<7} operands")
    for spec in IDENTITIES:
        operands = " ".join(
            f"{'+' if c.weight >= 0 else '-'}{c.key}"
            + ("" if c.on_missing == "skip" else "*")
            + ("" if c.role == "component" else f"[{c.role}]")
            for c in spec.contributors
        )
        divisor = f" / {spec.divisor}" if spec.divisor else ""
        print(f"{spec.id:<20} {spec.kind:<13} {spec.form:<8} {spec.clause:<7} {operands}{divisor}")
    print("  * = absent operand assumed 0 (audited by operators/audit/ev_bridge.py)")
    print()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=str(pathlib.Path.home() / ".finrobot" / "artifacts.db"))
    parser.add_argument("--type", default=None, help="artifact type filter (e.g. equity_research)")
    parser.add_argument("--tolerance", type=float, default=0.01, help="relative residual band")
    parser.add_argument("--verbose", action="store_true", help="print every violation")
    parser.add_argument("--top", type=int, default=3, help="example artifacts per identity")
    parser.add_argument("--quiet-registry", action="store_true")
    args = parser.parse_args()

    if not args.quiet_registry:
        _registry_table()

    db = pathlib.Path(args.db)
    if not db.exists():
        print(f"no artifact store at {db}")
        return 1
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)

    where = "WHERE type = ?" if args.type else ""
    params = (args.type,) if args.type else ()
    rows = con.execute(
        f"SELECT id, ticker, type, payload FROM artifacts {where} ORDER BY created_at", params
    ).fetchall()
    print(f"{len(rows)} artifacts read from {db.name}")

    bound: Counter[str] = Counter()
    violated: Counter[str] = Counter()
    worst: dict[str, tuple[float, str, str]] = {}
    tickers: dict[str, set[str]] = defaultdict(set)
    types: dict[str, Counter[str]] = defaultdict(Counter)
    malformed = 0

    for artifact_id, ticker, artifact_type, payload in rows:
        try:
            artifact = json.loads(payload)
        except (TypeError, ValueError):
            malformed += 1
            continue
        raw = artifact.get("inputs", {}).get("raw_data")
        if not isinstance(raw, dict):
            continue
        for spec in checked_identities():
            resolved = artifact_operands(spec.id, raw)
            if resolved is None:
                continue
            operands, published = resolved
            result = relative_residual(spec.id, operands, published)
            if result is None:
                continue
            residual, expected = result
            bound[spec.id] += 1
            types[spec.id][artifact_type] += 1
            if residual > args.tolerance:
                violated[spec.id] += 1
                tickers[spec.id].add(ticker)
                previous = worst.get(spec.id)
                if previous is None or residual > previous[0]:
                    worst[spec.id] = (residual, artifact_id, f"{published:.6g} vs {expected:.6g}")
                if args.verbose:
                    print(
                        f"  {spec.id:<20} {ticker:<6} {published:.6g} vs {expected:.6g} "
                        f"({residual:.2%}) {artifact_id}"
                    )

    print()
    print(f"{'id':<20} {'bound':>6} {'violated':>9} {'rate':>7}  worst / example")
    for spec in checked_identities():
        n, v = bound[spec.id], violated[spec.id]
        if n == 0:
            print(
                f"{spec.id:<20} {0:>6} {0:>9} {'-':>7}  (never binds — nothing published all leaves)"
            )
            continue
        rate = f"{v / n:.1%}"
        detail = ""
        if v:
            residual, artifact_id, comparison = worst[spec.id]
            detail = f"{residual:.2%} {comparison} {artifact_id}"
        print(f"{spec.id:<20} {n:>6} {v:>9} {rate:>7}  {detail}")
        if v and args.top:
            names = sorted(tickers[spec.id])[: args.top]
            print(f"{'':<20}        tickers: {', '.join(names)} | types: {dict(types[spec.id])}")

    if malformed:
        print(f"\n{malformed} payload(s) did not parse as JSON")
    print("\nThis is a measurement, not a gate: a residual above tolerance is a candidate")
    print("defect OR a legitimate clock/caliber difference the artifact already discloses.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
