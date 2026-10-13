"""Instrument classification — is this symbol an operating company or a fund?

The ticker chokepoint (``engine.data.ticker.validate_ticker``) is deliberately
*purely syntactic*: it validates 1–12 chars of ``A-Z0-9.-`` and nothing else, so
``VTSAX`` and ``IEI`` are as "valid" as ``AAPL``. Until this module existed, no
code anywhere distinguished an investment fund from an operating company. The
consequence was measured on the live providers, not assumed:

* ``fetch_canonical(PRICE)`` works for a fund (both EODHD and Yahoo quote it);
* ``fetch_canonical(FINANCIALS)`` succeeds *without raising* and returns a
  contract whose company fields are all ``None`` — IEI: revenue / ebitda /
  net_income / market_cap / total_debt / sector all ``None``; VTSAX likewise.
  The data layer's only non-syntactic gate is geographic
  (``ticker.is_us_equity_ticker``, CN/HK suffixes, backtest-only), which passes
  a fund;
* the equity pipeline then died at ``extract_financial_data`` with
  ``ValueError: Missing or zero revenue for IEI`` — a category error reported as
  a missing number, after a full LLM pipeline had been paid for.

``quote_type`` is the provider's own statement of what the security IS, and it
arrives in the same payload the financials arm already reads (Yahoo
``info["quoteType"]``: ``EQUITY`` / ``ETF`` / ``MUTUALFUND``; EODHD
``General.Type``: ``Common Stock`` / ``ETF`` / ``FUND``). This module maps that
vendor vocabulary onto one internal vocabulary so the pipeline layer can route
instead of misinterpret.

Deliberate boundary: only *classification* lives here. Nothing in this module
decides what a fund is worth — a fund has no revenue, EBITDA, free cash flow or
enterprise value, so the DCF/EV/multiples stack is undefined for it and a
separate pipeline computes NAV-based measures instead.
"""

from __future__ import annotations

import re
from enum import StrEnum

__all__ = [
    "COMPANY_QUOTE_TYPES",
    "FUND_QUOTE_TYPES",
    "FundInstrumentError",
    "InstrumentType",
    "classify_instrument",
    "is_fund_quote_type",
    "normalize_quote_type",
]


class InstrumentType(StrEnum):
    """What kind of security a symbol denotes.

    ``UNKNOWN`` is a real answer, not a failure: a provider that returns no
    ``quote_type`` (or a value outside both vocabularies) has told us nothing,
    and callers must not treat "not proven a fund" as "proven a company".
    """

    COMPANY = "company"
    FUND = "fund"
    UNKNOWN = "unknown"


#: Vendor ``quote_type`` values that denote a pooled investment vehicle. Covers
#: Yahoo (``ETF``, ``MUTUALFUND``, ``CLOSED-END FUND``), EODHD (``FUND``,
#: ``ETF``) and the SEC-derived spellings, compared after :func:`normalize_quote_type`.
FUND_QUOTE_TYPES: frozenset[str] = frozenset(
    {
        "ETF",
        "MUTUALFUND",
        "MUTUAL FUND",
        "FUND",
        "CLOSED END FUND",
        "CLOSEDEND FUND",
        "CEF",
        "MONEY MARKET FUND",
        "MONEYMARKETFUND",
        "UNIT INVESTMENT TRUST",
    }
)

#: Vendor values that denote a single operating issuer. ``REIT``/``ADR`` are
#: operating companies for this purpose (they file 10-K/10-Q and have revenue) —
#: the repo already handles their *sector* quirks in the valuation operators.
COMPANY_QUOTE_TYPES: frozenset[str] = frozenset(
    {
        "EQUITY",
        "STOCK",
        "COMMON STOCK",
        "COMMONSTOCK",
        "ADR",
        "REIT",
        "PREFERRED STOCK",
    }
)

#: Separator/whitespace normalization for vendor spellings: ``MUTUAL_FUND``,
#: ``mutual-fund`` and ``Mutual Fund`` all collapse to one key.
_SEPARATOR_RE = re.compile(r"[\s_\-]+")


def normalize_quote_type(raw: str | None) -> str | None:
    """Uppercase + collapse separators of a vendor ``quote_type``, or ``None``.

    ``None``/blank input returns ``None`` (absent stays absent) — never ``""``,
    so callers can distinguish "the provider said nothing" from "the provider
    said something unrecognized".
    """
    if raw is None:
        return None
    text = _SEPARATOR_RE.sub(" ", str(raw).strip()).strip().upper()
    return text or None


def classify_instrument(quote_type: str | None) -> InstrumentType:
    """Map a provider ``quote_type`` onto :class:`InstrumentType`.

    Unrecognized values are ``UNKNOWN`` rather than ``COMPANY``: the equity
    pipelines get their fail-fast message from a *positive* fund identification,
    so an unknown value must not silently promise "this is an operating company".
    """
    normalized = normalize_quote_type(quote_type)
    if normalized is None:
        return InstrumentType.UNKNOWN
    if normalized in FUND_QUOTE_TYPES:
        return InstrumentType.FUND
    if normalized in COMPANY_QUOTE_TYPES:
        return InstrumentType.COMPANY
    return InstrumentType.UNKNOWN


def is_fund_quote_type(quote_type: str | None) -> bool:
    """True only for a *positively identified* fund (never for ``None``/unknown)."""
    return classify_instrument(quote_type) is InstrumentType.FUND


class FundInstrumentError(ValueError):
    """An operating-company pipeline was handed a positively identified fund.

    Raised at the equity extractor chokepoint BEFORE the missing-revenue branch,
    so a fund can never again surface as ``ValueError: Missing or zero revenue
    for IEI`` — a category error reported as a missing number, after a full LLM
    pipeline had already been paid for. The message names the ticker, states that
    it is a fund, and points at the pipeline + CLI command that DO apply.

    Subclasses ``ValueError`` so existing ``except ValueError`` call sites keep
    their behaviour; it is deliberately NOT a ``ProviderError`` (nothing failed to
    fetch — the caller asked the wrong pipeline).
    """

    def __init__(self, ticker: str, quote_type: str | None = None) -> None:
        detail = f" (quoteType={quote_type!r})" if quote_type else ""
        super().__init__(
            f"'{ticker}'{detail} is an investment fund, not an operating company. A fund "
            "files no income statement, so revenue / EBITDA / enterprise value are "
            "undefined for it and the equity pipelines cannot value it. Run the fund "
            "pipeline instead: pipeline key 'fund_research' (CLI: `finrobot fund "
            f"{ticker}`)."
        )
        self.ticker = ticker
        self.quote_type = quote_type
