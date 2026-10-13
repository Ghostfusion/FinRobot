from __future__ import annotations

import asyncio
import sys
import threading
from collections.abc import Coroutine
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeVar

import click

from finrobot import __version__
from finrobot.config import FinRobotSettings, get_settings
from finrobot.engine.analysis.prompts import ANALYSIS_TYPES
from finrobot.engine.data.ticker import validate_ticker

if TYPE_CHECKING:
    from finrobot.engine.deps import FinRobotDeps
    from finrobot.engine.pipelines.base import Pipeline


# Reminder appended to CLI pipeline output. HTML rendering lives in the
# server process; CLI runs are stand-alone and don't share state with it.
_HTML_REPORT_NOTE = (
    "\nNote: HTML reports require the server. Run 'finrobot serve', "
    "then trigger the analysis via the /chat API or Desktop app. "
    "CLI results are not shared with the server (separate processes)."
)


def _validate_ticker_arg(raw: str) -> str:
    """Normalise a CLI ``ticker`` argument or abort with a clean CLI error.

    Wraps the shared :func:`validate_ticker` so cache keys stay consistent and
    junk symbols are rejected before a pipeline ever runs. A raised ValueError
    becomes a ``ClickException`` (clean one-line stderr, exit 1) instead of a
    traceback.
    """
    try:
        return validate_ticker(raw)
    except ValueError as e:
        raise click.ClickException(str(e)) from e


def _default_ledger_path(ticker: str) -> str:
    """Where ``backtest --auto`` writes its trial ledger when ``--ledger`` is absent.

    Under the app's own home directory rather than the working directory, so an
    ``--auto`` run never drops a file into whatever tree the user happens to be
    standing in; the run prints the path it used.
    """
    from finrobot.paths import ensure_home

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return str(ensure_home() / "ledgers" / f"{ticker}-{stamp}.jsonl")


def _parse_bps_grid(raw: str) -> tuple[float, ...]:
    """Parse a ``--cost-bps`` value like ``"0,1,2.5,5"`` into cost levels."""
    try:
        values = tuple(float(part) for part in raw.split(",") if part.strip())
    except ValueError as e:
        raise click.ClickException(f"Invalid --cost-bps {raw!r}: {e}") from e
    if not values:
        raise click.ClickException(f"--cost-bps {raw!r} names no cost levels")
    return values


def _settings_for_model(model: str | None) -> FinRobotSettings:
    """CLI settings, applying ``--model`` only when one was actually given.

    ``FinRobotSettings.model_name`` is a ``str``, not ``str | None``, so passing
    ``model_name=None`` through is a validation error — which is exactly what
    happened to ``backtest --auto`` without ``--model``: the command died on
    startup before it could do anything. The override has to be conditional, and
    this is the one place that gets it right instead of two.
    """
    if model:
        return get_settings(use_env=True, model_name=model)
    return get_settings(use_env=True)


def _build_deps(model: str | None = None) -> "FinRobotDeps":
    """Build deps only. No agent creation.
    Used by pipeline commands that create their own sub-agents."""
    from finrobot.obs import setup_logging

    setup_logging(get_settings(use_env=True))

    from finrobot.engine.data.factory import build_data_layer
    from finrobot.engine.deps import FinRobotDeps
    from finrobot.engine.skills.registry import SkillRegistry

    # Credentials come from the repo-root .env (Data Layer v3).
    settings = _settings_for_model(model)

    # Runtime config validation: checks LLM key + FMP key (required).
    # Raises ValueError; we convert to ClickException for clean CLI output.
    try:
        settings.validate_runtime_config()
    except ValueError as e:
        raise click.ClickException(str(e)) from e

    # Load skills if available
    skills_path = Path(settings.skills_dir)
    registry = SkillRegistry(skills_path) if skills_path.exists() else None

    # Build provider chain via shared factory (FMP primary → yfinance fallback)
    data_layer = build_data_layer(settings)
    deps = FinRobotDeps(data_layer=data_layer, settings=settings, skill_runtime=registry)

    return deps


def _build_runtime(model: str | None = None) -> tuple[Any, "FinRobotDeps"]:
    """Build lead agent + deps. Used by `run` command (Mode A)."""
    from finrobot.engine.orchestrator import create_lead_agent

    deps = _build_deps(model)
    agent = create_lead_agent(deps.settings, skill_registry=deps.skill_runtime)
    return agent, deps


def _build_pipeline(key: str, deps: "FinRobotDeps") -> "Pipeline":
    """Build the pipeline registered under ``key`` for a CLI subcommand.

    Looks the factory up in the pipeline registry (the single source of truth)
    instead of each subcommand inlining its own
    ``create_*_pipeline`` import — adding a pipeline no longer means touching
    the CLI. Builds the shared sub-agents the factory needs.
    """
    from finrobot.engine.agents.factory import create_sub_agents
    from finrobot.engine.pipelines.registry import get_pipeline_factories

    sub_agents = create_sub_agents(deps.settings, skill_registry=deps.skill_runtime)
    pipeline: Pipeline = get_pipeline_factories()[key](sub_agents)
    return pipeline


