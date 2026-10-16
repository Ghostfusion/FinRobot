"""Typed projections from normalized canonical data to engine models.

ADR-0006 Step 4: functions here accept *already-normalized* typed inputs
(``NormalizedFinancials``, ``NormalizedPrice``) instead of raw ``DataResult``
dicts. The normalization关卡 lives exclusively in ``DataLayer.fetch_canonical``
— extractor is the projection layer (typed → FinancialData / CompanyFinancials
/ PriceHistory) that carries EBITDA caliber logic, EV handling, shares fallback,
and provenance merging. It must not re-normalize.

Historical per-year callers (``_helpers._build_historical_metrics``) that still
receive raw ``DataResult`` slices from ``fetch_historical`` wrap them with
``normalize_financials / normalize_price`` at the call site before passing here.
"""

import math
from collections.abc import Mapping, Sequence
from typing import Any, Final

from finrobot.engine.data.instrument import FundInstrumentError, is_fund_quote_type
from finrobot.engine.data.normalize.contracts import NormalizedFinancials, NormalizedPrice
from finrobot.engine.models.metric_authority import compared_fields
from finrobot.engine.models.financial import (
    FIELD_WARN_EV_MISSING_NET_DEBT,
    FIELD_WARN_SHARES_DERIVED,
    DataProvenance,
    FinancialData,
    IncomeStatement,
    BalanceSheet,
    MarketData,
    ValuationMetrics,
    PriceHistory,
    CompanyFinancials,
)
from finrobot.engine.compute.operators.fx_normalize import (
    normalize_company_to_usd,
    normalize_financialdata_to_usd,
)
from finrobot.engine.compute.operators.multiples import calculate_ev
from finrobot.engine.primitives.book_value import (
    SHARES_PRICE_CONSISTENCY_TOL as _SHARES_PRICE_CONSISTENCY_TOL,
    reconcile_book_value_to_price_basis,
)
from finrobot.engine.primitives.ebitda import (
    calculate_ebitda_operating,
    calculate_ebitda_reported,
)
from finrobot.engine.primitives.industry import is_balance_sheet_financial, is_bank

# The tolerance governing when a reported share count is treated as OFF the quoted
# price's basis (→ use the market_cap/price-implied count for per-share calibers) is
# owned by ``primitives.book_value`` so the share-count reconciliation below and the
# book-value-per-share reconciliation move in lockstep on the same threshold.

# Economic band for a margin ratio. A gross/operating margin ABOVE 100% implies a
# negative cost of goods / operating cost — not credible: the only legitimate breach
# is a rare supplier-rebate contra-cost, indistinguishable from the far more common
# provider artifact of a dropped/restated cost line (FMP reports UL grossProfit ≥
# revenue with quarterly costOfRevenue=0, GM 100.14%, while the real gross margin is
# ~47% per the annual filings — unrecoverable in the TTM path). Withhold such a value
# (None → shown as N/A) rather than fabricate a 100% figure OR crash the IncomeStatement
# ``le`` bound. Invariant-suite #5: gross_margin ≤ 100% is a SOFT rule (compute-and-flag,
# legitimacy exit before any throw), not a hard model crash. Below -500% is a
# percent/decimal mixup (the same magnitude the ``ge=-5`` model floor documents).
_MARGIN_CEILING = 1.0
_MARGIN_FLOOR = -5.0

# The prose prefixes ``engine.data.validator`` emits when two sources disagree
# beyond tolerance: ``cross_validate`` (financial fields) and ``cross_validate_price``
# (the quote). Counted below so the reader-visible provenance can disclose "N
# divergences" even when the diverging metric is NOT a key field and therefore
# never appears as a structured ``degraded`` marker — the audited NVDA run carried
# a 37% ``total_cash`` divergence (a compared, non-key field) beside an empty
# degradation view.
_VALIDATOR_DIVERGENCE_PREFIXES = ("Data discrepancy:", "Price discrepancy:")

# A market cap and a share count from the SAME provider payload close to the cent
# (Yahoo derives ``marketCap = sharesOutstanding × price``; FMP rederives the count as
# ``marketCap/price``), so any gap between ``market_cap / shares`` and the run's
# resolved quote is a CLOCK difference, not an accounting one — the FINANCIALS
# canonical and the PRICE canonical have independent TTLs and the financials payload
# embeds its own, older quote. 1% is far above that noise floor and far below a
# session's move on a volatile name.
_MARKET_CAP_PRICE_TOL = 0.01


def _count_validator_divergences(warnings: list[str]) -> int:
    """Number of validator cross-source divergence warnings in ``warnings``."""
    return sum(1 for w in warnings if w.startswith(_VALIDATOR_DIVERGENCE_PREFIXES))


# The label naming the P/E's denominator. A provider's ``trailingPE`` rides a
# diluted-EPS basis while the report PRINTS TTM net income, so the two disagree by
# construction (owner review, EHC: the 20.8× provider P/E implied ~$590M of net
# income beside a printed $603.7M and a $621M filing fact). ``extract_financial_data``
# therefore derives P/E from the SAME figures the report shows and stamps this
# label, so the ratio's denominator is explicit instead of assumed.
PE_BASIS_NET_INCOME = "market cap ÷ TTM net income (one net-income authority)"

# The label naming the OPERATING MARGIN's numerator authority, in the shape of
# ``PE_BASIS_NET_INCOME`` above. A provider computes its own operating margin from
# ITS TTM frame's revenue while the income block prints a ``revenue`` leaf from the
# canonical snapshot — two revenues under one name, so the published margin is not
# the quotient of the figures beside it. Live 2026-10-15 (KGC): published 0.52478004
# beside 4,409,000,000 / 8,470,900,224 = 0.52048777, i.e. the provider divided by a
# frame revenue of 8,401,615,275 — 0.8% away from the revenue it printed. That is
# C10e's founding defect (CF: 0.49325 beside 0.39088) at sub-1% magnitude, so it takes
# the same fix as the P/E: derive the ratio from the leaves the report SHOWS and stamp
# the basis here, so the identity holds by construction instead of by luck.
OPERATING_MARGIN_BASIS_INCOME_STATEMENT = (
    "operating income ÷ revenue (one operating-income authority)"
)

#: The fallback's label: a snapshot with no operating income to divide still prints the
#: provider's margin, and says that is what it is.
OPERATING_MARGIN_BASIS_PROVIDER = (
    "the provider's own operating margin (no operating income to divide)"
)

#: Relative gap above which a superseded provider margin is NAMED in that label. The
#: P/E's analogous threshold is 1% — a cap-vs-close vintage difference on a ratio of
#: order 20x. A margin's caliber gap is a fraction of that: the live cases this
#: derivation exists for are 0.23-0.82% (KGC 0.8179%, INVH 0.2478%, MLI 0.2282%), and
#: the printed figure carries one decimal of a percent, so 0.1% is the smallest gap
#: that can move a digit the reader sees. Below it the provider's number is the same
#: reading of a rounder source, and a note would be noise.
_OPERATING_MARGIN_SUPERSEDE_TOL = 0.001

