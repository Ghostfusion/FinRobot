# Correlation Networks & Econophysics — learnings from the q-fin.ST corpus

`912` of 4372 corpus papers matched this category (the largest cluster; 909 with PDFs); this doc is based on a close reading of `6`.

Two of the six assigned papers (household income/wealth; herding-based technology transfer) are macro/distributional econophysics with no tradable signal — they are summarised and explicitly marked non-actionable in §1. The remaining four (Marchenko–Pastur spectral cleaning, conditional mutual-information core–periphery networks, relative-entropy finite-sample theory, 2D Ising stylised facts) yield concrete, implementable machinery.

---

## 1. What the corpus actually offers

**Directly usable**

- **Marchenko–Pastur (MP) eigenvalue cleaning.** For i.i.d. Gaussian returns with $Q=T/N\ge 1$, the eigenvalue density of the empirical correlation matrix converges to
  $$P_{\rm rm}(\lambda)=\frac{Q}{2\pi\lambda}\sqrt{(\lambda_+-\lambda)(\lambda-\lambda_-)},\qquad \lambda_\pm=\left(1\pm\frac{1}{\sqrt Q}\right)^2 ,$$
  so eigenvalues inside $[\lambda_-,\lambda_+]$ are statistically indistinguishable from noise and only the $k$ eigenmodes above $\lambda_+$ carry structure `(arXiv:2607.10297)`. Splitting $C=\sum_{\gamma=1}^N \lambda_\gamma u^\gamma_i u^\gamma_j$ into $C^{\rm STR}$ (top $k$) and $C^{\rm RND}$ (rest) is the whole denoising step.
- **Denoising is *very* aggressive in practice.** On 2010–2022 daily returns the number of structure-bearing modes was 10 (NIFTY 200, $N{=}140$), 12 (NIFTY 500, $N{=}312$) and 16 (S&P 500, $N{=}425$); the corresponding $\lambda_+$ were 1.461, 1.722, 1.851 and the largest eigenvalues 35.87, 68.62, 172.15 — i.e. only 7.14 %, 3.85 % and 3.76 % of modes lie above $\lambda_+$ `(arXiv:2607.10297)`. The market mode alone is an order of magnitude beyond $\lambda_+$.
- **Cleaning strengthens core–periphery (CP) structure.** Using a Markov-chain persistence measure, CP centralisation
  $$Q^{cp}=1-\frac{1}{n-2}\sum_{k=1}^{n-1}\gamma_k$$
  (where $\gamma_S=\sum_{i,j\in V(S)}a_{ij}/\sum_{i\in V(S),j\in V(G)}a_{ij}$ is the random-walk persistence of subset $S$) is much higher for $C^{\rm STR}$ than for $C^{\rm FULL}$ or $C^{\rm RND}$: means 0.888 / 0.951 / 0.860 (structured) vs 0.651 / 0.706 / 0.643 (full) vs 0.551 / 0.549 / 0.563 (random) across the three indices `(arXiv:2607.10297)`.
