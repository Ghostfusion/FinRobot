"""Unit tests for the EODHD FUND_PROFILE arm (no network).

Pins the vendor's DOCUMENTED SWPPX sample
(``eodhd-claude-skills/skills/eodhd-api/references/general/fundamentals-fund.md``)
through ``_map_fund_payload`` — above all its UNIT conversions, because the
vendor mixes fractions and percent NUMBERS inside one payload and a wrong read
is a 100× error (``Expense_Ratio`` "0.0200" is 0.02%, i.e. the fraction
0.0002 — SWPPX's real net expense ratio).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from finrobot.engine.data.categories import Category
from finrobot.engine.data.interface import ProviderPlanError
from finrobot.engine.data.normalize.contracts import NormalizedFundProfile
from finrobot.engine.data.providers.eodhd_provider import (
    ENDPOINTS,
    EODHDProvider,
    _map_fund_payload,
)
from finrobot.engine.data.providers.moomoo_provider import MoomooProvider
from finrobot.engine.data.types import DataType

# ---------------------------------------------------------------------------
# The vendor's documented SWPPX (Schwab S&P 500 Index Fund) sample, verbatim.
# ---------------------------------------------------------------------------
_SWPPX: dict[str, object] = {
    "General": {
        "Code": "SWPPX",
        "Type": "FUND",
        "Name": "Schwab® S&P 500 Index Fund",
        "Exchange": "NMFQS",
        "CurrencyCode": "USD",
        "ISIN": "US8085098551",
        "Fund_Summary": "The fund generally invests at least 80% of its net assets ...",
        "Fund_Family": "Schwab Funds",
        "Fund_Category": None,
        "Fund_Style": None,
        "Fiscal_Year_End": "October",
        "MarketCapitalization": 0,
    },
    "MutualFund_Data": {
        "Nav": "92.59",
        "Prev_Close_Price": "92.26",
        "Update_Date": "2024-09-30",
        "Portfolio_Net_Assets": "72273490000",
        "Share_Class_Net_Assets": "0",
        "Inception_Date": "1997-05-19",
        "Currency": "USD",
        "Domicile": "United States",
        # fraction (1.18%)
        "Yield": "0.0118",
        # percent numbers (26.66%, 32.81%, 10.09%, 15.73%)
        "Yield_YTD": "26.6621",
        "Yield_1Year_YTD": "32.8114",
        "Yield_3Year_YTD": "10.0894",
        "Yield_5Year_YTD": "15.7262",
        # percent number (0.02%) — a fraction read would be 100× wrong
        "Expense_Ratio": "0.0200",
        "Expense_Ratio_Date": "2023-02-27",
        "Asset_Allocation": {
            "0": {
                "Net_%": "0.34539",
                "Long_%": "0.34539",
                "Type": "Cash",
                "Short_%": None,
                "Benchmark": "0.00000",
            },
            "1": {
                "Net_%": "0.0",
                "Long_%": "0.0",
                "Type": "Not Classified",
                "Short_%": None,
                "Benchmark": "0.0",
            },
        },
        "Value_Growth": {
            "0": {
                "Name": "Price/Prospective Earnings",
                "Benchmark": 21.21499,
                "Stock_Portfolio": 21.18843,
            },
            "1": {"Name": "Price/Book", "Benchmark": 4.24585, "Stock_Portfolio": 4.26978},
        },
        "Top_Holdings": {
            "0": {"Name": "Apple Inc", "Weight": "6.88%"},
            "1": {"Name": "Microsoft Corp", "Weight": "6.68%"},
        },
        "Sector_Weights": {
            "Cyclical": {
                "0": {"Name": "Basic Materials", "Amount_%": 1.93346, "Benchmark": 2.0688},
                "1": {
                    "Name": "Consumer Cyclical",
                    "Amount_%": 10.20911,
                    "Benchmark": 10.28619,
                },
            },
            "Defensive": {
                "0": {
                    "Name": "Consumer Defensive",
                    "Amount_%": 5.7586,
                    "Benchmark": 5.64783,
                },
                "1": {"Name": "Healthcare", "Amount_%": 11.17687, "Benchmark": 11.22479},
            },
            "Sensitive": {
                "0": {
                    "Name": "Communication Services",
                    "Amount_%": 9.10839,
                    "Benchmark": 9.12729,
                },
                "1": {"Name": "Energy", "Amount_%": 3.36916, "Benchmark": 3.44415},
            },
            "Bond Sector": {
                "0": {"Name": "Government", "Amount_%": 2.69783, "Stocks_%": 0, "Benchmark": None}
            },
        },
        "World_Regions": {
            "Americas": {
                "0": {"Name": "North America", "Stocks_%": 99.399, "Benchmark": 99.172},
                "1": {"Name": "Latin America", "Stocks_%": 0, "Benchmark": 0.226},
            },
            "Greater Europe": {
                "0": {"Name": "United Kingdom", "Stocks_%": 0.09689, "Benchmark": 0.11856},
                "1": {"Name": "Europe Developed", "Stocks_%": 0.46, "Benchmark": 0.443},
            },
        },
        # deprecated lowercase mirrors, always null
        "market_capitalization": None,
        "world_regions": None,
        "sector_weights": None,
        "asset_allocation": None,
    },
}


class TestUnitConversions:
    """Every ratio/return/yield/weight lands on the contract's FRACTION scale."""

    @staticmethod
    def _one(vendor_field: str, value: object, contract_field: str) -> object:
        """Map one vendor cell and read back its CONTRACT field."""
        return _map_fund_payload({"MutualFund_Data": {vendor_field: value}})[contract_field]

    def test_expense_ratio_percent_becomes_a_fraction(self):
        """``"0.0200"`` is 0.02% (SWPPX's real fee) → 0.0002, NOT 0.02."""
        raw = self._one("Expense_Ratio", "0.0200", "net_expense_ratio")
        assert raw == pytest.approx(0.0002, rel=1e-12)

    def test_expense_ratio_accepts_a_numeric_cell(self):
        raw = self._one("Expense_Ratio", 0.02, "net_expense_ratio")
        assert raw == pytest.approx(0.0002, rel=1e-12)

    def test_yield_is_already_a_fraction(self):
        """``"0.0118"`` is 1.18% → stored as-is (no ÷100)."""
        raw = self._one("Yield", "0.0118", "distribution_yield")
        assert raw == pytest.approx(0.0118, rel=1e-12)

    def test_return_series_are_percent_numbers(self):
        ytd = self._one("Yield_YTD", "26.6621", "ytd_return")
        one_year = self._one("Yield_1Year_YTD", "32.8114", "return_1y")
        three_year = self._one("Yield_3Year_YTD", "10.0894", "return_3y_annual")
        five_year = self._one("Yield_5Year_YTD", "15.7262", "return_5y_annual")
        assert ytd == pytest.approx(0.266621, rel=1e-9)
        assert one_year == pytest.approx(0.328114, rel=1e-9)
        assert three_year == pytest.approx(0.100894, rel=1e-9)
        assert five_year == pytest.approx(0.157262, rel=1e-9)

    def test_asset_allocation_net_percent_is_already_a_fraction(self):
        payload = {
            "MutualFund_Data": {"Asset_Allocation": {"0": {"Type": "Cash", "Net_%": "0.34539"}}}
        }
        assert _map_fund_payload(payload)["asset_classes"] == {"Cash": pytest.approx(0.34539)}

    def test_sector_and_region_weights_are_percent_numbers(self):
        payload = {
            "MutualFund_Data": {
                "Sector_Weights": {
                    "Cyclical": {"0": {"Name": "Basic Materials", "Amount_%": 1.93346}}
                },
                "World_Regions": {"Americas": {"0": {"Name": "North America", "Stocks_%": 99.399}}},
            }
        }
        mapped = _map_fund_payload(payload)
        assert mapped["sector_weights"] == {"Basic Materials": pytest.approx(0.0193346)}
        assert mapped["region_weights"] == {"North America": pytest.approx(0.99399)}

    def test_top_holding_weight_is_a_percent_string(self):
        payload = {
            "MutualFund_Data": {"Top_Holdings": {"0": {"Name": "Apple Inc", "Weight": "6.88%"}}}
        }
        assert _map_fund_payload(payload)["top_holdings"] == [
            {"symbol": None, "name": "Apple Inc", "weight": pytest.approx(0.0688)}
        ]

    def test_equity_pe_is_a_multiple_not_a_percent(self):
        payload = {
            "MutualFund_Data": {
                "Value_Growth": {
                    "0": {
                        "Name": "Price/Prospective Earnings",
                        "Benchmark": 21.21499,
                        "Stock_Portfolio": 21.18843,
                    }
                }
            }
        }
        assert _map_fund_payload(payload)["equity_pe"] == pytest.approx(21.18843)


