# Skills plan — the 63 corpus documents against FinRobot's native skill system

Status of this pass: **2026-10-11.** Twenty-three corpus documents are converted and shipped as
agent skills — the twelve strongest of the first three corpora (§3) and eleven of the seventeen in
the fourth, `cat:q-fin.PR` (§7.1). The deferred, reference-only and overlap verdicts of §2, §4, §5
and §7.1 are recorded decisions, not a backlog. **79 skills ship**: 56 vendored plus 23
corpus-derived.

A corpus here is a set of literature reviews — what the finance papers say FinRobot should be able
to do — mapped input-by-input against the live endpoint inventory. A document becomes a
skill only when its own §3 table is mostly *served* rather than *gap*: a procedure whose core
inputs no provider can fetch would declare a capability nothing can fulfil.

## 1. How a document becomes a skill

`finrobot_desktop/scripts/convert_strategy_docs.py` maps the uniform section template every
document already follows onto the native skill body, so all 63 convert the same way:

| document section | becomes |
|---|---|
| `# Title — learnings from …` | frontmatter `name` |
| `## 1. What the corpus actually offers` | `## Core Principles` |
| `## 2. Implementable formulas & algorithms` | `## Methods & Formulas` |
| `## 3. Data requirements → available endpoints` | `## Data Requirements` **and** frontmatter `requires_data` |
| `## 4. Pitfalls, validation and measurement` | `## Pitfalls & Validation` |
| `## 5. Recommended first implementation in FinRobot` | `## Recommended Workflow` |
| `## Appendix — papers read` | `## References` |

Reviewed per-skill metadata — the description, triggers, persona and output format that a
machine cannot write — lives in [`skill_meta/<id>.yaml`](skill_meta/). Only documents with a
meta file convert by default, so the review tranche is explicit. **The documents are the
source of truth: edit the document, re-run the converter.**

```bash
cd finrobot_desktop
uv run --no-sync python scripts/convert_strategy_docs.py --check        # validate §3 vs endpoints.json
uv run --no-sync python scripts/convert_strategy_docs.py                # the reviewed tranche
uv run --no-sync python scripts/convert_strategy_docs.py --only <id>    # one document
uv run --no-sync python scripts/convert_strategy_docs.py --all --stdout # preview everything
```

`--check` parses all 63 §3 tables and reports every row the live inventory contradicts; it
currently exits clean (0 mismatches over 63 documents).

### Conventions

