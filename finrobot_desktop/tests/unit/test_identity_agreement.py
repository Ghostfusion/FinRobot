"""Every consumer of one identity must return the SAME number — the CF regression.

The audited CF report (2026-10-15T00:50) published a $86.40 EV/EBITDA method mid beside
a $65.44 own-history cross-check, and a 4.9x price-implied multiple beside a 5.7x
"current" one, because the arithmetic was written out five times: ``_ev_ebitda_method``
bridged net debt only while ``ev_band_equity_per_share`` bridged net debt + preferred +
NCI. Nothing in the system could state that one of the two was wrong, because nothing
declared the identity — the docstring in ``dcf.equity_bridge_value`` claimed "single
authority" while a second copy sat in ``multiples`` and a third (without the claims) in
``sotp``.

These tests are the structural version of that claim: ONE declaration
(``engine/models/identities``), every producer routed through it, and an issuer carrying
preferred AND noncontrolling interest so a bridged-vs-unbridged disagreement cannot
cancel out.
"""

from __future__ import annotations

import datetime as dt

import pytest

from finrobot.engine.compute.operators import sotp
from finrobot.engine.compute.operators.dcf import equity_bridge_value
from finrobot.engine.compute.operators.multiples import (
    calculate_ev,
    current_ev_ebitda,
    ev_band_equity_per_share,
    implied_ev_multiple,
)
from finrobot.engine.models import identities
from finrobot.engine.models.financial import (
    BalanceSheet,
    DCFInputs,
    FinancialData,
    IncomeStatement,
    MarketData,
)
from finrobot.engine.models.identities import (
    Contributor,
    Identity,
    artifact_operands,
    evaluate,
    relative_residual,
)
from finrobot.engine.primitives.historical_valuation import (
    PricePoint,
    YearlyFinancials,
    compute_historical_band,
)

# An issuer with a claim ranking ahead of common AND a minority interest — the two
# components whose omission was invisible: the net-debt-only identity still closes to
# the dollar (EHC: $0.86B NCI, ~4% of per-share value).
MARKET_CAP = 1_000.0
SHARES = 50.0
PRICE = MARKET_CAP / SHARES
TOTAL_DEBT = 100.0
TOTAL_CASH = 40.0
NET_DEBT = TOTAL_DEBT - TOTAL_CASH
PREFERRED = 10.0
NCI = 20.0
EBITDA = 100.0
EV = MARKET_CAP + NET_DEBT + PREFERRED + NCI
EV_EBITDA = EV / EBITDA
AS_OF = dt.date(2025, 12, 31)


def _financial_data() -> FinancialData:
    return FinancialData(
        ticker="TEST",
        timestamp=dt.datetime(2026, 1, 2),
        market=MarketData(market_cap=MARKET_CAP, current_price=PRICE, shares_outstanding=SHARES),
        income=IncomeStatement(revenue=500.0, ebitda=EBITDA),
        balance=BalanceSheet(
            total_debt=TOTAL_DEBT,
            total_cash=TOTAL_CASH,
            preferred_stock=PREFERRED,
            noncontrolling_interest=NCI,
        ),
    )


def _dcf_inputs() -> DCFInputs:
    return DCFInputs(
        revenue_base=500.0,
        revenue_growth_rates=[0.05],
        ebitda_margin=0.2,
        capex_pct_revenue=0.05,
        nwc_pct_revenue=0.02,
        risk_free_rate=0.04,
        beta=1.0,
        equity_risk_premium=0.05,
        cost_of_debt=0.05,
        debt_ratio=0.3,
        terminal_growth_rate=0.02,
        net_debt=NET_DEBT,
        preferred_stock=PREFERRED,
        noncontrolling_interest=NCI,
        shares_outstanding=SHARES,
    )


def _snapshot() -> dict[str, object]:
    """The artifact's own leaves for the same issuer, as the gate reads them."""
    return {
        "market": {"market_cap": MARKET_CAP, "current_price": PRICE, "shares_outstanding": SHARES},
        "income": {"revenue": 500.0, "ebitda": EBITDA, "net_income": 40.0},
        "balance": {
            "total_debt": TOTAL_DEBT,
            "total_cash": TOTAL_CASH,
            "preferred_stock": PREFERRED,
            "noncontrolling_interest": NCI,
        },
        "valuation": {
            "enterprise_value": EV,
            "ebitda_operating": EBITDA,
            "ev_ebitda": EV_EBITDA,
        },
    }


def test_ev_build_agrees_across_its_consumers() -> None:
    """``calculate_ev`` and the artifact reader are the same number."""
    assert calculate_ev(MARKET_CAP, TOTAL_DEBT, TOTAL_CASH, PREFERRED, NCI) == EV
    resolved = artifact_operands("ev_build", _snapshot())
    assert resolved is not None
    operands, published = resolved
    assert published == EV
    assert evaluate("ev_build", operands) == EV


