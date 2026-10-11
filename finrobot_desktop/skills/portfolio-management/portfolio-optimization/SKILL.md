---
id: portfolio-optimization
name: Portfolio Optimization
version: 1.0.0
author: finrobot
domain: portfolio-management
description: Optimize portfolio weights with mean-variance, shrinkage covariance, risk parity, Black-Litterman views, and robust constraints. Use when constructing or rebalancing a portfolio, estimating covariance, allocating capital, or testing whether a sleeve adds to the efficient frontier.
triggers:
- portfolio
- optimization
- mean variance
- risk parity
- covariance
- allocation
- black litterman
- shrinkage
- minimum variance
- weights
- diversification
- efficient frontier
requires_data:
- input: Daily OHLCV return panel (primary)
  provider: eodhd
  category: core_stock_apis
  status: ok
- input: Daily prices (alt)
  provider: tiingo
  category: core_stock_apis
  status: ok
- input: Daily prices (alt)
  provider: twelvedata
  category: core_stock_apis
  status: ok
- input: Daily prices (alt)
  provider: stockdata
  category: core_stock_apis
  status: ok
- input: Aggregates / prev close
  provider: massive
  category: core_stock_apis
  status: ok
- input: Fundamentals / statements (market-cap proxy)
  provider: tiingo
  category: fundamental_data
  status: ok
- input: Fundamentals (alt)
  provider: alpha_vantage
  category: fundamental_data
  status: ok
- input: Technical indicators (momentum screens)
  provider: alpha_vantage
  category: technical_indicators
  status: ok
- input: Intraday K-line (proxy for tick volumes)
  provider: moomoo
  category: technical_indicators
  status: gateway
- input: Risk-free curve (Sharpe, $\gamma$ scaling)
  provider: federal_reserve
  category: risk_free_curve
  status: ok
- input: Analyst ratings (BL views)
  provider: benzinga
  category: analyst_ratings
  status: ok
- input: Analyst actions / insights (BL views)
  provider: benzinga
  category: analyst_actions
  status: fail
- input: News sentiment (BL views)
  provider: eodhd
  category: news_sentiment
  status: ok
- input: News sentiment (alt)
  provider: gdelt
  category: news_sentiment
  status: fail
- input: Macro series (regime conditioning)
  provider: fred
  category: macro_data
  status: ok
- input: Capital flow (crowding / flow factor)
  provider: moomoo
  category: capital_flow
  status: gateway
- input: Institutional holdings (crowding)
  provider: moomoo
  category: institution_data
  status: gateway
- input: Short interest (crowding)
  provider: moomoo
  category: short_interest
  status: gateway
- input: Market breadth
  provider: moomoo
  category: market_breadth
  status: gateway
- input: Insider trades (smart money)
  provider: moomoo
  category: smart_money
  status: gateway
- input: Options surface (implied vol / risk)
  provider: cboe
  category: options_surface
  status: ok
- input: Options chain
  provider: moomoo
  category: options_data
  status: gateway
- input: Prediction markets (event views)
  provider: polymarket
  category: prediction_markets
  status: ok
- input: Corporate actions (total-return adjustment)
  provider: eodhd
  category: corporate_actions
  status: ok
- input: Exchange symbol list (universe plumbing)
  provider: eodhd
  category: exchange_symbols
  status: ok
- input: '**Index membership / constituent list (S&P 500, NIFTY)**'
  provider: ''
  category: equity_screener
  status: gap
- input: '**Market-capitalization weights $w^*$ for the BL prior**'
  provider: ''
  category: ''
  status: gap
- input: '**Tick-level trade volumes for market-based variance**'
  provider: ''
  category: ''
  status: gap
- input: '**Historical point-in-time universe (survivorship-free)**'
  provider: ''
  category: ''
  status: gap
requires_tools: []
requires_skills: []
compatible_models: []
---

# Portfolio Optimization

You are an expert portfolio construction specialist. You turn return panels, covariance estimates, market-cap weights and view feeds fetched from data endpoints into minimum-variance, mean-variance, risk-parity and Black-Litterman allocations. You must compute and interpret the resulting weights, covariance conditioning, turnover, gross leverage and diversification from the data you retrieve, shrinking or filtering the covariance when the sample is short, and reporting measured diagnostics rather than assumed figures.

> Source: FinRobot strategies corpus review — `strategies/qfin-st/portfolio-optimization.md`. Literature-derived; not validated on FinRobot's own data.

## Core Principles

