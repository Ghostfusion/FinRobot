# q-fin.PR — pricing of securities corpus

One of four sibling harvests indexed by the [strategies portfolio](../README.md). Source: an arXiv
`cat:q-fin.PR` harvest in `E:\fin paper4` — **2274 metadata records, 2250 PDFs** (24 papers were
unavailable at harvest: HTTP 404), 1997–2026.

Classification matched **2111/2274 (93%)** of the corpus to at least one of the **17** categories
below (title+abstract term sets, multi-label); the 163 unmatched papers are stated here rather than
hidden by a quota. 102 papers were read closely; each document states its reading list in its
appendix. Claims are cited by arXiv id; endpoint rows are real entries in the shared
[endpoint inventory](../endpoints.json), and an input no provider can serve is marked **gap**.

## Coverage

| Category | Corpus papers | With PDF | Read | Strategy document |
|---|---:|---:|---:|---|
| Option Pricing Foundations | 970 | 963 | 6 | [`option-pricing-foundations.md`](option-pricing-foundations.md) |
| Stochastic Volatility | 459 | 455 | 6 | [`stochastic-volatility.md`](stochastic-volatility.md) |
| Implied Volatility & Calibration | 450 | 444 | 6 | [`volatility-surface-calibration.md`](volatility-surface-calibration.md) |
| Hedging & Incomplete Markets | 424 | 419 | 6 | [`hedging-incomplete-markets.md`](hedging-incomplete-markets.md) |
| Numerical Pricing Methods | 394 | 392 | 6 | [`numerical-methods.md`](numerical-methods.md) |
| Credit & Counterparty Risk | 312 | 309 | 6 | [`credit-counterparty-risk.md`](credit-counterparty-risk.md) |
| Interest Rate & Term Structure | 303 | 301 | 6 | [`interest-rate-term-structure.md`](interest-rate-term-structure.md) |
| American & Exotic Options | 297 | 295 | 6 | [`american-exotic-options.md`](american-exotic-options.md) |
| Jumps & Lévy Processes | 261 | 261 | 6 | [`jump-and-levy.md`](jump-and-levy.md) |
| Equilibrium, Real Options & Corporate Valuation | 228 | 226 | 6 | [`equilibrium-and-corporate-valuation.md`](equilibrium-and-corporate-valuation.md) |
| Risk Measures, Capital & Optimal Decisions | 197 | 195 | 6 | [`risk-and-optimal-decisions.md`](risk-and-optimal-decisions.md) |
| Mathematical Foundations | 197 | 193 | 6 | [`mathematical-foundations.md`](mathematical-foundations.md) |
| Market Microstructure & Liquidity | 160 | 159 | 6 | [`market-microstructure-liquidity.md`](market-microstructure-liquidity.md) |
| Machine Learning for Pricing | 157 | 155 | 6 | [`ml-and-neural-pricing.md`](ml-and-neural-pricing.md) |
| Insurance & Mortality-Linked | 133 | 132 | 6 | [`insurance-mortality-linked.md`](insurance-mortality-linked.md) |
| Commodity & Energy Derivatives | 104 | 104 | 6 | [`commodity-energy-derivatives.md`](commodity-energy-derivatives.md) |
| Crypto & Digital Asset Derivatives | 52 | 51 | 6 | [`crypto-digital-derivatives.md`](crypto-digital-derivatives.md) |
| **total unique papers classified** | **2111** | — | **102** | 17 documents + this index |

## Reading lens

This corpus is **model-driven**: option pricing and its extensions, stochastic volatility, surface
calibration, hedging under frictions, interest-rate and credit modelling, numerical methods. It is
the *derivatives and mathematical-finance* complement to the other three corpora, and it overlaps
them only lightly — `q-fin.ST` ∩ PR = 104 papers, `q-fin.TR` ∩ PR = 81, `q-fin.GN` ∩ PR = 132; a
single paper appears in all four. A category's paper count reflects corpus composition, not
commercial importance.

Two consequences worth stating up front. First, the served data behind these documents is thin: a
single delayed SPX option chain (`cboe`), the Treasury curve (`federal_reserve`), macro series
(`fred`), equity OHLCV and a local gateway option chain (`moomoo`). Anything needing credit
spreads, swaps and swaptions, bond prices, futures, commodity or crypto prices is a recorded
**gap**, and several categories are honest about being blocked rather than convertible today.
Second, the runtime dependency set is pure NumPy by design (red line 11 in
`finrobot_desktop/tests/audit/test_architecture.py`), so Monte-Carlo, lattice and Fourier methods
are in scope while anything needing `torch` is not.

## Caveats

- Everything here is **literature-derived, not validated on FinRobot's own data**. Each document's
  §4 and §5 state how to test an implementation and what to build first.
- Data gaps are recorded **per document** as bold `gap` rows against the real endpoint inventory
  rather than assumed away.
- These documents follow the same section template as the other three corpora, so
  `finrobot_desktop/scripts/convert_strategy_docs.py` can convert any of them into an agent skill
  (see [`../SKILLS_PLAN.md`](../SKILLS_PLAN.md) for that track). None is converted yet.
- Counts are reproducible from `.state/metadata.jsonl`: a paper counts as *with PDF* unless its id
  appears in `.state/unavailable.jsonl`.
