# Behavioral & Decision Finance — learnings from the q-fin.GN corpus

`384` of 3095 corpus papers matched this category (379 with PDFs); this doc is based on a close reading of `6`.

Headline: **the tradable content of this category is concentrated in two measurement papers.** Four of the
six assigned papers are conceptual, architectural or qualitative and yield no estimator at all; only the
multivariate long/short sentiment decomposition (arXiv:1910.01407) and the transformer sentence-level mood
index (arXiv:2607.13968) produce quantities that can be estimated on data FinRobot can already fetch. The
heterogeneous-agent paper (arXiv:1205.3763) contributes a *simulation* diagnostic for behavioural breaks, not
a signal. Where the corpus is thin the doc says so instead of padding: §2 has six techniques but only four are
estimable today, and the rest of the space is explicitly marked non-actionable.

## 1. What the corpus actually offers

- **Two papers are quantitative estimators; two are non-actionable; one is architectural; one is a simulator.**
  Directly estimable: the MLSS sentiment state-space filter (arXiv:1910.01407) and the FinBERT mood index
  (arXiv:2607.13968). Simulation-only: the behavioural-break HAM (arXiv:1205.3763). Transferable primitive:
  entropy-based active labelling from the DeFi trust framework (arXiv:2512.00142). Non-actionable: the
  semi-bounded-rationality theory paper (arXiv:1305.6037, no data, no model estimated, no effect sizes) and
  the ESG-frameworks review (arXiv:2502.13148, a narrative survey of eight theories with no dataset, no
  regression and no reported statistic). Both are retained only to document that the category's behavioural
  wing is mostly conceptual.
- **Behavioural breaks are visible in pre/post-crisis distributions but are weak in the *mean*.** On all 30
  DJIA constituents around five crisis dates (Black Monday 1987, Ruble Devaluation 1998, Dot-com 2000,
  WTC 9/11 2001, Lehman 2008), 20 trading days before vs after each break point, full sample 5,519
  observations: mean, variance and skewness each increase in 4 of 5 periods, kurtosis decreases in 4 of 5
  (arXiv:1205.3763). Variance changes are large — Lehman $1.090\to4.744$ (+335.3%), WTC 9/11
  $0.458\to1.162$ (+153.6%) — and only Black Monday moves the other way.
- **Overconfidence is the only behavioural injection that raises variance almost deterministically in
  simulation.** Across 100 Monte Carlo runs per setup (H = 5 trader types, break injected at $t=126$ of 250,
  $\beta\in\{5,60,\dots,500\}$, $g_h\sim N(0,0.16)$, $b_h\sim N(0,0.09)$), overconfidence raises variance in
  94–99 of 100 runs; market sentiment affecting the *bias* parameter alone gives 100/100 mean increases;
  herding is the weakest injection — the 20-day before/after distributions are statistically indistinguishable
  in 61 of 100 runs (arXiv:1205.3763). The Cramér–von Mises test confirms the injected distribution shift:
  before-vs-20-day-before and 20-day-after-vs-after agree in 100/100 runs by construction, while the
  20-day windows differ in up to 99/100 runs for trend-affecting sentiment. Memory (fitness averaged over
  $m_h\sim U(0,20)$ lags) is the single strongest structural modification.
- **Sentiment decomposes into a permanent random-walk component and a mean-reverting VAR(1) component, and
  the decomposition is what restores return predictability.** On 27 of 30 DJIA names, 54 series (news and
  social), daily 2006-03-01 to 2017-12-29, BIC selects $q=2$ common long-term factors per channel and the
  filter's signal-to-noise ratio is ≈20× the univariate local-level alternative (AAPL 1.736 vs 0.096)
  (arXiv:1910.01407).
- **Only the short-term component carries the lagged return signal.** One-lag quantile $\mathrm{R}^1$:
  12.7% at $\tau=0.01$ and 11.9% at $\tau=0.99$ (both $p<0.01$) for MLSS, versus 4.5% / 3.4% for a univariate
  long/short filter and 0.1% / 1.0% for raw sentiment; the short-term block is significant at 1% in the
  extreme quantiles while the long-term block is insignificant in 6 of 9 (arXiv:1910.01407). Asymmetry:
  negative extreme returns are echoed by news for up to five days, positive ones within one.
- **A filtered-sentiment long/short overlay beats buy-and-hold on risk-adjusted terms, but transaction costs
  eat most of it.** Feb 2007–Jun 2017, DJIA equal-weight, 0.1%/side: MLSS annual return 7.891% vs 8.975%
  buy-and-hold, but volatility 15.209% vs 19.132%, Sharpe 0.519 vs 0.469, Sortino 0.671 vs 0.578; 553 trades
  cost \$37,974 ≈38% of the starting \$100,000. Gating trades on a rolling McFadden-$\mathrm{R}^2$ quantile
  ($\alpha=0.65$) cuts trades to 169, cost to \$12,007, and lifts return to 10.248%, Sharpe to 0.757, Sortino
  to 1.085 (arXiv:1910.01407). Without costs the Sharpe gain is 40%; with costs, 10%.
