"""Insider flow, 13F coverage denominator and CEO YoY (owner review 2026-10-13).

The 90-day insider net was summed client-side only, so it was invisible to the
thesis prompt and unmatched by the claim checker; the institutional table was
served from a partial 13F index while the report asserted a concentration; and
``ProxyCompensation.ceo_yoy_change_pct`` was never populated. These tests pin the
sign convention, the aggregation, the coverage denominator + warning, and the YoY
fill (with the blank preferred over a guess).
"""

from __future__ import annotations

from finrobot.engine.compute.operators.ownership import (
    build_proxy_compensation,
    compute_ownership_governance,
)

_EHC_SHARES = 98_653_384.0


def _tx(
    *,
    name: str,
    position: str | None,
    code: str,
    value: float | None,
    filing_date: str = "2026-08-11",
    accession_no: str = "0000785161-26-000001",
    transaction_type: str = "",
) -> dict:
    return {
        "filing_date": filing_date,
        "accession_no": accession_no,
        "insider_name": name,
        "insider_position": position,
        "code": code,
        "transaction_type": transaction_type,
        "shares": 1000.0,
        "value": value,
        "price_per_share": 100.0,
        "security_type": "non-derivative",
    }


def _insider_payload() -> dict:
    return {
        "transactions": [
            # EHC's real 90-day shape: sales only, the CEO's the largest.
            _tx(
                name="Mark J Tarr",
                position="President & CEO",
                code="S",
                value=21_525_046.74,
                accession_no="0000785161-26-000002",
            ),
            _tx(
                name="Douglas E Coltharp",
                position="EVP & Chief Financial Officer",
                code="S",
                value=2_365_795.22,
                accession_no="0000785161-26-000003",
            ),
            _tx(
                name="Andrew L Price",
                position="Chief Accounting Officer",
                code="P",
                value=500_000.0,
                accession_no="0000785161-26-000004",
            ),
            # Grants / exercises are NOT open-market flow.
            _tx(name="Mark J Tarr", position="President & CEO", code="A", value=9_000_000.0),
            _tx(name="Mark J Tarr", position="President & CEO", code="M", value=None),
        ],
        "window_days": 90,
    }


def _holdings_payload(*, rows: list[int], period_end: str = "2026-06-30") -> dict:
    return {
        "holders": [
            {
                "holder_name": f"HOLDER {i}",
                "holder_cik": str(1000 + i),
                "cusip": "29261A100",
                "name_of_issuer": "ENCOMPASS HEALTH CORP",
                "shares": shares,
                "value_usd": float(shares) * 100.0,
                "period_end": period_end,
                "filing_date": "2026-09-02",
                "accession_no": f"0001104659-26-10{i:04d}",
            }
            for i, shares in enumerate(rows)
        ],
        "source": "local_index",
        "warnings": [],
    }


class TestInsiderFlow:
    def test_signed_net_flow_aggregates_open_market_rows_only(self):
        """Purchases positive, sales negative; grants and exercises excluded."""
        analysis = compute_ownership_governance(
            insider_data=_insider_payload(),
            institutional_data=None,
            proxy_data=None,
        )
        assert analysis.insider_buy_value == 500_000.0
        assert analysis.insider_sell_value == 21_525_046.74 + 2_365_795.22
        assert analysis.insider_net_flow == 500_000.0 - (21_525_046.74 + 2_365_795.22)
        assert analysis.insider_net_flow is not None and analysis.insider_net_flow < 0
        assert analysis.insider_window_days == 90

    def test_largest_single_sale_is_attributable(self):
        analysis = compute_ownership_governance(
            insider_data=_insider_payload(),
            institutional_data=None,
            proxy_data=None,
        )
        sale = analysis.insider_largest_sale
        assert sale is not None
        assert sale.name == "Mark J Tarr"
        assert sale.position == "President & CEO"
        assert sale.value == 21_525_046.74

    def test_no_open_market_rows_yields_none_not_a_fabricated_zero(self):
        payload = {
            "transactions": [
                _tx(name="Mark J Tarr", position="President & CEO", code="A", value=9_000_000.0)
            ],
            "window_days": 90,
        }
        analysis = compute_ownership_governance(
            insider_data=payload, institutional_data=None, proxy_data=None
        )
        assert analysis.insider_net_flow is None
        assert analysis.insider_buy_value is None
        assert analysis.insider_sell_value is None
        assert analysis.insider_largest_sale is None

    def test_row_without_a_value_is_skipped_not_treated_as_zero(self):
        payload = {
            "transactions": [
                _tx(name="A B", position="CEO", code="S", value=None),
                _tx(name="C D", position="CFO", code="S", value=1_500_000.0),
            ],
            "window_days": 90,
        }
        analysis = compute_ownership_governance(
            insider_data=payload, institutional_data=None, proxy_data=None
        )
        assert analysis.insider_sell_value == 1_500_000.0
        assert analysis.insider_net_flow == -1_500_000.0


