"""Unit tests for finrobot.engine.compute.operators.credit_risk.

External sources for the expectations:
- The Merton identity ``E = V·Φ(d₁) − D·e^{−rT}·Φ(d₂)``, the distance to default
  ``DD = [ln(V/D) + (r − σ_V²/2)T] / (σ_V√T)`` and the risky-debt value
  ``V·Φ(−d₁) + D·e^{−rT}·Φ(d₂)`` are the standard definitions (Merton 1974;
  Crosbie & Bohn 2003 for the KMV formulation used here).
- The annualization constant 252 and the simple-return sample stdev mirror
  ``compute/operators/sniper.py`` so one issuer shows one volatility.

Every expected value below is derived from those definitions by hand (arithmetic
shown inline); none is taken from the function under test. The round-trip test is
the exception by construction — it starts from a *chosen* ``(V, σ_V)``, builds the
``(E, σ_E)`` the market would show, and asserts the solver walks back.
"""

from __future__ import annotations

import math
import statistics

import pytest

from finrobot.engine.backtest.validation.stats import norm_cdf
from finrobot.engine.compute.operators.credit_risk import (
    MIN_VOLATILITY_BARS,
    PERIODS_PER_YEAR,
    MertonInputs,
    annualized_equity_volatility,
    solve_merton,
)

# A textbook-firm fixture: V=100, D=70, r=5%, σ_V=20%, T=1.
#   d₁ = [ln(100/70) + (0.05 + 0.20²/2)] / 0.20 = (0.3566749 + 0.07)/0.20 = 2.1333747
#   d₂ = d₁ − 0.20 = 1.9333747
#   E  = 100·Φ(d₁) − 70·e^{−0.05}·Φ(d₂)
#   σ_E = σ_V·V·Φ(d₁)/E   (Itô: σ_E·E = σ_V·V·Φ(d₁))
_ASSET_VALUE = 100.0
_ASSET_VOL = 0.20
_BARRIER = 70.0
_RATE = 0.05
_HORIZON = 1.0
_D1 = (math.log(_ASSET_VALUE / _BARRIER) + (_RATE + 0.5 * _ASSET_VOL**2)) / _ASSET_VOL
_D2 = _D1 - _ASSET_VOL
_EQUITY_VALUE = _ASSET_VALUE * norm_cdf(_D1) - _BARRIER * math.exp(-_RATE) * norm_cdf(_D2)
_EQUITY_VOL = _ASSET_VOL * _ASSET_VALUE * norm_cdf(_D1) / _EQUITY_VALUE
_ANALYTIC_DD = (math.log(_ASSET_VALUE / _BARRIER) + (_RATE - 0.5 * _ASSET_VOL**2)) / _ASSET_VOL


def _inputs(**overrides: float) -> MertonInputs:
    """The fixture firm in equity view, with per-test overrides."""
    params: dict[str, float] = dict(
        equity_value=_EQUITY_VALUE,
        equity_volatility=_EQUITY_VOL,
        debt_barrier=_BARRIER,
        risk_free_rate=_RATE,
        horizon_years=_HORIZON,
    )
    params.update(overrides)
    return MertonInputs(**params)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# The inverse problem: does the solver recover the firm it was built from?
# ---------------------------------------------------------------------------


def test_recovers_the_asset_value_and_volatility_it_was_built_from() -> None:
    result = solve_merton(_inputs())

    assert result.asset_value == pytest.approx(_ASSET_VALUE, rel=1e-6)
    assert result.asset_volatility == pytest.approx(_ASSET_VOL, rel=1e-6)
    assert result.converged is True
    # The fixed point is reached in a handful of steps; the cap is not approached.
    assert 1 <= result.iterations <= 10


def test_distance_to_default_is_the_closed_form_of_the_recovered_pair() -> None:
    result = solve_merton(_inputs())
    recomputed = (
        math.log(result.asset_value / _BARRIER)
        + (_RATE - 0.5 * result.asset_volatility**2) * _HORIZON
    ) / (result.asset_volatility * math.sqrt(_HORIZON))

    assert result.distance_to_default == pytest.approx(recomputed, rel=1e-12)
    # …and it is the analytic DD of the fixture, so the recovered pair is the true
    # pair and not merely a self-consistent one.
    assert result.distance_to_default == pytest.approx(_ANALYTIC_DD, rel=1e-5)
    assert result.default_probability == pytest.approx(norm_cdf(-_ANALYTIC_DD), abs=1e-6)


def test_default_probability_is_always_the_cdf_of_negative_distance() -> None:
    for barrier in (10.0, 50.0, 150.0):
        result = solve_merton(_inputs(debt_barrier=barrier))

        assert result.default_probability == pytest.approx(
            norm_cdf(-result.distance_to_default), abs=1e-15
        )
        assert 0.0 < result.default_probability < 1.0


# ---------------------------------------------------------------------------
# Directional properties an analyst reads off the card
# ---------------------------------------------------------------------------


