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
| Providers | 6 chain members | **+13 adapters** (eodhd, tiingo, twelvedata, stockdata, benzinga, newsapi, massive, alpha_vantage, fred, federal_reserve, cboe, gdelt, polymarket, moomoo) |
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
- **Chain build (live):** 18 providers registered from `.env`, including
  `moomoo` (its OpenD gateway was reachable) and `sec_edgar` omitted (no valid SEC
  identity configured — see gaps).
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

## 9. Known gaps / follow-ups

1. **Frontend key entry** — `SettingsView.tsx` / `DataSourcesPanel.tsx` still
   render editable key fields. Under the new model a PUT of a key is rejected by
   `EnvSecretStore` (by design), so those fields should become read-only and the
   provider list should be driven by `/provider-health`. Not yet done.
2. **`SEC_USER_AGENT`** — resolved: with a valid `Name email` identity in `.env`,
   `sec_edgar` registers (under the runtime name `edgar_tools`) and `sec_filings`
   is served. No longer a gap.
3. **Providers unlisted by the owner's table** — resolved for FMP (owner
   request): `fmp` now leads `core_stock_apis` and `fundamental_data`. `massive`
   and `adanos` remain registered but absent from every priority list, so they
   never outrank a listed provider; add them to a category if that should change.
4. **`federal_reserve` base URL** — `api.fiscaldata.treasury.gov` exposes no daily
   par-yield-curve dataset; the adapter reads the official Treasury `daily-treasury-rates`
   CSV from `home.treasury.gov` instead. Confirm acceptable.
5. **Legacy stores** — `KeychainSecretStore` / `FileSecretStore` are now unused
   (kept so their existing tests import cleanly); remove in a follow-up along with
   the `keyring` dependency in `pyproject.toml`.
6. **Test updates** — tests pinning the old chain order / keychain behaviour need
   updating for the new ordering and env source (see design doc §8).
7. **moomoo category→SDK-method mapping** — several interpretive categories
   (expected_move, earnings_catalyst, earnings_surprise, smart_money, market_breadth)
   use the closest documented OpenD call; confirm against live OpenD.