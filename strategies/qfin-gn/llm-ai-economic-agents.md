# LLM & AI Economic Agents — learnings from the q-fin.GN corpus

`238` of 3095 corpus papers matched this category (233 with PDFs); this doc is based on a close reading of `6`.

Headline: **three of the six papers measure what LLMs do to expectations and prices; two are classical ML/DL
pipelines that merely share the "AI" label; none produces a validated, cost-aware trading edge.** The only
end-to-end reproducible *strategy* in the set is a macro→sector-ETF ranking pipeline built on an echo-state
network (arXiv:2108.02838), which contains no language model. The LLM papers yield **audit primitives** instead —
extrapolation measurement, interval-calibration testing, a contamination protocol, and an SDID event-study
template — buildable today on the news/price layer. The AI-crypto and biotech-event *results* are not (§3).

## 1. What the corpus actually offers

- **LLMs over-extrapolate recent returns, more strongly than humans do.** Regressing a forecast rank on 12 weekly
  return lags (contest-clustered SEs) gives a first-lag coefficient $>10\times$ the second for GPT-4o vs
  $\approx3\times$ for human Forcerank players; the regression explains $R^2=35.2\%$ of GPT forecasts vs $3.4\%$ of
  human scores; human–GPT rank correlation $0.279$; fitted "degree of extrapolation" $\lambda_1(1-\lambda_2)$ is
  $38.1$ vs $12.09$. Sample: 1,283 weekly contests, 12,807 stock-contest observations, 200 tickers, 1,757
  participants. Realized returns show short-term *reversals* (negative coefficients on lags $t-1..t-4$, one
  significant), so the LLM ranking is negatively associated with next-week performance. The bias survives a change
  of modality (candlestick charts instead of CSVs) and of vendor: Claude 3.5 Sonnet's market sentiment regressed on
  ChatGPT's gives slope $0.81$, $R^2=0.603$ (correlation $0.78$) (arXiv:2409.11540).
- **LLM return forecasts are optimistic, and their 80% intervals are slightly worse than quoting historical
  percentiles.** Across 9,959 stock-months the mean GPT forecast is $2.2\%$ vs a prompt-supplied historical mean of
  $1.4\%$ and a realized next-month $1.1\%$; only $0.45\%$ of forecasts are negative. The stated 80% interval
  contains the realized value $76.9\%$ of the time — *less* than the $79.0\%$ obtained from the historical
  10th/90th percentiles — at width $23.4\%$ vs $25.5\%$; misses are asymmetric ($12.7\%$ above the High vs $10.4\%$
  below the Low), so the distribution is positively skewed. The human CFO benchmark achieved only $36\%$ coverage:
  the LLM is far better calibrated than humans yet still miscalibrated in the tails (arXiv:2409.11540).
- **The launch of a language model was itself a priced event.** Synthetic difference-in-differences around
  ChatGPT's 2022-11-30 release gives average treatment effects of $10.7\%$–$15.6\%$ over one month and
  $35.5\%$–$41.3\%$ over two months for 16 CoinGecko "AI" tokens against 15 large non-AI controls, and
  $5.7\%$–$6.9\%$ / $9.8\%$–$13.2\%$ for a broader 86-token CoinMarketCap cohort. Sample 2022-10-01…2023-01-31,
  $T_{pre}=60$, $T_{post}=66$; AI-token mean daily return $0.94\%$ vs control $0.13\%$, in a market the paper calls
  "fear"/"extreme fear". Plain DID was inconclusive because the parallel-trends test rejected or failed to reject
  depending on specification — the stated reason for switching to SDID (arXiv:2305.12739).
- **Retail attention, not institutional attention, priced the AI narrative.** In a panel fixed-effects model with a
  post-launch dummy, Google Trends changes in "AI"/"Artificial Intelligence"/"ChatGPT" load insignificantly before
  the launch and for non-AI assets, but significantly on AI assets after it ($\beta_4=0.09^{***}$, $0.07^{***}$,
  $0.11^{***}$; adjusted $R^2\le0.09$; $n=4{,}305$). A news-wire attention index from Refinitiv Eikon article counts
  and polarity is economically negligible ($\beta_4\le0.01$) (arXiv:2305.12739).
- **LLM agents obey instructions rather than optimise profit, and their interaction reproduces a known asymmetry.**
  In an open-source continuous double auction with 8 GPT-4o agents, partial fills and a persistent book
  (fundamental value $\$28$ from $E[D]=\$1.40$, $r=5\%$), a market starting $2\times$ fundamental ($\$56$) fails to
  converge down over 15 rounds while one starting $0.5\times$ ($\$14$) converges up: under-valuation is corrected,
  over-valuation is not. Sweeping $\rho=P/V$ over $[0.1,3.5]$ maps each agent type's buy/sell/hold boundary; value
  investors buy for $\rho<1$ and sell for $\rho>1$, momentum traders barely respond to $\rho$. No return, Sharpe or
  P&L table is reported (arXiv:2504.10789).
