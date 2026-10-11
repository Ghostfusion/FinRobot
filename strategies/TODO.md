# Backlog — what to build, from the corpus reviews

Scope of this pass: a review of [`qfin-tr/agent-based-market-simulation.md`](qfin-tr/agent-based-market-simulation.md),
[`qfin-tr/llm-trading-systems.md`](qfin-tr/llm-trading-systems.md) and
[`qfin-tr/rl-trading-agents.md`](qfin-tr/rl-trading-agents.md), 2026-10-10. The other 43 documents are not yet
in scope; append their §5 items below as they are reviewed, keeping the same columns. Each row cites the
document section it comes from, so a row is checkable against the paper it rests on.

Nothing here is a validated strategy — §4 of each source document is the grading protocol, and the
documents themselves are literature-derived, not tested on FinRobot's data. Per `AGENT_ONBOARDING.md` §10 an
agent change must be a defect fix, so every **build** row needs an explicit owner decision before code is
written; the `defect` rows do not.

**Status key.** `ready` buildable in this repo today · `needs-dep` needs a new dependency ·
`needs-data` needs a feed no provider serves · `needs-owner` feature, owner sign-off required ·
`defect` fixable without new scope · `landed` already shipped · `blocked` depends on another row. Effort
letters (S/M/L) are the source documents' own estimates unless marked *review*.

**Where this stands.** Landed so far: `A1`–`A5`, `A7`, `C1`, `E1`, `E2`, `E6` — the validation gate now has
its inference primitives, its cost grid and a producer (`--auto`); the event-time gate, the probe inventory
and the runtime-dependency decision are in; and the simulation package exists with its ZI null arm. Nothing
below is in progress. What remains is `A6`, `B2`–`B5`, `C2`–`C8`, `D1`–`D4`, `E3`–`E5` and `E7`, all of
which are blocked on a dependency, a feed, or an explicit decision to build them. Two findings from the
first pass were wrong and are retracted rather than quietly dropped: `F1` (the §3 rows were correct) and
`A1`'s overstatement of what the gate was missing.

## A. Shared infrastructure