# Relative gap between a provider's TTM net income and the SEC XBRL TTM net income
# above which the difference is DISCLOSED (see ``net_income_divergence_warning``).
# A filing fact is rounded to the filing's own precision and the two windows can
# differ by a few days, so small gaps are noise; >5% is a caliber difference the
# narrative must not absorb silently.
_NET_INCOME_DIVERGENCE_TOL = 0.05

# Relative gap between an SEC XBRL ANNUAL fact and the provider's fiscal-year figure
# for the SAME year above which the difference is DISCLOSED (see
# ``xbrl_fiscal_divergence_warning``). Same 5% bar as the TTM net-income pair and for
# the same reason: a filing fact is one authority and the provider series another.
_XBRL_FISCAL_DIVERGENCE_TOL = 0.05

#: 8-K items that can move the BALANCE SHEET after its date — the three that can
#: add debt, retire it, or pledge assets: Item 1.01 (entry into a material
#: definitive agreement), 2.03 (creation of a direct financial obligation or an
#: obligation under an off-balance-sheet arrangement) and 2.04 (triggering events
#: that accelerate or increase a financial obligation). Everything the report
#: states off the balance sheet rides on it: total debt, net debt, EV, the WACC's
#: debt weight and the Merton default barrier.
_BALANCE_SHEET_8K_ITEMS: Final[dict[str, str]] = {
    "1.01": "entry into a material definitive agreement",
    "2.03": "creation of a direct financial obligation",
    "2.04": "a triggering event accelerating a financial obligation",
}


def post_balance_sheet_financing_warning(
    *,
    balance_sheet_date: str | None,
    filings_8k: Sequence[Mapping[str, Any]] | None,
) -> str | None:
    """Disclose a financing 8-K filed AFTER the balance-sheet date.

    Returns None when no qualifying filing post-dates the balance sheet — that is
    the honest "nothing found" answer, never a manufactured clean bill of health.
    ``balance_sheet_date`` is the date the report's balance-sheet figures are
    stated as of (the TTM window's end); comparison uses the ISO date prefix so a
    full timestamp and a bare ``YYYY-MM-DD`` both work. Item matching is exact
    after normalizing the ``Item `` prefix, so ``Item 2.02`` (results of
    operations) can never be read as ``2.03``.

    2026-10-16 NVDA: an 8-K filed 2026-08-17 carrying Items 1.01 and 2.03 (a
    material agreement and a new financial obligation) post-dated the 2026-07-26
    balance sheet, and the report neither reconciled nor disclosed it — debt, EV
    and the default barrier shipped as current with nothing to say they were not
    (review 2026-10-16, checklist C).
    """
    if not balance_sheet_date or not filings_8k:
        return None
    horizon = str(balance_sheet_date)[:10]
    if len(horizon) != 10:
        return None
    hits: list[tuple[str, list[str]]] = []
    for event in filings_8k:
        if not isinstance(event, Mapping):
            continue
        filed = str(event.get("filing_date") or event.get("filed_at") or "")[:10]
        if len(filed) != 10 or filed <= horizon:
            continue
        items = [str(item).replace("Item", "").strip() for item in (event.get("items") or [])]
        matched = [code for code in _BALANCE_SHEET_8K_ITEMS if code in items]
        if matched:
            hits.append((filed, matched))
    if not hits:
        return None
    hits.sort(reverse=True)
    newest_date, newest_items = hits[0]
    item_label = "Items" if len(newest_items) > 1 else "Item"
    reasons = "; ".join(_BALANCE_SHEET_8K_ITEMS[code] for code in newest_items)
    others = (
        f"; {len(hits) - 1} further such filing(s) since the balance sheet" if len(hits) > 1 else ""
    )
    return (
        f"an SEC 8-K filed {newest_date} ({item_label} {', '.join(newest_items)}: {reasons})"
        f"{others} post-dates the balance sheet ({horizon}): total debt, net debt, enterprise "
        f"value and the default barrier are stated as of the balance-sheet date and are NOT "
        f"restated for it — treat them as possibly stale, not current. The size of that "
        f"obligation is not available from the sourced filing text (the stored 8-K text stops "
        f"at its cover pages), so no amount is netted into those figures — they exclude it "
        f"rather than reflect it."
    )


def xbrl_fiscal_divergence_warning(
    *,
    label: str,
    concept: str,
    provider_series: Sequence[float | None] | None,
    provider_years: Sequence[int] | None,
    provider_source: str | None,
    xbrl_fact: Mapping[str, Any] | None,
) -> str | None:
    """Disclose a >5% gap between an SEC XBRL ANNUAL fact and the provider's same year.

    Why this exists (owner review 2026-10-15, TROW): the report printed THREE FY2025
    operating incomes and reconciled none of them — the XBRL chapter's
    ``us-gaap:OperatingIncomeLoss`` fact (2,188,800,000 → a 29.9% margin), the
    financial chapter's provider annual bar (2,477,400,000 → 33.9%), and the TTM
    income block (2,615,100,000 → 34.4%) — while the DCF's 42% EBITDA-margin
    assumption rests on the provider caliber. A reader comparing the XBRL chapter
    against the margin chart was left to guess which number the thesis used, and a
    reviewer recomputed the operating margin ~5 points lower off the XBRL fact
    (which moves the DCF ~12%: the target is the same order, the thesis is not).

    Matches the fact to the provider series by the fiscal year the period ENDS in —
    the same key ``HistoricalMetrics.years`` carries (``_year_of(fiscal_year|date)``
    in the historical extractor) — so a June-FY filer aligns on its own year label.
    Returns None when the fact's year is not in the provider's series (nothing to
    compare against), when either side is missing/non-finite, or within tolerance.
    Pure and side-effect free, like ``net_income_divergence_warning`` beside it.
    """
    if not isinstance(xbrl_fact, Mapping):
        return None
    xbrl_raw = xbrl_fact.get("value")
    xbrl_value = float(xbrl_raw) if isinstance(xbrl_raw, (int, float)) else None
    period_end = xbrl_fact.get("period_end")
    if xbrl_value is None or not provider_years or not provider_series:
        return None
    # Match on the period END's year, as a string prefix: the same key the provider's
    # annual arrays carry, and it needs no date parse (a 'YYYY' value works too).
    end_year = str(period_end or "")[:4]
    index = next(
        (i for i, year_label in enumerate(provider_years) if str(year_label) == end_year),
        None,
    )
    if index is None or index >= len(provider_series):
        return None
    provider_value = provider_series[index]
    if provider_value is None:
        return None
    if not (math.isfinite(provider_value) and math.isfinite(xbrl_value)):
        return None
    denominator = max(abs(provider_value), abs(xbrl_value))
    if denominator == 0:
        return None
    gap = abs(provider_value - xbrl_value) / denominator
    if gap <= _XBRL_FISCAL_DIVERGENCE_TOL:
        return None
    return (
        f"{label} disagreement for FY{end_year} ({gap:.1%}): this report's fiscal-year figure "
        f"is {provider_value:,.0f} ({provider_source or 'provider'}) while the SEC XBRL "
        f"fact {concept} for the same year (period end {period_end}) is {xbrl_value:,.0f}. "
        f"The margins, multiples and the DCF's margin assumption are computed on the "
        f"provider figure — state which of the two a number comes from instead of "
        f"treating them as one figure."
    )