class TestDocumentedSample:
    """The whole documented SWPPX payload maps field-by-field."""

    @pytest.fixture()
    def mapped(self) -> dict[str, object]:
        return _map_fund_payload(_SWPPX)

    def test_profile_fields(self, mapped):
        assert mapped["name"] == "Schwab® S&P 500 Index Fund"
        assert mapped["fund_family"] == "Schwab Funds"
        assert mapped["quote_type"] == "FUND"
        assert mapped["currency"] == "USD"
        assert mapped["inception_date"] == "1997-05-19"

    def test_levels(self, mapped):
        assert mapped["total_net_assets"] == pytest.approx(72_273_490_000.0)
        assert mapped["nav_per_share"] == pytest.approx(92.59)
        assert mapped["market_price"] == pytest.approx(92.26)

    def test_returns_and_fee(self, mapped):
        assert mapped["net_expense_ratio"] == pytest.approx(0.0002, rel=1e-12)
        assert mapped["distribution_yield"] == pytest.approx(0.0118, rel=1e-12)
        assert mapped["ytd_return"] == pytest.approx(0.266621, rel=1e-9)
        assert mapped["return_1y"] == pytest.approx(0.328114, rel=1e-9)
        assert mapped["return_3y_annual"] == pytest.approx(0.100894, rel=1e-9)
        assert mapped["return_5y_annual"] == pytest.approx(0.157262, rel=1e-9)

    def test_composition(self, mapped):
        assert mapped["asset_classes"] == {
            "Cash": pytest.approx(0.34539),
            "Not Classified": pytest.approx(0.0),
        }
        assert mapped["sector_weights"]["Healthcare"] == pytest.approx(0.1117687)
        assert mapped["sector_weights"]["Government"] == pytest.approx(0.0269783)
        assert mapped["region_weights"]["North America"] == pytest.approx(0.99399)
        assert mapped["equity_pe"] == pytest.approx(21.18843)
        assert [h["name"] for h in mapped["top_holdings"]] == ["Apple Inc", "Microsoft Corp"]
        assert mapped["top_holdings"][1]["weight"] == pytest.approx(0.0668)

    def test_every_emitted_key_is_a_contract_field(self, mapped):
        """The arm must not invent fields the contract lacks."""
        assert set(mapped) <= set(NormalizedFundProfile.model_fields)