_T = TypeVar("_T")


def _run_with_teardown(coro: Coroutine[Any, Any, _T], deps: "FinRobotDeps") -> _T:
    """Run one CLI workload and shut the data layer down on the SAME event loop.

    A CLI invocation is a one-shot process: it builds a DataLayer, runs a single
    pipeline and exits. Without an explicit teardown the DataCache's aiosqlite
    worker and the process-level quote-batch / SEC-holdings singletons outlive the
    run, and the interpreter blocks at exit joining them — the command printed its
    entire report and then never returned (observed 2026-10-12: ``finrobot fund
    IEI`` and ``finrobot research IEI`` both still alive minutes after their last
    line, exit 124 under ``timeout``; a deps-only script that builds the same
    layer and exits finished in 6s). ``scripts/*`` tools have always called
    ``factory.shutdown_data_layer`` for exactly this reason; the CLI never did.
    The server path is unaffected — it has its own FastAPI-lifespan teardown.

    BUG-082: the teardown MUST share the workload's event loop. Closing the layer
    from a second ``asyncio.run`` re-binds its aiosqlite connection to a fresh
    loop while the worker thread still belongs to the finished one — the orphan
    thread the same bug describes. One loop, one ``asyncio.run``.
    """

    from finrobot.engine.data.factory import shutdown_data_layer

    async def _guarded() -> _T:
        try:
            return await coro
        finally:
            await shutdown_data_layer(deps.data_layer)

    return asyncio.run(_guarded())


async def _should_use_ddm(deps: "FinRobotDeps", ticker: str) -> bool:
    """Check if ticker is a bank/financial that should use DDM.

    Fetches financials to get industry/sector, then uses the industry
    detection module. Returns False on any error (fail-open to DCF).

    BUG-082: this MUST be ``await``-ed inside the SAME ``asyncio.run`` as the
    pipeline execution. Wrapping the ``fetch`` in its own ``asyncio.run`` opened
    the shared DataCache aiosqlite connection on a throwaway loop; the next
    ``asyncio.run`` reused that connection, leaving its aiosqlite worker thread
    bound to the destroyed loop → the interpreter hung forever joining the
    orphan thread at shutdown. Keeping everything on one loop avoids that.
    """
    from finrobot.engine.primitives.industry import is_bank
    from finrobot.engine.data.types import DataType

    try:
        result = await deps.data_layer.fetch(DataType.FINANCIALS, ticker)
        data = result.data
        industry = data.get("industry")
        sector = data.get("sector")
        return is_bank(industry=industry, sector=sector)
    except (ValueError, KeyError, TypeError, RuntimeError, AttributeError):
        return False


class CliProgress:
    """Print pipeline progress to the terminal.

    Implements the ProgressCallback Protocol from
    finrobot.engine.pipelines.base. Writes to stdout so users see real-time
    step progress instead of waiting for the full pipeline to finish.
    """

    def __init__(self) -> None:
        self._total: int = 0

    async def on_step_start(self, step_index: int, total: int, step_name: str) -> None:
        self._total = total
        label = step_name.replace("_", " ").title()
        click.echo(f"  [{step_index}/{total}] {label}...", nl=False)

    async def on_step_end(
        self,
        step_index: int,
        total: int,
        step_name: str,
        duration_s: float,
        error: str | None = None,
    ) -> None:
        # A non-None error means the step DEGRADED (finished but failed
        # validation after all retries on a non-critical step, BUG-058) — say so
        # instead of printing a clean "done" that hides the failure.
        if error is not None:
            click.echo(f" degraded ({duration_s:.1f}s): {error[:80]}")
        else:
            click.echo(f" done ({duration_s:.1f}s)")

    async def on_step_retry(
        self, step_index: int, step_name: str, attempt: int, error: str
    ) -> None:
        # Newline so the retry note is on its own line (the preceding start
        # line was written without a newline).
        click.echo(f" retry {attempt} ({error[:60]})")
        # Reprint the step label so the subsequent on_step_end has context.
        label = step_name.replace("_", " ").title()
        click.echo(f"  [{step_index}/{self._total}] {label}...", nl=False)


@click.group()
@click.version_option(version=__version__, prog_name="finrobot")
def cli() -> None:
    """FinRobot — financial AI agent platform."""


@cli.command()
@click.option("--provider", multiple=True, help="Limit to provider id(s)")
@click.option("--json", "as_json", is_flag=True, help="Emit JSON")
def probe(provider: tuple[str, ...], as_json: bool) -> None:
    """Probe every configured data provider's endpoints (live key check)."""
    from finrobot import probe as probe_mod

    argv: list[str] = []
    for provider_id in provider:
        argv += ["--provider", provider_id]
    if as_json:
        argv.append("--json")
    raise SystemExit(probe_mod.main(argv))


