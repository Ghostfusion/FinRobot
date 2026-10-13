"""Cross-provider data validation for financials data.

Deterministic numeric comparator used by DataLayer.fetch() when more than
one provider can service a ``financials`` request. If the two providers
disagree beyond a conservative threshold, a warning is appended to the
primary DataResult and surfaced to the LLM via to_context_string().

Thresholds (conservative, chosen so TTM vs. latest-fiscal-year differences
don't trip the validator for most companies):

- revenue / net_income: 15% relative (covers one quarter of timing drift).
- total_cash: 10% relative (re-enabled 2026-06-08 once FMP adopted the
  cash + short-term-investments caliber that matches yfinance's ``total_cash``).
- market_cap: 5% relative (real-time vs. delayed should still be close).

Several fields are deliberately NOT cross-validated because the two providers
report them in DIFFERENT calibers — comparing them emits only false alarms, and
none is arbitrated downstream (SEC XBRL has no comparable concept), so there is no
real cross-source signal to recover:

- EBITDA: the FMP path reports operating-caliber EBITDA (EBIT + D&A, our own
  derivation) while yfinance returns reported-caliber ``info.ebitda`` (NI + tax +
  interest + D&A). At a 15% threshold this is apples-to-oranges — it falsely
  "agrees" for cash-rich firms and falsely alarms elsewhere.
- total_debt (removed 2026-06-06): the two providers mix balance-sheet lease
  conventions — FMP's ``total_debt`` carries bonds + finance leases while yfinance
  bundles operating leases too (MSFT FMP $57B vs yfinance $125B) — a caliber gap,
  not a data error, and not arbitrated downstream.
  (total_cash was removed alongside it on 2026-06-06 for the same reason, but was
  RE-ENABLED on 2026-06-08 once FMP switched to the cash + short-term-investments
  caliber — it now shares yfinance's caliber and is cross-validated again.)
- gross_margin / operating_margin (removed 2026-06-08): FMP derives the margin
  from its TTM income statement (``operating_income / revenue``) while yfinance
  uses Yahoo's ``info`` ratio on a latest-period convention. Live probe: MU
  operating_margin 48.5% (FMP TTM) vs 67.6% (yfinance) — 19.1pp — and KO 29.3%
  vs 35.1% — 5.7pp, both pure caliber gaps. The FMP value is the one we serve and
  it ties to SEC TTM at 0.0% on revenue AND net_income (the margin's own inputs),
  so the divergence is yfinance's convention, not a data error. Banks make it
  worse: yfinance returns gross_margin 0% for JPM (no COGS in ``info``), a 60pp
  phantom alarm.

revenue / net_income are as-reported in both providers and remain the genuine
like-for-like checks.

Only applies to data_type == "financials". Price and news have different
field structures and are not cross-validated here.

What this code does that raw LLM cannot: deterministic numeric agreement
checks between two APIs. An LLM would not autonomously call two APIs and
compare the numbers.
"""

from __future__ import annotations

import logging
from numbers import Real
from typing import Sequence

from finrobot.engine.data.authority import _SHARES_DERIVED_EPS, reconcile_results
from finrobot.engine.data.interface import DataResult
from finrobot.engine.models.metric_authority import (
    METRIC_REGISTRY_BY_NAME,
    MetricDecision,
    ReconciliationReport,
    compared_fields,
    key_fields,
)

logger = logging.getLogger(__name__)

# field -> relative tolerance (as a fraction). A VIEW over the leaf registry's
# ``compared_fields()`` — the band now has ONE home (the metric-authority rows), and
# this table cannot drift from it. The set is the four cross-provider PROSE-WARNING
# metrics: revenue / net_income (15%, one quarter of timing drift), total_cash (10%,
# re-enabled 2026-06-08 once FMP adopted the cash + short-term-investments caliber),
# market_cap (5%, real-time vs delayed). ebitda / total_debt / gross_margin are
# deliberately NOT here — different calibers across providers, declared as
# ``caliber_divergent`` rows in the registry.
_RELATIVE_FIELDS: dict[str, float] = {
    metric: row.tolerance_pct for metric, row in compared_fields().items()
}

