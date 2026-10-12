"""Merton structural credit risk — distance to default from the equity view.

What this code does that a raw model cannot: it inverts the Merton (1974) identity
``E = V·Φ(d₁) − D·e^{−rT}·Φ(d₂)`` — equity as a call on the firm's assets — for the
two quantities no market quotes directly, the asset value ``V`` and the asset
volatility ``σ_V``, and reports the distance to default (DD) and the model-implied
default probability ``Φ(−DD)`` that follow from them.

The joint solve is the KMV iteration (Crosbie & Bohn 2003; Vassalou & Xing 2004):
seed ``σ_V`` from the equity volatility scaled by leverage, invert the pricing
identity for ``V`` at that ``σ_V``, update ``σ_V`` with Itô's
``σ_E·E = σ_V·V·Φ(d₁)``, and repeat to a fixed point. Deterministic and RNG-free —
the only numerical choice is the root finder's bracket.

**What the model cannot see, and the caller must therefore state.**

- The default barrier ``D`` is a modelling choice, not a reported number. KMV's
  convention is ``short_term_debt + ½·long_term_debt``, which needs a provider that
  splits the balance sheet; where only a total is available the *total* becomes the
  barrier and the resulting DD is conservative (defaults sooner). Which basis was
  used is a caller-supplied string here, never assumed.
- Default can only occur at ``T`` (the equity's call is European — early exercise,
  i.e. a covenant breach, is outside the model), the asset value is assumed
  lognormal with constant volatility, and ``σ_E`` is a *trailing realized* estimate
  rather than an option-implied one.
- For a deposit-funded balance sheet (bank / insurer) the barrier logic is a
  category error — deposits are operating raw material, not capital structure.
  Withholding the measure is the caller's decision, not this module's.

Source: ``strategies/quants.md`` §Credit and Counterparty Risk (the Merton identity,
``PD(0,t) = 1 − S(t)``, the DD formula). ``strategies/qfin-pr/credit-counterparty-
risk.md`` is the deferred corpus review; this proxy is its one buildable arm.
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Sequence
from dataclasses import dataclass

from finrobot.engine.backtest.validation.stats import norm_cdf

PERIODS_PER_YEAR: int = 252
"""Trading sessions per year, for annualizing a daily volatility. The report's ONE
annualization constant — ``compute/operators/sniper.py`` derives its sniper volume
from the same 252 so the two chapters cannot disagree on a volatility."""

MIN_VOLATILITY_BARS: int = 60
"""Fewest daily closes a volatility estimate may be built from (≈ three months).
Below this the sample stdev is not an annual risk estimate, so the caller is told
``None`` instead of a number that would silently drive DD."""

MAX_ITERATIONS: int = 100
"""KMV fixed-point cap. The iteration converges in ≤ 10 steps on real inputs; the
cap exists so a pathological barrier cannot spin, and ``converged`` reports it."""

VOLATILITY_TOLERANCE: float = 1e-10
"""Relative ``σ_V`` change below which the fixed point is reached."""

_BISECTION_STEPS: int = 200
"""Halvings for the ``V`` root find. 200 steps is exact to double precision."""


@dataclass(frozen=True)
class MertonInputs:
    """The equity-view inputs the model consumes — all annualized, all in one
    currency (the caller passes the market value of equity and the book barrier)."""

    equity_value: float
    """``E`` — market capitalization (quote currency, same unit as the barrier)."""
    equity_volatility: float
    """``σ_E`` — annualized volatility of the equity's daily returns."""
    debt_barrier: float
    """``D`` — the default barrier (see the module docstring on the basis)."""
    risk_free_rate: float
    """``r`` — continuously-compounded annual risk-free rate."""
    horizon_years: float = 1.0
    """``T`` — the horizon over which default may occur (1 year by convention)."""


@dataclass(frozen=True)
class MertonResult:
    """The solved system. Every field is derived, none is an input echo."""

    asset_value: float
    """``V`` — the fitted market value of the firm's assets."""
    asset_volatility: float
    """``σ_V`` — the fitted annualized asset volatility."""
    distance_to_default: float
    """``DD`` — standard deviations of asset value between ``V`` and the barrier at
    ``T``. Higher is safer; it is a continuous score, not an ordinal rating."""
    default_probability: float
    """``Φ(−DD)`` — risk-neutral one-horizon default probability."""
    debt_to_value: float
    """``D / (D + E)`` market leverage against the barrier (not book leverage)."""
    implied_credit_spread: float | None
    """The model's own risky-debt yield minus ``r``, annualized. None when the
    debt leg is not a discount-priced claim (barrier ≤ 0, horizon ≤ 0)."""
    iterations: int
    """Fixed-point iterations actually run."""
    converged: bool
    """False when ``MAX_ITERATIONS`` was hit with ``σ_V`` still moving — the result
    is then reported, never silently kept."""


def annualized_equity_volatility(closes: Sequence[float]) -> float | None:
    """Annualized standard deviation of daily simple returns.

    Deliberately the same series, same estimator and same constant as the report's
    technical chapter (``sniper.py``: sample stdev of simple returns × √252) so one
    issuer never shows two different volatilities. ``None`` when the series is too
    short (``MIN_VOLATILITY_BARS``), when no usable return can be formed, or when
    the estimate is degenerate (zero dispersion).
    """
    if len(closes) < MIN_VOLATILITY_BARS:
        return None
    returns = [
        (closes[i] - closes[i - 1]) / closes[i - 1]
        for i in range(1, len(closes))
        if closes[i - 1] > 0.0
    ]
    if len(returns) < MIN_VOLATILITY_BARS - 1:
        return None
    daily = statistics.stdev(returns)
    if daily <= 0.0:
        return None
    return daily * math.sqrt(PERIODS_PER_YEAR)