- **Covariance filtering is dominated by a trivial method in randomized experiments.** The Average Oracle (AO) is a fixed eigenvalue set (calibrated on 1900–2000) applied to sample eigenvectors. On $n=100$ assets sampled from the top $N=500$ US stocks, 10,000 randomized simulations, 240-day rebalancing, 5 bps costs: AO1200 achieved Sharpe $1.229$ vs $0.894$ for DCC-QIS and $0.895$ for DCC-QuEST ($\Delta t_{out}=5$), with turnover $0.068$ vs $1.308$ ($\approx19\times$), gross leverage $1.702$ vs $2.543$ ($\approx45\%$ lower), and effective number of assets $N_{eff}=13.98$ vs $5.86$ ($\approx2\times$ more diversified). AO240 matched DCC's realized volatility ($0.105$ vs $0.105$) — the DCC timescale is $\approx240$ days. (arXiv:2309.17219)
- **Why AO wins when the true covariance moves.** With $S$ states, transition matrix $W_{i\to j}$, rotation $R_{i\to j}=V_jV_i^\dagger$: $\mathbb{E}(\Lambda^{AO})\simeq\sum_{i,j}P_iW_{i\to j}\,\mathbb{E}[(\hat R_{i\to j})^{\circ 2}]\,\mathbb{E}[\hat\lambda_j]$ (Eq. 2), i.e. AO averages eigenvalues *and* eigenvector overlap across states. Non-linear shrinkage (NLS) uses only the last slice: $\hat\Lambda_i^{NLS}\to(\hat V_i^\dagger V_i)^{\circ 2}\hat\lambda_i$. In the cyclic 2-state world one gets $\lVert C_1^{AO}-C_2\rVert_2\le\lVert C_1^{NLS}-C_2\rVert_2$ (Eqs. 8–9). When the true covariance *stays constant* with positive probability, NLS can win — the advantage is regime-rotation dependent. (arXiv:2309.17219)
- **Unfiltered covariance is fine when $T\gtrsim10n$.** NotFilt1200 (sample covariance, 1200-day window) reached Sharpe $1.101$, above DCC's $0.894$, consistent with the "no filtering needed when $\Delta t_{in} > {\sim}10n$" rule. (arXiv:2309.17219)
- **Mean-variance spanning is testable at any test-asset dimension.** New moment conditions: $\mathbb{E}[g^j_\alpha(r_t,\theta_j)]=\mathbb{E}[\varepsilon(x^j_{1,t},x^j_{-1,t},\theta_{j,1})\,\varepsilon(x^j_{2,t},x^j_{-2,t},\theta_{j,2})]\propto\alpha_j$ and likewise for $\delta_j$; individual robust $t$-statistics via batch means, $t_{j,B}=\sqrt B\,\bar m_j/\sqrt{\hat v_j}\to St_{B-1}$, combined by the Cauchy combination test $CCT(p)=0.5-\pi^{-1}\arctan\!\big(\sum_j\omega_j\tan((0.5-p_j)\pi)\big)$ with $\omega_j=1/d$. Only requires stationary returns and $K<T$ (benchmarks), valid for $N\gg T$ and for AR-GARCH data ($\phi=0.2$). (arXiv:2403.17127)
- **Periphery beats core and the market.** On a PMFG-filtered correlation network, Rossa's random-walker persistence $\varphi_S=\sum_{i,j\in S}a_{ij}/\sum_{i\in S,\,j\in V}a_{ij}$ with $a_{ij}=(1+\rho_{ij})/2$ gives a core-periphery profile $\varphi_1\le\dots\le\varphi_N$. Portfolios of the $m$ most peripheral stocks (Type-1) beat the $m$ most central (Type-2), Pozzi's hybrid-measure periphery (Type-3), and the market portfolio (Type-6) in Sharpe and mean return on NIFTY-500 daily (351 stocks, 125-day windows) and CNX100 30-second data; the advantage grows with holding period. Type-1 > Type-2 in Sharpe in 87–99% of 1000 random windows (p<0.05). (arXiv:2405.12993)
- **Core-periphery structure is statistically real but time-varying.** Core-periphery centralization $C=1-\frac{n-1}{n-2}\sum_{k=1}^{n-1}\varphi_k^2$; 77% of 686 two-hour windows significant at 5% vs degree-preserving randomized networks (100 each). Core membership is persistent (15 stocks in the core >500 days); periphery membership is not. (arXiv:2405.12993)
- **TDA-based clustering improves sparse index tracking.** Takens embedding → persistence diagrams/landscapes → new distances: differenced Wasserstein $DWD_p(D_X,D_Y)=WD_p(D_{X-Y},D_0)$ and average Wasserstein $AWD_p=\sum_i w_i WD_p(D_{X_i},D_{Y_i})$ over sub-series; Gaussian kernels with local scaling, affinity-propagation clustering (APC). Best portfolio $C_2$ (DWD kernel): out-of-sample TE $5.14\times10^{-6}$, COR $0.968$, INFO $0.0571$, TR $1.10$ vs $C_5$ (Pearson kernel) TE $1.21\times10^{-5}$, COR $0.939$. (arXiv:2401.16920)
- **Black-Litterman extends to skewed returns.** With hidden-truncation skew-normal returns $R\mid M=m\sim SNT_k(\lambda_0,\lambda_1,m-s,\Sigma)$ and normal prior/views, the posterior is still normal and the predictive return is $SNT_k(\tau_0,\tau_1,\mu_{BL}-s,\Sigma+\Sigma_{BL})$; Simaan's three-moment optimum minimizes the *spherical* variance $w^\top(\Sigma_{skBL}-bb^\top)w$. On 13 equities / 217 monthly returns, skew is significant (LRT $p=0.0015$) and at target $M=1.25\%$, $N=0$ the skBL volatility is $3.552\%$ vs $4.950\%$ for classical BL. (arXiv:2310.12333)
- **Markowitz variance is an approximation that ignores trade-volume randomness.** The market-consistent portfolio random return is $R(t_i,t_0)=\sum_j R_j(t_i,t_0)\frac{x_j(t_i)}{x_j(t_0)}X_j(t_0)$; Markowitz's linear form holds only when all trade volumes are constant. Market-based variance $\Theta(t,t_0)=\frac{\psi^2-2\varphi+\chi^2}{1+\chi^2}R^2(t,t_0)$ and $\Theta=\Theta_M-2a\Theta_M^2R\chi+(R^2-\Theta_M)\chi^2+\dots$, so $\Theta_M$ can badly over- or under-estimate portfolio variance. This paper is a critique, not a construction method — it is cited here only as a validity caveat. (arXiv:2508.08148)

