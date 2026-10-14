"""Audit invariants for v5 §6.6 historical-bands compute.

Three high-value contracts pinned:

1. **Leaf-layer isolation** — historical_valuation.py is the leaf the bands
   endpoint trusts; it must not reach into providers, the LLM stack, or
   upper engine layers. (The generic compute/* test catches this; we repeat
   it inline for visibility.)

2. **Quantile + current_classification reproducibility** — spec §6.6 lets
   the UI say "现在贵 / 合理 / 便宜" by comparing current to p75 / p90.
   That classification must be deterministic; same inputs → same answer.

3. **Degenerate inputs produce a graceful empty band**, not exceptions —
   missing FCF / empty price history / missing shares all return an empty
   HistoricalBand with a Chinese warning so the UI keeps rendering.
"""

from __future__ import annotations

import math
import re
from datetime import date
from pathlib import Path

import pytest

from finrobot.engine.primitives.historical_valuation import (
    PricePoint,
    YearlyFinancials,
    compute_historical_band,
)

SRC = (
    Path(__file__).resolve().parents[2]
    / "finrobot"
    / "engine"
    / "primitives"
    / "historical_valuation.py"
)


# ---------------------------------------------------------------------------
# Source invariants
# ---------------------------------------------------------------------------


class TestLeafIsolation:
    def test_no_forbidden_imports(self) -> None:
        src = SRC.read_text()
        forbidden = (
            "from finrobot.engine.pipelines",
            "from finrobot.engine.agents",
            "from finrobot.engine.orchestrator",
            "from finrobot.engine.data",
            "from finrobot.artifact",
            "import pydantic_ai",
            "from pydantic_ai",
            "import openai",
            "import yfinance",
            "import finnhub",
            "import pandas",
        )
        violations = [
            pat for pat in forbidden if re.search(rf"^\s*{re.escape(pat)}", src, re.MULTILINE)
        ]
        assert not violations, f"historical_valuation leaks: {violations}"


# ---------------------------------------------------------------------------
# Determinism contract
# ---------------------------------------------------------------------------


def _yearly(
    fy: int, *, ebitda: float | None = 30, fcf: float | None = 20, debt: float | None = 0
) -> YearlyFinancials:
    return YearlyFinancials(
        fiscal_date=date(fy, 12, 31),
        ebitda=ebitda,
        free_cash_flow=fcf,
        net_debt=debt,
    )


def _price(d: date, close: float) -> PricePoint:
    return PricePoint(sample_date=d, close=close)


class TestWithheldBandReason:
    """A withheld band must name the input that is actually missing.

    Live 2026-10-12 on NFLX the EV/EBITDA band was withheld while EBITDA AND free
    cash flow were both present — every year's net debt was None (the yfinance
    yearly path emitted no debt/cash legs). The old copy ("check whether EBITDA /
    FCF is disclosed") sent the reader looking for a disclosure that was right
    there in the data.
    """

    def test_missing_net_debt_is_named_and_ebitda_is_not_blamed(self) -> None:
        yearly = [_yearly(2024, ebitda=25, debt=None), _yearly(2025, ebitda=30, debt=None)]
        band = compute_historical_band(
            metric="ev_ebitda",
            yearly=yearly,
            prices=[_price(date(2025, 6, 1), 110.0)],
            shares_outstanding=10,
        )
        assert band.sample_count == 0
        assert len(band.warnings) == 1
        assert "net debt" in band.warnings[0]
        assert "EBITDA" not in band.warnings[0]

    def test_missing_ebitda_is_named(self) -> None:
        band = compute_historical_band(
            metric="ev_ebitda",
            yearly=[_yearly(2025, ebitda=None)],
            prices=[_price(date(2025, 6, 1), 110.0)],
            shares_outstanding=10,
        )
        assert band.sample_count == 0
        assert "EBITDA" in band.warnings[0]

    def test_p_fcf_band_names_free_cash_flow(self) -> None:
        """p_fcf needs no net debt, so its missing input must be named as FCF."""
        band = compute_historical_band(
            metric="p_fcf",
            yearly=[_yearly(2025, fcf=None)],
            prices=[_price(date(2025, 6, 1), 110.0)],
            shares_outstanding=10,
        )
        assert band.sample_count == 0
        assert "free cash flow" in band.warnings[0]


