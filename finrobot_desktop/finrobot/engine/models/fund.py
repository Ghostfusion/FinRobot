"""Fund (ETF / mutual fund / closed-end fund) engine models.

Two objects, split along the same compute boundary the rest of the engine uses:

* :class:`FundData` — the INPUT snapshot: the canonical fund profile plus the
  NAV / price series and its provenance. Pure data, no derived metrics.
* :class:`FundAssessment` — the OUTPUT of the deterministic compute layer
  (``engine.compute.coordinators.fund_profile`` + the ``fund_metrics``
  operators). Every number here is computed by code from ``FundData``; the LLM
  only narrates it.

A fund files no income statement, so none of the equity models
(``FinancialData`` / ``DCFResult`` / ``DDMResult`` …) apply to it. See
``engine.data.instrument`` for the classification that routes a symbol to the
fund pipeline instead of the equity pipelines.

Unit convention (mirrors ``NormalizedFundProfile``): every ratio / return /
yield / spread is a FRACTION — ``0.0015`` = 15 bp of expense, ``0.0382`` = 3.82%
yield, ``0.0004`` = a +0.04% premium to NAV. There is deliberately NO
percent-number field in this payload: the first draft carried a
``premium_discount_pct`` holding ``0.0393`` (i.e. percent) beside a
``nav_change_up_100bp_pct`` holding ``-0.0354`` (i.e. a fraction), two ``_pct``
fields with opposite units — and the fund chapter's fraction formatter duly
rendered the premium as 3.93% instead of 0.04%. One unit, no suffix traps.
"""

from __future__ import annotations

import math
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class FundHolding(BaseModel):
    """One reported portfolio position (fraction of net assets, not notional)."""

    model_config = ConfigDict(frozen=False)

    symbol: str | None = None
    name: str | None = None
    weight: float | None = Field(
        default=None, description="Fraction of net assets (0.0431 = 4.31%)"
    )


class FundProvenance(BaseModel):
    """Source + freshness + degradation flags for a fund snapshot's numbers.

    Mirrors the canonical ``Provenance`` contract so the coordinator can project
    one onto the other; kept local because ``engine/models/`` is a self-contained
    leaf layer (it imports nothing from ``engine/``).
    """

    model_config = ConfigDict(frozen=False)

    provider: str
    as_of: datetime = Field(description="Semantic time (= latest NAV date when known)")
    fetched_at: datetime = Field(description="Wall-clock time the upstream fetch completed")
    degraded: list[str] = Field(default_factory=list)


class FundData(BaseModel):
    """Input snapshot for the fund pipeline: profile + NAV series + provenance."""

    model_config = ConfigDict(frozen=False)

    ticker: str
    instrument: str = "fund"
    # ── identity ──────────────────────────────────────────────────────────
    name: str | None = None
    fund_family: str | None = None
    legal_type: str | None = None  # vendor legal form ("Exchange Traded Fund")
    category: str | None = None  # vendor style/category ("Large Blend")
    quote_type: str | None = None  # the provider's raw classification
    inception_date: date | None = None
    currency: str = "USD"
    as_of: datetime = Field(description="Semantic time (= latest NAV date when known)")
    # ── size + pricing ────────────────────────────────────────────────────
    total_net_assets: float | None = None  # USD
    nav_per_share: float | None = None
    market_price: float | None = None  # None when the fund is NAV-priced only
    shares_outstanding: float | None = None
    # ── cost ──────────────────────────────────────────────────────────────
    net_expense_ratio: float | None = None  # fraction of net assets / year
    gross_expense_ratio: float | None = None
    category_avg_expense_ratio: float | None = None  # peer cost benchmark, fraction
    turnover: float | None = None  # annual holdings turnover, fraction
    # ── income + performance ──────────────────────────────────────────────
    distribution_yield: float | None = None
    ytd_return: float | None = None
    return_3m: float | None = None
    return_1y: float | None = None
    return_3y_annual: float | None = None
    return_5y_annual: float | None = None
    beta_3y: float | None = None
    # ── allocation ────────────────────────────────────────────────────────
    asset_classes: dict[str, float] = Field(default_factory=dict)
    sector_weights: dict[str, float] = Field(default_factory=dict)
    region_weights: dict[str, float] = Field(default_factory=dict)
    bond_ratings: dict[str, float] = Field(default_factory=dict)
    bond_duration: float | None = Field(default=None, description="Years")
    bond_maturity: float | None = Field(default=None, description="Years")
    equity_pe: float | None = None
    top_holdings: list[FundHolding] = Field(default_factory=list)
    # The fund's FULL portfolio from its own SEC N-PORT filing, when available
    # (DataType.FUND_HOLDINGS). Empty when SEC could not serve it — then
    # ``top_holdings`` (the vendor excerpt) is the panel. ``portfolio_source`` /
    # ``portfolio_as_of`` name which source the concentration panel came from and
    # its as-of date (a fund's N-PORT is quarterly, so the date matters).
    portfolio_holdings: list[FundHolding] = Field(default_factory=list)
    portfolio_source: str | None = None
    portfolio_as_of: date | None = None
    # ── NAV / price series (oldest → newest) ──────────────────────────────
    nav_dates: list[date] = Field(default_factory=list)
    nav_closes: list[float] = Field(default_factory=list)

    provenance: FundProvenance
    warnings: list[str] = Field(default_factory=list)

    def allocation_total(self) -> float | None:
        """Sum of the reported asset-class weights, or ``None`` when unreported.

        A fund's asset mix must reconcile (the weights are shares of one
        portfolio), so a sum materially off 1.0 means the provider published a
        partial breakdown. Callers surface that as a warning rather than
        renormalizing — renormalizing would invent the missing slice.
        """
        if not self.asset_classes:
            return None
        return math.fsum(self.asset_classes.values())


class FundAssessment(BaseModel):
    """Deterministic fund metrics computed from :class:`FundData`.

    ``returns`` carries the NAV-series CAGRs alongside the provider's
    year-to-date and 3-month figures; ``cost_drag`` is the output of
    ``expense_cost_analysis``; ``concentration`` is the output of
    ``portfolio_concentration``; ``duration_sensitivity`` is ``None`` for a fund
    with no reported bond duration. Every field is ``None`` / an empty mapping
    when its inputs were missing — never a fabricated ``0``.
    """

    model_config = ConfigDict(frozen=False)

    ticker: str
    risk_free_rate: float = 0.0
    returns: dict[str, float | None] = Field(default_factory=dict)
    volatility: float | None = None
    max_drawdown: float | None = None
    sharpe: float | None = None
    premium_discount: float | None = Field(
        default=None,
        description="Market price vs NAV as a FRACTION (0.0004 = +0.04% premium)",
    )
    cost_drag: dict[str, float | None] = Field(default_factory=dict)
    concentration: dict[str, float | None] = Field(default_factory=dict)
    # Provenance of the portfolio behind ``concentration``: which source the
    # panel came from (``sec_nport`` for the fund's own filing, else the vendor id)
    # and its as-of date. A reader must see the N-PORT date (it is quarterly).
    portfolio_source: str | None = None
    portfolio_as_of: date | None = None
    portfolio_holding_count: int | None = None
    duration_sensitivity: dict[str, float | None] | None = None
    warnings: list[str] = Field(default_factory=list)