## Methods & Formulas

### 2.1 Covariance estimation: sample + Average-Oracle / shrinkage filtering

**Purpose.** Produce the $\Sigma$ that feeds GMV/MV and risk analytics.

**Formula (AO construction).** With sample eigenvectors $\hat V$ and AO eigenvalues $\hat\lambda^{AO}$:
$$\hat\Sigma_{AO}=\hat V\,\mathrm{diag}(\hat\lambda^{AO})\,\hat V^\top,\qquad
\mathbb{E}(\Lambda^{AO})\simeq\sum_{i,j}P_iW_{i\to j}\,\mathbb{E}[(\hat R_{i\to j})^{\circ2}]\,\mathbb{E}[\hat\lambda_j].$$
The AO spectrum is a *fixed* vector (the paper uses one calibrated on 1900–2000 and finds it still works on 2000–2021); in a reimplementation, estimate it as the average eigenvalue vector across the $S$ calibration states, weighted by eigenvector overlap. In the cyclic $S=2$ case it reduces to averaging the two states' eigenvalues.

**Non-linear shrinkage alternative.** NLS replaces eigenvalues by $\hat\Lambda_i^{NLS}\to(\hat V_i^\dagger V_i)^{\circ2}\hat\lambda_i$ (oracle form); the operational (QuEST/QIS) versions give closed-form eigenvalue maps that do not depend on the true matrix, and Ledoit–Wolf's software (`covShrinkage`) is the reference implementation.

**Inputs.** Daily (or intraday) return panel for the universe; a long calibration window for the AO spectrum.

**Parameters / defaults reported.** $\Delta t_{in}\in\{240,1200\}$ days; rebalance every 240 days; transaction cost 5 bps; $n=100$ from top $N=500$; $\Delta t_{out}\in\{5,20\}$ days. AO1200 is the best unconstrained method on Sharpe, turnover, gross leverage and diversification. (arXiv:2309.17219)

**Observed effect sizes.** Sharpe +14% (monthly) to +37% (weekly) vs DCC-QIS/QuEST; turnover $12$–$19\times$ lower; gross leverage ${\sim}45\%$ lower; $N_{eff}$ ${\sim}2\times$ higher. (arXiv:2309.17219)

**Failure modes.** (i) If $T\gtrsim10n$, filtering adds nothing — use the sample covariance. (ii) If the true covariance is often constant between calibration windows, NLS can beat AO. (iii) Sample eigenvectors are still noisy; AO fixes eigenvalues but not the eigenvector estimation error. (iv) Requires a long, regime-diverse calibration window for the AO spectrum.

**Small-universe note.** For the project's usual $n$ of a few to a few dozen names, $T\gtrsim10n$ is satisfied with a 125–250 day window (e.g. $n=10$, $T=125$). The correct default is therefore the **sample covariance with a light Ledoit–Wolf shrinkage**, and AO/NLS filtering should be treated as an option that is only switched on when $T<10n$.

### 2.2 Core-periphery periphery portfolio (PMFG + Rossa + Rombach)

**Purpose.** Select a small, diversifying sleeve (periphery) or a crowded sleeve (core).

