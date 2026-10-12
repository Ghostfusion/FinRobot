"""Tiingo provider unit tests. All HTTP calls are mocked."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from finrobot.engine.data.providers.tiingo_provider import TiingoProvider
from finrobot.engine.data.types import DataType


def _period() -> dict:
    """One annual Tiingo statement period, shaped like /statements returns it."""
    return {
        "date": "2025-12-31",
        "quarter": 0,
        "statementData": {
            "incomeStatement": [
                {"dataCode": "revenue", "value": 4_000_000_000},
                # Tiingo declares this an incomeStatement code: "the portion of
                # income attributable to non-controlling interest shareholders".
                {"dataCode": "nonControllingInterests", "value": 12_000_000},
            ],
            "balanceSheet": [{"dataCode": "equity", "value": 5_000_000_000}],
            "cashFlow": [],
            "overview": [],
        },
    }


@pytest.mark.asyncio
async def test_income_statement_nci_code_is_not_served_as_the_balance_sheet_field():
    """``noncontrolling_interest`` is the balance-sheet CARRYING AMOUNT of the NCI
    claim that ``calculate_ev`` folds into EV; Tiingo's only NCI-shaped data code
    is the period's income FLOW to NCI. Mapping them put one year's NCI earnings
    into EV as if it were an equity claim, so the field must stay absent (None →
    the ev_bridge audit reports the EV as unverifiable). Tiingo carries no
    balance-sheet NCI or preferred code at all (its /fundamentals/definitions
    list, 85 codes, has ``equity`` as its only equity code)."""
    provider = TiingoProvider(api_key="test-key")
    response = MagicMock()
    response.json.return_value = [_period()]
    with patch.object(TiingoProvider, "_get", new=AsyncMock(return_value=response)):
        result = await provider.fetch("KO", DataType.FINANCIALS)
    # The mapping ran and served what it does own...
    assert result.data["revenue"] == 4_000_000_000
    assert result.data["fiscal_year"] == "2025-12-31"
    # ... but neither EV-bridge claim is taken from a mismatched caliber.
    assert "noncontrolling_interest" not in result.data
    assert "preferred_stock" not in result.data