class TestEvEbitdaBand:
    def test_basic_band_computed_for_three_yearly_rows(self) -> None:
        yearly = [_yearly(2023, ebitda=20), _yearly(2024, ebitda=25), _yearly(2025, ebitda=30)]
        prices = [
            _price(date(2024, 6, 1), 100.0),  # ebitda from FY 2023 (20)
            _price(date(2025, 6, 1), 110.0),  # ebitda from FY 2024 (25)
            _price(date(2026, 1, 1), 120.0),  # ebitda from FY 2025 (30)
        ]
        band = compute_historical_band(
            metric="ev_ebitda",
            yearly=yearly,
            prices=prices,
            shares_outstanding=10,
        )
        # multiples: (100*10)/20=50, (110*10)/25=44, (120*10)/30=40
        assert band.current == 40.0
        assert band.median == 44.0
        assert band.sample_count == 3
        # W1-C2: with no canonical TTM override the current point is on the
        # trailing-annual EBITDA basis — that口径 must be disclosed so a caller
        # (the standalone /historical-bands route) can't silently flip 贵/合理/
        # 便宜 on an annual basis against the report's TTM verdict.
        assert any("annual" in w or "TTM" in w for w in band.warnings), band.warnings

    def test_nan_close_does_not_poison_band_quantiles(self) -> None:
        """A single NaN close (halted session / bad provider row) used to slip
        past `is None or <= 0` (NaN comparisons are False) and poison every
        quantile of the band — median/p25/p75 all NaN feeding the 贵/合理/便宜
        classifier. The NaN sample must simply be dropped."""
        yearly = [_yearly(2023, ebitda=20), _yearly(2024, ebitda=25), _yearly(2025, ebitda=30)]
        prices = [
            _price(date(2024, 6, 1), 100.0),
            _price(date(2025, 6, 1), float("nan")),
            _price(date(2026, 1, 1), 120.0),
        ]
        band = compute_historical_band(
            metric="ev_ebitda",
            yearly=yearly,
            prices=prices,
            shares_outstanding=10,
        )
        assert band.sample_count == 2
        assert band.median is not None and math.isfinite(band.median)
        assert band.p25 is not None and math.isfinite(band.p25)
        assert band.p75 is not None and math.isfinite(band.p75)
        assert all(math.isfinite(v) for _, v in band.timeline)

    def test_nan_net_debt_sample_is_dropped(self) -> None:
        """NaN can also enter via the financial leg (net_debt) — the EV sum
        propagates it; the isfinite gate must drop that sample too."""
        yearly = [
            _yearly(2023, ebitda=20),
            _yearly(2024, ebitda=25, debt=float("nan")),
            _yearly(2025, ebitda=30),
        ]
        prices = [
            _price(date(2024, 6, 1), 100.0),
            _price(date(2025, 6, 1), 110.0),
            _price(date(2026, 1, 1), 120.0),
        ]
        band = compute_historical_band(
            metric="ev_ebitda",
            yearly=yearly,
            prices=prices,
            shares_outstanding=10,
        )
        assert band.sample_count == 2
        assert band.median is not None and math.isfinite(band.median)

    def test_current_override_replaces_current_and_discloses_basis(self) -> None:
        """B2: a TTM current_override replaces the band's current point only.

        Historical quantiles/timeline stay on the annual basis; a warning must
        disclose the mixed口径 rather than silently swap it.
        """
        yearly = [_yearly(2023, ebitda=20), _yearly(2024, ebitda=25), _yearly(2025, ebitda=30)]
        prices = [
            _price(date(2024, 6, 1), 100.0),  # 50.0
            _price(date(2025, 6, 1), 110.0),  # 44.0
            _price(date(2026, 1, 1), 120.0),  # annual-basis current would be 40.0
        ]
        band = compute_historical_band(
            metric="ev_ebitda",
            yearly=yearly,
            prices=prices,
            shares_outstanding=10,
            current_override=37.5,  # canonical TTM multiple from the comps chapter
        )
        assert band.current == 37.5  # overridden, not the annual 40.0
        assert band.median == 44.0  # historical quantiles untouched (annual basis)
        assert band.sample_count == 3
        assert any("TTM" in w for w in band.warnings)

    def test_current_override_ignored_when_non_positive(self) -> None:
        """A zero/negative override is rejected — falls back to the annual current."""
        yearly = [_yearly(2025, ebitda=30)]
        prices = [_price(date(2026, 1, 1), 120.0)]  # (120*10)/30 = 40.0
        band = compute_historical_band(
            metric="ev_ebitda",
            yearly=yearly,
            prices=prices,
            shares_outstanding=10,
            current_override=0.0,
        )
        assert band.current == 40.0
        # Fell back to the trailing-annual current → discloses the口径 (W1-C2).
        assert any("annual" in w or "TTM" in w for w in band.warnings), band.warnings

    def test_annual_fallback_current_discloses_caliber(self) -> None:
        """W1-C2: when no TTM ``current_override`` is supplied the band's current
        point is the trailing-annual multiple — it MUST carry a口径 warning so
        the standalone /historical-bands route can't render '极贵' on an annual
        basis while the report calls the same ticker '合理' on TTM (signal flip)."""
        yearly = [_yearly(2025, ebitda=30)]
        prices = [_price(date(2026, 1, 1), 120.0)]  # (120*10)/30 = 40.0
        band = compute_historical_band(
            metric="ev_ebitda",
            yearly=yearly,
            prices=prices,
            shares_outstanding=10,
        )
        assert band.current == 40.0
        assert any("annual" in w for w in band.warnings), band.warnings

    def test_net_debt_added_to_ev(self) -> None:
        yearly = [_yearly(2024, ebitda=10, debt=500)]
        prices = [_price(date(2025, 1, 1), 100.0)]
        band = compute_historical_band(
            metric="ev_ebitda",
            yearly=yearly,
            prices=prices,
            shares_outstanding=10,
        )
        # (100*10 + 500) / 10 = 150
        assert band.current == 150.0

    def test_prices_before_any_fiscal_year_are_skipped_with_warning(self) -> None:
        yearly = [_yearly(2024)]
        prices = [
            _price(date(2022, 1, 1), 50.0),
            _price(date(2025, 1, 1), 100.0),
        ]
        band = compute_historical_band(
            metric="ev_ebitda",
            yearly=yearly,
            prices=prices,
            shares_outstanding=10,
        )
        assert band.sample_count == 1
        assert any("predate the earliest fiscal year" in w for w in band.warnings)


