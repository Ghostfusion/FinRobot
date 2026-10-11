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

**Start here.** Already landed: `A4`, the Sharpe guard (§F4). Next smallest, needing no new dependency and
no new data: `A3` (`--auto` persists no ledger, so the shipped validation gate cannot score the app's own
output), then `E2` (stylized-facts harness: numpy only, no data) and `A5` (event-time gate: no model
needed). A first pass of this review also reported `F1`; that finding was wrong and is retracted (§F1).

## A. Shared infrastructure

| # | Item | Source | Prereq | Acceptance | Status |
|---|---|---|---|---|---|
| A1 | **LANDED.** `diebold_mariano()` (Newey–West HAC, Harvey–Leybourne–Newbold small-sample correction, squared or absolute loss, corpus sign convention) and `sharpe_confidence_interval()` (percentile moving-block bootstrap) in `validation/overfitting.py`, sharing the SPA test's resampler — so the two cannot drift on serial dependence. Measured, and reported in the API: coverage 0.955 at a nominal 0.95 on i.i.d. returns but **0.900 on an AR(1) φ=0.2**, so an autocorrelated series now carries an explicit warning instead of a quietly optimistic band | llm §5.4; rl §5.1 | — | 16 tests: sign convention, degeneracy, h-monotone HLN correction, the Newey–West default lag, two 200-replication coverage studies (i.i.d. and AR(1)), determinism, fail-closed paths | **landed** |
| A2 | Cost-grid runner: report every run at 0/1/2/5/10 bps with a turnover term instead of one frictionless number. `finrobot backtest` currently has no cost flag and only appends "assumes zero commission and zero slippage" (observed on a live run) | llm §4 §5.2; rl §4 | A3 for the per-trial return series | a weak signal dies by 4–5 bps and a strong one survives, on the same ledger; the CLI stops printing a single frictionless result | needs-owner · S |
| A3 | `--auto` persists a trial ledger, so `finrobot validate` can score the app's own search. `TrialLedger` and `build_ledger_from_search` already exist and are tested; `run_strategy_selection` never writes one | rl §5.1 ("no result without a baseline on the same split and clock"); this review | — | `finrobot backtest TICKER --auto` followed by `finrobot validate <ledger>` runs end to end on the app's own output | needs-owner · S |
| A4 | **LANDED.** The annualised Sharpe is withheld when the equity curve's daily-return dispersion falls below `MIN_DAILY_RETURN_STD` (1e-4), with the reason stated in the warnings. Cause: the built-in `sma_crossover` carries backtrader's default one-share sizer, so a $100k account holds ~0.2% exposure and the curve barely moves. Measured — dispersion 1.4e-5 and a raw ratio of **-177.75** for that configuration (the live -116.571 is the same mechanism); a fully invested position gives 1.1e-2 and keeps its 2.566 | this review | — | near-flat curve → `sharpe_ratio=None` + warning; `abs(Sharpe) < 5` still holds on the invested one-year case; 3 unit tests + 1 end-to-end regression | **landed** |
| A5 | Event-time observability gate + contamination metadata: pre-open / intraday / after-close / weekend execution timing, a per-article field carrying the source model's release date and pretraining cutoff, and the delay-every-signal-one-day robustness arm | llm §5.3 | — | reported Sharpe on a pre-2023 window is materially *higher* than on a post-cutoff window — the expected overstatement, which is how the gate is shown to work | ready · S |
| A6 | Look-ahead audit gate in any training loop: recompute the policy gradient with future information removed and reject a run whose contamination is not zero within bootstrap error | rl §5.2; llm §4 | C1 | the audit runs on the implemented objective and flags a deliberately leaky arm | blocked on C1 · M |
| A7 | Probe coverage. Only 14 of the 18 registry providers declare a module-level `ENDPOINTS`, and `probe_all` iterates the catalogue's keys — so `fmp`, `finnhub`, `sec_edgar` and `yfinance`, all of which `PRIORITY` routes to, are invisible to the probe. That includes `fmp`, the **first** choice for `core_stock_apis`, and `sec_edgar`, the only provider for `SEC_FILINGS` (already recorded as an inventory gap at `qfin-st/news-sentiment-nlp.md:260`). The inverse also holds: `massive` declares a catalogue and probes `ok`, but appears in no `PRIORITY` tuple, so no category routes to it, yet all three reviewed documents cite it as available | this review; llm §3 | — | the probe emits rows for those four; every §3 status cell re-checked against the new snapshot | needs-owner · M |

## B. LLM trading systems — the one reviewed category whose data layer is nearly satisfied

