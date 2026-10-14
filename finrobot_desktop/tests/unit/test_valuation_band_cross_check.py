"""The own-history EV/EBITDA band cross-check (owner review 2026-10-13).

The football field shows the issuer's own 5-year EV/EBITDA band beside the
published target; nothing used to apply the band to the run's TTM EBITDA and
publish the implied per-share values. These tests pin the math (band multiple ×
TTM EBITDA → EV→equity bridge → per share), the never-fabricate rule (no band →
no cross-check), the bank suppression, and the basis wording that keeps the
method's own band distinct from the published target band.
"""

from __future__ import annotations

import pytest

from finrobot.engine.compute.operators.valuation_aggregator import aggregate_valuation
from finrobot.engine.compute.operators.valuation_synthesis import (
    resolve_canonical_thesis,
    synthesize_valuations,
)
from finrobot.engine.models.financial import CrossCheck, ValuationMethod

# EHC-like inputs (the owner-review case): own 5-year EV/EBITDA band on the run's
# TTM EBITDA, with the NCI the EV bridge must clear.
_EHC = {
    "ttm_ebitda": 1_463_500_032.0,
    "net_debt": 2_842_299_904.0 - 107_700_000.0,
    "nci": 863_400_000.0,
    "shares": 98_653_384.0,
    "p25": 9.975651894724482,
    "median": 10.590751147845076,
    "p75": 11.401397804210033,
}


def _band_cross_check(**overrides: object) -> list[CrossCheck]:
    kwargs: dict[str, object] = {
        "ticker": "EHC",
        "current_price": 124.42,
        "historical_ev_ebitda_band": (_EHC["p25"], _EHC["p75"]),
        "historical_ev_ebitda_median": _EHC["median"],
        "historical_ev_ebitda_sample_n": 947,
        "historical_ev_ebitda_window_years": 5,
        "ttm_ebitda": _EHC["ttm_ebitda"],
        "current_net_debt": _EHC["net_debt"],
        "shares_outstanding": _EHC["shares"],
        "noncontrolling_interest": _EHC["nci"],
    }
    kwargs.update(overrides)
    return aggregate_valuation(**kwargs).cross_checks  # type: ignore[arg-type]