- **Transformer sentence-level sentiment dominates dictionary sentiment against a human benchmark.**
  143,755 English finance articles from Dow Jones Factiva (Jan–Dec 2025, >300 words, mean 48.72
  sentences/article) scored with FinBERT; validated on 588 articles rated by 444 incentivised Prolific
  annotators (3 raters each, 1,776 evaluations, 5-point Likert). Transformer indices correlate ≈0.75–0.76 with
  human consensus vs ≈0.70–0.71 for dictionaries; in-sample macro-F1 0.668–0.687 vs 0.187 (dictionaries label
  almost everything neutral); out-of-sample macro-F1 0.638 vs 0.162 (random) and regression
  $\mathrm{R}^2=0.632$ vs 0.295 / 0.183 (arXiv:2607.13968).
- **Sentence-level indices are more polarised and more dispersed than word-count indices, and their scale is
  set by the aggregation rule.** Document-level SDs: `index_stat` 0.24, `index_pos_neg` 0.68,
  `index_pos_neg_max` 0.72, `index_pos_neg_tanh` 0.40, `index_ICI` 1.27, vs 0.06 and 0.03 for the two
  dictionary indices; same-day pairwise correlation among the six transformer indices averages 0.903 (all
  pairs ≥0.8), decaying to 0.741 at lag 1 and 0.645 at lag 2 (arXiv:2607.13968).
- **Calendar effects are material in daily news mood.** After publisher fixed effects and volume weighting,
  Tuesday has the highest mean sentiment (0.744) and Friday the lowest (−0.025); residualising on weekday
  fixed effects leaves the main dynamics unchanged but the level and dispersion differ systematically by
  weekday (arXiv:2607.13968).
- **Active learning with human experts lifts a small-data decision model from AUC 0.74 to 0.92.** 1,888 loan
  applications (45.52% funded, 18 attributes → 88 one-hot features), 1D-CNN (3 conv+pool layers, kernels
  {5,5,2}, 50/50/60 filters), six iterations of 150 entropy-selected expert annotations each (900 labels
  total); blockchain audit of the explanation hashes with 2–20% file-tampering detection (arXiv:2512.00142).
  Not a market signal, but the uncertainty-sampling loop transfers to label acquisition (§2.5).
- **Off-topic note:** none of the six is mis-tagged, but arXiv:1305.6037 and arXiv:2502.13148 are
  *conceptual* — zero datasets, regressions or effect sizes. They are reported only to explain why this
  category's implementable core is small; neither supports a §2 technique beyond the qualitative §2.6.

## 2. Implementable formulas & algorithms

### 2.1 Multivariate long/short sentiment decomposition (MLSS) by Kalman filter + EM
**Purpose.** Split a cross-section of noisy per-asset sentiment into a permanent (common) component and a
transient (idiosyncratic) component, so that the transient part can be used as a state variable for
return prediction. This is the single most valuable construction in the category.

**Formula.** For $K$ assets and observed daily sentiment $S_t\in\mathbb{R}^K$:
$$S_t = \Lambda F_t + \Psi_t + \epsilon_t,\qquad \epsilon_t\sim N(0,R)$$
$$\Psi_t = \Phi\,\Psi_{t-1} + u_t,\qquad u_t\sim N(0,Q_{\text{short}})$$
$$F_t = F_{t-1} + v_t,\qquad v_t\sim N(0,Q_{\text{long}})$$
with $\Lambda\in\mathbb{R}^{K\times q}$ factor loadings, $R$ diagonal observation-noise covariance,
$\Phi\in\mathbb{R}^{K\times K}$ the (diagonal, in the paper) short-term autoregression, $Q_{\text{short}}
\in\mathbb{R}^{K\times K}$ symmetric, and $Q_{\text{long}}\in\mathbb{R}^{q\times q}$. $F_t$ is the long-term
factor mood, $\Psi_t$ the short-term mood. Intraday-to-daily aggregation of a buzz-weighted feed is
$$S_{ta}=\frac{\sum_{s=sh_{t-1}}^{sh_t} \mathrm{Buzz}^a_{t,s}\,S^a_{t,s}}{\sum_{s=sh_{t-1}}^{sh_t}\mathrm{Buzz}^a_{t,s}}\in[-1,1],$$
with the cut hour $sh$ set to the exchange close (16:00 NYSE) so that the series aligns with close-to-close
returns. The filter's signal-to-noise ratio is $\sigma^2_v/\sigma^2_\epsilon$. Estimation: Kalman filter +
EM (smoothing recursion in the E-step, closed-form static-parameter updates in the M-step), iterate to
convergence.

