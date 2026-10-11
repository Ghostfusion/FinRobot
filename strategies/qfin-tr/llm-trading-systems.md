# LLM Trading Systems — learnings from the q-fin.TR corpus

`135` of 2370 corpus papers matched this category (135 with PDFs); this doc is based on a close reading of `6`.

Headline: **this category is the first in the portfolio whose data layer is almost entirely satisfied today.**
Every paper here starts from the same coarsest input FinRobot already fetches — firm-specific news plus
daily/intraday price and volume — and adds a *language model* between the text and the trade. The machinery
that changes versus classical sentiment is not the asset-pricing part (a daily value-weighted long–short
book from a text score is standard) but four things: **preference alignment as a substitute for supervised
fine-tuning**, **probability calibration of an LLM's own logits into a rankable score**, **contamination
control against the foundation model's pretraining window**, and **the operational cost/latency budget of
running the model over a news stream**. Classical dictionary/LM sentiment, event-study windows and
long–short construction are already derived in [`../qfin-st/news-sentiment-nlp.md`](../qfin-st/news-sentiment-nlp.md); this doc spends its space on what the decoder-only generation changes. Two of the six papers
(`2504.10789v1`, `2411.16585v1`) sit on the boundary with agent-based simulation and order-book modelling —
[`../qfin-st/market-simulation-agent-models.md`](../qfin-st/market-simulation-agent-models.md) and
[`../qfin-st/microstructure-execution.md`](../qfin-st/microstructure-execution.md) cover the counterpart
machinery — but both are retained because they use the *LLM as the generator* rather than the trade signal.

## 1. What the corpus actually offers

- **Preference alignment beats instruction tuning for financial sentiment, on a small corpus and one GPU.**
  FinDPO aligns Llama-3-8B-Instruct with Direct Preference Optimization over 32,970 labelled samples
  (Financial PhraseBank 4,840, Twitter Financial News 11,930, GPT-labelled Financial News 16,200; 80/20
  split), reaching weighted F1 **0.846** averaged over the three benchmarks versus 0.762 for FinGPT v3.3
  (+11%) and 0.771 for the same base model under supervised instruction tuning (FinSFT); per-dataset
  0.865/0.872/0.833. LoRA rank 16, α=16, dropout 0.05 gives 41.9M trainable parameters = **0.52%** of the
  base model, fitted in **4.5 h on a single A100 40 GB** over 5 epochs (arXiv:2507.18417).
- **The sentiment label itself is weak; the *probabilistic* score is what trades.** FinDPO's own
  contribution to portfolio construction is a "logit-to-score" converter — softmax over the first generated
  token's logits for the three valence classes — because causal LLMs emit discrete labels that cannot be
  ranked; the model was overconfident (probability 1.0/0.0) until temperature scaling was fitted by NLL on
  the *training* set (arXiv:2507.18417). This calibration was performed independently of the trading corpus
  to avoid leakage.
- **Decoder-only models dominate encoders on every axis, on a contamination-safe out-of-sample window.**
  MFAST evaluates six models on 190,236 news items from June 2024–January 2026 (post-dating the disclosed
  Llama-3 data-freshness cutoffs of March/December 2023): LLaMA-3-8B accuracy 0.787, F1 0.788, AUC 0.846,
  Brier 0.151, ECE 0.032; OPT-1.3B 0.763/0.763/0.821/0.166/0.041; RoBERTa 0.748; BERT 0.728;
  FinBERT 0.713; Loughran–McDonald dictionary 0.503 accuracy with ECE 0.143 — i.e. the dictionary is both
  weak *and* badly calibrated (arXiv:2609.23703).
- **The economic edge survives costs, capacity and multiple-testing correction — but only for the strongest
  models.** Net long–short Sharpe at 5 bps one-way cost: LLaMA-3 **2.85** (cumulative 180%, max drawdown
  −12.3%), OPT 2.45, RoBERTa 2.25, BERT 1.95, FinBERT 1.75, dictionary 0.68 (cumulative −9%); Nasdaq
  Composite benchmark 1.10. Significance: block-bootstrap Sharpe 95% CI [2.31, 3.34], White reality-check
  p=0.018, Hansen SPA p=0.026, deflated Sharpe 2.19 (p=0.014), Diebold–Mariano −7.12 (arXiv:2609.23703).
- **The edge is concentrated in linguistically hard news, which is the mechanism claim.** MFAST's
  stratified 1,200-article error analysis: LLaMA-3's accuracy *gain over the dictionary* is smallest on
  simple polarity (0.171) and largest on contrastive clauses (0.365), forward-looking guidance (0.335),
  negation (0.319) and event ambiguity (0.287) — exactly the categories where surface polarity is
  directionally wrong (arXiv:2609.23703).
