"""Focused tests for the PRICE provenance/currency-inference slice (contract §A).

Three currency cases and the prompt-visibility fixes:
  (a) an EODHD ``.US`` payload (whose /eod rows carry no currency) yields a
      canonical with ``quote_currency == "USD"`` and ``quote_currency_inferred``
      in ``degraded`` — NOT ``quote_currency_missing``;
  (b) a payload that declares its own currency is unchanged;
  (c) an unknown-exchange payload still abstains (``UNKNOWN`` +
      ``quote_currency_missing``);
  (d) ``to_prompt_summary`` now carries the PRICE provenance block + the
      reconciliation summary, and the step-prompt render labels provenance
      ownership and XBRL fact periods.

The ".US" rows mirror the real /eod shape (``date/open/high/low/close/
adjusted_close/volume``); the adjusted column is what the bar mapper reads.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from finrobot.engine.data.interface import DataResult
from finrobot.engine.data.normalize.contracts import (
    DEGRADED_QUOTE_CURRENCY_INFERRED,
    DEGRADED_QUOTE_CURRENCY_MISSING,
    DEGRADED_QUOTE_TS_MISSING,
    NormalizedPrice,
    Provenance,
)
from finrobot.engine.data.normalize.price import normalize_price
from finrobot.engine.data.providers.eodhd_provider import EODHDProvider
from finrobot.engine.data.types import DataType
from finrobot.engine.models.metric_authority import MetricDecision, ReconciliationReport
from finrobot.engine.pipelines.runner import _canonical_context_string, _label_xbrl_fact_periods

FETCH = datetime(2026, 10, 13, 19, 5, tzinfo=timezone.utc)

_BAR = {
    "date": "2026-10-10",
    "open": 227.0,
    "high": 229.0,
    "low": 226.0,
    "close": 228.52,
    "adjusted_close": 228.52,
    "volume": 41_000_000,
}


def _price_result(**data: Any) -> DataResult:
    base = {"current_price": 228.52, "price_history": [dict(_BAR)], "quote_currency": "USD"}
    base.update(data)
    return DataResult(
        data=base, provider="eodhd", ticker="NVDA.US", data_type="price", timestamp=FETCH
    )


async def _eodhd_price(ticker: str) -> DataResult:
    provider = EODHDProvider("test-token")
    response = httpx.Response(
        200,
        request=httpx.Request("GET", f"https://eodhd.com/api/eod/{ticker}"),
        json=[dict(_BAR)],
    )
    with patch.object(provider, "_get", AsyncMock(return_value=response)):
        return await provider.fetch(ticker, DataType.PRICE)


# ---------------------------------------------------------------------------
# (a/b/c) quote-currency provenance
# ---------------------------------------------------------------------------


async def test_us_suffixed_eodhd_price_infers_usd() -> None:
    """A ``NVDA.US`` /eod payload carries no currency → exchange-suffix inference."""
    result = await _eodhd_price("NVDA.US")
    assert result.data["exchange"] == "US"
    assert result.data["quote_currency"] == "USD"
    assert result.data["quote_currency_inferred"] is True

    price = normalize_price(result)
    assert price.quote_currency == "USD"
    assert DEGRADED_QUOTE_CURRENCY_INFERRED in price.provenance.degraded
    assert DEGRADED_QUOTE_CURRENCY_MISSING not in price.provenance.degraded


async def test_unknown_exchange_suffix_eodhd_price_abstains() -> None:
    """An unmapped suffix resolves to (None, None) — the canonical must abstain."""
    result = await _eodhd_price("NVDA.XX")
    assert result.data["exchange"] is None
    assert result.data["quote_currency"] is None
    assert result.data["quote_currency_inferred"] is False

    price = normalize_price(result)
    assert price.quote_currency == "UNKNOWN"
    assert DEGRADED_QUOTE_CURRENCY_MISSING in price.provenance.degraded
    assert DEGRADED_QUOTE_CURRENCY_INFERRED not in price.provenance.degraded


def test_declared_currency_is_unchanged() -> None:
    """A payload that carries its own currency keeps it — no inferred/lost marker."""
    price = normalize_price(_price_result(quote_currency="twd"))
    assert price.quote_currency == "TWD"
    assert DEGRADED_QUOTE_CURRENCY_INFERRED not in price.provenance.degraded
    assert DEGRADED_QUOTE_CURRENCY_MISSING not in price.provenance.degraded


def test_unknown_currency_still_abstains() -> None:
    """Nothing knows the currency → UNKNOWN + quote_currency_missing, as today."""
    price = normalize_price(_price_result(quote_currency=None))
    assert price.quote_currency == "UNKNOWN"
    assert DEGRADED_QUOTE_CURRENCY_MISSING in price.provenance.degraded
    assert DEGRADED_QUOTE_CURRENCY_INFERRED not in price.provenance.degraded


# ---------------------------------------------------------------------------
# (d) prompt visibility
# ---------------------------------------------------------------------------


def _decision() -> MetricDecision:
    return MetricDecision(
        metric="current_price",
        status="accepted",
        value=228.52,
        unit="USD/share",
        currency="USD",
        selected_source="eodhd",
        is_authoritative=True,
        reason_code="owner_selected",
        policy_version="metric_authority_v1",
        definition_version="v1",
        basis="session",
        comparability="session_price",
        tolerance_pct=0.01,
        tolerance_abs=None,
        period_end=date(2026, 10, 10),
        period_basis="session",
        disagreement_pct=None,
        agreement_is_independent=True,
        candidates=(),
        reconciled_at=FETCH,
    )


def _price_with_record() -> NormalizedPrice:
    return NormalizedPrice(
        ticker="NVDA",
        quote_currency="USD",
        current_price=228.52,
        provenance=Provenance(
            provider="eodhd",
            as_of=datetime(2026, 10, 10, 20, 0, tzinfo=timezone.utc),
            fetched_at=FETCH,
            from_cache=True,
            degraded=[DEGRADED_QUOTE_TS_MISSING, DEGRADED_QUOTE_CURRENCY_INFERRED],
        ),
        reconciliation=ReconciliationReport(
            policy_version="metric_authority_v1",
            run_as_of=FETCH,
            clock=FETCH,
            decisions=(_decision(),),
        ),
    )


def test_to_prompt_summary_carries_provenance_and_reconciliation() -> None:
    summary = _price_with_record().to_prompt_summary()
    prov = summary["provenance"]
    assert prov["provider"] == "eodhd"
    assert prov["as_of"] == "2026-10-10T20:00:00+00:00"
    assert prov["fetched_at"] == FETCH.isoformat()
    assert prov["from_cache"] is True
    assert prov["degraded"] == [DEGRADED_QUOTE_TS_MISSING, DEGRADED_QUOTE_CURRENCY_INFERRED]

    rec = summary["reconciliation"]
    assert rec["policy_version"] == "metric_authority_v1"
    assert rec["run_as_of"] == FETCH.isoformat()
    assert rec["decisions"] == [
        {
            "metric": "current_price",
            "status": "accepted",
            "selected_source": "eodhd",
            "is_authoritative": True,
            "reason_code": "owner_selected",
        }
    ]


def test_to_prompt_summary_reconciliation_none_without_record() -> None:
    price = NormalizedPrice(
        ticker="X",
        current_price=1.0,
        provenance=Provenance(provider="eodhd", as_of=FETCH, fetched_at=FETCH),
    )
    summary = price.to_prompt_summary()
    assert summary["reconciliation"] is None
    assert summary["provenance"]["degraded"] == []


def test_canonical_context_string_labels_provenance_owner() -> None:
    rendered = _canonical_context_string(DataType.PRICE, _price_with_record())
    assert "[canonical] price (normalized contract)" in rendered
    assert "THIS PRICE object only" in rendered
    # The PRICE render now exposes its own markers, not just the header label.
    assert DEGRADED_QUOTE_CURRENCY_INFERRED in rendered


def test_xbrl_fact_periods_are_labelled() -> None:
    snapshot = {
        "us-gaap:Revenues": [
            {
                "concept": "us-gaap:Revenues",
                "value": 302_969_000_000.0,
                "periods": ["Q3 2026", "Q4 2026"],
                "period_end": "2026-07-26",
            },
            {"concept": "us-gaap:Revenues", "value": 215_938_000_000.0, "period_end": "2026-01-25"},
        ]
    }
    labelled = _label_xbrl_fact_periods(snapshot)
    ttm_fact, annual_fact = labelled["us-gaap:Revenues"]
    assert ttm_fact["period_basis"] == "ttm"
    assert ttm_fact["period_label"] == "TTM (window ending 2026-07-26)"
    assert annual_fact["period_basis"] == "annual"
    assert annual_fact["period_label"] == "FY (period_end 2026-01-25)"
    # Additive only — values and facts preserved.
    assert annual_fact["value"] == 215_938_000_000.0
    assert len(labelled["us-gaap:Revenues"]) == 2


def test_label_xbrl_fact_periods_passthrough_on_non_dict() -> None:
    assert _label_xbrl_fact_periods(None) is None
    assert _label_xbrl_fact_periods("x") == "x"


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