**Required inputs.** Per-asset daily sentiment (news channel and, separately, social channel); per-asset
daily returns for the cointegration/validation step; optionally intraday sentiment and buzz fields.

**Parameters & defaults.** $q$ by BIC — the paper's data selects $q_{\text{news}}=2$, $q_{\text{social}}=2$;
$\Phi$ forced diagonal (drops lead–lag effects to control dimensionality); $R$ diagonal; short-term loading
matrix set to the identity so the short component is purely firm-specific. Missing values: EM handles them
natively, but the paper fills residual gaps (47/54 series <1% missing, all <7.5%) with a 5-day rolling mean.
Estimation window: full 2006–2018 sample; the trading exercise uses 126-observation rolling windows.

**Observed effect sizes.** S/N ratio ≈20× the univariate MLNSL alternative (AAPL 1.736 vs 0.096, MCD 1.401 vs
0.013, PFE 1.185 vs 0.007). Long-term sentiment cointegrates with the first PCA market factor (Engle–Granger);
the short-term correlation matrix explains 13.77% ($F=55.7$, $p<0.0001$) of return correlation across all
pairs and 37.89% ($F=23.2$, $p<0.0001$) within-sector, versus 0.95% ($p=0.069$) for unfiltered sentiment;
against *idiosyncratic* return correlation MLSS keeps $\mathrm{R}^2=11.34\%$ while MLNSL collapses to 4.31%.
Quantile-$\mathrm{R}^1$ at one lag: 12.7% ($\tau=0.01$), 11.9% ($\tau=0.99$).

**Failure modes.** The smoother is backward-looking — the authors concede a possible forward-looking bias and
re-run with parameters frozen on 2007–2017 to filter 2017–2019 (ranking reproduced); do the same, or use only
the causal filtered state. $\Lambda$ is identified only up to rotation and the paper's own loadings are
heterogeneous in sign, so a single factor is not "the market mood". Only the EM handles missing data natively;
the 5-day rolling-mean fill is a stopgap. The short-term component is the one carrying the signal — if the fit
weights the long-term block, the decomposition has failed.

### 2.2 Quantile-regression predictability test and R²-gated trading signal
**Purpose.** Test whether a filtered sentiment state predicts returns, specifically in the tails, and convert
it into a low-turnover long/short overlay.

**Formula.** With market log-return $r^m_t$ and filtered sentiment $S^{\text{model}}_{t-h}$:
$$r^m_t = \alpha(\tau) + \beta(\tau)\,S^{\text{model}}_{t-h} + u_t,\qquad
\hat V(\tau)=\min_{\alpha,\beta}\sum_t \rho_\tau\!\big(r^m_t-\alpha-\beta S^{\text{model}}_{t-h}\big),\quad
\rho_\tau(u)=u(\tau-\mathbb{1}_{u<0})$$
$$\mathrm{R}^1(\tau)=1-\frac{\hat V(\tau)}{\tilde V(\tau)},\qquad
\mathrm{LT}(\tau)=\frac{2\big(\tilde V(\tau)-\hat V(\tau)\big)}{\tau(1-\tau)s(\tau)}\ \to\ \chi^2_q$$
where $\tilde V$ is the intercept-only fit and $s(\tau)=1/f(F^{-1}(\tau))$. The trading criterion uses
volatility-standardised returns $\tilde r^m_t = r^m_t/\sqrt{RV_t}$ with $RV_t$ the realised variance from
5-minute intraday returns, and the binary target
$$Y_t=\mathbb{1}\{\tilde r^m_t < z_{1/3}\},\qquad
P(Y_{t+1}=1\mid X_t)=\mathrm{logit}\big(X_t^{\text{mod}}\theta\big),\quad X_t^{\text{mod}}=(1,\tilde r^m_t,S^{\text{mod}}_t)$$
$$s^{\text{mod}}_{t+1}=\begin{cases}+1 & \hat Y_{t+1}=0\\ -1 & \hat Y_{t+1}=1\end{cases},\qquad
\bar s^{\text{mod}}_t=\begin{cases}-1 & \hat Y_{t+1}=1\ \wedge\ R^2_t > z^{1,t}_\alpha(R^2)\\ +1 & \text{otherwise}\end{cases}$$
with $z^{1,t}_\alpha(R^2)$ the empirical $\alpha$-quantile of the rolling McFadden $\mathrm{R}^2$ up to $t$
(measurable at $t$, so no forward bias). Portfolio value is $s^{\text{mod}}_{t+1}c_0M_{t+1}$ plus cash, and
each signal change costs $\tfrac{\text{cost}}{2}|s^{\text{mod}}_{t+1}-s^{\text{mod}}_t|c_0M_{t+1}$.

**Required inputs.** Filtered sentiment vector $S^{\text{mod}}_t$ (§2.1), daily close-to-close returns of an
equal-weight portfolio, 5-minute intraday bars for $RV_t$.