- **Signal vs noise is distributionally separable.** Two-sample Kolmogorov–Smirnov $D\approx 0.98$–$1.00$ between the $Q^{cp}$ distributions of $C^{\rm STR}$ and $C^{\rm RND}$ (all $p<10^{-16}$); Wasserstein distances $W=0.217$–$0.402$ `(arXiv:2607.10297)`.
- **Denoised networks show scale-free degrees; noise networks do not.** MLE exponent $\hat\alpha=1+\big(\sum\ln(k_i/(k_{\min}-\tfrac12))\big)^{-1}$ gives $\hat\alpha=2.79$ (NIFTY 200) and $2.61$ (NIFTY 500) for structured MSTs with power-law $p$-values 0.452 / 0.526 ($>0.1$, plausible); the random-mode networks are rejected ($p\approx10^{-30}$ to $10^{-67}$) `(arXiv:2607.10297)`.
- **Periphery stocks beat core stocks out-of-sample.** With 500-day rolling estimation, top-$M$ periphery selection, 125-day holding, the structured-periphery strategy's signal-to-noise rises 0.65→0.81 (equal-weight, NIFTY 200, $M{=}10\to40$) and 0.69→1.21 (Markowitz); core-based portfolios underperform `(arXiv:2607.10297)`.
- **Conditional mutual information isolates *direct* links.** Regressing each stock on the market index (CAPM), computing histogram MI on residuals, and permuting to keep only significant pairs collapses dense raw-MI graphs to sparse, genuinely stock-to-stock graphs `(arXiv:2601.00395)`. Raw MI is dominated by common-factor co-movement; conditional MI ordering across regimes is pre-crash $<$ post-crash $<$ crash, consistent across US/Japan/Australia/India.
- **Crash topology signature.** During the COVID crash, conditional-MI MSTs compress and become fragile: US average path length 6.39→4.55, weighted degree 1.959→3.333, algebraic connectivity $\lambda_2$ 0.0059→0.0020, assortativity −0.383→−0.453, core concentration 0.194→0.164, periphery fragility 64.9→226.5 `(arXiv:2601.00395)`. Post-crash recovery is only partial.
- **Hellinger distance is a clean, parameter-light crash/regime detector.** With rolling window $W$, $H_t=\sqrt{\tfrac12\sum_b(\sqrt{p_b}-\sqrt{q_b})^2}$ and threshold $\mu_H+2\sigma_H$, the Feb–Mar 2020 crash is flagged simultaneously in all four QUAD markets `(arXiv:2601.00395)`.
- **Relative-entropy tests have closed-form asymptotics.** One-sample $2n\,D_{KL}(\hat p_n\|p)\xrightarrow{d}\chi^2_{k-1}$, with explicit Berry–Esseen and concentration bounds usable as conservative thresholds for divergence/change-point tests `(arXiv:2512.16411)`.
- **Ising/MSF diagnostic.** The microscopic stability factor $MSF=\frac{1}{2P}\sum_i|S_i(t)+S_i(t+\Delta t)|$ (fraction of agents not switching) drops *before* volatility spikes; cluster-size power law exponent $\approx1.9$ appears exactly at the critical point `(arXiv:2512.17925)`.

**Interesting but not actionable for FinRobot (macro/distributional)**

- **Two-class income/wealth structure.** ~97 % exponential (Boltzmann–Gibbs) bulk + ~3 % Pareto tail; derived parameter-free from Gibrat firm growth → Zipf firm sizes ($\alpha{=}1$) → max-entropy wages, giving owner-wealth exponent $\alpha_w=1/\theta\approx1.30$ from the firm-value scaling exponent $\theta=0.77$, and wealth/income temperature ratio $T_w/T_y\approx1.7$ yr `(arXiv:2604.22976)`. No tradable signal; only useful as an inequality/macro backdrop.
- **Herding model of technology transfer.** Kirman-type adoption with transition rates $\pi^+(x)=\frac{\sigma}{N}(1-x)+\frac{h}{N}x$, $\pi^-=0$, giving logistic productivity $A(t)=\dfrac{A_mA_0}{A_me^{-h t/(A_m-A_0)}+A_0(1-e^{-h t/(A_m-A_0)})}$ converging to a moving frontier `(arXiv:2604.11413)`. Country-level convergence, not a market signal.

---

## 2. Implementable formulas & algorithms

### 2.1 Marchenko–Pastur spectral cleaning of a correlation matrix
**Purpose.** Remove sampling noise from an $N\times N$ correlation matrix before it is used for portfolios, networks or risk.
**Formula.** Normalise returns $\tilde r_i(t)=(r_i(t)-\langle r_i\rangle)/\sigma_i$ with $\sigma_i=\sqrt{\langle r_i^2\rangle-\langle r_i\rangle^2}$; form $C_{ij}=\langle \tilde r_i(t)\tilde r_j(t)\rangle$; eigendecompose; keep $C^{\rm STR}_{ij}=\sum_{\gamma=1}^{k}\lambda_\gamma u^\gamma_i u^\gamma_j$ with $k=\#\{\lambda_\gamma>\lambda_+\}$.
**Inputs.** A $T\times N$ daily log-return panel, $T$ the estimation window.
**Parameters/defaults.** $Q=T/N$; $\lambda_\pm=(1\pm1/\sqrt Q)^2$. The papers use $N\in[140,425]$, $T\approx3200$ full-sample and a **500-day rolling window** for the tradable version ($Q\approx 1.2$–$3.6$ rolling) `(arXiv:2607.10297)`.
**Observed effect.** 10–16 retained modes; near-complete distributional separation from the noise component (KS $D\approx1$); $Q^{cp}$ up by ~0.2–0.4 absolute.
**Failure modes.** (i) MP assumes i.i.d. Gaussian returns — fat tails and volatility clustering violate it, so $\lambda_+$ is only a first-order guide; (ii) when $Q<1$ (short window, wide cross-section) the empirical matrix is singular and $\lambda_-=0$ — cleaning is mandatory, not optional; (iii) the market mode must usually be *kept* but it dominates weights, so portfolio use should shrink/demean it explicitly.

