"""Family-3 verifier: enterprise-value bridge completeness.

``calculate_ev`` now includes preferred equity and noncontrolling (minority)
interest, so a REPORTED component is folded into EV — no longer dropped. The
residual gap is a component the provider did NOT report (``None``): the extractor
coerces it to 0, which is right for the overwhelming majority of issuers but
UNVERIFIABLE. If the issuer actually carries preferred / NCI, EV — and every EV
multiple (EV/EBITDA, EV/Revenue) — is understated, and the omission stays INVISIBLE
to the ``market_cap + debt + preferred + NCI − cash`` identity, which still closes
to the dollar.

Flagged at ``review`` (not ``blocked_field``): the assumed-0 is usually correct, so
surface the unverifiable bridge so the analyst can confirm rather than auto-withhold
the whole valuation.

Which provider can fill it, probed against the live vendor APIs 2026-10-12:

* **FMP** — ``preferredStock`` / ``minorityInterest`` are balance-sheet schema
  fields, so this caliber states an explicit 0 for an issuer carrying neither and
  the check simply does not fire. (It is also rank-1 for fundamentals; the INCY
  report that raised both findings was served by yfinance only because FMP was out
  of quota — HTTP 429 on every symbol, breaker open.)
* **yfinance** — its statement module DOES carry the rows (``Preferred Stock``,
  ``Preferred Stock Equity``, ``Minority Interest``: live WFC 15.348B / 2.133B,
  matching the SEC facts to the dollar) and the provider now reads them, but it
  OMITS the row for an issuer that carries none — so a nil claim that the filer
  does not tag either stays None here and keeps this finding.
* **Tiingo** — carries no balance-sheet NCI or preferred data code at all; its
  only NCI-shaped code is the income-statement flow to NCI.
* **SEC XBRL** — ``PreferredStockValue`` / ``MinorityInterest`` are the filer's own
  statement and the pipeline already fetches those facts for every run, so they are
  the one remaining authoritative source for a nil claim. They are deliberately NOT
  wired into the bridge: a fact can be years stale (JPM's ``PreferredStockValue``
  was last filed 2009), ``_select_latest_fact`` has no recency gate, and TAG ABSENCE
  is not proof of a nil claim (JPM files none despite carrying preferred) — so a
  fill needs both a recency gate and an explicit decision that SEC outranks a vendor
  caliber. Live: INCY tags preferred 0 across 30 facts through 2026-03-31 (a usable
  reported zero) and has no ``MinorityInterest`` fact at all.
"""

from __future__ import annotations

from finrobot.engine.models.financial import FinancialData
from finrobot.engine.models.metric_authority import resolve_metric
from finrobot.engine.models.numeric_claim import Finding


def _authority_note(metric: str) -> str:
    """Name the declared owner of a bridge component that nobody supplied.

    Before the metric-authority registry, this finding could only say "the provider
    did not report it" — which reads as a vendor quirk and invites the reader to
    assume some other caliber has the number. The registry turns it into a citable
    statement: *who* owns the metric, which calibers could legitimately supply it, and
    whether the registry has itself declined to own it. The severity is unchanged
    (still ``review``): this adds provenance to an existing caveat, it does not change
    what ships.
    """
    resolution = resolve_metric(metric, {})
    row = resolution
    if row.status == "declined":
        return (
            f" Metric authority: no producer of record — declined ({row.reason_code}): "
            f"{row.citation}."
        )
    owner = row.producer_id or "unregistered"
    return (
        f" Metric authority: producer of record {owner!r} supplied no value, so no "
        f"wired source states this number and the assumed 0 cannot be confirmed."
    )


def audit_ev_bridge(fin: FinancialData) -> list[Finding]:
    # No EV was computed (provider lacked debt/cash) → there is no EV to call
    # incomplete; the missing-net-debt case is its own existing warning.
    if fin.valuation.enterprise_value is None:
        return []

    findings: list[Finding] = []
    for metric, label, value in (
        ("preferred_stock", "preferred stock", fin.balance.preferred_stock),
        (
            "noncontrolling_interest",
            "noncontrolling interest",
            fin.balance.noncontrolling_interest,
        ),
    ):
        # Reported (0.0 or a value) → already in EV via calculate_ev → nothing to
        # flag. None → provider didn't report it, EV assumed 0 → unverifiable.
        if value is None:
            findings.append(
                Finding(
                    field_key="enterprise_value",
                    check="ev_bridge_unverified",
                    severity="review",
                    evidence=(
                        f"{fin.ticker}: {label} not reported by the provider — EV "
                        f"assumes 0 for it. If the issuer carries {label}, this EV "
                        f"(and EV/EBITDA, EV/Revenue) is understated by that amount."
                        + _authority_note(metric)
                    ),
                )
            )
    return findings