def _sanitize_margin(
    value: float | None, *, label: str, warnings: list[str] | None = None
) -> float | None:
    """Withhold (return None) a margin ratio outside the economically-credible band.

    A margin > 100% (implied negative cost) or < -500% (percent/decimal mixup) is not a
    trustworthy figure — return None so the metric shows N/A instead of a fabricated
    value, and never let it reach the IncomeStatement bound and crash the whole report.
    Byte-identical (returns the input) for every credible margin in ``[-5.0, 1.0]``.
    """
    if value is None:
        return None
    if value > _MARGIN_CEILING:
        if warnings is not None:
            warnings.append(
                f"{label} {value:.1%} exceeds 100% (implied negative cost) — the provider's "
                f"gross profit ≥ revenue with the cost line unreported/restated; withheld as "
                f"unreliable rather than shown as a fabricated 100% or crashing the report"
            )
        return None
    if value < _MARGIN_FLOOR:
        if warnings is not None:
            warnings.append(
                f"{label} {value:.1%} below -500% — a likely percent/decimal mixup or provider "
                f"error; withheld"
            )
        return None
    return value


def derive_operating_margin(
    operating_income: float | None,
    revenue: float | None,
    provider_margin: float | None,
    *,
    warnings: list[str] | None = None,
) -> tuple[float | None, str | None]:
    """``(published margin, basis label)`` — the ONE place this ratio is decided.

    The margin a report prints must be the quotient of the two figures it prints beside
    it. A provider's own margin divides ITS TTM frame's revenue, which is not the
    published ``revenue`` leaf: live 2026-10-15 KGC published ``operating_margin``
    0.52478004 beside ``4,409,000,000 / 8,470,900,224 = 0.52048777`` (its frame revenue
    was 8,401,615,275 — 0.8% away), and the audited CF run printed 0.49325 beside
    0.39088, the contradiction C10e was written for. So derive the ratio from the
    caller's OWN leaves and return the label naming that numerator.

    The provider's value is used only when there is no numerator to divide — and is then
    LABELLED as itself (``OPERATING_MARGIN_BASIS_PROVIDER``) rather than passed off as a
    derivation. A derived ratio that ``_sanitize_margin`` withholds (>100%, i.e. an
    operating income exceeding its own revenue) publishes nothing AND no label: the
    provider's margin is not substituted there, because it is the very contradiction this
    function exists to remove. ``(None, None)`` when neither path yields a value.

    The label is for callers that publish provenance (the artifact's
    ``IncomeStatement.operating_margin_basis``). A comps peer row has no provenance
    block and may ignore it — but it must still take the DERIVED value, so the margin it
    shows can never disagree with the revenue beside it.
    """
    if operating_income is None or not revenue:
        margin = _sanitize_margin(provider_margin, label="operating_margin", warnings=warnings)
        return margin, OPERATING_MARGIN_BASIS_PROVIDER if margin is not None else None
    derived = operating_income / revenue
    margin = _sanitize_margin(derived, label="operating_margin", warnings=warnings)
    if margin is None:
        return None, None
    if (
        provider_margin is not None
        and provider_margin != 0.0
        and abs(derived - provider_margin) / abs(provider_margin) > _OPERATING_MARGIN_SUPERSEDE_TOL
    ):
        return margin, (
            f"{OPERATING_MARGIN_BASIS_INCOME_STATEMENT}; supersedes the provider's "
            f"{provider_margin:.4f}, which divides a different revenue"
        )
    return margin, OPERATING_MARGIN_BASIS_INCOME_STATEMENT


def net_income_divergence_warning(
    provider_net_income: float | None,
    provider_source: str | None,
    xbrl_net_income: float | None,
    xbrl_source: str | None,
    nci_earnings: float | None = None,
) -> str | None:
    """Disclose a >5% gap between the SEC XBRL TTM net income and the provider's.

    Once the P/E is derived from the printed net income, the report carries TWO
    net-income authorities: the income-statement table's provider TTM net income
    and the XBRL ``us-gaap:NetIncomeLoss`` TTM filing fact the narrative may cite.
    A gap above ``_NET_INCOME_DIVERGENCE_TOL`` relative is a caliber difference
    that must be DISCLOSED rather than absorbed silently into prose — the EHC
    review found $621M (XBRL), $603.7M (provider) and ~$590M (the old P/E-implied
    fourth number) inside one report.

    ``nci_earnings`` — the noncontrolling-interest share of net income the
    provider's own statement frame reports (``Net Income Including Noncontrolling
    Interests`` − ``Net Income Common Stockholders`` / the ``Minority Interests``
    row) — lets us NAME the cause instead of guessing. When the observed gap
    MATCHES that share, the two authorities are simply different CALIBERS: the SEC
    ``NetIncomeLoss`` is consolidated (incl. NCI) while the provider's
    ``netIncomeToCommon`` is attributable to the parent. THC: 3.174B (consolidated)
    vs 2.241B (parent) = 933M of NCI earnings — not a typo, and not "concept /
    window / filing rounding".

    Returns a warning naming BOTH values and BOTH sources, or None when either
    figure is missing / non-finite or the two agree within tolerance. Pure and
    side-effect free. When the gap is NOT explained by the reported NCI share the
    conservative caliber-gap wording is kept.
    """
    if provider_net_income is None or xbrl_net_income is None:
        return None
    if not (math.isfinite(provider_net_income) and math.isfinite(xbrl_net_income)):
        return None
    denominator = max(abs(provider_net_income), abs(xbrl_net_income))
    if denominator == 0:
        return None
    gap = abs(provider_net_income - xbrl_net_income) / denominator
    if gap <= _NET_INCOME_DIVERGENCE_TOL:
        return None
    if (
        nci_earnings is not None
        and math.isfinite(nci_earnings)
        and abs(abs(provider_net_income - xbrl_net_income) - abs(nci_earnings))
        / max(abs(provider_net_income - xbrl_net_income), abs(nci_earnings), 1.0)
        <= _NET_INCOME_DIVERGENCE_TOL
    ):
        consolidated, parent = (
            (xbrl_net_income, provider_net_income)
            if abs(xbrl_net_income) >= abs(provider_net_income)
            else (provider_net_income, xbrl_net_income)
        )
        return (
            f"Net income disagreement ({gap:.1%}) is the noncontrolling-interest "
            f"share of earnings, not a typo: the consolidated figure "
            f"{consolidated:,.0f} (incl. noncontrolling interests) differs from the "
            f"amount attributable to the parent {parent:,.0f} by {abs(nci_earnings):,.0f} "
            f"of NCI earnings. Cite ONE basis explicitly — consolidated (incl. NCI) vs "
            f"attributable to the parent — instead of mixing the two."
        )
    return (
        f"Net income disagreement ({gap:.1%}): the income statement's TTM net income is "
        f"{provider_net_income:,.0f} ({provider_source or 'provider'}) while the SEC XBRL "
        f"TTM filing fact is {xbrl_net_income:,.0f} ({xbrl_source or 'SEC XBRL'}) — a "
        f"caliber gap (concept / window / filing rounding), not a typo; cite ONE authority "
        f"explicitly instead of mixing the two"
    )