class TestPFcfBand:
    def test_p_fcf_uses_market_cap_over_fcf(self) -> None:
        yearly = [_yearly(2024, fcf=20)]
        prices = [_price(date(2025, 1, 1), 100.0)]
        band = compute_historical_band(
            metric="p_fcf",
            yearly=yearly,
            prices=prices,
            shares_outstanding=10,
        )
        # (100*10) / 20 = 50
        assert band.current == 50.0

    def test_missing_fcf_yields_empty_band(self) -> None:
        yearly = [_yearly(2024, fcf=None)]
        prices = [_price(date(2025, 1, 1), 100.0)]
        band = compute_historical_band(
            metric="p_fcf",
            yearly=yearly,
            prices=prices,
            shares_outstanding=10,
        )
        assert band.current is None
        assert band.sample_count == 0
        assert band.warnings  # something explaining why


# ---------------------------------------------------------------------------
# Reproducibility — same inputs always produce same quantiles
# ---------------------------------------------------------------------------


class TestQuantileReproducibility:
    def test_quantiles_match_known_inputs(self) -> None:
        # Construct prices where the multiples line up to exact known quantiles.
        yearly = [_yearly(2024, ebitda=10, debt=0)]
        # 5 prices → multiples 10, 20, 30, 40, 50 (price * 1 share / 10 EBITDA = price/10)
        prices = [_price(date(2025, i, 1), 100.0 + i * 100) for i in range(1, 6)]
        # multiples: (200, 300, 400, 500, 600) / 10 = (20, 30, 40, 50, 60)
        band = compute_historical_band(
            metric="ev_ebitda",
            yearly=yearly,
            prices=prices,
            shares_outstanding=1,
        )
        assert band.median == 40.0
        # numpy linear interpolation: p25 of [20,30,40,50,60] = 30, p75 = 50
        assert band.p25 == 30.0
        assert band.p75 == 50.0
        assert band.p90 == pytest.approx(56.0)

    def test_deterministic_across_repeated_calls(self) -> None:
        from datetime import timedelta

        yearly = [_yearly(2024, ebitda=25)]
        prices = [_price(date(2025, 1, 1) + timedelta(days=i), 100.0 + i) for i in range(30)]
        a = compute_historical_band(
            metric="ev_ebitda", yearly=yearly, prices=prices, shares_outstanding=10
        )
        b = compute_historical_band(
            metric="ev_ebitda", yearly=yearly, prices=prices, shares_outstanding=10
        )
        assert a == b


