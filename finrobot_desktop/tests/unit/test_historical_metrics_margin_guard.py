"""historical_extractor series guards (owner review of the EHC deep-dive).

Two defects in one series:

1. **Impossible margin.** Yahoo's EHC annual frame crosses that column's
   ``Cost Of Revenue`` (254.4M = the real SG&A magnitude) and ``Selling General
   And Administration`` (3411.1M = the real cost of revenue), so Yahoo's own
   ``Gross Profit`` row reads revenue − 254.4M = 5680.8M → a 95.7% gross margin
   against 40-42% for FY2022-24 and 43.9% TTM (live probe 2026-10-13). The
   plausibility guard must repair it and say so.
2. **Truncated series.** A provider annual fetch can silently return a shorter
   frame than the reported periods, charting an EPS / cash-flow trajectory that
   stops a year early — disclosed against the canonical TTM window end.

The guard input is the provider's per-year normalized dict, so these tests drive
``_build_from_yearly`` directly (the same pure entry the extractor uses).
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

import pytest

from finrobot.engine.compute.coordinators.historical_extractor import _build_from_yearly
from finrobot.engine.data.interface import DataResult
from finrobot.engine.data.types import DataType


def _dr(data: dict[str, Any]) -> DataResult:
    return DataResult(
        data=data,
        provider="yfinance",
        ticker="EHC",
        data_type=DataType.FINANCIALS,
        timestamp=datetime.now(tz=timezone.utc),
        warnings=[],
    )


def _build(yearly: list[dict[str, Any]], **kwargs: Any):
    return _build_from_yearly(
        "EHC",
        [_dr(y) for y in yearly],
        max_years=5,
        trailing_pe=None,
        **kwargs,
    )


# EHC's real annual frame, newest-first (live yfinance probe 2026-10-13). Only the
# newest year's Cost Of Revenue / SG&A are crossed; FY2022-24 are internally
# consistent (COGS ~2.6-3.1B, SG&A ~0.21-0.27B).
_EHC_CROSSED: list[dict[str, Any]] = [
    {
        "fiscal_year": "2025-12-31",
        "revenue": 5_935_200_000,
        "gross_profit": 5_680_800_000,
        "sga_expense": 3_411_100_000,
        "cost_of_revenue": 254_400_000,
        "total_equity": 2_438_200_000,
    },
    {
        "fiscal_year": "2024-12-31",
        "revenue": 5_373_200_000,
        "gross_profit": 2_233_200_000,
        "sga_expense": 266_500_000,
        "cost_of_revenue": 3_140_000_000,
        "total_equity": 2_067_000_000,
    },
    {
        "fiscal_year": "2023-12-31",
        "revenue": 4_801_200_000,
        "gross_profit": 1_982_800_000,
        "sga_expense": 258_000_000,
        "cost_of_revenue": 2_818_400_000,
        "total_equity": 1_647_500_000,
    },
    {
        "fiscal_year": "2022-12-31",
        "revenue": 4_348_600_000,
        "gross_profit": 1_753_200_000,
        "sga_expense": 209_000_000,
        "cost_of_revenue": 2_595_400_000,
        "total_equity": 1_310_300_000,
    },
]

# EHC's provider TTM gross margin (info.grossMargins, probe 2026-10-13) and the TTM
# window end the report's DCF revenue base sits on.
_EHC_TTM_MARGIN = 0.43865
_EHC_TTM_PERIOD_END = date(2026, 6, 30)


class TestCrossedCostLineRepair:
    def test_crossed_fy2025_is_repaired_and_the_impossible_margin_never_ships(self) -> None:
        hm = _build(
            _EHC_CROSSED,
            ttm_gross_margin=_EHC_TTM_MARGIN,
            ttm_period_end=_EHC_TTM_PERIOD_END,
        )
        assert hm.years == [2022, 2023, 2024, 2025]
        # FY2025 is (5935.2 − 3411.1) / 5935.2 = 42.5% — the real gross margin.
        assert hm.gross_margin[-1] == pytest.approx(0.4251, abs=5e-4)
        assert hm.gross_profit[-1] == pytest.approx(2_524_100_000, rel=1e-6)
        assert hm.cogs[-1] == pytest.approx(3_411_100_000, rel=1e-6)
        # The crossed pair is swapped back, so SG&A becomes the real SG&A.
        assert hm.sga[-1] == pytest.approx(254_400_000, rel=1e-6)
        assert hm.sga_ratio[-1] == pytest.approx(254_400_000 / 5_935_200_000, rel=1e-6)
        # Nothing impossible is published, and the earlier years are untouched.
        assert all(m is not None and m < 0.5 for m in hm.gross_margin)
        assert hm.gross_margin[:3] == pytest.approx([0.4032, 0.4130, 0.4156], abs=1e-4)
        assert len(hm.warnings) == 1
        warning = hm.warnings[0]
        assert "FY2025 gross margin" in warning
        assert "crossed or missing" in warning
        assert "repaired via revenue − SG&A (crossed cost lines)" in warning
        assert "42.5%" in warning

    def test_healthy_series_is_untouched(self) -> None:
        healthy = [
            {
                "fiscal_year": "2022-12-31",
                "revenue": 1000.0,
                "gross_profit": 400.0,
                "sga_expense": 100.0,
                "cost_of_revenue": 600.0,
            },
            {
                "fiscal_year": "2023-12-31",
                "revenue": 1100.0,
                "gross_profit": 440.0,
                "sga_expense": 110.0,
                "cost_of_revenue": 660.0,
            },
            {
                "fiscal_year": "2024-12-31",
                "revenue": 1200.0,
                "gross_profit": 480.0,
                "sga_expense": 120.0,
                "cost_of_revenue": 720.0,
            },
        ]
        hm = _build(healthy, ttm_gross_margin=0.40, ttm_period_end=date(2024, 12, 31))
        assert hm.warnings == []
        assert hm.gross_margin == pytest.approx([0.4, 0.4, 0.4])
        assert hm.gross_profit == pytest.approx([400.0, 440.0, 480.0])
        assert hm.cogs == pytest.approx([600.0, 660.0, 720.0])
        assert hm.sga == pytest.approx([100.0, 110.0, 120.0])

    def test_reported_cost_of_revenue_rescues_a_stale_gross_profit_row(self) -> None:
        """Only the ``Gross Profit`` row is stale: the provider's own
        ``cost_of_revenue`` is the consistent leg the guard must prefer over the
        TTM-margin fallback (real data beats a stated margin)."""
        yearly = [
            {
                "fiscal_year": "2022-12-31",
                "revenue": 1000.0,
                "gross_profit": 400.0,
                "sga_expense": 100.0,
                "cost_of_revenue": 600.0,
            },
            {
                "fiscal_year": "2023-12-31",
                "revenue": 1100.0,
                "gross_profit": 440.0,
                "sga_expense": 110.0,
                "cost_of_revenue": 660.0,
            },
            {
                "fiscal_year": "2024-12-31",
                "revenue": 1200.0,
                "gross_profit": 1140.0,  # stale: revenue − 60
                "sga_expense": 130.0,
                "cost_of_revenue": 700.0,  # → 500/1200 = 41.7%, consistent
            },
        ]
        hm = _build(yearly, ttm_gross_margin=0.40)
        assert hm.gross_profit[-1] == pytest.approx(500.0)
        assert hm.cogs[-1] == pytest.approx(700.0)
        assert hm.gross_margin[-1] == pytest.approx(500.0 / 1200.0)
        # SG&A untouched: only the gross-profit leg was stale.
        assert hm.sga[-1] == pytest.approx(130.0)
        assert any("revenue − reported cost of revenue" in w for w in hm.warnings)

    def test_unreconcilable_cost_lines_fall_back_to_the_provider_margin(self) -> None:
        """Neither the other leg nor the reported cost is consistent → publish the
        provider's own margin for the year (stated), never the impossible value."""
        yearly = [
            {"fiscal_year": "2023-12-31", "revenue": 1100.0, "gross_profit": 440.0},
            {"fiscal_year": "2024-12-31", "revenue": 1200.0, "gross_profit": 1200.0},
        ]
        hm = _build(yearly, ttm_gross_margin=0.40)
        assert hm.gross_margin[-1] == pytest.approx(0.40)
        assert hm.gross_profit[-1] == pytest.approx(480.0)
        assert any("provider TTM margin 40.0% × revenue" in w for w in hm.warnings)

    def test_median_of_other_years_is_the_reference_without_a_ttm_margin(self) -> None:
        """No TTM margin available → the other years' median still catches a crossed
        year (a 95.7% margin beside 40% peers is impossible either way)."""
        hm = _build(_EHC_CROSSED, ttm_gross_margin=None)
        assert hm.gross_margin[-1] == pytest.approx(0.4251, abs=5e-4)
        assert len(hm.warnings) == 1
        assert "other years' median" in hm.warnings[0]

    def test_single_year_series_cannot_fire_without_a_ttm_reference(self) -> None:
        """One year is the only reference it has; without a TTM margin the guard
        abstains rather than 'repairing' a legitimate figure."""
        yearly = [{"fiscal_year": "2024-12-31", "revenue": 1200.0, "gross_profit": 1140.0}]
        hm = _build(yearly)
        assert hm.warnings == []
        assert hm.gross_margin == pytest.approx([0.95])

    def test_fallback_label_names_the_median_when_no_ttm_margin(self) -> None:
        """No TTM margin → the reference-margin fallback must not claim a
        'provider TTM margin' it never had."""
        yearly = [
            {"fiscal_year": "2022-12-31", "revenue": 1000.0, "gross_profit": 400.0},
            {"fiscal_year": "2023-12-31", "revenue": 1050.0, "gross_profit": 430.5},
            {"fiscal_year": "2024-12-31", "revenue": 1100.0, "gross_profit": 451.0},
            {"fiscal_year": "2025-12-31", "revenue": 1200.0, "gross_profit": 1140.0},
        ]
        hm = _build(yearly, ttm_gross_margin=None)
        assert any("other years' median 41.0% × revenue" in w for w in hm.warnings)
        assert not any("provider TTM margin" in w for w in hm.warnings)
        assert hm.gross_margin[-1] == pytest.approx(0.41)

    def test_two_year_series_with_a_ttm_margin_repairs_only_the_broken_year(self) -> None:
        yearly = [
            {"fiscal_year": "2023-12-31", "revenue": 1100.0, "gross_profit": 440.0},
            {
                "fiscal_year": "2024-12-31",
                "revenue": 1200.0,
                "gross_profit": 1140.0,
                "sga_expense": 60.0,
            },
        ]
        hm = _build(yearly, ttm_gross_margin=0.40)
        assert hm.gross_margin[0] == pytest.approx(0.40)  # healthy year untouched
        assert hm.gross_margin[-1] == pytest.approx(0.40)  # broken year repaired
        assert len(hm.warnings) == 1

    def test_two_year_series_without_a_ttm_margin_abstains(self) -> None:
        """With a single peer the "median of the others" IS that peer: using it
        would drag the HEALTHY year toward the broken one, so the guard abstains
        rather than corrupt the series."""
        yearly = [
            {"fiscal_year": "2023-12-31", "revenue": 1100.0, "gross_profit": 440.0},
            {"fiscal_year": "2024-12-31", "revenue": 1200.0, "gross_profit": 1140.0},
        ]
        hm = _build(yearly, ttm_gross_margin=None)
        assert hm.warnings == []
        assert hm.gross_margin[0] == pytest.approx(0.40)
        assert hm.gross_margin[-1] == pytest.approx(0.95)

    def test_missing_gross_profit_stays_none_and_never_fires(self) -> None:
        yearly = [
            {"fiscal_year": "2023-12-31", "revenue": 1100.0, "gross_profit": 440.0},
            {"fiscal_year": "2024-12-31", "revenue": 1200.0, "gross_profit": None},
        ]
        hm = _build(yearly, ttm_gross_margin=0.40)
        assert hm.warnings == []
        assert hm.gross_margin[-1] is None
        assert hm.cogs[-1] is None


