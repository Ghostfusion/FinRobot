# Skills plan — the 46 corpus documents against FinRobot's native skill system

Status of this pass: **2026-10-11.** The twelve strongest documents are converted and
shipped as agent skills; the eight deferred, two reference-only and one overlap
verdicts below are recorded decisions, not a backlog.

The corpus is a set of literature reviews — what the finance papers say FinRobot should be
able to do — mapped input-by-input against the live endpoint inventory. A document becomes a
skill only when its own §3 table is mostly *served* rather than *gap*: a procedure whose core
inputs no provider can fetch would declare a capability nothing can fulfil.

## 1. How a document becomes a skill

`finrobot_desktop/scripts/convert_strategy_docs.py` maps the uniform section template every
document already follows onto the native skill body, so all 46 convert the same way:

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

`--check` parses all 46 §3 tables and reports every row the live inventory contradicts; it
currently exits clean (0 mismatches over 46 documents).

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

## 2. Verdicts — all 46 documents

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

## 3. The landed tranche — 12 skills

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

**Landed:** 12. **Convertible but not yet landed:** 23, in the same shape — the converter
emits them as soon as a `skill_meta/<id>.yaml` is reviewed. Adopt in tranches:
`list_summary()` is injected into the lead agent's instructions on every run, so its size is a
permanent context cost. At 68 skills it is 6,837 chars; the acceptance test budgets
~120 chars per skill rather than a fixed total, so a new tranche fails only if unusually verbose.

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