class TestCrossCheckMath:
    def test_band_multiple_times_ttm_ebitda_minus_bridge_over_shares(self):
        """p25→low, median→mid, p75→high through the full EV→equity bridge.

        The preferred stock / NCI claims are subtracted — an EV multiple applied
        to EBITDA only becomes COMMON equity after they clear.
        """
        checks = _band_cross_check(
            ttm_ebitda=1_000.0,
            current_net_debt=2_000.0,
            shares_outstanding=100.0,
            noncontrolling_interest=400.0,
            historical_ev_ebitda_band=(8.0, 12.0),
            historical_ev_ebitda_median=10.0,
            preferred_stock=100.0,
            historical_ev_ebitda_window_years=5,
            historical_ev_ebitda_sample_n=500,
        )
        assert len(checks) == 1
        check = checks[0]
        assert check.name == "ev_ebitda_band"
        # (8×1000 − 2000 − 100 − 400) / 100 = 55.0
        assert check.low == pytest.approx(55.0)
        # (10×1000 − 2500) / 100 = 75.0
        assert check.mid == pytest.approx(75.0)
        # (12×1000 − 2500) / 100 = 95.0
        assert check.high == pytest.approx(95.0)

    def test_ehc_shaped_band_lands_below_the_dcf_target(self):
        """The owner-review case: the own-history band prices EHC near its market
        price (~$111–$133), i.e. FAR below the $225.91 DCF target — exactly the
        contradiction the cross-check exists to surface."""
        check = _band_cross_check()[0]
        expected_mid = (
            _EHC["median"] * _EHC["ttm_ebitda"] - _EHC["net_debt"] - _EHC["nci"]
        ) / _EHC["shares"]
        assert check.mid == pytest.approx(expected_mid, rel=1e-9)
        assert check.low < check.mid < check.high
        assert check.high < 140.0
        assert check.mid < 225.91

    def test_basis_names_metric_window_and_ttm_ebitda_and_note_excludes_blend(self):
        """The entry must be self-describing: metric, window, the TTM EBITDA
        basis, and an explicit statement that it is NOT in the published blend."""
        check = _band_cross_check()[0]
        assert "EV/EBITDA" in check.basis
        assert "5-year" in check.basis
        assert "TTM EBITDA" in check.basis
        assert "net debt" in check.basis
        assert "NCI" in check.basis
        assert "947 samples" in check.basis
        assert "cross-check" in check.note
        assert "excluded from the published target blend" in check.note
        assert "mean-reversion" in check.label.lower() or "Mean-reversion" in check.note

    def test_missing_median_emits_no_entry(self):
        """No median → no mid → NO cross-check. Never a fabricated 0 band."""
        assert _band_cross_check(historical_ev_ebitda_median=None) == []

    def test_missing_ttm_ebitda_emits_no_entry(self):
        assert _band_cross_check(ttm_ebitda=None) == []

    def test_missing_shares_or_net_debt_emits_no_entry(self):
        assert _band_cross_check(shares_outstanding=None) == []
        assert _band_cross_check(current_net_debt=None) == []

    def test_scaling_shares_by_k_scales_the_band_by_one_over_k_and_keeps_the_samples(self):
        """§7.3's metamorphic relation, and the one assertion that would have caught
        instance B.

        The row is the EV→equity bridge OVER shares, so scaling the share count by k
        must scale low/mid/high by exactly 1/k. The band's own ``sample_count`` is a
        property of the BAND, not of the count, so it must not move — and it is the
        quantity that says whether the band is evidence at all. Instance B (THC
        20:27:40) published a cross-check its own decision had never read because
        ``fetch_reverse_multiple_band`` was called without the run's share count and
        the band resolved to 0 samples; the fix is a share count, and this test is
        what says the two quantities are independent.
        """
        band = (8.0, 12.0)
        small = _band_cross_check(
            ttm_ebitda=1_000.0,
            current_net_debt=2_000.0,
            shares_outstanding=100.0,
            noncontrolling_interest=0.0,
            preferred_stock=0.0,
            historical_ev_ebitda_band=band,
            historical_ev_ebitda_median=10.0,
            historical_ev_ebitda_window_years=5,
            historical_ev_ebitda_sample_n=948,
        )[0]
        large = _band_cross_check(
            ttm_ebitda=1_000.0,
            current_net_debt=2_000.0,
            shares_outstanding=1_000.0,
            noncontrolling_interest=0.0,
            preferred_stock=0.0,
            historical_ev_ebitda_band=band,
            historical_ev_ebitda_median=10.0,
            historical_ev_ebitda_window_years=5,
            historical_ev_ebitda_sample_n=948,
        )[0]

        # (8×1000 − 2000)/100 = 60 · (10×1000 − 2000)/100 = 80 · (12×1000 − 2000)/100 = 100
        assert (small.low, small.mid, small.high) == pytest.approx((60.0, 80.0, 100.0))
        for small_leg, large_leg in ((small.low, large.low), (small.mid, large.mid)):
            assert large_leg == pytest.approx(small_leg / 10.0, rel=1e-12)
        assert large.high == pytest.approx(small.high / 10.0, rel=1e-12)
        assert "948 samples" in small.basis
        assert "948 samples" in large.basis

    def test_a_band_with_no_sample_count_never_claims_one(self):
        """The count is the evidence's quantity: ``sample_count`` 0 or absent means
        the band did not compute, so the row must say the count is unavailable
        instead of printing "0 samples" as if a zero-sample band were a measurement.
        """
        for n in (None, 0):
            check = _band_cross_check(historical_ev_ebitda_sample_n=n)[0]
            assert "0 samples" not in check.basis
            assert "sample count unavailable" in check.basis

    def test_bank_suppressed(self):
        """EV/EBITDA is a category error for a balance-sheet financial — the
        cross-check row is suppressed alongside the method row."""
        assert _band_cross_check(financial_sector=True) == []


class TestSynthesisCarriesCrossChecks:
    def test_synthesize_valuations_persists_cross_checks(self):
        check = _band_cross_check()[0]
        vs = synthesize_valuations(
            [
                ValuationMethod(
                    name="dcf", low=180.73, mid=225.91, high=271.10, confidence=0.85, source="DCF"
                )
            ],
            current_price=124.42,
            cross_checks=[check],
        )
        assert [c.name for c in vs.cross_checks] == ["ev_ebitda_band"]

    def test_no_cross_checks_defaults_empty(self):
        vs = synthesize_valuations(
            [
                ValuationMethod(
                    name="dcf", low=180.0, mid=225.0, high=271.0, confidence=0.85, source="DCF"
                )
            ],
            current_price=124.42,
        )
        assert vs.cross_checks == []


