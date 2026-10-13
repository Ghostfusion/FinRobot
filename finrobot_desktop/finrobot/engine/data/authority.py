"""Data-layer adapters joining provider results to the metric-authority engine.

This module is the ONLY place that turns raw provider ``DataResult`` payloads into
:class:`~finrobot.engine.models.metric_authority.MetricObservation` atoms and runs
the leaf reconciler. It is pure: no network, no provider imports, no file I/O — the
results are handed in by :mod:`finrobot.engine.data.layer`, which owns the fetch and
the cache.

Why a separate module and not ``validator.py``: the validator is a *pairwise*
comparator that emits prose about two dicts; the authority engine is *n-way* and
records WHY one number won, with full provenance. This adapter is the bridge, and it
is the only layer that sees the provider payload's own field names, so the mapping
from a vendor's keys to registry metric names lives here and nowhere else.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Sequence

from finrobot.engine.data.asof import current_run_as_of
from finrobot.engine.data.interface import DataResult
from finrobot.engine.data.registry import provider_registry_id
from finrobot.engine.data.types import DataType
from finrobot.engine.models.metric_authority import (
    METRIC_REGISTRY_BY_NAME,
    POLICY_VERSION,
    MetricObservation,
    ReconciliationReport,
    resolve_metric_observations,
)

__all__ = [
    "observations_from_financials",
    "observations_from_price",
    "reconcile_results",
]

#: Relative distance within which a reported share count is treated as REDERIVED
#: from ``market_cap / current_price`` rather than read from a filing. Mirrors the
#: validator's ``_SHARES_DERIVED_EPS`` rule (``engine/data/validator.py``): a
#: rederived count must never be allowed to confirm the very fields it was computed
#: from (FMP's lineage trap). Kept as a literal here so this module does not import
#: the validator (which imports this one for its reconciliation views).
_SHARES_DERIVED_EPS = 1e-3

#: The nine registry metrics a provider financials payload can carry, mapped 1:1 to
#: their payload keys. The payload key IS the registry name for every one of these.
_FINANCIALS_METRICS: tuple[str, ...] = (
    "revenue",
    "net_income",
    "total_cash",
    "market_cap",
    "current_price",
    "shares_outstanding",
    "ebitda",
    "total_debt",
    "gross_margin",
)

#: Metrics a PRICE / QUOTE payload can carry (a quote is current-price only).
_PRICE_METRICS: tuple[str, ...] = ("current_price",)

#: Statement items are denominated in the issuer's REPORTING currency; market items
#: in the QUOTE currency. ``shares_outstanding`` is a count, so it carries no
#: currency — two providers' counts must stay comparable regardless of their tags.
_REPORTING_METRICS = frozenset(
    {"revenue", "net_income", "total_cash", "ebitda", "total_debt", "gross_margin"}
)
_QUOTE_METRICS = frozenset({"market_cap", "current_price"})

#: Point-in-time metrics carry no flow basis (a market cap is not "ttm").
_BASISLESS_METRICS = frozenset({"market_cap", "shares_outstanding"})

_REPORTING_CURRENCY_KEYS: tuple[str, ...] = ("reporting_currency", "financial_currency")


def _num(value: object) -> float | None:
    """Coerce to float iff ``value`` is a real number (excluding ``bool``)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _as_date(value: object) -> date | None:
    """A calendar date from a date/datetime/ISO string, else ``None``.

    A bare year label ("2024", FMP's ``fiscalYear`` fallback) is NOT a date — it
    returns ``None`` rather than fabricating a January 1st period end.
    """
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def _as_datetime(value: object) -> datetime | None:
    """A tz-aware UTC instant from a datetime/date/ISO string/epoch, else ``None``."""
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return None
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)
    return None


def _first_str(data: dict[str, Any], keys: Sequence[str]) -> str | None:
    for key in keys:
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip().upper()
    return None


def _currency(data: dict[str, Any], metric: str) -> str | None:
    """The observation's currency: reporting for statement items, quote for market
    items, ``None`` for a share count. Falls back to the payload's other currency
    tag (the result's own caliber) when the primary one is absent."""
    if metric in _REPORTING_METRICS:
        return _first_str(data, _REPORTING_CURRENCY_KEYS) or _first_str(data, ("quote_currency",))
    if metric in _QUOTE_METRICS:
        return _first_str(data, ("quote_currency",)) or _first_str(data, _REPORTING_CURRENCY_KEYS)
    return None


def _period_end(data: dict[str, Any], *, price: bool) -> date | None:
    """Fiscal period end (or the bar session date for a price) from the payload."""
    for key in ("period_end", "date", "fiscal_year"):
        if key in data:
            got = _as_date(data[key])
            if got is not None:
                return got
    if price:
        history = data.get("price_history")
        if isinstance(history, list) and history:
            last = history[-1]
            if isinstance(last, dict):
                return _as_date(last.get("date"))
    return None


def _period_basis(data: dict[str, Any], metric: str, *, price: bool) -> str | None:
    if price or metric == "current_price":
        return "session"
    if metric in _BASISLESS_METRICS:
        return None
    raw = data.get("period_basis")
    return raw if isinstance(raw, str) and raw.strip() else None


def _effective_at(data: dict[str, Any], *, price: bool) -> datetime | None:
    """Semantic time of the value: the quote instant for a price, else the
    payload's own ``as_of`` when present."""
    if price:
        return _as_datetime(data.get("quote_timestamp")) or _as_datetime(data.get("as_of"))
    return _as_datetime(data.get("as_of"))


def _published_at(data: dict[str, Any]) -> datetime | None:
    """When the SOURCE knew the value (filing instant), ``None`` when unknown."""
    for key in ("published_at", "filing_date", "filed"):
        got = _as_datetime(data.get(key))
        if got is not None:
            return got
    return None