- **Domain fine-tuning of a sentiment model bought nothing.** BioBERT fine-tuned on ~4,000 Financial PhraseBank
  samples (3 epochs, lr $2\times10^{-5}$) reached validation F1 $0.9104$ but only $62.86\%$ event-level accuracy on
  105 biotech inflection events, while off-the-shelf FinBERT scored $66.86\%$ ($66/105$); a larger mixed corpus
  (PhraseBank + FiQA, ~5,300 samples) did *worse* (F1 $0.8240$). The trading test — hold 1/2/3 months after a
  positive event against the NASDAQ Biotechnology Index, 2020–2023 — gave its best number to small caps at 3 months
  (300% cumulative, 1.31 Sharpe, 31% vol), but on 1–90-day horizons the naive 5%-open-to-close benchmark beat both
  fine-tuned models on small/micro caps (arXiv:2401.11011).
- **Classical ML, not LLM: a cost-sensitive classifier beats logit on imbalanced deal status.** From 19,006 FactSet
  M&A deals (2001–2020, >\$1m, public targets) the paper keeps 17,440 after merging 121 days of daily target
  sentiment (52 numerical + 108 one-hot + 121 sentiment features), trains on 16,525 pre-2019 deals (~80% completed)
  and tests on 915 post-2019 deals (~79% completed). Logit reaches out-of-sample accuracy $83\%$ / recall $71\%$ /
  F1 $63\%$ / ROC-AUC $0.79$; SMOTE + FFNN with an F1 loss reaches $86\%$ / $73\%$ / $67\%$ / $0.81$. Adding the
  sentiment block did **not** improve accuracy, and the highest-recall variant collapsed precision to $33\%$
  (arXiv:2110.09315).
- **Classical ML, not LLM: an echo-state network beats LSTM/GRU/ridge for sector ranking.** Eight iShares sector
  ETFs, 4,862 daily / 233 monthly observations, 2000-07-14…2019-11-10; recursive feature elimination selects four
  macro features per sector; the two-year-ahead model with a five-year lookback gives in-sample annualized return
  $24.70\%$ / Sharpe $1.185$ / Calmar $0.786$ and out-of-sample $15.16\%$ / $1.480$ / $0.892$, against an
  equal-weight 8-ETF benchmark of $13.60\%$ / $1.200$ / $0.990$ (the same benchmark row in every table, i.e. one
  test window) (arXiv:2108.02838).
- **Off-topic check.** None of the six is off-topic, but the fit is uneven and flagged inline above.
  arXiv:2110.09315 and arXiv:2108.02838 contain no language model and no agent — retained as this category's two
  *AI-pipeline* papers, and because sector rotation is the only fully reproducible strategy here. arXiv:2305.12739
  uses an LLM as the **treatment**, not the estimator. The genuinely LLM papers are arXiv:2409.11540,
  arXiv:2504.10789 and arXiv:2401.11011.

## 2. Implementable formulas & algorithms

### 2.1 Return-extrapolation measurement for any forecast source
**Purpose.** Detect whether a model's return forecast (or rank) is a weighted average of past returns, quantify how
fast those weights decay, and check the resulting prediction's sign against known short-term reversal.

**Formula.** With $n$ weekly lags,
$$Y_{i,t}=\gamma_0+\sum_{s=1}^{n}\beta_s\,\text{Return}_{i,t-s}+\varepsilon_{i,t},
\qquad
Y_{i,t}=5.5+\lambda_1\sum_{s=0}^{n}w_s\,\text{Return}_{i,t-s}+\epsilon_{i,t},\quad
w_s=\frac{\lambda_2^{\,s}}{\sum_{j=0}^{n}\lambda_2^{\,j}}$$
$$\text{DoE}=\lambda_1\,(1-\lambda_2),\qquad
\text{Return}^{\pm}_{i,t-s}=\max(\text{Return}_{i,t-s},0)\ \text{or}\ \min(\cdot,0)$$
$\lambda_2$ is the relative weighting of recent vs distant returns ($\lambda_2\to0$ = pure recency); $\lambda_1$ is
the level. Asymmetry is tested on the split series $\text{Return}^{\pm}$; predictive sign by Fama–MacBeth
regressions of next-period daily returns on the fitted value (Predicted) and the residual (Residual) of Eq. (1),
plus controls (log market cap, log book-to-market, asset growth, gross profits/assets, beta, weekly turnover, max
daily return last month).

**Required inputs.** $n=12$ (24 as robustness) trailing weekly returns per name; the model's forecast rank/score
for the same cross-section; next-period realized returns.

**Parameters & defaults.** 12 lags, contest-clustered SEs, GPT-4o, prompts carrying **only numeric
returns** with no tickers or firm names, JSON output, rank 1 = highest. Confidence is elicited but adjusting
forecasts by it changed nothing (mean $0.73$, sd $0.15$).

**Observed effect sizes.** $\beta_1/\beta_2>10$ (GPT) vs $\approx3$ (humans); $R^2=0.352$ vs $0.034$; rank
correlation $0.279$; DoE $38.1$ vs $12.09$; the extrapolative component (Predicted) is the part most robustly
*negatively* related to future returns (arXiv:2409.11540).

