"""Unit tests for the pure fund-metric operators (``engine.compute.operators.fund_metrics``).

Numbers are the REAL canonical values measured on the live providers (IEI bond
ETF / VTSAX index mutual fund), not invented — see ``NormalizedFundProfile``.

No network: every input is constructed here.
"""

from __future__ import annotations

import math
from datetime import date, timedelta

import pytest

from finrobot.engine.compute.operators.fund_metrics import (
    duration_rate_sensitivity,
    expense_cost_analysis,
    nav_series_statistics,
    portfolio_concentration,
    premium_discount,
)

# ── Real IEI values (measured) ────────────────────────────────────────────────
IEI_NET_EXPENSE = 0.0015
IEI_CATEGORY_AVG_EXPENSE = 0.005287
IEI_NAV = 113.43545
IEI_MARKET_PRICE = 113.48
IEI_BOND_DURATION = 3.54


def _bar_dates(count: int, *, span_days: int) -> list[date]:
    """``count`` bar dates ending today, evenly spread over ``span_days`` calendar days.

    Models a real range fetch: the first bar sits ``span_days`` back and the
    weekend/holiday sessions are simply absent.
    """
    last = date.today()
    first = last - timedelta(days=span_days)
    step = (last - first) / max(count - 1, 1)
    return [first + step * index for index in range(count)]


def _dated_growth(count: int, *, span_days: int, rate: float) -> tuple[list[float], list[date]]:
    """A series compounding ``rate``/yr over the ACTUAL bar dates.

    Generating the closes from the dates (rather than from a session index) means
    each window's CAGR comes back as exactly ``rate``.
    """
    dates = _bar_dates(count, span_days=span_days)
    if not dates:
        return [], []
    base = dates[0]
    closes = [100.0 * (1.0 + rate) ** ((day - base).days / 365.25) for day in dates]
    return closes, dates


class TestNavSeriesStatistics:
    def test_one_year_of_history_recovers_the_1y_cagr(self):
        closes, dates = _dated_growth(253, span_days=366, rate=0.10)
        stats = nav_series_statistics(closes, risk_free_rate=0.02, dates=dates)
        assert stats["cagr_1y"] == pytest.approx(0.10, rel=1e-6)
        # A monotonically rising series never draws down.
        assert stats["max_drawdown"] == pytest.approx(0.0)
        # 3y / 5y windows are not spanned by a one-year series.
        assert stats["cagr_3y"] is None
        assert stats["cagr_5y"] is None

    def test_five_calendar_years_of_sessions_compute_every_window(self):
        # 1253 bars over five CALENDAR years: five calendar years hold ~1253-1258
        # US sessions, NOT 5*252 = 1260 — which is why the old session-count rule
        # (>= years*252 + 1) left cagr_5y permanently unreachable.
        closes, dates = _dated_growth(1253, span_days=1830, rate=0.10)
        assert len(closes) < 5 * 252 + 1
        stats = nav_series_statistics(closes, dates=dates)
        assert stats["cagr_1y"] == pytest.approx(0.10, rel=1e-6)
        assert stats["cagr_3y"] == pytest.approx(0.10, rel=1e-6)
        assert stats["cagr_5y"] == pytest.approx(0.10, rel=1e-6)

    def test_windows_need_dates(self):
        # A bar count cannot decide whether a series spans a calendar window, so
        # without dates the CAGRs abstain rather than guess.
        closes = [100.0 * (1.10 ** (i / 252)) for i in range(5 * 252 + 1)]
        stats = nav_series_statistics(closes)
        assert stats["cagr_1y"] is None
        assert stats["cagr_3y"] is None
        assert stats["cagr_5y"] is None
        assert stats["volatility"] is not None

    def test_volatility_and_sharpe_from_a_moving_series(self):
        closes = [100.0 + (1.0 if i % 2 else -1.0) for i in range(60)]
        stats = nav_series_statistics(closes, risk_free_rate=0.02)
        assert stats["volatility"] is not None and stats["volatility"] > 0
        assert stats["sharpe"] is not None

    def test_max_drawdown_is_peak_to_trough_fraction(self):
        stats = nav_series_statistics([100.0, 120.0, 90.0, 110.0])
        # Peak 120 → trough 90 = 25% drawdown.
        assert stats["max_drawdown"] == pytest.approx(0.25)

    def test_short_series_degrades_windows_to_none_but_keeps_volatility(self):
        closes, dates = _dated_growth(100, span_days=120, rate=0.0)
        stats = nav_series_statistics(closes, dates=dates)
        assert stats["cagr_1y"] is None
        assert stats["cagr_3y"] is None
        assert stats["cagr_5y"] is None
        assert stats["volatility"] is not None

    def test_misaligned_or_unsorted_dates_are_ignored(self):
        closes, dates = _dated_growth(253, span_days=366, rate=0.10)
        # Wrong length → not a usable date axis.
        assert nav_series_statistics(closes, dates=dates[:100])["cagr_1y"] is None
        # Out-of-order → anchoring would be silently wrong, so abstain.
        assert nav_series_statistics(closes, dates=list(reversed(dates)))["cagr_1y"] is None
        # A NaN close drops its date in lockstep, leaving 252 usable points.
        holed = list(closes)
        holed[10] = math.nan
        holed_dates = list(dates)
        assert nav_series_statistics(holed, dates=holed_dates)["cagr_1y"] is not None

    def test_degenerate_series_returns_all_none(self):
        for closes in ([], [100.0]):
            stats = nav_series_statistics(closes)
            assert set(stats.values()) == {None}

    def test_non_finite_points_are_dropped(self):
        stats = nav_series_statistics([100.0, math.nan, 110.0])
        # Two usable points → max drawdown computable, no crash from the NaN.
        assert stats["max_drawdown"] == pytest.approx(0.0)


