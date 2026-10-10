# Strategies — research distilled from the q-fin.ST corpus

Implementable strategy knowledge for FinRobot, distilled from a local corpus of **arXiv `q-fin.ST`**
(Statistical Finance) papers, with every technique mapped onto data the project can actually fetch.

## Corpus and method

- **Source**: `E:\fin paper` — 4372 metadata records and 4348 downloaded PDFs
  (arXiv ids from 1997 through 2026; 24 records were unavailable at harvest time).
- **Classification**: each paper's title + abstract is matched, case-insensitively, against a term set
  per category below (multi-label — a paper may belong to several). **3435/4372 (79%) matched at least one** of the 16 categories.
- **Reading**: 6 papers per category (96 total) were selected by title-term match, breadth of focus
  (papers matching fewer categories rank higher) and recency, then read closely. Each document states
  the full category size, its own reading list, and cites claims by arXiv id.
- **Data mapping**: every input a technique needs is mapped to a **live-probed endpoint row** from
  [`endpoints.json`](endpoints.json) — provider, URL and probe status — and marked **gap** when no
  current provider can supply it.

## Coverage

| Category | Corpus papers | With PDF | Strategy document |
|---|---:|---:|---|
| correlation networks econophysics | 912 | 709 | [`correlation-networks-econophysics.md`](correlation-networks-econophysics.md) |
| ml price prediction | 736 | 721 | [`ml-price-prediction.md`](ml-price-prediction.md) |
| crypto assets | 723 | 665 | [`crypto-assets.md`](crypto-assets.md) |
| microstructure execution | 600 | 514 | [`microstructure-execution.md`](microstructure-execution.md) |
| econometrics forecasting | 512 | 476 | [`econometrics-forecasting.md`](econometrics-forecasting.md) |
| mean reversion pairs | 446 | 420 | [`mean-reversion-pairs.md`](mean-reversion-pairs.md) |
| volatility modeling | 442 | 393 | [`volatility-modeling.md`](volatility-modeling.md) |
| risk management tails | 426 | 406 | [`risk-management-tails.md`](risk-management-tails.md) |
| news sentiment nlp | 373 | 366 | [`news-sentiment-nlp.md`](news-sentiment-nlp.md) |
| factor models alpha | 256 | 246 | [`factor-models-alpha.md`](factor-models-alpha.md) |
| derivatives options | 236 | 203 | [`derivatives-options.md`](derivatives-options.md) |
| portfolio optimization | 187 | 171 | [`portfolio-optimization.md`](portfolio-optimization.md) |
| backtest methodology | 185 | 183 | [`backtest-methodology.md`](backtest-methodology.md) |
| regime switching | 135 | 130 | [`regime-switching.md`](regime-switching.md) |
| market simulation agent models | 109 | 97 | [`market-simulation-agent-models.md`](market-simulation-agent-models.md) |
| earnings events anomalies | 45 | 39 | [`earnings-events-anomalies.md`](earnings-events-anomalies.md) |
| **total unique papers classified** | **3435** | 3046 | 16 documents + this index |

## Provider endpoints

- [`data-endpoints.md`](data-endpoints.md) — the readable inventory: every catalog endpoint, its category,
  provider and live probe status.
- [`endpoints.json`](endpoints.json) — the same snapshot as data, as emitted by the probe.
- Regenerate with:

  ```bash
  cd finrobot_desktop
  uv run python -m finrobot.probe            # human table
  uv run python -m finrobot.probe --json     # machine-readable
  ```

  The probe exits non-zero when any endpoint fails, which is why a snapshot can show `auth`,
  `rate_limited` or `gateway` rows: those are findings, not errors. No credential value is ever
  emitted — the probe substitutes keys into request params/headers only.

## Caveats

- The corpus is **statistical-finance weighted**: methodologically heavy on time series, ML and
  econophysics, light on fundamental and discretionary strategy. A category's paper count reflects
  corpus composition, not commercial importance.
- Everything here is **literature-derived, not yet validated on FinRobot's own data**. Each document
  §4/§5 states how to test an implementation and what to build first.
- Several documents converge on the same hard data gaps: tick/L2 order-book history, crypto and
  on-chain data, point-in-time fundamentals, and factor-return series. Those are recorded per document
  as **gap**, not silently assumed.