def test_equity_bridge_agrees_across_its_consumers() -> None:
    """The DCF bridge, the band row and the SOTP floor all dock the same claims.

    Before the registry, the SOTP floor subtracted net debt ONLY — an option-premium
    name carrying preferred or NCI published an equity floor, a price floor and an
    implied option premium that ignored a claim senior to common.
    """
    equity_after_net_debt_and_claims = EV - NET_DEBT - PREFERRED - NCI
    assert equity_bridge_value(EV, _dcf_inputs()) == equity_after_net_debt_and_claims

    band_equity = ev_band_equity_per_share(
        multiple=10.0,
        ttm_ebitda=EBITDA,
        net_debt=NET_DEBT,
        preferred_stock=PREFERRED,
        noncontrolling_interest=NCI,
        shares_outstanding=SHARES,
    )
    assert band_equity == (10.0 * EBITDA - NET_DEBT - PREFERRED - NCI) / SHARES

    segment = sotp.value_segment(
        name="seg",
        metric_label="EV/EBITDA",
        metric_value=EBITDA,
        multiple=10.0,
        multiple_source="test",
    )
    breakdown = sotp.compute_sotp_breakdown(
        ticker="TEST",
        modelable_segments=[segment],
        net_debt=NET_DEBT,
        shares_outstanding=SHARES,
        current_price=PRICE,
        preferred_stock=PREFERRED,
        noncontrolling_interest=NCI,
    )
    floor = 10.0 * EBITDA - NET_DEBT - PREFERRED - NCI
    assert breakdown.equity_floor == floor
    assert breakdown.price_floor == floor / SHARES
    # The market residual is the same bridge read backwards.
    assert breakdown.implied_option_ev == PRICE * SHARES - floor


def test_ev_ebitda_agrees_across_its_consumers() -> None:
    """The comps chapter, the band's current point and the band's own samples."""
    assert current_ev_ebitda(_financial_data(), NET_DEBT) == EV_EBITDA

    band = compute_historical_band(
        metric="ev_ebitda",
        yearly=[
            YearlyFinancials(
                fiscal_date=AS_OF, ebitda=EBITDA, free_cash_flow=None, net_debt=NET_DEBT
            )
        ],
        prices=[PricePoint(sample_date=AS_OF, close=PRICE)],
        shares_outstanding=SHARES,
        preferred_stock=PREFERRED,
        noncontrolling_interest=NCI,
    )
    assert band.current == EV_EBITDA
    assert band.timeline == [(AS_OF, EV_EBITDA)]


def test_implied_multiple_inverts_the_band_bridge() -> None:
    """A round trip through the two directions of one identity returns the multiple."""
    multiple = 12.5
    per_share = ev_band_equity_per_share(
        multiple=multiple,
        ttm_ebitda=EBITDA,
        net_debt=NET_DEBT,
        preferred_stock=PREFERRED,
        noncontrolling_interest=NCI,
        shares_outstanding=SHARES,
    )
    assert per_share is not None
    assert implied_ev_multiple(
        price=per_share,
        shares_outstanding=SHARES,
        net_debt=NET_DEBT,
        preferred_stock=PREFERRED,
        noncontrolling_interest=NCI,
        ttm_ebitda=EBITDA,
    ) == pytest.approx(multiple)


def test_the_artifact_reader_derives_net_debt_from_the_balance_leaves() -> None:
    """The gate resolves ``net_debt`` the same way a caller does — no second formula."""
    resolved = artifact_operands("ev_ebitda", _snapshot())
    assert resolved is not None
    operands, published = resolved
    assert operands.get("net_debt") is None  # left to the identity, not hard-coded
    assert operands["total_debt"] == TOTAL_DEBT
    assert operands["total_cash"] == TOTAL_CASH
    assert evaluate("ev_ebitda", operands) == EV_EBITDA
    assert published == EV_EBITDA


def test_a_missing_balance_leg_is_not_a_zero() -> None:
    """None means "not reported": the identity cannot bind and is never checked."""
    snapshot = _snapshot()
    balance = snapshot["balance"]
    assert isinstance(balance, dict)
    del balance["total_debt"]
    resolved = artifact_operands("ev_ebitda", snapshot)
    assert resolved is not None
    operands, published = resolved
    assert relative_residual("ev_ebitda", operands, published) is None


def test_an_identity_total_cannot_be_read_as_a_component(monkeypatch: pytest.MonkeyPatch) -> None:
    """The role guard: a total of another identity is refused as an operand.

    This is the registry half of the XBRL defect that published noncontrolling interest
    of −$5,748,000,000: ``LiabilitiesAndStockholdersEquity`` IS the balance-sheet
    identity total (it equals Assets by definition), so reading it as a liabilities leaf
    made ``assets − liabilities = 0`` close and the wrong NCI pass every arithmetic
    check.
    """
    total_identity = Identity(
        id="_total_operand_fixture",
        total="liabilities_and_equity",
        kind="total_amount",
        form="sum",
        contributors=(Contributor("assets", 1.0),),
    )
    consumer = Identity(
        id="_test_reads_a_total",
        total="nci",
        kind="total_amount",
        form="sum",
        contributors=(Contributor("liabilities_and_equity", 1.0, role="total"),),
    )
    for spec in (total_identity, consumer):
        monkeypatch.setitem(identities._BY_ID, spec.id, spec)  # noqa: SLF001 - the guard's own registry
    with pytest.raises(ValueError, match="cannot be read as a component"):
        evaluate(consumer.id, {"liabilities_and_equity": 1.0})


def test_unknown_identity_is_not_silently_ignored() -> None:
    with pytest.raises(KeyError):
        identities.identity("no_such_identity")