# ---------------------------------------------------------------------------
# Degenerate inputs
# ---------------------------------------------------------------------------


class TestDegenerateInputs:
    def test_zero_shares_returns_empty_band(self) -> None:
        band = compute_historical_band(
            metric="ev_ebitda",
            yearly=[_yearly(2024)],
            prices=[_price(date(2025, 1, 1), 100)],
            shares_outstanding=0,
        )
        assert band.sample_count == 0
        assert any("shares" in w for w in band.warnings)

    def test_empty_price_history_returns_empty_band(self) -> None:
        band = compute_historical_band(
            metric="ev_ebitda",
            yearly=[_yearly(2024)],
            prices=[],
            shares_outstanding=10,
        )
        assert band.sample_count == 0

    def test_empty_financials_returns_empty_band(self) -> None:
        band = compute_historical_band(
            metric="ev_ebitda",
            yearly=[],
            prices=[_price(date(2025, 1, 1), 100)],
            shares_outstanding=10,
        )
        assert band.sample_count == 0


# ---------------------------------------------------------------------------
# Downsampling for chart payload size
# ---------------------------------------------------------------------------


class TestDownsample:
    def test_long_timeline_is_capped_below_max_points(self) -> None:
        yearly = [_yearly(2024)]
        prices = [
            _price(date(2025, 1, 1) if i == 0 else date(2025, 1, 1), 100 + i) for i in range(500)
        ]
        # Use distinct dates so dedup doesn't collapse
        prices = []
        from datetime import timedelta

        for i in range(500):
            prices.append(_price(date(2025, 1, 1) + timedelta(days=i), 100 + i))
        band = compute_historical_band(
            metric="ev_ebitda",
            yearly=yearly,
            prices=prices,
            shares_outstanding=10,
        )
        # All 500 samples count toward stats; only timeline gets downsampled.
        assert band.sample_count == 500
        assert len(band.timeline) <= 120
        # First and last sample must be present so the chart keeps its edges.
        assert band.timeline[0][0] == prices[0].sample_date
        assert band.timeline[-1][0] == prices[-1].sample_date


# ---------------------------------------------------------------------------
# Structural-break disclosure (l1)
# ---------------------------------------------------------------------------


