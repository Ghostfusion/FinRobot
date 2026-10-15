"""extractor: ONE net-income authority for the printed P/E, and the disclosure of
a provider-vs-XBRL net-income gap (owner review of the EHC deep-dive).

The EHC report showed three net-income numbers — $621M (SEC XBRL TTM filing fact,
narrated), $603.7M (the income-statement table) and ~$590M implied by the printed
20.8× P/E — because the P/E rode the provider's own diluted-EPS basis instead of
the net income the report prints.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from finrobot.engine.compute.coordinators.extractor import (
    PE_BASIS_NET_INCOME,
    extract_financial_data,
    net_income_divergence_warning,
    xbrl_fiscal_divergence_warning,
)
from finrobot.engine.data.interface import DataResult
from finrobot.engine.data.normalize.financials import normalize_financials
from finrobot.engine.data.normalize.price import normalize_price


def _make_fin(**overrides):
    data = dict(
        revenue=100e9,
        ebitda=35e9,
        net_income=20e9,
        gross_margin=0.47,
        operating_margin=0.28,
        pe_ratio=28.5,
        market_cap=3e12,
        shares_outstanding=15e9,
        current_price=200.0,
        total_debt=50e9,
        total_cash=20e9,
    )
    data.update(overrides)
    return normalize_financials(
        DataResult(
            data=data,
            provider="yfinance",
            ticker="AAPL",
            data_type="financials",
            timestamp=datetime.now(tz=timezone.utc),
        )
    )


def _make_price():
    return _make_price_at(200.0)


def _make_price_at(price: float):
    return normalize_price(
        DataResult(
            data={
                "current_price": price,
                "price_history": [
                    {"date": "2024-01-01", "close": 180.0},
                    {"date": "2024-06-01", "close": 220.0},
                    {"date": "2024-12-01", "close": price},
                ],
            },
            provider="yfinance",
            ticker="AAPL",
            data_type="price",
            timestamp=datetime.now(tz=timezone.utc),
        )
    )


def _ehc_fin(**overrides):
    """EHC's snapshot shape: market_cap = shares × price, provider P/E on its own
    (diluted-EPS) basis, net income = the printed income-statement figure."""
    return _make_fin(
        net_income=603_699_968,
        market_cap=98_653_384 * 124.42,
        shares_outstanding=98_653_384,
        current_price=124.42,
        pe_ratio=20.806,
        **overrides,
    )


class TestPeNetIncomeAuthority:
    def test_pe_is_market_cap_over_ttm_net_income(self) -> None:
        """The ratio is derived from the figures the report PRINTS, not the
        provider's own trailingPE (a different denominator)."""
        fd = extract_financial_data(_ehc_fin(), _make_price_at(124.42))
        live_cap = fd.market.shares_outstanding * 124.42
        assert fd.market.pe_ratio == pytest.approx(live_cap / 603_699_968, rel=1e-9)
        assert fd.market.pe_ratio == pytest.approx(20.33, abs=0.01)

    def test_basis_is_stamped_on_the_market_block(self) -> None:
        fd = extract_financial_data(_make_fin(), _make_price())
        assert fd.market.pe_basis is not None
        assert fd.market.pe_basis.startswith(PE_BASIS_NET_INCOME)

    def test_basis_is_a_label_not_a_row_warning(self) -> None:
        """Coverage flips its "partial" flag on ANY FinancialData.warnings entry
        (coverage.service: ``partial = any(row.warnings)``), so a property of every
        P/E must never be routed through the row-level warning list."""
        fd = extract_financial_data(_ehc_fin(), _make_price_at(124.42))
        assert not any("one net-income authority" in w for w in fd.warnings)

    def test_disagreeing_provider_ratio_is_named_and_superseded(self) -> None:
        """EHC shape: the provider's 20.8× implies a net income the report never
        prints, so the basis change is disclosed rather than silent."""
        fd = extract_financial_data(_ehc_fin(), _make_price_at(124.42))
        assert fd.market.pe_basis is not None
        assert "supersedes" in fd.market.pe_basis
        assert "20.81" in fd.market.pe_basis

    def test_agreeing_provider_ratio_adds_no_supersede_note(self) -> None:
        # market_cap 3e12 / net_income 20e9 = 150.0 — the provider says 150.0 too.
        fd = extract_financial_data(_make_fin(pe_ratio=150.0), _make_price())
        assert fd.market.pe_ratio == pytest.approx(150.0)
        assert fd.market.pe_basis == PE_BASIS_NET_INCOME

    def test_provider_ratio_is_the_fallback_when_net_income_is_missing(self) -> None:
        fin = _make_fin(net_income=None)
        fd = extract_financial_data(fin, _make_price())
        # market_cap/price == provider market_cap → mc_ratio 1.0
        assert fd.market.pe_ratio == pytest.approx(28.5)
        assert fd.market.pe_basis is None

    def test_provider_ratio_is_the_fallback_when_net_income_is_non_positive(self) -> None:
        """A loss-maker has no meaningful P/E from market_cap ÷ net income; the
        provider value (already None for most loss-makers) survives instead."""
        fin = _make_fin(net_income=-5e9)
        fd = extract_financial_data(fin, _make_price())
        assert fd.market.pe_ratio == pytest.approx(28.5)
        assert fd.market.pe_basis is None

    def test_pe_is_none_when_neither_authority_can_produce_one(self) -> None:
        fin = _make_fin(net_income=None, pe_ratio=None)
        fd = extract_financial_data(fin, _make_price())
        assert fd.market.pe_ratio is None
        assert fd.market.pe_basis is None