# KEY fundamentals that drive valuation (DCF numerator / comps base). An
# over-tolerance divergence on these is escalated from a prose warning to a
# STRUCTURED Provenance.degraded marker (BUG-007) so dcf_seed / comps can
# react programmatically. The primary value still flows — this only flags it.
# A view over the registry's ``key_field=True`` rows (sorted), so the key set has
# one home too.
_KEY_FIELDS: tuple[str, ...] = key_fields()


def _is_number(v: object) -> bool:
    # bool is a subclass of int; exclude it to avoid comparing True/False as numbers.
    return isinstance(v, Real) and not isinstance(v, bool)


def cross_validate(primary: DataResult, secondary: DataResult) -> list[str]:
    """Compare two financials DataResults for the same ticker.

    Returns a list of human-readable warning strings for any discrepancies.
    An empty list means the two providers agree within tolerance.

    Only fields present in BOTH results are checked. Missing fields are not
    flagged — that is the extractor's responsibility.
    """
    warnings: list[str] = []
    p, s = primary.data, secondary.data

    # D5: empty secondary data → warn instead of silently passing all checks
    if not s:
        return [
            f"Secondary provider {secondary.provider} returned empty data "
            f"— cross-validation skipped"
        ]

    for field, tolerance in _RELATIVE_FIELDS.items():
        pv, sv = p.get(field), s.get(field)
        if pv is None or sv is None:
            continue
        if not _is_number(pv) or not _is_number(sv):
            continue
        if pv == 0 and sv == 0:
            continue
        denominator = max(abs(pv), abs(sv))
        if denominator == 0:
            continue
        rel_diff = abs(pv - sv) / denominator
        if rel_diff > tolerance:
            warnings.append(
                f"Data discrepancy: {field} differs by {rel_diff:.0%} "
                f"({primary.provider}: {pv:,.0f} vs "
                f"{secondary.provider}: {sv:,.0f}). "
                f"Threshold: {tolerance:.0%}."
            )

    return warnings


def has_comparable_financials(result: DataResult) -> bool:
    """True iff ``result`` carries at least one number :func:`cross_validate`
    actually compares (a field in ``_RELATIVE_FIELDS``).

    The trap this closes: an all-``None`` financials dict —
    ``{"revenue": None, "net_income": None, ...}`` — is non-empty, so a bare
    ``if not result.data`` guard waves it through as a real secondary. But
    ``cross_validate`` then ``continue``s past every ``None`` field and returns
    ``[]``, which the DataLayer reads as "two providers agree". That is phantom
    confidence: the secondary contributed no comparable number. The DataLayer
    uses this predicate to gate such a secondary exactly like a truly-empty one
    (warn + don't count toward ``secondary_count``), so a single live provider
    can never masquerade as a cross-validated pair.
    """
    data = result.data
    if not data:
        return False
    return any(_is_number(data.get(field)) for field in _RELATIVE_FIELDS)


# --- Market-cap consistency (lineage-aware) ----------------------------------
#
# Validates the accounting identity market_cap ≈ price × shares_outstanding —
# BUT only when ``shares_outstanding`` comes from a source INDEPENDENT of
# market_cap. The trap this avoids: FMP has no raw share count, so its
# ``shares_outstanding`` is rederived as ``int(market_cap / price)``
# (fmp_provider.py:378). Checking ``market_cap ≈ price × (market_cap/price)`` is
# a tautology — it can never fail and carries zero information (a "False
# Validation"). yfinance/Finnhub report shares straight from filings, so they ARE
# independent. We detect a derived share count empirically (shares ≈ mc/price)
# rather than hardcoding provider names, and ABSTAIN (return []) when no
# independent count exists — we never emit a spurious "consistent" signal.
#
# When an independent count IS available, the implied/reported RATIO is flagged by
# DIRECTION (not a hardcoded GOOG/META allowlist): >1.1 means market cap spans more
# shares than are reported (multi-class issuer with one class reported, or an ADR
# ratio); <0.9 means the reported count exceeds what market cap implies (stale or
# rounded share data). Calibrated on the S&P500 closure study (2026-06-05, 503
# names): the ratio does NOT cleanly map to a class count — genuine dual-class
# spans 1.16 (META) to 3.86 (IBKR) — so we never claim "dual" vs "triple". Always a
# WARNING, never an error — the primary value still flows.