- **Earlier, weaker evaluation produced the same ranking but larger, less credible numbers.** On 965,375
  Refinitiv articles (2010–2023, 6,214 firms, three-day excess-return labels, novelty filter at cosine
  ≥0.8 within 20 days), OPT-2.7B accuracy **0.744** vs BERT 0.725, FinBERT 0.722, dictionary 0.501; the
  next-day regression coefficient on OPT is 0.274 (t=5.37) with within-R² 0.021, while the dictionary is
  0.083 (t=1.87, insignificant). Value-weighted L/S Sharpe 3.05 at 10 bps and a **355%** gain over
  Aug 2021–Jul 2023 versus 0.91% for the dictionary (arXiv:2412.19245). The later framework shows the same
  ordering under a 5 bps assumption and stricter isolation, with materially smaller magnitudes
  (arXiv:2609.23703) — read the 355% as an upper bound under weaker controls.
- **Domain fine-tuning of a base model buys almost nothing over out-of-the-box FinBERT at this scale.**
  BioFinBERT (BioBERT fine-tuned on ~4,000 Financial PhraseBank samples, 3 epochs, lr 2e-5) scored
  validation F1 0.9104 but 62.86% event-level success on 105 biotech inflection events (2020–2023), while
  off-the-shelf FinBERT predicted **66.86% (66/105)** of the same press releases correctly; a larger mixed
  corpus (PhraseBank + FiQA, ~5,300 samples) did *worse* (F1 0.8240), and a hand-curated biotech set gave
  no improvement in trading (arXiv:2401.11011). This is the clearest negative result in the set.
- **LLM agents faithfully execute instructed strategies rather than maximising profit, and their
  interactions reproduce real market phenomena.** In a persistent order book with 8 heterogeneous GPT-4o
  agents (endowment 1,000,000 cash + 10,000 shares, fundamental value $28 from a $1.40 expected dividend at
  a 5% rate, dividend ±$1.00 at 50/50), price starting 100% above fundamental ($56) **failed to converge
  down** over 15 rounds while starting 50% below ($14) converged up — an asymmetry in correcting
  over- versus under-valuation. Systematic variation of the price-to-fundamental ratio ρ=P/V over
  [0.1, 3.5] maps each agent type's buy/sell/hold decision boundary (arXiv:2504.10789).
- **An autoregressive transformer can generate the order-flow stream itself.** MarketGPT tokenises Nasdaq
  TotalView-ITCH 5.0 messages into 24 tokens/message (vocab 12,111 = 12,012 + 98 symbols), a 768-dim,
  12-layer, 12-head, ~100M-param decoder pretrained on **91,124,274 messages (2,186,982,576 tokens)** across
  20 assets, and reproduces stylised facts in generated AAPL flow (T=135,813 messages): return excess
  kurtosis 4.93±1.99 vs empirical 2.44, DFA exponent α 0.73±0.02 vs 0.64, Hurst 0.77±0.05 vs 0.678 — but
  over-states persistence and under-predicts the spread (arXiv:2411.16585). One RTX 4090, ~7% of generated
  messages fail referential error-correction.
- **Off-topic check:** none of the six is off-topic. arXiv:2411.16585 is the weakest fit (it ends in a
  simulator, not a trade) but supplies the set's only generative order-flow engine; arXiv:2401.11011 is
  retained as the domain-fine-tuning negative control.

## 2. Implementable formulas & algorithms

### 2.1 Preference-optimised financial LLM (DPO + LoRA)
**Purpose.** Replace supervised instruction tuning of a causal LLM with human-preference alignment that
generalises to unseen events, on a small labelled corpus and a single commodity GPU.