**Parameters & defaults.** $h=1$ for the primary test (extend to $h\le5$ only as a robustness check);
quantile grid $\{0.01,0.05,0.10,0.33,0.50,0.66,0.90,0.95,0.99\}$; rolling window 126 observations; sell
threshold = 1/3 Gaussian quantile; transaction cost 0.1%/side; trade-gating $\alpha=0.65$; $c_0=\$100{,}000/M_0$.

**Observed effect sizes.** MLSS $\mathrm{R}^1$ 12.7% at $\tau=0.01$ and 11.9% at $\tau=0.99$; all five rival
filters ≤5.3% and ≤3.4%. With costs, MLSS Sharpe 0.519 (BH 0.469); after R² gating at $\alpha=0.65$ Sharpe
0.757, Sortino 1.085, 169 trades.

**Failure modes.** The sign inverts if returns are not standardised by $RV_t$ — volatility persistence then
leaks into the classifier. The signal is regime-dependent (§4), and the filter is argued to matter *more*
after 2007. The gating threshold $\alpha$ is a free parameter; tuning it on the test period reintroduces
selection bias.

### 2.3 Transformer sentence-level mood index with human-label validation
**Purpose.** Build a daily news-mood time series that tracks human sentiment judgements rather than word
counts — the measurement layer that feeds §2.1 and §2.2.

