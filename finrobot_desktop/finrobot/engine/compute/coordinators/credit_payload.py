"""Structural (Merton/KMV) credit risk — the payload chapter 11 renders.

The compute leaf lives in ``compute/operators/credit_risk.py`` (the joint solve for
asset value / asset volatility, then DD and the implied default probability). This
module is the deterministic glue around it: it decides which of four states the
issuer is in, fetches the two market inputs the leaf cannot (the trailing equity
volatility from the price history, the market value of equity from the frozen
financial snapshot), and packages one pydantic model the artifact builder persists
and the front end renders without further math.

**The four states are the honest part.** A reader must never be handed a default
probability that the data cannot support, and must never be told "not applicable"
when the real reason is a missing input:

``computed``       the model ran; all fields are populated.
``no_debt``        a genuinely debt-free balance sheet: the structural model has no
                   barrier to breach, so DD/PD are undefined *by construction*, not
                   missing. (``total_debt = 0``, which is a report, not an absence.)
``not_applicable`` a balance-sheet financial (bank / insurer). Deposits and float
                   are operating raw material there, so the barrier logic is a
                   category error — the same reason the pipeline withholds the
                   FCFF-DCF and the EV/EBITDA band for those issuers.
``not_computable`` an input is genuinely absent (debt unreported, no market cap, no
                   usable price history) — with the reason attached, never a zero.

Deterministic: no RNG, no LLM, no clock beyond the price window's own end date.
"""

from __future__ import annotations

import logging
from typing import Final, Literal

from pydantic import BaseModel, Field

from finrobot.engine.compute.operators.credit_risk import (
    MIN_VOLATILITY_BARS,
    MertonInputs,
    annualized_equity_volatility,
    solve_merton,
)
from finrobot.engine.data.historical_loaders import load_price_history
from finrobot.engine.data.layer import DataLayer
from finrobot.engine.primitives.industry import is_balance_sheet_financial

logger = logging.getLogger(__name__)

CREDIT_HORIZON_YEARS: Final[float] = 1.0
"""Horizon the default probability is quoted over. One year is the convention for a
distance-to-default reading (and the horizon the barrier is defined at)."""

CREDIT_VOLATILITY_YEARS: Final[int] = 1
"""Trailing window for the equity volatility — the same one-year series the
technical chapter's sniper levels are built from, so one issuer shows one vol."""

BARRIER_BASIS_TOTAL_DEBT: Final[str] = "total_debt"
"""The only basis this app can currently form: the provider reports a single debt
total, not the short/long split KMV's convention needs."""

NOT_APPLICABLE_WARNING: Final[str] = (
    "structural credit risk not applicable: this is a balance-sheet financial "
    "(bank / insurer), where deposits and float are operating raw material rather "
    "than capital structure — the Merton default barrier has no economic meaning "
    "for a deposit-funded balance sheet"
)
DEBT_NOT_REPORTED_WARNING: Final[str] = (
    "structural credit risk not computed: the provider reports no total debt for "
    "this issuer (None ≠ $0 — an unreported balance sheet cannot be treated as "
    "debt-free)"
)
NO_DEBT_WARNING: Final[str] = (
    "no debt on the balance sheet: the structural model has no barrier to breach, "
    "so distance to default and default probability are undefined for this issuer"
)
BARRIER_BASIS_WARNING: Final[str] = (
    "debt barrier = total debt: the KMV convention (short-term debt + ½·long-term "
    "debt) needs a provider that splits the balance sheet, so this distance to "
    "default is conservative — the barrier sits at least as high as KMV's"
)


def _short_history_warning(bars: int) -> str:
    return (
        f"structural credit risk not computed: {bars} daily closes are too few for an "
        f"annualized equity volatility (at least {MIN_VOLATILITY_BARS} are needed)"
    )


def _mixed_currency_warning(reporting_currency: str) -> str:
    return (
        "structural credit risk not computed: the balance sheet is in "
        f"{reporting_currency} while the equity leg is quoted in USD, and the pipeline's "
        "FX-normalization chokepoint (financial_modeling) did not run for this artifact — "
        "a barrier in one currency divided by equity in another produces a meaningless "
        "leverage ratio, so no distance to default is published"
    )


class CreditRisk(BaseModel):
    """Chapter 11 payload — one issuer's structural credit risk.

    ``state`` says what is being reported and every numeric field is optional so an
    uncomputed state is *empty* rather than zero-filled. The reader sees the state
    and the warnings; nothing is inferred from an absent field.
    """

    state: Literal["computed", "no_debt", "not_applicable", "not_computable"] = Field(
        description="Which of the four readings this issuer gets — see the module docstring."
    )
    method: str = Field(
        default="merton_kmv",
        description="Model identity: Merton (1974) solved by the KMV fixed-point iteration.",
    )
    horizon_years: float = Field(description="Horizon DD/PD are quoted over (years).")
    equity_value: float | None = Field(
        default=None, description="Market value of equity (market cap) in USD."
    )
    debt_barrier: float | None = Field(
        default=None, description="The default barrier D in USD (basis in barrier_basis)."
    )
    barrier_basis: str | None = Field(
        default=None, description="How D was formed; 'total_debt' today."
    )
    asset_value: float | None = Field(
        default=None, description="Fitted market value of the firm's assets V (USD)."
    )
    asset_volatility: float | None = Field(
        default=None, description="Fitted annualized asset volatility σ_V."
    )
    equity_volatility: float | None = Field(
        default=None, description="Input annualized equity volatility σ_E (trailing, realized)."
    )
    volatility_bars: int | None = Field(
        default=None, description="Daily closes the volatility was estimated from."
    )
    risk_free_rate: float | None = Field(
        default=None, description="Annual rate r used in the solve (continuously compounded)."
    )
    distance_to_default: float | None = Field(
        default=None, description="DD — standard deviations of asset value above the barrier."
    )
    default_probability: float | None = Field(
        default=None, description="Φ(−DD): model-implied probability of default over the horizon."
    )
    debt_to_value: float | None = Field(
        default=None, description="Market leverage D / (D + E) against the barrier."
    )
    implied_credit_spread: float | None = Field(
        default=None,
        description=(
            "The model's own risky-debt yield minus r, annualized — the spread a bond "
            "market would quote for this structure. None when the debt leg is not a "
            "discount-priced claim."
        ),
    )
    iterations: int | None = Field(default=None, description="KMV fixed-point iterations run.")
    converged: bool | None = Field(
        default=None, description="False when the iteration cap was hit (result still reported)."
    )
    warnings: list[str] = Field(
        default_factory=list, description="State reason or modelling caveat, reader-facing."
    )