class TestDegradation:
    """A thin/absent payload degrades to missing values, never raises."""

    def test_absent_sections(self):
        mapped = _map_fund_payload({})
        assert mapped["name"] is None
        assert mapped["total_net_assets"] is None
        assert mapped["net_expense_ratio"] is None
        assert mapped["asset_classes"] == {}
        assert mapped["sector_weights"] == {}
        assert mapped["region_weights"] == {}
        assert mapped["equity_pe"] is None
        assert mapped["top_holdings"] == []

    def test_non_dict_payload(self):
        assert _map_fund_payload("nonsense")["name"] is None
        assert _map_fund_payload(None)["top_holdings"] == []

    def test_general_only(self):
        mapped = _map_fund_payload({"General": {"Name": "Vanguard 500 Index", "Type": "FUND"}})
        assert mapped["name"] == "Vanguard 500 Index"
        assert mapped["quote_type"] == "FUND"
        assert mapped["nav_per_share"] is None

    def test_unparsable_cells_stay_absent(self):
        payload = {"MutualFund_Data": {"Expense_Ratio": "n/a", "Yield_YTD": None, "Nav": ""}}
        mapped = _map_fund_payload(payload)
        assert mapped["net_expense_ratio"] is None
        assert mapped["ytd_return"] is None
        assert mapped["nav_per_share"] is None

    def test_malformed_composition_sections_are_skipped(self):
        payload = {
            "MutualFund_Data": {
                "Asset_Allocation": {"0": {"Type": None, "Net_%": "0.1"}, "1": "junk"},
                "Sector_Weights": ["junk"],
                "Top_Holdings": {"0": {"Name": "Apple Inc", "Weight": None}},
            }
        }
        mapped = _map_fund_payload(payload)
        assert mapped["asset_classes"] == {}
        assert mapped["sector_weights"] == {}
        assert mapped["top_holdings"] == []