| # | Item | Source | Prereq | Acceptance | Status |
|---|---|---|---|---|---|
| A1 | **LANDED.** `diebold_mariano()` (Newey–West HAC, Harvey–Leybourne–Newbold small-sample correction, squared or absolute loss, corpus sign convention) and `sharpe_confidence_interval()` (percentile moving-block bootstrap) in `validation/overfitting.py`, sharing the SPA test's resampler — so the two cannot drift on serial dependence. Measured, and reported in the API: coverage 0.955 at a nominal 0.95 on i.i.d. returns but **0.900 on an AR(1) φ=0.2**, so an autocorrelated series now carries an explicit warning instead of a quietly optimistic band | llm §5.4; rl §5.1 | — | 16 tests: sign convention, degeneracy, h-monotone HLN correction, the Newey–West default lag, two 200-replication coverage studies (i.i.d. and AR(1)), determinism, fail-closed paths | **landed** |
| A2 | **LANDED.** `validation/costs.py::cost_grid` re-prices a ledger across 0/1/2/5/10 bps per side and re-runs the whole gate at each level, so the output is a range and `breaks_at` names the level where the seal fails. Two deliberate rules: an unpinned winner is re-selected per level (the search's conclusion under those costs), and a ledger with no recorded turnover is refused rather than re-priced from a guess. CLI: `finrobot validate <ledger> --cost-grid` / `--cost-bps 0,5,25` | llm §4 §5.2; rl §4 | A3 for the per-trial series | 6 tests: monotone erosion, a crushing level that fails the seal, the winner flip at 50 bps, pinning, and the fail-closed paths | **landed** |
| A3 | **LANDED.** `backtest --auto` now persists the search as a `TrialLedger` (every tuned parameter set, its per-bar account returns, and the metric the search ranked by), defaulting to `~/.finrobot/ledgers/<ticker>-<stamp>.jsonl` or `--ledger PATH`, and prints the path. The adapter gained an opt-in per-bar series plus a turnover meter to make that material available; SDK mirrors it via `auto_backtest(..., ledger_path=)`. A ledger is written only when one would be *valid*: ≥ 2 trials, every one carrying a series, all on one bar grid — otherwise the reason is stated in the result's warnings instead of a broken ledger being scored as if well-formed | rl §5.1; this review | — | 8 tests, including a two-trial search whose ledger the gate then scores end to end, plus the three no-ledger paths; CLI-level test that `--auto` with no `--model` reaches the search | **landed** |
| A4 | **LANDED.** The annualised Sharpe is withheld when the equity curve's daily-return dispersion falls below `MIN_DAILY_RETURN_STD` (1e-4), with the reason stated in the warnings. Cause: the built-in `sma_crossover` carries backtrader's default one-share sizer, so a $100k account holds ~0.2% exposure and the curve barely moves. Measured — dispersion 1.4e-5 and a raw ratio of **-177.75** for that configuration (the live -116.571 is the same mechanism); a fully invested position gives 1.1e-2 and keeps its 2.566 | this review | — | near-flat curve → `sharpe_ratio=None` + warning; `abs(Sharpe) < 5` still holds on the invested one-year case; 3 unit tests + 1 end-to-end regression | **landed** |
| A5 | **LANDED.** `engine/data/normalize/news_timing.py`: `classify_publication()` returns the session plus the `eligible_session` a signal may first be acted on (pre-open trades the same session; at/after the open, after the close, weekend or holiday, the next), `NewsObservation` carries the declared model release date and pretraining cutoff with a `contaminated` property, `observability_gate()` adds the delay-one-day arm, and `contamination_sharpe_contrast()` makes the acceptance criterion testable. It **reuses** `normalize/session.py`'s taxonomy rather than starting a second one. Verified independently: Friday 16:00 ET → Monday 09:30, Friday 09:00 → same session, contrast reports a 3.46 overstatement | llm §5.3 | — | 39 tests: a 15-case boundary table (holidays, Juneteenth from 2022, both DST transitions), gate precedence, inclusive contamination boundary, ET-vs-UTC date | **landed** |
| A6 | Look-ahead audit gate in any training loop: recompute the policy gradient with future information removed and reject a run whose contamination is not zero within bootstrap error | rl §5.2; llm §4 | C1 | the audit runs on the implemented objective and flags a deliberately leaky arm | blocked on C1 · M |
| A7 | **LANDED.** `fmp`, `finnhub` and `edgar` now declare catalogue rows mirroring the requests their own code makes; `sec_edgar` needed probe support for `kind=identity`, since its credential is the SEC User-Agent. The inventory went from 49 rows / 14 providers to **54 rows / 17 providers**, and one live probe run found **0 flapped rows** (gdelt still `rate_limited`), so the fresh snapshot was adopted rather than merged. The §3 audit, keyed on `(url, category)`, covered 709 of 724 non-gap rows with **0 inventory mismatches and 0 status drifts**; 7 stale claims were corrected (three `sec_edgar` cells asserting no probe row exists, two prose lines asserting fmp/finnhub/sec_edgar are absent, two inventory counts) and two wording-only cells were left alone. Verified independently: FMP authenticates by query param and finnhub/SEC by header, and no `ProbeResult` carries the value. `yfinance` remains catalogue-exempt (it is a keyless library, not an HTTP surface) | this review; llm §3 | — | 5 tests, including the credential-never-in-a-record check; `test_data_categories.py`'s exemption list trimmed to the three genuine exemptions | **landed** |

## B. LLM trading systems — the one reviewed category whose data layer is nearly satisfied

| # | Item | Source | Prereq | Acceptance | Status |
|---|---|---|---|---|---|
| B1 | News spine: ingest firm-specific news → NER-link to tickers → one-sided dedup (cosine > 0.8 against the prior 5 days, same firm) → score → recency-weighted firm-day aggregate. The encoder is the fork: a FinBERT-class local model needs `transformers`+`torch`, or start with the Loughran–McDonald dictionary as the document's own null arm | llm §5.1 | encoder decision (see C1) | transformer > dictionary ordering reproduced on a public post-cutoff window; the dictionary lands near 0.5 accuracy | needs-dep · M |
| B2 | Calibrated score object + long–short backtester: logit/softmax → calibrated score → daily rank → value-weighted top/bottom quintile, rebalancing only on quantile crossing | llm §5.2 | A2, B1 | costs and turnover move the ranking in the documented direction; a sign-permutation placebo collapses the Sharpe to ≈0 | blocked · M |
| B3 | Event-time gate | = A5 | — | = A5 | ready |
| B4 | Statistical-inference report block | = A1 + the shipped gate | — | = A1 | partly done |
| B5 | Event-driven biotech blueprint: link `fda_calendar`/earnings dates to press-release and filing text, score with a domain encoder, test 1/2/3-month holds by market-cap bucket | llm §5.5 | D2 for the text arm | event-day conditional accuracy beats a 5%-move momentum benchmark | needs-data · M |
| — | DPO + LoRA training in-house | llm §2.1, §5 "not recommended first" | labelled corpus + GPU | — | **not now** |

## C. RL trading agents — runtime decision taken (C1), the rest await authorization

C1 resolved as *keep the runtime set pure NumPy and enforce it*: the heavy stack
belongs in a separate environment, and no RL item below needs torch in this venv.
C2–C8 are therefore no longer blocked by the runtime; they are blocked by not
having been asked for. C2 is the first one worth taking, since it is the audit that
has to run before any other RL number is believed.

| # | Item | Source | Prereq | Acceptance | Status |
|---|---|---|---|---|---|
| C1 | **LANDED — decision: keep the runtime set pure NumPy; the heavy stack gets its own environment.** The decision is now enforced, not documented: red line 11 in `tests/audit/test_architecture.py` fails if `torch`, `tensorflow`, `jax`, `stable-baselines3`, `gymnasium`, `gym`, `scipy`, `scikit-learn` or `transformers` appears in `[project] dependencies`. The same red line also caught a real packaging defect while being written: numpy was imported by **13 first-party modules** (the gate, the simulation package, the strategy agent, the monte-carlo operator) and declared nowhere — it only arrived as a matplotlib extra, so a differently-resolved install would have broken the gate at import time. `numpy>=1.26` is now declared and `uv.lock` refreshed | this review | owner decision (taken: keep it out) | 2 tests; the audit file's docstring, which listed red lines 1–7 while 10 existed, now lists all eleven | **landed** |
| C2 | RL-vs-myopic walk-forward harness with the four-metric report: conditional mean PnL, variance, loss-side CVaR and probability of non-negative PnL, against a myopic baseline on identical clocks and costs. Needs no torch if the myopic baseline is a small convex program (note: `scipy` is absent; small QPs are numpy-tractable) | rl §5.1 | C1 | no result published without the baseline on the same split and clock | blocked · S |
| C3 | Look-ahead audit | = A6 | C1, C2 | = A6 | blocked |
| C4 | Inhomogeneous reward-volatility objective as a selectable risk term, with per-step targets and the IVO gradient | rl §5.3 | C1 | the policy family spans linear-to-front-loaded as the risk coefficient rises, which the homogeneous objective never does | blocked · M |
| C5 | Ensemble actor–critic selector (PPO+A2C+DDPG) with a separately reported turbulence kill-switch overlay | rl §5.4 | C1 | the reported ordering reproduces on 2016-01→2020-05 *with costs*; training stops at the test boundary — the source paper keeps training on its test period, which must not be copied | blocked · M |
| C6 | Two-threshold speculative entry/exit controller for pair spreads, with Gibbs exploration densities and an intensity cap | rl §5.5 | C1 | learned value functions match a finite-difference HJB solve on the same grid; residual concentrated at the free boundary | blocked · M |
| C7 | Manipulation-regime stress test (simulation-only, explicitly fenced): non-linear-impact environment, DDPG agent, full-information solver benchmark, estimated-parameter variant — used as a negative control on our own stack, never surfaced as a tradable signal | rl §5.6 | C1 | the volatility ordering reproduces; the reward carries an explicit no-manipulation penalty | blocked · M |
| C8 | Imitation+RL market-making skeleton, expert-first, validated on a Hawkes simulator before live data | rl §5.7 | C1, D1 | fine-tuned Sharpe beats the expert it was cloned from in every cell; training time ≤ 1.0× vanilla PPO | blocked · L |

## D. Data acquisition — the binding constraint the three documents share

| # | Item | Source | Prereq | Acceptance | Status |
|---|---|---|---|---|---|
| D1 | Register an order-level ingestion path as a first-class category (`order_book_depth`, `tick_trades`). Commercial candidates: Databento (Nasdaq TotalView-ITCH, nanosecond) and LOBSTER (academic 10-level LOB). Unblocks the strongest ABM calibration (10 LOB levels/side in arXiv:2208.13654), C7, C8 and both generative flow models | abm §3; rl §3 §5.8; llm §3 | owner decision + licence | one symbol-quarter loads and yields both signed metaorders and per-side arrival intensities | needs-data · L |
| D2 | Full text, where it is already free: SEC EDGAR full-text search (`efts.sec.gov`) and press releases carried as 8-K EX-99 exhibits, through the existing `sec_edgar`/`edgar_tools` provider. The honest residue is foreign private issuers (6-K/20-F) at Refinitiv scale with vendor entity IDs. The `llm-trading-systems.md` §3 row marks *all* full text a gap, which overstates what the repo can already fetch | llm §3 gap (ii) | A7 (probe row first) | a 10-K or 8-K body retrieves by full-text query and lands in the news spine | needs-owner · M |
| D3 | Delisting-adjusted total returns — without them a multi-thousand-firm news universe carries uncontrolled survivorship drift that no news provider fixes | llm §3 gap (iv) | licence | a delisted name's total return includes the terminal distribution | needs-data · M |
| D4 | LLM inference telemetry: per-article latency, GPU memory and cost. LLaMA-3-class needs 54.2 GB and 112 ms/article against FinBERT's 4.4 GB and 8.5 ms — a 13× gap that decides intraday vs end-of-day deployability | llm §3 gap (v) | B1 | a scored news run reports its own wall time and memory | needs-dep · S |

## E. Agent-based market simulation — self-contained code, no feed required

| # | Item | Source | Prereq | Acceptance | Status |
|---|---|---|---|---|---|
| E1 | **LANDED — decision: build, and record why.** Recorded in `engine/simulation/__init__.py`: ABIDES pins an older interpreter than this 3.14 venv and ABIDES-Gym needs `gym`/`gymnasium`, which red line 11 (see C1) keeps out of the runtime set — so adoption was not available, not merely unchosen. The honest downside is stated in the same docstring: ABIDES is battle-tested and scales to many assets, whereas this engine models only trader↔exchange latency and a single price-time-priority book. It is a calibration baseline, not a replacement | abm §2.1 §2.6 §5.1 §5.5 | C1 | the reason is recorded where the code lives, so the next person does not re-litigate it | **landed** |
| E2 | **LANDED.** `engine/simulation/stylized_facts.py`: `hill_tail_index`, `realized_volatility`, `return_autocorr`, `squared_return_autocorr` (3-lag smoothed over `{lag-1, lag, lag+1}`, with lag 0 excluded as it is 1.0 by construction), `block_bootstrap_weights`, `bootstrap_paths` and `coverage_matrix`. The band is the real point estimate ± a 95% block-bootstrap interval, which makes the identity case exact — a series against itself scores 1.0 — without a SciPy inverse normal | abm §2.2 §5.2 | — | acceptance is per cell, never an averaged loss; measured on i.i.d. noise against a heavy-tailed series, the Hill cell is the one that fails | **landed** |
| E3 | Demand block + fundamental generator: fundamental/momentum/noise/market-maker demand rules plus mean-reverting, OU and Kalman fundamental processes | abm §2.3–2.4 §5.3 | E2 | Hill/volatility/ACF coverage comparable to the source, knowingly failing the volume facts | needs-owner · M |
| E4 | Herding and belief-clearing module: Gaussian priors, logistic propensities, finite-speed diffusion on lattice/ER/WS graphs | abm §2.5 §5.4 | — | degree-8 converges faster than degree-4; kurtosis rises with herding intensity; joint dynamics overshoot then reverse | needs-owner · M |
| E5 | Scenario generator: POV sell algorithm, spiking trader, prominence-based amplitude, Monte Carlo quantiles | abm §2.7 §5.6 | E3; intraday volume profile | the non-monotone POV and inventory-limit curves reproduce, plus the ~80 bp mini crash | needs-owner · M |
| E6 | **LANDED.** `engine/simulation/{engine,agents,report}.py`: a discrete-event continuous-double-auction engine (min-heap queue, price-time priority, delay-the-send latency) with zero-intelligence agents, and `validation_report()`, which **raises** unless a ZI arm accompanies the simulated series. Every arm is measured on one shared moment set, and kurtosis is reported per arm (real / simulated / ZI) rather than for the model alone. Not implemented and named in the docstring: the Figgie card-game fixture and the §2.7 flash-crash scenario generator | abm §5.7 | E2 | 26 tests; verified independently that the same seed reproduces the path and that a bare simulated series raises | **landed** |
| E7 | RL-inside-simulator training loop (continual vs frozen vs untrained) | abm §2.6 §5.5 | E1, C1 | the continual group shows positive spread PnL and near-zero inventory; the training protocol is disclosed, because frozen, untrained and continual agents differ by 14× in kurtosis | blocked · L |

## F. Defects and inconsistencies found in this review

1. **RETRACTED — the two `alpha_vantage` rows are correct.** The first audit compared rows by URL alone, and
   Alpha Vantage serves four categories from one URL (`news_data`, `news_sentiment`, `fundamental_data`,
   `technical_indicators`), so the four inventory rows collapsed to whichever came last. Keyed on
   `(url, category)` they all match. All **66 §3 rows in the three documents are correct**, and a repeat of
   the audit across all 46 documents (724 non-gap rows) found no inventory mismatch either; the only
   differences are presentational — three older documents write enum names in uppercase (`CORE_STOCK_APIS`),
   `derivatives-options.md` writes `ok=true`/`ok=false`, several use prose statuses ("fail — HTTP 429"). No
   document edit is needed.
2. **`sec_edgar` has no probe row** — see A7. Effect: the SEC full-text path (`D2`) is unverified in the
   inventory while the documents cite it as available.
3. **`massive` is cited in all three §3 tables as `ok` but is in no category priority** — accurate about the
   probe, misleading about reachability. A finding to state in the documents, not a code defect: the registry
   documents unlisted keyed providers as deliberate.
4. **The Sharpe artifact** — a finite, meaningless metric reached the user; **fixed** (A4).
5. **`--auto` writes no ledger** — the app's own search output could not be validated; **fixed** (A3).
6. **The gate could not score a real search at all** — found by handing it the app's own ledger, and **fixed**. PBO computed every CSCV split's per-trial Sharpe with a helper that raised on any zero-dispersion column, and a 50-bar indicator warm-up makes the first block flat for *every* trial, while a sparse strategy is flat in most blocks: so `finrobot validate` refused every realistic ledger while passing 260 synthetic tests in which each trial moved on every bar. `pbo_cscv` now leaves undefined-in-this-subset trials out of that split's ranking, skips and counts splits with fewer than two rankable trials, and raises with block-coarsening advice only when nothing is rankable. Verified end to end: the app's own `--auto` ledger scores 15.0, **not sealed** — the correct verdict for a search on a 1-share sizer. This is the single most useful thing the live run produced, and no amount of unit testing would have found it, because the tests encoded the assumption that broke.
7. **The architectural audit suite is red on the committed tree, and CI does not run it.** `tests/audit/test_architecture.py` fails two of its own red lines: no `print` in `finrobot/` hits `probe.py:186,198` (the probe's table printer), and no `os.environ` outside `config.py` hits `env.py:8,73,141` (the env-var mapping module). Both are pre-existing — `env.py` is unchanged since `78d4707` and the same two `print` calls are in the committed `probe.py` — but `.github/workflows/desktop-ci.yml` runs `pytest tests/unit/` only, so nothing enforces them. Either the allowlists are too narrow (both files have a real claim to an exemption) or the code should move to `logging`/`get_settings`; that is a decision, not a cleanup. A guard that is red and unenforced is worse than no guard, because it teaches everyone to ignore the suite. Deliberately not fixed here: `probe.py` was being edited by another writer, and `env.py` is a config-layering change outside this work.

## G. Explicitly not now

- DPO/LoRA training in-house (llm §5).
- The manipulation agent and the FinFlowRL skeleton surfaced as anything other than fenced simulations
  (rl §5.6–5.7): the source's own point is that a model-free agent will find the impact externality if the
  reward admits it.
- Multi-asset ABM at the scale the source itself failed to hold: 30 assets / ~108,500 agents throttled to
  2,000 trades per 30 minutes because one SQLite gateway serialised order processing.

## Provenance of this review

- **Endpoint audit — and a correction to this document's first pass.** All 66 §3 rows in the three documents,
  then all 724 non-gap rows across the 46 documents, re-parsed and compared cell-by-cell against
  `strategies/endpoints.json` (49 rows / 14 providers). The first pass keyed rows by URL and reported two
  `alpha_vantage` mismatches; that was the audit's bug, not the documents' (§F1). Keyed on `(url, category)`
  there are none.
- **A second correction.** This backlog first listed White's reality check as missing from the gate. It is
  not — `spa_test` is the studentized-max reality check over a moving-block bootstrap, with Hansen's
  trimming. Only Diebold–Mariano and a reusable bootstrap CI are genuinely absent (A1).
- **Fix shipped with this document.** A4's Sharpe guard landed in the same change, verified against the
  measured separation (degenerate 1.4e-5 dispersion / raw -177.75 refused; invested 1.1e-2 / 2.566 kept).
- **What the smoke test found.** Running the documented `--auto` invocation for real, rather than only
  through mocks, showed the command could not start at all: it passed `model_name=None` to
  `FinRobotSettings`, which is a `str`, so pydantic rejected it before any work happened. Fixed in the same
  change as A3, with the conditional in one helper every `--model` command now shares. This is the argument
  for smoke-testing a path a test suite has "covered": the suite tested the search, not the command.
- **Verified independently of the tests**, for each delivered item: the DM sign convention and both coverage
  studies (i.i.d. and AR(1)); the cost grid's monotone erosion and winner flip; the ledger the agent writes
  scoring in the gate; the event-time boundaries (Friday 16:00 → Monday, pre-open → same session); the
  simulation's seed determinism and its refusal to report without a ZI arm; and the probe's credential
  placement.
- **Dependency audit** of `finrobot_desktop/.venv` (Python 3.14.0): `numpy`, `pandas`, `backtrader` present;
  `torch`, `stable-baselines3`, `gymnasium`, `transformers`, `scikit-learn`, `scipy` absent. This is what
  turns the RL document's "items 1–5 are buildable now" into C1: they are buildable in *principle*, on daily
  bars, but not in this environment as it stands.
- **One live run** for evidence: `finrobot backtest AAPL --start 2024-01-01 --end 2024-10-01 --strategy
  sma_crossover --params '{"fast":10,"slow":30}'` → 2 trades, `Sharpe Ratio -116.571`, 12m12s wall time.
- **Citations checked externally**: the arXiv ids in all three appendices resolve to live abstract pages
  (e.g. `2509.12764`), so every claim in these documents is traceable beyond the local PDF harvest.
- **Re-ranking note.** The source documents rank their own §5 by value-per-effort. Where the repo's actual
  state contradicts a "buildable now" claim — the RL stack — this backlog says so rather than repeating it.