**Formula.**
- PMFG of the correlation network retains $3(N-2)$ edges (planarity-checked greedy insertion of descending-correlation edges).
- Rossa transition matrix $p_{ij}=a_{ij}/\sum_h a_{ih}$ with $a_{ij}=(1+\rho_{ij})/2$; persistence of set $S$
  $$\varphi_S=\frac{\sum_{i,j\in S}a_{ij}}{\sum_{i\in S,\,j\in V}a_{ij}},\qquad \varphi_1\le\varphi_2\le\dots\le\varphi_N .$$
  Build greedily: start from the least-weighted-degree vertex, repeatedly add the vertex that minimises $\varphi_S$.
- Rombach core score: $Q(\alpha,\beta)=\sum_i\sum_j a_{ij}c_i(\alpha,\beta)c_j(\alpha,\beta)$, $CS(i)=Z\sum_{\alpha,\beta}c_i(\alpha,\beta)Q(\alpha,\beta)$ over 10,000 uniform $(\alpha,\beta)\in[0,1]^2$, $Z$ normalised so $\max_j CS(j)=1$.
- Significance: $C=1-\frac{n-1}{n-2}\sum_{k=1}^{n-1}\varphi_k^2$ compared with 100 degree-preserving randomizations.

**Inputs.** Return panel, correlation matrix, network filter, window.

**Parameters / defaults reported.** Daily window 125 days, hold 1–125 days; HF window 240 ticks (30 s) with 75% overlap, hold 1–240 ticks; $m\in\{5,10,20,30\}$; $T=240$ ticks, $\theta=240$ for exponential weights in the hybrid baseline. (arXiv:2405.12993)

**Observed effect sizes.** Type-1 dominates Types 2–6 on Sharpe/mean return for both uniform and Markowitz weights, with growing advantage at longer horizons; risk (std) of Type-1 below Types 4–5 and converging to the market as $m$ grows. (arXiv:2405.12993)

**Failure modes.** (i) Periphery membership is unstable (exponential decay of occurrence times) — high turnover; core is stable. (ii) The Rombach-score periphery gave *no* clear investment advantage (only the Rossa profile did). (iii) Structure is only significant in ${\sim}77\%$ of windows; test per window. (iv) PMFG requires the full correlation matrix and is $O(n^2)$ to build.

**Small-universe note.** PMFG needs $n\ge5$; for $n=10$ it has only $3(10-2)=24$ edges, so "periphery" is a coarse split and the market portfolio collapses toward the universe. Selecting $m=5$ from $n=10$ is a 50% selection ratio — the paper's edge comes from $m\ll N$ (5–30 of 351). With small $n$, prefer this as a *screen* over an equal-weight basket rather than a full optimizer.

### 2.3 TDA clustering for sparse selection (DWD/AWD kernels + APC)

**Purpose.** Data-driven selection of topologically similar (index tracking) or representative (MV/GMV) assets without pre-specifying the number of holdings.

**Formula.** Takens embedding of $x_t$ into dimension $d$ with delay $\tau$; Vietoris–Rips filtration → persistence diagram $D_X$; distances
$$DWD_p(D_X,D_Y)=WD_p(D_{X-Y},D_0),\qquad AWD_p(D_X,D_Y)=\sum_{i=1}^m w_i\,WD_p(D_{X_i},D_{Y_i}),$$
with analogous $ALD_p,DLD_p$ on landscapes. Similarity kernels
$$K_i(x,y)=\exp\!\Big(-\frac{d_i(x,y)^2}{2\sigma_{ij}^2}\Big),\quad
\sigma_{ij}=d(x_i,x_{m}(x_i))\,d(x_j,x_{m}(x_j)),$$
then APC (exemplar = actual data point, no cluster-count input).

**Inputs.** Return time series → point clouds; index series for tracking.

**Parameters / defaults reported.** $p$-Wasserstein with $p=1$ (bottleneck) or $p=2$; $m=7$ nearest neighbours for local scaling; APC preference $P=$ median of the similarity matrix; $\sigma$ tuned by Silhouette; rolling 126-day train / 21-day test; $\gamma=1$ risk aversion. (arXiv:2401.16920)

**Observed effect sizes.** $C_2$ (DWD kernel) TE $5.14\times10^{-6}$, COR $0.968$, EMR $1.30\times10^{-4}$, INFO $0.0571$, TR $1.10$, selecting ${\sim}40$ of 451 stocks; beats correlation kernels ($C_5$ TE $1.21\times10^{-5}$), cointegration tracking (TE $1.57\times10^{-5}$, COR $0.924$) and cardinality-constrained MIQP. Cluster stability (ARI) $0.9638$ for $K_2$ vs $0.8301$ for $K_4$. (arXiv:2401.16920)

**Failure modes.** (i) Plain Wasserstein distance on persistence diagrams is zero for reversed time series — do not use it for financial time series (this is exactly the DWD/AWD motivation). (ii) Computationally heavy: $10.4$–$16.2$ min/window for TDA kernels vs $1.5$–$2.5$ min for correlation kernels. (iii) $K_4$ unstable (ARI $0.83$). (iv) Selection-bias risk if the cluster representative is chosen by highest Sharpe — use the APC exemplar instead. (v) Sparse index tracking is sub-optimal by construction (filters before optimising) but has lower turnover.