**Formula.** With policy $\pi_\theta$ (trainable, LoRA adapters), frozen reference $\pi_{\rm ref}$, prompt
$\tilde x$ and preferred/dispreferred completions $y_w,y_l$:
$$\mathcal L_{\rm DPO}=-\mathbb E_{(\tilde x,y_w,y_l)}\Big[\log\sigma\Big(\beta\log\tfrac{\pi_\theta(y_w\mid\tilde x)}{\pi_{\rm ref}(y_w\mid\tilde x)}-\beta\log\tfrac{\pi_\theta(y_l\mid\tilde x)}{\pi_{\rm ref}(y_l\mid\tilde x)}\Big)\Big]$$
Preference pairs are built *synthetically* from ground-truth labels: $y_w$=true label; if the reference model
predicted correctly, $y_l$ is a random other class; if it predicted wrongly, $y_l$=that wrong prediction
(teaches away from the model's own errors).

**Required inputs.** Labelled financial sentiment corpora with a 3-class structure. FinDPO used Financial
PhraseBank (4,840), TFNS tweets (11,930), and a 5-class GPT-labelled news set collapsed to 3 classes
(16,200) — 32,970 total, 80/20. No market data required for training.

**Parameters & defaults.** Base Llama-3-8B-Instruct; LoRA $r{=}16$, $\alpha{=}16$, dropout 0.05; AdamW;
small initial lr (Llama-3 already pretrained), 10% warm-up, weight decay as regulariser; 5 epochs.
$\beta$ controls KL deviation from $\pi_{\rm ref}$ (defaults not tabulated; keep small). Cost: 4.5 h,
A100 40 GB, 41.9M trainable params (0.52%).

**Observed effect sizes.** Weighted F1 0.846 avg (0.865 / 0.872 / 0.833) vs FinSFT 0.771 and FinGPT v3.3
0.762; the same base model under instruction tuning matches an older Llama-2-13B model, so the gain is
attributable to DPO, not to scale. FinBERT excluded from FPB (leakage: trained on full FPB).

**Failure modes.** The synthetic dispreferred label can bias toward the model's own error distribution;
DPO on 3-class sentiment does not remove the need for calibration (§2.2); the 5-class→3-class collapse of
the NWGI set loses intensity information; dataset overlap between training corpora and the portfolio test
period is a leakage risk that must be audited explicitly.

### 2.2 Logit-to-score conversion and temperature calibration
**Purpose.** Turn a causal LLM's discrete valence prediction into a continuous, rankable sentiment score in
$[-1,1]$ suitable for portfolio weighting, and fix the systematic overconfidence that makes raw softmax
probabilities useless.

**Formula.** Over the logits $z$ at the *first generated token* for the class tokens
$\{$positive, negative, neutral$\}$:
$$S=\sum_{c\in\{\rm pos,neg,neu\}} w_c\,\mathrm{softmax}(z/T)_c,\qquad w=(+1,-1,0)$$
so a positive-sentiment view scores near $+1$ and a negative view near $-1$. $T$ is fitted post hoc by
minimising the negative log-likelihood on the *training* set only. Multiple same-day articles are averaged
per firm-day:
$$S_t=\frac{1}{N_t}\sum_{i=1}^{N_t}S_{it}$$
(FinDPO uses the simple mean; MFAST uses a recency-weighted mean of eligible article probabilities and
reports last-story and max-confidence variants.)

**Required inputs.** The model's logits/next-token distribution over the three class strings; article
timestamps and firm identifiers for the daily aggregation. FinDPO's article corpus: 204,017 articles
(Feb 2015–Jun 2021) linked to S&P 500 constituents by BERT-base-NER at a 98% confidence threshold, which
discarded 24.1% of scraped articles (552,598→419,368).

**Parameters & defaults.** $T$>1 (temperature scaling; value fitted, not fixed). NER threshold 0.98.
Long-short legs: top/bottom 35% of the ranked investable universe (417 companies with news coverage),
equal-weighted, daily rebalance. Risk-free rate $R_f{=}0$ (10Y yield near zero over the sample).

**Observed effect sizes.** Before calibration the model assigned probability 1.0 to the predicted class; the
converted scores enabled the FinDPO long-short book to reach cumulative 747.10% and Sharpe 3.41 at zero cost
(FinLlama 260.74%, Sharpe 2.33) — a 187% improvement in cumulative return over the prior state of the art.

**Failure modes.** Calibration must be fitted on data disjoint from the trading corpus (FinDPO fits on the
sentiment training set, not the article corpus); averaging same-day articles across a firm washes out
intraday timing; a 3-class softmax with a neutral mass makes the score scale-dependent on how the model
treats neutral, so cross-model score comparison is only valid after the same calibration.

### 2.3 Market-friction-aware sentiment-to-trading operator (MFAST)
**Purpose.** Convert timestamped text into *auditable, feasible* trades by making calibration, ranking,
execution timing, costs, capacity and statistical inference one pipeline rather than a backtest add-on.

**Formula.** For firm $i$, trading day $t$, model $m$: raw score $s^{(m)}_{i,t}=P_m(y_{i,t}=1\mid x_{i,t},\theta_m)$;
calibrated $s_e^{(m)}_{i,t}=g_m(s^{(m)}_{i,t})$ with $g_m$ a validation-set map; daily rank
$r^{(m)}_{i,t}=\mathrm{rank}_{i\in E_t}(s_e^{(m)}_{i,t})$ within the eligible universe $E_t$; participation cap
$|\Delta q_{i,t}|\le\lambda\,\mathrm{ADV}_{i,t}$; net return
$$R^{net}_{p,t}=R^{gross}_{p,t}-c\sum_i|\Delta w_{i,t}|$$
with value-weighted legs and weights that change only when a stock crosses a quantile threshold.

**Required inputs.** Timestamped firm-specific news; daily returns, bid/ask quotes, share and dollar volume,
market cap, and liquidity proxies (Amihud illiquidity, Kyle λ); model probabilities. MFAST's construction:
3,129,924 Refinitiv items → 1,985,135 single-firm → 1,122,475 after a five-day same-firm novelty screen
(cosine >0.80) → **973,481 tradable** items for 3,452 firms, after screens of positive quotes, ≥1,000 shares,
≥$50,000 dollar volume, quoted spread <20%, and non-missing $\lambda$/Amihud. Splits: train 2010–2023
(701,928), validation Jan–May 2024 (81,317), **test Jun 2024–Jan 2026 (190,236)**.

**Parameters & defaults.** 5 bps one-way cost (main specification); 10% daily-dollar-volume participation
cap; value-weighted; top/lowest quintile legs with threshold-crossing rebalancing; labels are the sign of the
cumulative 3-day excess return over the execution-aligned window $[e,e+2]$, where $e$ is the first eligible
trading day *after* observability is applied. Execution: pre-09:30 ET articles may trade the same day; all
intraday, after-close, weekend and holiday articles trade only from the next decision point.

**Observed effect sizes.** Net L/S Sharpe at 5 bps: 2.85 / 2.45 / 2.25 / 1.95 / 1.75 / 0.68 (LLaMA-3 / OPT /
RoBERTa / BERT / FinBERT / dictionary). Robustness: ranking stable for costs 0–50 bps, for decile/quintile/
tercile cutoffs, for 1/3/5-day holds, and after excluding the largest 50 stocks; factor-adjusted alphas
remain positive after market, size, value, profitability, investment and momentum controls.

**Failure modes.** Capacity binds first in small/illiquid names (value-weighting masks infeasible microcap
trades); the execution model is not a full order-book simulator, so intraday liquidity, queue position and
hidden liquidity are out of scope; the whole result depends on the novelty/dedup discipline — without it,
repeated wire updates mechanically multiply a firm's weight on one story.

### 2.4 Domain fine-tuning recipe and its negative control
**Purpose.** Adapt a base encoder to a sub-sector language (biomedical + financial) and test whether the
domain match actually improves sentiment-driven event trading.

**Formula.** Standard masked-LM fine-tuning with a 3-class head; the practical object is the *dataset mix*
and the *epoch/learning-rate* pair:
$$\text{BioFinBERT}=\text{BioBERT}\;\xrightarrow[\text{3 epochs, lr }2\times10^{-5}]{\text{Financial PhraseBank}};$$
comparison arms add FiQA (5 epochs, lr $6\times10^{-5}$, batch 16) or a hand-labelled biotech set
(~2,000 sentences from 96 BioPharma-Dive articles, 60% human / 40% GPT-3.5 pseudo-labelled).

**Required inputs.** A pre-existing labelled financial sentiment set; press-release PDFs and SEC filings
(10-Q/10-K for US, 6-K/20-F for foreign) around inflection events. BioFinBERT used 26 biotech names and
**105 events** in 2020–2023.

**Parameters & defaults.** 3–5 epochs (more than 10 overtrains); lr $2\times10^{-5}$ → $6\times10^{-5}$;
batch 16 (32 similar on T4). Event labels by market cap: large >±1%, mid >±2%, small >±3%, micro >±4%.

**Observed effect sizes.** FinBERT 66.86% (66/105) event-level accuracy; BioFinBERT 62.86% success with
validation F1 0.9104 (PhraseBank-only) but 0.8240 with the larger mix. Press releases were significantly
more predictive than prior/posterior 10-Q filings. Trading: 1-month hold best for micro-cap, 2-month best for
large-cap, 3-month best for small-cap (**300%** cumulative, Sharpe 1.31, 31% vol) against the NBI benchmark.

**Failure modes.** Validation F1 and event-level trading success are *decoupled* — a high-F1 model can trade
worse; curated small sets with pseudo-labels did not beat the generic corpus; the winner varied by market-cap
bucket, so a single "best" classifier is an average across regimes; the 105-event sample is too small for
strong inference.

### 2.5 LLM-agent market simulator with structured decision outputs
**Purpose.** Run financial-theory experiments (price discovery, bubbles, liquidity provision) with
natural-language agents instead of human subjects, and inspect how prompts generate correlated behaviour.

**Formula.** Each agent is a system prompt (strategy identity) plus a user prompt (market state, depth,
position, price history, fundamentals, action space). Decisions are forced into a validated schema
(Pydantic/function calling):
$$\text{decision}=(\texttt{valuation},\, \texttt{price\_target},\, \texttt{orders}[\,\cdot\,],\, \texttt{replace\_decision},\, \texttt{reasoning})$$
Order book mechanics: three-stage matching = (i) post non-crossing limit orders under price-time priority,
(ii) net market orders market-to-market, then market-to-book, (iii) convert residual market orders to
aggressive limits; partial fills tracked. Decision-boundary analysis is a partial-dependence scan:
vary $\rho=P/V$ over $[0.1,3.5]$ with the book held constant and record buy/sell/hold.

**Required inputs.** Synthetic market parameters only — the simulator is self-contained: fundamental value
$V=\mathbb E[D]/r$, dividend process, interest rate, endowments, agent population.

**Parameters & defaults.** 8 agents, 15–20 rounds baseline (stress scenario 100 rounds); endowment
1,000,000 cash + 10,000 shares; $V=\$28$ from $\mathbb E[D]=\$1.40$, $r=5\%$; dividend ±$1.00 at 50/50 each
round; zero transaction costs; GPT-4o; order submission randomised within a round to simulate concurrency.

**Observed effect sizes.** Qualitatively reported: value investors buy below and sell above $V$ with a sharp
$\rho$-boundary; momentum traders respond to recent trend, not $\rho$; prices converge up from 0.5×V but
**fail to converge down** from 2×V within 15 rounds; bubbles and underreaction emerge from agent
composition. No closed-form P&L table — the output is behavioural.

**Failure modes.** LLMs optimise for *instruction adherence, not profit* — they hold a strategy even when it
loses money, so results describe prompts, not rational agents; agents sharing one foundation model can move
in correlated ways, an unmodelled systemic-risk channel; discrete rounds (LLM latency) mean the "continuous"
auction is not continuous; zero costs remove frictions that matter live.

### 2.6 Autoregressive order-flow transformer for the LOB
**Purpose.** Generate the market-by-order message stream itself — a bottom-up simulator whose output is an
order flow with the correct stylised facts — for RL training, stress tests and ex-ante market-design studies.

**Formula.** Tokenise each pre-processed message (18 fields) into 24 tokens; a decoder-only transformer
$f_\theta$ maps the token sequence to logits $\hat y\in\mathbb R^{v}$; objective
$$\mathcal L=-\sum_i \log P(x_i\mid x_{<i}),\qquad P(x_i\mid x_{<i})=\mathrm{softmax}(\hat y)_i,\quad v=|\mathcal V|$$
Fields are made stationary per Nagy et al.: prices as ticks from the previous mid $p_{t-1}$, inter-arrival
times as features; rare values truncated (ticks beyond 999, sizes above 9,999). Long sequences use RoPE,
a rolling KV cache and a single **attention-sink** token; sampling is nucleus (top-p) not top-k, because the
optimal $k$ differs across token types.

**Required inputs.** A recorded L3 message archive: Nasdaq TotalView-ITCH 5.0, 6 train/1 val/1 test days,
six core fields (ns timestamp, type, order ID, direction, size, price) and five message types (add, execute,
execute-at-different-price, cancel, replace) at all book levels.

**Parameters & defaults.** 768 embedding dim, 12 layers, 12 heads, ~100M params; vocab 12,111 = 12,012 + 98
symbols; pretrain context $L{=}10{,}368$ tokens ($n{=}432$ messages), eval context reduced to $L{=}2{,}688$
with no measured loss; temperature **1.02** and top-p **0.98** (temperature >1 is required to stop
under-prediction of rare executions and large sizes).

**Observed effect sizes.** Pretraining set 91.1M messages / 2.19B tokens across 20 assets; eval sets
$T{=}135{,}813$ messages. Excess kurtosis 4.93±1.99 vs 2.44 empirical; DFA α 0.73±0.02 vs 0.64; power-law
decay γ 0.54±0.05 vs 0.72; Hurst 0.77±0.05 vs 0.678. Order-type frequencies roughly match but the model
over-predicts limit orders and under-predicts replace orders; ~7% of messages are hallucinated references
and discarded.

**Failure modes.** It never saw news, so it produces *plausible* not *predictive* trajectories; the
generated book lacks realistic liquidity (erratic best-bid/ask volume, spread under-predicted by a few
cents), distorting the return distribution; sampling parameters do not transfer across ticker-finetuned
models; inference is the bottleneck (24 tokens/message on one RTX 4090).

### 2.7 Contamination-safe evaluation protocol
**Purpose.** Make the measured edge credible when the signal comes from a foundation model that may already
have seen the news during pretraining, and when dozens of model/cost/cutoff combinations are compared.

**Formula.** Strict chronological isolation with label windows truncated at split boundaries (no return
label crosses a split); foundation-model exposure handled by a post-cutoff test start; and a battery of
falsification and multiplicity corrections:
$$\text{placebo: }\text{date-shuffle},\;\text{firm-shuffle},\;\text{sign-permutation}; \qquad
\text{corrections: }\text{DM},\;\text{White RC},\;\text{Hansen SPA},\;\text{DSR}$$

**Required inputs.** Known model release dates and disclosed pretraining data-freshness cutoffs; a held-out
post-cutoff window; the returns matrix; a pre-specified strategy family so the number of trials is countable.

**Parameters & defaults.** MFAST used the *stricter* Llama-3 family cutoff (Mar 2023 for 8B / Dec 2023 for
70B) and started the primary test on **June 1, 2024**, after the checkpoint's April 18, 2024 release; Jan–May
2024 is a validation/release-date buffer, reported as evidence for nothing. All models run as static
checkpoints with retrieval/browsing/tools disabled. Missing blocks are removed by a boundary duplicate audit
(same-firm cosine >0.80 across splits within 20 trading days → cluster backward).

**Observed effect sizes.** LLaMA-3 net L/S Sharpe 2.85, block-bootstrap CI [2.31, 3.34]; daily alpha
0.182% CI [0.109%, 0.252%]; DM −7.12 (p<0.001); White RC max stat 2.37 (p=0.018); Hansen SPA 2.21
(p=0.026); DSR 2.19 (p=0.014). Public replication (GDELT headlines → returns, 2019–2024, same post-release
rule) preserved the *ranking* but shrank magnitudes: LLaMA-3 accuracy 0.612, Sharpe 0.92, cumulative 41%.

**Failure modes.** No public model card proves the absence of *document-level* pretraining exposure, so the
protocol reduces rather than eliminates the risk; a public arm with noisier timestamps/entity matching is
not a substitute for the licensed sample; multiplicity corrections only work if the strategy family is
fixed *before* the test window — tuning on the test window voids them.

## 3. Data requirements → available endpoints

Provider rows are real entries in `strategies/endpoints.json`; **gap** means no current provider can supply
it. This category's text+price core is well served; the gaps are scale/linkage quality and L3 depth.

| Input | Endpoint | Category | Provider | Probe status |
|---|---|---|---|---|
| Firm-specific news articles (headline + body) | `https://eodhd.com/api/news` | `news_data` | eodhd | ok |
| News text (secondary) | `https://api.stockdata.org/v1/news/all` | `news_data` | stockdata | ok |
| News text (secondary) | `https://api.benzinga.com/api/v2/news` | `news_data` | benzinga | ok |
| News text (secondary) | `https://newsapi.org/v2/everything` | `news_data` | newsapi | ok |
| News + native sentiment tag | `https://www.alphavantage.co/query` | `news_data` | alpha_vantage | ok |
| Pre-scored news sentiment | `https://eodhd.com/api/sentiments` | `news_sentiment` | eodhd | ok |
| Pre-scored news sentiment | `https://www.alphavantage.co/query` | `news_sentiment` | alpha_vantage | ok |
| Global news-sentiment stream (public replication) | `https://api.gdeltproject.org/api/v2/doc/doc` | `news_sentiment` | gdelt | rate_limited (HTTP 429) |
| Daily OHLCV / returns | `https://eodhd.com/api/eod/AAPL` | `core_stock_apis` | eodhd | ok |
| Daily OHLCV (secondary) | `https://api.tiingo.com/tiingo/daily/AAPL/prices` | `core_stock_apis` | tiingo | ok |
| Daily/prev aggregate bars | `https://api.massive.com/v2/aggs/ticker/AAPL/prev` | `core_stock_apis` | massive | ok |
| Intraday bars (execution timing) | `https://api.twelvedata.com/time_series` | `core_stock_apis` | twelvedata | ok |
| Intraday K-line via local OpenD gateway | `moomoo://get_cur_kline` | `technical_indicators` | moomoo | gateway (not live-probed) |
| Tradable symbol universe | `https://eodhd.com/api/exchange-symbol-list/US` | `exchange_symbols` | eodhd | ok |
| Dividends (agent-simulator fundamentals) | `https://eodhd.com/api/div/AAPL` | `corporate_actions` | eodhd | ok |
| Earnings calendar (event windows) | `https://api.benzinga.com/api/v2.1/calendar/earnings` | `earnings_calendar` | benzinga | ok |
| Earnings-date price history | `moomoo://get_financials_earnings_price_history` | `earnings_catalyst` | moomoo | gateway (not live-probed) |
| FDA / clinical event calendar (biotech) | `https://api.benzinga.com/api/v2.1/calendar/fda` | `fda_calendar` | benzinga | ok |
| Guidance revisions (forward-looking text) | `https://api.benzinga.com/api/v2.1/calendar/guidance` | `guidance_revisions` | benzinga | ok |
| Fundamentals / statements | `https://api.tiingo.com/tiingo/fundamentals/AAPL/statements` | `fundamental_data` | tiingo | ok |
| Macro / interest-rate series | `https://api.stlouisfed.org/fred/series/observations` | `macro_data` | fred | ok |
| Risk-free curve (discount rate) | `https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2026/all` | `risk_free_curve` | federal_reserve | ok |
| Prediction-market odds (event sentiment) | `https://gamma-api.polymarket.com/markets` | `prediction_markets` | polymarket | ok |
| **Licensed, entity-linked, event-time news at Refinitiv scale with vendor firm IDs** | — | — | — | **gap** |
| **Full-text press releases and 10-Q/10-K/6-K/20-F documents** | — | — | — | **gap** |
| **L3 market-by-order message archive (ITCH/DBN) for the flow model** | — | — | — | **gap** |
| **Delisting-adjusted total returns (CRSP `DLRET`) for survivorship control** | — | — | — | **gap** |
| **LLM inference telemetry (per-article latency, GPU memory, cost)** | — | — | — | **gap** |

**What the gaps cost, quantified.** (i) *Licensed event-time news.* MFAST's proprietary arm needed 3.13M raw
items trimmed to 973,481 tradable, 190,236 in the 20-month test window; the public GDELT replication that
eodhd/stockdata/newsapi approximate preserved the model *ranking* but dropped headline accuracy to 0.612 and
Sharpe to 0.92 (vs 0.787 / 2.85), paid entirely for noisier timestamps and entity matching. (ii) *Full-text
documents.* BioFinBERT's study is 105 press releases and bracketing filings over 2020–2023; without full
text the "press releases beat 10-Qs" result is unbuildable, and a `fda_calendar` date alone is not a
sentiment input. (iii) *L3 archive.* MarketGPT consumed 91.1M messages / 2.19B tokens in 8 days over 20
names, full depth at every level (~$10^7$ messages/name/day); no news or bar endpoint substitutes.
(iv) *Delisting returns.* Without them a 3,452-firm 2010–2026 news universe carries uncontrolled survivorship
drift no news provider fixes. (v) *Inference telemetry.* LLaMA-3 needs 54.2 GB and 112.0 ms/article (8.9/s)
vs FinBERT 4.4 GB and 8.5 ms (117.6/s) — a 13× throughput gap deciding intraday vs end-of-day deployability.

## 4. Pitfalls, validation and measurement

- **Contamination is the dominant threat, and "no public model card" is not proof.** Do not report
  foundation-model test results on news published before the model's disclosed data-freshness cutoff; MFAST
  discards everything through 31 Dec 2023 even though the checkpoint shipped in Apr 2024, and starts the
  primary test on 1 Jun 2024 (arXiv:2609.23703). Run static checkpoints, retrieval/browsing off.
- **Pre-observation price movement.** A pre-09:30 ET article may trade the same day; an article released at
  or after 09:30, after the 16:00 close, on a weekend or holiday may only enter on the next decision point.
  Include the same-day return in labels only when the input was genuinely observable first
  (arXiv:2609.23703). A stricter robustness arm delays every signal a full trading day.
- **Event-date leakage via near-duplicates.** A budget item must never be assigned a label from a window
  that crosses a split. Use an *one-sided* novelty screen (cosine >0.80 to prior five-day same-firm stories;
  never use a future article to filter a past one) plus a cross-split boundary duplicate audit with a
  20-trading-day horizon (arXiv:2609.23703, arXiv:2412.19245).
- **Distinguish offline accuracy from implementable value.** A model can top a classification benchmark and
  lose money: BioFinBERT's higher validation F1 (0.9104) came with *lower* event-level success (62.86%) than
  off-the-shelf FinBERT (66.86%) (arXiv:2401.11011). And a signal with real gross alpha can be killed by
  turnover: MFAST's dictionary strategy returns −9% net at 5 bps while being ~chance-accurate
  (arXiv:2609.23703).
- **Cost assumption choice flips the conclusion.** FinDPO is the only method that stays profitable at 5 bps
  (annualised 66.64%, Sharpe 2.03) and every baseline turns negative at 4–5 bps; the same methods look
  uniformly strong at 0 bps (arXiv:2507.18417). Report the cost grid, not one number.
- **Multiple testing and specification search.** Fix the model/strategy family before touching the test
  window; then report block-bootstrap CIs, Diebold–Mariano, White reality-check, Hansen SPA and a deflated
  Sharpe ratio — MFAST's DSR of 2.19 (p=0.014) is the honest version of its 2.85 raw Sharpe
  (arXiv:2609.23703).
- **Liquidity/regime dependence is a mechanism, not noise.** The strongest models' predictive coefficients
  *increase* from high- to low-liquidity stocks, consistent with costly information processing — so a
  capacity-capped, value-weighted portfolio is required or the result is a microcap artefact
  (arXiv:2609.23703). For agent simulations, the asymmetry (2×V fails to revert, 0.5×V converges) is itself
  the finding: report both directions (arXiv:2504.10789).
- **Direction, not point accuracy, is the trading metric.** LLM sentiment regressions report next-day
  *coefficients* and within-R² (0.021–0.052), not price forecasts; treat R²≈0.05 with $t{=}6.4$ as the
  signal, never as a return forecast (arXiv:2609.23703, arXiv:2412.19245).
- **Generative-flow realism must be tested via stylised facts, and deviations are diagnostic.** Compare
  kurtosis, squared/absolute-return autocorrelation, DFA exponent and Hurst against the tape; a model that
  over-states persistence (α 0.73 vs 0.64) and under-predicts spread tells you its liquidity layer, not its
  language layer, is wrong (arXiv:2411.16585).

## 5. Recommended first implementation in FinRobot

Ordered by value-per-effort against what the layer can fetch today. Items 1–4 are buildable now; 5–6 need
one feed or a compute budget.

1. **From-text-to-daily-vector pipeline ("news spine").** *What:* ingest firm-specific news, NER-link to
   tickers, dedup with the one-sided cosine>0.8 / 5-day screen, score with a local encoder (FinBERT-class,
   no API cost), aggregate to a recency-weighted firm-day score. *Data:* eodhd `news` (+ eodhd `sentiments`
   as a free baseline), `exchange-symbol-list/US` for the universe. *Passing:* reproduces the MFAST *relative*
   ordering (transformer > dictionary) on a public post-cutoff window, with the dictionary scoring near 0.5
   accuracy and the transformer clearly above it. *Effort:* M.
2. **Calibrated score object + long-short backtester with a cost grid.** *What:* the logit/softmax →
   calibrated-score → daily-rank → value-weighted top/bottom-quintile book, run at 0/1/2/5/10 bps with a
   turnover term, rebalancing only on quantile crossing. *Data:* eodhd/massive/tiingo daily OHLCV. *Passing:*
   costs and turnover change the ranking in the expected direction (weak signals die by 4–5 bps; strong ones
   survive), and a sign-permutation placebo collapses the Sharpe to ~0. *Effort:* M.
3. **Event-time observability gate and contamination attribution.** *What:* an execution-timing module
   (pre-open vs intraday vs after-close vs weekend) and a per-article metadata field carrying the source
   model's release date + pretraining cutoff, so any reported metric can be restricted to post-cutoff
   articles. *Data:* eodhd `news` timestamps; a static table of model cutoffs. *Passing:* the reported
   Sharpe on a pre-2023 window is materially *higher* than on the post-cutoff window (the expected
   overstatement), demonstrating the gate works. *Effort:* S.
4. **Statistical-inference report block.** *What:* block-bootstrap Sharpe CI, DM test, White reality-check,
   Hansen SPA and deflated Sharpe as reusable functions around any backtest. *Data:* the strategy return
   series only. *Passing:* DSR < raw Sharpe and the CIs exclude zero for the signal, not for the placebo.
   *Effort:* S.
5. **Event-driven biotech blueprint (optional, high-variance).** *What:* link `fda_calendar` and earnings
   dates to press-release/10-Q text, score with a domain encoder, and test 1/2/3-month holds by market-cap
   bucket. *Data:* benzinga `fda_calendar`/`earnings_calendar`, daily bars. *Blocker:* full-text documents
   are a **gap** (see §3), so start with the calendar signal only. *Passing:* event-day conditional
   accuracy > the 5%-move momentum benchmark. *Effort:* M.
6. **Acquire a news/depth feed pair.** *What:* add a licensed event-time news feed with vendor entity IDs
   (to close gap i) and, if the flow simulator is in scope, an L3 archive (gap iii) registered as new data
   categories. *Value:* the licensed feed recovers roughly headline-accuracy 0.79 / Sharpe 2.85 versus the
   public-replication 0.61 / 0.92; the L3 archive is the only way to train the §2.6 generator. *Effort:* L.

**Not recommended first:** building the DPO training job (§2.1) in-house. Both DPO and agent-simulation
machinery are validated publicly and are gated on a labelled-corpus and compute cost that the news spine
(items 1–3) does not need; add DPO only once the spine's ranking is reproducible and calibration is the
binding constraint.

## Appendix — papers read

| arXiv id | Title | Year |
|---|---|---|
| 2507.18417v1 | FinDPO: Financial Sentiment Analysis for Algorithmic Trading through Preference Optimization of LLMs | 2025 |
| 2609.23703v1 | Financial Language Models as Applied Artificial Intelligence Systems for News-Based Trading under Market Frictions | 2026 |
| 2412.19245v1 | Sentiment trading with large language models | 2024 |
| 2401.11011v1 | BioFinBERT: Finetuning Large Language Models (LLMs) to Analyze Sentiment of Press Releases and Financial Text Around Inflection Points of Biotech Stocks | 2024 |
| 2504.10789v1 | Can Large Language Models Trade? Testing Financial Theories with LLM Agents in Market Simulations | 2025 |
| 2411.16585v1 | MarketGPT: Developing a Pre-trained transformer (GPT) for Modeling Financial Time Series | 2024 |