def _quality_flags(result: DataResult) -> tuple[str, ...]:
    """Degradation markers carried verbatim: the result's structured divergence and
    circuit-open channels, plus any ``degraded`` list on the payload itself."""
    flags: list[str] = [
        *result.key_field_divergences,
        *result.price_field_divergences,
        *result.circuit_open_providers,
    ]
    degraded = result.data.get("degraded") if isinstance(result.data, dict) else None
    if isinstance(degraded, list):
        flags.extend(str(marker) for marker in degraded)
    return tuple(str(flag) for flag in flags)


def _derived_from(data: dict[str, Any], metric: str) -> tuple[str, ...]:
    """``shares_outstanding`` is marked derived from ``market_cap``/``current_price``
    when the payload's own numbers satisfy the rederivation test (shares ≈ mc/price),
    so a rederived count can never confirm its own parents."""
    if metric != "shares_outstanding":
        return ()
    shares = _num(data.get("shares_outstanding"))
    market_cap = _num(data.get("market_cap"))
    price = _num(data.get("current_price")) or _num(data.get("price"))
    if shares is None or shares <= 0 or market_cap is None or price is None:
        return ()
    if market_cap <= 0 or price <= 0:
        return ()
    if abs(shares - market_cap / price) / shares < _SHARES_DERIVED_EPS:
        return ("market_cap", "current_price")
    return ()


def _observations(
    result: DataResult, metrics: Sequence[str], *, price: bool
) -> list[MetricObservation]:
    data = result.data if isinstance(result.data, dict) else {}
    # Collapse a runtime provider name to its registry id so the leaf's owner check
    # (producer_id → calibers) resolves: ``edgar_tools`` must match the
    # ``sec_edgar`` caliber. Identity for every id that already matches.
    source = provider_registry_id(result.provider)
    flags = _quality_flags(result)
    observations: list[MetricObservation] = []
    for metric in metrics:
        row = METRIC_REGISTRY_BY_NAME.get(metric)
        if row is None:
            continue
        raw = data.get(metric)
        if price and metric == "current_price" and raw is None:
            raw = data.get("price")  # a QUOTE payload names the price "price"
        value = _num(raw)
        if value is None:
            continue
        observations.append(
            MetricObservation(
                metric=metric,
                source=source,
                value=value,
                unit=row.unit,
                currency=_currency(data, metric),
                period_end=_period_end(data, price=price),
                period_basis=_period_basis(data, metric, price=price),
                effective_at=_effective_at(data, price=price),
                retrieved_at=result.timestamp,
                published_at=None if price else _published_at(data),
                derived_from=_derived_from(data, metric),
                quality_flags=flags,
            )
        )
    return observations


def observations_from_financials(result: DataResult) -> list[MetricObservation]:
    """One observation per registry metric present in a FINANCIALS payload."""
    return _observations(result, _FINANCIALS_METRICS, price=False)


def observations_from_price(result: DataResult) -> list[MetricObservation]:
    """The ``current_price`` observation from a PRICE / QUOTE payload."""
    return _observations(result, _PRICE_METRICS, price=True)


def _observations_for(result: DataResult) -> list[MetricObservation]:
    data_type = result.data_type
    if data_type in (DataType.FINANCIALS, "financials"):
        return observations_from_financials(result)
    if data_type in (DataType.PRICE, DataType.QUOTE, "price", "quote"):
        return observations_from_price(result)
    return []


def reconcile_results(
    results: Sequence[DataResult],
    *,
    clock: datetime | None = None,
    run_as_of: datetime | None = None,
) -> ReconciliationReport:
    """Reconcile every metric seen across ``results`` into one report.

    ``clock`` defaults to now (UTC); ``run_as_of`` defaults to the run's point-in-time
    ceiling (:func:`finrobot.engine.data.asof.current_run_as_of`).

    That ceiling is NOT ``None`` on a live run: ``engine/pipelines/runner.py`` pins it
    at the START of every run (``set_run_as_of(datetime.now(UTC))``, cleared in a
    ``finally``), so the ceiling is the run's own start instant. An early version of
    the gate treated ``retrieved_at > ceiling`` as lookahead — which is true of every
    fetch in every live run by construction — and turned all eight decisions of
    ``art_2026-10-13T22:36:11_EHC_equity_research_dfa427`` into
    ``unavailable``/``after_run_as_of``, caveating a healthy single-source fetch with
    8 ``metric_authority_unavailable`` findings. The gate therefore reads the SOURCE's
    knowledge time (``published_at``) only: see
    :func:`finrobot.engine.models.metric_authority._intrinsic_reason`.

    Honest limit: a vendor statement read carries ``published_at=None``, so for those
    the gate cannot fire — a vendor revision dated after a simulated decision point is
    not detectable from what we store, and our own retrieval time is not a substitute.

    Deterministic: decisions are sorted by metric and the resolver itself is
    order-independent, so the same observations produce a byte-identical report.
    """
    if clock is None:
        clock = datetime.now(tz=timezone.utc)
    if run_as_of is None:
        run_as_of = current_run_as_of()

    grouped: dict[str, list[MetricObservation]] = {}
    for result in results:
        for observation in _observations_for(result):
            grouped.setdefault(observation.metric, []).append(observation)

    decisions = tuple(
        resolve_metric_observations(metric, grouped[metric], clock=clock, run_as_of=run_as_of)
        for metric in sorted(grouped)
    )
    return ReconciliationReport(
        policy_version=POLICY_VERSION,
        run_as_of=run_as_of,
        clock=clock,
        decisions=decisions,
    )