**Failure modes.** Pretraining contamination dominates (§2.3). Eq. (1) explains only $38\%$ of the forecast, so
decompose Predicted vs Residual before concluding "the signal is inverted"; ranks are ordinal, so inference is
cross-sectional only.

### 2.2 Interval-calibration audit of stated confidence
**Purpose.** Test whether a model's 80% forecast interval is an 80% interval, and separate level bias from tail bias.

**Formula.**
$$\text{Coverage}=\frac{1}{N}\sum_i \mathbf{1}\{r_{i,t+1}\in[L_i,H_i]\},\qquad \text{nominal}=0.80$$
$$\text{Upside miss}=\frac{1}{N}\sum_i\mathbf{1}\{r_{i,t+1}>H_i\},\qquad
\text{Downside miss}=\frac{1}{N}\sum_i\mathbf{1}\{r_{i,t+1}<L_i\}$$
Benchmark coverage uses the historical 10th/90th percentiles of the *same* prompt window; width $(H_i-L_i)$ is
compared with the historical inter-decile range. A third check regresses each of $\{L_i,E_i,H_i\}$ on the nine
historical percentiles $\text{Ret}^{10\%},\dots,\text{Ret}^{90\%}$ (plus min/max) to expose symmetry assumptions.

**Required inputs.** Up to 10 years (minimum 5) of monthly returns per asset; a prompt asking for the 10th
percentile, expected return and 90th percentile as JSON.

**Parameters & defaults.** 10,000 randomly drawn stock-months (100 months × 100 stocks, 10 per size decile), 9,959
after the history filter; monthly horizon.

**Observed effect sizes.** Coverage $76.9\%$ vs the $79.0\%$ historical-decile benchmark and $36\%$ for human CFOs;
width $23.4\%$ vs $25.5\%$; $12.7\%$ / $10.4\%$ asymmetric misses; $0.45\%$ of forecasts below zero; mean $2.2\%$
vs historical $1.4\%$ vs realized $1.1\%$. The expected-return regression loads largest on the 90th percentile,
while the High forecast is less sensitive to high percentiles than the Low forecast is to low ones — tail pessimism
with level optimism (arXiv:2409.11540).

**Failure modes.** Cost scales with $N$ (≈10k calls per study). The model truncates at zero, so coverage alone
hides skew; beating humans is not being calibrated.

### 2.3 Contamination and reproducibility protocol for prompt-based signals
**Purpose.** Stop a prompt pipeline from scoring the future it already memorised, and make it re-runnable.

**Formula.** A run is admissible only if the evaluation date follows the model cutoff, the statistic is invariant
to the prompt wrapper, and it replicates across model families:
$$\text{admissible}=\mathbf{1}\{t_{eval}>t_{cutoff}\}\cdot
\mathbf{1}\{|\hat\theta_{\text{persona}}-\hat\theta_{\text{base}}|<\varepsilon\}\cdot
\mathbf{1}\{\rho(\hat\theta_A,\hat\theta_B)>\rho_{\min}\}$$
where $\hat\theta$ is the measured statistic (e.g. the $\lambda$ pair of §2.1) and $\rho$ the cross-family correlation.

**Required inputs.** The numeric payload, the prompt text, a pinned model version string, and two independently
trained model families.

**Parameters & defaults.** Anonymised 10×12 weekly / 10×120 monthly return grids; persona preamble "You are a
sophisticated Hedge Fund investor"; $\varepsilon$ set to the statistic's sampling noise; $\rho_{\min}=0.78$ from
the paper's cross-family benchmark.