@cli.command("verify-audit")
@click.option(
    "--path",
    "ledger_path",
    default=None,
    type=click.Path(dir_okay=False, path_type=Path),
    help="Ledger file to check (default: ~/.finrobot/audit_chain.jsonl)",
)
def verify_audit(ledger_path: Path | None) -> None:
    """Verify the machine audit ledger's hash chain.

    The ledger is the tamper-evident record of what each saved report artifact
    asserted (see finrobot/audit_chain.py). One line of verdict; a broken chain
    exits 1 so a cron/CI wrapper can alert on it the same way `probe --json`
    reports a dead provider. The default path is resolved at call time so a
    relocated home directory is honoured.
    """
    from finrobot.audit_chain import default_ledger_path, verify_chain

    path = ledger_path or default_ledger_path()
    report = verify_chain(path)
    if report.ok:
        click.echo(f"OK: audit chain intact ({report.n_entries} entries) — {path}")
        return
    click.echo(
        f"BROKEN: {report.reason} at seq {report.first_bad_seq} "
        f"({report.n_entries} entries read) — {path}"
    )
    sys.exit(1)


@cli.group()
def pit() -> None:
    """Inspect the point-in-time snapshot store."""


@pit.command("show")
@click.argument("symbol")
@click.option(
    "--as-of",
    "as_of_raw",
    default=None,
    help="View date YYYY-MM-DD (default: today). Snapshots dated after it are invisible.",
)
@click.option("--json", "as_json", is_flag=True, help="Emit the raw payload as JSON")
def pit_show(symbol: str, as_of_raw: str | None, as_json: bool) -> None:
    """Show what the engine knew about SYMBOL as of a date.

    The read side of the PIT store, and the question a lookahead-safe replay depends on:
    every run appends its provider snapshot under the date it was taken, and
    ``read_as_of`` masks anything dated later — so this prints the view a run on that
    date would have had, never a later one. A symbol with no qualifying snapshot is
    reported as such and exits 1: an absent snapshot is not an empty one.
    """
    import json as _json
    from datetime import date as _date

    from finrobot.engine.data.pit_store import PitStore, default_pit_root

    try:
        view_date = _date.fromisoformat(as_of_raw) if as_of_raw else _date.today()
    except ValueError:
        click.echo(f"--as-of must be YYYY-MM-DD, got {as_of_raw!r}")
        sys.exit(2)

    store = PitStore(default_pit_root())
    ticker = symbol.upper()
    payload = store.read_as_of(ticker, view_date)
    if payload is None:
        click.echo(f"no snapshot for {ticker} on or before {view_date.isoformat()}")
        sys.exit(1)

    if as_json:
        click.echo(_json.dumps(payload, indent=2, default=str))
        return

    membership = store.membership(ticker, view_date)
    click.echo(f"{ticker} as of {view_date.isoformat()} — membership: {membership}")
    for key in ("artifact_id", "type", "data_source"):
        if key in payload:
            click.echo(f"  {key}: {payload[key]}")
    raw_keys = payload.get("raw_data")
    if isinstance(raw_keys, dict):
        click.echo(f"  raw_data sections: {', '.join(sorted(raw_keys)) or '(none)'}")
    click.echo("  (--json for the full payload)")


# --- Skill subcommands ---


@cli.group()
def skill() -> None:
    """Manage FinRobot skills."""


@skill.command("list")
def skill_list() -> None:
    """List all available skills grouped by domain."""
    from finrobot.engine.skills.registry import SkillRegistry

    settings = get_settings()
    skills_path = Path(settings.skills_dir)
    if not skills_path.exists():
        click.echo("No skills directory found. Run convert_skills.py first.")
        return
    registry = SkillRegistry(skills_path)
    for s in registry.list_all():
        click.echo(f"  [{s.domain}] {s.id}: {s.name}")


@skill.command("search")
@click.argument("query")
def skill_search(query: str) -> None:
    """Search skills by keyword."""
    from finrobot.engine.skills.registry import SkillRegistry

    settings = get_settings()
    skills_path = Path(settings.skills_dir)
    if not skills_path.exists():
        click.echo("No skills directory found. Run convert_skills.py first.")
        return
    registry = SkillRegistry(skills_path)
    results = registry.search(query)
    if not results:
        click.echo(f"No skills matching '{query}'")
        return
    for s in results:
        click.echo(f"  {s.id}: {s.name}")
        click.echo(f"    {s.description[:120]}")


# --- Main commands ---


@cli.command()
@click.argument("question")
@click.option("--model", default=None, help="Override model, e.g. anthropic:claude-sonnet-4-6")
def run(question: str, model: str | None) -> None:
    """Ask a quick financial question (Mode A)."""
    agent, deps = _build_runtime(model)
    result = agent.run_sync(question, deps=deps)
    click.echo(result.output)


