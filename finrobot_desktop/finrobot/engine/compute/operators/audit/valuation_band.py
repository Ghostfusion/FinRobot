"""Numeric-audit verifier: the published target vs the issuer's own multiple band.

The football field shows the issuer's own 5-year EV/EBITDA history and the
published price target side by side; nothing used to check them against each
other. EHC shipped a $225.91 target whose implied ~17x TTM EBITDA sat miles above
the issuer's own 5-year p90 of 12.2x while the report's own band labeled the stock
"fair" at the median — an internal contradiction the reader had to notice alone
(owner review 2026-10-13).

This verifier makes that contradiction explicit: it re-derives the multiple the
PUBLISHED target implies (the same EV→equity bridge, inverted) and flags it at
``review`` when it sits outside the band's [p25, p90] range. ``review`` (not
``blocked_field``): the target is a judgment call — the cross-check is evidence
for the reader, not a reason to withhold the number. Nothing here gates the
verdict or the target.

Everything is computed from the frozen artifact (the published target, the run's
TTM EBITDA, the balance-sheet bridge, and the technical chapter's own
``historical_bands``) — no provider call, no LLM.
"""

from __future__ import annotations

from typing import Any

from finrobot.engine.compute.operators.multiples import implied_ev_multiple
from finrobot.engine.compute.operators.valuation_aggregator import ev_ebitda_band_cross_check
from finrobot.engine.models.numeric_claim import Finding

_CHECK_ID = "target_multiple_outside_band"


def audit_target_multiple_band(
    ticker: str,
    *,
    target_price: float | None,
    shares_outstanding: float | None,
    net_debt: float | None,
    preferred_stock: float | None,
    noncontrolling_interest: float | None,
    ttm_ebitda: float | None,
    band_p25: float | None,
    band_p90: float | None,
    window_years: int | None = None,
) -> list[Finding]:
    """Flag a published target whose implied EV/EBITDA leaves the issuer's band.

    ``implied = (target_price × shares + net_debt + preferred + NCI) / ttm_ebitda``;
    a finding is emitted when it exceeds the band's p90 or falls below its p25 —
    i.e. the target prices the business outside the multiple range the issuer has
    actually traded at over the band window.

    Returns ``[]`` when any required input is missing or non-positive: an implied
    multiple without a denominator, or a comparison without a band, is not a
    finding — it is a gap another verifier owns.
    """
    if target_price is None or target_price <= 0:
        return []
    if band_p25 is None or band_p90 is None or band_p25 <= 0 or band_p90 <= 0:
        return []
    implied = implied_ev_multiple(
        target_price,
        shares_outstanding,
        net_debt,
        preferred_stock,
        noncontrolling_interest,
        ttm_ebitda,
    )
    if implied is None:
        return []
    above = implied > band_p90
    below = implied < band_p25
    if not above and not below:
        return []
    bound = band_p90 if above else band_p25
    bound_label = "p90" if above else "p25"
    window_txt = f"{window_years}-year" if window_years else "multi-year"
    side = "above" if above else "below"
    return [
        Finding(
            field_key="thesis.price_target",
            check=_CHECK_ID,
            severity="review",
            evidence=(
                f"{ticker}: the ${target_price:.2f} target implies {implied:.1f}x TTM EBITDA "
                f"vs the issuer's own {window_txt} {bound_label} of {bound:.1f}x — the "
                f"target sits {side} its own historical multiple range"
            ),
        )
    ]