**Formula.** For each sentence $s$, FinBERT emits log-probabilities $\ell_s=(\ell_{s,\text{pos}},
\ell_{s,\text{neg}},\ell_{s,\text{neu}})$; take the arg-max label and one-hot encode, then sum to document
counts $(pos,neg,neu)$. Six aggregation rules (all in $[-1,1]$ except ICI):
$$\text{index\_stat}=\frac{pos-neg}{pos+neg+neu},\qquad
\text{index\_pos\_neg}=\frac{pos-neg}{pos+neg}\ (\text{0 if } pos=neg)$$
$$\text{index\_pos\_neg\_max}=\frac{pos-neg}{\max(pos,neg)},\qquad
\text{index\_pos\_neg\_tanh}=\tanh\!\frac{pos-neg}{\max(neu,1)},\qquad
\text{ICI}=\ln\frac{1+pos}{1+neg}$$
with `index_stat_n_fun(n)` the same ratio over the first $n$ sentences. Daily aggregation with publisher
fixed effects and volume weights, clustered standard errors:
$$y^{(k)}_{ijd}=\alpha^{(k)}_i+\sum_{d'\in\mathcal D}\beta^{(k)}_{d'}\mathbb{1}\{d=d'\}+\varepsilon^{(k)}_{ijd},\qquad
\text{Mood}^{(k)}_d=\hat\beta^{(k)}_d-\bar\beta^{(k)}.$$

**Required inputs.** Article text with timestamp, ticker and publisher; human-labelled validation subsample
(consensus Likert ratings) for scoring.

**Parameters & defaults.** Sentence split (BERT 512-token limit forces sentence-level scoring); minimum
article length 300 words; three-class thresholds $\pm0.33$; 3-fold chronological `TimeSeriesSplit`;
hyperparameters by grid search on macro-F1; analytic weights ∝ publication volume; 7-day trailing moving
average for display only.

**Observed effect sizes.** Human-consensus correlation 0.75–0.76 (transformer) vs 0.70–0.71 (dictionary);
in-sample macro-F1 0.668–0.687 vs 0.187; out-of-sample macro-F1 0.638 (ICI/pos_neg) vs 0.627 (SVM) vs 0.162
(dictionary); out-of-sample regression $\mathrm{R}^2$ 0.632 vs 0.295 / 0.183; inter-rater mean deviation
−0.070 (95% limits ±0.49–0.63).

**Failure modes.** The neutral class dominates (mean 37.2 of 48.7 sentences) and dictionary methods collapse
into it entirely — report per-class F1, not accuracy. The best downstream classifier barely beats the index
itself, so extra ML layers add little. The aggregation rule changes scale by ~5×; fix one and report the rest
as robustness. Trailing averages must be past-only.

### 2.4 Heterogeneous-agent behavioural-break simulator (herding / overconfidence / sentiment)
**Purpose.** A *diagnostic* sandbox: inject a behavioural bias at a chosen break date and ask which observable
distributional signatures (mean, variance, skewness, kurtosis shifts) it reproduces. Simulation-only — it does
not estimate parameters from FinRobot data.

**Formula.** Brock–Hommes adaptive belief system with $H$ belief types $f_{h,t}=g_h x_{t-1}+b_h$ and price
deviation $x_t=p_t-p^f_t$:
$$R x_t = \sum_{h=1}^H n_{h,t} f_{h,t} + \eta_t,\qquad
n_{h,t}=\frac{\exp(\beta U_{h,t-1})}{\sum_{h=1}^H \exp(\beta U_{h,t-1})}$$
$$U_{h,t-1}=(x_{t-1}-R x_{t-2})\,\frac{f_{h,t-2}-R x_{t-2}}{a\sigma^2}$$
with memory length $m_h$:
$$U_{h,t-1}=\frac{1}{m_h}\sum_{l=0}^{m_h-1}(x_{t-1-l}-R x_{t-2-l})\,\frac{f_{h,t-2-l}-R x_{t-2-l}}{a\sigma^2}.$$
Behavioural injections, applied from the break date $t^\ast$:
- *Herding:* one type copies the previous period's most profitable type, $(g_h,b_h)\leftarrow(g^\ast,b^\ast)_{t-1}$.
- *Overconfidence:* scale the drawn coefficients, $g_h\leftarrow(1+\kappa)g_h$, $b_h\leftarrow(1+\kappa)b_h$, $\kappa\in[0.05,0.5]$.
- *Market sentiment:* shift the means of the generating distributions by $\mu$: trend $\pm[0.04,0.4]$, bias $\pm[0.03,0.3]$.

**Required inputs.** None externally (self-contained simulation); the *empirical* counterpart is daily close
differences of an index's constituents around a known break date.

**Parameters & defaults.** $R=1.1$; $a\sigma^2=1$; $H=5$; $g_h\sim N(0,0.16)$; $b_h\sim N(0,0.09)$;
$\beta\in\{5,60,115,\dots,500\}$; noise $\eta\sim U(-0.05,0.05)$; 250 simulated days with break at
$t^\ast=126$, first and last 10% discarded; 100 Monte Carlo runs per setup; $m_h\sim U(0,20)$ for the memory
extension.

**Observed effect sizes.** As in §1: overconfidence raises variance in 94–99/100 runs without moving the mean;
sentiment on the bias parameter matches the empirical pattern best (100/100 mean increases, only 3/100 runs
fail to distinguish the 20-day windows); herding changes little (61/100 indistinguishable) but shifts the mean
in 78/100 runs; memory is strongest.

**Failure modes.** Everything is in-sample simulation — the paper matches *aggregate distributional shifts*,
never an out-of-sample price path; do not read a matching variance shift as a validated trading model.
Trend-affecting sentiment injections paradoxically produce near-normal samples and can erase the
leptokurtosis the model exists to generate; parameter identification is explicitly unsolved for real data
(one prior $\beta$ estimate, on DAX 2000); the three biases injected together mostly cancel.

### 2.5 Entropy-based active learning for label acquisition
**Purpose.** When ground-truth labels are expensive (human sentiment ratings, credit outcomes), select the
most informative unlabelled cases for expert annotation instead of sampling randomly.

**Formula.** For a classifier with predicted class probabilities $P(\theta\mid x)$ over $N$ classes, the
entropy uncertainty score is
$$\varnothing(x)=\frac{-\sum_{\theta}P(\theta\mid x)\log P(\theta\mid x)}{\log N}\in[0,1].$$
Rank unlabelled instances by $\varnothing(x)$ descending, annotate the top block, retrain, repeat. (The
paper's companion mechanism — SHA-256 hashing of encrypted explanations with hash-only on-chain storage for
tamper-proof audit — is a trust/audit device with no alpha content and is not reproduced here.)

**Required inputs.** A classifier emitting calibrated class probabilities; an unlabelled pool; an expert (or
LLM) annotation channel.

**Parameters & defaults.** The paper's loop: 150 annotations/iteration, 6 iterations, 1D-CNN with 3 conv+pool
layers (kernels {5,5,2}, filters {50,50,60}), dropout 0.10, lr $10^{-4}$, batch 100, $L_2$ 0.01, Bayesian
hyperparameter search, 5-fold CV on AUC.

**Observed effect sizes.** AUC 0.74 (no expert data) → 0.92 after six iterations (900 expert labels).

**Failure modes.** Entropy is only as good as the calibration of $P(\theta\mid x)$; an overconfident network
assigns low entropy to genuinely ambiguous cases. Label-quality drift across iterations is not measured.

### 2.6 Semi-bounded-rationality preprocessing stack (missing-data completion + denoising)
**Purpose.** The one operational reading of arXiv:1305.6037: before any decision model, filter outliers,
impute missing values and use a *consistent* (deterministic) model in place of an inconsistent human
decision-maker. This is a design principle, not an estimator — no effect size is available, and the paper
reports no data.

**Formula / procedure.** Three stages: (i) signal-processing denoise of the input (drop or winsorise
measurement-error outliers); (ii) a *correlation machine* that estimates missing values from the observed
cross-section; (iii) a *causal machine* that maps cause to effect consistently. In this portfolio stage (ii)
is the EM inside the §2.1 state-space model (or a rolling-mean fill for short gaps) and stage (i) is a robust
filter applied before the §2.1 fit.

**Required inputs.** The raw sentiment/price panel with a documented missingness pattern.
**Parameters & defaults.** None published; the only corpus anchor is the MLSS gap-fill rule (5-day rolling
mean; 47/54 series <1% missing).
**Observed effect sizes.** None — the paper is theoretical.
**Failure modes.** The paper asserts rationality is *indivisible*, so it gives no way to decide how much
imputation is "too much"; signal manufactured in thin series is undetectable here. Treat it as a checklist.

## 3. Data requirements → available endpoints

Every row cites a probed row of `strategies/endpoints.json` unless marked **gap**; credentials are env-var
names only.

| Input | Endpoint | Category | Provider | Probe status |
|---|---|---|---|---|
| News headline/URL/publish time per ticker (§2.3 corpus) | `https://eodhd.com/api/news` (`api_token=$EODHD_API_KEY`) | news_data | eodhd | ok |
| Aggregated daily sentiment series per ticker | `https://eodhd.com/api/sentiments` (`s={ticker}`) | news_sentiment | eodhd | ok |
| News + per-ticker sentiment score (AV feed) | `https://www.alphavantage.co/query` (`function=NEWS_SENTIMENT`) | news_sentiment | alpha_vantage | ok |
| Wire/company news feed | `https://api.benzinga.com/api/v2/news` (`token=$BENZINGA_API_KEY`) | news_data | benzinga | ok |
| General news search | `https://newsapi.org/v2/everything` (`X-Api-Key:$NEWSAPI_API_KEY`) | news_data | newsapi | ok |
| News (alt aggregate) | `https://api.stockdata.org/v1/news/all` | news_data | stockdata | ok |
| Global news tone timeline | `https://api.gdeltproject.org/api/v2/doc/doc` (`mode=timelinetone`) | news_sentiment | gdelt | rate_limited |
| Daily close-to-close returns for §2.2 | `https://eodhd.com/api/eod/AAPL` (any ticker) | core_stock_apis | eodhd | ok |
| Daily prices (secondary) | `https://api.tiingo.com/tiingo/daily/AAPL/prices` | core_stock_apis | tiingo | ok |
| Daily/intraday bars | `https://api.twelvedata.com/time_series` (`interval=1min`) | core_stock_apis | twelvedata | ok |
| Daily aggregate bars | `https://api.massive.com/v2/aggs/ticker/AAPL/prev` | core_stock_apis | massive | ok |
| Intraday bars for realised variance $RV_t$ (§2.2) | `moomoo://get_cur_kline` | technical_indicators | moomoo | gateway (not live-probed) |
| Tradable universe / constituent list | `https://eodhd.com/api/exchange-symbol-list/US` | exchange_symbols | eodhd | ok |
| Macro consumer-sentiment survey proxy | `https://api.stlouisfed.org/fred/series/observations` (`$FRED_API_KEY`) | macro_data | fred | ok |
| Risk-free curve for the overlay's cash leg | `https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2026/all` | risk_free_curve | federal_reserve | ok |
| Analyst ratings (sentiment cross-check) | `https://api.benzinga.com/api/v2.1/calendar/ratings` | analyst_ratings | benzinga | ok |
| Guidance revisions (sentiment cross-check) | `https://api.benzinga.com/api/v2.1/calendar/guidance` | guidance_revisions | benzinga | ok |
| Institutional ownership (herding proxy) | `moomoo://get_shareholders_institutional` | institution_data | moomoo | gateway (not live-probed) |
| Capital flow (herding/overconfidence proxy) | `moomoo://get_capital_flow` | capital_flow | moomoo | gateway (not live-probed) |
| **Full article body text** for FinBERT sentence scoring (§2.3) | — | — | — | **gap** — EODHD/NewsAPI/StockData return title+URL; only Alpha Vantage adds a short summary |
| **TRMI-style minute-level buzz-weighted sentiment** (700+ sources, 2M articles/day) used by §2.1 | — | — | — | **gap** — no probed provider; `eodhd /sentiments` is a coarse daily aggregate |
| **Human-annotated sentiment consensus labels** for §2.3 validation | — | — | — | **gap** — must be collected (Prolific-style) or proxied by a held-out manual sample |
| **Social-media sentiment** (Twitter/X, StockTwits) — the social channel of §2.1 | — | — | — | **gap** — no probed endpoint |
| **ESG / sustainability scores** (for the arXiv:2502.13148 literature) | — | — | — | **gap** — no probed endpoint |
| **On-chain / DeFi data and loan-application records** (arXiv:2512.00142) | — | — | — | **gap** — no probed endpoint; framework is out of scope for trading |

**What the gaps cost, quantified.** §2.3 needs the *full article body*: the paper scored 143,755 articles at
~48.7 sentences each (≈7 million sentence classifications), so title-only scoring drops most of the evidence
and regresses toward the dictionary behaviour the paper shows to be degenerate (macro-F1 0.187). §2.1 needs a
buzz-weighted intraday feed: the paper's input is >2 million articles/day over 700+ sources aggregated with a
buzz weight, whereas `eodhd /sentiments` supplies one normalised daily number per ticker with no buzz field
and no social channel — the news half is buildable, the social half is not. The validation gap removes the
*only* external quality check: without human labels the transformer index cannot be shown to beat a
dictionary, which is the paper's entire result. §2.2's realised variance needs 5-minute bars: `twelvedata
time_series` serves 1-minute bars (usable) while the moomoo K-line route is a local gateway not live-probed;
daily-only data would drop the volatility adjustment that stops the classifier chasing volatility
persistence.

## 4. Pitfalls, validation and measurement

- **Look-ahead through smoothing.** The MLSS filter is estimated with a Kalman *smoother*, which uses future
  observations; the authors flag this and repeat the portfolio exercise with parameters frozen on 2007–2017 to
  filter 2017–2019, obtaining the same ranking (arXiv:1910.01407). Use the causal filter (or frozen
  parameters) for any signal that feeds a trade. The same trap applies to any 7-day moving average of mood —
  the mood paper's `MA7` is explicitly *trailing* (arXiv:2607.13968).
- **Transaction costs dominate the sentiment overlay.** The unfiltered MLSS strategy trades 553 times over
  nine years and pays \$37,974 ≈38% of starting capital at 0.1%/side; costs cut the Sharpe gain from 40% to
  10% (arXiv:1910.01407). Any FinRobot replication must report net-of-cost performance and must implement the
  rolling-R² gate (§2.2) or it will reproduce the gross-only illusion.
- **Metric and aggregation choice determine the conclusion.** Accuracy hides the neutral collapse: dictionary
  indices get 39.0% accuracy but macro-F1 0.187 in-sample and 0.162 out-of-sample (random) because they label
  almost everything neutral (arXiv:2607.13968). Report macro-F1, balanced accuracy and confusion matrices, and
  quantile-local $\mathrm{R}^1(\tau)$ rather than a single $R^2$ — the sentiment–return relation lives in the
  tails and vanishes at the median (arXiv:1910.01407). The six transformer aggregation rules span document-level
  SDs 0.24–1.27 and disagree on extremes while the daily dynamics stay robust (lag-0 correlation 0.903); fix
  one rule for the signal and report the rest as robustness.
- **Multiple testing across quantiles and models.** The sentiment paper tests nine quantiles × five filters
  × multiple lags; without a correction the extreme-quantile hits are not credible. The paper's defence is a
  single pre-specified statistic per model family ($\chi^2$ on $\mathrm{LT}(\tau)$) and a $p$-value table —
  reproduce that, and fix the quantile grid before looking at the data.
- **Regime dependence and sample split.** Raw sentiment predictability decays after 2007 (arXiv:1910.01407,
  citing Beckers 2018 and Garcia 2013); the 2007–2009 crisis and 2009–2017 bull market are deliberately
  combined as two regimes, with a held-out 2017–2019 check. Split by regime *and* validate chronologically —
  the mood paper uses 3-fold `TimeSeriesSplit` precisely because k-fold shuffles future information into
  training (arXiv:2607.13968).
- **Small-sample break windows and their null tests.** The HAM benchmark uses only 20 trading days each side
  of five break dates (~460–580 observations per partial sample); the paper's own controls (40-day windows,
  fixed 15-stock cohorts of 300/600 observations) are needed before a shift is believed — 20-day windows
  cannot identify a kurtosis change. Validate with the Cramér–von Mises equal-distribution test and
  Jarque–Bera rather than by eye: before-vs-20-day-before and 20-day-after-vs-after should agree in 100/100
  runs while the before/after pair differs; a modification failing the first pair is leaking the break
  (arXiv:1205.3763).