# shares within this relative distance of mc/price is treated as rederived from
# them (i.e. NOT an independent source), so it can't validate its own parents.
# The threshold lives in ``engine.data.authority`` (which also applies it when
# building a ``shares_outstanding`` observation's derivation lineage) and is
# imported above so the rule has ONE home.

# implied/reported ratio inside [LO, HI] = closes (single effective class). Outside
# → flagged by direction. 0.9/1.1 chosen so normal float-vs-outstanding and
# timing noise stay silent (S&P500 study: 425/503 names land inside this band).
_SINGLE_CLASS_LO, _SINGLE_CLASS_HI = 0.9, 1.1


def _num(v: object) -> float | None:
    """Coerce to float iff v is a real number (excluding bool); else None."""
    return float(v) if isinstance(v, Real) and not isinstance(v, bool) else None


# --- Current-price cross-source check ----------------------------------------
#
# cross_validate() only runs for FINANCIALS. PRICE is fetched single-source
# (first provider wins), so a stale, split-unadjusted, or wrong-ticker price
# flows downstream as authoritative — and price drives market_cap, upside %, and
# the model-vs-market circuit breaker. This is a lightweight tripwire: confirm
# the current price against a SECOND provider's quote before trusting it. Same 5%
# band as market_cap (market_cap ≈ price × shares, so a looser price tolerance
# would be self-inconsistent) — wide enough to tolerate a delayed feed on a
# volatile session, tight enough to catch a ~2× split mismatch or multi-day-stale
# quote. Measured 2026-06-05: FMP vs yfinance agree to <0.04% across 12 names.
# A view over the ``current_price`` registry row's relative band (one home).
_PRICE_REL_TOLERANCE: float = METRIC_REGISTRY_BY_NAME["current_price"].tolerance_pct


def _price_of(result: DataResult) -> float | None:
    """Current price from a PRICE (``current_price``) or QUOTE (``price``) result."""
    return _num(result.data.get("current_price")) or _num(result.data.get("price"))


def cross_validate_price(primary: DataResult, secondary: DataResult) -> list[str]:
    """Compare the current price of two providers; warn if they diverge >5%.

    Returns ``[]`` when they agree, when either price is missing/non-positive, or
    when no second price is available (abstain — never a false "agree" signal).
    """
    pv, sv = _price_of(primary), _price_of(secondary)
    if pv is None or sv is None or pv <= 0 or sv <= 0:
        return []
    rel_diff = abs(pv - sv) / max(pv, sv)
    if rel_diff <= _PRICE_REL_TOLERANCE:
        return []
    return [
        f"Price discrepancy: current price differs by {rel_diff:.0%} "
        f"({primary.provider}: {pv:,.2f} vs {secondary.provider}: {sv:,.2f}). "
        f"Threshold: {_PRICE_REL_TOLERANCE:.0%}. Possible stale or split-unadjusted "
        f"price, wrong ticker, or a delayed feed on a volatile session — verify."
    ]


def _coherent_mc_price(result: DataResult) -> tuple[float, float] | None:
    """Return (market_cap, price) from one result iff both are positive numbers."""
    mc = _num(result.data.get("market_cap"))
    px = _num(result.data.get("current_price")) or _num(result.data.get("price"))
    if mc is not None and px is not None and mc > 0 and px > 0:
        return mc, px
    return None


def _independent_shares(result: DataResult) -> float | None:
    """Return this result's reported share count iff it is NOT derived as mc/price.

    A count within ``_SHARES_DERIVED_EPS`` of the result's own ``mc/price`` is
    rederived (the FMP lineage trap) and returns None — it cannot independently
    validate the very fields it was computed from.
    """
    sh = _num(result.data.get("shares_outstanding"))
    if sh is None or sh <= 0:
        return None
    mc_px = _coherent_mc_price(result)
    if mc_px is not None:
        mc, px = mc_px
        if abs(sh - mc / px) / sh < _SHARES_DERIVED_EPS:
            return None  # derived from this result's own market_cap/price
    return sh


