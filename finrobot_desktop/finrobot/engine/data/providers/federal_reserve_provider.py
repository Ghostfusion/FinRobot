# finrobot/engine/data/providers/federal_reserve_provider.py
"""US Treasury risk-free yield-curve provider (keyless).

Backed by the U.S. Department of the Treasury's *Daily Treasury Par Yield Curve
Rates*, published at
https://home.treasury.gov/resource-center/data-chart-center/interest-rates and
served as CSV from the ``daily-treasury-rates.csv`` feed. No credential.
Serves ``risk_free_curve`` only: ``fetch`` returns the most recent business
day's par yields keyed by maturity label (``1 Mo`` … ``30 Yr``).

The par yield curve is NOT served by the Fiscal Data API
(https://api.fiscaldata.treasury.gov) — that API's full dataset list contains no
daily Treasury yield/par-rate table; Treasury publishes the curve itself. See
docs/DATA_PROVIDERS_V3_DESIGN.md §5.2 / §11.
"""

from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from typing import Any

import httpx

from finrobot.engine.data.catalog import EndpointSpec
from finrobot.engine.data.categories import Category
from finrobot.engine.data.interface import (
    DataProvider,
    DataResult,
    ProviderError,
    ProviderPlanError,
    RateLimitedProviderError,
)
from finrobot.engine.data.types import DataType

_BASE_URL = "https://home.treasury.gov"
_CSV_PATH = "/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/{year}/all"
_TIMEOUT = 45.0
#: The Treasury CSV endpoint is genuinely slow rather than broken: a live call
#: measured ~17s for the 2026 daily yield curve (15.9 KB). The old 15s timeout
#: meant this provider could NEVER return the risk-free curve — the probe
#: reported `connect / ReadTimeout` and so did the adapter. Deliberately above
#: the ~17s measurement, still bounded.
_MIN_INTERVAL = 0.5
_SUPPORTED: list[str | DataType] = [Category.RISK_FREE_CURVE]

_PLAN_MARKERS: tuple[str, ...] = (
    "subscription",
    "plan",
    "upgrade",
    "entitlement",
    "not authorized",
    "does not have access",
    "premium",
    "exclusive",
)


class FederalReserveProvider(DataProvider):
    """DataProvider backed by the U.S. Treasury Daily Treasury Par Yield Curve.

    Provides the keyless risk-free curve (``risk_free_curve``) from the
    Department of the Treasury's published par-yield table at
    https://home.treasury.gov/resource-center/data-chart-center/interest-rates.
    No API key required.
    """

    def __init__(self) -> None:
        # Reuse one AsyncClient across the session to amortise TLS handshakes.
        self._client = httpx.AsyncClient(timeout=_TIMEOUT)

    @property
    def name(self) -> str:
        return "federal_reserve"

    def capabilities(self) -> list[str | DataType]:
        return list(_SUPPORTED)

    async def fetch(self, ticker: str, data_type: str | DataType, **kwargs: Any) -> DataResult:
        if data_type not in _SUPPORTED:
            raise ProviderError(
                "data_type "
                f"'{data_type}' is not supported by federal_reserve. Supported: {_SUPPORTED}"
            )
        try:
            year = kwargs.get("year")
            data = await self._fetch_curve(int(year) if year is not None else None)
        except httpx.TimeoutException as e:
            raise ProviderError(f"federal_reserve timeout for '{ticker}'") from e
        except httpx.HTTPStatusError as e:
            raise _classify_http_error(e, ticker) from e
        except (
            httpx.ConnectError,
            httpx.RemoteProtocolError,
            httpx.ReadError,
            httpx.WriteError,
        ) as e:
            raise ProviderError(
                f"federal_reserve network error for '{ticker}' ({type(e).__name__})"
            ) from e
        except ProviderError:
            raise
        except (ValueError, KeyError, TypeError, AttributeError) as e:
            raise ProviderError(
                f"federal_reserve fetch failed for '{ticker}' ({type(e).__name__})"
            ) from e

        return DataResult(
            data=data,
            provider=self.name,
            ticker=ticker,
            data_type=data_type,
            timestamp=datetime.now(tz=timezone.utc),
        )

    async def _fetch_curve(self, year: int | None = None) -> dict[str, Any]:
        """Fetch the most recent par-yield row for ``year`` (default: current UTC year)."""
        target_year = year if year is not None else datetime.now(tz=timezone.utc).year
        url = f"{_BASE_URL}{_CSV_PATH.format(year=target_year)}"
        params = {
            "type": "daily_treasury_yield_curve",
            "field_tdr_date_value": str(target_year),
            "page": "",
            "_format": "csv",
        }
        resp = await self._client.get(url, params=params)
        resp.raise_for_status()
        header, row, as_of = _latest_row(list(csv.reader(io.StringIO(resp.text))))
        if row is None or as_of is None:
            raise ProviderError(
                f"federal_reserve returned no par-yield rows for year {target_year}"
            )
        curve: dict[str, float | None] = {}
        for label, cell in zip(header[1:], row[1:]):
            curve[label] = _optional_float(cell)
        return {
            "as_of": as_of,
            "curve": curve,
            "source": "U.S. Department of the Treasury",
        }

    async def close(self) -> None:
        """Release the shared httpx client. Called from DataLayer.close()."""
        await self._client.aclose()


def _classify_http_error(exc: httpx.HTTPStatusError, ticker: str) -> ProviderError:
    """Map a Treasury HTTP failure onto the typed taxonomy (no request URL in messages)."""
    status = exc.response.status_code
    if status == 429:
        return RateLimitedProviderError(f"federal_reserve rate limited (HTTP 429) for '{ticker}'")
    if status == 403 and _is_plan_gate(exc.response):
        return ProviderPlanError(
            f"federal_reserve endpoint gated upstream (HTTP 403) for '{ticker}'"
        )
    return ProviderError(f"federal_reserve API error for '{ticker}' (HTTP {status})")


def _is_plan_gate(response: httpx.Response) -> bool:
    """True when a 403 body reads as an upstream plan/entitlement gate."""
    try:
        body = response.text.lower()
    except (httpx.ResponseNotRead, UnicodeDecodeError):
        return False
    return any(marker in body for marker in _PLAN_MARKERS)


def _latest_row(rows: list[list[str]]) -> tuple[list[str], list[str] | None, str | None]:
    """Return (header, newest data row, its ISO date) from a Treasury CSV grid."""
    if not rows:
        return [], None, None
    header = rows[0]
    latest: list[str] | None = None
    latest_date: str | None = None
    for row in rows[1:]:
        if not row:
            continue
        iso = _parse_us_date(row[0])
        if iso is None:
            continue
        if latest_date is None or iso > latest_date:
            latest_date = iso
            latest = row
    return header, latest, latest_date


def _parse_us_date(value: str | None) -> str | None:
    """Convert a Treasury ``MM/DD/YYYY`` date cell to ISO ``YYYY-MM-DD``."""
    if not value:
        return None
    parts = value.split("/")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        return None
    month, day, year = parts
    return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"


def _optional_float(value: Any) -> float | None:
    """Parse a yield cell, preserving None for absent/blank values (never a fake 0)."""
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


ENDPOINTS: dict[Category, EndpointSpec] = {
    Category.RISK_FREE_CURVE: EndpointSpec(
        capability=Category.RISK_FREE_CURVE,
        method="GET",
        url=f"{_BASE_URL}{_CSV_PATH.format(year='{year}')}",
        params={
            "type": "daily_treasury_yield_curve",
            "field_tdr_date_value": "{year}",
            "page": "",
            "_format": "csv",
        },
    ),
}