class TestInstitutionalCoverage:
    def test_coverage_uses_shares_outstanding_as_the_denominator(self):
        analysis = compute_ownership_governance(
            insider_data=None,
            institutional_data=_holdings_payload(rows=[3_000_000, 2_000_000]),
            proxy_data=None,
            shares_outstanding=_EHC_SHARES,
        )
        assert analysis.institutional_shares_listed == 5_000_000
        assert analysis.institutional_coverage_pct is not None
        assert analysis.institutional_coverage_pct == 5_000_000 / _EHC_SHARES * 100.0

    def test_low_coverage_warns_that_concentration_cannot_be_asserted(self):
        analysis = compute_ownership_governance(
            insider_data=None,
            institutional_data=_holdings_payload(rows=[3_000_000, 2_000_000]),
            proxy_data=None,
            shares_outstanding=_EHC_SHARES,
        )
        coverage_warnings = [w for w in analysis.warnings if "13F index incomplete" in w]
        assert len(coverage_warnings) == 1
        assert "2026-06-30" in coverage_warnings[0]
        assert "cannot be asserted" in coverage_warnings[0]
        assert "5.1%" in coverage_warnings[0]

    def test_high_coverage_does_not_warn(self):
        analysis = compute_ownership_governance(
            insider_data=None,
            institutional_data=_holdings_payload(rows=[30_000_000, 20_000_000]),
            proxy_data=None,
            shares_outstanding=_EHC_SHARES,
        )
        assert analysis.institutional_coverage_pct is not None
        assert analysis.institutional_coverage_pct > 20.0
        assert not [w for w in analysis.warnings if "13F index incomplete" in w]

    def test_unknown_shares_outstanding_publishes_the_floor_without_a_percentage(self):
        analysis = compute_ownership_governance(
            insider_data=None,
            institutional_data=_holdings_payload(rows=[3_000_000]),
            proxy_data=None,
        )
        assert analysis.institutional_shares_listed == 3_000_000
        assert analysis.institutional_coverage_pct is None
        assert not [w for w in analysis.warnings if "13F index incomplete" in w]


_SCT_TWO_YEARS = (
    "Summary Compensation Table\n"
    "Name and Principal Position Salary Stock Awards Total\n"
    "John Smith 2026 1,000,000 2,000,000 3,000,000 100,000 (4) 6,100,000 "
    "President and CEO 2025 900,000 1,800,000 2,700,000 90,000 5,490,000"
)


def _proxy_payload(text: str) -> dict:
    return {
        "filing_date": "2026-04-07",
        "accession_no": "0000785161-26-000105",
        "text": text,
        "proxy": {"form": "DEF 14A"},
        "warnings": [],
    }


class TestCeoYoyChange:
    def test_yoy_computed_from_the_prior_fiscal_year_row(self):
        proxy = build_proxy_compensation(_proxy_payload(_SCT_TWO_YEARS))
        assert proxy is not None
        assert proxy.ceo_total_compensation == 6_100_000.0
        assert proxy.ceo_yoy_change_pct is not None
        assert proxy.ceo_yoy_change_pct == (6_100_000.0 - 5_490_000.0) / 5_490_000.0 * 100.0

    def test_yoy_left_none_when_no_prior_year_is_visible(self):
        text = (
            "Summary Compensation Table\n"
            "Name and Principal Position Salary Stock Awards Total\n"
            "John Smith 2026 1,000,000 2,000,000 3,000,000 100,000 (4) 6,100,000 "
            "President and CEO"
        )
        proxy = build_proxy_compensation(_proxy_payload(text))
        assert proxy is not None
        assert proxy.ceo_total_compensation == 6_100_000.0
        assert proxy.ceo_yoy_change_pct is None

    def test_yoy_left_none_when_no_compensation_was_extracted(self):
        """EHC's own proxy: no SCT total parsed → no YoY (blank, not invented)."""
        proxy = build_proxy_compensation(_proxy_payload("Our proxy statement."))
        assert proxy is not None
        assert proxy.ceo_total_compensation is None
        assert proxy.ceo_yoy_change_pct is None
