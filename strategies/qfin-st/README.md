# q-fin.ST — statistical finance corpus

One of three sibling harvests indexed by the [strategies portfolio](../README.md). Source: an arXiv
`cat:q-fin.ST` harvest in `E:\fin paper` — **4372 metadata records, 4348 PDFs** (24 papers were
unavailable at harvest: HTTP 404), 1997–2026.

Classification matched **3435/4372 (79%)** of the corpus to at least one of the **16** categories below
(title+abstract term sets, multi-label). 99 papers were read closely; each document states its own
reading list in its appendix. Claims are cited by arXiv id; endpoint rows are real entries in the shared
[endpoint inventory](../endpoints.json), and an input no provider can serve is marked **gap**.

## Coverage

| Category | Corpus papers | With PDF | Read | Strategy document |
|---|---:|---:|---:|---|
| correlation networks econophysics | 912 | 909 | 6 | [`correlation-networks-econophysics.md`](correlation-networks-econophysics.md) |
| ml price prediction | 736 | 731 | 6 | [`ml-price-prediction.md`](ml-price-prediction.md) |
| crypto assets | 723 | 720 | 6 | [`crypto-assets.md`](crypto-assets.md) |
| microstructure execution | 600 | 599 | 6 | [`microstructure-execution.md`](microstructure-execution.md) |
| econometrics forecasting | 512 | 508 | 9 | [`econometrics-forecasting.md`](econometrics-forecasting.md) |
| mean reversion pairs | 446 | 443 | 6 | [`mean-reversion-pairs.md`](mean-reversion-pairs.md) |
| volatility modeling | 442 | 441 | 6 | [`volatility-modeling.md`](volatility-modeling.md) |
| risk management tails | 426 | 426 | 6 | [`risk-management-tails.md`](risk-management-tails.md) |
| news sentiment nlp | 373 | 372 | 6 | [`news-sentiment-nlp.md`](news-sentiment-nlp.md) |
| factor models alpha | 256 | 252 | 6 | [`factor-models-alpha.md`](factor-models-alpha.md) |
| derivatives options | 236 | 235 | 6 | [`derivatives-options.md`](derivatives-options.md) |
| portfolio optimization | 187 | 186 | 6 | [`portfolio-optimization.md`](portfolio-optimization.md) |
| backtest methodology | 185 | 183 | 6 | [`backtest-methodology.md`](backtest-methodology.md) |
| regime switching | 135 | 134 | 6 | [`regime-switching.md`](regime-switching.md) |
| market simulation agent models | 109 | 109 | 6 | [`market-simulation-agent-models.md`](market-simulation-agent-models.md) |
| earnings events anomalies | 45 | 45 | 6 | [`earnings-events-anomalies.md`](earnings-events-anomalies.md) |
| **total unique papers classified** | **3435** | 3415 | **99** | 16 documents + this index |

## Caveats

- **q-fin.ST is statistical-finance weighted**: heavy on time series, ML and econophysics, light on
  fundamental and discretionary strategy. A category's paper count reflects corpus composition, not
  commercial importance.
- Everything here is **literature-derived, not validated on FinRobot's own data**. Each document's §4
  and §5 state how to test an implementation and what to build first.
- Several documents converge on the same hard data gaps — tick/L2 order-book history, crypto and
  on-chain data, point-in-time fundamentals, factor-return series. These are marked **gap** per document
  rather than silently assumed.
