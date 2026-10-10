# Econometrics & Forecasting — learnings from the q-fin.ST corpus

512 of 4372 corpus papers matched this category; this doc is based on a close reading of 9
(the 6 assigned papers plus three category papers — `1410.7799`, `2102.00968`, `2509.10483` —
pulled from the manifest because the assignment's emphasis (dynamic model averaging, Occam's
window, forecast combination, nowcasting) is not covered by the assigned six).

## 1. What the corpus actually offers

- **Dynamic Model Averaging (DMA) with a forgetting factor** gives a recursive, time-varying
  model-averaging forecast; in the euro-area GDP nowcast it beat both benchmarks decisively
  (RMSE 0.0043 vs 0.0088 for AR(2) and 0.0101 for a random walk) `(arXiv:1410.7799)`.
- **Dynamic Occam's Window (DOW / FEAR algorithm)** makes DMA feasible when $K=2^J$ models is
  too large, by keeping only models whose weight is within a factor $C$ of the best; for
  $T{=}45$, $J{=}25$, $N{=}1000$ retained models the cost is 0.68 % of full DMA, i.e. ~150×
  faster `(arXiv:1410.7799)`.
- **Pointwise CRPS learning** replaces scalar combination weights $w_{t,k}$ with weight
  *functions* $w_{t,k}(p)$ over the quantile level $p$; a proposition proves the pointwise risk
  can never exceed the constant-weight CRPS risk, and is strictly smaller whenever the optimal
  weights are non-constant `(arXiv:2102.00968)`.
- **Panel regression with time-varying coefficients** (LRVC) estimated year-by-year on an
  11-country × 29-year panel of 7 macro factors; pooled residual SD = 0.747 pp, but
  Jarque–Bera $p=0.0172$ and RMSE/MAE = 1.402 both reject Gaussian residuals `(arXiv:2510.04211)`.
- **A rigorous IID battery** (Ljung–Box on both $Z_t$ and $|Z_t|$, 4 simultaneous $p$-values,
  1 % threshold) shows that **no** raw or log corporate bond *rate* series is IID, and that only
  *log-spreads of logs* of lower-rated bonds pass — the log transform is the load-bearing step
  `(arXiv:2410.22498)`.
- **Two-parameter "balanced" forecasting families** (rate-of-interest / rate-of-discount, 24
  models × 8 criteria) beat both Holt–Winters and ARIMA on Air Passengers (SAE ≈1255 vs 2083 /
  2228), on US quarterly retail sales (≈1.289 M vs 1.716 M / 1.722 M) and on 467 S&P 500
  companies `(arXiv:2207.04882)`.
- **TAC max-norm exponential fitting** fits ExpAR-type nonlinear models without an initial
  guess, recovering simulated parameters to ~2 % with RSS 2.2e-6, and gives an exact
  *data-suitability* test for exponential-decay fitting `(arXiv:2402.04138)`.
- **A quantum conditional Boltzmann machine loses to its classical baseline**: on NARMA-10 the
  classical CRBM RMSE is 0.056 ± 0.013 while the fully-quantum QQRBM is 0.119 ± 0.028 and
  QFeatureQRBM 0.105 ± 0.009 (both significantly worse); the hybrid QCRBM is statistically
  indistinguishable `(arXiv:2607.24065)`.
- **DAMNETS** generates Markovian network time series via sparse *delta matrices* and dominates
  network generators (B–A degree-distribution MMD 8e-3 vs 14–16 for the baselines; financial
  correlation-network degree MMD 0.13 vs 0.14–0.95) `(arXiv:2203.15009)`.
- **Regime-conditioned equity-premium prediction**: a "Bullish Index" from the local Hurst
  exponent marks shocks; the macro-variable PC model then earns $R^2_{OS}=9.64\%$ in peak
  periods and the technical-indicator PC model $2.10\%$ in trough periods, with annualised
  certainty-equivalent gains of 11.96 % / 13.16 % `(arXiv:2509.10483)`.

## 2. Implementable formulas & algorithms

### 2.1 Dynamic Model Averaging with forgetting (DMA)

- **Purpose.** Recursive forecast averaging over a candidate model set when the generating model
  can change over time; gives automatic shrinkage and variable inclusion probabilities.
- **Formula.** Model $m_k$: $y_t = x_t^{(k)\top}\beta^{(k)} + \varepsilon_t^{(k)}$,
  $\varepsilon_t^{(k)} \sim N(0, \sigma_t^{2(k)})$. With predictive likelihood
  $L_k(y_t \mid y_{1:t-1})$:
  $$w_{t|t,k} = \frac{w_{t|t-1,k}\,L_k(y_t\mid y_{1:t-1})}{\sum_{\ell=1}^{K} w_{t|t-1,\ell}\,L_\ell(y_t\mid y_{1:t-1})},
  \qquad
  w_{t+1|t,k} = \frac{w_{t|t,k}^{\lambda}}{\sum_{\ell=1}^{K} w_{t|t,\ell}^{\lambda}}.$$
  The forecast is $\hat y_t = \sum_k w_{t|t-1,k}\,\hat y_{t|t-1,k}$. Dynamic Model Selection
  (DMS) replaces the average by the single arg-max model.