class TestProviderArm:
    def test_capabilities_and_catalog_row(self):
        provider = EODHDProvider("test-token")
        assert Category.FUND_DATA in provider.capabilities()
        spec = ENDPOINTS[Category.FUND_DATA]
        assert spec.url == "https://eodhd.com/api/fundamentals/{ticker}"
        assert spec.params == {"api_token": "$KEY", "fmt": "json"}

    async def test_403_on_fundamentals_is_a_plan_gate(self):
        """The real gate body carries no ``_PLAN_GATE_MARKERS`` text, so the
        endpoint must translate the raw 403 itself (breaker not charged)."""
        request = httpx.Request("GET", "https://eodhd.com/api/fundamentals/IEI")
        response = httpx.Response(
            403,
            request=request,
            text="Forbidden. Please contact support@eodhistoricaldata.com",
        )
        error = httpx.HTTPStatusError("403", request=request, response=response)
        provider = EODHDProvider("test-token")
        with patch.object(provider, "_get", AsyncMock(side_effect=error)):
            with pytest.raises(ProviderPlanError):
                await provider.fetch("IEI", DataType.FUND_PROFILE)

    async def test_bare_symbol_falls_back_to_the_us_suffix(self):
        """Caller's symbol first, verbatim; ``.US`` only after a not-found."""
        success = httpx.Response(
            200,
            request=httpx.Request("GET", "https://eodhd.com/api/fundamentals/IEI.US"),
            json=_SWPPX,
        )
        not_found = httpx.HTTPStatusError(
            "404",
            request=httpx.Request("GET", "https://eodhd.com/api/fundamentals/IEI"),
            response=httpx.Response(
                404, request=httpx.Request("GET", "https://eodhd.com/api/fundamentals/IEI")
            ),
        )
        mock = AsyncMock(side_effect=[not_found, success])
        provider = EODHDProvider("test-token")
        with patch.object(provider, "_get", mock):
            result = await provider.fetch("IEI", DataType.FUND_PROFILE)
        assert [call.args[0] for call in mock.call_args_list] == [
            "/fundamentals/IEI",
            "/fundamentals/IEI.US",
        ]
        assert result.provider == "eodhd"
        assert result.data_type == DataType.FUND_PROFILE
        assert result.data["nav_per_share"] == pytest.approx(92.59)

    async def test_suffixed_symbol_is_not_double_suffixed(self):
        """``SWPPX.US`` is tried verbatim — the arm never appends a second suffix."""
        success = httpx.Response(
            200,
            request=httpx.Request("GET", "https://eodhd.com/api/fundamentals/SWPPX.US"),
            json=_SWPPX,
        )
        mock = AsyncMock(side_effect=[success])
        provider = EODHDProvider("test-token")
        with patch.object(provider, "_get", mock):
            await provider.fetch("SWPPX.US", DataType.FUND_PROFILE)
        assert [call.args[0] for call in mock.call_args_list] == ["/fundamentals/SWPPX.US"]


def test_moomoo_does_not_claim_fund_data():
    """The moomoo absence is deliberate (see its ``_CATEGORIES`` comment).

    Constructing the adapter touches no gateway/SDK (both are lazy), so this pins
    the documented verdict without network access.
    """
    assert Category.FUND_DATA not in MoomooProvider("127.0.0.1", 11111).capabilities()