@cli.command()
@click.argument("ticker")
@click.option("--model", default=None, help="Override model, e.g. anthropic:claude-sonnet-4-6")
@click.option(
    "--lang",
    default=None,
    type=click.Choice(["en", "zh"]),
    help="Output language (en=English, zh=Chinese)",
)
def research(ticker: str, model: str | None, lang: str | None) -> None:
    """Run equity research pipeline on a ticker (Mode B).

    Calls pipeline.execute() directly — does NOT rely on LLM tool selection.
    This is deterministic: the pipeline always runs all 5 steps regardless of model.
    """
    ticker = _validate_ticker_arg(ticker)
    deps = _build_deps(model)

    pipeline = _build_pipeline("research", deps)

    result = _run_with_teardown(
        pipeline.execute(deps, ticker, progress=CliProgress(), lang=lang), deps
    )
    click.echo(result.format_summary())
    click.echo(_HTML_REPORT_NOTE)


@cli.command()
@click.argument("ticker")
@click.option("--model", default=None, help="Override model, e.g. anthropic:claude-sonnet-4-6")
@click.option(
    "--lang",
    default=None,
    type=click.Choice(["en", "zh"]),
    help="Output language (en=English, zh=Chinese)",
)
@click.option(
    "--peers",
    default=None,
    help="Comma-separated peer tickers (3-10), e.g. AAPL,MSFT,GOOGL. "
    "Overrides automatic peer selection with your own comparable set.",
)
def comps(ticker: str, model: str | None, lang: str | None, peers: str | None) -> None:
    """Run comparable company analysis pipeline."""
    ticker = _validate_ticker_arg(ticker)
    deps = _build_deps(model)

    pipeline = _build_pipeline("comps", deps)

    # Only forward `peers` when supplied, so the default path passes no run
    # kwargs and behaves byte-identically to before the override existed.
    # dict[str, Any] (not object) so the **unpack stays mypy-clean against
    # execute()'s typed keyword params (lang / source_artifact_id: str | None).
    extra: dict[str, Any] = {}
    if peers:
        # BUG-047: validate format AND count at the CLI entry, before the
        # ~30s data_collection step, so a bad --peers fails in 0s with a clean
        # ClickException instead of a bare ValueError traceback from deep in
        # the pipeline. Reuses the shared validate_ticker (rejects CJK / junk
        # like '苹果,!!!') and the same bounds the runtime check enforces
        # (_helpers.py keeps its check as defense-in-depth for SDK/route paths).
        from finrobot.engine.pipelines._helpers import (
            _PEER_COMP_INPUT_MAX,
            _PEER_COMP_SET_MIN,
        )

        peers_list = [_validate_ticker_arg(p) for p in peers.split(",") if p.strip()]
        if not _PEER_COMP_SET_MIN <= len(peers_list) <= _PEER_COMP_INPUT_MAX:
            raise click.ClickException(
                f"--peers needs {_PEER_COMP_SET_MIN}-{_PEER_COMP_INPUT_MAX} tickers, "
                f"got {len(peers_list)}."
            )
        extra["peers"] = peers_list

    result = _run_with_teardown(
        pipeline.execute(deps, ticker, progress=CliProgress(), lang=lang, **extra), deps
    )
    click.echo(result.format_summary())


@cli.command()
@click.argument("ticker")
@click.option("--model", default=None, help="Override model, e.g. anthropic:claude-sonnet-4-6")
@click.option(
    "--force-dcf",
    is_flag=True,
    default=False,
    help="Force FCF-DCF even for banks (skip DDM auto-detection)",
)
@click.option(
    "--lang",
    default=None,
    type=click.Choice(["en", "zh"]),
    help="Output language (en=English, zh=Chinese)",
)
def dcf(ticker: str, model: str | None, force_dcf: bool, lang: str | None) -> None:
    """Run DCF valuation pipeline.

    For banks (detected via industry/sector), automatically uses DDM
    (Dividend Discount Model) instead of FCF-DCF. Use --force-dcf to override.
    """
    ticker = _validate_ticker_arg(ticker)
    deps = _build_deps(model)

    from finrobot.engine.agents.factory import create_sub_agents
    from finrobot.engine.pipelines.registry import get_pipeline_factories

    sub_agents = create_sub_agents(deps.settings, skill_registry=deps.skill_runtime)
    factories = get_pipeline_factories()

    from finrobot.engine.pipelines.base import PipelineResult

    async def _dcf_or_ddm() -> PipelineResult:
        """BUG-082: bank detection + pipeline run on ONE event loop.

        Folding ``_should_use_ddm``'s FINANCIALS fetch into this single
        ``asyncio.run`` keeps the shared DataCache aiosqlite connection bound to
        the live loop, so it is never reused across a destroyed loop (which
        deadlocked the interpreter at shutdown).
        """
        if not force_dcf and await _should_use_ddm(deps, ticker):
            click.echo(
                f"Detected {ticker.upper()} as a bank/financial institution. "
                "Using DDM (Dividend Discount Model) instead of FCF-DCF.\n"
                "Use --force-dcf to override.\n",
                err=True,
            )
            ddm_pipeline: Pipeline = factories["ddm"](sub_agents)
            return await ddm_pipeline.execute(deps, ticker, progress=CliProgress(), lang=lang)

        dcf_pipeline: Pipeline = factories["dcf"](sub_agents)
        return await dcf_pipeline.execute(deps, ticker, progress=CliProgress(), lang=lang)

    result = _run_with_teardown(_dcf_or_ddm(), deps)
    click.echo(result.format_summary())
    click.echo(_HTML_REPORT_NOTE)