**Protocol (composed from the papers' own defences).**
1. **Anonymise the payload.** Numeric series only, no tickers, dates or firm identifiers (arXiv:2409.11540 uses a
   10×12 grid of weekly returns and a 10×120 grid of monthly returns).
2. **Cutoff audit.** For every evaluation date $t$, compare it with the model's training cutoff; a "forecast" of an
   event preceding the cutoff is a *recall* test. Fatal for arXiv:2305.12739-style studies: the ChatGPT launch is
   inside the knowledge window, so an LLM asked about AI tokens after Nov-2022 is contaminated by construction.
3. **Cross-family replication.** Re-run the identical prompt on an independently trained model and require
   agreement of the coefficient pattern, not just the level (arXiv:2409.11540: slope $0.81$, correlation $0.78$).
4. **Prompt-invariance null.** Vary the persona preamble and check the statistic is unchanged; the paper's test —
   prefixing "You are a sophisticated Hedge Fund investor" — had *negligible* effect, so persona-level debiasing
   must not be counted as a fix.
5. **Pin the artefacts.** Model name *and* version (GPT-4o, Claude 3.5 Sonnet), decoding parameters, prompt text
   and response schema, stored with the run.

**Observed effect sizes.** Correlation $0.78$ across families; persona-preamble effect negligible; the S&P 500
sentiment measure ($-1/0/+1$) averaged $0.37$ over 438 AAII-matched monthly observations whose own bull–bear spread
averaged $6.5\%$ (arXiv:2409.11540).

**Failure modes.** Cross-family agreement is *not* correctness — both models can inherit the same human bias.
Anonymisation removes identifiers but not the return history that identifies the period. Temperature, seed and
provider-side updates are uncontrolled; a pipeline that cannot pin them is a research artefact, not a signal.

### 2.4 Synthetic difference-in-differences for a technology shock
**Purpose.** Estimate the causal return effect of a discrete event (a product launch, a regulation, a listing) on a
cohort of assets when parallel trends are not credible.

**Formula.** With outcome $R_{it}$ (daily log return) and binary treatment $GPT_{it}=1$ after the event,
$$(\hat\tau^{sdid},\hat\mu,\hat\alpha,\hat\beta)=\operatorname*{arg\,min}_{\tau,\mu,\alpha,\beta}
\sum_{i=1}^{N}\sum_{t=1}^{T}\big(R_{it}-\mu-\alpha_i-\beta_t-GPT_{it}\tau\big)^2\,\hat\omega_i^{sdid}\hat\lambda_t^{sdid}$$
where the unit weights solve a regularised balance problem and the time weights a symmetric one without a
regulariser; covariates enter by residualisation, $R^{res}_{it}=R_{it}-\hat\beta_1 Cap_{it}-\hat\beta_2 Vol_{it}$.

**Required inputs.** A strictly balanced panel of daily log returns for treated and control assets; a binary
treatment date; log volume and log market cap; ≥ as many controls as treated.

**Parameters & defaults.** $T_{pre}=60$, $T_{post}=66$; 500 bootstrap replications for SEs; assets with daily volume
below \$20,000 excluded; 15 controls for the 16-asset CoinGecko cohort, 85 for the 86-asset CoinMarketCap cohort.

**Observed effect sizes.** SDID $0.11151^{*}$ (1 month) and $0.36416^{***}$ (2 months) for the narrow cohort;
$0.05714^{**}$ and $0.11128^{***}$ for the broad cohort; index-control variants $0.15600^{**}$ / $0.14022^{***}$.
DID on the same data gave $0.08481$ (ns) and $0.32139^{***}$ (arXiv:2305.12739).

**Failure modes.** DID parallel-trends $p$-values spanned $0.0002$–$0.91$, so the "significant" DID result is
specification-dependent — report both estimators. No placebo date is reported; a sector-wide AI rally coincident
with the launch would be absorbed into $\tau$. The ATT is a 125-day bear-market average.

### 2.5 LLM-agent policy sweep in a simulated order book
**Purpose.** Map how a prompt-defined agent reacts to mispricing, and generate endogenous market behaviour
(bubbles, liquidity provision) that historical replay cannot produce.

**Formula.** With fundamental value $V=E[D]/r$ (infinite horizon) or
$V_t=\sum_{\tau=t}^{T}E[D]/(1+r)^{\tau-t+1}+K/(1+r)^{T-t+1}$ with $K=E[D]/r$ (finite), the sweep parameter is
$$\rho=\frac{P}{V}$$
For each $\rho\in[0.1,3.5]$: set $P=\rho V$, rebuild a consistent book, run multiple decision trials per agent
type, record $\{$buy, sell, hold$\}$, order type, quantity, limit price. Agents return a validated schema
(`valuation_reasoning`, `valuation`, `price_target`, `orders[]`, `replace_decision`, `reasoning`) so reasoning is
inspectable alongside the action.

**Required inputs.** None live — a self-contained simulator (continuous double auction, price-time priority,
partial fills, market-to-market then market-to-book matching, stochastic dividends). Agent population is the
experimental variable: value, momentum, market-maker, contrarian, speculator and sentiment agents, plus
deterministic controls.

**Parameters & defaults.** 8 agents, 15–20 rounds (100 for the stress scenario), endowment 1,000,000 cash + 10,000
shares each, $E[D]=\$1.40$ with $\pm\$1.00$ at 50/50, $r=5\%$ per round, transaction costs 0, GPT-4o as the
decision engine.

**Observed effect sizes.** Qualitative only: value investors buy below and sell above $\rho=1$; momentum traders
are insensitive to $\rho$; starting at $\rho=2$ the price does not converge down over 15 rounds while starting at
$\rho=0.5$ it converges up; order sizes rise with $|\rho-1|$ (arXiv:2504.10789).

**Failure modes.** One foundation model for all agents creates correlated behaviour and possible amplification —
the paper names this as a systemic-risk channel. No statistical test, no P&L, no costs, discrete rounds imposed by
LLM latency. Full machinery also derived in
[`../qfin-st/market-simulation-agent-models.md`](../qfin-st/market-simulation-agent-models.md) and
[`../qfin-tr/llm-trading-systems.md`](../qfin-tr/llm-trading-systems.md).

### 2.6 Fine-tuning audit: does domain adaptation beat off-the-shelf?
**Purpose.** Decide whether a domain-adapted sentiment model is worth building, using event-level accuracy rather
than an F1 on the fine-tuning corpus.

**Formula.** Standard cross-entropy over {positive, neutral, negative}, with the decisive metric
$$\text{Success}=\frac{1}{N_{ev}}\sum_{e}\mathbf{1}\{\operatorname{sign}(\text{sentiment}_e)=
\operatorname{sign}(\text{abnormal return}_e)\}$$
where the event label is itself cap-dependent: $|r|>1\%$ (large), $>2\%$ (mid), $>3\%$ (small), $>4\%$ (micro).

**Required inputs.** Full press-release text per event, the surrounding 10-Q/10-K/6-K/20-F documents, event-day
abnormal return, market cap for the label threshold.

**Parameters & defaults.** BioBERT + Financial PhraseBank (~4,000 samples), 3 epochs, lr $2\times10^{-5}$;
alternative ~5,300 samples (PhraseBank + FiQA), 5 epochs, batch 16, lr $6\times10^{-5}$; curated set from 96
BioPharma-Dive articles → ~2,000 sentences, 60% hand-labelled, 40% GPT-3.5 pseudo-labelled.

**Observed effect sizes.** BioFinBERT F1 $0.9104$ / event success $62.86\%$; larger mixed corpus F1 $0.8240$;
off-the-shelf FinBERT event success $66.86\%$ ($66/105$). Press-release sentiment is consistently more predictive
than 10-Q sentiment. Strategy: BioPharma model best for large caps, FinPhrase for mid caps, the 5%-open-to-close
benchmark best for small/micro caps; small caps, 3-month hold: 300% cumulative, 1.31 annualized Sharpe, 31% vol
(arXiv:2401.11011).

**Failure modes.** 105 events across 26 stocks in one sector, 2020–2023 (a COVID-era window); the cap-dependent
label threshold is a free parameter; 40% of the curated set is pseudo-labelled; no costs, no significance test.
Detail also in [`../qfin-tr/llm-trading-systems.md`](../qfin-tr/llm-trading-systems.md).

### 2.7 Two-stage macro → sector-ETF ranking with an echo-state network
**Purpose.** Rank sectors by predicted return from macro state, then hold the top ranks.

**Formula.** Stage 1, per sector, on RFE-selected features $u(t)$ (4 of the sector's macro set):
$$x(t+1)=(1-a)\,x(t)+f\!\big(s_{in}W_{in}u(t+1)+\rho_r W x(t)\big),\qquad
y(t+1)=g\big(W_{out}[x(t);u(t)]\big)$$
where $W_{in}$ and $W$ are random and **frozen**; only $W_{out}$ is fitted (ridge, $\alpha=1$). Stage 2 ranks
sectors by predicted return $\hat r_j=(\hat y_j-y_j)/y_j$ and forms an equal-weight long-only top-4 portfolio.
Baselines: ridge; LSTM (3 layers, 16/256/64 units, ReLU); GRU (32/256/64).

**Required inputs.** Daily adjusted ETF closes; macro series (GDP, unemployment, CPI, 30-year mortgage rate,
effective fed funds, plus sector-specific sets such as industrial production, refinery utilisation, trade balance,
R&D value), interpolated to monthly.

**Parameters & defaults.** ESN: 100 reservoir units, leak rate $0.5$, spectral radius $1$, density $0.5$,
transient 0. Lookbacks 0.5–5 years; horizons 1, 3, 6, 12 and 24 months; monthly rebalancing; risk-free rate 0.

**Observed effect sizes.** Benchmark (equal-weight 8 ETFs) out-of-sample $13.60\%$ / $1.200$ / $0.990
(return/Sharpe/Calmar). ESN two-year-ahead, five-year lookback: in-sample $24.70\%$ / $1.185$ / $0.786$,
out-of-sample $15.16\%$ / $1.480$ / $0.892$. ESN is first and LSTM second for cumulative return in nearly every
horizon; GRU and ridge are unstable out-of-sample (arXiv:2108.02838).

**Failure modes.** No transaction costs, no risk-free rate, no significance test; model and lookback are chosen by
inspecting three metrics across $4\times6\times5$ combinations (an uncorrected selection problem); ESN
hyperparameters were fixed by "preliminary experiments"; the train/test split date is never stated and the
benchmark row is identical in all tables, implying one test window.

### 2.8 Cost-sensitive classifier for an imbalanced binary event
**Purpose.** Predict a rare, costly event (a cancelled deal, a failed readout) where a false negative costs far more
than a false positive.

**Formula.** With $p$ the label, $q$ the predicted probability, $\gamma$ the focusing parameter,
$$\text{Focal}= -\frac{1}{N}\sum_n\big[p_n(1-q_n)^{\gamma}\log q_n+(1-p_n)q_n^{\gamma}\log(1-q_n)\big]$$
$$\text{Tversky}=1-\frac{\sum_n p_nq_n}{\sum_n p_nq_n+\alpha\sum_n(1-p_n)q_n+\beta\sum_n p_n(1-q_n)},
\qquad \alpha=\beta=0.5\ \Rightarrow\ \text{F1 loss}$$
Pipeline: PCA (20 components) on numericals, MCA (45 components, >90% of inertia) on one-hot categoricals, an
optional 121-day sentiment series compressed to a 5-dim LSTM-autoencoder embedding, SMOTE on the reduced set, then
an FFNN tuned by Bayesian optimisation (1–2 layers, 8–256 units; selu/elu/relu).

**Required inputs.** Deal/event numericals and categoricals (payment method, management attitude, competing bids,
bid premium, relative size, termination fee), a 121-day daily sentiment series per event, and the outcome label.

**Parameters & defaults.** Train pre-2019 (16,525 events, ~80% positive), test 2019+ (915 events, ~79% positive);
52 numerical + 108 one-hot features; SMOTE for the minority class; metrics accuracy / recall / precision / F1 /
PR-AUC / ROC-AUC.

**Observed effect sizes.** Logit OOS $83\%$ / $71\%$ / $57\%$ / $63\%$ / $0.67$ / $0.79$; weighted logit
$80\%$ / $76\%$ / $50\%$ / $60\%$ / $0.67$ / $0.78$; best balanced model (SMOTE-NN-F1) $86\%$ / $73\%$ / $62\%$ /
$67\%$ / $0.68$ / $0.81$; max-recall variant $62\%$ / $85\%$ / $33\%$ / $48\%$ / $0.63$ / $0.71$
(arXiv:2110.09315).

**Failure modes.** The paper calls its results "preliminary" and reports no confidence intervals; the sentiment
branch added noise or nothing; SMOTE changes the effective prior, so precision must accompany recall; accuracy is
meaningless at an 80/20 split. Deal features and daily sentiment history are both **gaps** (§3).

## 3. Data requirements → available endpoints

Provider rows below are real entries in `strategies/endpoints.json` (exact `url` / `category` / `provider` /
`code`); "gap" means **no current provider can supply it.**

| Input | Endpoint | Category | Provider | Probe status |
|---|---|---|---|---|
| Daily OHLCV (sector ETFs, targets, S&P 500) | `https://eodhd.com/api/eod/AAPL` | `core_stock_apis` | eodhd | ok |
| Daily OHLCV (secondary) | `https://api.tiingo.com/tiingo/daily/AAPL/prices` | `core_stock_apis` | tiingo | ok |
| Previous-session aggregate bars | `https://api.massive.com/v2/aggs/ticker/AAPL/prev` | `core_stock_apis` | massive | ok |
| Intraday minute bars (event-day windows) | `https://api.twelvedata.com/time_series` | `core_stock_apis` | twelvedata | ok |
| Intraday K-line via local OpenD gateway | `moomoo://get_cur_kline` | `technical_indicators` | moomoo | gateway (not live-probed) |
| Top-of-book snapshot | `moomoo://get_market_snapshot` | `core_stock_apis` | moomoo | gateway (not live-probed) |
| News text/headlines for sentiment scoring | `https://eodhd.com/api/news` | `news_data` | eodhd | ok |
| News text (secondary) | `https://api.stockdata.org/v1/news/all` | `news_data` | stockdata | ok |
| Newswire text (secondary) | `https://api.benzinga.com/api/v2/news` | `news_data` | benzinga | ok |
| News search (secondary) | `https://newsapi.org/v2/everything` | `news_data` | newsapi | ok |
| Provider sentiment score (classical baseline) | `https://eodhd.com/api/sentiments` | `news_sentiment` | eodhd | ok |
| Provider sentiment score (secondary) | `https://www.alphavantage.co/query` | `news_sentiment` | alpha_vantage | ok |
| Global news tone/aggregate | `https://api.gdeltproject.org/api/v2/doc/doc` | `news_sentiment` | gdelt | rate_limited |
| Macro series (GDP, CPI, unemployment, EFFR, mortgage) | `https://api.stlouisfed.org/fred/series/observations` | `macro_data` | fred | ok |
| Macro indicator list (secondary) | `moomoo://get_macro_indicator_list` | `macro_data` | moomoo | gateway (not live-probed) |
| Macro release calendar | `moomoo://get_economic_calendar` | `economic_calendar` | moomoo | gateway (not live-probed) |
| Policy-rate expectations | `moomoo://get_fed_watch_target_rate` | `fed_watch` | moomoo | gateway (not live-probed) |
| Company statements/fundamentals | `https://api.tiingo.com/tiingo/fundamentals/AAPL/statements` | `fundamental_data` | tiingo | ok |
| Earnings calendar (event windows) | `https://api.benzinga.com/api/v2.1/calendar/earnings` | `earnings_calendar` | benzinga | ok |
| FDA / regulatory event calendar | `https://api.benzinga.com/api/v2.1/calendar/fda` | `fda_calendar` | benzinga | ok |
| Guidance revisions | `https://api.benzinga.com/api/v2.1/calendar/guidance` | `guidance_revisions` | benzinga | ok |
| Analyst ratings / actions | `https://api.benzinga.com/api/v2.1/calendar/ratings` | `analyst_ratings` | benzinga | ok |
| Dividends (ETF/deal cash flows) | `https://api.benzinga.com/api/v2.2/calendar/dividends` | `corporate_actions` | benzinga | ok |
| Risk-free curve (Sharpe/Calmar inputs) | `https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2026/all` | `risk_free_curve` | federal_reserve | ok |
| Tradable universe / tickers | `https://eodhd.com/api/exchange-symbol-list/US` | `exchange_symbols` | eodhd | ok |
| **Full-text SEC filings (10-Q/10-K/6-K/20-F)** | — | — | — | **gap** |
| **Company press-release full text** | — | — | — | **gap** |
| **M&A deal terms (payment, attitude, rumor flag, termination fee, competing bids)** | — | — | — | **gap** |
| **Google Trends search volume** | — | — | — | **gap** |
| **Crypto asset prices / market caps (AI-token cohorts)** | — | — | — | **gap** |
| **LLM inference endpoint with pinned model version** | — | — | — | **gap** |
| **Point-in-time (as-published) macro vintages** | — | — | — | **gap** |

**What the gaps cost, quantified.** (i) *AI-crypto event study:* arXiv:2305.12739 needs 125 daily log returns for
16 treated + 15 control tokens (plus 86 + 85 in robustness); no provider serves any crypto price, so the "ChatGPT
effect" is context, not an estimator FinRobot can run. (ii) *Biotech event study:* arXiv:2401.11011 needs 105
events × (1 press release + 2 filings) ≈ 315 full documents; news endpoints return headlines, not filing bodies, so
sentiment here is computed on truncated text. (iii) *Deal-status classifier:* arXiv:2110.09315 needs 19,006 deal
records (52 numerical + 40 binary + 11 categorical fields, 2001–2020) plus 121 daily sentiment scores each (~2.1M
sentiment-days); both are gaps, so §2.8 can only be prototyped on a hand-built list. (iv) *Attention proxy:* the
Google Trends regressor behind the $0.09^{***}$–$0.11^{***}$ coefficients has no provider. (v) *LLM pipelines:* no
inference endpoint, so every LLM step runs offline and §2.3 step 5 cannot be automated. (vi) *Macro:* FRED gives
revised series, not vintages, so a sector-rotation backtest runs on data unavailable at the time.

## 4. Pitfalls, validation and measurement

- **Pretraining contamination is the first-order threat for any LLM signal.** Training corpora may contain the
  outcomes being forecast (arXiv:2409.11540); defend with numeric-only, identifier-free prompts plus a cutoff audit.
  For arXiv:2305.12739 the event itself lies inside every contemporary model's knowledge window, so LLM commentary
  on it is unusable as evidence.
- **A well-explained forecast can still be a bad forecast.** The extrapolation model explains $38\%$ of GPT
  forecasts; split each forecast into Predicted (which carries the inverted relation to future returns) and
  Residual (which may not). Never sign-flip an LLM signal without that decomposition (arXiv:2409.11540).
- **Prompt-level debiasing does not work, and calibration must be judged against a naive benchmark.** Prefixing
  "You are a sophisticated Hedge Fund investor" left forecasts unchanged; $76.9\%$ coverage beats the $36\%$ of
  surveyed CFOs but loses to quoting historical deciles ($79.0\%$) (arXiv:2409.11540).
- **Selection and specification are uncorrected.** arXiv:2108.02838 picks model *and* lookback by inspecting three
  metrics across $4\times6$ settings per horizon, with no multiplicity adjustment, no significance test and a zero
  risk-free rate, while its DID-style parallel-trends cousin (arXiv:2305.12739) spans $p=0.0002$–$0.91$ across
  specifications — report both estimators and the pre-trend plot, and add the placebo dates the papers omit.
- **Costs and horizons are the usual free lunch.** Sector rotation is long-only top-4 equal weight, monthly, zero
  costs; the LLM-agent simulator sets costs to zero and reports no P&L; the biotech strategy reports no costs. Every
  "beats the benchmark" claim here is gross (arXiv:2108.02838, arXiv:2504.10789, arXiv:2401.11011).
- **Class imbalance changes the metric, not just the loss.** At ~80% completion accuracy is uninformative; the
  paper's SMOTE variant shows the trade (85% recall at 33% precision out-of-sample). Use recall and PR-AUC, and
  keep a temporal split because deal regimes shift (arXiv:2110.09315).
- **Regime dependence is explicit in two papers.** The ChatGPT effect is measured in a "fear"/"extreme fear" market
  and differs by window (1 vs 2 months: $10.7\%$ vs $35.5\%$) (arXiv:2305.12739); the LLM agents correct
  undervaluation but not overvaluation, and bubble persistence is framed as a stability risk (arXiv:2504.10789).
- **Small samples and unexamined data choices masquerade as effects.** 105 events / 26 stocks / one sector /
  2020–2023 (arXiv:2401.11011); 15–20 rounds with 8 agents and one model version (arXiv:2504.10789); one
  unspecified test window (arXiv:2108.02838).
- **Correlated agents are a systemic channel.** Many agents sharing one foundation model can respond to the same
  prompt and signal in the same direction without coordinating — an amplifier of instability, and a reason to
  stress-test prompt-driven strategies (arXiv:2504.10789).
- **Endpoint-status honesty.** `gdelt` is `rate_limited` and every `moomoo://` row is a local-gateway SDK call, not
  a live-probed HTTP endpoint; do not treat either as a guaranteed high-frequency feed in a backtest.

## 5. Recommended first implementation in FinRobot

Ranked by value per unit of effort against what the data layer can fetch today. Items 1–4 are buildable now;
5–8 are blocked or partial.

1. **Sector-rotation ESN pipeline (macro → ETF ranking).** Port §2.7 (RFE per sector; ESN 100 units, leak 0.5,
   spectral radius 1, density 0.5; rank by predicted return; equal-weight top 4; monthly). *Data:* fred
   `series/observations`, eodhd `eod` / tiingo `prices`, federal_reserve `risk_free_curve`. *Passing:*
   out-of-sample Sharpe above the equal-weight 8-ETF benchmark over a **pre-registered** window, net of costs.
   *Effort:* M.
2. **LLM signal audit harness (calibration + contamination).** Implement §2.2 and §2.3 as a reusable module:
   elicit point + interval forecasts, score coverage and tail-miss rates against the historical-decile benchmark,
   replicate across two model families, and refuse to emit a score when the evaluation date precedes a pinned
   cutoff. *Data:* eodhd/stockdata/benzinga `news`; local inference. *Passing:* coverage within $\pm3$ pp of
   nominal, monotone PIT, cross-family coefficient agreement near the $0.78$ level. *Effort:* M.
3. **Extrapolation guard on any LLM-generated return view.** §2.1 — regress the rank/score on 12 weekly lags,
   report $\lambda_1,\lambda_2$ and DoE, and flag a view whose sign disagrees with measured reversal after
   decomposing Predicted vs Residual. *Data:* daily bars → weekly returns. *Passing:* DoE and $\beta_1/\beta_2$
   reproduced out-of-sample; guard fires on synthetic extrapolative forecasts. *Effort:* S.
4. **Event-study template: SDID around a dated shock.** §2.4 as a generic module (balanced panel, unit and time
   weights, 500 bootstrap SEs) with DID alongside. *Data:* daily bars for treated/control cohorts;
   `exchange_symbols`. *Passing:* reproduces the 1- vs 2-month ATT ordering on a US equity analogue, with a
   pre-trend plot and the placebo dates the paper omits. *Effort:* M.
5. **Biotech event-study sentiment pipeline.** §2.6 — score press-release and filing text around value-driving
   events, compare press-release vs 10-Q predictive power, then hold 1–3 months after positive events by cap
   bucket. *Data:* benzinga `fda`/`earnings`/`guidance`, `news`, daily bars. *Passing:* press-release sentiment
   beats filing sentiment on event-day sign. *Risk:* **press-release text and filing bodies are gaps** — until then
   the module scores headlines, which is not the paper's object. *Effort:* M (L with a filing source).
6. **LLM-agent market simulator (framework port).** §2.5 — persistent book, partial fills, schema-validated
   decisions, $\rho$ sweep. *Data:* none live. *Passing:* reproduces the under/over-valuation convergence asymmetry
   and maps decision boundaries per agent type. *Effort:* L.
7. **Cost-sensitive event classifier.** §2.8 — PCA/MCA reduction, SMOTE, focal/F1/Tversky losses, Bayesian search,
   recall/PR-AUC on a temporal split. *Data:* tiingo `fundamentals`, benzinga calendars, `corporate_actions`.
   *Passing:* recall ≥ 70% at precision ≥ 60% out-of-sample. *Risk:* **deal-terms and daily sentiment history are
   gaps**, so v1 is a framework. *Effort:* M.
8. **Attention-proxy panel (blocked).** The interaction regression of returns on attention changes before/after a
   dated narrative shock, by cohort. *Data:* Google Trends (gap) and crypto prices (gap). *Passing:* insignificant
   pre-launch, significant post-launch for the treated cohort only. *Effort:* S once data exists.

## Appendix — papers read

| arXiv id | Title | Year |
|---|---|---|
| 2305.12739v1 | The Influence of ChatGPT on Artificial Intelligence Related Crypto Assets: Evidence from a Synthetic Control Analysis | 2023 |
| 2401.11011v1 | BioFinBERT: Finetuning Large Language Models (LLMs) to Analyze Sentiment of Press Releases and Financial Text Around Inflection Points of Biotech Stocks | 2024 |
| 2504.10789v1 | Can Large Language Models Trade? Testing Financial Theories with LLM Agents in Market Simulations | 2025 |
| 2409.11540v1 | What Does ChatGPT Make of Historical Stock Returns? Extrapolation and Miscalibration in LLM Stock Return Forecasts | 2024 |
| 2110.09315v1 | Predicting Status of Pre and Post M&A Deals Using Machine Learning and Deep Learning Techniques | 2021 |
| 2108.02838v1 | Two-Stage Sector Rotation Methodology Using Machine Learning and Deep Learning Techniques | 2021 |
