"""What a cached provider payload's fields MEAN — declared once, digested so a
silent meaning change cannot slip past the cache.

Why this module exists (the 2026-10-14 CF incident): a FINANCIALS canonical row
lives 24h. The yfinance margins were fixed in code (``4e1a75f``) but the raw and
canonical version tags were unchanged, so a report generated nine hours later was
built from a payload cached fourteen hours BEFORE the fix and published
``operating_margin = 0.49325`` beside operands that divide to ``0.39088``. The
version tag was hand-maintained in a different file from the payload it described
(``cache._RAW_SLOT_VERSION``), so nothing forced the author to notice the drift.

This module removes the "different file, hand-maintained" hole. It declares, per
:class:`~finrobot.engine.data.types.DataType` (and per provider where the meaning
differs), the fields the normalize/consumer path depends on — each with its unit,
caliber and basis — and produces :func:`semantics_digest`, a stable digest over
that declaration PLUS the SHA-256 of the producing provider module's source file.
Any edit to a provider's source (even a comment) or to a declared field's meaning
moves the digest, and :func:`cache.raw_slot_key` / :func:`cache.canonical_key`
bake it into the slot tag so the row self-invalidates.

The precedent is the schema-evolution rule two wire formats state directly: Avro
requires data to be read with the schema that WROTE it and only lets defaults fill
absent fields (https://avro.apache.org/docs/1.12.0/specification/), and protobuf
states the wire format provides no way to detect a field encoded with one
definition and decoded with another
(https://protobuf.dev/programming-guides/proto3/). A cached payload is exactly that
wire: this module is the "schema that wrote it".

Design, deliberately boring: the declarations are DATA, and :func:`semantics_digest`
is a pure function of that data plus the on-disk source of the declared producers.
It reads only its own package's provider source files (deterministic, offline),
never the cache or the network, and memoizes them per path so the cache hot path
stays a dict lookup.

Leaf: standard library only (plus the ``DataType`` StrEnum leaf); no cache/network I/O.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from finrobot.engine.data.types import DataType

__all__ = [
    "RAW_SLOT_VERSION",
    "FieldSemantics",
    "FIELD_SEMANTICS",
    "PROVIDER_FIELD_SEMANTICS",
    "PRODUCERS",
    "PROVIDER_MODULE",
    "semantics_rev",
    "declared_fields",
    "producer_modules",
    "semantics_digest",
    "declared_pairs",
]

#: Repository root (``finrobot_desktop/``); provider source paths below are
#: relative to it. ``semantics.py`` = ``<root>/finrobot/engine/data/semantics.py``.
_REPO_ROOT = Path(__file__).resolve().parents[3]

#: Digest length. 12 hex chars (48 bits) of a SHA-256 is ample for a slot tag and
#: matches ``identities.identity_digest`` so the two halves of a canonical key read
#: the same way.
_DIGEST_CHARS = 12


# Raw provider-slot format versions. Bump when a provider's cached RAW payload
# SHAPE changes incompatibly, so old entries are ignored (treated as a miss)
# and refetched, instead of feeding a stale format into the compute layer.
# Without this a long-TTL type silently serves the old shape until expiry.
#   proxy_statement v2 — 2026-06-02: the DEF 14A text slice was re-anchored on
#   the real Summary Compensation Table; pre-v2 slices miss the SCT + pay-ratio
#   for large issuers, so the comp parser can't recover from them (7-day TTL).
#   peer_candidates v2 — 2026-06-05: candidate profiles were added so the
#   deterministic peer screen can reject value-chain partners (foundry /
#   equipment) before comps math consumes them.
#   price v2 — 2026-06-07: canonical PRICE now relies on the validated
#   fetch_price() path. Old raw PRICE rows may have been written by bare fetch()
#   without cross-source quote validation, so they must not seed the canonical
#   slot.
#   sentiment v2 — 2026-06-10: source_alignment switched from free English
#   phrases ('Wide divergence' …) to stable enum tokens; the route schema now
#   validates against the AlignmentToken Literal, so pre-token rows must miss.
#   forward_estimates v2 — 2026-06-11: FMP v3→stable migration renamed every
#   estimate figure (estimatedRevenueAvg → revenueAvg, estimatedEpsAvg →
#   epsAvg, …); the operator reads stable names only, so legacy-named cached
#   rows would parse as "no estimates" until TTL expiry.
#   financials v2 — 2026-06-14: the FMP financials payload now carries
#   book_value_per_share ((totalStockholdersEquity − preferred) ÷ shares); legacy
#   rows omit it, so a cyclical's comps_pb (book-value primary multiple) can never
#   revive from a cached row — old rows must miss + refetch. Pairs with the
#   CANONICAL_CONTRACT_VERSION v7 bump, which invalidates the normalized slot that
#   is read ahead of this raw slot.
#   financials v3 — 2026-06-22: the FMP financials payload now carries
#   dividend_per_share / payout_ratio / dividend_yield (/ratios-ttm) and
#   return_on_equity (/key-metrics-ttm). Legacy rows omit them, so the DDM seed
#   can never recover a dividend on an FMP-primary ticker (raises "no dividend").
#   Pairs with the CANONICAL_CONTRACT_VERSION v8 bump.
#   price v3 — 2026-07-01: full PRICE provider payloads now carry quote_currency.
#   Legacy PRICE rows omit it and would normalize to UNKNOWN (or, pre-v9, USD),
#   so they must miss and refetch instead of feeding mixed-currency comparisons.
#   financials v4 — 2026-07-06: the TTM aggregation window is now cadence-aware
#   (semi-annual filers sum 2 six-month rows, not 4). Legacy raw rows cached the
#   doubled sum-of-4 aggregate (UL revenue ~127B vs a ~50B year), so they must miss
#   and re-aggregate. Pairs with the CANONICAL_CONTRACT_VERSION v10 bump (the
#   normalized slot, read ahead of this raw slot).
#   peer_candidates v3 — 2026-07-07: the payload now carries a top-level ``active``
#   map (isActivelyTrading per candidate) so the peer screen can drop a delisted /
#   renamed listing (VMware VMW, old Block SQ). Legacy v2 rows have no ``active`` key,
#   so every candidate reads as UNKNOWN and a dead ticker keeps shipping until the 1h
#   TTL — they must miss + refetch to pick up the liveness signal. PEER_CANDIDATES is
#   a RAW-only type (never fetched via fetch_canonical, see layer._CANONICAL_TYPES), so
#   this is the ONLY layer to bump — CANONICAL_CONTRACT_VERSION must NOT move.
#   financials v5 — 2026-10-12: the yfinance financials payload now carries
#   preferred_stock / noncontrolling_interest, read off its balance-sheet DataFrame
#   (the statement module's ``Preferred Stock`` / ``Minority Interest`` rows), and the
#   Tiingo caliber no longer maps its INCOME-STATEMENT ``nonControllingInterests`` flow
#   onto that balance-sheet field. Legacy yfinance rows omit both, so a run served from
#   one reports the EV bridge as unverifiable (or, on Tiingo, folds a year of NCI
#   earnings into EV as if it were an equity claim). Pairs with the
#   CANONICAL_CONTRACT_VERSION v11 bump (the normalized slot, read ahead of this raw
#   slot).
#   financials v6 — 2026-10-14: the yfinance financials payload now DERIVES
#   gross_margin / operating_margin from its own TTM statement frame and never
#   publishes Yahoo's ``info.operatingMargins`` / ``info.grossMargins`` scalar in
#   place of a frame row (the margins gain a ``*_margin_basis`` tag; operating
#   margin is WITHHELD rather than scalar-filled when the frame carries no
#   Operating Income row). A pre-v6 row can carry a margin whose numerator and
#   denominator contradict the same block's own revenue + operating_income, and
#   because the canonical slot is read BEFORE this raw slot with a 24h TTL, a run
#   inside that window publishes the contradiction (CF 2026-10-14: operating
#   margin 0.49325 beside OI 3,025 / revenue 7,739 = 39.1% — and above the same
#   block's 42.5% gross margin, which is impossible). Pairs with the
#   CANONICAL_CONTRACT_VERSION v13 bump. Observed: CF's canonical cached
#   2026-10-14T06:19Z (pre-fix) still served the pre-fix margin hours after the fix
#   landed, and the report shipped the contradiction.
#   schedule_13 v2 — 2026-10-16: the 13D/13G cover-page parser now reads the
#   "Percent of Class" value off the FULL Row-11 caption ("PERCENT OF CLASS
#   REPRESENTED BY AMOUNT IN ROW 9" → "8.28%"), not only off a compact label whose
#   value sits within a short non-digit run. A pre-v2 row stores
#   ``pct_of_class: null`` for those layouts, and the consumer uses that
#   percentage to infer whether an as-filed share count predates a split: Vanguard's
#   NVDA 13G/A (2024-02-13, pre the June-2024 10:1 split) therefore rendered as
#   204.50M shares with NO basis beside BlackRock's split-adjusted 1.81B row — a
#   10x understatement of a 5%+ holder, invisible to the reader (review 2026-10-16,
#   item 3). The 24h row would otherwise keep serving it: SCHEDULE_13 was an
#   UNVERSIONED raw type, so neither a revision nor a digest guarded its slot.
RAW_SLOT_VERSION: dict[str, int] = {
    DataType.PRICE.value: 3,
    DataType.PROXY_STATEMENT.value: 2,
    DataType.PEER_CANDIDATES.value: 3,
    DataType.SENTIMENT.value: 2,
    DataType.FORWARD_ESTIMATES.value: 2,
    DataType.FINANCIALS.value: 6,
    DataType.SCHEDULE_13.value: 2,
}


@dataclass(frozen=True)
class FieldSemantics:
    """The meaning of one field in a cached provider payload.

    ``unit`` names what the number IS (``USD``, ``USD_per_share``, ``shares``,
    ``ratio_fraction``, ``percent``, ``multiple``, ``seconds`` …); ``caliber``
    names the measurement convention (``ttm_flow`` vs ``point_in_time_stock``,
    ``split_dividend_adjusted``, ``reported_vs_operating`` …); ``basis`` names
    where it comes from (``income_statement`` / ``balance_sheet`` / ``quote`` /
    ``derived``). ``note`` carries a required nuance the unit/caliber/basis cannot
    (e.g. "withheld when the frame has no Operating Income row") in one line.
    """

    field: str
    unit: str
    caliber: str
    basis: str
    note: str = ""


#: The fields whose meaning the normalize/consumer path depends on, keyed by the
#: BASE data type. A type absent here declares no field semantics, so only the
#: human revision (or a provider source edit, via the sources pin) can move it.
FIELD_SEMANTICS: Mapping[str, tuple[FieldSemantics, ...]] = {
    DataType.FINANCIALS.value: (
        FieldSemantics("revenue", "USD", "ttm_flow", "income_statement"),
        FieldSemantics("operating_income", "USD", "ttm_flow", "income_statement"),
        FieldSemantics("net_income", "USD", "ttm_flow", "income_statement"),
        FieldSemantics("ebitda", "USD", "ttm_flow", "derived"),
        FieldSemantics("gross_profit", "USD", "ttm_flow", "income_statement"),
        FieldSemantics(
            "gross_margin",
            "ratio_fraction",
            "ttm_flow",
            "derived",
            "gross_profit / revenue; never a vendor info.*Margins scalar",
        ),
        FieldSemantics(
            "operating_margin",
            "ratio_fraction",
            "ttm_flow",
            "derived",
            "operating_income / revenue; withheld (never scalar-filled) when the "
            "frame carries no Operating Income row — the 2026-10-14 CF case",
        ),
        FieldSemantics("total_debt", "USD", "point_in_time_stock", "balance_sheet"),
        FieldSemantics("total_cash", "USD", "point_in_time_stock", "balance_sheet"),
        FieldSemantics("preferred_stock", "USD", "point_in_time_stock", "balance_sheet"),
        FieldSemantics(
            "noncontrolling_interest",
            "USD",
            "point_in_time_stock",
            "balance_sheet",
            "a balance-sheet equity claim, never an income-statement flow",
        ),
        FieldSemantics(
            "book_value_per_share",
            "USD_per_share",
            "point_in_time_stock",
            "derived",
            "(totalStockholdersEquity − preferred) ÷ shares",
        ),
        FieldSemantics("dividend_per_share", "USD_per_share", "ttm_flow", "declared"),
        FieldSemantics("payout_ratio", "ratio_fraction", "ttm_flow", "derived"),
        FieldSemantics("return_on_equity", "ratio_fraction", "ttm_flow", "derived"),
        FieldSemantics("shares_outstanding", "shares", "point_in_time_stock", "quote"),
        FieldSemantics(
            "market_cap",
            "USD",
            "point_in_time_stock",
            "quote",
            "shares x price at the quote instant",
        ),
    ),
    DataType.PRICE.value: (
        FieldSemantics(
            "price",
            "USD_per_share",
            "derived_from_bars",
            "quote",
            "the current close of the split+dividend-adjusted series",
        ),
        FieldSemantics("quote_currency", "currency_code", "as_reported", "quote"),
        FieldSemantics("price_52w_high", "USD_per_share", "split_dividend_adjusted", "bars"),
        FieldSemantics("price_52w_low", "USD_per_share", "split_dividend_adjusted", "bars"),
        FieldSemantics(
            "trailing_1y_return_pct",
            "percent",
            "dividend_inclusive",
            "bars",
            "auto-adjusted bars; NOT a price-only return",
        ),
    ),
    DataType.FORWARD_ESTIMATES.value: (
        FieldSemantics("revenueAvg", "USD", "forward_estimate", "analyst_consensus"),
        FieldSemantics("epsAvg", "USD_per_share", "forward_estimate", "analyst_consensus"),
        FieldSemantics("ebitdaAvg", "USD", "forward_estimate", "analyst_consensus"),
        FieldSemantics("netIncomeAvg", "USD", "forward_estimate", "analyst_consensus"),
        FieldSemantics("fiscalYear", "fiscal_year", "period_label", "analyst_consensus"),
    ),
    DataType.PEER_CANDIDATES.value: (
        FieldSemantics("symbol", "ticker", "as_reported", "screener"),
        FieldSemantics("marketCap", "USD", "point_in_time_stock", "quote"),
        FieldSemantics("price", "USD_per_share", "point_in_time_stock", "quote"),
        FieldSemantics(
            "active",
            "bool",
            "liveness",
            "screener",
            "isActivelyTrading; drops a delisted/renamed listing before the screen",
        ),
        FieldSemantics("sector", "label", "as_reported", "profile"),
    ),
    DataType.SENTIMENT.value: (
        FieldSemantics(
            "source_alignment",
            "enum_token",
            "cross_source",
            "aggregated",
            "a stable AlignmentToken, never free English prose",
        ),
        FieldSemantics("score", "ratio_fraction", "signed", "aggregated"),
    ),
    DataType.PROXY_STATEMENT.value: (
        FieldSemantics(
            "text",
            "text",
            "summary_compensation_table_anchor",
            "def_14a",
            "re-anchored on the real SCT so the comp parser recovers it",
        ),
        FieldSemantics("total_comp", "USD", "fiscal_year", "summary_compensation_table"),
    ),
    DataType.FUND_PROFILE.value: (
        FieldSemantics("nav", "USD_per_share", "point_in_time", "fund_summary"),
        FieldSemantics("total_net_assets", "USD", "point_in_time", "fund_summary"),
        FieldSemantics(
            "expense_ratio",
            "ratio_fraction",
            "annual",
            "fund_summary",
            "vendors mix percent and fraction in one payload — normalized to a fraction",
        ),
        FieldSemantics("distribution_yield", "ratio_fraction", "trailing_12m", "fund_summary"),
        FieldSemantics("trailing_returns", "ratio_fraction", "trailing_window", "fund_summary"),
        FieldSemantics("sector_weights", "ratio_fraction", "of_net_assets", "fund_summary"),
        FieldSemantics(
            "top_holdings",
            "position",
            "of_net_assets",
            "vendor_excerpt",
            "a truncated vendor excerpt, NOT the fund's full filed portfolio",
        ),
    ),
    DataType.FUND_HOLDINGS.value: (
        FieldSemantics(
            "holdings[].weight",
            "ratio_fraction",
            "of_net_assets",
            "n_port",
            "the fund's own filed portfolio, not a top-N excerpt",
        ),
        FieldSemantics("holdings[].value", "USD", "point_in_time", "n_port"),
        FieldSemantics(
            "series_id",
            "id",
            "as_reported",
            "n_port",
            "matches the filing to the ticker's series (siblings share a CIK)",
        ),
    ),
}

#: Provider-specific field semantics where a provider's caliber differs from the
#: type default. Presence here REPLACES :data:`FIELD_SEMANTICS` for that
#: ``(data_type, provider)`` pair — the provider's declaration is authoritative.
PROVIDER_FIELD_SEMANTICS: Mapping[tuple[str, str], tuple[FieldSemantics, ...]] = {
    (DataType.FINANCIALS.value, "yfinance"): (
        FieldSemantics("revenue", "USD", "ttm_flow", "ttm_statement_frame"),
        FieldSemantics("operating_income", "USD", "ttm_flow", "ttm_statement_frame"),
        FieldSemantics("net_income", "USD", "ttm_flow", "ttm_statement_frame"),
        FieldSemantics("ebitda", "USD", "ttm_flow", "derived"),
        FieldSemantics(
            "gross_margin",
            "ratio_fraction",
            "ttm_flow",
            "derived",
            "derived from the TTM frame; never Yahoo info.grossMargins",
        ),
        FieldSemantics(
            "operating_margin",
            "ratio_fraction",
            "ttm_flow",
            "derived",
            "derived from the TTM frame; withheld (never Yahoo info.operatingMargins) "
            "when the frame carries no Operating Income row (v6, 2026-10-14)",
        ),
        FieldSemantics("total_debt", "USD", "point_in_time_stock", "balance_sheet_frame"),
        FieldSemantics("total_cash", "USD", "point_in_time_stock", "balance_sheet_frame"),
        FieldSemantics(
            "preferred_stock",
            "USD",
            "point_in_time_stock",
            "balance_sheet_frame",
            "the statement module's 'Preferred Stock' row",
        ),
        FieldSemantics(
            "noncontrolling_interest",
            "USD",
            "point_in_time_stock",
            "balance_sheet_frame",
            "the statement module's 'Minority Interest' row — the balance-sheet claim",
        ),
        FieldSemantics("book_value_per_share", "USD_per_share", "point_in_time_stock", "derived"),
        FieldSemantics("shares_outstanding", "shares", "point_in_time_stock", "quote"),
        FieldSemantics("market_cap", "USD", "point_in_time_stock", "quote"),
    ),
    (DataType.FINANCIALS.value, "tiingo"): (
        FieldSemantics("revenue", "USD", "ttm_flow", "income_statement"),
        FieldSemantics("operating_income", "USD", "ttm_flow", "income_statement"),
        FieldSemantics("net_income", "USD", "ttm_flow", "income_statement"),
        FieldSemantics("total_debt", "USD", "point_in_time_stock", "balance_sheet"),
        FieldSemantics("total_cash", "USD", "point_in_time_stock", "balance_sheet"),
        FieldSemantics(
            "noncontrolling_interest",
            "USD",
            "point_in_time_stock",
            "balance_sheet",
            "balance-sheet claim only — the income-statement nonControllingInterests "
            "flow is NOT mapped here (v5, 2026-10-12)",
        ),
        FieldSemantics("shares_outstanding", "shares", "point_in_time_stock", "quote"),
        FieldSemantics("market_cap", "USD", "point_in_time_stock", "quote"),
    ),
    (DataType.PRICE.value, "eodhd"): (
        FieldSemantics(
            "price",
            "USD_per_share",
            "split_dividend_adjusted",
            "quote",
            "OHLC scaled by adjusted_close / close",
        ),
        FieldSemantics("quote_currency", "currency_code", "as_reported", "quote"),
        FieldSemantics("price_52w_high", "USD_per_share", "split_dividend_adjusted", "bars"),
        FieldSemantics("price_52w_low", "USD_per_share", "split_dividend_adjusted", "bars"),
        FieldSemantics("trailing_1y_return_pct", "percent", "dividend_inclusive", "bars"),
    ),
}

#: Runtime provider name → repo-relative source file. Only providers that appear
#: in :data:`PRODUCERS` need an entry; a missing entry means that provider's
#: source contributes no bytes to the digest (still covered by the sources pin).
PROVIDER_MODULE: Mapping[str, str] = {
    "fmp": "finrobot/engine/data/providers/fmp_provider.py",
    "yfinance": "finrobot/engine/data/providers/yfinance_provider.py",
    "tiingo": "finrobot/engine/data/providers/tiingo_provider.py",
    "eodhd": "finrobot/engine/data/providers/eodhd_provider.py",
    "finnhub": "finrobot/engine/data/providers/finnhub_provider.py",
    "stockdata": "finrobot/engine/data/providers/stockdata_provider.py",
    "twelvedata": "finrobot/engine/data/providers/twelvedata_provider.py",
    "massive": "finrobot/engine/data/providers/massive_provider.py",
    "moomoo": "finrobot/engine/data/providers/moomoo_provider.py",
    "adanos": "finrobot/engine/data/providers/adanos_provider.py",
    "sec_edgar": "finrobot/engine/data/providers/edgar_provider.py",
}

#: Providers whose source can produce each BASE data type. Used to fold EVERY
#: producer's source into the aggregate digest of a type, so a change in any one
#: of them moves the type's raw slot.
PRODUCERS: Mapping[str, tuple[str, ...]] = {
    DataType.FINANCIALS.value: ("fmp", "yfinance", "tiingo"),
    DataType.PRICE.value: (
        "fmp",
        "yfinance",
        "tiingo",
        "twelvedata",
        "stockdata",
        "finnhub",
        "eodhd",
    ),
    DataType.FORWARD_ESTIMATES.value: ("fmp",),
    DataType.PEER_CANDIDATES.value: ("fmp",),
    DataType.SENTIMENT.value: ("adanos", "eodhd"),
    DataType.PROXY_STATEMENT.value: ("sec_edgar",),
    DataType.FUND_PROFILE.value: ("eodhd", "yfinance", "moomoo"),
    DataType.FUND_HOLDINGS.value: ("sec_edgar",),
}


def semantics_rev(data_type: str | DataType) -> int:
    """The human revision of a type's RAW payload format; ``0`` when unversioned.

    These are the values (and the incident-log comment above :data:`RAW_SLOT_VERSION`)
    that used to live in ``cache._RAW_SLOT_VERSION`` — moved here, verbatim, so the
    declaration and the digest that guards it are one module.
    """
    return RAW_SLOT_VERSION.get(str(data_type), 0)


def declared_fields(
    data_type: str | DataType, provider: str | None = None
) -> tuple[FieldSemantics, ...]:
    """The field semantics for ``(data_type, provider)``.

    ``provider`` selects that provider's own declaration from
    :data:`PROVIDER_FIELD_SEMANTICS` when one exists, else the type default from
    :data:`FIELD_SEMANTICS`. ``None`` always reads the type default.
    """
    base = str(data_type)
    if provider is not None:
        override = PROVIDER_FIELD_SEMANTICS.get((base, provider))
        if override is not None:
            return override
    return FIELD_SEMANTICS.get(base, ())


def producer_modules(data_type: str | DataType, provider: str | None = None) -> tuple[str, ...]:
    """Repo-relative source files whose bytes the digest covers for ``(data_type, provider)``.

    ``None`` → every producer of the type (:data:`PRODUCERS`); a named provider →
    only that provider's module. An undeclared provider contributes nothing.
    """
    base = str(data_type)
    names = (provider,) if provider is not None else PRODUCERS.get(base, ())
    modules = (PROVIDER_MODULE.get(name) for name in names)
    return tuple(m for m in modules if m is not None)


def declared_pairs() -> tuple[tuple[str, str], ...]:
    """Every ``(data_type, provider)`` pair whose semantics are declared and pinned.

    The audit acknowledges one digest per pair, so a change that moves a pair's
    meaning is a decision the author must record.
    """
    pairs: list[tuple[str, str]] = []
    for base, providers in PRODUCERS.items():
        for provider in providers:
            pairs.append((base, provider))
    return tuple(pairs)


_SOURCE_DIGESTS: dict[str, str] = {}


def _source_digest(relative_path: str) -> str:
    """SHA-256 of a provider source file, line endings normalized, memoized by path.

    ``\\r\\n`` is normalized to ``\\n`` so the digest is identical on a Windows
    checkout and in CI. Memoized per path: provider source does not change inside a
    running process, so the cache hot path stays a dict lookup. Tests that mutate a
    provider file call :func:`_reset_source_cache`.
    """
    digest = _SOURCE_DIGESTS.get(relative_path)
    if digest is None:
        raw = (_REPO_ROOT / relative_path).read_bytes()
        digest = hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()
        _SOURCE_DIGESTS[relative_path] = digest
    return digest


def _reset_source_cache() -> None:
    """Drop the memoized provider-source digests (tests only)."""
    _SOURCE_DIGESTS.clear()


def semantics_digest(data_type: str | DataType, provider: str | None = None) -> str:
    """A stable short digest of what a cached payload for ``(data_type, provider)`` MEANS.

    Over the declared field semantics (unit/caliber/basis/note) for the type (or the
    provider's own declaration) PLUS the SHA-256 of each producing provider module's
    source file — so ANY edit to a provider's source, even a comment, moves the
    digest. ``cache.raw_slot_key`` bakes it into a versioned type's slot and
    ``cache.canonical_key`` into every canonical slot, so a meaning change
    self-invalidates instead of being served until TTL expiry.
    """
    fields = declared_fields(data_type, provider)
    modules = producer_modules(data_type, provider)
    payload = {
        "data_type": str(data_type),
        "provider": provider,
        "fields": [[f.field, f.unit, f.caliber, f.basis, f.note] for f in fields],
        "sources": [[path, _source_digest(path)] for path in modules],
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:_DIGEST_CHARS]