def extract_financial_data(
    fin: NormalizedFinancials,
    price: NormalizedPrice,
) -> FinancialData:
    """Project NormalizedFinancials + NormalizedPrice into FinancialData.

    Normalization has already happened upstream (ADR-0006): ``fin`` and
    ``price`` are typed, currency-resolved, provenance-stamped objects from
    ``DataLayer.fetch_canonical``.  This function only computes derived
    fields (EBITDA calibers, EV, shares fallback, 52w high/low) and assembles
    the engine model.

    Two EBITDA calibers are recomputed from absolute line items so neither
    rides on a provider's opaque (and, for the latest quarter, sometimes
    D&A-less) ebitda field. Operating is the primary EV/EBITDA numerator;
    reported is the street cross-check. Falls back to the provider-supplied
    ebitda only when components are absent (e.g. yfinance-sourced snapshots).

    Raises ValueError for missing critical fields (revenue, market_cap).
    Non-critical missing fields (debt, cash, D&A) are defaulted and recorded
    in FinancialData.warnings so the caller can surface them to the user.
    """
    ticker = fin.ticker

    # Fail fast on a positively identified FUND before the missing-revenue branch
    # below: a fund's FINANCIALS fetch succeeds *without raising* and returns a
    # contract whose company lanes are all None (IEI / VTSAX: revenue, EBITDA,
    # net_income, market_cap all None), so it would otherwise die as
    # "Missing or zero revenue for IEI" — a category error reported as a missing
    # number, after the LLM pipeline had already been paid for. Route the caller
    # to the fund pipeline instead.
    if is_fund_quote_type(fin.quote_type):
        raise FundInstrumentError(ticker, fin.quote_type)

    revenue = fin.revenue
    provider_market_cap = fin.market_cap

    # Banks have no COGS, so gross margin is undefined. FMP forces its non-bank
    # template (~60% phantom) and yfinance returns 0% — suppress to None at this
    # symmetric chokepoint so neither provider's meaningless value reaches the
    # report (Mode A/B parity; the FMP provider also suppresses at source).
    bank = is_bank(industry=fin.industry, sector=fin.sector)
    gross_margin = None if bank else fin.gross_margin

    # Two EBITDA calibers, recomputed from absolute line items so neither
    # rides on a provider's opaque (and, for the latest quarter, sometimes
    # D&A-less) ebitda field. Operating is the primary EV/EBITDA numerator;
    # reported is the street cross-check. Falls back to the provider-supplied
    # ebitda only when components are absent (e.g. yfinance-sourced snapshots).
    ebitda_operating = calculate_ebitda_operating(
        fin.operating_income, fin.depreciation_amortization
    )
    if ebitda_operating is None:
        ebitda_operating = fin.ebitda
    ebitda_reported = calculate_ebitda_reported(
        fin.net_income,
        fin.income_tax_expense,
        fin.interest_expense,
        fin.depreciation_amortization,
    )
    ebitda = ebitda_operating

    if not revenue:
        raise ValueError(f"Missing or zero revenue for {ticker}")

    warnings: list[str] = []
    field_warnings: dict[str, list[str]] = {}

    raw_debt = fin.total_debt
    raw_cash = fin.total_cash
    total_debt = raw_debt if raw_debt is not None else 0
    total_cash = raw_cash if raw_cash is not None else 0

    # --- current_price: the authoritative market basis (live quote) ---
    current_price = price.current_price or fin.current_price
    if not current_price or current_price <= 0:
        raise ValueError(
            f"Could not determine current_price for {ticker}. "
            "Ensure the price provider is configured and returning data."
        )

    # --- shares_outstanding: the provider/SEC count for per-share valuation ---
    # The count must be an INDEPENDENT observation, not a market-cap division:
    # deriving shares = market_cap/price and then publishing market_cap = shares ×
    # price makes the two mutually derived (authority._derived_from then always
    # flags the count as derived, and the share-count check is a tautology). So we
    # keep the provider/SEC count whenever it exists, flag a large divergence from
    # market_cap/price (multi-class single-class .info count / ADR ratio) WITHOUT
    # swapping in the derived value, and only fall back to market_cap/price when no
    # count is reported at all (labelled).
    reported_shares = fin.shares_outstanding
    if reported_shares is not None and reported_shares > 0:
        if provider_market_cap and provider_market_cap > 0:
            implied = provider_market_cap / current_price
            if abs(reported_shares - implied) / implied > _SHARES_PRICE_CONSISTENCY_TOL:
                # Divergent counts are single-CLASS counts of a multi-class issuer
                # (or an ADR ratio), and the numerator is TOTAL equity value: keeping
                # the class count overstates every per-share figure by the class ratio.
                # Probed 2026-10-14: Yahoo still reports GOOG 5.527bn vs cap/price
                # 12.230bn (54.8%), META 2.205bn vs 2.548bn (13.4%), FOX 220M vs 422M
                # (47.8%) — while BP and THC tie exactly. So the price-consistent
                # count wins on divergence and the divergence is DISCLOSED (never
                # silent) so the reader knows which basis the per-share metrics use.
                warnings.append(
                    f"shares_outstanding from {fin.provenance.provider} for {ticker} "
                    f"({reported_shares:,.0f}) diverges "
                    f"{abs(reported_shares - implied) / implied:.0%} from market_cap/price "
                    f"({implied:,.0f}) — likely a single share class of a multi-class "
                    "issuer or an ADR ratio. Using the price-consistent count so per-share "
                    "metrics (EPS, P/E, implied price) stay on the market's basis."
                )
                field_warnings.setdefault("pe", []).append(FIELD_WARN_SHARES_DERIVED)
                shares = implied
            else:
                shares = reported_shares
                # Below the multi-class band the two counts agree as a SHARE count —
                # but this same ratio is the market cap's implied price against the
                # run's quote, and a gap there is not a share-structure fact. It
                # means the cap and the quote are different instants (CF 2026-10-14:
                # cap 17.744B ⇒ $117.25/share against a resolved $119.46 close, a
                # 1.88% one-session lag, while the report also printed "+1.88% last
                # session"). The cap feeds EV and every EV-based multiple; the quote
                # feeds upside/downside — publishing both without this note puts two
                # price bases in one artifact.
                cap_implied_price = provider_market_cap / reported_shares
                cap_price_gap = abs(cap_implied_price - current_price) / current_price
                if cap_price_gap > _MARKET_CAP_PRICE_TOL:
                    warnings.append(
                        f"market_cap for {ticker} ({provider_market_cap:,.0f}) implies "
                        f"${cap_implied_price:,.2f}/share against the run's "
                        f"${current_price:,.2f} quote ({cap_price_gap:.1%} apart) — the cap "
                        "and the quote are from different instants (the financials snapshot "
                        "carries its own, older price), so EV and the EV-based multiples ride "
                        "the cap's session while the upside/downside percentages ride the "
                        "quote's. Read the multiples as of the cap's session."
                    )
        else:
            shares = reported_shares
    elif provider_market_cap and provider_market_cap > 0:
        shares = provider_market_cap / current_price
        warnings.append(
            f"shares_outstanding missing or invalid from {fin.provenance.provider} "
            f"for {ticker} — derived as market_cap/price ({shares:,.0f}). "
            "Per-share metrics (EPS, P/E) may be approximate."
        )
        field_warnings.setdefault("pe", []).append(FIELD_WARN_SHARES_DERIVED)
    else:
        raise ValueError(
            f"Neither shares_outstanding nor market_cap available from "
            f"{fin.provenance.provider} for {ticker} — cannot form market_cap/price."
        )

    # --- book value per share on the SAME price-consistent basis as `shares`/EPS ---
    # The provider divided book equity by `reported_shares`; when that count is off
    # the quoted price's basis (BP's /shares-float ~437M vs the ~2.62B ADR count) the
    # per-ordinary bvps ($128) is the ADR ratio × the per-ADR figure ($21). Rescale
    # it in lockstep with `shares` above (same tol, same market_cap/current_price) so
    # the displayed bvps and the comps_pb anchor (peer median P/B × bvps) sit on the
    # per-ADR price basis. No-op / byte-identical for US issuers and price-consistent
    # ADRs (SHEL/HSBC/TSM). `market_cap` is still the raw provider cap here (used
    # verbatim just below).
    bvps_price_consistent, bvps_note = reconcile_book_value_to_price_basis(
        fin.book_value_per_share, reported_shares, provider_market_cap, current_price
    )
    if bvps_note is not None:
        warnings.append(bvps_note)

    # --- market_cap: the provider's reported value, else a labelled fallback ---
    # F3: the old ``market_cap = shares × current_price`` made the cap and the
    # share count mutually derived (a later market_cap/price share-count check is
    # then a tautology). Use the provider's cap when reported; only when it is
    # absent do we derive shares × price and LABEL it as approximate.
    if provider_market_cap and provider_market_cap > 0:
        market_cap = provider_market_cap
    else:
        market_cap = shares * current_price
        warnings.append(
            f"market_cap missing or invalid from {fin.provenance.provider} for {ticker} "
            f"— derived as shares × current_price ({market_cap:,.0f}); treat as approximate."
        )
    mc_ratio = 1.0

    # --- N15: consistent EV handling ---
    # Only compute EV when both total_debt and total_cash are available.
    # Matches prompts.py behavior: no defaulting missing components to 0.
    ev: float | None = None
    ev_ebitda: float | None = None
    ev_ebitda_reported: float | None = None
    ev_revenue: float | None = None

    if raw_debt is not None and raw_cash is not None:
        ev = calculate_ev(
            market_cap,
            total_debt,
            total_cash,
            fin.preferred_stock or 0.0,
            fin.noncontrolling_interest or 0.0,
        )
        ev_ebitda = ev / ebitda_operating if (ebitda_operating and ebitda_operating > 0) else None
        ev_ebitda_reported = (
            ev / ebitda_reported if (ebitda_reported and ebitda_reported > 0) else None
        )
        ev_revenue = ev / revenue if revenue > 0 else None
    else:
        missing_ev_parts = []
        if raw_debt is None:
            missing_ev_parts.append("total_debt")
        if raw_cash is None:
            missing_ev_parts.append("total_cash")
        warnings.append(
            f"{', '.join(missing_ev_parts)} not available from provider — "
            "EV and EV-based multiples (EV/EBITDA, EV/Revenue) cannot be computed"
        )
        field_warnings.setdefault("ev_ebitda", []).append(FIELD_WARN_EV_MISSING_NET_DEBT)

    # Balance-sheet financials (banks / insurers): deposits / float / reserves are
    # operating raw material, not capital structure, and there is no clean above-the-line
    # EBITDA — so enterprise value and EVERY EV-based multiple are category errors
    # (``audit.sector_sign`` flags exactly ``enterprise_value`` + ``ev_ebitda`` for these
    # issuers). Enforce the invariant HERE, at the single canonical FinancialData producer,
    # so NO consumer surface can leak it: the /financials snapshot tile, the historical-bands
    # current override, coverage rows, and the report all read this object. This is the
    # STRUCTURAL gate for the recurring "a new surface forgot to suppress bank EV/EBITDA"
    # family (the live /financials + /historical-bands endpoints were leak surfaces 5 & 6 on
    # 2026-06-26; comps/report suppressed per-path since 06-24). sector_sign is now a pure
    # backstop. Bank-applicable metrics (P/E, P/B, market cap) are untouched — only the
    # EV-based fields are nulled. is_balance_sheet_financial (NOT is_bank) is the wider
    # cash-flow-suppression boundary, matching the comps builder + aggregator.
    if is_balance_sheet_financial(industry=fin.industry, sector=fin.sector):
        ev = None
        ev_ebitda = None
        ev_ebitda_reported = None
        ev_revenue = None

    # 52w high/low from the canonical (windowed to trailing 52 weeks, intraday
    # high/low when present, close fallback otherwise).
    high_52w = price.fifty_two_week_high()
    low_52w = price.fifty_two_week_low()

    # --- P/E: ONE net-income authority ---
    # The provider's ``trailingPE`` rides its own denominator (Yahoo's diluted-EPS
    # basis), so it implied a net income the report never printed (owner review,
    # EHC: 20.8× → ~$590M beside a printed $603.7M income statement and a $621M
    # filing fact). Derive the ratio from the SAME figures the report shows —
    # market_cap ÷ TTM net_income — and stamp that basis on ``MarketData.pe_basis``
    # (a label, NOT a row warning: coverage flips its "partial" flag on any
    # FinancialData.warnings entry). The
    # provider value survives only as a fallback (net income missing / ≤ 0, or a
    # cross-currency ADR whose quote-ccy cap and reporting-ccy net income cannot
    # form a ratio), where it is still marked to the live cap by ``mc_ratio``.
    same_currency = fin.reporting_currency.upper() == fin.quote_currency.upper()
    pe_ratio: float | None
    pe_basis: str | None = None
    if same_currency and fin.net_income is not None and fin.net_income > 0:
        derived_pe = market_cap / fin.net_income
        pe_ratio = derived_pe
        pe_basis = PE_BASIS_NET_INCOME
        if (
            fin.pe_ratio is not None
            and fin.pe_ratio > 0
            and abs(derived_pe - fin.pe_ratio) / fin.pe_ratio > 0.01
        ):
            pe_basis = (
                f"{PE_BASIS_NET_INCOME}; supersedes the provider's trailingPE "
                f"{fin.pe_ratio:,.2f}×, which rides a different denominator"
            )
    else:
        pe_ratio = fin.pe_ratio * mc_ratio if fin.pe_ratio is not None else None

    # --- Operating margin: the income block's OWN leaves ---
    # Same reasoning as the P/E above, on the sibling published ratio: the margin the
    # artifact prints must be the quotient of the two figures it prints beside it. The
    # rule itself lives in ``derive_operating_margin`` so the comps peer path — which
    # publishes the same three fields into a row the comps chapter renders — decides it
    # identically instead of a second time.
    operating_margin, operating_margin_basis = derive_operating_margin(
        fin.operating_income, revenue, fin.operating_margin, warnings=warnings
    )

    # --- Quote basis -------------------------------------------------------
    # A provider that served no quote timestamp served a session CLOSE, not a
    # live tick — the canonical contract already records that as the
    # ``quote_ts_missing`` degradation, so the report can label the price
    # honestly instead of printing "Live" over yesterday's close (owner review
    # 2026-10-13: "Live $124.42" was the Oct 12 close).
    # The flags live on the PRICE feed's provenance (its own ``quote_ts_missing``
    # / ``quote_currency_missing`` codes), not the financials' — and the price's
    # semantic as-of is the latest BAR date, i.e. exactly the session the quote
    # belongs to (EHC: 2026-10-12, the close the report was labelling "Live").
    _quote_degraded = set(price.provenance.degraded) if price.provenance is not None else set()
    quote_is_live = "quote_ts_missing" not in _quote_degraded
    quote_as_of = price.provenance.as_of if price.provenance is not None else None

    # Carry any warnings that arrived on the canonical objects (e.g. cross-validate
    # discrepancies forwarded from raw fetch).
    for w in fin.warnings:
        if w not in warnings:
            warnings.append(w)
    for w in price.warnings:
        if w not in warnings:
            warnings.append(w)

    # --- Reader-visible decision-record coverage (2026-10-13 audit) ------------
    # The report must never present "0 conflicts + degraded []" while the run
    # actually carried a divergence the ``degraded`` marker list cannot express
    # (total_cash is a compared, NON-key field, so it never becomes a structured
    # marker). These counts ride the published ``provenance`` block so the reader
    # sees the run's real standing. ``metrics_decided`` / ``metrics_without_record``
    # describe the FINANCIALS decision record (``data_authority``); the PRICE
    # record is published separately as ``price_authority``.
    fin_decisions = fin.reconciliation.decisions if fin.reconciliation is not None else ()
    decided_metrics = {d.metric for d in fin_decisions}
    compared_metrics = compared_fields()
    metrics_decided = len(decided_metrics)
    metrics_without_record = sum(1 for m in compared_metrics if m not in decided_metrics)
    divergence_warnings = _count_validator_divergences(warnings)

    fin_prov = fin.provenance
    price_prov = price.provenance

    return FinancialData(
        ticker=ticker,
        company_name=fin.company_name or "",
        # As-of of THIS snapshot's headline = the session the displayed
        # current_price belongs to (PRICE canonical's semantic ``as_of``), NOT the
        # FINANCIALS fetch time. The two canonicals have independent TTLs, so the
        # FINANCIALS fetch (which embeds a staler price) can lag the dedicated
        # PRICE canonical by a full session; stamping fin.fetched_at here mislabels
        # the "As of" pill against the fresh price the market block / 13 chapters
        # actually render (AAPL 2026-07-02: pill said 06-30 16:14 while the
        # headline was 07-01's $294.38). The financials' own period is separately
        # carried in ``fiscal_period_end`` / the "TTM 截至 X" label, so no fidelity
        # is lost. Contract: the freshness pill reads the price ``as_of``
        # (normalize/contracts Provenance docstring).
        timestamp=price.provenance.as_of,
        fiscal_period_end=fin.period_end,
        # Carry the TTM constituent quarter-ends so audit.ttm_period can assert the
        # four quarters don't overlap/gap (numeric-audit family-4). Empty on the
        # yfinance / annual paths → the verifier abstains.
        ttm_quarter_ends=fin.ttm_quarter_ends,
        income=IncomeStatement(
            revenue=revenue,
            # None ≠ 0: propagate a missing figure as None so the derived metric
            # is withheld (data unavailable) rather than fabricated as a real 0.
            ebitda=ebitda,
            net_income=fin.net_income,
            # The NCI share of that same TTM net income, so a reader (and the
            # divergence warning below) can tell a consolidation-caliber
            # difference from a data error.
            nci_earnings=fin.nci_earnings,
            # Withhold an economically-impossible margin (>100% / <-500%) so a broken
            # provider figure (UL: FMP grossProfit ≥ revenue) shows N/A instead of
            # crashing the IncomeStatement le bound or printing a fabricated 100%.
            gross_margin=_sanitize_margin(gross_margin, label="gross_margin", warnings=warnings),
            # Derived from THIS block's own operating_income ÷ revenue (see the
            # "Operating margin: the income block's OWN leaves" block above); the
            # provider's own value is the labelled fallback only.
            operating_margin=operating_margin,
            operating_margin_basis=operating_margin_basis,
            operating_income=fin.operating_income,
            depreciation_amortization=fin.depreciation_amortization,
            capital_expenditure=fin.capital_expenditure,
            rd_expense=fin.rd_expense,
            sga_expense=fin.sga_expense,
            interest_expense=fin.interest_expense,
            income_tax_expense=fin.income_tax_expense,
        ),
        balance=BalanceSheet(
            # Preserve None (not reported) into FinancialData — the local
            # total_debt/total_cash are 0-coerced only for the guarded EV calc
            # above; the stored balance must not fabricate a zero (N15/#10).
            total_debt=raw_debt,
            total_cash=raw_cash,
            # EV-bridge completeness (numeric-audit family 3): preferred + NCI are
            # folded into calculate_ev above when reported; carried here so
            # audit.ev_bridge can flag an UNREPORTED (None) one. None ≠ 0.
            preferred_stock=fin.preferred_stock,
            noncontrolling_interest=fin.noncontrolling_interest,
        ),
        market=MarketData(
            market_cap=market_cap,
            shares_outstanding=shares,
            current_price=current_price,
            pe_ratio=pe_ratio,
            # Names the P/E's denominator (see the block above); None when the
            # provider's own ratio was kept as the fallback.
            pe_basis=pe_basis,
            quote_is_live=quote_is_live,
            quote_as_of=quote_as_of,
            price_52w_high=high_52w,
            price_52w_low=low_52w,
            # Same canonical PRICE object the 52w high/low above derive from —
            # single source, self-consistent (thesis-prompt momentum context).
            trailing_1y_return_pct=price.trailing_1y_return_pct(),
            industry=fin.industry,
            sector=fin.sector,
            country=fin.country,
            is_adr=fin.is_adr,
            beta=fin.beta,
        ),
        valuation=ValuationMetrics(
            enterprise_value=ev,
            ebitda_operating=ebitda_operating,
            ebitda_reported=ebitda_reported,
            ev_ebitda=ev_ebitda,
            ev_ebitda_reported=ev_ebitda_reported,
            ev_revenue=ev_revenue,
            # Per-ADR (price-consistent) per-share book value, carried for the cyclical
            # comps P/B method (the target's pb_ratio is derived in
            # build_xbrl_aligned_company from this bvps × the reconciled shares above,
            # so it stays self-consistent = market_cap/book_equity).
            book_value_per_share=bvps_price_consistent,
        ),
        # Carry the currency tags so a foreign target (TWD financials, USD
        # market_cap) can be FX-normalized in build_xbrl_aligned_company before
        # comps multiples — without these the target defaulted to USD/USD and
        # core_pe collapsed for ADRs (BUG-018).
        reporting_currency=fin.reporting_currency,
        quote_currency=fin.quote_currency,
        data_source=fin.provenance.provider,
        provenance=DataProvenance(
            provider=fin.provenance.provider,
            as_of=fin.period_end,
            period_basis=fin.period_basis,
            pe_ttm_lag_quarters=fin.pe_ttm_lag_quarters,
            # Combine financials degraded flags (ttm_lag) with the price
            # feed's (close_only) since the snapshot shows both 52w (price)
            # and P/E (financials) numbers.
            degraded=list(dict.fromkeys([*fin.provenance.degraded, *price.provenance.degraded])),
            # The two canonicals' TRUE fetch instants + cache state, published so
            # a reader can tell a fetch from a session close (the audited brief
            # rendered a session close as "Fetched" and attributed the financials'
            # provenance to the price). ``retrieved_at``/``from_cache`` describe the
            # FINANCIALS canonical (the block's provider/as_of/period_basis);
            # ``price_*`` describe the PRICE canonical paired with
            # ``price_authority``; ``session_as_of`` is the quote's session (=
            # ``timestamp``). Never NULL-overwritten: a genuine None means the
            # instant was not reported, not that it matched.
            retrieved_at=fin_prov.fetched_at,
            from_cache=fin_prov.from_cache,
            price_retrieved_at=price_prov.fetched_at if price_prov is not None else None,
            price_from_cache=price_prov.from_cache if price_prov is not None else None,
            session_as_of=price_prov.as_of if price_prov is not None else None,
            metrics_decided=metrics_decided,
            metrics_without_record=metrics_without_record,
            divergence_warnings=divergence_warnings,
        ),
        warnings=warnings,
        field_warnings=field_warnings,
        # The FINANCIALS decision record ONLY — never the price's. A price-only
        # record must not masquerade as the financials authority (2026-10-13
        # audit); ``None`` here means the financial metrics have NO decision
        # record, which ``provenance.metrics_without_record`` discloses. The PRICE
        # record rides under its own key so the two objects stay distinguishable.
        data_authority=fin.reconciliation,
        price_authority=price.reconciliation,
    )