class TestAnnualSeriesLagDisclosure:
    def test_lagging_series_warns_naming_both_dates(self) -> None:
        lagging = [
            {"fiscal_year": "2021-12-31", "revenue": 900.0, "gross_profit": 360.0},
            {"fiscal_year": "2022-12-31", "revenue": 1000.0, "gross_profit": 400.0},
            {"fiscal_year": "2023-12-31", "revenue": 1100.0, "gross_profit": 440.0},
            {"fiscal_year": "2024-12-31", "revenue": 1200.0, "gross_profit": 480.0},
        ]
        hm = _build(lagging, ttm_gross_margin=0.40, ttm_period_end=_EHC_TTM_PERIOD_END)
        assert len(hm.warnings) == 1
        warning = hm.warnings[0]
        assert "2024-12-31" in warning
        assert "2026-06-30" in warning
        assert "18 months later" in warning
        assert "lags the reported periods" in warning

    def test_normal_six_month_gap_does_not_warn(self) -> None:
        """FY2025 ending 2025-12-31 against a TTM window ending 2026-06-30 is the
        normal reporting lag — no disclosure."""
        hm = _build(
            _EHC_CROSSED,
            ttm_gross_margin=_EHC_TTM_MARGIN,
            ttm_period_end=_EHC_TTM_PERIOD_END,
        )
        assert not any("lags the reported periods" in w for w in hm.warnings)

    def test_no_warning_without_a_ttm_period_end(self) -> None:
        hm = _build(_EHC_CROSSED, ttm_gross_margin=_EHC_TTM_MARGIN)
        assert not any("lags the reported periods" in w for w in hm.warnings)


class TestEquitySeries:
    def test_shareholders_equity_is_populated_from_total_equity(self) -> None:
        """The provider now emits the parent-only ``total_equity`` leg; the series
        used to ship all-null while the balance sheet carried the figure."""
        hm = _build(_EHC_CROSSED, ttm_gross_margin=_EHC_TTM_MARGIN)
        assert hm.shareholders_equity == pytest.approx(
            [1_310_300_000, 1_647_500_000, 2_067_000_000, 2_438_200_000]
        )

    def test_shareholders_equity_stays_none_when_the_provider_omits_it(self) -> None:
        yearly = [{"fiscal_year": "2024-12-31", "revenue": 1200.0, "gross_profit": 480.0}]
        hm = _build(yearly)
        assert hm.shareholders_equity == [None]