- **Inputs.** A vector of lagged candidate predictors $x_t$ (macro indicators + 5 GDP lags in the
  paper) and the target $y_t$ (year-on-year GDP growth).
- **Parameters/defaults.** Forgetting factor $\lambda = 0.99$ (Raftery et al. 2010); flat prior
  $w_{0|0,k}=1/K$; models estimated recursively with fixed parameters in the paper's baseline.
- **Observed effect.** Euro-area nowcast, 2003q1–2014q1: RMSE 0.0043 (DMA-R and DMA-E), MAE
  0.0033, MAX 0.0125; vs RW 0.0101 / 0.0067 / 0.0332 and AR(2) 0.0088 / 0.0059 / 0.0376. DMS is
  slightly worse (RMSE 0.0048). DMA-R (small model population) ≈ DMA-E (expanded), so the small
  population is preferred. A time-varying-parameter DMA **overreacted to the 2008 crisis** and
  did worse — the model *set* changed, not the coefficients.
- **Failure modes.** $K=2^J$ explodes with $J$; misspecified models still enter the denominator;
  DMS can beat DMA when data are noisy (Google-search predictors, Koop–Onorante) — the averaging
  advantage is not universal.

### 2.2 Dynamic Occam's Window (DOW, the FEAR algorithm)

- **Purpose.** Run DMA without evaluating the whole $2^J$ model space by dynamically pruning and
  re-admitting ("resurrecting") models.
- **Formula.** After renormalising weights over the current set $M_0(t)$, keep
  $$M_0(t) = \{\, m_k \in M_1(t) : w_{t|t,k} \ge C \max_{\ell:\,m_\ell\in M_1(t)} w_{t|t,\ell} \,\},$$
  where $M_1(t)$ expands $M_0(t-1)$ by all one-regressor neighbours. Iterate **F**orecast →
  **E**xpand → **A**ssess → **R**educe. Cost in notional units of computation:
  $$\mathrm{NUC}_{DMA} = 2^J T, \qquad \mathrm{NUC}_{DOW} = N\,\frac{T(T+1)}{2},$$
  so DOW wins when $2^J / N > (T+1)/2$.