class TestNetIncomeDivergenceWarning:
    def test_agreement_within_tolerance_is_silent(self) -> None:
        # EHC's real pair: 603.7M provider vs 621.0M XBRL = 2.9% — below 5%.
        assert (
            net_income_divergence_warning(
                603_699_968, "yfinance", 621_000_000, "SEC XBRL us-gaap:NetIncomeLoss:ttm"
            )
            is None
        )

    def test_divergence_names_both_values_and_both_sources(self) -> None:
        warning = net_income_divergence_warning(
            500_000_000, "yfinance", 620_000_000, "SEC XBRL us-gaap:NetIncomeLoss:ttm"
        )
        assert warning is not None
        assert "500,000,000" in warning
        assert "620,000,000" in warning
        assert "yfinance" in warning
        assert "SEC XBRL us-gaap:NetIncomeLoss:ttm" in warning
        # |500M − 620M| / 620M (the larger magnitude) = 19.4%
        assert "19.4%" in warning

    def test_missing_xbrl_value_is_silent(self) -> None:
        assert net_income_divergence_warning(603_699_968, "yfinance", None, "SEC XBRL") is None

    def test_missing_provider_value_is_silent(self) -> None:
        assert net_income_divergence_warning(None, "yfinance", 621_000_000, "SEC XBRL") is None

    def test_missing_sources_fall_back_to_neutral_labels(self) -> None:
        warning = net_income_divergence_warning(100.0, None, 200.0, None)
        assert warning is not None
        assert "(provider)" in warning
        assert "(SEC XBRL)" in warning

    def test_zero_and_non_finite_inputs_are_silent(self) -> None:
        assert net_income_divergence_warning(0.0, "yfinance", 0.0, "SEC XBRL") is None
        assert net_income_divergence_warning(float("nan"), "yfinance", 1.0, "SEC XBRL") is None
        assert net_income_divergence_warning(1.0, "yfinance", float("inf"), "SEC XBRL") is None

    def test_negative_vs_positive_is_measured_on_the_larger_magnitude(self) -> None:
        warning = net_income_divergence_warning(-300.0, "yfinance", 100.0, "SEC XBRL")
        assert warning is not None
        assert "133.3%" in warning

    def test_gap_explained_by_nci_earnings_is_named_not_called_a_caliber_gap(self) -> None:
        """F2 (THC): provider net income is attributable to the parent (2.241B),
        the SEC XBRL TTM ``NetIncomeLoss`` is consolidated incl. NCI (3.174B); the
        933M gap IS the noncontrolling-interest earnings. The warning must NAME
        that — dollar amount + basis — instead of the misleading 'caliber gap
        (concept / window / filing rounding), not a typo'."""
        warning = net_income_divergence_warning(
            2_241_000_000,
            "yfinance",
            3_174_000_000,
            "SEC XBRL us-gaap:NetIncomeLoss:ttm",
            nci_earnings=933_000_000,
        )
        assert warning is not None
        assert "noncontrolling-interest" in warning
        assert "933,000,000" in warning
        assert "consolidated" in warning
        assert "attributable to the parent" in warning
        # The old guessy wording must be gone when the cause is known.
        assert "caliber gap" not in warning

    def test_unexplained_gap_keeps_conservative_wording(self) -> None:
        """When the reported NCI share does NOT match the gap, keep the
        conservative caliber-gap wording — never fabricate an NCI cause."""
        warning = net_income_divergence_warning(
            500_000_000, "yfinance", 620_000_000, "SEC XBRL", nci_earnings=1_000_000
        )
        assert warning is not None
        assert "caliber gap" in warning
        assert "noncontrolling-interest" not in warning


class TestQuoteBasis:
    """The report printed "Live $124.42" for a previous session's close (owner
    review 2026-10-13); the price feed knows better — it flags a bar-inferred
    observation time with ``quote_ts_missing``."""

    def test_bar_only_history_is_a_close_not_a_live_quote(self) -> None:
        fd = extract_financial_data(_ehc_fin(), _make_price_at(124.42))
        assert fd.market.quote_is_live is False
        # The feed's own as-of: the session the newest bar belongs to.
        assert fd.market.quote_as_of is not None
        assert fd.market.quote_as_of.date().isoformat() == "2024-12-01"

    def test_a_stamped_quote_is_live(self) -> None:
        price = normalize_price(
            DataResult(
                data={
                    "current_price": 124.42,
                    "quote_timestamp": "2024-12-01T20:00:00+00:00",
                    "price_history": [
                        {"date": "2024-12-01", "close": 124.42},
                    ],
                },
                provider="yfinance",
                ticker="AAPL",
                data_type="price",
                timestamp=datetime.now(tz=timezone.utc),
            )
        )
        fd = extract_financial_data(_ehc_fin(), price)
        assert fd.market.quote_is_live is True