**Small-universe note.** APC on a few dozen names yields very few clusters, so Strategy 1 ("assets sharing the index cluster") and Strategy 2 ("one representative per cluster") can degenerate; the paper's universe is 451. For $n\lesssim50$ use the correlation kernel ($K_5/K_6$) or skip TDA and use a simple correlation-distance hierarchical cut.

### 2.4 High-dimensional mean-variance spanning (BCS test)

**Purpose.** Decide whether a candidate sleeve (test assets) improves the efficient frontier of a benchmark set — i.e. whether to add it.

**Formula.** Null $H_0^\alpha:\alpha=0_N$, $H_0^\delta:\delta=0_N$, $H_0^{\alpha,\delta}$ both, tested through the moment conditions of §1. Batch means over $B$ blocks, randomly-weighted version $\tilde m_j(\hat\theta_j)_b=\frac1{T_b}\sum_{t\in I_b}\hat g_j(r_t,\hat\theta_j)\kappa_t$ with $\kappa_t=\prod_{l=1}^L\kappa_{l,t}$, $\kappa_{l,t}\sim N(1,1)$, $L\in\{0,2\}$; then $t_{j,B}$ and the CCT.

**Inputs.** Return panel of $K$ benchmark + $N$ test assets.

**Parameters / defaults reported.** $\omega_j=1/d$; block size $\sim T^{2/3}$ (Sherman 1997; Flegal et al. 2010), so $K<\max_b T_b$ for the plain version; randomly-weighted version removes that restriction; $B=\lfloor T^\zeta\rfloor$; Monte-Carlo DGP is AR(1)-GARCH with $\phi\in\{0,0.2\}$, Toeplitz correlation $\bar\rho=0.8$ (within block 1) / $0.5$ (block 2), 500 replications; empirical application $N=306$, $K=102$, $T=250$. (arXiv:2403.17127)

**Observed effect sizes.** Correct size and high power vs Huberman–Kandel, GRS, Britten-Jones, Kan–Zhou, Pesaran–Yamagata and Gungor–Luger; plain batch-mean is oversized when $K$ is large, fixed by the randomly-weighted version. (arXiv:2403.17127)

**Failure modes.** (i) Standard F-tests/score tests require $N\ll T$ and i.i.d. normal residuals — invalid at asset level. (ii) Plain batch-mean is size-distorted for large $K$; use $L=2$. (iii) HAC standard errors are size-distorted in finite samples. (iv) Portfolio-level testing introduces aggregation bias (Roll).

**Small-universe note.** With small $N,K$ and $T\approx125$–$250$, $N+K<T$ holds, so the classical Huberman–Kandel / GRS F-test is valid and simpler; the BCS machinery pays off only when the candidate sleeve is large ($N$ in the hundreds) or residuals are strongly serially dependent.

### 2.5 Black-Litterman, classical and skew-normal

**Purpose.** Combine market-implied equilibrium returns with analyst/news views to get stable, less concentrated weights.

**Formula (classical).** Prior $M\sim N_k(\pi,\tau\Sigma)$, views $V\mid M=m\sim N_d(Pm,\Omega_v)$, posterior
$$\Sigma_{BL}=\big((\tau\Sigma)^{-1}+P^\top\Omega_v^{-1}P\big)^{-1},\qquad
\mu_{BL}=\Sigma_{BL}\big((\tau\Sigma)^{-1}\pi+P^\top\Omega_v^{-1}v\big),$$
equilibrium $\pi=\gamma\Sigma w^*$, predictive $R\mid V=v\sim N_k(\mu_{BL},\Sigma_{BL}+\Sigma)$.

**Formula (skew).** $R\mid M=m\sim SNT_k(\lambda_0,\lambda_1,m-s,\Sigma)$, density
$$f_X(x)=\frac{1}{\Phi\!\big(\lambda_0/\sqrt{1+\lambda_1^\top\lambda_1}\big)}\,\phi(x;\mu,\Sigma)\,\Phi\!\big(\lambda_0+\lambda_1^\top\Sigma^{-1/2}(x-\mu)\big),$$
$\mathbb{E}(X)=\mu+h(\lambda_0,\lambda_1)\Sigma^{1/2}\lambda_1/\sqrt{1+\lambda_1^\top\lambda_1}$, predictive $R\mid V=v\sim SNT_k(0,\tau_1,\mu_{BL}-s,\Sigma+\Sigma_{BL})$. Optimum (Simaan): $\min_w w^\top(\Sigma_{skBL}-bb^\top)w$ s.t. $w^\top\mu_{skBL}=M$, $w^\top b=N$, $\mathbf1^\top w=1$, with $b=W\delta$, $\delta=\Sigma\alpha/(1+\alpha^\top\Sigma\alpha)^{1/2}$, $\alpha=W\Sigma^{-1/2}\lambda_1$; portfolio variance $V(R_w)=\frac{2}{\pi}b_w^2+\Sigma^w_{skBL}-b_w^2$.