def _opt_float(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def publish_band_cross_check(structured: dict[str, Any], raw_data: dict[str, Any]) -> bool:
    """Publish the own-history EV/EBITDA cross-check row if the synthesis lacks it.

    The valuation pipeline asks the data layer for the band while BUILDING the
    synthesis; when that fetch yields no quantiles the row is simply absent —
    and with it the only place the reader can see the target beside the issuer's
    own multiple range (owner review 2026-10-13 asked for exactly that range in
    the football field). The technical chapter computed the SAME band from the
    same run and it is frozen on ``technical_analysis.historical_bands``, so the
    row is filled here from that band through the one producer
    (``ev_ebitda_band_cross_check``).

    Never overrides an existing row (the synthesis' own band, when it resolved,
    is the better-sourced one) and never fabricates one: every input is read
    from the frozen artifact, and a missing one leaves the list untouched.

    The row is tagged ``consulted_by_verdict=False`` (design §5): it is published
    *after* the verdict, from a band the verdict never saw, so it is display-only
    evidence. Nothing here is fabricated (the band is the same run's own data), but
    the tag is what keeps the two cases apart — the reader is not shown a
    cross-check that reads as corroboration of a call that never saw it, and the
    output-contract clause C8 does not read it against the call. An untagged row
    means the opposite: the synthesis built it while deciding.

    Returns True when a row was added.
    """
    synthesis = structured.get("valuation_synthesis")
    if not isinstance(synthesis, dict):
        return False
    existing = synthesis.get("cross_checks")
    if isinstance(existing, list) and existing:
        return False

    technical = structured.get("technical_analysis")
    band = technical.get("historical_bands") if isinstance(technical, dict) else None
    if not isinstance(band, dict) or band.get("metric") != "ev_ebitda":
        return False

    income = raw_data.get("income") if isinstance(raw_data, dict) else None
    balance = raw_data.get("balance") if isinstance(raw_data, dict) else None
    market = raw_data.get("market") if isinstance(raw_data, dict) else None
    income = income if isinstance(income, dict) else {}
    balance = balance if isinstance(balance, dict) else {}
    market = market if isinstance(market, dict) else {}

    total_debt = _opt_float(balance.get("total_debt"))
    total_cash = _opt_float(balance.get("total_cash"))

    check = ev_ebitda_band_cross_check(
        ttm_ebitda=_opt_float(income.get("ebitda")),
        band_p25=_opt_float(band.get("p25")),
        band_median=_opt_float(band.get("median")),
        band_p75=_opt_float(band.get("p75")),
        shares=_opt_float(market.get("shares_outstanding")),
        current_net_debt=(
            total_debt - total_cash if total_debt is not None and total_cash is not None else None
        ),
        preferred_stock=_opt_float(balance.get("preferred_stock")),
        noncontrolling_interest=_opt_float(balance.get("noncontrolling_interest")),
        window_years=(
            int(band["window_years"])
            if isinstance(band.get("window_years"), (int, float))
            else None
        ),
        sample_count=(
            int(band["sample_count"])
            if isinstance(band.get("sample_count"), (int, float))
            else None
        ),
        # The band this row is filled FROM is the frozen technical band, which carries
        # its own structural-break caveat — and this path is exactly the one the audited
        # report took (the synthesis' own band fetch yielded no quantiles, so the row was
        # published from here). Dropping the caveat here would publish the issuer's own
        # multiple range as a clean signal over a window containing an EBITDA ramp.
        band_break_caveat=(
            band.get("classification_caveat")
            if isinstance(band.get("classification_caveat"), str)
            else None
        ),
        # Display-only (design §5): this row is published after the verdict, so the
        # call was already written when it appeared. The tag is provenance, not value.
        consulted_by_verdict=False,
    )
    if check is None:
        return False
    synthesis["cross_checks"] = [check.model_dump(mode="json")]
    return True


def target_multiple_band_findings_from_structured(
    structured: dict[str, Any], raw_data: dict[str, Any]
) -> list[Finding]:
    """Run the verifier against a frozen equity-research artifact.

    Reads only what the report already froze: ``thesis.price_target`` (the
    PUBLISHED target), the raw ``FinancialData`` dump for the TTM EBITDA and the
    EV bridge, and ``technical_analysis.historical_bands`` for the issuer's own
    band. Every read is guarded — a missing band or bridge component yields no
    finding rather than a comparison against an assumed value.
    """
    thesis = structured.get("thesis")
    target_price = _opt_float(thesis.get("price_target")) if isinstance(thesis, dict) else None
    if target_price is None:
        return []

    band: dict[str, Any] = {}
    technical = structured.get("technical_analysis")
    if isinstance(technical, dict):
        candidate = technical.get("historical_bands")
        if isinstance(candidate, dict):
            band = candidate
    # Only the EV/EBITDA band can be re-applied to EBITDA dollars; a P/FCF band
    # would need a free-cash-flow denominator this verifier does not carry.
    if band.get("metric") != "ev_ebitda":
        return []

    income = raw_data.get("income") if isinstance(raw_data, dict) else None
    balance = raw_data.get("balance") if isinstance(raw_data, dict) else None
    market = raw_data.get("market") if isinstance(raw_data, dict) else None
    income = income if isinstance(income, dict) else {}
    balance = balance if isinstance(balance, dict) else {}
    market = market if isinstance(market, dict) else {}

    total_debt = _opt_float(balance.get("total_debt"))
    total_cash = _opt_float(balance.get("total_cash"))
    net_debt = (
        total_debt - total_cash if total_debt is not None and total_cash is not None else None
    )

    ticker = str(
        (raw_data.get("ticker") if isinstance(raw_data, dict) else None)
        or structured.get("ticker")
        or "?"
    ).upper()
    window = band.get("window_years")
    return audit_target_multiple_band(
        ticker,
        target_price=target_price,
        shares_outstanding=_opt_float(market.get("shares_outstanding")),
        net_debt=net_debt,
        preferred_stock=_opt_float(balance.get("preferred_stock")),
        noncontrolling_interest=_opt_float(balance.get("noncontrolling_interest")),
        ttm_ebitda=_opt_float(income.get("ebitda")),
        band_p25=_opt_float(band.get("p25")),
        band_p90=_opt_float(band.get("p90")),
        window_years=int(window) if isinstance(window, (int, float)) else None,
    )


def attach_target_multiple_band_findings(
    structured_out: dict[str, Any], raw_data: dict[str, Any]
) -> list[str]:
    """Append the verifier's findings to ``structured_out["numeric_audit"]``.

    The single wiring entry point for the artifact builder. Appends the findings
    in the same shape every other verifier's findings take, rolls the artifact
    status up to ``caveated`` (a ``review`` finding annotates, it never withholds),
    and returns the ``[NUMERIC-AUDIT/...]`` warning lines. No-op (returns ``[]``)
    when the numeric-audit block is absent or there is nothing to flag.
    """
    audit = structured_out.get("numeric_audit")
    if not isinstance(audit, dict):
        return []
    findings = target_multiple_band_findings_from_structured(structured_out, raw_data)
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