class TestXbrlFiscalDivergenceWarning:
    """One fiscal year, two authorities — the annual sibling of the TTM net-income pair.

    Owner review 2026-10-15 (TROW): the report printed THREE FY2025 operating incomes
    (XBRL fact 2,188,800,000 → 29.9%; provider annual 2,477,400,000 → 33.9%; provider
    TTM 2,615,100,000 → 34.4%) and reconciled none of them, while the DCF's 42%
    EBITDA-margin assumption rode the provider caliber.
    """

    _TROW_YEARS = [2022, 2023, 2024, 2025]
    _TROW_OP_INCOME = [2_496_000_000.0, 2_038_000_000.0, 2_476_600_000.0, 2_477_400_000.0]

    def _warning(self, **overrides):
        kwargs = dict(
            label="Operating income",
            concept="us-gaap:OperatingIncomeLoss",
            provider_series=self._TROW_OP_INCOME,
            provider_years=self._TROW_YEARS,
            provider_source="yfinance",
            xbrl_fact={
                "concept": "us-gaap:OperatingIncomeLoss",
                "value": 2_188_800_000.0,
                "period_end": "2025-12-31",
                "units": "USD",
            },
        )
        kwargs.update(overrides)
        return xbrl_fiscal_divergence_warning(**kwargs)

    def test_divergence_names_the_year_both_values_and_both_sources(self) -> None:
        warning = self._warning()
        assert warning is not None
        assert "FY2025" in warning
        assert "2,477,400,000" in warning
        assert "2,188,800,000" in warning
        assert "yfinance" in warning
        assert "us-gaap:OperatingIncomeLoss" in warning
        # |2,477.4M − 2,188.8M| / 2,477.4M (the larger magnitude) = 11.6%
        assert "11.6%" in warning

    def test_the_same_year_agreeing_is_silent(self) -> None:
        # TROW's revenue: the provider's FY2025 bar and the XBRL fact are the same figure.
        assert (
            self._warning(
                label="Revenue",
                concept="us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
                provider_series=[
                    6_488_400_000.0,
                    6_460_500_000.0,
                    7_093_600_000.0,
                    7_314_800_000.0,
                ],
                xbrl_fact={
                    "value": 7_314_800_000.0,
                    "period_end": "2025-12-31",
                    "units": "USD",
                },
            )
            is None
        )

    def test_a_fact_from_a_year_the_series_does_not_carry_is_silent(self) -> None:
        """TROW's ``us-gaap:GrossProfit`` fact is filed for 2011 — the provider series
        starts at 2022, so there is no same-year figure to compare against and the
        disclosure must stay silent rather than invent one."""
        assert (
            self._warning(
                label="Gross profit",
                concept="us-gaap:GrossProfit",
                provider_series=[
                    3_566_000_000.0,
                    3_206_100_000.0,
                    3_684_100_000.0,
                    3_750_300_000.0,
                ],
                xbrl_fact={"value": 2_747_100_000.0, "period_end": "2011-12-31", "units": "USD"},
            )
            is None
        )

    def test_missing_or_malformed_inputs_are_silent(self) -> None:
        assert self._warning(xbrl_fact=None) is None
        assert self._warning(xbrl_fact={}) is None
        assert self._warning(xbrl_fact={"value": None, "period_end": "2025-12-31"}) is None
        assert self._warning(xbrl_fact={"value": "n/a", "period_end": "2025-12-31"}) is None
        assert self._warning(provider_years=None) is None
        assert self._warning(provider_years=[]) is None
        assert self._warning(provider_series=None) is None
        # The fact's year is in the series but the provider omitted that year's figure.
        assert self._warning(provider_series=[1.0, 2.0, 3.0, None]) is None

    def test_zero_and_non_finite_values_are_silent(self) -> None:
        # BOTH sides zero is the one pairing with no ratio to compare (0/0).
        assert (
            self._warning(
                provider_series=[1.0, 2.0, 3.0, 0.0],
                xbrl_fact={"value": 0.0, "period_end": "2025-12-31"},
            )
            is None
        )
        assert self._warning(provider_series=[1.0, 2.0, 3.0, float("inf")]) is None
        assert self._warning(xbrl_fact={"value": float("nan"), "period_end": "2025-12-31"}) is None

    def test_a_period_end_given_as_a_bare_year_aligns(self) -> None:
        # Some concepts carry a 'YYYY' period_end rather than a full date.
        warning = self._warning(xbrl_fact={"value": 2_188_800_000.0, "period_end": "2025"})
        assert warning is not None and "FY2025" in warning
