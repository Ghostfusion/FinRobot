# FinRobot Data Layer v3 — Implementation

Companion to `DATA_PROVIDERS_V3_DESIGN.md`. Records what was actually built,
how to run it, and what remains. **No credential values appear here** — variable
names only.

---

## 1. What changed (summary)

| Area | Before | After |
|---|---|---|
| Credential source | OS keychain + `settings.json`; env/`.env` deliberately dropped | **Repo-root `.env`** is the single source |
| LLM | anthropic + openai built-ins | **OpenRouter** built-in, model/key/base URL from `.env` |
| Data chain | hard-coded 6-provider list | **category-priority failover** over a provider registry |
| Providers | 6 chain members | **+14 adapters** (eodhd, tiingo, twelvedata, stockdata, benzinga, newsapi, massive, alpha_vantage, fred, federal_reserve, cboe, gdelt, polymarket, moomoo) |
| Endpoints | implicit | declarative **catalog** + live **probe** |

## 2. New modules

| Path | Role |
|---|---|
| `finrobot/env.py` | repo-root `.env` discovery/parse; canonical provider→env-var map |
| `finrobot/engine/data/categories.py` | `Category` (33), `PRIORITY` table, `DATATYPE_CATEGORY` map |
| `finrobot/engine/data/catalog.py` | `EndpointSpec` + catalog aggregator |
| `finrobot/engine/data/registry.py` | `ProviderSpec` registry; `build_provider_chain`; `order_for_category` |
| `finrobot/probe.py` | live endpoint probe (`python -m finrobot.probe`, `finrobot probe`) |
| `finrobot/engine/data/providers/{eodhd,tiingo,twelvedata,stockdata,benzinga,newsapi,massive,alpha_vantage,fred,federal_reserve,cboe,gdelt,polymarket,moomoo}_provider.py` | 14 new adapters |

## 3. Modified modules

- **`config.py`** — added the `openrouter` built-in; expanded the data-key fields
  and `DATA_PROVIDER_KEY_FIELDS` (single source); `data_key(provider_id)`;
  `_effective_base_url` (OpenRouter base override); `apply_env_secrets()`;
  `get_settings(use_env=...)`; docstrings updated (ADR-0013 reversal recorded).
- **`engine/data/factory.py`** — `build_provider_chain` now delegates to the registry.
- **`engine/data/layer.py`** — `_serves()` capability bridge (DataType ⇄ Category)
  and `_ordered(data_type)`; every provider walk now iterates in category-priority
  order. The `isinstance(EdgarToolsProvider)` / `isinstance(FMPProvider)` fast-paths
  are unchanged (still used for the SEC/FMP-only routes).
- **`secret_store.py`** — added `EnvSecretStore` (reads `.env`, rejects writes);
  `create_secret_store()` returns it with mode `"env"`; `SecretStorageMode` gains
  `"env"`; dropped the orphaned `sys` import.
- **`cli.py`** — `_build_deps` uses `get_settings(use_env=True)`; added the `probe` command.
- **`sdk.py`** — `FinRobot.__init__` uses `get_settings(use_env=True)`.

## 4. `.env` format

The shipped file at the repo root is the schema; env-var names are the contract
(see the design doc §3.3). Grouped by provider with the access URL as a comment
above each key. `MOOMOO_HOST/PORT` configure the local OpenD gateway; the
password is never stored.

## 5. How the failover chain works

1. `registry.build_provider_chain(settings)` instantiates every provider whose
   precondition holds (key present / gateway reachable / keyless) in global order.
2. For each request the `DataLayer` maps `data_type → Category` and iterates the
   providers that `_serves()` the category, sorted by `PRIORITY[Category]`
   (unlisted providers last, stable).
3. First healthy provider that returns wins; financials additionally fetch one
   secondary for cross-validation; the circuit breaker still applies.

## 6. Running the probe

```bash
cd finrobot_desktop
python -m finrobot.probe                # human table, all providers
python -m finrobot.probe --provider eodhd --json
finrobot probe --provider finrobot      # via CLI
```

Classification vocabulary: `ok | auth | plan | rate_limited | not_found | connect
| http | no_key | no_catalog | gateway`. Results are printed, never persisted.

## 7. Verification performed

- **Config hydration (live):** `get_settings(use_env=True)` resolved
  `openrouter:deepseek/deepseek-v4.1-flash`, the OpenRouter key, base URL, the
  data keys, and `moomoo_host/port` from `.env`; keyless `data_key("yfinance")`
  returned None.
- **Catalog:** `endpoint_catalog()` aggregated 14 providers / 49 endpoint rows.
- **Chain build (live):** 19 providers registered from `.env`, including `moomoo`
  (its OpenD gateway was reachable) and `edgar_tools` (the `sec_edgar` adapter,
  served from `SEC_USER_AGENT` — see §9.2; this superseded an earlier 18-provider
  build where the `.env` overlay was not yet applied at boot, §8).
- **Lint:** `ruff check finrobot/` (the CI rule set) is clean after fixing one
  orphaned import; `ruff format` applied to all changed files.
- **Types/tests:** see §9 (recorded after the run).