@cli.command()
@click.argument("ticker")
@click.option("--model", default=None, help="Override model, e.g. anthropic:claude-sonnet-4-6")
@click.option(
    "--lang",
    default=None,
    type=click.Choice(["en", "zh"]),
    help="Output language (en=English, zh=Chinese)",
)
def ddm(ticker: str, model: str | None, lang: str | None) -> None:
    """Run DDM (Dividend Discount Model) valuation pipeline.

    DDM values a company based on projected dividends discounted at cost of equity.
    Appropriate for banks, utilities, and dividend-paying stocks where
    traditional free cash flow is not meaningful.
    """
    ticker = _validate_ticker_arg(ticker)
    deps = _build_deps(model)

    pipeline = _build_pipeline("ddm", deps)

    result = _run_with_teardown(
        pipeline.execute(deps, ticker, progress=CliProgress(), lang=lang), deps
    )
    click.echo(result.format_summary())
    click.echo(_HTML_REPORT_NOTE)


@cli.command()
@click.argument("ticker")
@click.option("--model", default=None, help="Override model, e.g. anthropic:claude-sonnet-4-6")
@click.option(
    "--lang",
    default=None,
    type=click.Choice(["en", "zh"]),
    help="Output language (en=English, zh=Chinese)",
)
def fund(ticker: str, model: str | None, lang: str | None) -> None:
    """Run investment-fund research pipeline (ETF / mutual fund / closed-end fund).

    Computes NAV risk/return statistics, expense-ratio cost drag, premium/discount
    to NAV and portfolio concentration from real provider data. Use it for ETFs,
    mutual funds and closed-end funds — a fund files no income statement, so the
    equity pipelines cannot value it.
    """
    ticker = _validate_ticker_arg(ticker)
    deps = _build_deps(model)

    pipeline = _build_pipeline("fund_research", deps)

    result = _run_with_teardown(
        pipeline.execute(deps, ticker, progress=CliProgress(), lang=lang), deps
    )
    click.echo(result.format_summary())
    click.echo(_HTML_REPORT_NOTE)


@cli.command()
@click.argument("ticker")
@click.option("--model", default=None, help="Override model, e.g. anthropic:claude-sonnet-4-6")
@click.option(
    "--lang",
    default=None,
    type=click.Choice(["en", "zh"]),
    help="Output language (en=English, zh=Chinese)",
)
def lbo(ticker: str, model: str | None, lang: str | None) -> None:
    """Run LBO (leveraged buyout) analysis pipeline.

    Deterministic IRR/MOIC arithmetic — LLM selects assumptions, code computes returns.
    """
    ticker = _validate_ticker_arg(ticker)
    deps = _build_deps(model)

    pipeline = _build_pipeline("lbo", deps)

    result = _run_with_teardown(
        pipeline.execute(deps, ticker, progress=CliProgress(), lang=lang), deps
    )
    click.echo(result.format_summary())
    click.echo(_HTML_REPORT_NOTE)


@cli.command()
@click.argument("ticker")
@click.option("--model", default=None, help="Override model, e.g. anthropic:claude-sonnet-4-6")
@click.option(
    "--lang",
    default=None,
    type=click.Choice(["en", "zh"]),
    help="Output language (en=English, zh=Chinese)",
)
def earnings(ticker: str, model: str | None, lang: str | None) -> None:
    """Run earnings quality analysis pipeline.

    Requires FMP API key for earnings surprise data (set FINROBOT_FMP_API_KEY).
    """
    ticker = _validate_ticker_arg(ticker)
    deps = _build_deps(model)

    pipeline = _build_pipeline("earnings", deps)

    result = _run_with_teardown(
        pipeline.execute(deps, ticker, progress=CliProgress(), lang=lang), deps
    )
    click.echo(result.format_summary())


@cli.command(name="ic-memo")
@click.argument("ticker")
@click.option("--model", default=None, help="Override model, e.g. anthropic:claude-sonnet-4-6")
@click.option(
    "--lang",
    default=None,
    type=click.Choice(["en", "zh"]),
    help="Output language (en=English, zh=Chinese)",
)
def ic_memo(ticker: str, model: str | None, lang: str | None) -> None:
    """Run Investment Committee (IC) memo pipeline.

    Runs DCF + LBO inline and applies IRR hurdle gate (PASS if IRR < 15%).
    """
    ticker = _validate_ticker_arg(ticker)
    deps = _build_deps(model)

    pipeline = _build_pipeline("ic-memo", deps)

    result = _run_with_teardown(
        pipeline.execute(deps, ticker, progress=CliProgress(), lang=lang), deps
    )
    click.echo(result.format_summary())
    click.echo(_HTML_REPORT_NOTE)


