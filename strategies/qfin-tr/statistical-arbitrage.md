# Statistical Arbitrage — learnings from the q-fin.TR corpus

`63` of 2370 corpus papers matched this category (63 with PDFs); this doc is based on a close reading of `6`.

This document is about **trade construction** — universe selection, spread formation, basket
aggregation, leader/lagger ranking, sizing and capacity. The signal theory (cointegration screening,
Lévy/OU verification, z- vs q-scores, matching portfolios) is derived in
[`../qfin-st/mean-reversion-pairs.md`](../qfin-st/mean-reversion-pairs.md) and is not repeated here.
The corpus's construction contribution is narrow but sharp — graph clustering partitions the universe
into tradable sub-baskets, dynamic re-selection keeps crypto pairs alive across regimes, and end-to-end
policy learning collapses factor model, residual and weights into one net — and every one of these
constructions is transaction-cost-fragile.

## 1. What the corpus actually offers

- **The graph-clustering framework is real but cost-fragile.** Replicating Cartea et al.'s
  SPONGE$_{\rm sym}$ portfolio on S&P 500 daily data (2000-01-01 to 2022-12-31) gives, *without* costs,
  annualized return 10.24%, Sharpe 1.17, Sortino 2.09 — almost the original paper's 12.20%/1.10/2.01.
  A flat 0.05% cost **per side** collapses it to 2.44%, Sharpe 0.28, Sortino 0.49, with cumulative
  costs over the test period roughly **4× net profit** (arXiv:2406.10695). This is the most important
  number in the category.
- **Fix the drag by trading less and filtering harder, not by forecasting better.** Rebalance every
  10th rather than 3rd trading day and lengthen the clustering look-back from 5 to 30 days; then a
  5-model soft-voting classifier (MLP, AdaBoost, HistGradientBoosting, SGD, logistic regression) over
  14 graph/price features filters signals, keeping only those above the 90th percentile of predicted
  profitability ($P_2=0.60$; 0.68 solo). Out-of-sample 2006-03 to 2022-12: ARC 49.33%, ASD 38.01%,
  IR 1.30, Sortino 3.38, MDD 31.98%, max loss duration 2.10 y, Calmar 1.54, versus the same strategy
  with costs at ARC 1.13% / IR 0.14 and SPY at 9.12% / 0.45. Best single model:
  HistGradientBoosting, Brier 0.218, precision 0.653 (arXiv:2406.10695).
- **Cost sensitivity is monotone but small once the filter is in, and profit concentration is a
  defect.** Information ratio 1.43 (0% cost), 1.30 (0.05%), 1.23 (0.075%), 1.16 (0.10%) — the
  signal-filtered book is *largely immune* to the cost rate, unlike the unfiltered book (0.05% turns
  +10.24% into +2.44%). Most take-profit exits came from two low-volume, high-volatility S&P members
  (EP, CPWR); the step-like equity curve is a fingerprint of a few outliers, and the authors re-run
  with those names excluded as a sensitivity arm (arXiv:2406.10695).
- **Dynamic cointegration works in crypto, at minute granularity and with quote-aware fills.**
  BitMEX minute data, 2018-09-27 to 2019-10-02, 39 rolling weeks, three-month formation. Scenario 1
  (best pair each week): average monthly return 17.3% (ADF screen) / 13.9% (KSS screen), Sharpe 6.96
  and 6.57, annualized SD 30.0% / 25.8%. Scenario 2 (Johansen basket over 9 contracts): realized P&L
  1.44 XBT of which 0.81 XBT is *commission profit*, Sharpe 7.94, SD 24.7%, ~90% of months positive,
  max drawdown ≈0.15 XBT. Buy-and-hold is negative for every pair tested (arXiv:2109.10662).
- **Fees and pair identity decide the crypto result.** On BitMEX the maker fee is **negative**
  (−0.0250%) and the taker fee +0.0750% (funding 0.0100% per 8 h), and the strategy runs mostly limit
  orders, so 26–56% of P&L is the maker rebate — a construction choice, not alpha. The pairs that work
  are dominated by TRX, ADA and XRP; ETH-perp/ETH-futures, the most obvious pair, has Sharpe 0.29
  while ADA–TRX exceeds 20 in the single-pair sweep (arXiv:2109.10662).
- **A clean OU-vs-naive negative result.** On US names with market cap > $1 bn (Refinitiv/Datastream,
  3,986,371 rows × 26 columns; selection by minimum mean-squared distance on 2018–2020 returns and
  Engle–Granger validation — UAL–DAL statistic −12.0389, p = 0.000), a fitted OU model with percentile
  thresholds returned annualized 4.93%, vol 8.39%, Sharpe 0.468, Sortino 0.773, MDD −8.99%, win 53.3%;
  the naive 30-day rolling z-score on the *same* pairs returned 7.22%, 7.98%, 0.779, 1.203, −5.91%,
  54.6% (arXiv:2412.12458). Both books had near-zero inter-pair correlation; the OU fit added
  structure but not outperformance.