class TestBasisWordingDistinguishesTheThreeBands:
    def _single_method_vs(self):
        return synthesize_valuations(
            [
                ValuationMethod(
                    name="dcf",
                    low=180.73099239135718,
                    mid=225.91374048919644,
                    high=271.0964885870357,
                    confidence=0.85,
                    source="implied_price ± 20% (placeholder band, not a real distribution)",
                )
            ],
            current_price=124.42,
        )

    def test_method_own_band_and_published_band_are_both_labelled(self):
        """Owner review: the basis printed the lone method's mid as both the method
        value and the target, while the quoted range was the confidence-dial band
        and the method's own ±20% band never appeared."""
        thesis = resolve_canonical_thesis(self._single_method_vs(), "EHC")
        basis = thesis.basis or ""
        # the method's own band
        assert "own range $180.73–$271.10" in basis
        # the method value, printed once
        assert basis.count("$225.91") == 2  # method mid + the published target
        # the published band, labelled with its provenance
        assert "Published target band $169.44–$282.39" in basis
        assert "single-method confidence dial" in basis
        # the published band is NOT the method's own band
        assert "Range [$169.44, $282.39]" not in basis

    def test_degenerate_method_band_is_not_printed_as_a_range(self):
        """A method whose low/high collapsed onto its mid has no range to show.

        Owner review wording to avoid: a "low" and a "high" that are both the
        target. When the band is not a real one the clause is omitted entirely.
        """
        vs = synthesize_valuations(
            [
                ValuationMethod(
                    name="dcf", low=225.91, mid=225.91, high=225.91, confidence=0.85, source="DCF"
                )
            ],
            current_price=124.42,
        )
        basis = resolve_canonical_thesis(vs, "EHC").basis or ""
        assert "own range" not in basis
        assert "DCF $225.91 (wt 0.85)" in basis

    def test_published_band_provenance_is_the_method_mid_span_when_corroborated(self):
        vs = synthesize_valuations(
            [
                ValuationMethod(
                    name="dcf", low=260.0, mid=280.0, high=300.0, confidence=0.5, source="DCF"
                ),
                ValuationMethod(
                    name="comps_pe", low=265.0, mid=285.0, high=305.0, confidence=0.5, source="PE"
                ),
            ],
            current_price=230.0,
        )
        basis = resolve_canonical_thesis(vs, "AAPL").basis or ""
        assert "own range $260.00–$300.00" in basis
        assert "Published target band $280.00–$285.00 (span of the surviving method mids)" in basis
        assert "method-weighted blend" in basis


_BREAK_CAVEAT = (
    "the band's cheap/fair/expensive classification is computed on a window containing "
    "a structural EBITDA break (FY2023-01-31 -> FY2024-01-31, 5.9x step): the P25/P90 "
    "quantiles are driven by the pre-step small-EBITDA base - treat the badge as "
    "directional only (quantile method unchanged)."
)


class TestCrossCheckBreakCaveat:
    """l1: a quantile-only row read as a clean "$493 (+115%) CHEAP" signal.

    2026-10-13 NVDA: the own-history cross-check row is derived from a 5-year window
    that opens on the pre-ramp FY2023 EBITDA base, so its p25/p90 blend two earnings
    regimes. The row must carry the band's caveat — in a dedicated field AND in its
    basis text, so no consumer can read it as clean.
    """

    def test_caveat_lands_on_the_row_and_in_its_basis(self):
        checks = _band_cross_check(historical_ev_ebitda_break_caveat=_BREAK_CAVEAT)
        assert len(checks) == 1
        check = checks[0]
        assert check.band_break_caveat == _BREAK_CAVEAT
        assert check.basis.endswith(_BREAK_CAVEAT)

    def test_caveat_does_not_move_the_per_share_values(self):
        plain = _band_cross_check()[0]
        annotated = _band_cross_check(historical_ev_ebitda_break_caveat=_BREAK_CAVEAT)[0]
        assert (annotated.low, annotated.mid, annotated.high) == (
            plain.low,
            plain.mid,
            plain.high,
        )

    def test_absent_caveat_leaves_the_row_clean(self):
        check = _band_cross_check()[0]
        assert check.band_break_caveat is None
        assert "structural EBITDA break" not in check.basis

    def test_band_break_caveat_appears_in_the_serialized_row(self):
        """Whatever the artifact serializes must carry it (the frontend keys on it)."""
        check = _band_cross_check(historical_ev_ebitda_break_caveat=_BREAK_CAVEAT)[0]
        assert check.model_dump()["band_break_caveat"] == _BREAK_CAVEAT