def extract_company_financials(fin: NormalizedFinancials) -> CompanyFinancials:
    """Project NormalizedFinancials into CompanyFinancials for a peer comps row.

    Runs the SAME EBITDA-caliber logic as the target path
    (``extract_financial_data``) so the peer EV/EBITDA numerator matches the
    target's instead of mixing calibers:

    - **EBITDA = operating caliber (EBIT + D&A)** recomputed from line items,
      falling back to the provider's reported ``ebitda`` only when operating
      components are absent. Previously the peer used the raw provider
      ``ebitda`` (reported caliber: NI+tax+interest+D&A) while the target used
      operating — for cash-rich peers the two differ materially and the table
      compared apples to oranges.
    - **total_debt / total_cash stay None when the provider omits them** so
      ``calculate_multiples`` withholds EV instead of fabricating EV=market_cap
      and poisoning the median. Previously ``or 0`` silently assumed zero net debt.

    ``reporting_currency`` carries the provider's IS/BS currency tag (ISO 4217,
    taken at face value — see normalize.currency) so the downstream FX step
    converts before EV/EBITDA is computed. Raises ValueError for missing
    revenue/market_cap so the caller drops the peer rather than comparing zeros.
    """
    ticker = fin.ticker

    revenue = fin.revenue
    market_cap = fin.market_cap
    if not revenue:
        raise ValueError(f"Missing or zero revenue for peer {ticker}")
    if not market_cap:
        raise ValueError(f"Missing or zero market_cap for peer {ticker}")

    # Operating EBITDA (EBIT + D&A) is the canonical EV/EBITDA numerator since
    # EV already nets out cash. Reported fallback only when components missing —
    # identical treatment to the target so neither side fabricates a caliber.
    ebitda_operating = calculate_ebitda_operating(
        fin.operating_income, fin.depreciation_amortization
    )
    if ebitda_operating is None:
        ebitda_operating = fin.ebitda

    # P/B = market_cap / book equity (book equity = bvps × shares). Computed ONLY
    # for single-currency issuers (reporting == quote): market_cap is quote-ccy and
    # book equity is reporting-ccy, so a TWD/USD ADR would mix units (the same leg
    # forward_pe / pe_ratio gate on). US memory/storage peers (MU/WDC/STX/SNDK) are
    # all USD/USD → clean; a foreign memory peer leaves pb_ratio None and falls back
    # to P/E in the comps median rather than printing a cross-currency P/B. Withheld
    # (None) on non-positive book equity — a negative-equity P/B is meaningless.
    bvps = fin.book_value_per_share
    pb_ratio: float | None = None
    single_currency = fin.reporting_currency == fin.quote_currency
    if (
        single_currency
        and bvps is not None
        and bvps > 0
        and fin.shares_outstanding is not None
        and fin.shares_outstanding > 0
        and market_cap > 0
    ):
        pb_ratio = market_cap / (bvps * fin.shares_outstanding)

    # pb_ratio above stays on the self-consistent RAW pair (bvps × shares =
    # book_equity, so pb = market_cap/book_equity is byte-identical and correct even
    # when the provider count is off the price basis). The CARRIED book value is
    # separately re-expressed on the per-ADR price basis so a peer's displayed bvps is
    # coherent with its price (no-op for US / price-consistent peers). Only the target
    # row's bvps feeds comps_pb as an anchor, but keeping the peer's coherent avoids a
    # latent per-ordinary figure leaking into any future consumer.
    bvps_anchor, _bvps_note = reconcile_book_value_to_price_basis(
        bvps, fin.shares_outstanding, market_cap, fin.current_price
    )

    # The comps chapter renders this margin beside this row's revenue, so it is decided
    # by the SAME rule the target path uses (``derive_operating_margin``) — the
    # provider's own margin divides its frame's revenue, not this row's. The label has no
    # home here (a peer row carries no provenance block) and is discarded.
    operating_margin, _margin_basis = derive_operating_margin(
        fin.operating_income, revenue, fin.operating_margin
    )

    return CompanyFinancials(
        ticker=ticker,
        name=fin.company_name,
        revenue=revenue,
        # None ≠ 0: propagate a missing figure as None so the affected multiple is
        # withheld (data unavailable) rather than computed against a fabricated 0.
        ebitda=ebitda_operating,
        net_income=fin.net_income,
        market_cap=market_cap,
        total_debt=fin.total_debt,
        total_cash=fin.total_cash,
        # EV-bridge completeness: carry preferred + NCI so calculate_multiples folds
        # them into this company's EV (symmetric with the target extract path).
        preferred_stock=fin.preferred_stock,
        noncontrolling_interest=fin.noncontrolling_interest,
        # Banks have no COGS — suppress the meaningless gross margin so a bank
        # peer row doesn't show ~60% (FMP) / 0% (yfinance). Symmetric with the
        # target path (extract_financial_data) and the FMP provider source fix.
        # A >100% (impossible) margin is withheld too so a broken provider figure
        # doesn't print a fabricated 100% in the comps table (peer path has no
        # warnings channel — silent withhold, mirroring how peers drop other fields).
        gross_margin=None
        if is_bank(industry=fin.industry, sector=fin.sector)
        else _sanitize_margin(fin.gross_margin, label="gross_margin"),
        operating_margin=operating_margin,
        # Period-consistent EBIT for NOPAT core P/E (BUG-017) — preferred over
        # operating_margin × revenue once revenue may be XBRL-reconciled.
        operating_income=fin.operating_income,
        pe_ratio=fin.pe_ratio,
        # P/B (cyclical comps multiple) + the per-ADR per-share book value. bvps is
        # reporting-ccy (FX-scaled with the other reporting items in
        # normalize_company_to_usd); pb_ratio is computed single-currency above from
        # the raw pair so it's already dimensionless and unaffected by the anchor's
        # per-ADR rescale.
        book_value_per_share=bvps_anchor,
        pb_ratio=pb_ratio,
        income_tax_expense=fin.income_tax_expense,
        reporting_currency=fin.reporting_currency,
        quote_currency=fin.quote_currency,
    )


