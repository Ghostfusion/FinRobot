"""extractor: the printed operating margin is divided from the block's OWN leaves.

Live 2026-10-15, KGC: the artifact printed ``operating_margin`` 0.52478004 beside
4,409,000,000 / 8,470,900,224 = 0.52048777 — the provider had divided its own TTM
frame's revenue (8,401,615,275) rather than the ``income.revenue`` leaf the same
artifact prints. Same defect class as the audited CF run (0.49325 beside 0.39088) —
C10e's founding contradiction — so it takes the same fix as the P/E: derive the ratio
from the published leaves and stamp the basis.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from finrobot.engine.compute.coordinators.extractor import (
    OPERATING_MARGIN_BASIS_INCOME_STATEMENT,
    OPERATING_MARGIN_BASIS_PROVIDER,
    extract_company_financials,
    extract_financial_data,
)
from finrobot.engine.data.interface import DataResult
from finrobot.engine.data.normalize.financials import normalize_financials
from finrobot.engine.data.normalize.price import normalize_price

# KGC's live 2026-10-15 snapshot: the revenue and operating income the artifact
# printed, and the margin the provider published alongside them.
_KGC_REVENUE = 8_470_900_224.0
_KGC_OPERATING_INCOME = 4_409_000_000.0
_KGC_PROVIDER_MARGIN = 0.52478004


def _make_fin(**overrides):
    data = dict(
        revenue=_KGC_REVENUE,
        ebitda=6e9,
        net_income=2e9,
        gross_margin=0.69,
        operating_margin=_KGC_PROVIDER_MARGIN,
        operating_income=_KGC_OPERATING_INCOME,
        market_cap=3e10,
        shares_outstanding=1.2e9,
        current_price=25.0,
        total_debt=2e9,
        total_cash=1e9,
    )
    data.update(overrides)
    return normalize_financials(
        DataResult(
            data=data,
            provider="yfinance",
            ticker="KGC",
            data_type="financials",
            timestamp=datetime.now(tz=timezone.utc),
        )
    )


def _price():
    return normalize_price(
        DataResult(
            data={
                "current_price": 25.0,
                "price_history": [
                    {"date": "2026-08-01", "close": 24.0},
                    {"date": "2026-10-01", "close": 25.0},
                ],
            },
            provider="yfinance",
            ticker="KGC",
            data_type="price",
            timestamp=datetime.now(tz=timezone.utc),
        )
    )


class TestOperatingMarginIncomeAuthority:
    def test_margin_is_operating_income_over_the_printed_revenue(self) -> None:
        """The identity ``income.operating_margin == income.operating_income /
        income.revenue`` (C10e, the registry's ``operating_margin``) holds by
        construction, not by the provider's luck."""
        income = extract_financial_data(_make_fin(), _price()).income
        assert income.operating_income is not None
        assert income.revenue
        assert income.operating_margin == pytest.approx(
            income.operating_income / income.revenue, rel=1e-12
        )
        assert income.operating_margin == pytest.approx(
            _KGC_OPERATING_INCOME / _KGC_REVENUE, rel=1e-12
        )
        # The provider's value was 0.8% away — a residual C10e now catches, so it
        # must not be what gets published.
        assert income.operating_margin != pytest.approx(_KGC_PROVIDER_MARGIN, rel=1e-6)

    def test_basis_names_the_authority_and_the_superseded_provider_value(self) -> None:
        fd = extract_financial_data(_make_fin(), _price())
        assert fd.income.operating_margin_basis is not None
        assert fd.income.operating_margin_basis.startswith(OPERATING_MARGIN_BASIS_INCOME_STATEMENT)
        assert "supersedes" in fd.income.operating_margin_basis
        assert "0.5248" in fd.income.operating_margin_basis

    def test_agreeing_provider_margin_adds_no_supersede_note(self) -> None:
        agreed = _KGC_OPERATING_INCOME / _KGC_REVENUE
        fd = extract_financial_data(_make_fin(operating_margin=agreed), _price())
        assert fd.income.operating_margin == pytest.approx(agreed, rel=1e-12)
        assert fd.income.operating_margin_basis == OPERATING_MARGIN_BASIS_INCOME_STATEMENT

    def test_basis_is_a_label_not_a_row_warning(self) -> None:
        """Coverage flips its "partial" flag on ANY ``FinancialData.warnings`` entry
        (coverage.service: ``partial = any(row.warnings)``), so a property of every
        operating margin must never be routed through the row-level warning list."""
        fd = extract_financial_data(_make_fin(), _price())
        assert not any("operating-income authority" in w for w in fd.warnings)

    def test_provider_margin_is_the_labelled_fallback_without_a_numerator(self) -> None:
        """A snapshot with no operating income has nothing to divide: the provider's
        margin still prints, and says that is what it is."""
        fd = extract_financial_data(_make_fin(operating_income=None), _price())
        assert fd.income.operating_margin == pytest.approx(_KGC_PROVIDER_MARGIN)
        assert fd.income.operating_margin_basis == OPERATING_MARGIN_BASIS_PROVIDER

    def test_no_provider_margin_states_no_basis(self) -> None:
        fd = extract_financial_data(
            _make_fin(operating_margin=None, operating_income=None), _price()
        )
        assert fd.income.operating_margin is None
        assert fd.income.operating_margin_basis is None

    def test_a_withheld_derived_margin_is_not_replaced_by_the_provider_value(self) -> None:
        """An operating income exceeding its own revenue is a broken figure:
        ``_sanitize_margin`` withholds it, so nothing is published — and the provider's
        margin must NOT be substituted, since it is the contradiction being removed."""
        fd = extract_financial_data(_make_fin(operating_income=_KGC_REVENUE * 1.5), _price())
        assert fd.income.operating_margin is None
        assert fd.income.operating_margin_basis is None


class TestPeerRowMarginAuthority:
    """The comps chapter renders a peer's margin beside that peer's revenue, so the
    peer path takes the SAME derivation (``derive_operating_margin``) — one rule, two
    callers, rather than a second implementation that can drift."""

    def test_peer_row_margin_divides_its_own_revenue(self) -> None:
        row = extract_company_financials(_make_fin())
        assert row.operating_income is not None
        assert row.revenue
        assert row.operating_margin == pytest.approx(row.operating_income / row.revenue, rel=1e-12)
        # Not the provider's own 0.52478004, which divided a different revenue.
        assert row.operating_margin != pytest.approx(_KGC_PROVIDER_MARGIN, rel=1e-6)

    def test_peer_row_keeps_the_provider_margin_without_a_numerator(self) -> None:
        row = extract_company_financials(_make_fin(operating_income=None))
        assert row.operating_margin == pytest.approx(_KGC_PROVIDER_MARGIN)