- **Inputs.** Same as DMA; a valid initial model population.
- **Parameters/defaults.** Threshold $C \in (0,1]$; Madigan–Raftery used $C = 1/20$. In the paper
  $M_0$ never exceeded 10,000 models; a cap $N$ of 50,000+ is non-binding (equivalent to
  unconstrained Occam's window).
- **Observed effect.** $T{=}45$, $J{=}25$, $N{=}1000$: $\mathrm{NUC}_{DOW}/\mathrm{NUC}_{DMA} = 0.68\%$
  (~150× faster). Nowcast RMSE improved up to ~10,000 models and flattened thereafter; the
  algorithm automatically grows the population in turbulent periods (start of 2008–2009) and
  shrinks it in quiet ones (final $M_0$ size 186).
- **Failure modes.** Assumes (i) a valid initial population and (ii) models change slowly;
  re-estimates every model from scratch each period, so cost is quadratic in $T$; convergence of
  low-inclusion-probability coefficients can require up to 50,000 models.

### 2.3 Pointwise CRPS learning (aggregation across quantiles)

- **Purpose.** Combine probabilistic forecasts when experts are better in different parts of the
  distribution (centre vs tails) and at different times.
- **Formula.** Continuous Ranked Probability Score and its quantile-loss representation:
  $$\mathrm{CRPS}(F,y)=\int_{\mathbb{R}}\big(F(x)-\mathbf{1}\{x\ge y\}\big)^2 dx
  = 2\int_0^1 \mathrm{QL}_p\!\big(F^{-1}(p),\,y\big)\,dp,\qquad
  \mathrm{QL}_p(q,y)=\big(\mathbf{1}\{y<q\}-p\big)(q-y).$$
  Pointwise combination across quantiles:
  $$\tilde F_t^{-1}(p) = \sum_{k=1}^{K} w_{t,k}(p)\,\hat F_{t,k}^{-1}(p),\qquad
  w_{t,k}(p) = \sum_{l=1}^{L} \theta_{t,k,l}\,\phi_l(p),$$
  with $\phi$ a B-spline basis. Fully adaptive Bernstein online aggregation (BOAG) weight update:
  $$w_t^{\text{BOA}} = K w_0 \odot \mathrm{SoftMax}\!\big(R_t(1-V_t)\big),$$
  with $V_{t,k}=\sum_i r_{i,k}^2$ the cumulative variance of the instantaneous regret and
  per-expert, time-adaptive learning rates $\eta_{t,k}$.
- **Inputs.** For each expert $k$ and each $p$ on a grid $P$, the predicted quantile
  $\hat F_{t,k}^{-1}(p)$; realised $y_t$.
- **Parameters/defaults.** Grid $P=(0.01,0.02,\dots,0.99)$ (99 points) is standard; P-Spline
  smoothing penalty mixing parameter $\lambda = 1/2$ (smooths towards *constant* weights, which
  recovers plain CRPS learning as $\lambda\to1$); a forgetting grid $f\in\{2^x\}$ is essential
  when optimal weights drift.
- **Observed effect.** Prop. 1: pointwise risk $\le$ constant-weight CRPS risk, strict iff the
  optimal weight functions are non-constant. Theorem 1: BOAG attains selection rate
  $O(1/t)$ and convex-aggregation rate $O(1/\sqrt t)$ (up to a $\log\log t$ term). Empirical (EU
  ETS Phase III, 2092 daily EUA prices, 250-day rolling window, 1841 out-of-sample points), CRPS
  difference vs naive, ×$10^{4}$: BOAG P-Smooth **−0.170** ($p=0.055$), BOAG Pointwise **−0.182**
  ($p=0.039$), ML-PolyG −0.141, EWAG −0.089; best single expert I-GARCH$_t$ −0.037 (n.s.,
  $p=0.406$); BMA **+0.032** (worse than naive); ETS-ANN +2.101 (much worse).
- **Failure modes.** *Quantile crossing* — fix by rearranging (sorting) the predicted quantiles;
  Chernozhukov et al. show this never worsens quantile loss. Selection optimality needs a bounded
  conditional target with strictly positive density. B-Smooth (global smoothing) *underperformed*
  Pointwise here, while P-Smooth (local) helped — over-smoothing destroys the pointwise signal.
  Batch quantile regression is far more expensive than the online learner.

### 2.4 Panel regression with time-varying coefficients + orthogonal preconditioner

- **Purpose.** Estimate how the contribution of each macro/fundamental factor evolves over time
  in a panel where a static average would mask structural change.
- **Formula.** Linear regression with varying coefficients (LRVC), estimated year-by-year on the
  cross-section:
  $$\Delta y_{i,t} = \alpha_t + \sum_{j=1}^{d} \beta_{t-1,j}\,x_{i,t-1,j} + e_{i,t},
  \qquad i=1,\dots,N,\; t=1,\dots,T.$$
  Orthogonal preconditioner: standardise $z_{i,t,j}=(x_{i,t,j}-\mu_j)/\sigma_j$, take the pooled
  correlation matrix $\Omega = W\Lambda W^\top$, form $p_{i,t,k}=\sum_j W_{j,k}z_{i,t,j}$, fit
  $\Delta y_{i,t}=\alpha_{tP}+\sum_k \gamma_{t-1,k}p_{i,t-1,k}+e_{i,t}$ in the orthogonal basis,
  then recover
  $$\beta_{t-1,j} = \frac{1}{\sigma_j}\sum_k W_{j,k}\gamma_{t-1,k},
  \qquad \alpha_t = \alpha_{tP} - \mu^\top\beta_{t-1}.$$
  Because $W$ is orthogonal and all $d$ components are retained, fitted values and residuals are
  identical to the raw specification up to numerical precision — the transform is a pure
  conditioning fix.
- **Inputs.** An annual (or quarterly) panel of $d$ lagged macro factors and a growth-rate target.
- **Parameters/defaults.** $d=7$ (GDP/pc, price level, FDI, trade, GCF, central-gov debt, private
  debt), $N=11$, $T=29$ (1995–2024); pooled VIFs 1.1–4.0 (mean 2.6), so collinearity is moderate
  but the yearly design is ill-conditioned.
- **Observed effect.** Pooled residual SD 0.747 pp over 319 observations; mean residual 0.000;
  median 0.013; skew 0.037; kurtosis 4.549; IQR/SD 0.98; Jarque–Bera $p=0.0172$; RMSE/MAE 1.402.
  Country residuals reveal the danger: Czechia +0.192 and Latvia −0.207 mean residual — the
  deviations cancel in the pool but distort the factor-contribution decomposition.
- **Failure modes.** Collinearity inflates per-year slope variance; tiny per-year cross-sections
  ($N=11$) make the design poorly conditioned; a non-zero residual mean invalidates the additive
  $\Delta y_{i,t,j}$ contribution split; residual non-normality weakens t-based inference.

### 2.5 Ljung–Box IID battery on $Z_t$ and $|Z_t|$

- **Purpose.** Validate that a fitted RW / AR(1) model's innovations really are IID — the test
  most papers skip.
- **Formula.** $\hat Q_T(k) = T(T+2)\sum_{j=1}^{k}\hat\rho_T^2(j)/(T-j)$ with
  $\hat\rho_T(j)=\frac{1}{T}\sum_{i=1}^{T-j}(Z_i-\bar Z)(Z_{i+j}-\bar Z)$, asymptotically
  $\chi^2_k$. Models: RW, $Z_t=X_t-X_{t-1}$; or AR(1), $X_t=a+bX_{t-1}+Z_t$ by OLS.
- **Inputs.** Monthly rate/spread series and a volatility normaliser.
- **Parameters/defaults.** Test both $Z_t$ and $|Z_t|$; lags $k=5$ and $k=10$; pass iff **all
  four** $p$-values $>0.01$ (deliberately below 5 % to compensate for multiple testing).
- **Observed effect.** No rate series (raw or logged) passes. Only spreads pass, and only after
  logging: $S_{r,1}=\ln(R_r-R_{AAA})$, $S_{r,2}=\ln R_r-\ln R_{AAA}$, and
  $S_{r,3}=\ln(\ln R_r-\ln R_{AAA})$; lower-rated bonds (BBB, BB, B, CCC) pass, high-rated do not.
  Sometimes the innovations must also be divided by VIX, $W_t=Z_t/V(t)$, to pass — stock
  volatility acting as bond volatility.
- **Failure modes.** Zero autocorrelation of $Z_t$ is *not* IID: GARCH/Heston processes have zero
  ACF in levels but autocorrelated $|Z_t|$. Durbin–Watson tests only lag 1. Unit-root testing is
  deliberately bypassed here, so RW vs AR(1) cannot be distinguished by this test alone.

### 2.6 Balanced two-parameter forecasting families + powering

- **Purpose.** Nonparametric one-step-ahead forecaster and a cheap competitor to ARIMA /
  Holt–Winters that needs no trend/seasonal decomposition.
- **Formula.** Rate of interest $r_i=(y_{i+1}-y_i)/y_i$; rate of discount
  $d_i=(y_{i+1}-y_i)/y_{i+1}$. Order-$\ell$ mean $r_{i,\ell}=\mathrm{mean}(r_{i-\ell+1},\dots,r_i)$;
  forecasts $\hat x_{i+1}=x_i(1+r_{i,\ell})$ (from $X$ with rate series $R_Y$) or
  $\hat x_{i+1}=x_i/(1-d_{i,\ell})$ (from $D_Y$). Eight optimization criteria $\varepsilon_k$
  (SAE / SSE / weighted forms) select the preferred order $\ell_{\max}$ and length $L$; the
  "balanced" defaults are $\ell_{\max}=\lceil (n-1)/2\rceil$, $L=\lfloor (n-1)/2\rfloor$.
  *Powering* replaces $Y$ by $Y^{\alpha}$, $\alpha\in[0,1]$.
- **Inputs.** Two aligned series $X$ (level) and $Y$ (same or a related series whose rates drive
  the forecast).
- **Parameters/defaults.** 24 models ($]$, $[$, $\backslash$ × 8 criteria); balanced order/length
  as above; best $\alpha$ empirically in 0.4–0.9, mostly 0.6–0.8.
- **Observed effect.** Air Passengers 12-step: HW SAE 2083, ARIMA 2228; best model ≈1255
  ($\backslash_6$), monthly-best counts 62/100 vs HW 32 and ARIMA 26. US quarterly retail sales:
  HW 1,716,246, ARIMA 1,722,353, best model ≈1,289,315 ($[_5$) ≈25 % lower; 47/76 best quarters.
  Powering cut SAE by 8–19 % on 6 of the 9 enrollment series (e.g. −18.6 % for public 4-year).
  Stock market: 467 S&P 500 companies, last 100 daily forecasts, 72 models, 3,362,400 forecasts;
  mean "hit" score (# forecasts falling inside the next day's low–high range, out of 100) ≈71.1,
  best criteria $k=2$ and $k=5$ (mean 71.5–71.58); $X=$Close with $Y\in\{$Close, Open, Mid$\}$
  scores highest.
- **Failure modes.** The model *and* $\alpha$ are chosen on the same series, so the reported SAE
  reductions are in-sample — no out-of-sample protocol for the selection step. The "best model"
  is unstable across series (only 6/9 chose $\backslash_3$ under powering). No predictive
  distribution and no residual diagnostics.

### 2.7 TAC max-norm exponential fitting and the ExpAR model

- **Purpose.** Fit exponential-decay / exponential-autoregressive structure without an initial
  guess, and decide *in advance* whether a dataset is even suitable for exponential fitting.
- **Formula.** Best approximation in max-norm among $f(t)=a\exp(kt)+b$: for $n=3$,
  $a_k=(T_1-T_3)/(\exp(kt_1)-\exp(kt_3))$. A dataset is *admissible* when the best line $r(t)$
  alternates $\pm$ at three points (Chebyshev's Alternation Theorem); **Theorem 1**: the best
  exponential exists iff the data are admissible and condition ♠ fails (♠ = $T_1=\max$ and the
  second-largest value occurs after the minimum). Generalised ExpAR:
  $$x_t = c_0 + \sum_{i=1}^{p}\Big(c_i + \pi_i\,e^{-\gamma (x_{t-d}-z_i)^2}\Big)x_{t-i} + \varepsilon_t.$$
- **Inputs.** A single time series; for ExpAR the lag vectors $x_1=(x_2,\dots,x_{n-1})$,
  $x_2=(x_1,\dots,x_{n-2})$ recast it as a 2-D fit.
- **Parameters/defaults.** $p=d=2$ in the example; tolerance $10^{-7}$; fitted by the `nlstac`
  R package.
- **Observed effect.** ExpAR simulation (100 points, 98 used): true
  $(c_0,c_1,c_2,\pi_1,\pi_2,\gamma,z_1,z_2)=(-1.49,1.65,0.54,-0.44,-0.84,1.3,2.52,3.86)$;
  recovered $(-1.519,1.653,0.556,-0.445,-0.851,1.273,2.514,3.867)$, RSS $2.16\times10^{-6}$,
  MSE $2.2\times10^{-8}$. Demand curve: true $(Q_0,k,\alpha)=(48,3.42,0.006)$; recovered
  $(47.74,3.480,0.00551)$, MSE 0.0053.
- **Failure modes.** The paper states the ExpAR 2-D embedding is *beyond the proven convergence*
  of TAC — the result "stands to reason" but is not guaranteed. If max precedes min in the data
  (♠), no exponential is the best fit and a constant/line wins. Near-zero values blow up the
  *relative* error even when absolute error is bounded.

### 2.8 Markovian network time series generation (DAMNETS)

- **Purpose.** Generate dynamic graphs $p(G_t\mid G_{t-1})$ for financial-contagion and
  correlation-network simulation.
- **Formula.** Delta matrix $\Delta^{(t)}_{ij}=A^{(t)}_{ij}-A^{(t-1)}_{ij}\in\{-1,0,1\}$ (very
  sparse); encode $H^{(t-1)}=\mathrm{GAT}(X,A^{(t-1)})$; decode each row with a binary-tree
  sparse sampler (two MLPs for edge-add / edge-delete leaves); a Transformer self-attention layer
  ties rows together. Sample $\Delta^{(t)}$, then $A^{(t)}=A^{(t-1)}+\Delta^{(t)}$.
- **Inputs.** A training set of network time series $\{\{G_t^i\}_{t=0}^{T}\}_{i=1}^{N}$.
- **Parameters/defaults.** B–A: $n=100$, $m=4$, $T=96$; bipartite: $p=0.5$, $p^{con}=0.1$;
  community decay: $p_{int}=0.9$, $p_{ext}=0.01$, $f_{dec}=0.2$.
- **Observed effect.** B–A degree MMD 8e-3 (DAMNETS) vs 15.08 (AGE), 16.33 (TagGen), 14.01
  (DYMOND). Financial correlation networks (49 liquid US stocks, 5-minute returns, thresholded at
  1 SD, 97 weeks, $T=5$): degree MMD 0.13 vs AGE 0.14, DYMOND 0.16, TagGen 0.95. DAMNETS is the
  only model replicating all statistics across datasets.
- **Failure modes.** Markovian assumption; evaluation is MMD over hand-picked summary statistics
  (not a likelihood); correlation instability forced *random* train/test splits and 5 seeds —
  chronological splitting was explicitly rejected.

### 2.9 Exotic-method verdict: variational quantum conditional Boltzmann machines

**Question:** does the quantum machinery beat the classical baseline? **Answer: no, and the
paper says so.**

- NARMA-10 (input-driven, 10-step nonlinear recurrence): classical CRBM($3H^*$) RMSE
  **0.056 ± 0.013**; hybrid QCRBM 0.056 ± 0.014 (**statistically indistinguishable**,
  Holm-adjusted $p_{adj}=1.0$); fully-quantum QQRBM 0.119 ± 0.028 (**worse**, $p_{adj}=6.3\times10^{-5}$);
  QFeatureQRBM 0.105 ± 0.009 (**worse**, $p_{adj}=4.9\times10^{-7}$).
- Gaussian-process benchmark: CRBM 584 ± 511; QQRBM 1456 ± 803 (**worse**, $p_{adj}=0.024$);
  QCRBM 607 ± 537 (indistinguishable, $p_{adj}=0.187$).
- Iso-parameter (matched-budget) comparison at $P\in\{84,120,156,192\}$: the classical CRBM is
  lowest at three of four budgets and no CRBM-vs-QCRBM difference is significant at any budget.
- Power analysis bounds the null: with $n=12$ paired observations only medium-to-large effects
  $d\gtrsim d_{\min}\approx0.89$ are detectable, so a *small* quantum advantage is not excluded —
  but no evidence for one exists.
- Barren-plateau onset is earlier than theory predicts: fitted gradient-variance decay base
  $\hat b_3 = 0.520\pm0.013 < 2^{-1/2}\approx0.707$ at depth $L_Q=3$.

**Verdict for FinRobot:** do not invest in quantum/hybrid energy-based forecasters. The honest
classical baseline (a Gaussian–Bernoulli CRBM, or simply ARIMA/GARCH) remains the reference, and
the paper's own headline is "no systematic evidence of a quantum advantage at the available
sample size."

## 3. Data requirements → available endpoints

Every row below cites a real row of `strategies/endpoints.json`; probe status is copied verbatim
(`ok`, `gateway` = local OpenD SDK not reachable by the prober, `auth`, `rate_limited`, `connect`,
`http`). Anything no current provider can supply is marked **gap**.

| Input | Endpoint | Category | Provider | Probe status |
|---|---|---|---|---|
| Daily OHLCV / close series (all price-based methods) | `https://eodhd.com/api/eod/AAPL` | CORE_STOCK_APIS | eodhd | ok |
| Daily prices (secondary) | `https://api.tiingo.com/tiingo/daily/AAPL/prices` | CORE_STOCK_APIS | tiingo | ok |
| Daily prices (secondary) | `https://api.twelvedata.com/time_series` | CORE_STOCK_APIS | twelvedata | ok |
| Daily prices (secondary) | `https://api.massive.com/v2/aggs/ticker/AAPL/prev` | CORE_STOCK_APIS | massive | ok |
| Intraday klines for realized vol / Hurst (FDMAA) | `moomoo://get_cur_kline` | TECHNICAL_INDICATORS | moomoo | gateway (SDK) |
| Technical indicators (MA / momentum rules) | `https://www.alphavantage.co/query` | TECHNICAL_INDICATORS | alpha_vantage | ok |
| Macro series: GDP, HICP, PPI, unemployment, IP, oil, NEER, M3, credit, D/P inputs | `https://api.stlouisfed.org/fred/series/observations` | MACRO_DATA | fred | ok |
| Macro indicators (secondary) | `moomoo://get_macro_indicator_list` | MACRO_DATA | moomoo | gateway (SDK) |
| Corporate bond yields by rating (ICE BofA, e.g. `BAMLC0A1CAAAEY`) | `https://api.stlouisfed.org/fred/series/observations` | MACRO_DATA | fred | ok |
| VIX monthly/daily (`VIXCLS`) | `https://api.stlouisfed.org/fred/series/observations` | MACRO_DATA | fred | ok |
| Risk-free rate / Treasury curve | `https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2026/all` | RISK_FREE_CURVE | federal_reserve | connect (ReadTimeout) |
| Options surface / implied vol | `https://cdn.cboe.com/api/global/delayed_quotes/options/_SPX.json` | OPTIONS_SURFACE | cboe | http (307) |
| Options chain (implied vol, expected move) | `moomoo://get_option_chain` | OPTIONS_DATA | moomoo | gateway (SDK) |
| Expected move (option-implied) | `moomoo://get_option_underlying_overview` | EXPECTED_MOVE | moomoo | gateway (SDK) |
| News flow as nowcast indicator | `https://eodhd.com/api/news` | NEWS_DATA | eodhd | ok |
| News sentiment | `https://eodhd.com/api/sentiments` | NEWS_SENTIMENT | eodhd | ok |
| News sentiment (secondary) | `https://www.alphavantage.co/query` | NEWS_SENTIMENT | alpha_vantage | ok |
| Global news tone | `https://api.gdeltproject.org/api/v2/doc/doc` | NEWS_SENTIMENT | gdelt | rate_limited (429) |
| Analyst ratings (equity-premium conditioning) | `https://api.benzinga.com/api/v2.1/calendar/ratings` | ANALYST_RATINGS | benzinga | ok |
| Earnings calendar | `https://api.benzinga.com/api/v2.1/calendar/earnings` | EARNINGS_CALENDAR | benzinga | ok |
| Dividends (for D/P, total return) | `https://eodhd.com/api/div/AAPL` | CORPORATE_ACTIONS | eodhd | ok |
| Corporate actions (secondary) | `https://api.benzinga.com/api/v2.2/calendar/dividends` | CORPORATE_ACTIONS | benzinga | ok |
| Fundamental statements (panel regressors, factor inputs) | `https://api.tiingo.com/tiingo/fundamentals/AAPL/statements` | FUNDAMENTAL_DATA | tiingo | ok |
| Fundamentals (secondary) | `https://www.alphavantage.co/query` | FUNDAMENTAL_DATA | alpha_vantage | ok |
| Short interest (cross-sectional conditioning) | `moomoo://get_short_interest` | SHORT_INTEREST | moomoo | gateway (SDK) |
| Institutional holdings | `moomoo://get_shareholders_institutional` | INSTITUTION_DATA | moomoo | gateway (SDK) |
| Capital flow | `moomoo://get_capital_flow` | CAPITAL_FLOW | moomoo | gateway (SDK) |
| Market breadth (advance/decline) | `moomoo://get_rise_fall_distribution` | MARKET_BREADTH | moomoo | gateway (SDK) |
| Prediction-market probabilities (event nowcasts) | `https://gamma-api.polymarket.com/markets` | PREDICTION_MARKETS | polymarket | ok |
| Exchange symbol universe | `https://eodhd.com/api/exchange-symbol-list/US` | EXCHANGE_SYMBOLS | eodhd | ok |
| **Gap:** Eurostat / World Bank panel regressors (price-level index, FDI, trade openness, gross capital formation, central-gov debt, private-sector debt) | — | — | — | **gap** |
| **Gap:** real-time GDP *vintages* (the DOW paper's own caveat) | — | — | — | **gap** |
| **Gap:** MOVE bond-volatility index | — | — | — | **gap** |
| **Gap:** realised bond volatility | — | — | — | **gap** |
| **Gap:** Survey of Professional Forecasters GDP mean/dispersion | — | — | — | **gap** |

Notes. (i) FRED is routed under `MACRO_DATA` and can serve both the nowcast regressors and the
ICE BofA rating yields / VIX, so most of §2.1–2.2 and §2.5 are implementable today. (ii) The
`RISK_FREE_CURVE` and `OPTIONS_SURFACE` probes currently fail (timeout / 307), so any curve- or
surface-based factor must fail over to FRED (`MACRO_DATA`) or moomoo. (iii) moomoo rows are
reachable only through the local OpenD gateway (`moomoo://`), so they are effectively unavailable
in a hosted deployment. (iv) The panel-regression regressors of §2.4 are Eurostat/World Bank
series with no provider in the current inventory — that technique cannot be reproduced end-to-end
without adding a provider.

## 4. Pitfalls, validation and measurement

- **Vintage / look-ahead bias.** The DOW paper explicitly calls its exercise *pseudo*-real-time
  because it uses the latest GDP vintage and never-revised indicators `(arXiv:1410.7799)`. Any
  macro nowcast in FinRobot must use point-in-time data or declare the bias.
- **Multiple testing.** The bond paper lowers its pass threshold to 1 % (from the usual 5 %)
  precisely because it evaluates four simultaneous Ljung–Box $p$-values per series
  `(arXiv:2410.22498)`. The quantum paper applies Holm–Bonferroni across all simultaneous tests
  `(arXiv:2607.24065)`. Uncorrected multi-model "best model" selection (as in the balanced
  forecaster, `arXiv:2207.04882`) is a data-snooping trap.
- **Test the *right* null.** A zero autocorrelation function for $Z_t$ does not imply IID —
  GARCH/Heston have autocorrelated $|Z_t|$ with zero ACF in levels `(arXiv:2410.22498)`. Always
  test both $Z_t$ and $|Z_t|$.
- **Out-of-sample protocol.** The equity-premium paper uses an expanding-window recursive
  regression starting 1966, a historical-average benchmark (Welch–Goyal), Campbell–Thompson
  $R^2_{OS}$, and Clark–West MSFE-adjusted tests, and still finds in-sample $R^2$ of only 0.31 %
  (macro) and 0.49 % (technical) on average, with only 1 of 14 macro variables beating the HA
  benchmark over the full sample `(arXiv:2509.10483)`. Small in-sample $R^2$ is normal; the
  out-of-sample test is what matters.
- **Parameter stability.** Static panels hide structural change; the LRVC paper motivates
  time-varying coefficients with the 2008 and COVID breaks and notes that convergence conclusions
  are sensitive to the estimation strategy `(arXiv:2510.04211)`. DMA that varies *coefficients*
  overreacted to the crisis, whereas varying the *model set* worked `(arXiv:1410.7799)`.
- **Beware selection leakage.** The balanced-forecaster SAE improvements and the "powering"
  $\alpha$ are optimised on the same series being scored `(arXiv:2207.04882)`; treat them as
  in-sample and re-validate on a held-out window.
- **Regime conditioning is not optional for the premium.** Strong predictability appears only
  after a Bullish-Index shock (peak/trough = top/bottom 2.5 % quantile); unconditionally it is
  weak `(arXiv:2509.10483)`.
- **Null results need power analysis.** Do not read "no significant difference" between the
  hybrid quantum and classical CRBM as equivalence: with $n=12$ only $d\gtrsim0.89$ is
  detectable `(arXiv:2607.24065)`.
- **Distributional forecasts need crossing checks.** Pointwise quantile combination can produce
  crossing quantiles; rearranging never worsens the quantile loss `(arXiv:2102.00968)`.
- **How to test an implementation.** (1) Fit on a training window, forecast recursively
  out-of-sample, never touching future data; (2) report MAE *and* RMSE (RMSE/MAE ≈1.25 for
  Gaussian residuals — 1.402 here signals fat tails, `arXiv:2510.04211`); (3) run the Ljung–Box
  battery on $Z_t$ and $|Z_t|$; (4) use Diebold–Mariano or Clark–West for the comparison against
  a naive/AR/HA benchmark; (5) report a utility-based metric (certainty-equivalent return with
  transaction costs), not just $R^2_{OS}$ `(arXiv:2509.10483)`.

## 5. Recommended first implementation in FinRobot

1. **Macro nowcast module: DMA + Dynamic Occam's Window over FRED series.** Build a recursive
   DMA/DOW engine over the `MACRO_DATA` (fred) indicator set, using the FRED GDP growth series as
   target and a DOW window with $C$ near $1/20$ and $\lambda=0.99$. Data: FRED macro series (probe
   `ok`). Expected value: the paper's ~2× RMSE reduction vs AR(2) (0.0043 vs 0.0088) on a
   like-for-like quarterly nowcast. Risk: FRED vintages are not point-in-time → declare
   pseudo-real-time, as the paper does. Effort: **M/L**.
2. **Pointwise CRPS forecast-combination layer for every probabilistic output.** Wrap the
   existing quantile/distribution forecasts (vol, returns, earnings-move) in a BOAG pointwise
   combiner with a 99-point probability grid and P-Spline smoothing ($\lambda=1/2$), always
   followed by quantile rearrangement. Data: whatever the model suite already emits; no new
   provider needed. Expected value: the paper's −0.17×10⁻⁴ CRPS improvement over naive, with the
   guarantee (Prop. 1) that pointwise cannot be worse than constant weights. Risk: needs a
   history of expert forecasts; online learner is slow to stabilise in the first year. Effort: **M**.
3. **Panel TVC (LRVC) analyser for cross-sectional factor contribution.** Implement the
   year-by-year LRVC with the orthogonal preconditioner (eigendecomposition of the pooled
   correlation matrix, coefficient recovery via $\beta=\mathrm{diag}(\sigma)^{-1}W\gamma$) for
   equity-factor or sector panels built from `FUNDAMENTAL_DATA` (tiingo) and `CORE_STOCK_APIS`.
   Data: tiingo fundamentals (`ok`) + eodhd prices (`ok`). Expected value: honest decomposition of
   evolving factor contributions instead of a single average slope. Risk: **the paper's
   Eurostat/World Bank macro regressors are a data-layer gap** — this build only works on
   provider-backed fundamentals, and requires a cross-section of ≥10 names to be meaningful.
   Effort: **M**.
4. **IID residual-validation gate on every AR/RW model.** Add the four-$p$-value Ljung–Box
   battery ($Z_t$ and $|Z_t|$, $k=5,10$, 1 % threshold) as a mandatory pre-release check for any
   time-series model in FinRobot, with a log-spread transform helper. Data: none beyond existing
   series. Expected value: catches the stochastic-volatility residual failure that most model
   reports miss. Risk: low; short samples (FRED rate history is 3 years for some series) reduce
   power. Effort: **S**.
5. **Balanced two-parameter forecaster as a cheap ARIMA/Holt–Winters alternative.** Implement the
   rate-of-interest / rate-of-discount families with the 8 criteria and balanced order/length
   defaults, and the powering search over $\alpha\in[0,1]$. Data: `CORE_STOCK_APIS` daily prices
   (`ok`). Expected value: paper reports 8–25 % lower SAE than ARIMA/HW across series, and ~71/100
   next-day low–high hit rate on S&P 500 names. Risk: selection is in-sample in the paper —
   FinRobot must add a hold-out window before claiming the improvement. Effort: **S/M**.
6. **Document the quantum/exotic-forecaster rejection.** Record that the corpus's only rigorous
   quantum-forecasting comparison shows no advantage (`arXiv:2607.24065`), so FinRobot does not
   pursue quantum Boltzmann machines; keep the classical CRBM/ARIMA/GARCH baseline instead. Data:
   none. Expected value: prevents a costly dead end. Risk: none. Effort: **S**.

## Appendix — papers read

| arXiv id | Title | Year |
|---|---|---|
| 2607.24065 | Variational Quantum Conditional Boltzmann Machines for Time-Series Forecasting: Architectures, Symmetric Hyperparameter Evaluation, and a Nonlinear Benchmark | 2026 |
| 2510.04211 | Panel regression for the GDP of the Central and Eastern European countries using time-varying coefficients | 2025 |
| 2509.10483 | Equity Premium Prediction: Taking into Account the Role of Long, even Asymmetric, Swings in Stock Market Behavior | 2025 |
| 2410.22498 | New Time Series Models for Corporate Bond Log Yields | 2024 |
| 2402.04138 | TAC Method for Fitting Exponential Autoregressive Models and Others: Applications in Economy and Finance | 2024 |
| 2207.04882 | Variations on two-parameter families of forecasting functions: seasonal/nonseasonal models, comparison to exponential smoothing and ARIMA models, and applications to stock market data | 2022 |
| 2203.15009 | DAMNETS: A Deep Autoregressive Model for Generating Markovian Network Time Series | 2022 |
| 2102.00968 | CRPS Learning | 2021 |
| 1410.7799 | Dynamic Model Averaging in Large Model Spaces Using Dynamic Occam's Window | 2014 |

Papers 2102.00968, 1410.7799 and 2509.10483 were added from the corpus manifest (same category)
to cover the assignment's dynamic-model-averaging / forecast-combination / nowcasting emphasis,
which the six assigned papers do not address. None of the nine is off-topic.
