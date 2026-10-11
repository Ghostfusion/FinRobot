# q-fin.TR — trading & market microstructure corpus

One of three sibling harvests indexed by the [strategies portfolio](../README.md). Source: an arXiv
`cat:q-fin.TR` harvest in `E:\fin paper2` — **2370 metadata records, 2359 PDFs** (11 papers were
unavailable at harvest: HTTP 404), 1997–2026.

Classification matched **1803/2370 (76%)** of the corpus to at least one of the **14**
categories below (title+abstract term sets, multi-label). 84 papers were read closely; each
document states its own reading list in its appendix. Claims are cited by arXiv id; endpoint rows are real
entries in the shared [endpoint inventory](../endpoints.json), and an input no provider can serve is marked
**gap**.

## Coverage

| Category | Corpus papers | With PDF | Read | Strategy document |
|---|---:|---:|---:|---|
| Limit-Order-Book Dynamics | 537 | 537 | 6 | [`limit-order-book-dynamics.md`](limit-order-book-dynamics.md) |
| Price Impact & Adverse Selection | 477 | 475 | 6 | [`price-impact-adverse-selection.md`](price-impact-adverse-selection.md) |
| Market Making & Liquidity Provision | 348 | 347 | 6 | [`market-making-liquidity.md`](market-making-liquidity.md) |
| High-Frequency Trading & Latency | 315 | 314 | 6 | [`high-frequency-latency.md`](high-frequency-latency.md) |
| Order Flow & Hawkes Processes | 303 | 302 | 6 | [`order-flow-hawkes.md`](order-flow-hawkes.md) |
| Crypto Exchange Microstructure | 273 | 273 | 6 | [`crypto-exchange-microstructure.md`](crypto-exchange-microstructure.md) |
| Optimal Execution & Liquidation | 244 | 241 | 6 | [`optimal-execution-liquidation.md`](optimal-execution-liquidation.md) |
| Agent-Based Market Simulation | 227 | 227 | 6 | [`agent-based-market-simulation.md`](agent-based-market-simulation.md) |
| Market Structure & Regulation | 200 | 200 | 6 | [`market-structure-regulation.md`](market-structure-regulation.md) |
| Reinforcement Learning Trading Agents | 193 | 191 | 6 | [`rl-trading-agents.md`](rl-trading-agents.md) |
| Market Games & Equilibrium Models | 138 | 138 | 6 | [`market-games-equilibrium.md`](market-games-equilibrium.md) |
| LLM Trading Systems | 135 | 135 | 6 | [`llm-trading-systems.md`](llm-trading-systems.md) |
| Statistical Arbitrage | 63 | 63 | 6 | [`statistical-arbitrage.md`](statistical-arbitrage.md) |
| Prediction Markets & Betting | 52 | 51 | 6 | [`prediction-markets-betting.md`](prediction-markets-betting.md) |
| **total unique papers classified** | **1803** | — | **84** | 14 documents + this index |

## Reading lens

This corpus is **microstructure/ML-trading** weighted — how trading *mechanically* works: books, liquidity, execution, latency. A category's paper count reflects corpus composition,
not commercial importance.

## Caveats

- Everything here is **literature-derived, not validated on FinRobot's own data**. Each document's §4 and
  §5 state how to test an implementation and what to build first.
- Data gaps are recorded **per document** as bold `gap` rows against the real endpoint inventory rather
  than assumed away.
- Counts are reproducible from `metadata.jsonl`: a paper counts as *with PDF* unless its id appears in
  `.state/unavailable.jsonl` (pre-2007 ids contain a slash and are stored with an underscore, so a naive
  filename test undercounts).