def _d1(asset_value: float, debt: float, rate: float, vol: float, horizon: float) -> float:
    return (math.log(asset_value / debt) + (rate + 0.5 * vol * vol) * horizon) / (
        vol * math.sqrt(horizon)
    )


def _equity_value(
    asset_value: float, debt: float, rate: float, vol: float, horizon: float
) -> float:
    """The Merton pricing identity: equity at ``asset_value``. Strictly increasing
    in ``asset_value``, which is what makes the bisection below valid."""
    d1 = _d1(asset_value, debt, rate, vol, horizon)
    d2 = d1 - vol * math.sqrt(horizon)
    return asset_value * norm_cdf(d1) - debt * math.exp(-rate * horizon) * norm_cdf(d2)


def _solve_asset_value(
    equity_value: float, debt: float, rate: float, vol: float, horizon: float
) -> float:
    """Invert ``E = V·Φ(d₁) − D·e^{−rT}·Φ(d₂)`` for ``V`` by bisection.

    Bracketed from ``V = E`` (where the identity under-predicts equity, since the
    debt leg is a positive subtraction) upward: doubling until the identity
    over-predicts, then halving. ``V ≥ E`` always holds for a positive barrier, so
    the search never needs a lower bracket.
    """
    target = equity_value
    low = equity_value
    high = equity_value
    for _ in range(64):
        if _equity_value(high, debt, rate, vol, horizon) >= target:
            break
        high *= 2.0
    else:  # pragma: no cover — the identity is unbounded in V, so this is unreachable
        raise ValueError(
            f"no asset-value bracket for equity={equity_value!r} debt={debt!r} vol={vol!r}"
        )
    mid = low
    for _ in range(_BISECTION_STEPS):
        mid = 0.5 * (low + high)
        if _equity_value(mid, debt, rate, vol, horizon) < target:
            low = mid
        else:
            high = mid
    return 0.5 * (low + high)


def solve_merton(inputs: MertonInputs) -> MertonResult:
    """Solve the Merton/KMV system for ``DD`` and the implied default probability.

    Raises ``ValueError`` on inputs the model is undefined for — non-positive
    equity value, barrier, equity volatility or horizon. That is a caller-visible
    contract: the pipeline decides between 'not applicable' (a deposit-funded
    balance sheet), 'no debt' (no barrier to breach) and 'not computable' (missing
    input); it is never a silent zero.

    A non-converged fixed point is returned with ``converged=False`` rather than
    raised: the numbers are still the model's answer, and the caller reports them
    with the caveat attached.
    """
    equity = float(inputs.equity_value)
    debt = float(inputs.debt_barrier)
    equity_vol = float(inputs.equity_volatility)
    rate = float(inputs.risk_free_rate)
    horizon = float(inputs.horizon_years)
    if equity <= 0.0:
        raise ValueError(f"equity value must be positive, got {equity!r}")
    if debt <= 0.0:
        raise ValueError(f"debt barrier must be positive, got {debt!r}")
    if equity_vol <= 0.0:
        raise ValueError(f"equity volatility must be positive, got {equity_vol!r}")
    if horizon <= 0.0:
        raise ValueError(f"horizon must be positive, got {horizon!r}")

    # Seed: leverage-scaled equity volatility (σ_V ≈ σ_E·E/(E + D) at V ≈ E + D).
    vol = equity_vol * equity / (equity + debt)
    asset_value = _solve_asset_value(equity, debt, rate, vol, horizon)
    converged = False
    iterations = 0
    for iterations in range(1, MAX_ITERATIONS + 1):
        asset_value = _solve_asset_value(equity, debt, rate, vol, horizon)
        phi_d1 = norm_cdf(_d1(asset_value, debt, rate, vol, horizon))
        if phi_d1 <= 0.0:  # pragma: no cover — Φ(d₁) ∈ (0,1) for positive inputs
            raise ValueError(f"degenerate Φ(d₁)={phi_d1!r} at V={asset_value!r}")
        updated = equity_vol * equity / (asset_value * phi_d1)
        if abs(updated - vol) <= VOLATILITY_TOLERANCE * max(vol, 1e-12):
            vol = updated
            converged = True
            break
        vol = updated
    # The last published V must belong to the last published σ_V.
    asset_value = _solve_asset_value(equity, debt, rate, vol, horizon)

    root_t = vol * math.sqrt(horizon)
    distance_to_default = (
        math.log(asset_value / debt) + (rate - 0.5 * vol * vol) * horizon
    ) / root_t
    default_probability = norm_cdf(-distance_to_default)

    # The model prices the debt leg too: a risky zero-coupon claim on V is worth
    # V·Φ(−d₁) + D·e^{−rT}·Φ(d₂) today, so its yield over r IS the credit spread —
    # the number a bond market would quote, had this app a bond feed.
    d1 = _d1(asset_value, debt, rate, vol, horizon)
    d2 = d1 - root_t
    risky_debt_value = asset_value * norm_cdf(-d1) + debt * math.exp(-rate * horizon) * norm_cdf(d2)
    implied_credit_spread: float | None = None
    if 0.0 < risky_debt_value < debt:
        implied_credit_spread = -math.log(risky_debt_value / debt) / horizon - rate

    return MertonResult(
        asset_value=asset_value,
        asset_volatility=vol,
        distance_to_default=distance_to_default,
        default_probability=default_probability,
        debt_to_value=debt / (debt + equity),
        implied_credit_spread=implied_credit_spread,
        iterations=iterations,
        converged=converged,
    )
