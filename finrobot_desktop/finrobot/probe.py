# finrobot/probe.py
"""Live endpoint probe for Data Layer v3 providers.

For every enabled provider × catalog endpoint, make ONE live call and classify
the result with the same vocabulary the settings route uses
(``ok | auth | plan | rate_limited | not_found | connect | http``). Results are
reported (human table or ``--json``) and NEVER persisted — the declarative
catalog stays authoritative (see ``docs/DATA_PROVIDERS_V3_DESIGN.md`` §7).

Run: ``python -m finrobot.probe`` or the ``finrobot probe`` CLI command.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime

import httpx

from finrobot.config import FinRobotSettings, get_settings
from finrobot.engine.data.catalog import EndpointSpec, endpoint_catalog
from finrobot.engine.data.registry import REGISTRY

logger = logging.getLogger(__name__)

_PROBE_TICKER = "AAPL"


@dataclass
class ProbeResult:
    provider: str
    category: str
    url: str
    ok: bool
    code: str
    detail: str = ""


def _make_client() -> httpx.AsyncClient:
    """The HTTP client for one probe run.

    Two settings deliberately mirror production rather than httpx's defaults,
    because a probe that disagrees with the adapters is worse than no probe:

    * ``follow_redirects`` — the cboe adapter follows cdn.cboe.com's 302 to
      cdn-api.cboe.com, so a non-following probe reported a false ``http 307``.
    * ``timeout`` — must not be shorter than the slowest adapter, or the probe
      reports false failures for endpoints production handles. The Treasury CSV
      (federal_reserve) needs ~17s. ``test_probe_render`` pins this against the
      adapters' own ``_TIMEOUT`` values.
    """
    return httpx.AsyncClient(timeout=45.0, follow_redirects=True)


def _classify(exc: BaseException) -> tuple[str, str]:
    """Map a probe failure to (code, key-free detail). NEVER returns raw text:
    the exception message can embed the request URL (which carries the key)."""
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        if status in (401, 403):
            return "auth", f"HTTP {status}"
        if status == 404:
            return "not_found", f"HTTP {status}"
        if status == 429:
            return "rate_limited", f"HTTP {status}"
        return "http", f"HTTP {status}"
    if isinstance(exc, (httpx.ConnectError, httpx.ConnectTimeout, httpx.TimeoutException)):
        return "connect", type(exc).__name__
    return "unknown", type(exc).__name__


def _render(
    ep: EndpointSpec, key: str | None, ticker: str, *, year: int | None = None
) -> tuple[str, dict[str, str], dict[str, str]]:
    """Substitute the catalog's placeholders into the URL, params and headers.

    Substitution is textual rather than ``str.format``: a row may legitimately
    carry a placeholder the probe cannot fill (moomoo's SDK rows are
    ``moomoo://{sdk_method}``), and an unfilled ``{year}`` used to abort the
    ENTIRE run with ``KeyError`` — federal_reserve's Treasury CSV row ships
    ``{year}`` in both the path and a param. Anything unresolvable passes through
    verbatim so the call gets classified instead of crashing the probe.
    """
    resolved_year = str(year if year is not None else datetime.now().year)

    def _sub(text: str) -> str:
        return (
            text.replace("{ticker}", ticker)
            .replace("{year}", resolved_year)
            .replace("$KEY", key or "")
        )

    url = _sub(ep.url)
    params = {k: _sub(v) for k, v in ep.params.items()}
    headers: dict[str, str] = {}
    if ep.auth_header and key:
        headers[ep.auth_header] = _sub(ep.auth_value)
    return url, params, headers


def _credential(provider_id: str, kind: str, settings: FinRobotSettings) -> str | None:
    """The value the probe substitutes for ``$KEY`` in a row's params/headers.

    ``identity`` providers (SEC EDGAR) authenticate with a User-Agent naming the
    requester rather than an API key, so their value lives in the
    ``sec_user_agent`` setting; ``data_key()`` maps only the keyed providers and
    would report a configured identity as "credential not configured". Both
    kinds take the same substitution path — only the source differs.
    """
    if kind == "identity":
        return getattr(settings, "sec_user_agent", "") or None
    return settings.data_key(provider_id)


async def probe_provider(
    provider_id: str, settings: FinRobotSettings, *, category: str | None = None
) -> list[ProbeResult]:
    """Probe one provider's catalog rows. Keyless/gateway rows are reported
    without a network call when there is nothing HTTP-shaped to call."""
    spec = REGISTRY.get(provider_id)
    if spec is None:
        raise ValueError(f"Unknown provider '{provider_id}'")
    rows = endpoint_catalog().get(provider_id, {})
    if not rows:
        return [ProbeResult(provider_id, "", "", False, "no_catalog", "no endpoint catalog rows")]

    if spec.kind in ("keyed", "identity"):
        key = _credential(provider_id, spec.kind, settings)
        if not key:
            return [
                ProbeResult(
                    provider_id, str(cat), ep.url, False, "no_key", "credential not configured"
                )
                for cat, ep in rows.items()
            ]
    else:
        key = None

    if spec.kind == "gateway":
        return [
            ProbeResult(provider_id, str(cat), ep.url, False, "gateway", "local gateway (SDK)")
            for cat, ep in rows.items()
        ]

    results: list[ProbeResult] = []
    async with _make_client() as client:
        for cat, ep in rows.items():
            if category is not None and str(cat) != category:
                continue
            url, params, headers = _render(ep, key, _PROBE_TICKER)
            try:
                resp = await client.request(ep.method, url, params=params, headers=headers)
                resp.raise_for_status()
                results.append(ProbeResult(provider_id, str(cat), url, True, "ok"))
            except (
                httpx.HTTPError,
                OSError,
                UnicodeDecodeError,
                ValueError,
                KeyError,
                TypeError,
            ) as exc:
                code, detail = _classify(exc)
                results.append(ProbeResult(provider_id, str(cat), url, False, code, detail))
    return results


async def probe_all(
    settings: FinRobotSettings, *, providers: list[str] | None = None
) -> list[ProbeResult]:
    ids = providers or list(endpoint_catalog().keys())
    out: list[ProbeResult] = []
    for provider_id in ids:
        out.extend(await probe_provider(provider_id, settings))
    return out


def _print_table(results: list[ProbeResult]) -> None:
    width = max((len(r.provider) for r in results), default=8)
    for r in results:
        status = "OK" if r.ok else r.code
        print(f"{r.provider:<{width}}  {r.category:<22}  {status:<12}  {r.url}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Probe data-provider endpoints.")
    parser.add_argument("--provider", action="append", help="limit to provider id(s)")
    parser.add_argument("--json", action="store_true", help="emit JSON")
    args = parser.parse_args(argv)

    settings = get_settings(use_env=True)
    results = asyncio.run(probe_all(settings, providers=args.provider))
    if args.json:
        print(json.dumps([asdict(r) for r in results], indent=2))
    else:
        _print_table(results)
    return 0 if all(r.ok for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