def _empty(state: str, warnings: list[str], horizon_years: float) -> CreditRisk:
    """A state-carrying payload with no numbers — the never-zero-fill path."""
    return CreditRisk(
        state=state,  # type: ignore[arg-type]
        horizon_years=horizon_years,
        warnings=warnings,
    )


async def build_credit_risk(
    ticker: str,
    *,
    market_cap: float | None,
    total_debt: float | None,
    risk_free_rate: float | None,
    data_layer: DataLayer,
    industry: str | None = None,
    sector: str | None = None,
    horizon_years: float = CREDIT_HORIZON_YEARS,
    reporting_currency: str = "USD",
    usd_normalized: bool = True,
) -> CreditRisk:
    """Assemble the chapter-11 payload for one issuer.

    Args:
        market_cap: market value of equity in USD (``FinancialData.market``).
        total_debt: reported total debt in USD, or None when the provider does not
            report it (None ≠ 0 — see ``DEBT_NOT_REPORTED_WARNING``).
        risk_free_rate: the annual rate the solve discounts the barrier at. The
            caller resolves it (the DCF's own rate, or the pipeline's documented
            static fallback) so this module never invents one.
        data_layer: used only to load the trailing price history for σ_E.
        industry / sector: only to recognize a balance-sheet financial.
        reporting_currency: the balance sheet's own currency tag. Both legs of the
            model must be one currency, so a non-USD tag is only usable when the
            pipeline's FX chokepoint has already converted the line items.
        usd_normalized: whether that chokepoint ran for this artifact. Together
            with ``reporting_currency`` it is the guard against dividing a barrier
            in one currency by equity in another (BUG-073 caliber drift, which for
            this model shows up as a fake near-1.0 leverage ratio).
    """
    if is_balance_sheet_financial(industry=industry, sector=sector):
        return _empty("not_applicable", [NOT_APPLICABLE_WARNING], horizon_years)

    if not usd_normalized and reporting_currency.upper() != "USD":
        return _empty(
            "not_computable",
            [_mixed_currency_warning(reporting_currency.upper())],
            horizon_years,
        )

    if total_debt is None:
        return _empty(
            "not_computable",
            [DEBT_NOT_REPORTED_WARNING],
            horizon_years,
        )

    if total_debt <= 0.0:
        return CreditRisk(
            state="no_debt",
            horizon_years=horizon_years,
            equity_value=market_cap if (market_cap or 0.0) > 0.0 else None,
            debt_barrier=total_debt,
            barrier_basis=BARRIER_BASIS_TOTAL_DEBT,
            warnings=[NO_DEBT_WARNING],
        )

    if market_cap is None or market_cap <= 0.0:
        return _empty(
            "not_computable",
            [
                "structural credit risk not computed: no market capitalization to price the equity leg"
            ],
            horizon_years,
        )

    if risk_free_rate is None:
        return _empty(
            "not_computable",
            [
                "structural credit risk not computed: no risk-free rate available to discount the barrier"
            ],
            horizon_years,
        )

    prices = await load_price_history(ticker, data_layer, years=CREDIT_VOLATILITY_YEARS)
    closes = [point.close for point in prices]
    equity_vol = annualized_equity_volatility(closes)
    if equity_vol is None:
        return _empty("not_computable", [_short_history_warning(len(closes))], horizon_years)

    result = solve_merton(
        MertonInputs(
            equity_value=market_cap,
            equity_volatility=equity_vol,
            debt_barrier=total_debt,
            risk_free_rate=risk_free_rate,
            horizon_years=horizon_years,
        )
    )

    warnings = [BARRIER_BASIS_WARNING]
    if not result.converged:
        warnings.append(
            f"KMV fixed point did not converge in {result.iterations} iterations: the "
            "reported distance to default is the last iterate, not a fixed point"
        )

    return CreditRisk(
        state="computed",
        horizon_years=horizon_years,
        equity_value=market_cap,
        debt_barrier=total_debt,
        barrier_basis=BARRIER_BASIS_TOTAL_DEBT,
        asset_value=result.asset_value,
        asset_volatility=result.asset_volatility,
        equity_volatility=equity_vol,
        volatility_bars=len(closes),
        risk_free_rate=risk_free_rate,
        distance_to_default=result.distance_to_default,
        default_probability=result.default_probability,
        debt_to_value=result.debt_to_value,
        implied_credit_spread=result.implied_credit_spread,
        iterations=result.iterations,
        converged=result.converged,
        warnings=warnings,
    )