def test_more_leverage_lowers_distance_to_default_and_raises_default_risk() -> None:
    light = solve_merton(_inputs(debt_barrier=50.0))
    heavy = solve_merton(_inputs(debt_barrier=90.0))

    assert heavy.distance_to_default < light.distance_to_default
    assert heavy.default_probability > light.default_probability
    assert heavy.debt_to_value > light.debt_to_value


def test_higher_equity_volatility_lowers_distance_to_default() -> None:
    calm = solve_merton(_inputs(equity_volatility=0.15))
    violent = solve_merton(_inputs(equity_volatility=0.60))

    assert violent.distance_to_default < calm.distance_to_default
    assert violent.default_probability > calm.default_probability
    # The asset volatility moves with it — a halved DD with an unchanged σ_V would
    # mean the leverage channel alone was answering.
    assert violent.asset_volatility > calm.asset_volatility


def test_debt_to_value_is_market_leverage_against_the_barrier() -> None:
    result = solve_merton(_inputs())

    assert result.debt_to_value == pytest.approx(_BARRIER / (_BARRIER + _EQUITY_VALUE))
    assert 0.0 < result.debt_to_value < 1.0


def test_implied_credit_spread_is_positive_and_rises_with_leverage() -> None:
    light = solve_merton(_inputs(debt_barrier=20.0))
    heavy = solve_merton(_inputs(debt_barrier=95.0))

    assert light.implied_credit_spread is not None
    assert heavy.implied_credit_spread is not None
    assert 0.0 < light.implied_credit_spread < heavy.implied_credit_spread


def test_vanishing_risk_at_the_limit() -> None:
    """A near-riskless firm: negligible equity vol against a covered barrier."""
    result = solve_merton(_inputs(equity_volatility=0.001))

    assert result.distance_to_default > 10.0
    assert result.default_probability < 1e-20
    assert result.implied_credit_spread is not None
    assert abs(result.implied_credit_spread) < 1e-3


def test_is_deterministic() -> None:
    assert solve_merton(_inputs()) == solve_merton(_inputs())


# ---------------------------------------------------------------------------
# The caller-visible contract: undefined inputs raise, they never return a zero
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("field", "value", "expected_message"),
    [
        ("equity_value", 0.0, "equity value must be positive"),
        ("equity_value", -1.0, "equity value must be positive"),
        ("debt_barrier", 0.0, "debt barrier must be positive"),
        ("debt_barrier", -5.0, "debt barrier must be positive"),
        ("equity_volatility", 0.0, "equity volatility must be positive"),
        ("equity_volatility", -0.2, "equity volatility must be positive"),
        ("horizon_years", 0.0, "horizon must be positive"),
    ],
)
def test_undefined_inputs_raise_value_error(
    field: str, value: float, expected_message: str
) -> None:
    with pytest.raises(ValueError, match=expected_message):
        solve_merton(_inputs(**{field: value}))


def test_a_negative_risk_free_rate_is_accepted() -> None:
    """Real rates have been negative; the model is defined, so it must not raise."""
    result = solve_merton(_inputs(risk_free_rate=-0.01))

    assert result.distance_to_default > 0.0
    assert 0.0 < result.default_probability < 1.0


# ---------------------------------------------------------------------------
# The volatility input the report shares with the technical chapter
# ---------------------------------------------------------------------------


def _alternating_closes(bars: int, step: float) -> list[float]:
    """Closes whose simple returns alternate +step, −step exactly."""
    closes = [100.0]
    for i in range(bars - 1):
        sign = 1.0 if i % 2 == 0 else -1.0
        closes.append(closes[-1] * (1.0 + sign * step))
    return closes


def test_annualized_volatility_matches_the_hand_computed_sample_stdev() -> None:
    step = 0.01
    closes = _alternating_closes(101, step)  # 100 returns, alternating +1% / −1%
    # mean 0 → sample variance = Σx²/(n−1) = n·step²/(n−1); n=100 → step·√(100/99)
    expected_daily = step * math.sqrt(100 / 99)
    expected = expected_daily * math.sqrt(PERIODS_PER_YEAR)

    assert annualized_equity_volatility(closes) == pytest.approx(expected, rel=1e-12)
    assert annualized_equity_volatility(closes) == pytest.approx(
        statistics.stdev(
            [(closes[i] - closes[i - 1]) / closes[i - 1] for i in range(1, len(closes))]
        )
        * math.sqrt(PERIODS_PER_YEAR),
        rel=1e-12,
    )


def test_annualized_volatility_needs_enough_history() -> None:
    assert annualized_equity_volatility(_alternating_closes(MIN_VOLATILITY_BARS - 1, 0.01)) is None
    assert annualized_equity_volatility(_alternating_closes(MIN_VOLATILITY_BARS, 0.01)) is not None


def test_annualized_volatility_is_none_when_there_is_no_dispersion() -> None:
    """A flat series has zero sample stdev — an absent estimate, not a zero vol."""
    assert annualized_equity_volatility([100.0] * 80) is None


def test_annualized_volatility_skips_unusable_prior_closes() -> None:
    """A zero/negative close is bad data, not a −100% return."""
    closes = _alternating_closes(101, 0.01)
    closes[40] = 0.0

    estimate = annualized_equity_volatility(closes)

    assert estimate is not None
    assert estimate > 0.0