- **End-to-end policy learning beats the two-stage pipeline — before costs.** CRSP US equities
  2000-01 to 2022-12 (13,610 companies, 5,787 daily observations; filter close ≥ \$5, 20-day median
  market cap ≥ \$1 bn, 20-day median dollar volume ≥ \$1 m, refreshed monthly → 5,188 companies,
  avg 1,470/month). Pre-cost Sharpe: CAPM 0.13, Fama–French 5+MOM 0.52, PCA-8 0.96, PCA-10 0.92, best
  simple autoencoder + OU extraction 0.42, **end-to-end autoencoder policy 1.51–1.81** (15 latent
  dims: 1.81, mean 6.24%, SD 3.46%). An ANN extractor over OU statistics is negative everywhere
  (−0.31 to 0.12) (arXiv:2402.08233).
- **Robust lead-lag detection is a construction primitive.** Clustering sliding-window subsequences
  (q = 10, shift 1) from 679 US equities × 5,211 days (2000–2020), 14 ETFs × 3,324 days and 52 futures
  × 5,166 days, then aggregating relative lags with a voting threshold θ = 6, recovers synthetic lags
  exactly (MSE ≈ 0 for noise σ ≤ 1.5, ARI ≈ 0.8) where cross-correlation does not. On equities the
  leader/lagger strategy reaches Sharpe 0.839–0.847 versus the CCF benchmark's 0.595; **on ETFs and
  futures it fails to be consistently profitable** (ETF p-values 0.05–0.91) (arXiv:2305.06704).
- **The lead-lag layer can be made significance-bounded.** Symbolic transfer entropy converges to
  $2T\cdot\mathrm{TE}\to\chi^2(d)$, $d=(n_A n_{A^+}-1)(n_B-1)$, and the Vuong statistic tests whether
  predictor $B$ beats predictor $C$. On one day (2017-01-03) of tick mid-price signs for 1,177 NYSE
  and German-exchange stocks with ≥ 1,000 price variations each, Bonferroni over
  $n_t=n(n+1)/2=693{,}253$ tests at $q=0.01$ retains only **0.3% of links**; 767 nodes stay
  non-isolated and exchange assortativity is 0.56. Measured reaction time (NEM → ABX) is ≤ ~1 s
  (arXiv:2206.10173).
- **Off-topic note.** arXiv:2206.10173 is the weakest fit — primary listing q-fin.ST, an
  inference/network-identification paper rather than a construction one. It is retained because it
  supplies the only scale-free significance test and time-shift procedure for §2.5's lead-lag leg,
  where bootstrap alternatives are computationally infeasible. No assigned paper is out of category.

## 2. Implementable formulas & algorithms

### 2.1 Signed-graph clustering into tradable sub-baskets (SPONGE$_{\rm sym}$)

**Purpose.** Partition the actively-traded universe into groups of mutually co-moving stocks so that a
*group-relative* deviation is tradable as a single multi-name basket, and so that the same basket can
be re-used when the constituent relationship changes.

**Formula.** Build an undirected, signed, weighted graph whose adjacency matrix is the correlation
matrix $A$ of *residual* returns over the last $T$ days. Split $A=A^{+}+A^{-}$ into positive and
negative entries, form the Laplacians $L^{+}=A^{+}-D^{+}$ and $L^{-}=A^{-}-D^{-}$ with $D^{\pm}$ the
degree matrices, and symmetrize: $L^{+}_{\rm sym}=(D^{+})^{-1/2}L^{+}(D^{+})^{-1/2}$ and
$L^{-}_{\rm sym}=(D^{-})^{-1/2}L^{-}(D^{-})^{-1/2}$.
Take the $k$ smallest generalized eigenvectors of $(L^{+}_{\rm sym}+\tau^{-}I,\;L^{-}_{\rm sym}+\tau^{+}I)$
and run k-means++ on the embedding; $k$ is the smallest number of eigenvectors explaining 90% of the
correlation-matrix variance (or read off the Marchenko–Pastur bulk edge). Trade signal: the cluster
mean of the last 5 days' returns, long names below it / short above, re-evaluated every 10 days.

**Required inputs.** An $N\times T$ panel of *residual* returns (market/factor regression residuals, not
raw returns — otherwise the first eigenvector dominates and every cluster is the market); position
signs; per-signal graph features (local degree, global degree, graph density, cluster size, number of
clusters, all normalized by sub-graph or graph size) and conventional features (5-day cumulative
return deviation from the cluster mean, its sign, 10-day mean cluster return, 10-day mean stock
return).