| # | Item | Source | Prereq | Acceptance | Status |
|---|---|---|---|---|---|
| B1 | News spine: ingest firm-specific news → NER-link to tickers → one-sided dedup (cosine > 0.8 against the prior 5 days, same firm) → score → recency-weighted firm-day aggregate. The encoder is the fork: a FinBERT-class local model needs `transformers`+`torch`, or start with the Loughran–McDonald dictionary as the document's own null arm | llm §5.1 | encoder decision (see C1) | transformer > dictionary ordering reproduced on a public post-cutoff window; the dictionary lands near 0.5 accuracy | needs-dep · M |
| B2 | Calibrated score object + long–short backtester: logit/softmax → calibrated score → daily rank → value-weighted top/bottom quintile, rebalancing only on quantile crossing | llm §5.2 | A2, B1 | costs and turnover move the ranking in the documented direction; a sign-permutation placebo collapses the Sharpe to ≈0 | blocked · M |
| B3 | Event-time gate | = A5 | — | = A5 | ready |
| B4 | Statistical-inference report block | = A1 + the shipped gate | — | = A1 | partly done |
| B5 | Event-driven biotech blueprint: link `fda_calendar`/earnings dates to press-release and filing text, score with a domain encoder, test 1/2/3-month holds by market-cap bucket | llm §5.5 | D2 for the text arm | event-day conditional accuracy beats a 5%-move momentum benchmark | needs-data · M |
| — | DPO + LoRA training in-house | llm §2.1, §5 "not recommended first" | labelled corpus + GPU | — | **not now** |

## C. RL trading agents — blocked on one runtime decision

| # | Item | Source | Prereq | Acceptance | Status |
|---|---|---|---|---|---|
| C1 | **Runtime decision (blocks every other RL row).** The venv is Python 3.14.0 and has no `torch`, `stable-baselines3`, `gymnasium`, `transformers`, `scikit-learn` or `scipy`; SB3 2.9.x declares support only through 3.13; and the desktop sidecar is PyInstaller-frozen (`package = ["pyinstaller>=6.10"]`), so a torch dependency must not enter the app's dependency set. Choose: a separate optional extra + separate environment, or keep the small nets pure-numpy | this review | owner decision | an RL extra that `uv sync` does not install for the app, with the frozen sidecar size unchanged | needs-owner · S |
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
| E1 | **Adopt-vs-build decision on the discrete-event engine.** ABIDES (JPMorgan; ACM SIGSIM 2020) and ABIDES-Gym (arXiv:2110.14771) already provide a discrete-event market with Gym environments — that covers this document's §2.1 engine *and* its §2.6 RL loop, where the document plans to build §2.1 from scratch. Verify the upstream Python pin (likely below 3.14) before choosing | abm §2.1 §2.6 §5.1 §5.5 | C1 for the Gym arm | either a one-asset ABIDES run reproduces a Figgie-style homogeneous-game null, or the build-from-scratch row is accepted with the reason recorded | needs-owner · S |
| E2 | Stylized-facts harness: Hill tail index, realised volatility, return and squared-return ACFs (3-lag smoothed), inverse-variance weights from a block bootstrap, and a coverage report | abm §2.2 §5.2 | — | the 9-moment × N-day coverage matrix on a real and a synthetic series. Acceptance is **per cell** — a 10% coverage cell on squared-return ACF(60) is a real failure — never an averaged loss | ready · S |
| E3 | Demand block + fundamental generator: fundamental/momentum/noise/market-maker demand rules plus mean-reverting, OU and Kalman fundamental processes | abm §2.3–2.4 §5.3 | E2 | Hill/volatility/ACF coverage comparable to the source, knowingly failing the volume facts | needs-owner · M |
| E4 | Herding and belief-clearing module: Gaussian priors, logistic propensities, finite-speed diffusion on lattice/ER/WS graphs | abm §2.5 §5.4 | — | degree-8 converges faster than degree-4; kurtosis rises with herding intensity; joint dynamics overshoot then reverse | needs-owner · M |
| E5 | Scenario generator: POV sell algorithm, spiking trader, prominence-based amplitude, Monte Carlo quantiles | abm §2.7 §5.6 | E3; intraday volume profile | the non-monotone POV and inventory-limit curves reproduce, plus the ~80 bp mini crash | needs-owner · M |
| E6 | Zero-intelligence control arm + validation report: the minimal agent set as a permanent null, one report printing coverage, kurtosis by group and the homogeneous-game null | abm §5.7 | E2 | every ABM result is reported against the ZI arm *and* real data on the same moments — a zero-intelligence market already reproduces six stylized facts, so the claim is only informative relative to that baseline | ready · S |
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
5. **`--auto` writes no ledger** — the app's own search output cannot be validated (A3).

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