async def normalize_peer_to_usd(
    company: CompanyFinancials, *, fmp_api_key: str | None = None
) -> CompanyFinancials:
    """Convert a peer's IS/BS items (and market_cap if quoted in non-USD) to
    canonical USD using today's spot FX. No-op fast path when both currency
    tags are already USD — the common case for US peers.

    ``fmp_api_key`` is forwarded to the FX layer as a fallback source so a
    yfinance rate-limit storm doesn't drop an otherwise-fetchable foreign peer.

    Lives here (a compute coordinator, alongside ``extract_company_financials``)
    rather than in any one pipeline so BOTH the comps pipeline AND the
    ``analyze competitors`` path normalize peers through the identical FX recipe
    — there is exactly one comps normalization path, never two (BUG-016).
    """
    if company.reporting_currency == "USD" and company.quote_currency == "USD":
        return company
    # Lazy: fx pulls yfinance; kept off the cold-start import path (test_cold_import).
    from finrobot.engine.data.providers.fx import fetch_fx_rate_to_usd

    reporting_rate = (
        1.0
        if company.reporting_currency == "USD"
        else await fetch_fx_rate_to_usd(company.reporting_currency, fmp_api_key=fmp_api_key)
    )
    if company.quote_currency == "USD":
        quote_rate = 1.0
    elif company.quote_currency == company.reporting_currency:
        # Local listing (e.g. 2330.TW): both tags equal, reuse the rate.
        quote_rate = reporting_rate
    else:
        quote_rate = await fetch_fx_rate_to_usd(company.quote_currency, fmp_api_key=fmp_api_key)
    return normalize_company_to_usd(company, reporting_rate, quote_rate)