class TestReportPathForwardsTheBreakCaveat:
    """The report's own-history row is built through ``_helpers.build_valuation_synthesis``
    (equity_research → the band spread), so the caveat has to survive that seam."""

    def _financials(self):
        from datetime import datetime, timezone

        from finrobot.engine.models.financial import (
            BalanceSheet,
            FinancialData,
            IncomeStatement,
            MarketData,
            ValuationMetrics,
        )

        return FinancialData(
            ticker="EHC",
            timestamp=datetime(2026, 10, 13, tzinfo=timezone.utc),
            income=IncomeStatement(revenue=6.2e9, ebitda=_EHC["ttm_ebitda"]),
            balance=BalanceSheet(total_debt=2_842_299_904.0, total_cash=107_700_000.0),
            market=MarketData(
                market_cap=12.27e9,
                shares_outstanding=_EHC["shares"],
                current_price=124.42,
            ),
            # Non-None EV is the extractor's "both debt and cash were reported" gate;
            # without it the fallback chain leaves net debt None and the cross-check
            # would be dropped (see build_valuation_synthesis).
            valuation=ValuationMetrics(enterprise_value=1.0),
        )

    def test_row_carries_the_caveat_through_the_report_path(self):
        from finrobot.engine.pipelines._helpers import build_valuation_synthesis

        vs = build_valuation_synthesis(
            {"data_collection": self._financials()},
            124.42,
            ticker="EHC",
            historical_ev_ebitda_band=(_EHC["p25"], _EHC["p75"]),
            historical_ev_ebitda_sample_n=947,
            historical_ev_ebitda_median=_EHC["median"],
            historical_ev_ebitda_window_years=5,
            historical_ev_ebitda_break_caveat=_BREAK_CAVEAT,
        )
        assert vs is not None
        rows = [c for c in vs.cross_checks if c.name == "ev_ebitda_band"]
        assert len(rows) == 1
        assert rows[0].band_break_caveat == _BREAK_CAVEAT
        assert rows[0].basis.endswith(_BREAK_CAVEAT)

    def test_row_without_the_kwarg_stays_clean(self):
        from finrobot.engine.pipelines._helpers import build_valuation_synthesis

        vs = build_valuation_synthesis(
            {"data_collection": self._financials()},
            124.42,
            ticker="EHC",
            historical_ev_ebitda_band=(_EHC["p25"], _EHC["p75"]),
            historical_ev_ebitda_sample_n=947,
            historical_ev_ebitda_median=_EHC["median"],
            historical_ev_ebitda_window_years=5,
        )
        assert vs is not None
        rows = [c for c in vs.cross_checks if c.name == "ev_ebitda_band"]
        assert len(rows) == 1
        assert rows[0].band_break_caveat is None


class TestCrossCheckDropIsDisclosed:
    def test_missing_median_names_the_gap_instead_of_dropping_silently(self):
        """The row exists to put the target beside the issuer's own band — a
        missing input must be named, not silently skipped."""
        agg = aggregate_valuation(
            ticker="EHC",
            current_price=124.42,
            ttm_ebitda=_EHC["ttm_ebitda"],
            current_net_debt=_EHC["net_debt"],
            shares_outstanding=_EHC["shares"],
            historical_ev_ebitda_band=(_EHC["p25"], _EHC["p75"]),
            historical_ev_ebitda_median=None,
            historical_ev_ebitda_sample_n=947,
        )
        assert agg.cross_checks == []
        dropped = [w for w in agg.warnings if "ev_ebitda cross-check" in w]
        assert len(dropped) == 1
        assert "band median" in dropped[0]
        assert "no own-history multiple check" in dropped[0]

    def test_no_band_no_warning(self):
        """Without any band there is nothing to cross-check, so nothing is said."""
        agg = aggregate_valuation(
            ticker="EHC",
            current_price=124.42,
            ttm_ebitda=_EHC["ttm_ebitda"],
            current_net_debt=_EHC["net_debt"],
            shares_outstanding=_EHC["shares"],
        )
        assert agg.cross_checks == []
        assert not [w for w in agg.warnings if "ev_ebitda cross-check" in w]