## 8. Defects fixed on the spot

- `probe._render` substituted `{ticker}` only in the URL, not in param values —
  fixed (params now substitute both `$KEY` and `{ticker}`).
- `EndpointSpec` could not express a scheme-prefixed auth header (Tiingo's
  `Token <key>`) — added `auth_value`; Tiingo's rows set `"Token $KEY"`.
- The `sec_filings` priority entry named the registry id `sec_edgar` while the
  provider reports `edgar_tools`, so neither `order_for_category()` nor
  `DataLayer._ordered()` ever ranked it — a silent no-op (invisible while the
  category has a single vendor). Added `registry.PROVIDER_NAME_BY_ID` +
  `provider_runtime_name()` and resolved ids in both rank maps;
  `tests/unit/test_data_categories.py` pins the invariant.
- `server.lifespan` built settings with a bare `get_settings(...)`, so
  `apply_env_secrets` never ran: the app booted on the *placeholder* SEC identity
  and an empty `model_name`, and `sec_edgar` never registered. `EnvSecretStore`
  still hydrated data-provider API keys, so the chain looked populated and hid
  the fault. Extracted `server.load_boot_settings()` (`use_env=True`) for the boot
  path + the clear-secret rebuild, and fixed the two `finrobot backtest` call
  sites that had the same omission. `tests/unit/test_boot_settings_env.py` pins it.
- The `edgar` logger logged the configured SEC identity (a person's name + email)
  at INFO on client init, and the JSON file handler persisted it to
  `finrobot.log`. Pinned `edgar` to WARNING in `obs.setup._NOISY`, and scrubbed
  the 143 lines earlier boots had already written to that log.

## 9. Known gaps / follow-ups

1. **Frontend credential entry** — resolved. Key rows render read-only
   (`ReadOnlyCredential`; `SettingsView.test.tsx` pins `disabled` + `readonly`),
   the provider list is driven by `/api/settings/provider-health`, and a PUT
   carrying a key is refused by `EnvSecretStore` with a user-visible error
   (`test_routes_settings.py`). The SEC identity field — the last editable
   credential control — is read-only too; it used to write `settings.json` and
   thereby shadow `.env` (see §9.2).
2. **`SEC_USER_AGENT`** — resolved: with a valid `Name email` identity in `.env`,
   `sec_edgar` registers (under the runtime name `edgar_tools`) and `sec_filings`
   is served. No longer a gap.
   **Precedence (design doc §11 Q1)** — decided: the UI keeps no write path for
   the identity (read-only field, §9.1), so `settings.json` can no longer shadow
   `.env` through normal use. `apply_env_secrets` therefore stays fill-only: an
   operator who edits `settings.json` by hand still wins, which is intended —
   that file is app config, `.env` is the credential source.
3. **Providers unlisted by the owner's table** — decided: `massive` and `adanos`
   stay registered but unranked, so they can never outrank a listed provider and
   remain usable only as end-of-chain fallbacks. `fmp` leads `core_stock_apis`
   and `fundamental_data` (owner request).
4. **`federal_reserve` base URL** — accepted: `api.fiscaldata.treasury.gov`
   exposes no daily par-yield-curve dataset, so the adapter reads the official
   Treasury `daily-treasury-rates` CSV from `home.treasury.gov`.
5. **Legacy stores** — removed: `KeychainSecretStore` / `FileSecretStore` deleted
   from `secret_store.py` along with the `keyring` dependency in `pyproject.toml`
   (and its now-obsolete tests). `EnvSecretStore` is the only store.
   `keyring` remains installed as a transitive dependency of
   `pydantic-ai[fastmcp]`; nothing in `finrobot/` imports it.
6. **Test updates** — resolved: no test still pins the old chain order.
   `tests/unit/test_data_layer.py`'s chain tests are generic 3-provider failover
   cases, and the suite is green (3317 passed / 10 known Windows-local failures,
   see design doc §8). The remaining keychain-pinned tests go away with the
   legacy stores in §9.5.
7. **moomoo category→SDK-method mapping** — verified against a live OpenD gateway
   (TCP `MOOMOO_HOST:MOOMOO_PORT` reachable; live `OpenQuoteContext`). All five
   interpretive mappings returned `ret=0` with real data and are correct as coded;
   no change needed.

   | Category | OpenD call | Live result |
   |---|---|---|
   | `expected_move` | `get_option_underlying_overview` | ret=0, IV / IV-rank / HV columns |
   | `earnings_catalyst` | `get_financials_earnings_price_history` | ret=0, 584 rows, predicted-vs-actual vola, IV crush |
   | `earnings_surprise` | `get_financials_earnings_price_move` | ret=0, 110 rows, day-offset price + IV/HV |
   | `smart_money` | `get_insider_trade_list` + `get_shareholders_holding_changes` | both ret=0, real holder-change rows |
   | `market_breadth` | `get_rise_fall_distribution` | ret=0, rise/fall bucket distribution |

   One shape note (not a mapping error, left as-is): `get_rise_fall_distribution`
   returns a dict, not a DataFrame, so `_records` wraps it as a single record with
   the distribution nested under `range_list`.