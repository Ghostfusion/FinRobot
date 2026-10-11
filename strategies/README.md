# Strategies — what the finance literature says FinRobot should be able to do

FinRobot's data layer exposes a fixed set of provider endpoints. These documents go the other way:
they read the academic literature, extract the techniques that are *implementable from data FinRobot
can actually fetch*, and mark the inputs no provider can serve as **gap**.

## The four corpora

Sibling arXiv harvests covering the four `q-fin` subcategories, all harvested with the same tool and
metadata schema, so they can be read the same way:

| Corpus | arXiv category | Sources | Records | PDFs | Categories | Documents |
|---|---|---|---:|---:|---:|---|
| statistical finance | `cat:q-fin.ST` | `E:\fin paper` | 4372 | 4348 | 16 | [`qfin-st/`](qfin-st/README.md) |
| trading & market microstructure | `cat:q-fin.TR` | `E:\fin paper2` | 2370 | 2359 | 14 | [`qfin-tr/`](qfin-tr/README.md) |
| general finance | `cat:q-fin.GN` | `E:\fin paper3` | 3095 | 3066 | 16 | [`qfin-gn/`](qfin-gn/README.md) |
| pricing of securities | `cat:q-fin.PR` | `E:\fin paper4` | 2274 | 2250 | 17 | [`qfin-pr/`](qfin-pr/README.md) |
| **unique papers** | | | **11126** | 11047 | 63 | 63 documents |

The corpora overlap only lightly, so each contributes genuinely distinct ground: `q-fin.ST` ∩ `q-fin.TR`
= 349 papers, `q-fin.ST` ∩ `q-fin.GN` = 237, `q-fin.TR` ∩ `q-fin.GN` = 136, all three = 20. The
`q-fin.PR` harvest is newer ground still — `q-fin.ST` ∩ PR = 104, `q-fin.TR` ∩ PR = 81,
`q-fin.GN` ∩ PR = 132, and exactly one paper appears in all four.

| Corpus | Reading lens | Papers classified |
|---|---|---:|
| q-fin.ST | statistical methods: volatility, regimes, factors, ML and econophysics | 3435/4372 (79%) |
| q-fin.TR | how trading *mechanically* works: books, liquidity, execution, latency | 1803/2370 (76%) |
| q-fin.GN | the economic environment: growth, credit, policy, distribution | 2423/3095 (78%) |
| q-fin.PR | pricing models: options, volatility, hedging, rates, credit, numerical methods | 2111/2274 (93%) |

## Method

1. **Classify cover-everything.** Every paper's title + abstract is matched against per-category term
   sets, case-insensitively and multi-label, so no paper is silently dropped — the unmatched share is
   stated in each corpus README rather than hidden by a quota.
2. **Read a small, stated sample.** Six papers per category (more where a category's sub-questions could
   not be covered otherwise) are picked by title-term match, breadth of focus and recency, then read
   closely. Each document's appendix lists exactly which papers it read.
3. **Cite by arXiv id.** Every quantitative claim carries the id it came from, so it can be checked.
4. **Map inputs to endpoints.** Each document's §3 table names, per required input, the real endpoint
   row that serves it — provider, category, probe status — or marks it **gap**.
5. **Say what to do first.** §5 ranks a first implementation for FinRobot, and §4 states how to validate
   it — the pitfalls the papers themselves report.
6. **Convert, when the inputs are served.** A document whose §3 table is mostly served converts to an
   agent skill via `finrobot_desktop/scripts/convert_strategy_docs.py`; the verdict for every one of the
   46 documents is in [`SKILLS_PLAN.md`](SKILLS_PLAN.md).

## Layout

```
strategies/
  README.md            # this index
  SKILLS_PLAN.md       # the 46 verdicts, and how a document converts to an agent skill
  skill_meta/<id>.yaml # reviewed per-skill metadata (description, triggers, persona, output)
  endpoints.json       # live probe snapshot of every provider endpoint (shared)
  data-endpoints.md    # the same snapshot, readable
  TODO.md              # backlog derived from the reviews (qfin-tr trio, so far)
  qfin-st/             # 16 docs from cat:q-fin.ST  (+ its own README)
  qfin-tr/             # 14 docs from cat:q-fin.TR  (+ its own README)
  qfin-gn/             # 16 docs from cat:q-fin.GN  (+ its own README)
  qfin-pr/             # 17 docs from cat:q-fin.PR  (+ its own README)
```

## The shared endpoint inventory

- [`data-endpoints.md`](data-endpoints.md) — every catalog endpoint with its category, provider and live
  probe status; the "needs attention" section explains each failure.
- [`endpoints.json`](endpoints.json) — the same snapshot as data, as emitted by the probe.

Regenerate after any adapter or catalog change:

```bash
cd finrobot_desktop
uv run python -m finrobot.probe            # human table
uv run python -m finrobot.probe --json     # machine-readable rows
```

The probe exits non-zero when any endpoint fails — by design. `auth`, `rate_limited`, `plan` and
`gateway` rows are findings, not errors: `gateway` means the provider is SDK-shaped and served over the
local OpenD gateway rather than HTTP. No credential value is ever emitted — the probe substitutes keys
into request params/headers only, and neither is part of the emitted record.

## Caveats

- These are **literature-derived, not validated on FinRobot's own data.** Nothing here is a
  backtested strategy; §4/§5 of each document is the testing plan.
- Paper counts reflect **corpus composition**, not commercial importance: `q-fin.ST` skews statistical,
  `q-fin.TR` skews microstructure/ML, `q-fin.GN` skews econophysics and macro.
- The gaps the documents converge on (tick/L2 order-book history, crypto and on-chain data,
  point-in-time fundamentals, factor-return series) are recorded per document, not assumed away.
