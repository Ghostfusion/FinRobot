# q-fin.ST — statistical finance corpus

One of three sibling harvests indexed by the [strategies portfolio](../README.md). Source: an arXiv
`cat:q-fin.ST` harvest in `E:\fin paper` — **4372 metadata records, 4348 PDFs** (24 papers were
unavailable at harvest: HTTP 404), 1997–2026.

Classification matched **3435/4372 (79%)** of the corpus to at least one of the **16** categories below
(title+abstract term sets, multi-label). 99 papers were read closely; each document states its reading
list in its appendix. Claims are cited by arXiv id; endpoint rows are real entries in the shared
[endpoint inventory](../endpoints.json), and an input no provider can serve is marked **gap**.

## Coverage

| Category | Corpus papers | With PDF | Read | Strategy document |
|---|---:|---:|---:|---|
| Correlation Networks & Econophysics | 912 | 909 | 6 | [`correlation-networks-econophysics.md`](correlation-networks-econophysics.md) |
| ML Price Prediction | 736 | 731 | 6 | [`ml-price-prediction.md`](ml-price-prediction.md) |
| Crypto Assets | 723 | 720 | 6 | [`crypto-assets.md`](crypto-assets.md) |
| Microstructure & Execution | 600 | 599 | 6 | [`microstructure-execution.md`](microstructure-execution.md) |
| Econometrics & Forecasting | 512 | 508 | 9 | [`econometrics-forecasting.md`](econometrics-forecasting.md) |
| Mean-Reversion & Pairs Trading | 446 | 443 | 6 | [`mean-reversion-pairs.md`](mean-reversion-pairs.md) |
| Volatility Modeling | 442 | 441 | 6 | [`volatility-modeling.md`](volatility-modeling.md) |
| Risk Management & Tails | 426 | 426 | 6 | [`risk-management-tails.md`](risk-management-tails.md) |
| News Sentiment & NLP | 373 | 372 | 6 | [`news-sentiment-nlp.md`](news-sentiment-nlp.md) |
| Factor Models & Alpha | 256 | 252 | 6 | [`factor-models-alpha.md`](factor-models-alpha.md) |
| Derivatives & Options | 236 | 235 | 6 | [`derivatives-options.md`](derivatives-options.md) |
| Portfolio Optimization | 187 | 186 | 6 | [`portfolio-optimization.md`](portfolio-optimization.md) |
| Backtest Methodology | 185 | 183 | 6 | [`backtest-methodology.md`](backtest-methodology.md) |
| Regime Switching | 135 | 134 | 6 | [`regime-switching.md`](regime-switching.md) |
| Market Simulation & Agent Models | 109 | 109 | 6 | [`market-simulation-agent-models.md`](market-simulation-agent-models.md) |
| Earnings & Events | 45 | 45 | 6 | [`earnings-events-anomalies.md`](earnings-events-anomalies.md) |
| **total unique papers classified** | **3435** | — | **99** | 16 documents + this index |

## Reading lens

This corpus is **statistical/ML** weighted — volatility, regimes, factors, ML prediction and econophysics,
light on fundamental and discretionary strategy. A category's paper count reflects corpus composition, not
commercial importance.

## Caveats

- Everything here is **literature-derived, not validated on FinRobot's own data**. Each document's §4 and
  §5 state how to test an implementation and what to build first.
- Data gaps are recorded **per document** as bold `gap` rows against the real endpoint inventory rather
  than assumed away.
- Counts are reproducible from `metadata.jsonl`: a paper counts as *with PDF* unless its id appears in
  `.state/unavailable.jsonl` (pre-2007 ids contain a slash and are stored with an underscore, so a naive
  filename test undercounts).