@cli.command()
@click.argument("ticker")
@click.option(
    "--strategy",
    default="sma_crossover",
    show_default=True,
    help=(
        "Built-in strategy name (sma_crossover) or, if you have whitelisted an "
        "import-path prefix in FINROBOT_BACKTEST_STRATEGY_MODULE_PREFIXES, a "
        "module:ClassName that loads a custom bt.Strategy. NOTE: module:ClassName "
        "executes that module's top-level code on import; it is disabled by default."
    ),
)
@click.option("--start", required=True, help="Start date (YYYY-MM-DD)")
@click.option("--end", required=True, help="End date (YYYY-MM-DD)")
@click.option("--cash", default=100_000.0, show_default=True, help="Initial cash")
@click.option(
    "--params", default=None, help='Strategy params as JSON, e.g. \'{"fast":10,"slow":30}\''
)
@click.option(
    "--save-chart", default=None, type=click.Path(), help="Save equity curve PNG to this path"
)
@click.option(
    "--auto", is_flag=True, default=False, help="LLM-guided strategy selection (iterative)"
)
@click.option("--model", default=None, help="Override model for --auto mode")
@click.option(
    "--ledger",
    default=None,
    type=click.Path(),
    help=(
        "With --auto, where to write the trial ledger for `finrobot validate`. "
        "Defaults to ~/.finrobot/ledgers/<ticker>-<timestamp>.jsonl."
    ),
)
def backtest(
    ticker: str,
    strategy: str,
    start: str,
    end: str,
    cash: float,
    params: str | None,
    save_chart: str | None,
    auto: bool,
    model: str | None,
    ledger: str | None,
) -> None:
    """Run a backtest on a ticker with a given strategy.

    Example:
        finrobot backtest AAPL --strategy sma_crossover --start 2023-01-01 --end 2024-01-01

    With --auto, the LLM picks and iteratively tunes strategy parameters, and the
    search is persisted as a trial ledger so the validation gate can score it:
        finrobot backtest AAPL --start 2023-01-01 --end 2024-01-01 --auto
        finrobot validate ~/.finrobot/ledgers/AAPL-<timestamp>.jsonl
    """
    ticker = _validate_ticker_arg(ticker)

    from finrobot.engine.data.factory import build_data_layer, shutdown_data_layer
    from finrobot.engine.backtest.engine import BacktestConfig, BacktestResult

    if auto:
        from finrobot.engine.backtest.strategy_agent import run_strategy_selection

        settings = _settings_for_model(model)

        # Catch a missing/invalid LLM key up front (same check _build_deps runs)
        # so --auto fails with a clean message instead of a late traceback from
        # the first LLM call. Mirrors _build_deps' ValueError -> ClickException.
        try:
            settings.validate_runtime_config()
        except ValueError as e:
            raise click.ClickException(str(e)) from e

        ledger_target = ledger or _default_ledger_path(ticker)

        async def _run_auto() -> BacktestResult:
            data_layer = build_data_layer(settings)
            try:
                return await run_strategy_selection(
                    settings,
                    ticker,
                    start,
                    end,
                    data_layer,
                    initial_cash=cash,
                    ledger_path=ledger_target,
                )
            finally:
                # shutdown_data_layer (not a bare close): the backtest's price
                # window also opens the process-level quote-batch singleton, and
                # leaking it is the same exit hang the pipeline commands fixed.
                await shutdown_data_layer(data_layer)

        result = asyncio.run(_run_auto())
        click.echo(result.format_summary())
    else:
        import json

        from finrobot.engine.backtest.backtrader_adapter import BackTraderAdapter

        if ledger:
            click.echo(
                "Note: --ledger applies to --auto only. A single manual run is not a search, "
                "so there is no search for the selection-bias gates to correct — run --ledger "
                "with --auto and score that ledger."
            )

        strategy_params: dict[str, float | int | str] = {}
        if params:
            try:
                strategy_params = json.loads(params)
            except json.JSONDecodeError as e:
                raise click.ClickException(f"Invalid --params JSON: {e}") from e

        config = BacktestConfig(
            ticker=ticker,
            start_date=start,
            end_date=end,
            strategy=strategy,
            strategy_params=strategy_params,
            initial_cash=cash,
        )

        settings = get_settings(use_env=True)

        async def _run_manual() -> BacktestResult:
            data_layer = build_data_layer(settings)
            try:
                return await BackTraderAdapter(data_layer).run(config)
            finally:
                # shutdown_data_layer (not a bare close): the backtest's price
                # window also opens the process-level quote-batch singleton, and
                # leaking it is the same exit hang the pipeline commands fixed.
                await shutdown_data_layer(data_layer)

        result = asyncio.run(_run_manual())
        click.echo(result.format_summary())

    if save_chart and result.chart_base64:
        import base64

        chart_bytes = base64.b64decode(result.chart_base64)
        Path(save_chart).write_bytes(chart_bytes)
        click.echo(f"\nEquity curve saved to {save_chart}")