def market_cap_consistency(primary: DataResult, secondary: DataResult) -> list[str]:
    """Lineage-aware check of market_cap ≈ price × shares_outstanding.

    Computes ``implied = market_cap / price`` from any result carrying both, then
    compares it to an INDEPENDENT reported share count (one not rederived as
    mc/price). Returns a single share-structure WARNING when the ratio leaves the
    single-class band, or ``[]`` when consistent OR when no independent share
    count exists (abstain — never a false "consistent" pass).
    """
    results = (primary, secondary)

    mc_px: tuple[float, float] | None = None
    for r in results:
        mc_px = _coherent_mc_price(r)
        if mc_px is not None:
            break
    if mc_px is None:
        return []
    mc, price = mc_px
    implied = mc / price

    reported: float | None = None
    source: str = ""
    for r in results:
        ind = _independent_shares(r)
        if ind is not None:
            reported, source = ind, r.provider
            break
    if reported is None:
        # FMP-only lineage trap: every available share count is mc/price.
        logger.debug(
            "market_cap_consistency abstained for %s — no independent share count "
            "(all derived as market_cap/price)",
            primary.ticker,
        )
        return []

    ratio = implied / reported
    if _SINGLE_CLASS_LO <= ratio <= _SINGLE_CLASS_HI:
        return []  # closes — single effective share class

    # Direction-based, calibrated on the S&P500 closure study (2026-06-05, 503
    # names). The ratio does NOT cleanly map to a class count — genuine dual-class
    # issuers span 1.16 (META) to 3.86 (IBKR) — so we flag DIRECTION + scale and
    # never assert "dual" vs "triple" (that was a false-precision band).
    if ratio > _SINGLE_CLASS_HI:
        # reported < implied: only part of the share base is reported.
        label = (
            f"reported shares are {ratio:.2f}× below market-cap-implied — market cap "
            f"spans all share classes while the reported count likely covers one "
            f"(multi-class issuer, e.g. Alphabet/Fox) or reflects an ADR ratio"
        )
    else:  # ratio < _SINGLE_CLASS_LO
        # reported > implied: in the study this was always a stale/rounded count
        # (yfinance .info returns placeholders like 815,000,000), never structure.
        label = (
            f"reported shares EXCEED market-cap-implied by {1.0 / ratio:.2f}× — likely a "
            f"stale or rounded reported share count, or a market cap from a different session"
        )

    return [
        f"Market-cap consistency: implied shares (market_cap/price = {implied:,.0f}) "
        f"vs reported shares ({source}: {reported:,.0f}) → ratio {ratio:.2f}. {label}; verify."
    ]


def key_field_divergences(primary: DataResult, secondary: DataResult) -> list[str]:
    """KEY fields (revenue / net_income) that diverge beyond tolerance between
    two financials providers.

    Companion to :func:`cross_validate` for the BUG-007 structured-degradation
    channel: ``cross_validate`` produces human-readable warnings for ALL fields,
    while this returns just the over-tolerance KEY field NAMES so the caller can
    stamp a ``provider_divergence:<field>`` marker onto ``Provenance.degraded``.
    Same tolerances, same numeric guards — it does NOT introduce a second
    threshold (CLAUDE.md: no parallel divergence definition).

    Empty list when the providers agree within tolerance on the key fields, or
    when the secondary returned empty data (no comparison possible).
    """
    diverged: list[str] = []
    p, s = primary.data, secondary.data
    if not s:
        return diverged

    for field in _KEY_FIELDS:
        tolerance = _RELATIVE_FIELDS[field]
        pv, sv = p.get(field), s.get(field)
        if pv is None or sv is None:
            continue
        if not _is_number(pv) or not _is_number(sv):
            continue
        if pv == 0 and sv == 0:
            continue
        denominator = max(abs(pv), abs(sv))
        if denominator == 0:
            continue
        if abs(pv - sv) / denominator > tolerance:
            diverged.append(field)

    return diverged


