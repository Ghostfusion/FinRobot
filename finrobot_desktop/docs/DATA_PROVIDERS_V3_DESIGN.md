# FinRobot Data Layer v3 — Design

Status: **accepted** (owner decisions below locked in this session).
Scope: `finrobot_desktop/finrobot/` (V2 engine). V0 `finrobot_autogen/` and V1
`finrobot_equity/` are out of scope.

> **Security.** This document names environment variables and public vendor URLs
> only. It never contains a credential value, and `.env` is never committed
> (already covered by the root `.gitignore`). See §10.

---

## 1. Problem

V2 today is deliberately the opposite of what we now need:

- `FinRobotSettings.settings_customise_sources` returns `(init_settings,)` only —
  it **explicitly drops the env and `.env` sources** (`config.py:176-193`). User
  config comes from `~/.finrobot/settings.json` + the OS keychain
  (`secret_store.py`), per ADR-0013.
- The data layer is a **hard-coded 6-provider chain** (`factory.build_provider_chain`,
  `factory.py:20-91`): `FMP? → Finnhub? → yfinance → EDGAR? → Adanos? → News`.
  Failover is by chain position + capability filter, not by data category.

We need: **one `.env` at the repository root as the single credential source**;
**OpenRouter** as the LLM; **moomoo OpenD** as a data provider; the remaining
`.env` keys as additional providers; a **probe** step that enumerates the
endpoints each provider can actually serve; and a **single failover chain**
ordered per data category.

## 2. Locked decisions

| Decision | Choice |
|---|---|
| Where the new data layer lives | **Rework V2 in place** (`finrobot_desktop/finrobot`) |
| Key source | **`.env` is the single source**; keychain + Settings key-entry retired |
| moomoo OpenD | **Optional / degradable** — registered only when the gateway is reachable |
| Endpoint probing | **Static catalog + live probe** command (results logged, not persisted) |