class TestExpenseCostAnalysis:
    def test_real_iei_expense_against_its_category_average(self):
        out = expense_cost_analysis(
            IEI_NET_EXPENSE,
            0.0016,
            0.04,
            5,
            IEI_CATEGORY_AVG_EXPENSE,
        )
        expected_drag = 10_000.0 * (1.04**5 - (1.04 - IEI_NET_EXPENSE) ** 5)
        assert out["expense_drag_usd_per_10k"] == pytest.approx(expected_drag)
        assert out["expense_drag_usd_per_10k"] > 0
        assert out["fee_share_of_gross_return"] == pytest.approx(IEI_NET_EXPENSE / 0.04)
        assert out["fee_vs_category_avg"] == pytest.approx(
            IEI_NET_EXPENSE - IEI_CATEGORY_AVG_EXPENSE
        )
        assert out["fee_vs_category_avg"] < 0  # cheaper than peers
        assert out["category_avg_expense_ratio"] == IEI_CATEGORY_AVG_EXPENSE
        assert out["horizon_years"] == 5.0

    def test_missing_inputs_stay_none_never_zero(self):
        out = expense_cost_analysis(None, None, None, 5, None)
        assert out["expense_drag_usd_per_10k"] is None
        assert out["fee_share_of_gross_return"] is None
        assert out["fee_vs_category_avg"] is None
        assert out["category_avg_expense_ratio"] is None

    def test_negative_growth_still_costs_but_has_no_fee_share(self):
        # A fee is still paid on a losing fund, but a non-positive gross return
        # has no meaningful "share of return".
        out = expense_cost_analysis(0.0015, None, -0.0255, 5, None)
        assert out["expense_drag_usd_per_10k"] is not None
        assert out["expense_drag_usd_per_10k"] > 0
        assert out["fee_share_of_gross_return"] is None

    def test_zero_horizon_reports_no_drag(self):
        out = expense_cost_analysis(0.0015, None, 0.04, 0, None)
        assert out["expense_drag_usd_per_10k"] is None


class TestPortfolioConcentration:
    def test_top10_hhi_and_effective_n(self):
        weights = {f"H{i}": 0.05 for i in range(12)}
        out = portfolio_concentration(weights)
        assert out["top10_weight"] == pytest.approx(0.5)
        assert out["hhi"] == pytest.approx(12 * 0.05**2)
        assert out["effective_n"] == pytest.approx(1.0 / (12 * 0.05**2))
        assert out["unlisted_remainder"] == pytest.approx(1.0 - 0.6)
        assert out["holdings_count"] == 12.0

    def test_single_holding_is_fully_concentrated(self):
        out = portfolio_concentration({"NVDA": 1.0})
        assert out["hhi"] == pytest.approx(1.0)
        assert out["effective_n"] == pytest.approx(1.0)
        assert out["unlisted_remainder"] == pytest.approx(0.0)

    def test_empty_mapping_returns_all_none(self):
        out = portfolio_concentration({})
        assert set(out.values()) == {None}


class TestDurationRateSensitivity:
    def test_real_iei_duration_and_nav(self):
        out = duration_rate_sensitivity(IEI_BOND_DURATION, IEI_NAV)
        assert out is not None
        assert out["nav_change_up_100bp"] == pytest.approx(-0.0354)
        assert out["nav_change_down_100bp"] == pytest.approx(0.0354)
        assert out["nav_change_up_100bp_usd"] == pytest.approx(IEI_NAV * -0.0354)
        assert out["nav_change_down_100bp_usd"] == pytest.approx(IEI_NAV * 0.0354)

    def test_missing_inputs_return_none(self):
        assert duration_rate_sensitivity(None, IEI_NAV) is None
        assert duration_rate_sensitivity(IEI_BOND_DURATION, None) is None


class TestPremiumDiscount:
    def test_real_iei_premium_is_a_fraction(self):
        value = premium_discount(IEI_NAV, IEI_MARKET_PRICE)
        assert value == pytest.approx(IEI_MARKET_PRICE / IEI_NAV - 1.0)
        assert value > 0  # IEI traded at a small premium

    def test_missing_or_non_positive_nav_returns_none(self):
        assert premium_discount(None, IEI_MARKET_PRICE) is None
        assert premium_discount(IEI_NAV, None) is None
        assert premium_discount(0.0, IEI_MARKET_PRICE) is None