async def normalize_financials_to_usd(
    financials: FinancialData, *, fmp_api_key: str | None = None
) -> FinancialData:
    """Convert a ticker's IS/BS items (and market_cap/price if quoted non-USD) to
    canonical USD using today's spot FX. No-op fast path when both currency tags
    are already USD — the common US-issuer case.

    The ``FinancialData`` sibling of :func:`normalize_peer_to_usd`: the single
    async fetch-and-normalize recipe every absolute-valuation seed caller (DCF /
    DDM / IC-memo pipelines + the dcf-seed route) runs BEFORE
    ``seed_dcf_inputs`` / ``seed_ddm_inputs``, so a foreign issuer's TWD
    revenue/net_income/debt never mixes with its USD market_cap (BUG-073). The
    seed leaves stay pure/sync; the async FX read happens here.

    ``fmp_api_key`` is forwarded to the FX layer as a fallback source so a
    yfinance rate-limit storm doesn't strand an otherwise-fetchable foreign rate.
    """
    if financials.reporting_currency == "USD" and financials.quote_currency == "USD":
        return financials
    # Lazy: fx pulls yfinance; kept off the cold-start import path (test_cold_import).
    from finrobot.engine.data.providers.fx import fetch_fx_rate_to_usd

    reporting_rate = (
        1.0
        if financials.reporting_currency == "USD"
        else await fetch_fx_rate_to_usd(financials.reporting_currency, fmp_api_key=fmp_api_key)
    )
    if financials.quote_currency == "USD":
        quote_rate = 1.0
    elif financials.quote_currency == financials.reporting_currency:
        # Local listing (e.g. 2330.TW): both tags equal, reuse the rate.
        quote_rate = reporting_rate
    else:
        quote_rate = await fetch_fx_rate_to_usd(financials.quote_currency, fmp_api_key=fmp_api_key)
    return normalize_financialdata_to_usd(financials, reporting_rate, quote_rate)


def extract_price_history(price: NormalizedPrice) -> PriceHistory:
    """Project NormalizedPrice into PriceHistory.

    Reads typed bars (``price.bars``) instead of raw dict ``data.get()``.
    avg_price = mean of bar closes; data_points = number of bars;
    52w high/low from the canonical derived methods (intraday high/low
    with close fallback, window already trimmed to trailing 52 weeks).
    """
    closes = [b.close for b in price.bars]
    avg = sum(closes) / len(closes) if closes else 0.0
    high_52w = price.fifty_two_week_high()
    low_52w = price.fifty_two_week_low()
    return PriceHistory(
        ticker=price.ticker,
        period="1y",
        data_points=len(price.bars),
        current_price=price.current_price,
        high_52w=high_52w if high_52w is not None else 0.0,
        low_52w=low_52w if low_52w is not None else 0.0,
        avg_price=avg,
    )