This reverses ADR-0013 ("keys live only in the OS keychain, user config is
app-stored-only"). The reversal is intentional and recorded in §8.

## 3. Configuration: `.env` at repo root

### 3.1 Location and loading

- File: `<repo root>/.env` — the same path the current checkout already uses.
  Resolution order for the path: `$FINROBOT_ENV_FILE` (test/ops override) →
  `<repo root>/.env` discovered by walking up from the package to the directory
  containing `.git`. No other location is read.
- New module `finrobot/env.py` owns **all** environment access for credentials
  (extending the existing red-line that only `config.py` / `secret_store.py`
  touch `os.environ`). It parses `.env` itself (no new runtime dependency; the
  format is `KEY=VALUE`, `#` comments, optional surrounding quotes) and exposes
  `load_env_secrets() -> dict[str, str]`.
- Loading happens **once**, as early as possible: `cli.py` entrypoint,
  `server.py` boot (before `get_settings`), and `sdk.FinRobot.__init__`.

### 3.2 Precedence

```
init kwargs (explicit / tests)   ← highest
.env value
FinRobotSettings default          ← lowest
```

`.env` never overrides an explicitly-passed kwarg, so tests stay hermetic.

### 3.3 Variable → provider mapping (names only)

| `.env` variable | Provider id | Access URL (public; from the file's header comment) |
|---|---|---|
| `OPENROUTER_API_KEY` | *(LLM)* `openrouter` | `https://openrouter.ai/api/v1` |
| `OPENROUTER_BASE_URL` | *(LLM)* `openrouter` | — |
| `OPENROUTER_MODEL_NAME` | *(LLM)* `openrouter` | — |
| `FINNHUB_API_KEY` | `finnhub` | `https://finnhub.io/api/v1` |
| `ALPHAVANTAGE_API_KEY` | `alpha_vantage` | `https://www.alphavantage.co/query` |
| `TIINGO_API_KEY` | `tiingo` | `https://api.tiingo.com` |
| `FMP_API_KEY` | `fmp` | `https://financialmodelingprep.com/stable` |
| `FRED_API_KEY` | `fred` | `https://api.stlouisfed.org/fred` |
| `MASSIVE_API_KEY` | `massive` | `https://api.massive.com` (Polygon.io rebranded) |
| `EODHD_API_KEY` | `eodhd` | `https://eodhd.com/api` |
| `TWELVEDATA_API_KEY` | `twelvedata` | `https://api.twelvedata.com` |
| `STOCKDATA_API_KEY` | `stockdata` | `https://api.stockdata.org` |
| `NEWSAPI_API_KEY` | `newsapi` | `https://newsapi.org/v2` |
| `BENZINGA_API_KEY` | `benzinga` | `https://api.benzinga.com/api` |
| `MOOMOO_HOST` / `MOOMOO_PORT` | `moomoo` | local OpenD gateway (no HTTP host) |
| `MOOMOO_AUTOSTART` / `MOOMOO_ACCOUNT` / `MOOMOO_OPEND_PATH` | `moomoo` | — |

Keyless providers (no `.env` entry): `yfinance`, `sec_edgar`, `gdelt`,
`polymarket`, `cboe`, `federal_reserve`.

`SEC_USER_AGENT` — the SEC identity is **not a secret**; it stays an app-stored
value unless the owner also wants it in `.env`. Default behaviour: read
`SEC_USER_AGENT` from `.env` when present, else fall back to the current
`sec_user_agent` field. (Flagged in §11.)

### 3.4 Settings integration

- `DATA_PROVIDER_SECRET_FIELDS` becomes the **settings-field ↔ env-name** table
  (`fmp_api_key` ↔ `FMP_API_KEY`, …), one entry per keyed provider, plus the
  new vendors. It remains the single source shared by the hydrator and the
  settings route.
- `_provider_keys` (the LLM key sink) is hydrated from `.env`
  (`provider id → OPENROUTER_API_KEY` for the LLM axis) instead of the keychain.
- `secret_store.py` (`KeychainSecretStore`, `FileSecretStore`,
  `create_secret_store`) and the `FINROBOT_DEV_MODE` / `FINROBOT_USE_KEYCHAIN`
  switches are **retired**. `keyring` drops out of `pyproject.toml` dependencies.
- Infra knobs (`FINROBOT_CACHE_DB_PATH`, `FINROBOT_SKILLS_DIR`,
  `FINROBOT_BACKTEST_STRATEGY_MODULE_PREFIXES`, `NO_COLOR`) are unchanged.

## 4. LLM: OpenRouter

- Add a built-in `ProviderConfig(id="openrouter", label="OpenRouter",
  kind="openai-compatible", base_url=OPENROUTER_BASE_URL)`.
- `model_name` seeds to `openrouter:<OPENROUTER_MODEL_NAME>` when unset.
- The key flows through the existing `_provider_keys` map; `create_model`'s
  `openai-compatible` branch already handles OpenRouter — **no new branch**.
- `anthropic` / `openai` built-ins: retained (harmless; user may still pick one),
  with OpenRouter first.
- `LANGCHAIN_PROVIDER=OPENROUTER` is honoured as an optional selector hint; it
  does not pull LangChain in.

## 5. Data providers: categories, priority, catalog

### 5.1 Category model

The table defines **33 categories** across two groups — a fallback group and a
single-vendor group. These are *not* the existing `DataType` values, so we add a
first-class `Category` enum and a `DataType → Category` map.

```mermaid
flowchart LR
  C[Consumer: pipelines/routes] --> DT[DataType]
  DT --> CAT["Category (33)"]
  CAT --> P["PRIORITY[category]<br/>ordered provider ids"]
  P --> L[DataLayer walk]
  L --> OK[first healthy provider wins]
```

### 5.2 Priority table (authoritative)

Fallback chains (left = highest priority). One owner-requested deviation from
the original reference table: **`fmp` leads `core_stock_apis` and
`fundamental_data`** (the table omitted FMP; the engine treats it as the primary
financials/quote source, and the pre-existing chain-order tests encode that).

| Category | Order |
|---|---|
| `core_stock_apis` | fmp > eodhd > moomoo > yfinance > tiingo > twelvedata > stockdata > benzinga |
| `news_data` | eodhd > benzinga > moomoo > yfinance > alpha_vantage > stockdata > newsapi |
| `fundamental_data` | fmp > moomoo > yfinance > tiingo > alpha_vantage |
| `analyst_ratings` | moomoo > finnhub > yfinance > benzinga |
| `earnings_calendar` | moomoo > finnhub > yfinance > benzinga |
| `technical_indicators` | moomoo > yfinance > alpha_vantage |
| `options_data` | moomoo > yfinance |
| `short_interest` | moomoo > yfinance |
| `institution_data` | moomoo > yfinance |
| `macro_data` | fred > moomoo |
| `prediction_markets` | polymarket > moomoo |
| `corporate_actions` | eodhd > moomoo > benzinga |
| `news_sentiment` | eodhd > alpha_vantage > gdelt |

Single-vendor (no fallback):

| Category | Provider |
|---|---|
| `sec_filings` | sec_edgar |
| `risk_free_curve` | federal_reserve |
| `options_surface` | cboe |
| `exchange_symbols` | eodhd |
| `equity_screener` | yfinance |
| `market_movers` | yfinance |
| `capital_flow` | moomoo |
| `earnings_catalyst` | moomoo |
| `earnings_surprise` | moomoo |
| `economic_calendar` | moomoo |
| `expected_move` | moomoo |
| `fed_watch` | moomoo |
| `market_breadth` | moomoo |
| `revenue_breakdown` | moomoo |
| `smart_money` | moomoo |
| `analyst_actions` | benzinga |
| `fda_calendar` | benzinga |
| `guidance_revisions` | benzinga |
| `news_retractions` | benzinga |
| `offerings_calendar` | benzinga |

### 5.3 Why "single chain" ≠ one global sort

The per-category orders **conflict** (e.g. `core_stock_apis` wants
`moomoo > yfinance`; `news_data` wants `benzinga > moomoo`), so no single global
provider ordering satisfies the table. "Single chain" therefore means: **one
`DataLayer`, one provider set, one failover mechanism — iterated in
`PRIORITY[category]` order for the requested data type.** This preserves the
existing layer contract (capability filter → health gate → first success wins)
and only changes the *order source* from list position to the category table.

### 5.4 Endpoint catalog

`finrobot/engine/data/catalog.py` holds a declarative catalog:

```python
@dataclass(frozen=True)
class EndpointSpec:
    capability: Category
    method: str
    url: str
    params: dict[str, str] = field(default_factory=dict)

PROVIDER_ENDPOINTS: dict[str, dict[Category, EndpointSpec]] = {
    "eodhd": {
        Category.core_stock_apis: EndpointSpec(Category.core_stock_apis, "GET",
            "https://eodhd.com/api/eod/{ticker}", {"api_token": "$KEY", "fmt": "json"}),
        ...
    },
    ...
}
```

The catalog is the single source of truth for (a) which providers claim which
categories, (b) the exact URL/params, and (c) what the probe exercises. Provider
adapters *build requests from the catalog* rather than re-declaring URLs.

## 6. moomoo OpenD

- Transport: the local **OpenD gateway** via the `moomoo-api` Python SDK
  (`OpenQuoteContext(host=MOOMOO_HOST, port=MOOMOO_PORT)`), **not** HTTP. OpenD
  must be installed, running, and previously logged in ("remember password").
- Capabilities map to categories: snapshot/quote → `core_stock_apis`,
  `technical_indicators`, `options_data`, `short_interest`, `institution_data`,
  `capital_flow`, `market_breadth`, `revenue_breakdown`, `smart_money`; calendar
  endpoints → `earnings_calendar`, `economic_calendar`, `earnings_catalyst`,
  `earnings_surprise`, `expected_move`, `fed_watch`; plus `macro_data`,
  `prediction_markets`, `corporate_actions` fallbacks.
- **Optional/degradable**: at chain build, a short reachability probe
  (`MOOMOO_HOST:PORT` TCP open) decides registration. Unreachable → the provider
  is skipped and every list falls through. Startup and CI never require OpenD.
- We **never** read or store the moomoo password; only `MOOMOO_ACCOUNT` (login id)
  is used for auto-login.
- The SDK import is lazy and guarded, so environments without `moomoo-api`
  installed degrade identically to "OpenD down".

## 7. Probe harness

- `finrobot/probe.py` + CLI `finrobot probe [--provider ID] [--category CAT]`.
- For every enabled provider × catalog entry it makes one live call and classifies
  the result with the existing `routes/settings._classify_data_provider_error`
  vocabulary: `ok | auth | plan | rate_limited | not_found | connect | http`.
- Output: a per-provider/per-endpoint matrix (human table + `--json`). Results are
  **logged, not persisted** — the catalog stays authoritative (owner decision).
- Rate limits are respected per provider (`_MIN_INTERVAL` from the adapter).
- The same harness backs the existing `/test-data-provider` route, so the UI and
  the CLI share one implementation.

## 8. Blast radius & migration (from reconnaissance)

Replaces (or edits):

- `config.py` — `settings_customise_sources`, `BUILTIN_PROVIDERS`,
  `DATA_PROVIDER_SECRET_FIELDS`, key fields, `model_post_init`, `validate_runtime_config`,
  `get_settings` docstrings.
- `secret_store.py` — retired; `server.py` `hydrate_settings_from_secrets` reworked.
- `engine/data/factory.py` — `build_provider_chain` reworked to the category registry.
- `engine/data/layer.py` — provider iteration becomes category-ordered; the
  `isinstance(EdgarToolsProvider/FMPProvider)` fast-paths are re-expressed as
  category lookups.
- `routes/settings.py` — keychain probes removed; `secret_storage_mode` retired;
  `available_providers` / `_PROVIDER_KEY_FIELDS` / PUT+clear-secret reworked.
- Frontend `SettingsView.tsx` / `DataSourcesPanel.tsx` / `schema.d.ts` — key
  entry becomes read-only (keys live in `.env`); provider list becomes dynamic.
- `pyproject.toml` — drop `keyring`, add `moomoo-api` (optional extra).

Tests to update (pinned today, per recon): `test_sdk.py`, `test_routes_data_provider_note.py`,
`test_provider_health_route.py`, `test_routes_settings.py`, `test_desktop_v1_api.py`,
`test_server.py`, `test_config_p2a.py`, `test_config.py`, `test_secret_store.py`,
`test_provider_health.py`, `test_data_layer.py`, `test_cache.py`,
`test_architecture.py`, `test_no_direct_yfinance_imports.py`, plus the per-provider
unit tests.

## 9. Testing strategy

- Keep the deterministic offline gate (`pytest -m "not integration"`) green; the
  live probe network calls are `@pytest.mark.integration`.
- New unit tests: `.env` parsing + precedence; OpenRouter provider construction;
  category→order resolution; catalog completeness (every priority entry has a
  provider + catalog rows); moomoo skip-when-unreachable.
- Shape parity: every price/financials adapter must satisfy the existing
  `test_provider_price_shape.py` / canonical-traceability contracts (or the
  category's canonical contract).

## 10. Security

- `.env` is gitignored at the repo root; `.env.*` too. The probe/CLI never echo
  values; error messages are key-free (reuse the `_classify_*` policy that strips
  request URLs carrying `apiKey=`).
- No credential is ever logged, dumped, serialized to `settings.json`, or written
  into artifacts/PDFs.
- `_provider_keys` stays a `PrivateAttr` (never in `model_dump()`).
- The design doc and all commits reference variable **names** only.

## 11. Open questions (owner)

1. `SEC_USER_AGENT` — keep in `.env` or leave app-stored? (Design default: `.env`
   when present, else app-stored.)
2. `adanos` (retail sentiment) is in the repo today but absent from the priority
   table and absent from `.env`; it therefore registers keyless-disabled. Confirm
   it stays (and gets an env var) or is dropped.
3. `federal_reserve` vs `fred` — both appear; `fred` uses `FRED_API_KEY`
   (macro series), `federal_reserve` is the keyless risk-free-curve source
   (Treasury/H.15). Confirm this split.