class TestStructuralBreakDisclosure:
    """A window whose EBITDA base jumps ≥3x blends two regimes.

    Live 2026-10-13 NVDA: the 5-year window opens 2023-01-31, when the trailing FY
    EBITDA was $5.99B; FY2024's $35.58B is a 5.9x step, so p25 = 37.76x / p90 =
    183.34x are driven by the pre-ramp base and `classify_band` badged the stock
    CHEAP (27.06x ≤ 37.76x). The publication is a DISCLOSURE: the quantiles and the
    classification are unchanged, the break (years + step) is named on the band so
    the UI can caveat the badge.
    """

    def _band_with_ramp(self):
        yearly = [_yearly(2023, ebitda=6), _yearly(2024, ebitda=36), _yearly(2025, ebitda=90)]
        prices = [
            _price(date(2024, 6, 1), 100.0),  # FY2023 EBITDA 6  → 16.7x
            _price(date(2025, 6, 1), 110.0),  # FY2024 EBITDA 36 → 3.1x
            _price(date(2026, 1, 1), 120.0),  # FY2025 EBITDA 90 → 1.3x
        ]
        return compute_historical_band(
            metric="ev_ebitda", yearly=yearly, prices=prices, shares_outstanding=10
        )

    def test_structural_ebitda_step_is_published_on_the_band(self):
        band = self._band_with_ramp()
        assert band.structural_break is not None
        step = band.structural_break
        # The 6x step FY2023 → FY2024 is the dominant regime change (the 2.5x
        # FY2024 → FY2025 step is below the 3x threshold).
        assert step.from_fiscal_date == date(2023, 12, 31)
        assert step.to_fiscal_date == date(2024, 12, 31)
        assert step.from_ebitda == 6.0
        assert step.to_ebitda == 36.0
        assert step.step_multiple == pytest.approx(6.0)

    def test_break_is_disclosed_as_a_warning(self):
        band = self._band_with_ramp()
        hits = [w for w in band.warnings if "structural EBITDA break" in w]
        assert hits, band.warnings
        assert "2023-12-31" in hits[0] and "2024-12-31" in hits[0]
        assert "6.0x" in hits[0]
        assert "quantile method is unchanged" in hits[0]

    def test_quantiles_are_unchanged_by_the_disclosure(self):
        band = self._band_with_ramp()
        # The published numbers are exactly the pre-disclosure computation: the
        # method is a product decision, only the disclosure was added.
        # multiples: 1000/6, 1100/36, 1200/90 → sorted [13.33, 30.56, 166.67];
        # inclusive linear interpolation puts p25 halfway between the first two.
        assert band.median == pytest.approx(1100.0 / 36)
        assert band.current == pytest.approx(1200.0 / 90)
        assert band.p25 == pytest.approx(1200.0 / 90 + 0.5 * (1100.0 / 36 - 1200.0 / 90))

    def test_no_break_when_growth_stays_under_three_x(self):
        yearly = [_yearly(2023, ebitda=20), _yearly(2024, ebitda=25), _yearly(2025, ebitda=30)]
        prices = [
            _price(date(2024, 6, 1), 100.0),
            _price(date(2025, 6, 1), 110.0),
            _price(date(2026, 1, 1), 120.0),
        ]
        band = compute_historical_band(
            metric="ev_ebitda", yearly=yearly, prices=prices, shares_outstanding=10
        )
        assert band.structural_break is None
        assert not any("structural EBITDA break" in w for w in band.warnings)

    def test_break_in_an_unsampled_fiscal_year_is_not_flagged(self):
        """Only fiscal years the window's samples actually aligned to count: a step
        in a year no price point ever used cannot have shaped the quantiles."""
        yearly = [_yearly(2023, ebitda=1), _yearly(2024, ebitda=6), _yearly(2025, ebitda=90)]
        # Every price sits after FY2025, so every sample uses the SAME denominator.
        prices = [_price(date(2026, 1, 1), 100.0), _price(date(2026, 6, 1), 110.0)]
        band = compute_historical_band(
            metric="ev_ebitda", yearly=yearly, prices=prices, shares_outstanding=10
        )
        assert band.sample_count == 2
        assert band.structural_break is None

    def test_p_fcf_band_publishes_no_ebitda_break(self):
        """The break is an EBITDA-denominator signal; a P/FCF band must not claim it."""
        yearly = [_yearly(2023, ebitda=6, fcf=20), _yearly(2024, ebitda=36, fcf=25)]
        prices = [_price(date(2024, 6, 1), 100.0), _price(date(2025, 6, 1), 110.0)]
        band = compute_historical_band(
            metric="p_fcf", yearly=yearly, prices=prices, shares_outstanding=10
        )
        assert band.structural_break is None

    def test_ebitda_collapse_is_disclosed_too(self):
        """A ≥3x EBITDA COLLAPSE blends regimes exactly as a ramp does: the post-step
        multiples are computed off a base a third the size, so the same caveat must
        fire (the step is reported as a magnitude, not a signed ratio)."""
        yearly = [_yearly(2023, ebitda=90), _yearly(2024, ebitda=6)]
        prices = [_price(date(2024, 6, 1), 100.0), _price(date(2025, 6, 1), 110.0)]
        band = compute_historical_band(
            metric="ev_ebitda", yearly=yearly, prices=prices, shares_outstanding=10
        )
        assert band.structural_break is not None
        assert band.structural_break.step_multiple == pytest.approx(15.0)
        assert any("structural EBITDA break" in w for w in band.warnings)