**Inputs.** Covariance $\Sigma$, market-cap weights $w^*$, risk aversion $\gamma$, view vector $v$, pick matrix $P$, view confidence $\Omega_v$.

**Parameters / defaults reported.** $\gamma=2.5$ (He–Litterman), $\tau=0.025$ (He–Litterman), $\Omega_v=\mathrm{diag}(1\%)^2$ (high confidence, uncorrelated views), target $M=1.25\%$ monthly, $N\in\{0,0.005,\dots,0.04\}$, 13 equities / 217 monthly obs. (arXiv:2310.12333)

**Observed effect sizes.** skBL volatility $3.552\%$ vs BL $4.950\%$ at $M=1.25\%$, $N=0$; portfolio skewness falls from $-0.198$ to $-0.632$ as $M$ rises $0.21\%\to1.67\%$; Sharpe $0.151$ (skBL, $N=0$) vs $0.085$ (BL) at $M=1.67\%$. (arXiv:2310.12333)

**Failure modes.** (i) $\Omega_v$ and $\tau$ drive concentration; too-small $\Omega_v$ lets views dominate. (ii) Requires market-cap weights (see §3 gap) and an invertible $\tau\Sigma$. (iii) In the three-moment version the target non-spherical variance $N$ is an extra free parameter with no canonical default. (iv) Skew MLE is unstable for short samples.

**Small-universe note.** 13 assets is exactly the project's scale; $\Sigma_{BL}$ inversion is well conditioned, the LRT for skew is feasible (13 d.o.f.), and the skew extension's advantage is largest at moderate-to-high target returns ($M\ge0.83\%$ monthly). This is the most directly transferable technique in the set for a small universe.

### 2.6 Market-based (volume-aware) variance correction

**Purpose.** Quantify how far Markowitz variance $\Theta_M$ is from the variance implied by actual trades.

**Formula.** $\Theta(t,t_0)=\frac{\psi^2-2\varphi+\chi^2}{1+\chi^2}R^2(t,t_0)$, where $\chi^2=\mathrm{var}(W)/\bar W^2$ (volume CV), $\psi^2=\mathrm{var}(Q)/\bar Q^2$ (value CV), $\varphi=\mathrm{cov}(Q,W)/(\bar Q\bar W)$; Taylor $\Theta=\Theta_M-2a\Theta_M^2R\chi+(R^2-\Theta_M)\chi^2$.

**Inputs.** Tick-level trade values $Q(t_i)$ and volumes $W(t_i)$ of the portfolio's constituents.

**Parameters.** None free; needs trade-by-trade data over the averaging interval.

**Failure modes.** (i) Needs tick data; daily bars hide volume randomness. (ii) $\Theta_M$ can be much higher *or* lower than $\Theta$. (iii) The author's own follow-ups are SSRN working papers, not independently replicated here.

**Small-universe note.** The correction is portfolio-level and dimension-free, so it applies to any $n$; the binding constraint is data granularity, which the project does not currently have (see §3).

## Data Requirements