- **Incentive design and pre-registration for label collection.** The mood paper's human benchmark used
  output-agreement incentives (bonus within one Likert point of consensus), disabled copy-paste, and
  pre-registered the design on OSF before collection (arXiv:2607.13968). Inter-rater agreement must be
  reported (mean deviation −0.070; Bland–Altman limits ±0.49–0.63) before the labels are used as ground truth.
- **Parameter non-identifiability in the HAM.** The intensity of choice $\beta$ has essentially one published
  real-data estimate; the paper sweeps $\beta\in\{5,\dots,500\}$, shows the qualitative results survive, and
  warns the parameter "still remains a rather theoretical concept" (arXiv:1205.3763). Do not report a fitted
  $\beta$ as an estimate.

## 5. Recommended first implementation in FinRobot

1. **Daily sentiment mood index from transformer scoring (§2.3).** *What:* sentence-split the article text the
   layer can already retrieve, score with FinBERT, emit `index_pos_neg` and `index_ICI` per ticker-day, then
   aggregate with publisher fixed effects and volume weights. *Data:* EODHD `news_data`, Benzinga `/v2/news`,
   Alpha Vantage `NEWS_SENTIMENT`; bodies are a **gap** — start title+summary and measure the shortfall against
   a manual sample. *Passing result:* on a hand-labelled sample of ≥300 articles, macro-F1 ≥0.60 and
   correlation with human consensus ≥0.70 (the paper's out-of-sample floor). *Risk:* title-only scoring
   regresses to dictionary behaviour. *Effort:* M.
2. **MLSS long/short decomposition of the sentiment panel (§2.1).** *What:* fit the state-space model by
   Kalman filter + EM with $q=2$, diagonal $\Phi$, and expose the short-term component as a state variable.
   *Data:* the daily index from item 1 plus `core_stock_apis` returns. *Passing result:* filter S/N at least an
   order of magnitude above the local-level baseline, and the short-term correlation matrix explaining ≥10% of
   idiosyncratic return correlation (paper: 11.34%). *Risk:* the social channel is a gap, so half the intended
   input is missing; if the long-term block carries the weight, stop. *Effort:* M.
3. **Quantile-regression predictability gate (§2.2).** *What:* the $\chi^2$ test on $\mathrm{R}^1(\tau)$ with a
   pre-fixed nine-quantile grid and a chronological split. *Data:* filtered sentiment + daily returns.
   *Passing result:* significant $\mathrm{R}^1$ at $\tau\le0.05$ and $\tau\ge0.95$ for the short-term
   component only (paper: 12.7% / 11.9%), median-quantile $\mathrm{R}^1<1\%$. *Risk:* overlapping windows
   inflate significance; use non-overlapping or block-bootstrap inference. *Effort:* S–M.
4. **Cost-aware long/short overlay with R² trade gating (§2.2).** *What:* the vol-standardised logit signal
   with the rolling McFadden-$\mathrm{R}^2$ quantile gate, priced at 0.1%/side. *Data:* item 3's signal +
   `risk_free_curve` for the cash leg. *Passing result:* net Sharpe above the equal-weight benchmark
   (paper: 0.757 vs 0.469 after gating) with turnover reported. *Risk:* $\alpha$ tuned on the test set;
   fix it ex ante. *Effort:* S.
5. **Human-label acquisition loop (§2.5) for FinRobot's own sentiment ground truth.** *What:* entropy-ranked
   annotation of unlabelled articles, in small batches, with inter-rater agreement reported. *Data:* the
   article pool from item 1; a labelling budget. *Passing result:* macro-F1 improvement per 150 labels
   approaching the paper's AUC 0.74→0.92 trajectory on FinRobot's own corpus. *Risk:* no blockchain layer
   needed — the audit machinery does not transfer to trading. *Effort:* M.
6. **Behavioural-break diagnostic sandbox (§2.4), not a signal.** *What:* port the Brock–Hommes system with
   the herding/overconfidence/sentiment injections and the Cramér–von Mises + Jarque–Bera tests; run it on
   the five historical break dates against realised before/after shifts. *Data:* none live; empirical side
   uses daily closes. *Passing result:* reproduces the variance increase and kurtosis-decrease direction on
   ≥3 of 5 break dates. *Risk:* simulation-only, no tradable output. *Effort:* M.
7. **Missing-data/outlier preprocessing contract (§2.6).** *What:* a documented, repo-wide rule for
   sentiment-panel gaps and outliers, tying the semi-bounded-rationality principle to the MLSS fill rule.
   *Data:* none. *Passing result:* every series reports its missingness fraction and fill method; none with
   >7.5% missing enters the model. *Risk:* over-imputation manufactures signal. *Effort:* S.
8. **Do not build:** ESG/sustainability scoring (arXiv:2502.13148 has no estimator) and DeFi on-chain trust
   infrastructure (arXiv:2512.00142 is an architecture, not a market signal). Record both as out of scope.

## Appendix — papers read

| arXiv id | Title | Year |
|---|---|---|
| 1205.3763v2 | Behavioural breaks in the heterogeneous agent model: the impact of herding, overconfidence, and market sentiment | 2012 |
| 1910.01407v4 | A tale of two sentiment scales: Disentangling short-run and long-run components in multivariate sentiment dynamics | 2019 |
| 1305.6037v1 | Semi-bounded Rationality: A model for decision making | 2013 |
| 2512.00142v1 | DeFi TrustBoost: Blockchain and AI for Trustworthy Decentralized Financial Decisions | 2025 |
| 2607.13968v1 | Measuring Sentiment News with Transformer-Based Language Models | 2026 |
| 2502.13148v1 | Theoretical Frameworks for Integrating Sustainability Factors into Institutional Investment Decision-Making | 2025 |
