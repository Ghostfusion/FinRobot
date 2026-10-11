# q-fin.GN — general finance corpus

One of three sibling harvests indexed by the [strategies portfolio](../README.md). Source: an arXiv
`cat:q-fin.GN` harvest in `E:\fin paper3` — **3095 metadata records, 3066 PDFs** (29 papers were
unavailable at harvest: HTTP 404), 1997–2026.

Classification matched **2423/3095 (78%)** of the corpus to at least one of the **16**
categories below (title+abstract term sets, multi-label). 96 papers were read closely; each
document states its own reading list in its appendix. Claims are cited by arXiv id; endpoint rows are real
entries in the shared [endpoint inventory](../endpoints.json), and an input no provider can serve is marked
**gap**.

## Coverage

| Category | Corpus papers | With PDF | Read | Strategy document |
|---|---:|---:|---:|---|
| Econophysics Methods | 509 | 506 | 6 | [`econophysics-methods.md`](econophysics-methods.md) |
| Trade Networks & Economic Complexity | 495 | 493 | 6 | [`trade-networks-complexity.md`](trade-networks-complexity.md) |
| Banking, Credit & Financial Institutions | 458 | 451 | 6 | [`banking-credit-institutions.md`](banking-credit-institutions.md) |
| Behavioral & Decision Finance | 384 | 379 | 6 | [`behavioral-decision-finance.md`](behavioral-decision-finance.md) |
| Asset Pricing & Anomalies | 350 | 348 | 6 | [`asset-pricing-anomalies.md`](asset-pricing-anomalies.md) |
| Monetary Policy & Macroeconomics | 345 | 341 | 6 | [`monetary-macro-policy.md`](monetary-macro-policy.md) |
| Wealth & Income Distribution | 309 | 308 | 6 | [`econophysics-wealth-income.md`](econophysics-wealth-income.md) |
| Corporate Finance & Investment | 303 | 299 | 6 | [`corporate-finance-investment.md`](corporate-finance-investment.md) |
| Economic Growth & Development | 287 | 280 | 6 | [`economic-growth-development.md`](economic-growth-development.md) |
| Household Finance, Inclusion & Labor | 281 | 277 | 6 | [`household-inclusion-labor.md`](household-inclusion-labor.md) |
| LLM & AI Economic Agents | 238 | 233 | 6 | [`llm-ai-economic-agents.md`](llm-ai-economic-agents.md) |
| Crypto & Digital Economics | 219 | 218 | 6 | [`crypto-digital-economics.md`](crypto-digital-economics.md) |
| Systemic Risk & Financial Crises | 188 | 187 | 6 | [`systemic-risk-crises.md`](systemic-risk-crises.md) |
| Real Estate & Housing | 104 | 104 | 6 | [`real-estate-housing.md`](real-estate-housing.md) |
| Energy & Commodity Markets | 97 | 96 | 6 | [`energy-commodity-markets.md`](energy-commodity-markets.md) |
| Pandemic & Crisis Economics | 57 | 55 | 6 | [`pandemic-crisis-economics.md`](pandemic-crisis-economics.md) |
| **total unique papers classified** | **2423** | — | **96** | 16 documents + this index |

## Reading lens

This corpus is **econophysics and macro** weighted — the economic environment: growth, credit, policy, distribution, econophysics. A category's paper count reflects corpus composition,
not commercial importance.

## Caveats

- Everything here is **literature-derived, not validated on FinRobot's own data**. Each document's §4 and
  §5 state how to test an implementation and what to build first.
- Data gaps are recorded **per document** as bold `gap` rows against the real endpoint inventory rather
  than assumed away.
- Counts are reproducible from `metadata.jsonl`: a paper counts as *with PDF* unless its id appears in
  `.state/unavailable.jsonl` (pre-2007 ids contain a slash and are stored with an underscore, so a naive
  filename test undercounts).