- **`requires_data`** is one entry per §3 row, with exactly four string keys —
  `input`, `provider`, `category`, `status`. It is the one frontmatter field no vendored skill
  populates, and the corpus's §3 tables are shaped exactly for it. `status` is one of:
  - `ok` — probe-verified HTTP endpoint,
  - `gateway` — served over the local OpenD gateway rather than HTTP (moomoo's rows),
  - `fail` — probe fails (rate-limited, auth, HTTP error),
  - `gap` — no provider serves the input,
  - `derived` — no provider serves it because the skill computes it from the others.
  A `gap` or `derived` row is **declared, not omitted** — the honesty is the point of the field.
- **`author: finrobot`** for corpus-derived skills, so they never blur with the 56 vendored
  `author: anthropic` ones.
- **`domain` is a grouping label only** — `SkillRegistry.search` scores on `triggers`, and
  `list_summary()` groups by domain. Granularity is therefore cosmetic; the split below
  follows the corpora's own categories rather than inventing a taxonomy.

## 2. Verdicts — the first three corpora, 46 documents

| corpus | document | verdict | domain |
|---|---|---|---|
| st | `volatility-modeling` | **skill** | `quant-research` |
| st | `regime-switching` | **skill** | `risk-management` |
| st | `risk-management-tails` | **skill** | `risk-management` |
| st | `portfolio-optimization` | **skill** | `portfolio-management` |
| st | `mean-reversion-pairs` | **skill** | `systematic-trading` |
| tr | `statistical-arbitrage` | **skill** | `systematic-trading` |
| st | `correlation-networks-econophysics` | **skill** | `quant-research` |
| st | `ml-price-prediction` | **skill** | `quant-research` |
| st | `news-sentiment-nlp` | **skill** | `news-sentiment` |
| st | `econometrics-forecasting` | **skill** | `macro-research` |
| tr | `optimal-execution-liquidation` | **skill** | `execution` |
| st | `earnings-events-anomalies` | **skill** | `equity-research` |
| st | `derivatives-options` | skill | `derivatives` |
| st | `market-simulation-agent-models` | skill | `market-simulation` |
| tr | `agent-based-market-simulation` | skill | `market-simulation` |
| tr | `llm-trading-systems` | skill | `news-sentiment` |
| tr | `rl-trading-agents` | skill | `quant-research` |
| tr | `market-games-equilibrium` | skill | `quant-research` |
| tr | `price-impact-adverse-selection` | skill | `market-microstructure` |
| tr | `market-structure-regulation` | skill | `market-microstructure` |
| tr | `market-making-liquidity` | skill | `defi` |
| tr | `high-frequency-latency` | skill | `quant-research` |
| tr | `prediction-markets-betting` | skill | `prediction-markets` |
| gn | `behavioral-decision-finance` | skill | `quant-research` |
| gn | `econophysics-methods` | skill | `quant-research` |
| gn | `asset-pricing-anomalies` | skill | `quant-research` |
| gn | `llm-ai-economic-agents` | skill | `quant-research` |
| gn | `energy-commodity-markets` | skill | `quant-research` |
| gn | `systemic-risk-crises` | skill | `risk-management` |
| gn | `pandemic-crisis-economics` | skill | `risk-management` |
| gn | `monetary-macro-policy` | skill | `macro-research` |
| gn | `household-inclusion-labor` | skill | `macro-research` |
| gn | `real-estate-housing` | skill | `macro-research` |
| gn | `corporate-finance-investment` | skill | `equity-research` |
| gn | `banking-credit-institutions` | skill | `financial-analysis` |
| st | `backtest-methodology` | **overlap → reference** | — |
| st | `crypto-assets` | **deferred** | — |
| st | `factor-models-alpha` | **deferred** | — |
| st | `microstructure-execution` | **deferred** | — |
| tr | `crypto-exchange-microstructure` | **deferred** | — |
| tr | `limit-order-book-dynamics` | **deferred** | — |
| tr | `order-flow-hawkes` | **deferred** | — |
| gn | `crypto-digital-economics` | **deferred** | — |
| gn | `trade-networks-complexity` | **deferred** | — |
| gn | `economic-growth-development` | **reference-only** | — |
| gn | `econophysics-wealth-income` | **reference-only** | — |

Totals: **35 skill · 8 deferred · 2 reference-only · 1 overlap.**

## 3. The first landed tranche — 12 skills

Chosen as the documents whose §3 inputs are entirely served and which no vendored skill
covers. Each is `finrobot_desktop/skills/<domain>/<id>/SKILL.md`:

| skill | notes |
|---|---|
| `volatility-modeling` | HAR/GARCH-family forecasting, QLIKE-first evaluation, regime-gated router |
| `regime-switching` | HMM / Markov-switching / change-point detection, regime-conditional risk |
| `risk-management-tails` | VaR/ES/CVaR, extreme-value tails, drawdowns, reverse stress |
| `portfolio-optimization` | mean-variance, shrinkage covariance, risk parity, Black-Litterman |
| `mean-reversion-pairs` | Engle-Granger/Johansen cointegration, OU half-life, z-thresholds |
| `statistical-arbitrage` | factor-neutral residuals, cross-sectional ranking, neutral book |
| `correlation-networks-econophysics` | correlation networks, MST, centrality, spectral denoising |
| `ml-price-prediction` | ML return prediction, walk-forward, leakage control, baseline compare |
| `news-sentiment-nlp` | news ingestion, entity linking, scoring, no-look-ahead aggregation |
| `econometrics-forecasting` | ARIMA/VAR/VECM, stationarity/cointegration tests, forecast evaluation |
| `optimal-execution-liquidation` | Almgren-Chriss, VWAP/TWAP, impact/risk trade-off |
| `earnings-events-anomalies` | event studies, CAR/BHAR, surprise, post-earnings drift |

**Landed:** all 12 of these, plus the eleven `qfin-pr` skills of §7.1 — **23 corpus-derived skills
in all**. **Convertible but not yet landed:** the remaining 23 documents of the first three
corpora, in the same shape — the converter emits them as soon as a `skill_meta/<id>.yaml` is
reviewed. Adopt in tranches: `list_summary()` is injected into the lead agent's instructions on
every run, so its size is a permanent context cost. At 79 skills it is 8,253 chars; the acceptance
test budgets ~120 chars per skill rather than a fixed total, so a new tranche fails only if
unusually verbose.

## 4. Deferred — 8 documents

Each is blocked by an input whose defining procedure cannot run without it. Deferred is not
rejected: author it once a feed exists, not before.

| document | blocked by |
|---|---|
| `crypto-assets` | crypto / on-chain price and network data |
| `crypto-exchange-microstructure` | event-level signed tape |
| `crypto-digital-economics` | on-chain, funding and mempool data |
| `factor-models-alpha` | factor-return series |
| `limit-order-book-dynamics` | L2 / market-by-order depth |
| `microstructure-execution` | L2 / market-by-order depth |
| `order-flow-hawkes` | event-level signed tape |
| `trade-networks-complexity` | a bilateral trade matrix |

Five feeds unblock all eight: **L2/market-by-order depth, event-level signed tape,
on-chain/funding/mempool data, factor-return series, a bilateral trade matrix.** This is the
same short list `strategies/TODO.md` §D1 records as the binding constraint.

## 5. Reference-only and overlap

- **`economic-growth-development`, `econophysics-wealth-income`** — long-run diagnostics with no
  procedure the app can run. They belong as `references/` material inside a macro skill, not as
  a `SKILL.md`.
- **`backtest-methodology` — overlap.** Its §5 states its own items 1–7 are already built, and
  they are: `scores.py`, `splits.py`, `ledger.py`, `overfitting.py`, `minerva.py`, `validate.py`
  in `finrobot/engine/backtest/validation/`. It is a specification of shipped code, so it
  converts to a *reference*, not a methodology skill. It is also the only document in the corpus
  carrying an "Implementation status" note — the precedent for how the others will age as the
  app implements them.

## 6. Caveats carried forward

- **Literature-derived, never validated on FinRobot's own data.** §4/§5 of each document is the
  testing plan; nothing here is a backtested strategy.
- The weakest verdicts: `derivatives-options` (partial overlap with the vendored
  `partner-lseg/option-vol-analysis`), `high-frequency-latency` (narrow), `market-making-liquidity`
  (DeFi pool-state bound) and `banking-credit-institutions` (depends on the single
  `fred/macro_data` row, so one endpoint outage makes it inert).
- Any generated skill referenced by a pipeline step must also be registered in
  `_PIPELINE_SAFE_METHODOLOGY`, or the unattended prompt receives a raw body. No landed skill is
  referenced by a pipeline today.
- The 56 vendored skills now declare their own `requires_data` / `requires_tools`. Eleven of them
  (`partner-lseg`, `partner-spglobal`) name MCP tools this app does not implement; that dependency
  is now declared rather than silent.

## 7. The q-fin.PR corpus — 17 more documents, eleven converted

`strategies/qfin-pr/` is a fourth harvest: `cat:q-fin.PR` (*Pricing of Securities*), 2274 records /
2250 PDFs, written in the same section template as the other three, so the converter in §1 handles
it unchanged. One document per category, 17 in all, each based on a close reading of 6 papers; the
coverage table and reading lens are in [`qfin-pr/README.md`](qfin-pr/README.md).

The verdicts in §2 cover the other three corpora; these 17 were reviewed separately, in §7.1.

Two facts about this corpus bear directly on that decision.

**The served share is far lower.** Across the 17 documents, 195 of the 334 declared §3 rows (58%)
are served by a real endpoint, against a corpus that is dominated by fixed-income, credit,
commodity and intraday inputs rather than equity prices and news.

| document | §3 rows | served | share |
|---|---:|---:|---:|
| `equilibrium-and-corporate-valuation` | 23 | 18 | 78% |
| `hedging-incomplete-markets` | 18 | 13 | 72% |
| `numerical-methods` | 14 | 10 | 71% |
| `stochastic-volatility` | 18 | 12 | 67% |
| `american-exotic-options` | 17 | 11 | 65% |
| `risk-and-optimal-decisions` | 19 | 12 | 63% |
| `mathematical-foundations` | 16 | 10 | 62% |
| `volatility-surface-calibration` | 15 | 9 | 60% |
| `credit-counterparty-risk` | 26 | 15 | 58% |
| `commodity-energy-derivatives` | 21 | 12 | 57% |
| `jump-and-levy` | 18 | 10 | 56% |
| `ml-and-neural-pricing` | 22 | 12 | 55% |
| `interest-rate-term-structure` | 19 | 10 | 53% |
| `market-microstructure-liquidity` | 19 | 10 | 53% |
| `option-pricing-foundations` | 19 | 9 | 47% |
| `crypto-digital-derivatives` | 22 | 10 | 45% |
| `insurance-mortality-linked` | 28 | 12 | 43% |

**But the share is a proxy, not the verdict.** `option-pricing-foundations` is among the
lowest-served yet its core — Black-Scholes, risk-neutral valuation, contingent claims — runs on the
SPX option chain plus the Treasury curve, both served; its gaps are secondary inputs (a long-history
option panel, a VIX series, intraday realized measures). Conversely `ml-and-neural-pricing` is 55%
served but several of its methods need `torch`, which the runtime set excludes by design (red line
11 in `finrobot_desktop/tests/audit/test_architecture.py`). Each document's §5 first item is the
honest test of what is buildable, so read that rather than the percentage.

**The blockers that span this corpus**, in the order that would unlock the most: credit spreads and
CDS, swap/swaption quotes, bond prices, futures and commodity curves, crypto prices and on-chain
records, and any intraday quote or order-book feed. These are the same gaps the other three corpora
converge on, arriving from the derivatives side.

One caveat on the taxonomy: `q-fin.PR` is a single arXiv category, so the 17-way split is analytic
(title+abstract term sets, multi-label, 93% of the corpus matched to at least one category), not
arXiv's own. Each document states its own member count and the 163 unmatched papers are stated
rather than hidden.

### 7.1 Conversion review

Each document was reviewed against the same criterion as §2 — the procedure must be executable on
data the layer actually serves, and must not duplicate an existing skill. Read the §5 first item,
not the served percentage: it is the honest test.

**Eleven of the seventeen pass; four are deferred on a missing market feed; two are overlaps.**

The pattern is the interesting part. The pricing categories convert *because pricing models need
little market data* — the delayed SPX chain, the Treasury curve and equity OHLCV carry them, even
where the §3 table is only half served. The four deferred documents are blocked for the opposite
reason: their subject *is* a market the app has no feed for. A thin §3 table is therefore not the
same as an unbuildable document, and the two must not be conflated.

| document | served | verdict | basis |
|---|---:|---|---|
| `option-pricing-foundations` | 47% | **convertible** | §5.1/5.2/5.5 read only the served Treasury curve and SPX chain; gaps are a long-history panel, a VIX series and intraday measures |
| `volatility-surface-calibration` | 60% | **convertible** | §5.1–5.3 invert and fit the served SPX chain; the model-free variance index needs nothing else |
| `stochastic-volatility` | 67% | **convertible** | §5.1 model-side on the served chain/curve; §5.2–5.3 need no data at all |
| `numerical-methods` | 71% | **convertible** | every §5 item is model-side or reads the served curve/chain; no external feed |
| `american-exotic-options` | 65% | **convertible** | §5.1–5.3 LSMC/Bermudan/barrier need only OHLCV plus the curve |
| `jump-and-levy` | 56% | **convertible** | §5.1–5.4 calibrate to the served SPX chain and daily OHLCV |
| `hedging-incomplete-markets` | 72% | **convertible** | §5.1–5.3 run on OHLCV plus the served SPX surface |
| `interest-rate-term-structure` | 53% | **convertible** | §5.1–5.4 use the served Treasury curve and SPX put-call parity; the swaption arm is `gap` and stays out |
| `equilibrium-and-corporate-valuation` | 78% | **convertible** | §5.1–5.3 use OHLCV, FRED and dividends — but partially overlaps the vendored `dcf-model` |
| `risk-and-optimal-decisions` | 63% | **convertible** | §5.1–5.3 run on the equity panel, chain and FRED; the risk-measure half overlaps `risk-management-tails` |
| `ml-and-neural-pricing` | 55% | **convertible** | the NumPy arm only (delta correction, no-transaction-band evaluation, LSMC); the `torch` arms are out of scope by red line 11 |
| `market-microstructure-liquidity` | 53% | **overlap** | §5.1–5.2 repeat `volatility-surface-calibration`'s chain harness and IV inversion; the depth/funding arms are `gap` |
| `mathematical-foundations` | 62% | **overlap** | the BSDE/Malliavin/robust-bound machinery duplicates `numerical-methods` and `hedging-incomplete-markets`, with no distinct data story |
| `credit-counterparty-risk` | 58% | **deferred** | the category's core is credit spreads and CDS, which nothing serves; only the Merton distance-to-default proxy is buildable |
| `commodity-energy-derivatives` | 57% | **deferred** | every core input — power, gas, temperature, carbon — is `gap` |
| `crypto-digital-derivatives` | 45% | **deferred** | the document itself concludes the category is blocked on data, not on models |
| `insurance-mortality-linked` | 43% | **deferred** | mortality tables, insurance loss data and credit spreads are all `gap` |

**All eleven are converted and shipped.** Each has a reviewed `strategies/skill_meta/<id>.yaml`
and a generated body under `finrobot_desktop/skills/`. One data story — the served SPX chain, the
Treasury curve, equity OHLCV — carries them into three new domain groups: six into `derivatives`
(`option-pricing-foundations`, `volatility-surface-calibration`, `stochastic-volatility`,
`jump-and-levy`, `american-exotic-options`, `hedging-incomplete-markets`), one into `fixed-income`
(`interest-rate-term-structure`), and `numerical-methods` and `ml-and-neural-pricing` into
`quant-research`, `equilibrium-and-corporate-valuation` into `equity-research`,
`risk-and-optimal-decisions` into `risk-management`. Their gaps are unchanged from §3 — the
tranche declares 74 `gap` rows in `requires_data` rather than hiding them.

The two overlap notes above were settled by scoping each sibling's *identity* and cutting the
trigger that would misroute a query. The Heston engine and its calibration live in
`stochastic-volatility`, while `volatility-surface-calibration` owns chain inversion, no-arbitrage
and the model-free variance index. The jump-family pricers and the Merton calibration live in
`jump-and-levy`, while `option-pricing-foundations` owns Black-Scholes, Greeks, implied-vol
extraction, replicability and discrete-hedging error. The same treatment gave `discount curve` to
`interest-rate-term-structure` while `put-call parity` stayed with `option-pricing-foundations`,
kept `indifference pricing` with `hedging-incomplete-markets` (leaving `utility indifference` to
`risk-and-optimal-decisions`), and kept plain-DCF framing out of
`equilibrium-and-corporate-valuation`, whose identity is the discount rate and valuation duration
the vendored `dcf-model` does not estimate.

`ml-and-neural-pricing` ships the NumPy arm only — the delta-correction regression, the
no-transaction-band evaluation and the LSMC module. Its persona states outright that the
deep-hedging network, the band *training*, the PINN, the deep-calibration scaffold and CARLOS are
not implemented, and the banned `torch` stack appears nowhere in the generated body.