@cli.command()
@click.argument("ledger", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--trial-id", type=int, default=None, help="Trial to score (default: best Sharpe)")
@click.option("--blocks", default=10, show_default=True, help="CSCV blocks (even, >= 2)")
@click.option(
    "--benchmark",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="CSV of per-bar benchmark returns for the SPA test",
)
@click.option("--as-json", "as_json", is_flag=True, help="Emit the report as JSON")
@click.option(
    "--cost-grid",
    "cost_grid_enabled",
    is_flag=True,
    default=False,
    help=(
        "Also re-price the ledger across the corpus's 0/1/2/5/10 bps-per-side grid, "
        "because one frictionless number is not an answer. Needs a turnover: the "
        "ledger's, or --turnover."
    ),
)
@click.option(
    "--cost-bps",
    "cost_bps",
    default=None,
    help="Custom per-side grid in bps, e.g. '0,5,10'; implies --cost-grid",
)
@click.option(
    "--turnover",
    type=float,
    default=None,
    help="Notional traded per bar as a fraction of capital, when the ledger records none",
)
def validate(
    ledger: Path,
    trial_id: int | None,
    blocks: int,
    benchmark: Path | None,
    as_json: bool,
    cost_grid_enabled: bool,
    cost_bps: str | None,
    turnover: float | None,
) -> None:
    """Score a trial ledger with the backtest validation gate.

    The ledger is a JSONL file: one header line, then one evaluated parameter set
    per line (see ``finrobot.engine.backtest.validation.build_ledger_from_search``
    to produce one from a search). The gate reports deflated Sharpe, PBO/CSCV,
    SPA, MinTRL and regime stability, and only Seals a strategy that passes all
    five. Costs real data: no network calls, everything is computed from the file.

    Example:
        finrobot validate trials.jsonl --blocks 10
        finrobot validate trials.jsonl --cost-grid
    """
    import csv

    from finrobot.engine.backtest.validation import (
        DEFAULT_BPS_GRID,
        TrialLedger,
        ValidationConfig,
        cost_grid,
        validate_ledger,
    )

    try:
        loaded = TrialLedger.read_jsonl(ledger)
    except ValueError as e:
        raise click.ClickException(f"Unreadable ledger '{ledger}': {e}") from e

    benchmark_returns: list[float] | None = None
    if benchmark is not None:
        try:
            with benchmark.open(encoding="utf-8", newline="") as handle:
                rows = [row for row in csv.reader(handle) if row]
            benchmark_returns = [
                float(row[-1]) for row in rows[1:] if not row[0].lower().startswith("date")
            ]
        except (OSError, ValueError) as e:
            raise click.ClickException(f"Unreadable benchmark '{benchmark}': {e}") from e
        if len(benchmark_returns) != loaded.n_bars:
            raise click.ClickException(
                f"Benchmark has {len(benchmark_returns)} bars but the ledger grid has "
                f"{loaded.n_bars}; they must align bar for bar"
            )

    try:
        report = validate_ledger(
            loaded,
            winner_trial_id=trial_id,
            benchmark=benchmark_returns,
            config=ValidationConfig(n_blocks=blocks),
        )
    except ValueError as e:
        raise click.ClickException(str(e)) from e

    grid = None
    if cost_grid_enabled or cost_bps is not None:
        try:
            grid = cost_grid(
                loaded,
                bps_grid=(_parse_bps_grid(cost_bps) if cost_bps is not None else DEFAULT_BPS_GRID),
                turnover=turnover,
                winner_trial_id=trial_id,
                benchmark=benchmark_returns,
                config=ValidationConfig(n_blocks=blocks),
            )
        except ValueError as e:
            raise click.ClickException(str(e)) from e

    if as_json:
        if grid is None:
            click.echo(report.model_dump_json(indent=2))
            return
        # One document with both parts, so a machine consumer that asked for the
        # grid does not have to concatenate two JSON documents from one stream.
        import json

        click.echo(
            json.dumps(
                {
                    "report": report.model_dump(mode="json"),
                    "cost_grid": grid.model_dump(mode="json"),
                },
                indent=2,
            )
        )
        return

    click.echo(report.format_summary())
    if grid is not None:
        click.echo()
        click.echo(grid.format_summary())


@cli.command()
@click.argument("ticker")
@click.argument("question")
@click.option("--model", default=None, help="Override model, e.g. anthropic:claude-sonnet-4-6")
@click.option("--top-k", default=5, show_default=True, help="Number of RAG chunks to retrieve")
def ask(ticker: str, question: str, model: str | None, top_k: int) -> None:
    """Ask a question about a company's 10-K filing using RAG.

    Fetches the latest 10-K from SEC EDGAR, retrieves relevant passages
    via BM25, and answers the question with source citations.
    """
    ticker = _validate_ticker_arg(ticker)

    from finrobot.engine.analysis.qa import run_qa

    deps = _build_deps(model)
    result = _run_with_teardown(
        run_qa(deps.data_layer, deps.settings, ticker, question, top_k=top_k), deps
    )
    click.echo(result)


@cli.command()
@click.argument("ticker")
@click.argument(
    "analysis_type",
    type=click.Choice(
        sorted(ANALYSIS_TYPES),
        case_sensitive=False,
    ),
)
@click.option("--model", default=None, help="Override model, e.g. anthropic:claude-sonnet-4-6")
def analyze(ticker: str, analysis_type: str, model: str | None) -> None:
    """Run standalone financial analysis on a ticker.

    ANALYSIS_TYPE: balance | cashflow | competitors | income | overview | risk
    """
    ticker = _validate_ticker_arg(ticker)

    from finrobot.engine.analysis.prompts import run_analysis

    deps = _build_deps(model)
    result = _run_with_teardown(
        run_analysis(deps.data_layer, deps.settings, ticker, analysis_type.lower()), deps
    )
    click.echo(result)


def _start_parent_death_watchdog(parent_pid: int) -> threading.Event:
    """Terminate this server when ``parent_pid`` (the desktop shell) is gone.

    The desktop sidecar is a PyInstaller one-file binary: Tauri spawns a
    bootloader that forks the real server, and Tauri kills the bootloader with
    SIGKILL on quit. SIGKILL is uncatchable, so the bootloader cannot forward it
    and this uvicorn process would be reparented to launchd and keep holding
    127.0.0.1:8321 — a stale orphan the next launch then talks to by mistake.

    Polling the *Tauri* pid directly (not ``os.getppid()``, which the bootloader
    masks) lets the server self-terminate on app quit or crash. Gated on an
    explicit ``--parent-pid`` so a standalone ``finrobot serve`` under
    systemd/nohup (real parent pid 1) never trips it.

    Returns the stop ``Event`` so callers (notably tests) can shut the daemon
    thread down deterministically — ``stop.set()`` breaks the poll loop on its
    next tick. Without this the loop is unstoppable: a test that leaves it
    running keeps calling ``os._exit(0)`` every 2s once the watched pid is gone,
    hard-killing the whole pytest session at a random later test (BUG-050).
    ``serve`` ignores the return — in production the watchdog runs for the
    process lifetime and exits via ``os._exit`` on real parent death.
    """
    import os
    import sys

    stop = threading.Event()

    def _parent_alive() -> bool:
        # POSIX: signal 0 sends nothing — it just probes existence + our right to
        # signal (ProcessLookupError = gone; PermissionError = alive, other uid).
        # Windows: NEVER os.kill here — CPython maps os.kill(pid, sig) for any sig
        # other than CTRL_C/CTRL_BREAK to TerminateProcess, so os.kill(parent, 0)
        # would *kill the shell we guard*. Probe via OpenProcess(SYNCHRONIZE) +
        # WaitForSingleObject: a 0-timeout wait returns WAIT_TIMEOUT (0x102) while
        # the process runs, WAIT_OBJECT_0 (0) once it exits; OpenProcess failing
        # means the pid is already gone. [Runtime-verify on real Windows — Phase 2.]
        if sys.platform == "win32":
            import ctypes

            synchronize, wait_timeout = 0x00100000, 0x00000102
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.OpenProcess(synchronize, False, parent_pid)
            if not handle:
                return False
            try:
                return bool(kernel32.WaitForSingleObject(handle, 0) == wait_timeout)
            finally:
                kernel32.CloseHandle(handle)
        try:
            os.kill(parent_pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            pass  # parent alive but owned by another uid
        return True

    def _watch() -> None:
        # Event.wait doubles as the poll interval *and* an interruptible
        # shutdown signal: returns True the instant stop is set, False on the
        # 2s timeout (the normal poll tick).
        while not stop.wait(2.0):
            if not _parent_alive():
                os._exit(0)  # parent gone — exit hard, no clients left to drain

    threading.Thread(target=_watch, name="parent-death-watchdog", daemon=True).start()
    return stop


@cli.command()
@click.option("--host", default="127.0.0.1", show_default=True, help="Bind address")
@click.option("--port", default=8321, show_default=True)
@click.option(
    "--reload",
    is_flag=True,
    default=False,
    help="Auto-restart on code changes (dev mode). Watches finrobot/.",
)
@click.option(
    "--log-level",
    default="info",
    show_default=True,
    type=click.Choice(["critical", "error", "warning", "info", "debug", "trace"]),
)
@click.option(
    "--parent-pid",
    type=int,
    default=None,
    help=(
        "Exit when this process disappears (the desktop shell's PID). Used by "
        "the Tauri sidecar so the server never orphans on 127.0.0.1; omit for "
        "standalone runs."
    ),
)
def serve(host: str, port: int, reload: bool, log_level: str, parent_pid: int | None) -> None:
    """Start the FinRobot server.

    Use ``--reload`` during development so editing Python files
    auto-restarts the worker — avoids stale-process 500s after edits.
    """
    from finrobot.obs import setup_logging

    setup_logging(get_settings())

    if parent_pid is not None:
        _start_parent_death_watchdog(parent_pid)

    import uvicorn

    if reload:
        # reload mode requires an import string (not the app object) so the
        # worker can re-import after file changes.
        uvicorn.run(
            "finrobot.server:app",
            host=host,
            port=port,
            reload=True,
            reload_dirs=["finrobot"],
            log_level=log_level,
            log_config=None,
        )
    else:
        from finrobot.server import app

        uvicorn.run(app, host=host, port=port, log_level=log_level, log_config=None)
