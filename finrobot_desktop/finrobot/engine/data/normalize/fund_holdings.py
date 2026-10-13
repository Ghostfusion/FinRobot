"""normalize_fund_holdings: raw FUND_HOLDINGS ``DataResult`` → canonical portfolio.

Transport-level normalization, mirroring ``normalize_fund_profile``: the provider
arm owns the SEC-key mapping AND the unit conversion (the contract's convention is
that every weight is a FRACTION of net assets — see ``NormalizedFundHoldings``),
while this gate coerces types, drops malformed entries instead of fabricating
them, stamps provenance and carries the fetch's warnings.

Invariants enforced here rather than trusted from the provider:

* a non-finite weight (``NaN``/``inf`` from a vendor DataFrame) becomes an
  unusable row and is dropped — never a ``NaN`` that would poison the summed
  coverage or the Herfindahl index;
* a weight is a share of one portfolio, so it may not be negative: N-PORT reports
  short/derivative legs with a negative ``pctValue``, and keeping those would
  corrupt every concentration measure. They are dropped (documented) rather than
  silently kept;
* ``holding_count`` and ``coverage`` are recomputed from the surviving rows, so a
  provider that over-counts (or would include a dropped row) cannot desync them
  from ``holdings``.
"""

from __future__ import annotations

import math
from datetime import date, datetime
from typing import Any

from finrobot.engine.data.interface import DataResult
from finrobot.engine.data.normalize.contracts import (
    FundFees,
    FundPortfolioHolding,
    NormalizedFundHoldings,
    Provenance,
)


def _num(value: Any) -> float | None:
    """Coerce a scalar to a finite float, else ``None``.

    ``bool`` is rejected deliberately (``True`` is not ``1.0`` in a financial
    contract), and a non-numeric string stays absent rather than becoming ``0``.
    """
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int | float):
        out = float(value)
    elif isinstance(value, str):
        try:
            out = float(value.strip())
        except ValueError:
            return None
    else:
        return None
    return out if math.isfinite(out) else None


def _text(value: Any) -> str | None:
    """Trimmed string, or ``None`` for blank/absent (never ``""``)."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _date(value: Any) -> date | None:
    """``date`` / ISO string / ``datetime`` → ``date``, else ``None``."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value.strip()[:10])
        except ValueError:
            return None
    return None


def _holdings(raw: Any, warnings: list[str]) -> list[FundPortfolioHolding]:
    """Position list → ``FundPortfolioHolding`` objects, dropping unusable rows.

    A row with no finite weight carries no portfolio information, and a NEGATIVE
    weight is a short/derivative leg (N-PORT ``pctValue``) that would corrupt the
    concentration measures — both are dropped. ``FundPortfolioHolding.weight`` is
    REQUIRED, so a row without one cannot be represented and must be skipped.
    """
    if not isinstance(raw, list):
        return []
    out: list[FundPortfolioHolding] = []
    dropped = 0
    for row in raw:
        if not isinstance(row, dict):
            dropped += 1
            continue
        weight = _num(row.get("weight"))
        if weight is None or weight < 0:
            dropped += 1
            continue
        name = _text(row.get("name"))
        out.append(
            FundPortfolioHolding(
                symbol=_text(row.get("symbol")),
                name=name or _text(row.get("symbol")),
                weight=weight,
                value_usd=_num(row.get("value_usd")),
                asset_type=_text(row.get("asset_type")),
            )
        )
    if dropped:
        warnings.append(
            f"Fund portfolio: {dropped} reported position(s) had no usable non-negative "
            "weight fraction and were dropped (shorts/derivatives are excluded from the "
            "concentration panel)."
        )
    return out


def _fees(raw: Any) -> FundFees | None:
    """The optional ``fees`` block → ``FundFees``, or ``None`` when absent."""
    if not isinstance(raw, dict):
        return None
    return FundFees(
        net_expense_ratio=_num(raw.get("net_expense_ratio")),
        as_of=_date(raw.get("as_of")),
        form=_text(raw.get("form")),
    )


def normalize_fund_holdings(result: DataResult) -> NormalizedFundHoldings:
    """Project a raw provider FUND_HOLDINGS payload onto the canonical contract."""
    data = result.data if isinstance(result.data, dict) else {}
    warnings = list(result.warnings)
    holdings = _holdings(data.get("holdings"), warnings)
    as_of = _date(data.get("as_of"))

    # Recompute rather than trust the provider: coverage/holding_count must match
    # the rows that actually survive the gate, or the panel lies about the fund.
    coverage: float | None = None
    if holdings:
        coverage = math.fsum(holding.weight for holding in holdings)

    return NormalizedFundHoldings(
        ticker=result.ticker,
        as_of=as_of,
        filing_date=_date(data.get("filing_date")),
        form=_text(data.get("form")),
        series_name=_text(data.get("series_name")),
        series_id=_text(data.get("series_id")),
        class_id=_text(data.get("class_id")),
        total_net_assets=_num(data.get("total_net_assets")),
        holding_count=len(holdings),
        coverage=coverage,
        holdings=holdings,
        fees=_fees(data.get("fees")),
        provenance=Provenance(
            provider=result.provider,
            # The N-PORT report period end is the semantic age of the portfolio;
            # fall back to the fetch instant when the filing stated none.
            as_of=(
                datetime.combine(as_of, datetime.min.time())
                if as_of is not None
                else result.timestamp
            ),
            fetched_at=result.timestamp,
        ),
        warnings=warnings,
    )