### 2.2 Core–periphery profile via Markov-chain persistence
**Purpose.** Rank assets into a dense core and a sparse periphery from any weighted adjacency/correlation graph.
**Formula.** Transition matrix $p_{ij}=a_{ij}/\sum_h a_{ih}$, stationary $\pi_i=CD(i)/\sum_j CD(j)$. Starting from the lowest-strength vertex, iteratively add the vertex that minimises persistence $\gamma_S=\sum_{i,j\in V(S)}a_{ij}/\sum_{i\in V(S),j\in V(G)}a_{ij}$, producing non-decreasing $\gamma_1\le\dots\le\gamma_N$ and coreness values; summarise with $Q^{cp}=1-\frac{1}{n-2}\sum_{k=1}^{n-1}\gamma_k$.
**Inputs.** Non-negative weighted matrix (raw correlations need an $|C|$ or distance-to-weight map).
**Parameters.** No free parameters beyond the graph construction; MST built on Euclidean distance $d_{ij}=\sqrt{2(1-C_{ij})}$ or, for MI, $d_{ij}=1/(mi_{ij}+\epsilon)$, $\epsilon=10^{-9}$ `(arXiv:2601.00395)`.
**Observed effect.** Structured networks: $Q^{cp}$ mean 0.86–0.95 vs 0.55–0.71 for full/random `(arXiv:2607.10297)`.
**Failure modes.** Coreness ordering is sensitive to the sparsification rule; on the raw correlation graph everything looks core-like because of the market mode. Always compare against degree-preserving randomised graphs (see §4).

