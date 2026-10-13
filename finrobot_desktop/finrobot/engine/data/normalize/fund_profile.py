"""normalize_fund_profile: raw FUND_PROFILE ``DataResult`` → canonical profile.

Transport-level normalization, mirroring ``normalize_forward_estimates``: the
provider arm owns the vendor-key mapping AND the unit conversion (the contract's
convention is that every ratio / return / yield is a FRACTION — see
``NormalizedFundProfile``), while this gate coerces types, drops malformed
entries instead of fabricating them, stamps provenance and carries the fetch's
warnings.

Two invariants are enforced here rather than trusted from the provider:

* a non-finite number (``NaN``/``inf`` from a vendor DataFrame) becomes ``None``
  — never a ``NaN`` that would poison every downstream average;
* the asset-class weights are checked for reconciliation and a partial breakdown
  is *reported* (``warnings``), never renormalized — renormalizing would invent
  the missing slice of the portfolio.
"""

from __future__ import annotations

import math
from datetime import date, datetime
from typing import Any

from finrobot.engine.data.interface import DataResult
from finrobot.engine.data.normalize.contracts import (
    FundHolding,
    NormalizedFundProfile,
    Provenance,
)

#: Below this distance from 1.0 the reported asset mix is treated as complete.
#: The weights are shares of one portfolio, so anything further off is a partial
#: breakdown (measured: Yahoo's IEI mix sums to 1.0000 across six classes).
_ALLOCATION_TOLERANCE = 0.01


def _num(value: Any) -> float | None:
    """Coerce a vendor scalar to a finite float, else ``None``.

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


def _weights(raw: Any) -> dict[str, float]:
    """A ``{label: weight}`` mapping of finite, non-negative fractions.

    Non-dict input, non-numeric values and negative weights are dropped: a
    negative portfolio *weight* is a data error (shorts are reported in their
    own class by the vendors we read), and silently keeping it would corrupt
    every concentration measure derived from these weights.
    """
    if not isinstance(raw, dict):
        return {}
    out: dict[str, float] = {}
    for key, value in raw.items():
        weight = _num(value)
        if weight is None or weight < 0:
            continue
        label = str(key).strip()
        if label:
            out[label] = weight
    return out


def _holdings(raw: Any) -> list[FundHolding]:
    """Position list → ``FundHolding`` objects, skipping entries with no weight.

    A holding with no reported weight carries no portfolio information and is
    dropped rather than emitted as a 0-weight row that would deflate the
    concentration measures.
    """
    if not isinstance(raw, list):
        return []
    out: list[FundHolding] = []
    for row in raw:
        if not isinstance(row, dict):
            continue
        weight = _num(row.get("weight"))
        if weight is None or weight < 0:
            continue
        symbol = row.get("symbol")
        name = row.get("name")
        out.append(
            FundHolding(
                symbol=str(symbol).strip() if symbol else None,
                name=str(name).strip() if name else None,
                weight=weight,
            )
        )
    return out


def _date(value: Any) -> date | None:
    """``date`` / ISO string / epoch-seconds → ``date``, else ``None``.

    Yahoo's ``fundInceptionDate`` is epoch seconds (float); EODHD's
    ``Inception_Date`` is an ISO string. Both spellings are accepted here because
    the field is the same fact.
    """
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, date | datetime):
        return value.date() if isinstance(value, datetime) else value
    if isinstance(value, int | float):
        stamp = float(value)
        if not math.isfinite(stamp) or stamp <= 0:
            return None
        try:
            return datetime.fromtimestamp(stamp, tz=None).date()  # noqa: DTZ006 - vendor epoch
        except (OverflowError, OSError, ValueError):
            return None
    if isinstance(value, str):
        try:
            return date.fromisoformat(value.strip()[:10])
        except ValueError:
            return None
    return None


def _text(value: Any) -> str | None:
    """Trimmed string, or ``None`` for blank/absent (never ``""``)."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def normalize_fund_profile(result: DataResult) -> NormalizedFundProfile:
    """Project a raw provider FUND_PROFILE payload onto the canonical contract."""
    data = result.data if isinstance(result.data, dict) else {}
    stripped_cash = _weights(data.get("asset_classes"))
    warnings = list(result.warnings)
    total = math.fsum(stripped_cash.values()) if stripped_cash else None
    if total is not None and abs(total - 1.0) > _ALLOCATION_TOLERANCE:
        warnings.append(
            f"Fund asset-class weights sum to {total:.4f} (expected 1.0 ±{_ALLOCATION_TOLERANCE}); "
            "the provider's breakdown is partial — weights are shown as reported, not renormalized."
        )

    return NormalizedFundProfile(
        ticker=result.ticker,
        name=_text(data.get("name")),
        fund_family=_text(data.get("fund_family")),
        legal_type=_text(data.get("legal_type")),
        category=_text(data.get("category")),
        quote_type=_text(data.get("quote_type")),
        inception_date=_date(data.get("inception_date")),
        currency=_text(data.get("currency")) or "USD",
        as_of=result.timestamp,
        total_net_assets=_num(data.get("total_net_assets")),
        nav_per_share=_num(data.get("nav_per_share")),
        market_price=_num(data.get("market_price")),
        shares_outstanding=_num(data.get("shares_outstanding")),
        net_expense_ratio=_num(data.get("net_expense_ratio")),
        gross_expense_ratio=_num(data.get("gross_expense_ratio")),
        category_avg_expense_ratio=_num(data.get("category_avg_expense_ratio")),
        turnover=_num(data.get("turnover")),
        distribution_yield=_num(data.get("distribution_yield")),
        ytd_return=_num(data.get("ytd_return")),
        return_3m=_num(data.get("return_3m")),
        return_1y=_num(data.get("return_1y")),
        return_3y_annual=_num(data.get("return_3y_annual")),
        return_5y_annual=_num(data.get("return_5y_annual")),
        beta_3y=_num(data.get("beta_3y")),
        asset_classes=stripped_cash,
        sector_weights=_weights(data.get("sector_weights")),
        region_weights=_weights(data.get("region_weights")),
        bond_ratings=_weights(data.get("bond_ratings")),
        bond_duration=_num(data.get("bond_duration")),
        bond_maturity=_num(data.get("bond_maturity")),
        equity_pe=_num(data.get("equity_pe")),
        top_holdings=_holdings(data.get("top_holdings")),
        provenance=Provenance(
            provider=result.provider,
            # The vendors publish the fund snapshot's own update date in some
            # payloads and nothing in others; the fetch instant is the honest
            # semantic time when the payload carries no stamp of its own.
            as_of=result.timestamp,
            fetched_at=result.timestamp,
        ),
        warnings=warnings,
    )