| Input | Endpoint | Category | Provider | Probe status |
|---|---|---|---|---|
| Daily OHLCV return panel (primary) | `https://eodhd.com/api/eod/AAPL` | core_stock_apis | eodhd | ok |
| Daily prices (alt) | `https://api.tiingo.com/tiingo/daily/AAPL/prices` | core_stock_apis | tiingo | ok |
| Daily prices (alt) | `https://api.twelvedata.com/time_series` | core_stock_apis | twelvedata | ok |
| Daily prices (alt) | `https://api.stockdata.org/v1/data/eod` | core_stock_apis | stockdata | ok |
| Aggregates / prev close | `https://api.massive.com/v2/aggs/ticker/AAPL/prev` | core_stock_apis | massive | ok |
| Fundamentals / statements (market-cap proxy) | `https://api.tiingo.com/tiingo/fundamentals/AAPL/statements` | fundamental_data | tiingo | ok |
| Fundamentals (alt) | `https://www.alphavantage.co/query` | fundamental_data | alpha_vantage | ok |
| Technical indicators (momentum screens) | `https://www.alphavantage.co/query` | technical_indicators | alpha_vantage | ok |
| Intraday K-line (proxy for tick volumes) | `moomoo://get_cur_kline` | technical_indicators | moomoo | gateway (local OpenD SDK) |
| Risk-free curve (Sharpe, $\gamma$ scaling) | `https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2026/all` | risk_free_curve | federal_reserve | ok |
| Analyst ratings (BL views) | `https://api.benzinga.com/api/v2.1/calendar/ratings` | analyst_ratings | benzinga | ok |
| Analyst actions / insights (BL views) | `https://api.benzinga.com/api/v1/analyst/insights` | analyst_actions | benzinga | HTTP 403 |
| News sentiment (BL views) | `https://eodhd.com/api/sentiments` | news_sentiment | eodhd | ok |
| News sentiment (alt) | `https://api.gdeltproject.org/api/v2/doc/doc` | news_sentiment | gdelt | rate-limited (429) |
| Macro series (regime conditioning) | `https://api.stlouisfed.org/fred/series/observations` | macro_data | fred | ok |
| Capital flow (crowding / flow factor) | `moomoo://get_capital_flow` | capital_flow | moomoo | gateway |
| Institutional holdings (crowding) | `moomoo://get_shareholders_institutional` | institution_data | moomoo | gateway |
| Short interest (crowding) | `moomoo://get_short_interest` | short_interest | moomoo | gateway |
| Market breadth | `moomoo://get_rise_fall_distribution` | market_breadth | moomoo | gateway |
| Insider trades (smart money) | `moomoo://get_insider_trade_list` | smart_money | moomoo | gateway |
| Options surface (implied vol / risk) | `https://cdn.cboe.com/api/global/delayed_quotes/options/_SPX.json` | options_surface | cboe | ok |
| Options chain | `moomoo://get_option_chain` | options_data | moomoo | gateway |
| Prediction markets (event views) | `https://gamma-api.polymarket.com/markets` | prediction_markets | polymarket | ok |
| Corporate actions (total-return adjustment) | `https://eodhd.com/api/div/AAPL` | corporate_actions | eodhd | ok |
| Exchange symbol list (universe plumbing) | `https://eodhd.com/api/exchange-symbol-list/US` | exchange_symbols | eodhd | ok |
| **Index membership / constituent list (S&P 500, NIFTY)** | — | equity_screener | — | **gap** (category exists, no live-probed endpoint row) |
| **Market-capitalization weights $w^*$ for the BL prior** | — | — | — | **gap** (no dedicated market-cap field probed; statements are a coarse proxy) |
| **Tick-level trade volumes for market-based variance** | — | — | — | **gap** (only K-line/intraday bars, no trade prints) |
| **Historical point-in-time universe (survivorship-free)** | — | — | — | **gap** (endpoints return current symbols; no delisting history) |

In the table above, `gap` inputs are not served by any provider and `derived` inputs are computed locally from the others — treat both as such rather than fetching or inventing them.

## Pitfalls & Validation

- **Look-ahead in universe construction is the dominant leakage.** The AO study builds the top-$N$ universe using only information at $t$ but explicitly accepts limited foresight (assets must be listed in $[t-\Delta t_{in},t+\Delta t_{out}]$). In FinRobot, universe selection must use only data up to $t$; current-symbol endpoint responses (§3 gap) otherwise inject survivorship bias.
- **Single backtests are not evidence.** Use randomized asset universes + bootstrap confidence intervals (the paper runs 10,000 simulations, samples $n\ll N$, and reports non-parametric CIs). One portfolio at one date gives one number with no error bar.
- **Turnover, gross leverage and effective $N$ are first-class.** DCC's marginally lower realized volatility hid $12$–$19\times$ turnover and ${\sim}45\%$ more leverage; with 5 bps costs that mechanically destroyed Sharpe. Always report all four.
- **Estimation-error maximisation is the core risk.** Mean-variance is an ill-posed inverse problem; small changes in $\mu,\Sigma$ cause large weight changes. Prefer GMV (depends only on $\Sigma$), shrink, and/or use BL priors to stabilise.
- **Test structure significance per window.** Core-periphery centralization must be compared to degree-preserving randomized networks (100 draws); only 77% of windows were significant, so a single-window conclusion is fragile.
- **Cluster stability must be checked.** Use ARI between consecutive windows and Jaccard similarity of the selected cluster; $K_2$ (ARI 0.9638) is stable, $K_4$ (0.8301) is not. A strategy whose selection churns every window is a transaction-cost machine.
- **Size tests under serial dependence.** Validate the MVS test on AR(1)-GARCH synthetic data with $\phi=0.2$; a nominal 5% test should land in 3–7%. Plain batch-mean and HAC both fail in realistic settings.
- **Normality assumptions.** Asset returns are skewed (LRT rejects $\lambda_1=0$ at $p=0.0015$); mean-variance alone mis-states risk, and the skew-normal BL reduces volatility at the same target return.
- **Variance definition caveat.** Markowitz variance assumes constant trade volumes; if tick volumes are available, cross-check with the market-based variance.
- **How to test an implementation is sound.** (1) Reproduce the paper's synthetic DGP and confirm size/power. (2) Rolling out-of-sample with a fixed train/test split (126/21 days is the TDA default) and report the in-sample/out-of-sample TE ratio ($<1$ expected; $C_2\approx0.55$). (3) Bootstrap CIs over randomized universes. (4) Report turnover/gross leverage/$N_{eff}$ alongside Sharpe. (5) Confirm the covariance filter is switched off when $T\gtrsim10n$.