### 2.3 Conditional p-threshold mutual information network
**Purpose.** Build a dependency graph that contains *direct* nonlinear stock–stock links after removing market-wide co-movement.
**Formula.**
1. CAPM residualisation: $r_i(t)=\alpha_i+\beta_i r_M(t)+\varepsilon_i(t)$, $ar_i(t)=r_i(t)-\hat\alpha_i-\hat\beta_i r_M(t)$ (OLS).
2. Histogram MI with $n_{\rm bins}=16$: $\hat I(X;Y)=\sum_{k=1}^{n_b}\sum_{l=1}^{n_b}\hat p_{kl}\log\frac{\hat p_{kl}}{\hat p_k\hat p_l}$.
3. Permutation test: $N_{\rm perm}=100$ shuffles of one series, $p=\dfrac{\#\{k:I^{(k)}_{\rm perm}\ge I_{\rm obs}\}+1}{N_{\rm perm}+1}$; keep $mi_{ij}=\hat I$ if $p\le\alpha$ else $0$.
4. Distance $d_{ij}=1/(mi_{ij}+\epsilon)$ ($\infty$ if $mi_{ij}=0$); MST via Prim on the largest connected component.
**Inputs.** $T\times N$ returns plus one market-index return series per market.
**Parameters/defaults.** $\alpha=0.05$ (robustness checked at 0.01 and 0.10), $n_{\rm bins}=16$, $N_{\rm perm}=100$, $\Delta t=1$ day. Universe: top 200 by market cap `(arXiv:2601.00395)`.
**Observed effect.** Number of significant links rises sharply pre-crash→crash; APL falls, $\lambda_2$ falls, $|r|$ rises (numbers in §1).
**Failure modes.** (i) MI from histograms is biased upward at small $N$ — the permutation test is what makes it usable; (ii) with $N=200$ and ~150 daily obs the sample is too small for stable MI (the paper leans on the significance filter, not on estimator accuracy); (iii) $\alpha$ controls sparsity strongly; (iv) empty bins break $d_{ij}$.

### 2.4 Core concentration & periphery fragility indices
**Purpose.** Two scalars that summarise CP reorganisation and systemic vulnerability.
**Formula.** $C_{\rm core}=\langle CE\rangle/\langle CC\rangle$ (mean eigenvector centrality over mean closeness centrality); $F_{\rm peri}=|r|/\lambda_2$ where $r$ is degree assortativity and $\lambda_2$ the second-smallest eigenvalue of the weighted Laplacian $L_w=D_w-A_w$ `(arXiv:2601.00395)`.
**Parameters.** None.
**Observed effect.** Crash: $C_{\rm core}$ falls (e.g. US 0.194→0.164), $F_{\rm peri}$ rises (US 64.9→226.5; Japan 78.0→281.3).
**Failure modes.** $F_{\rm peri}$ is a ratio of two noisy estimates and can blow up as $\lambda_2\to0$; treat as ordinal, not cardinal. Both are MST-dependent.

### 2.5 Hellinger-distance crash/regime detector
**Purpose.** Data-driven segmentation into calm / crash / post-crash without a volatility model.
**Formula.** Reference distribution $P_0$ from returns pooled over $(t-W,\dots,t-1)$ across all assets, current cross-section $P_1$ on day $t$; histogram each into $B$ bins; $H_t=\sqrt{\tfrac12\sum_{b=1}^B(\sqrt{p_b}-\sqrt{q_b})^2}$; flag crash when $H_t>\mu_H+2\sigma_H$ `(arXiv:2601.00395)`.
**Parameters.** $W=60$ trading days; bin range restricted to central quantiles to blunt outliers.
**Observed effect.** Synchronised threshold crossings in Feb–Mar 2020 across US/Japan/Australia/India.
**Failure modes.** $\mu_H+2\sigma_H$ is computed over the whole sample → mild look-ahead if applied in real time; use an expanding/rolling mean–std instead. Sensitive to bin count and to the central-quantile truncation.

### 2.6 Empirical relative-entropy divergence test
**Purpose.** Statistically calibrated test that two return distributions (or two regimes' return distributions) differ.
**Formula.** $D_{KL}(p\|q)=\sum_{i=1}^k p_i\log(p_i/q_i)$; discretise returns into $k$ states. One-sample: $2n\,D_{KL}(\hat p_n\|p)\xrightarrow{d}\chi^2_{k-1}$. Pre-asymptotic Berry–Esseen error $E_{n,k}=42(k-1)^{1/4}+16\sum_{i=1}^k\frac{(1-p_i)^{3/2}}{(np_i)^{1/2}}$, with $\kappa^{\rm up/down}_{n,k}(x)=x\pm\frac{x^{3/2}}{\sqrt{\mu n}}+O(1/n)$, $\mu=\min_i p_i$ `(arXiv:2512.16411)`.
**Inputs.** Two samples of discretised returns; $k$ bins.
**Parameters/defaults.** $\mu=1.37\times10^5$ observations needed for $E_{n,k}<1$ at $k=4$ (3.36×10³ at $k=2$) — i.e. Berry–Esseen bounds are pre-asymptotic, not finite-sample; Agrawal's bound $M^3_{k,n}(x)=e^{-nx}\big(1-\frac{k-1}{nx}\big)^{k-1}$ is the tightest usable concentration bound. Two-sample tests must keep $k\le8$ at $n=100$ to avoid empty bins and divergent estimates.
**Observed effect.** Asymptotic $\chi^2$ quantile is accurate except for $n<50$ and deep in the tail; Sanov bounds are far too loose, Mardia's slightly better, Agrawal's clearly best `(arXiv:2512.16411)`.
**Failure modes.** $D_{KL}$ is asymmetric and unbounded; the empirical version has a positive bias; two-sample $D_{KL}(\hat p_n\|\hat q_m)$ can be $+\infty$ if any $q$-bin is empty.

### 2.7 Ising microscopic-stability-factor diagnostic
**Purpose.** A cheap "how coherent is the cross-section right now" signal that leads volatility.
**Formula.** Local field $h_i(t)=J\sum_{\langle i,j\rangle}s_j(t)-\alpha s_i(t)|M(t)|$ with $M(t)=\frac1P\sum_i s_i(t)$; Glauber update $P(s_i{=}+1)=1/(1+e^{-2\beta h_i})$; $MSF(t,\Delta t)=\frac{1}{2P}\sum_i|S_i(t)+S_i(t+\Delta t)|$; returns $R(t)=\ln M(t)-\ln M(t-1)$ `(arXiv:2512.17925)`.
**Parameters/defaults.** $J=1$, $\alpha=4$ (the global-coupling term that produces intermittency), $T_c\approx2.26$; lattice $100\times100$; $2\times10^6$ steps with $25\times10^3$ thermalisation.
**Observed effect.** MSF ≈0.75 (disordered, Gaussian returns), 0.8–0.9 (critical, heavy tails, cluster exponent ≈1.9), →1 (ordered, returns vanish); sudden MSF drops precede volatility spikes.
**Failure modes.** Pure simulation — never calibrated to market data. The "price = magnetisation" mapping is a metaphor; use only the *shape* of the MSF-as-leading-indicator idea, replacing spins by sign(return − median) or by sector breadth.

---

## 3. Data requirements → available endpoints

Every row below cites a real probe row from `strategies/endpoints.json`.

| Input | Endpoint | Category | Provider | Probe status |
|---|---|---|---|---|
| Daily adjusted close panel ($T\times N$), primary | `https://eodhd.com/api/eod/AAPL` | core_stock_apis | eodhd | ok |
| Daily close panel, fallback | `https://api.tiingo.com/tiingo/daily/AAPL/prices` | core_stock_apis | tiingo | ok |
| Daily close panel, fallback | `https://api.twelvedata.com/time_series` | core_stock_apis | twelvedata | ok |
| Daily close panel, fallback | `https://api.massive.com/v2/aggs/ticker/AAPL/prev` | core_stock_apis | massive | ok |
| Universe / symbol list (build $N$-asset cross-section) | `https://eodhd.com/api/exchange-symbol-list/US` | exchange_symbols | eodhd | ok |
| Market-index return $r_M$ for CAPM residualisation | `https://eodhd.com/api/eod/AAPL` (swap symbol to `^GSPC`/index ticker) | core_stock_apis | eodhd | ok |
| Macro regime series for conditioning (rates, spreads) | `https://api.stlouisfed.org/fred/series/observations` | macro_data | fred | ok |
| Event/earnings windows for event-conditioned networks | `https://api.benzinga.com/api/v2.1/calendar/earnings` | earnings_calendar | benzinga | ok |
| News sentiment for regime/news conditioning | `https://eodhd.com/api/sentiments` | news_sentiment | eodhd | ok |
| News sentiment, fallback | `https://www.alphavantage.co/query` | news_sentiment | alpha_vantage | ok |
| News sentiment, fallback | `https://api.gdeltproject.org/api/v2/doc/doc` | news_sentiment | gdelt | rate_limited |
| Crash/event probability (prediction market) | `https://gamma-api.polymarket.com/markets` | prediction_markets | polymarket | ok |
| Risk-free rate for Sharpe/Sharpe-difference tests | `https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2026/all` | risk_free_curve | federal_reserve | **failed** (`connect`) |
| Implied-vol index / VIX term structure | `https://cdn.cboe.com/api/global/delayed_quotes/options/_SPX.json` | options_surface | cboe | **failed** (`http`) |
| Short interest (crowding/periphery proxy) | `moomoo://get_short_interest` | short_interest | moomoo | gateway (not live) |
| Market breadth (advance/decline for MSF analogue) | `moomoo://get_rise_fall_distribution` | market_breadth | moomoo | gateway (not live) |
| Capital flow (periphery vs core flows) | `moomoo://get_capital_flow` | capital_flow | moomoo | gateway (not live) |
| Sector / GICS classification (sector-mode interpretation, CP labelling) | — | — | — | **gap** |
| Correlation / covariance / MI matrices | derived from returns above | — | — | derived (no provider) |
| Hellinger/MSF/CP/Q^cp statistics | derived | — | — | derived (no provider) |

Notes: `fmp`, `yfinance`, `finnhub` and `sec_edgar` appear in `categories.py::PRIORITY` but are not in the live-probed inventory, so the rows above use only probed providers. Sector classification is a genuine gap — the corpus repeatedly interprets eigenmodes as sector modes but FinRobot has no category that returns GICS sectors.

---

## 4. Pitfalls, validation and measurement

**Leakage**
- MP bounds must be estimated on the *same* window used to clean: using full-sample eigenvalues to denoise a rolling portfolio is look-ahead. The papers explicitly use a 500-day rolling estimation window and a separate 125-day out-of-sample holding period `(arXiv:2607.10297)`.
- The Hellinger threshold $\mu_H+2\sigma_H$ and the MI permutation null must be computed within the estimation window only; computing them on the full sample leaks the crash `(arXiv:2601.00395)`.

**Overfitting / estimator bias**
- Empirical relative entropy is positively biased; the one-sample limit is $\chi^2_{k-1}$, not normal, so naive z-tests are wrong `(arXiv:2512.16411)`.
- Histogram MI is upward-biased at small $N$; the permutation filter is the correction, not optional `(arXiv:2601.00395)`.
- Berry–Esseen bounds for relative entropy only beat the asymptotic approximation for very large $n$ ($>1.37\times10^5$ at $k=4$); for realistic windows prefer the asymptotic $\chi^2$ quantile plus a concentration bound, not the Berry–Esseen bound `(arXiv:2512.16411)`.
- Retained-mode count $k$ is data-dependent per window; a hard-coded $k$ re-introduces the arbitrariness MP was meant to remove.

**Regime caveats**
- MP assumes stationary i.i.d. Gaussian returns; volatility clustering, fat tails and regime shifts violate it. The corpus sidesteps this by conditioning (crash vs non-crash) `(arXiv:2601.00395)` — do the same rather than trusting one global $\lambda_+$.
- Correlations rise and converge in crashes, so *all* assets look like a core; conditional MI on CAPM residuals is what restores discrimination `(arXiv:2601.00395)`.
- Post-crash structure does not return to pre-crash: recovery is partial and heterogeneous across markets, so a denoising model fitted pre-crash will mis-rank assets afterwards `(arXiv:2601.00395)`.
- $Q=T/N$ must be reported. For $N=200$ and a 150-day window $Q=0.75<1$ — the MP formalism does not apply and the correlation matrix is singular; this is exactly why the crash paper uses MI rather than correlation.

**How to validate an implementation**
1. **Distributional separation test.** Compare $Q^{cp}$ (or any statistic) across $C^{\rm STR}$, $C^{\rm FULL}$, $C^{\rm RND}$ with two-sample KS $D=\sup_x|F_1(x)-F_2(x)|$ and Wasserstein $W=\int|F_1-F_2|$; expect $D\approx1$ between structured and random `(arXiv:2607.10297)`.
2. **Degree-preserving randomisation.** Generate 100 configuration-model graphs preserving the degree sequence; empirical $p=\frac{1}{100}\sum_{i=1}^{100}\mathbf 1\{Q^{cp}_{i,\rm rand}>Q^{cp}\}$; CP structure is significant at 1 % in 97.6–100 % of windows in the paper `(arXiv:2607.10297)`.
3. **Monte-Carlo window subsampling.** Draw $M=1000$ subsets of $n=500$ rolling windows without replacement, pool out-of-sample returns, recompute annualised Sharpe $S_m=\sqrt{\cdot}\,\mu_m/\sigma_m$ (risk-free = 0), and test median Sharpe difference vs each benchmark with a one-sided **Wilcoxon signed-rank** test plus a win proportion $\hat p=\frac1M\sum_m\mathbf 1\{S^{STR}_m>S^{j}_m\}$ `(arXiv:2607.10297)`.
4. **Power-law fit check.** Fit discrete power law by MLE, measure KS distance between empirical and fitted degree CDFs, and accept only if Monte-Carlo $p>0.1$ `(arXiv:2607.10297)`.
5. **Sanity on the relative-entropy test.** Simulate $k$-bin multinomials under $p=q$ and confirm the 75 %/95 % empirical quantiles of $2nD_{KL}(\hat p_n\|p)$ match $\chi^2_{k-1}$ for $n\gtrsim100$ `(arXiv:2512.16411)`.

---

## 5. Recommended first implementation in FinRobot

1. **`CorrelationDenoiser` — MP spectral cleaning.** Build the normalized-return correlation matrix from a `core_stock_apis` panel, compute $Q=T/N$ and $\lambda_\pm$, return $C^{\rm STR}$/$\lambda$ spectrum/mode count. Data: daily closes (eodhd primary, tiingo/twelvedata fallbacks). Value: preconditioner for every downstream correlation/risk task; high. Risk: low. Effort: **M**.
2. **`CorePeripheryProfile` + periphery portfolio.** Markov-chain persistence → coreness → $Q^{cp}$; select top-$M$ periphery assets ($M\in\{10,20,30,40\}$) from the denoised network; equal-weight and inverse-variance. Data: same panel + risk-free curve (currently failing — use 0 or a FRED rate as fallback). Value: paper reports SNR 0.65→0.81 (EW) / 0.69→1.21 (Markowitz), statistically significant vs full/random/HSR/market benchmarks. Risk: medium (window/$k$ sensitivity). Effort: **M**.
3. **`ConditionalMINetwork`.** CAPM residualisation on `core_stock_apis` returns + market index, 16-bin MI, 100-permutation significance at $\alpha=0.05$, Prim MST, and the topology/CP index suite ($C_{\rm core}$, $F_{\rm peri}$, APL, $\lambda_2$, assortativity). Value: regime-aware dependency graph and fragility monitor; the crash signature (APL↓, $\lambda_2$↓, $F_{\rm peri}$↑) is directly reportable. Risk: high (compute: $O(N^2)$ permutation tests; needs $N\lesssim200$). Effort: **L**.
4. **`HellingerRegimeDetector`.** Rolling cross-sectional Hellinger distance with $W=60$ and an *expanding* $\mu_H+2\sigma_H$ threshold; segment history into calm/stress and gate strategy 2/3 on it. Data: panel only. Value: cheap, parameter-light regime labels that feed the crash-conditioned analyses. Risk: low. Effort: **S**.
5. **`RelativeEntropyDivergence` change-point test.** Discretise a return series into $k\le8$ bins; use $2nD_{KL}\sim\chi^2_{k-1}$ for one-sample and Agrawal's $M^3_{k,n}$ bound for conservative thresholds; two-sample version for detecting distribution shifts between windows. Data: any return series. Value: principled, calibrated regime/divergence test complementing (4). Risk: medium (empty-bin divergence; bias). Effort: **M**.
6. **`CrossSectionalStabilityFactor` (research diagnostic).** Map each asset to $\pm1$ by sign(return − median), compute the MSF-style persistence $\frac{1}{2N}\sum_i|s_i(t)+s_i(t+\Delta t)|$ and track its drops as a leading volatility indicator (or substitute `market_breadth` when the moomoo gateway is live). Data: panel (+ breadth). Value: exploratory; Ising paper is simulation-only, so validate against realised vol before trusting it. Risk: high (unproven mapping). Effort: **S**.

Skip the income/wealth and technology-transfer models (`arXiv:2604.22976`, `arXiv:2604.11413`) — no tradable signal and no data layer for them.

---

## Appendix — papers read

| arXiv id | title | year |
|---|---|---|
| 2607.10297 | Recovering Structural Organization in Noisy Correlation Networks Using Financial Systems as a Testbed | 2026 |
| 2604.22976 | Statistical Mechanics of Household Income and Wealth: Derivation from Firm Dynamics via Maximum Entropy and Mixture Aggregation | 2026 |
| 2604.11413 | A Herding-Based Model of Technological Transfer and Economic Convergence: Evidence from Central and Eastern Europe | 2026 |
| 2601.00395 | Core-Periphery Dynamics in Market-Conditioned Financial Networks: A Conditional P-Threshold Mutual Information Approach | 2026 |
| 2512.16411 | Asymptotic and finite-sample distributions of one- and two-sample empirical relative entropy | 2025 |
| 2512.17925 | Stylized Facts and Their Microscopic Origins: Clustering, Persistence, and Stability in a 2D Ising Framework | 2025 |