**Parameters & defaults (the paper's own).** Look-back for clustering 30 days (raised from an
initial 5); rebalance every 10th trading day (raised from every 3rd); signal classifier trained on the
first 1,500 trading days from 2000-01-01; validation split 80/20 random; probability threshold
$P_2=0.60$ (90th percentile of the ensemble's validation distribution); grid search using Brier score
loss; MinMax scaler on the 14 features.

**Observed effect sizes.** Features normalized by *sub-graph size* compare across clusters; normalizing
by *graph size* absorbs the fact that the S&P 500 universe is not always 500 names. The classifier
turns a benchmark IR* of 0.14 (with costs) into 1.30 on the same period; the ensemble weights matter —
equal weighting drops IR* to 0.76 and ARC to 28.91%, and the solo HistGradientBoosting book to
0.91/31.58% (arXiv:2406.10695).

**Failure modes.** (i) The whole construction is a turnover machine: cost is 4× profit before the
rebalance-frequency and threshold changes. (ii) A single classifier probability threshold is fragile —
the paper re-ran *without* rounding the threshold and changed ARC from 49.33% to 47.15%, i.e. the
number of names traded is a live hyperparameter. (iii) Equity correlation is dominated by the market
factor; clustering must run on residuals. (iv) Names can leave the index; the universe must be
historical, not current.

### 2.2 Dynamic cointegration re-selection with OU half-life calibration

**Purpose.** Keep the tradable spread's parameters current in a regime-shifting market by re-selecting
the pair/basket every trading week from a rolling formation window, and using the OU half-life both
to rank candidates and to set the z-score look-back.

**Formula.** For each candidate pair, estimate the spread $S_t=P^1_t-\beta P^2_t$ (with a constant
intercept) by OLS; screen with the Engle–Granger/ADF test on the residual, optionally supplement with
the Kapetanios–Snell–Shin nonlinear test
$$\Delta S_t=\delta S^3_{t-1}+\epsilon_t,\qquad H_0:\delta=0,\ H_1:\delta<0,$$
and, for baskets of $n\ge3$ legs, the Johansen rank test on the error-correction form, retaining the
linear combination(s) with rank $r>0$ and coefficient p-values < 10%. Assume the chosen spread is OU,
$dS_t=\theta(\mu-S_t)\,dt+\sigma\,dW_t$, and calibrate $\theta$ by the regression
$\Delta S_t=a+bS_{t-1}+\epsilon_t$ with $\theta=-b/\Delta t$, so that
$$t_{1/2}=\frac{\ln 2}{\theta}.$$
Convert half-life into the look-back of the moving average used in the z-score, with the EMA and SMA
sharing a center of mass: $N_{\rm SMA}=2/\alpha_{\rm EMA}-1$ with $t_{1/2}=\ln 2/\alpha_{\rm EMA}$.
Then z-score with entry $|z_t|>2$, exit $|z_t|<1$ (thresholds in §2.3), and rebuild the coefficient
vector for trading: if $|\beta|<1$ divide the spread by $|\beta|$ and round coefficients to integers,
giving $\tilde S_t=w_1P^1_t+w_2P^2_t+c$ with $\min|w_i|=1$.

**Required inputs.** Minute-binned close prices for every leg; the best bid and best ask quotes and
market trades for the execution simulation; contract metadata (tick size, multiplier, funding);
per-leg volumes.

**Parameters & defaults (the paper's own).** Formation window 3 months; trading window 1 week
(39 non-overlapping weeks); cointegration confidence 1%; candidate ranking by *minimum half-life*;
Johansen candidate filters: coefficient p-value < 10%, unit portfolio value preferably < 1 XBT
(practice: < 3 XBT), then shortest half-life. For the basket scenario, the spread is
$S_t=\sum_i w_iP^i_t$ over the 9 BitMEX contracts with $\min_i|w_i|=1$ and integer weights.

**Observed effect sizes.** Scenario 1 (single pair) average monthly return 17.3% (ADF) / 13.9% (KSS);
scenario 2 (Johansen basket) Sharpe 7.94 vs 6.96/6.57; commission profit 35% (ADF), 26% (KSS) and
0.81/1.44 XBT (basket) of total P&L. The nonlinear screen does **not** improve profitability
(arXiv:2109.10662).

**Failure modes.** Jumps are the main source of bad signals; discrete tick sizes mean the
integer-weight spread does not exactly replicate the OLS spread; pair choice dominates the result
(per-pair Sharpe 0.29 to > 20); inverse-contract P&L conventions (XBT-denominated, multiplier
0.000001 for the quanto ETH contract) must be handled explicitly or the backtest is wrong; short-sale
availability varies by venue.

### 2.3 OU entry/exit: z-score and s-score with point-in-time thresholds

**Purpose.** Convert the spread into an entry/exit rule with parameters estimated on a training window
and applied unchanged out of sample — the only way to avoid fitting the exit threshold to the signal.

**Formula.** Discretize the OU SDE over step $\delta=t_{k+1}-t_k$:
$$S_{t+1}=aS_t+b+\epsilon,\qquad a=e^{-\lambda\delta},\quad b=\mu(1-e^{-\lambda\delta}),\quad
\mathrm{sd}(\epsilon)=\sigma\sqrt{\frac{1-e^{-2\lambda\delta}}{2\lambda}},$$
estimated as a linear regression; invert with $\lambda=-\ln a/\delta$,
$\mu=b/(1-a)$ and $\sigma=\mathrm{sd}(\epsilon)\sqrt{-2\ln a/(\delta(1-a^2))}$.
Signal: $Z=(S_t-\mu)/\sigma$; map $Z$ to a rolling percentile over a 90-day window (point-in-time) and
enter short the spread above the 75th percentile, long below the 25th, clear when $Z$ crosses the 50th
percentile. The autoencoder paper's variant uses the Avellaneda–Lee *s-score*
$$s_i=\frac{X_i(t)-m_i}{\sigma_{{\rm eq},i}},\qquad \sigma_{{\rm eq},i}=\frac{\sigma_i}{\sqrt{2k_i}},$$
opening long at $s_i=-1.25$ (short at $+1.25$), closing at $-0.5$ (long) / $+0.75$ (short), and
trading only names whose OU regression has $R^2>0.25$.

**Required inputs.** A training-window spread series (long enough for a stable $a$), the spread series
of the evaluation window, and — for the s-score variant — the residual series, its $k_i$ and $\sigma_i$,
and the regression $R^2$.

**Parameters & defaults.** Rolling window 30 days (naive baseline) vs the OU parameters on the full
training window; percentile look-back 90 days; entry/exit percentiles 25/75/50; s-score thresholds
±1.25 open, −0.5/+0.75 close; $R^2$ filter 0.25; next-day execution assumed.

**Observed effect sizes.** Naive 30-day z-score book: annualized return 7.22%, vol 7.98%, Sharpe 0.779,
Sortino 1.203, max drawdown −5.91%, win 54.6%, VaR(95%) −0.0081. OU book: 4.93%, 8.39%, 0.468, 0.773,
−8.99%, 53.3%, −0.0085. The OU book underperforms despite "capturing the correct signals and overall
trend" — the authors attribute this to sub-optimal tuning and non-stationary pairs
(arXiv:2412.12458).

**Failure modes.** Non-stationary pairs make the fixed $\mu,\sigma$ meaningless ("if the pair fails to
revert, the z-score has no anchor"); the paper's cointegration test was run on 2018–2020, *before*
COVID, so the trading window crosses a regime break; no transaction costs and no slippage in the
simulation; one-year test window; intra-pair correlation near zero does not imply factor neutrality.

### 2.4 End-to-end autoencoder policy: residual extraction and portfolio weights in one net

**Purpose.** Remove the three separate modelling choices (factor model → residual → signal → weights)
that each carry modelling risk, by training a single network that outputs portfolio weights and is
optimized directly on a risk-adjusted return objective.

**Formula.** With standardised returns $Z$ (capped at 3σ), an encoder $F=\mathrm{relu}(W^{(0)}Z+b^{(0)})$
and decoder $\hat Z=\tanh(W^{(1)}F+b^{(1)})$, the residual layer is $\hat Z-Z$ and the policy layer is
$$w_t=\tanh\!\big(W^{(2)}(\hat Z_t-Z_t)\big),\qquad w_t\leftarrow\frac{w_t}{\lVert w_t\rVert_1},$$
so target leverage is 1. The objective mixes reconstruction and trading:
$$\min_{\theta=\{W^{(0)},W^{(1)},W^{(2)},b^{(0)},b^{(1)}\}}\;
\lambda\,\mathrm{MSE}(Z_t,\hat Z_t)+(1-\lambda)\,\mathrm{Sharpe}(w_t,R_{t+1}),\qquad
\mathrm{Sharpe}=\sqrt{252}\,\frac{\mu_{p,t}}{\sigma_{p,t}},$$
with the realised portfolio return $r_{p,t}=\sum_i w_{i,t}r_{i,t+1}$.

**Required inputs.** A $N\times T_\tau$ matrix of standardised daily returns per rebalance date;
actual next-day returns for the Sharpe term; a universe filter for eligibility; optional Fama–French
factor returns and PCA eigenportfolio returns as benchmarks.

**Parameters & defaults (the paper's own).** $T_\tau=252$ days of standardised returns; cap at 3σ;
decoder tanh; Adam, learning rate $10^{-3}$, 10 epochs, new model fitted every trading day;
$\lambda=0.5$; hidden width 20 for the simple autoencoders; latent dimension swept 3–50; weights used
at $t+1$ are built only from data through $t$.

**Observed effect sizes.** Pre-cost Sharpe (best per family): CAPM 0.13, FF 0.30, FF3 0.33,
FF5+MOM 0.52, PCA-8 0.96, PCA-15 0.87, best simple AE + OU 0.42, end-to-end policy 1.51 (3 dims) /
1.67 (6 dims) / **1.81 (15 dims)** with mean 6.24% and SD 3.46%. The optimal latent count lands in the
literature's 10–15 range. OU+FFN extraction is negative for every model (−0.31 to +0.12)
(arXiv:2402.08233).

**Failure modes.** All results are **gross**; the authors state the strategy is not yet after-cost
competitive and propose turnover penalties and signal smoothing. Retraining daily changes the
architecture and creates turnover. The policy is unconstrained (no sector/factor neutrality), so the
book can load hidden exposures, and no transaction-cost or capacity analysis is provided.

### 2.5 Robust lead-lag detection via subsequence clustering and voting

**Purpose.** Rank a cross-section from "most leading" to "most lagging" so that leaders' momentum can
be used to trade laggers — a construction primitive when the pair relationship is directional rather
than symmetric.

**Formula.** From each of $n$ series of length $T$ extract overlapping subsequences (STS) of length
$q$ with shift $s$, giving $h=(T-q)/s+1$ STS per series and $N=n\cdot h$ in total. Cluster the enlarged
universe with k-means++ (or spectral clustering using the Gaussian kernel
$G_{ij}=\exp(-\|Y_{ia}-Y_{jb}\|^2/2\sigma^2)$, $\sigma=1/N$ by default and KNN-sparsified). For each
cluster $\phi_d$ and each pair $\{X_i,X_j\}$, collect the relative start-index differences
$$\Delta_d\{X_i,X_j\}=\{s^k_i-s^l_j\},$$
aggregate across all clusters, and estimate the pairwise lag by the **mode** (better than the median
in every reported experiment):
$$\gamma\{X_i,X_j\}=\mathrm{Mode}\Big(\bigcup_{d=1}^{K}\Delta_d\{X_i,X_j\}\Big).$$
Filter with a voting threshold so that only consistently co-clustered pairs survive:
$V_{ij}=|\bigcup_d \Delta_d\{X_i,X_j\}|$ if that count is $\ge\theta$ and $0$ otherwise, and
$\Gamma_{ij}=\gamma\{X_i,X_j\}$ when $V_{ij}\ne0$, else $0$. Rank rows of $\Gamma$ by row-sum to split
leaders $D_\alpha$ and laggers $G_\beta$, then trade
$\mathrm{PnL}^{t+\delta}_{G_\beta}=\mathrm{sign}(\mathrm{EWMA}(\mathrm{ret}^{t-p}_{D_\alpha}:\mathrm{ret}^{t}_{D_\alpha}))\cdot\mathrm{ret}^{t+\delta}_{G_\beta}$.

**Required inputs.** Daily close-to-close returns (market-excess, winsorized at ±0.15), with
zero-return days and mostly-empty names dropped; a rolling window of length $l$ for re-estimating
$\Gamma$.

**Parameters & defaults (the paper's own).** $q=10$, $s=1$, $l=21$, $K=11k$ clusters ($k$ = number of
factors in the simulation), Gaussian $\sigma=1/N$, voting threshold $\theta=6$, leader fraction
$\alpha=0.75$ (0.7–0.85 tested), prediction look-back $p=7$ days, horizon $\delta=7$ days, vol target
$\sigma_{\rm tgt}=0.15$ annualized.

**Observed effect sizes.** Synthetic: MSE ≈ 0 for $\sigma\le1.5$ with the voting threshold, ≈12
without it in the heterogeneous setting; ARI ≈ 0.8. Equities: $G_\beta$ Sharpe 0.839 (KM Mod) / 0.847
(SP Mod) vs CCF 0.595; $D_\alpha$ 0.892 (SP Med) vs 0.675; hit rate ≈0.52; PnL/trade 5.0 bps, with
Sharpe p-values ≈ 0. ETFs and futures: no consistent profitability (ETF $D_\alpha$ best Sharpe 0.538,
p = 0.051; futures $G_\beta$ p-values 0.51–0.98) (arXiv:2305.06704).

**Failure modes.** Clustering subsequences of a *single* series is known to be meaningless — the
method needs many input series; the voting threshold is needed for noisy (heterogeneous) systems;
k-means++ and spectral swap ranks depending on noise level (spectral better above $\sigma\approx1.5$);
the ETF/futures failure shows the primitive is asset-class dependent, not universal.

### 2.6 Asynchronous transfer-entropy inference for the lead-lag network

**Purpose.** Replace bootstrap significance with a closed-form test so a large lead-lag network can be
built in reasonable time, and measure the *timescale* over which information transfer exists.

**Formula.** Symbolic transfer entropy from $B$ to $A$ is the conditional-entropy reduction
$$\mathrm{TE}_{B\to A}=H(A^+|A)-H(A^+|A,B),$$
and under the null (no transfer) Wilks' theorem gives
$$2T\cdot\mathrm{TE}_{B\to A}\ \xrightarrow{d}\ \chi^2(d),\qquad d=(n_A n_{A^+}-1)(n_B-1),$$
where $n_A$, $n_{A^+}$, $n_B$ are the numbers of states of the past of $A$, the future of $A$, and
$B$ (binary states ⇒ $d=1$). To test whether predictor $B$ beats predictor $C$ for the same target,
define $Q=\mathrm{TE}_{B\to A}-\mathrm{TE}_{C\to A}$, $L=TQ$ and the Vuong statistic
$V:=L/(\sqrt{T}\,\omega)\xrightarrow{d}\mathcal N(0,1)$ with
$\omega^2=\mathrm{Var}[\log P(a^+|a,b)-\log P(a^+|a,c)]$, where $E[L]=0$ under $H_0$ exactly when the
two branching structures have equal degrees of freedom. Asynchronous matching assigns to each event of
$A$ the last known event of $B$; shifting $A$ forward by $\tau$ yields $\mathrm{TE}(\tau)$, and the
smallest $\tau^\*$ at which the test stops rejecting is the measured reaction delay.

**Required inputs.** Event tables with timestamps and a discrete state per event — here signed
mid-price changes $\mathrm{sign}(P_{t+1}-P_t)$ per stock, dropping names with fewer than 1,000
mid-price changes to stay out of the small-sample bias regime.

**Parameters & defaults (the paper's own).** Binary states; $T>1{,}000$ for the normal approximation
(analytic p-values are too permissive at $T=100$); Bonferroni threshold $q/n_t$ with
$n_t=n(n+1)/2$ and $q=0.01$ family-wise; trading-hours filter 14:30–16:30 UTC with 5 minutes trimmed
at each end to exclude the auction.

**Observed effect sizes.** On 1,177 stocks and $n_t=693{,}253$ tests, only 0.3% of links survive
Bonferroni; 767 nodes are non-isolated; exchange assortativity is 0.56, i.e. links concentrate within
venue as a configuration model would not predict. NEM → ABX transfer entropy is significant only up
to about 1 s (the paper notes this is not speculative: prices move too little in 1 s to beat costs).
The analytical test's true-positive rate exceeds the bootstrap's, at the price of slightly weaker
type-I control (arXiv:2206.10173).

**Failure modes.** Spurious transfer entropy from hidden common drivers (lagged correlation is neither
necessary nor sufficient for causality); finite-sample bias grows with the number of symbols;
bootstrap alternatives are infeasible at Bonferroni thresholds; sign-only encoding discards magnitude;
the method is a screening/allocation layer, not a P&L claim.

### 2.7 Turnover, cost and capacity accounting

**Purpose.** Make the construction decision *the* cost decision: given a signal and a probability of
profitability, choose trade count, per-name size and exit thresholds so that the strategy survives
realistic costs.

**Formula.** For a signal classified profitable with probability $P$ (from §2.1) and symmetric win/loss
factor $\lambda$ (absorbed by renormalization), the Kelly fraction is
$$f^\*=\frac{2P-1}{\lambda}\ \longrightarrow\ f^\*=2P-1$$
once all per-name fractions are rescaled to sum to one on each side. Exit thresholds decay with time
since rebalance: $\mathrm{Threshold}_{\rm tp}=\mathrm{THR}(10-T_D)/10$,
$\mathrm{Threshold}_{\rm sl}=0.05(10-T_D)/10$ and $\mathrm{Threshold}_{\rm RW}=\mathrm{Threshold}\cdot P$,
where $T_D$ is days since the last rebalance and $\mathrm{THR}=8\%$ is chosen so the average over the
9 days the take-profit can trigger equals the 4% training threshold.

**Required inputs.** Signed expected returns and classifier probabilities per signal; per-side
transaction cost; per-name dollar volume and price (for capacity); days since rebalance; the
rebalance calendar.

**Parameters & defaults (the paper's own).** Cost 0.05% per side, both at open and close; sensitivity
grid 0%, 0.05%, 0.075%, 0.1%; take-profit scale THR = 8%; stop-loss 5%; Kelly sizing vs equal
weighting compared directly; stop-loss threshold swept 1%/3%/10%; crypto commission structure as an
alternative cost model: maker −0.0250%, taker 0.0750%, funding 0.0100% per 8 h.

**Observed effect sizes.** With Kelly the book raises return at the expense of volatility and drawdown
duration (ARC 49.33% vs 50.33% without Kelly, but MDD 31.98% vs 33.94% and Sortino 3.38 vs 3.26); the
time-variant thresholds cut volatility and DD "by roughly the same factor" and raise Calmar/Sortino
slightly, and removing both changes IR* by < 2% — i.e. the risk-management overlay is nearly free but
not the source of alpha. The stop-loss sweep hurts at both ends: ARC 41.54% (1%) and 46.00% (10%) vs
49.33% base (arXiv:2406.10695). The crypto result attributes 26–56% of P&L to commission rebates
(arXiv:2109.10662).

**Failure modes.** A flat per-side cost hides a liquidity-dependent cost: the profitable S&P names are
the illiquid ones, so 0.05% is optimistic exactly where the P&L lives; turnover is capped by the
voting/threshold layer, not the sizing layer; a stop-loss on a mean-reverting spread closes at maximum
expected reversion; capacity is bounded by the *smaller* leg's dollar volume (the crypto paper's
"size must already be available at the quoted price" rule).

## 3. Data requirements → available endpoints

| Input | Endpoint | Category | Provider | Probe status |
|---|---|---|---|---|
| Daily adjusted OHLCV for the equity universe | `https://eodhd.com/api/eod/AAPL` | `core_stock_apis` | eodhd | ok |
| Daily OHLCV (secondary source) | `https://api.tiingo.com/tiingo/daily/AAPL/prices` | `core_stock_apis` | tiingo | ok |
| Intraday minute bars (execution/cost simulation) | `https://api.twelvedata.com/time_series` | `core_stock_apis` | twelvedata | ok |
| Intraday K-line via local OpenD gateway | `moomoo://get_cur_kline` | `technical_indicators` | moomoo | gateway (not live-probed) |
| Tradable symbol universe and exchange listing | `https://eodhd.com/api/exchange-symbol-list/US` | `exchange_symbols` | eodhd | ok |
| Fundamentals (market-cap / size universe filter) | `https://api.tiingo.com/tiingo/fundamentals/AAPL/statements` | `fundamental_data` | tiingo | ok |
| Dividends and splits (total-return adjustment) | `https://eodhd.com/api/div/AAPL` | `corporate_actions` | eodhd | ok |
| Top-of-book best bid/ask (nearest available quote) | `moomoo://get_market_snapshot` | `core_stock_apis` | moomoo | gateway (not live-probed) |
| **Historical index membership (S&P 500 constituents by date)** | — | — | — | **gap** |
| **Point-in-time market-cap and dollar-volume panel (CRSP-scale)** | — | — | — | **gap** |
| **Crypto spot/perpetual minute bars with best bid/ask (BitMEX et al.)** | — | — | — | **gap** |
| **Tick-by-tick mid-price event series for the lead-lag network** | — | — | — | **gap** |
| **Fama–French / eigenportfolio factor returns** | — | — | — | **gap** |
| **Per-name L2 depth and signed trades (fill modelling for the min-size rule)** | — | — | — | **gap** |

**What each gap costs, in the papers' own terms.** (i) *Historical index membership*: the graph paper
trades only names actually in the S&P 500 on each date (2000-01-01 → 2022-12-31, ≈5,750 days, universe
occasionally < 500 names); without it the backtest silently trades winners and the 49.33% ARC means
nothing (arXiv:2406.10695). (ii) *PIT fundamentals panel*: the autoencoder paper filters on 20-day
median market cap ≥ \$1 bn and dollar volume ≥ \$1 m refreshed monthly, cutting 13,610 companies to
5,188 (avg 1,470/month); the OU paper filters market cap > \$1 bn on a 3,986,371-row table. Per-name
statements cannot reproduce a monthly PIT filter without snapshot reconstruction (arXiv:2402.08233,
arXiv:2412.12458). (iii) *Crypto minute bars with quotes*: 39 weeks × 3-month formation of minute
closes **plus** best bid/ask and trades to decide if size was available — 12 months across 9 contracts,
and the catalog serves no crypto at all (arXiv:2109.10662). (iv) *Tick mid-price events*: the TE network
needs ≈1,177 stocks × ≥1,000 mid-price changes on one day and 693,253 Bonferroni tests; the bars the
catalog serves are orders of magnitude too coarse (arXiv:2206.10173). (v) *Factor returns*: every
benchmark in §2.1/§2.4 (PCA, FF3, FF5+MOM) is absent; PCA is estimable from the panel, the Fama–French
arms are not (arXiv:2402.08233). (vi) *L2 depth and signed trades*: the crypto fill rule and the §2.7
cost model cannot be validated against real depth; the top-of-book gateway snapshot is the only
quote-like feed (arXiv:2109.10662).

## 4. Pitfalls, validation and measurement

- **Look-ahead and survivorship.** Historical S&P constituents only; training frozen on the first
  1,500 trading days with all performance out of sample from 2006-03 (arXiv:2406.10695). Z-score
  percentiles are rolling-backward with next-day execution (arXiv:2412.12458). The autoencoder policy
  uses data through $t$ for the $t+1$ return, retrains on 252 past days, and reports only next-day
  out-of-sample results (arXiv:2402.08233). $\Gamma$ is re-estimated on a 21-day window and shifted
  forward one day (arXiv:2305.06704). The crypto split is walk-forward by construction
  (arXiv:2109.10662).
- **Multiple testing.** Three non-interchangeable corrections: Bailey–De Prado deflated Sharpe with
  per-strategy p-values (arXiv:2305.06704); Bonferroni over $n(n+1)/2$ TE tests at $q=0.01$, which
  discards 99.7% of links (arXiv:2206.10173); grid-search CV with Brier loss plus a t-test of IR*
  against SPY (t = 2118.84, df = 4225, p < 0.00001) (arXiv:2406.10695). The qfin-st mean-reversion doc
  quantifies pair-enumeration (≈1,250 false positives at uncorrected p = 0.01 on the S&P 500).
- **Costs change the sign of the conclusion.** 0.05% per side turns +10.24% into +2.44% annualized;
  the OU paper models no costs at all and says so (arXiv:2406.10695, arXiv:2412.12458). The crypto P&L
  depends on a negative maker fee — zero it and 26–56% of profit disappears (arXiv:2109.10662).
- **Regime and asset-class dependence.** Jump-driven signal failure in crypto motivates
  Markov-switching/Bayesian spreads (arXiv:2109.10662); the OU test window is pre-COVID while trading
  crosses it (arXiv:2412.12458); the lead-lag primitive works on equities but not ETFs or futures
  (arXiv:2305.06704).
- **Metric choice and null tests.** Report hit rate *with* avg-profit/avg-loss (a high hit rate can be
  a losing book) (arXiv:2406.10695); validate recovery on a synthetic lagged multi-factor model with
  known $L_{ij}$ (MSE ≈ 0, ARI ≈ 0.8) against a CCF null before touching real data
  (arXiv:2305.06704); benchmark analytic p-values against 10,000-sample bootstraps
  (arXiv:2206.10173).
- **Capacity is a rule.** Execute only when the traded size was available at the quote at least one
  period after the signal — applied to every leg (arXiv:2109.10662). Profit concentration in two
  illiquid names is what happens without it (arXiv:2406.10695).

## 5. Recommended first implementation in FinRobot

Ranked by (evidence weight) × (implementability with the current data layer):

1. **Survivorship-free universe builder.** `https://eodhd.com/api/exchange-symbol-list/US` plus a
   checked-in historical index-membership file (membership is a **gap**). *Passing:* the universe on
   any rebalance date equals the index members that date; delisted tickers appear in 2012, not 2022.
2. **Daily panel loader with corporate-action adjustment.** `https://eodhd.com/api/eod/AAPL`
   cross-checked with `https://api.tiingo.com/tiingo/daily/AAPL/prices`, applying
   `https://eodhd.com/api/div/AAPL`. *Passing:* adjusted close for a split/dividend name matches a
   hand-checked reference to 1e-6.
3. **Pair/cointegration engine.** Port the qfin-st mean-reversion pipeline (Engle–Granger + ADF,
   maximum-weight matching, OU half-life), add the crypto paper's KSS and Johansen variants.
   *Passing:* surviving-pair count matches qfin-st's Bonferroni-corrected range; no shared stocks.
4. **Graph-clustering basket selector.** Residualize on the market, build the signed correlation
   graph, run SPONGE$_{\rm sym}$ with the 90%-variance cluster count, emit cluster long/short weights
   at a 10-day rebalance. *Passing:* the 2006–2022 no-cost replication reproduces ARC ≈ 10%/Sharpe
   ≈ 1.1 and the cost-adjusted run collapses to single-digit returns.
5. **Turnover and cost accounting module** (§2.7): per-side cost, Kelly sizing $f=2P-1$, time-variant
   thresholds, capacity check against per-leg dollar volume. *Passing:* reproduces IR* 1.43 → 1.16
   across 0%–0.10% and prints cost/profit so a cost-dominated strategy is rejected automatically.
6. **OU z-score / s-score execution layer** (§2.3) with PIT percentile thresholds and integer-share
   reconstruction; uses `moomoo://get_cur_kline` (gateway) or `https://api.twelvedata.com/time_series`.
   *Passing:* reproduces the negative result (OU Sharpe below naive on the same pairs).
7. **Lead-lag ranking layer** (§2.5) on the daily panel. *Passing:* recovers the synthetic lag matrix
   (MSE ≈ 0 for σ ≤ 1.5), beats the CCF benchmark on equities, reports no edge on ETFs/futures.
8. **Significance-bounded lead-lag network (deferred).** §2.6 requires the tick **gap**; implement once
   a tick/mid-price feed exists. *Passing:* analytic χ² and Vuong tests match 10,000-sample bootstraps
   at 5%, and the Bonferroni network retains of order 0.3% of links.

## Appendix — papers read

| arXiv id | Title | Year |
|---|---|---|
| 2406.10695v1 | Statistical arbitrage in multi-pair trading strategy based on graph clustering algorithms in US equities market | 2024 |
| 2109.10662v1 | Evaluation of Dynamic Cointegration-Based Pairs Trading Strategy in the Cryptocurrency Market | 2021 |
| 2412.12458v1 | An Application of the Ornstein-Uhlenbeck Process to Pairs Trading | 2024 |
| 2402.08233v1 | End-to-End Policy Learning of a Statistical Arbitrage Autoencoder Architecture | 2024 |
| 2305.06704v3 | Robust Detection of Lead-Lag Relationships in Lagged Multi-Factor Models | 2023 |
| 2206.10173v1 | Statistical inference of lead-lag at various timescales between asynchronous time series from p-values of transfer entropy | 2022 |