# --- Metric-authority reconciliation -----------------------------------------
#
# The pairwise comparators above emit prose about TWO dicts; the leaf registry's
# ``resolve_metric_observations`` reconciles N observations with full provenance
# (which source won, why, and every alternative considered). These two functions are
# the bridge the data layer calls after a provider walk: one supplies the
# ``Data authority:`` prose lines, the other the STRUCTURED key-divergence list that
# feeds ``Provenance.degraded`` — replacing the pairwise :func:`key_field_divergences`
# as the single source for that channel.
#
# The prose set is restricted to the cross-validated rows (``compared_fields()``): a
# warning line flips a coverage row to ``partial``, so preferred_stock /
# noncontrolling_interest conflicts keep their structured decision record without
# adding prose.

_AUTHORITY_PREFIX = "Data authority: "


def _fmt_num(value: float | None) -> str:
    return "N/A" if value is None else f"{value:,.0f}"


def _authority_line(decision: MetricDecision) -> str | None:
    """One ``Data authority:`` prose line for a non-clean decision, or ``None``.

    Clean = an accepted selection with every alternative comparable within tolerance.
    A conflict, an unavailable metric, or an alternative that could not be compared
    (a period/currency/unit mismatch) is reported; a ``fallback`` is left to the
    structured record.
    """
    if decision.status == "conflict":
        over = [
            candidate
            for candidate in decision.candidates
            if candidate.reason_code == "above_tolerance_published_flagged"
        ]
        selected = decision.selected_source or "?"
        details = "; ".join(
            f"{candidate.source} {_fmt_num(candidate.value)} "
            f"({candidate.deviation_pct:.1%} > {decision.tolerance_pct:.0%} tolerance)"
            for candidate in over
            if candidate.deviation_pct is not None
        )
        note = "producer of record" if decision.is_authoritative else "not the producer of record"
        return (
            f"{_AUTHORITY_PREFIX}{decision.metric} conflict — "
            f"{selected} {_fmt_num(decision.value)} vs {details}; using {selected} ({note})."
        )
    if decision.status == "unavailable":
        return (
            f"{_AUTHORITY_PREFIX}{decision.metric} unavailable — no eligible "
            f"observation ({decision.reason_code})."
        )
    mismatched = [
        candidate
        for candidate in decision.candidates
        if not candidate.eligible and candidate.reason_code.startswith("definition_mismatch_")
    ]
    if mismatched:
        selected = decision.selected_source or "?"
        details = "; ".join(
            f"{candidate.source} {_fmt_num(candidate.value)} ({candidate.reason_code})"
            for candidate in mismatched
        )
        return (
            f"{_AUTHORITY_PREFIX}{decision.metric} not compared — {details}; "
            f"using {selected} {_fmt_num(decision.value)}."
        )
    return None


def authority_reconciliation(
    results: Sequence[DataResult], *, report: ReconciliationReport | None = None
) -> list[str]:
    """``Data authority:`` prose lines for the non-clean decisions across ``results``.

    One line per non-clean decision, restricted to the cross-validated rows
    (``compared_fields()``) so a caliber-divergent or non-warning metric cannot flip
    a coverage row to ``partial``. Deterministic order (the report is sorted by
    metric). Pass ``report`` when the caller already reconciled the same results, so
    the walk reconciles once.
    """
    if report is None:
        report = reconcile_results(results)
    compared = compared_fields()
    lines: list[str] = []
    for decision in report.decisions:
        if decision.metric not in compared:
            continue
        line = _authority_line(decision)
        if line is not None:
            lines.append(line)
    return lines


def authority_key_field_divergences(
    results: Sequence[DataResult], *, report: ReconciliationReport | None = None
) -> list[str]:
    """KEY-field metric names (``key_field=True`` rows) that are over tolerance or
    unavailable across ``results`` — the single source for the structured
    ``key_field_divergences`` channel (BUG-007).

    Replaces the pairwise :func:`key_field_divergences` for the data layer: same
    output for a two-provider fetch (the owner's value is the reference, the same
    relative-deviation formula), but computed from the reconciled decision so the
    structured marker and the prose warning can never disagree.
    """
    if report is None:
        report = reconcile_results(results)
    key = set(key_fields())
    diverged: list[str] = []
    for decision in report.decisions:
        if decision.metric not in key:
            continue
        if decision.status in ("conflict", "unavailable"):
            diverged.append(decision.metric)
    return diverged