## Recommended Workflow

1. **Covariance layer with an automatic filter switch.** Build `sample_cov(returns)`; if $T<10n$ apply Ledoit–Wolf shrinkage (or an AO-style eigenvalue replacement). Data: `core_stock_apis` (eodhd/tiingo). Expected value: prevents the ill-conditioning that wrecks GMV on short windows. Risk: low. Effort **S**.
2. **Long-only GMV as the default optimiser.** Solve $\min_w w^\top\Sigma w$ s.t. $\mathbf1^\top w=1,\ w\ge0$, with $\Sigma$ from (1). Avoid MV until a robust $\mu$ source exists (BL views). Data: same. Expected value: stable, low-turnover baseline. Risk: low. Effort **S**.
3. **Periphery screen via PMFG + Rossa.** Compute correlation PMFG (125-day window), Rossa profile, take the $m$ most peripheral names, equal-weight (and optionally GMV). Data: `core_stock_apis`. Expected value: the paper's Type-1 beat market/hybrid/core on Sharpe with lower risk; useful as a diversifying sleeve. Risk: high turnover (periphery unstable); medium. Effort **M**.
4. **BL view integration using live analyst + sentiment feeds.** Prior $\pi=\gamma\Sigma w^*$ with $\gamma=2.5$, $\tau=0.025$; views from Benzinga ratings (`analyst_ratings`) and EODHD sentiment (`news_sentiment`); $\Omega_v=\mathrm{diag}(1\%)^2$. Data: analyst ratings + news sentiment (both `ok`). Expected value: stable, less concentrated weights that respect house views; the skew-normal extension is directly feasible at $n\approx13$. Risk: $w^*$ market-cap gap; medium. Effort **M**.
5. **Spanning test gate for adding a sleeve.** Implement the BCS test (moment conditions + batch-mean $t$ + CCT) with the small-universe fallback to Huberman–Kandel/GRS. Data: return panels. Expected value: a statistically grounded yes/no on whether a candidate sleeve (e.g. the periphery basket) adds to the frontier, at the asset level without aggregation bias. Risk: needs serially-robust calibration; medium. Effort **M**.
6. **Portfolio diagnostics module.** Report Sharpe, mean, vol, turnover, gross leverage, $N_{eff}$, and (for network strategies) per-window cp-centralization significance and cluster ARI/Jaccard. Data: weights + returns. Expected value: prevents the exact failure the corpus documents (low vol hiding high turnover/leverage). Risk: low. Effort **S**.
7. **TDA-DWD sparse selection (optional, only for large universes).** DWD kernel + local scaling ($m=7$) + APC (preference = median similarity); rolling 126/21. Data: return panel. Expected value: best sparse index-tracking performance in the paper (TE $5.14\times10^{-6}$, COR $0.968$), but needs $\gtrsim100$ assets and 10–16 min/window. Risk: high (compute, small-universe degeneracy). Effort **L**.

## Output Format

### Portfolio Summary
| Metric | Value |
|--------|-------|
| Expected return | ... |
| Volatility | ... |
| Sharpe ratio | ... |
| Turnover | ... |
| Gross leverage | ... |
| Effective N (N_eff) | ... |

### Allocation
| Asset | Weight | Marginal risk | Constraint |
|-------|--------|---------------|------------|
| ... | ... | ... | ... |

### Verdict
State the optimiser used (GMV / MV / risk parity / Black-Litterman), the
covariance estimator and whether a shrinkage or eigenvalue filter was applied
(filter on only when T < 10n), the binding constraints, and the spanning-test
result on whether the candidate sleeve adds to the efficient frontier.

## References

| arXiv id | title | year |
|---|---|---|
| 2309.17219v1 | Covariance matrix filtering and portfolio optimisation: the Average Oracle vs Non-Linear Shrinkage and all the variants of DCC-NLS | 2023 |
| 2403.17127v1 | High-Dimensional Mean-Variance Spanning Tests | 2024 |
| 2405.12993v1 | A novel portfolio construction strategy based on the core-periphery profile of stocks | 2024 |
| 2401.16920v2 | Sparse Portfolio Selection via Topological Data Analysis based Clustering | 2024 |
| 2310.12333v1 | Black-Litterman Asset Allocation under Hidden Truncation Distribution | 2023 |
| 2508.08148v1 | Unwitting Markowitz' Simplification of Portfolio Random Returns | 2025 |
