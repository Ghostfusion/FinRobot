# Factor Models & Alpha — learnings from the q-fin.ST corpus

`256` of 4372 corpus papers matched this category (246 with PDFs, 2000–2026); this doc is based on a close reading of `6`.

## 1. What the corpus actually offers

- **Principal-direction estimation error splits into two terms with different epistemics.** In the high-dimension/low-sample (HL) regime ($p\to\infty$, $n$ fixed) the sine-squared angle between the $j$-th sample eigenvector $h_j$ and the population principal direction $b_j$ has an almost-sure limit that is the sum of an *out-of-subspace* term $OE_j=\delta^2/(n\lambda_j+\delta^2)$ (distance from the sample direction to the span of the loadings) and an *in-subspace rotation* term weighted by the finite-sample signal-to-noise share (arXiv:2609.20550v1). $OE_j$ is **estimable from the data** as the ratio of the average bulk eigenvalue to the $j$-th eigenvalue of the dual Gram matrix; the rotation term is **provably non-estimable from data alone** (arXiv:2609.20550v1).
- **Out-of-subspace error dominates.** In a calibrated 3-factor US-equity simulation, $OE$ is 80–93% of predicted total error across $n\in[20,250]$ at $p=3000$ (arXiv:2609.20550v1). This is the headline: most PCA factor-model error is idiosyncratic noise pushing sample directions off the loading subspace, not mis-rotation *inside* the subspace.
- **Sample factor subspaces are inconsistent, but their *distance* to the truth is consistently estimable.** $\sum_j\sin^2\angle_p(h_j,B)=\tfrac12\|\Pi_H-\Pi_B\|_F^2\to\sum_j \delta^2/(n\lambda_j+\delta^2)$, and this limit is estimated by the observable statistic $\sum_j \ell/\theta_j$ (arXiv:2609.20550v1). The subspace itself does not converge; its distortion does.
- **A model-level zero-alpha test can be localized inside the market by a capitalization axis.** Ordering stocks by formation-date market cap and pairing each whole-stock prefix with an equal-exposure market position yields a zero-investment *bridge* whose regression alpha traces a curve $\alpha_m(p)$ over cumulative cap share $p\in[0,1]$ (arXiv:2607.01765v3). The curve records direction, magnitude, location and frequency of pricing errors along a fixed, predetermined coordinate, complementing (not replacing) maximum-Sharpe spanning tests.
- **Cap-axis magnitude is a distinct coordinate from Sharpe gain and from size exposure.** Across 155 monthly factors, $\mathrm{Spearman}(\Delta SR, IAE)=-0.079$; regressing $IAE$ on the absolute FF3-SMB loading gives $R^2=0.019$ (arXiv:2607.01765v3). 45 of 155 factors sit above the median $\Delta SR$ *and* below the median $IAE$.
- **Prespecified loadings are generally not the regression loadings of the factors they report.** For characteristics-based OLS factor portfolios this is a theorem: consistency requires the loading span to be invariant under the second-moment matrix $Q_t$, which happens only by accident (arXiv:2409.02521v4). Empirically the discrepancy is 19–48% of loading size at *every* window length and does not vanish as the window grows.
- **Exactly one traded factor representation carries a given loading matrix as its own regression loadings**, the *moment-weighted factor portfolios*, obtained by weighting the cross-sectional regression by $Q_t$ instead of running OLS (arXiv:2409.02521v4). This gives a parameter-free, pseudoinverse-based factor construction.
- **Transfer/attention weighting is a first-order efficiency device for factor extraction on mixed-frequency panels.** Replacing fixed linear aggregation with learned cross-sectional and temporal attention yields consistency and asymptotic normality at rate $\bar\alpha=O(1/T)+O(1/N)$ and strict efficiency gains for target-signal components that overlap the auxiliary panel (arXiv:2601.16274v2).
- **Residual-quality diagnostics are cheap and informative.** A size-augmented CAPM whose residuals are normalized by the VIX produces residuals that are closer to IID Gaussian, and the model is ergodic under a log-scale AR(1) volatility (arXiv:2411.19444v8). This is a single-series diagnostic, not a cross-sectional one.
- **One assigned paper is off-topic.** arXiv:2503.21256v1 (Dynamic Asset Pricing Theory for Life Contingent Risks) is an FTAP/pricing-kernel treatment of life-insurance and annuity valuation. It contains no factor-estimation, cross-sectional-alpha or risk-factor-specification content and is not used below.

**Panel vs single-name split (explicit).** The PC-error theory, the cap-axis bridge, the loading-gap test and the moment-weighted construction all **require a cross-section of many assets** at each date (they estimate or test a $p\times p$ or $n_t\times n_t$ second-moment object); the MPTE framework requires a full panel plus an auxiliary panel. Only the VIX-normalized size-CAPM residual diagnostic (arXiv:2411.19444v8) is a pure time-series exercise that **works on one portfolio/name** plus a benchmark and VIX. See §3 for what the data layer can actually supply.

## 2. Implementable formulas & algorithms

### 2.1 HL principal-direction error decomposition and the data-driven OE floor

**Purpose.** Quantify how much a PCA/statistical factor model can be trusted given the number of assets $p$ and the (scarce) number of observations $n$, and produce a computable lower bound on eigenvector error.

**Model.** $y = Bf + z$, with $p\gg k$, $B\in\mathbb{R}^{p\times k}$ rank $k$, $\Sigma_f=\mathbb{E}[ff^\top]\succ0$, $\Sigma_y=B\Sigma_fB^\top+\Delta_z$. Write $\Sigma_0:=B\Sigma_fB^\top=b\,\Delta_0\,b^\top$, $\Delta_0=\mathrm{diag}(p\mu_1,\dots,p\mu_k)$, $b=[b_1\cdots b_k]$ orthonormal (the *principal directions*).

**Estimator.** Scaled sample covariance $S=YY^\top/(np)$ with unit eigenvectors $h_j$; the fixed-size dual is $W=Y^\top Y/(np)\in\mathbb{R}^{n\times n}$ with eigenvalues $\theta_j$ (Gram duality: $S$ and $W$ share nonzero eigenvalues). As $p\to\infty$, $W\to W_0+(\delta^2/n)I_n$, $W_0=F^\top G_B F/n$, $G_B=\lim B^\top B/p$.

**Decomposition (Theorem 1, arXiv:2609.20550v1).** With $(\lambda_j,\nu_j)$ the $j$-th eigenpair of the limiting $k\times k$ systematic dual Gram $N$ and $e_j$ the $j$-th coordinate axis:

$$\sin^2\angle_p(h_j,b_j)\;\longrightarrow\;\underbrace{\frac{\delta^2}{n\lambda_j+\delta^2}}_{OE_j}\;+\;\underbrace{\frac{n\lambda_j}{n\lambda_j+\delta^2}\,\sin^2\angle(\nu_j,e_j)}_{IE_j}.$$

With $\mathrm{SNR}_j=n\lambda_j/\delta^2$: $\sin^2\angle_p(h_j,b_j)\to \frac{1}{1+\mathrm{SNR}_j}+\frac{\mathrm{SNR}_j}{1+\mathrm{SNR}_j}\sin^2\angle(\nu_j,e_j)$.

**Estimable floor (Theorem 2).** Let $\ell^{(p)}=\frac{1}{n-k}\big(\mathrm{tr}\,W^{(p)}-\sum_{i\le k}\theta_i^{(p)}\big)$ be the *average bulk eigenvalue*. Then $\ell^{(p)}/\theta_j^{(p)}\to \delta^2/(n\lambda_j+\delta^2)=\lim_p\sin^2\angle_p(h_j,B)$, a strongly consistent, fully observable estimator of the out-of-subspace error and hence a lower bound for the total error.

**Aggregate form (Corollary 1).** $\sum_{j=1}^k \sin^2\angle_p(h_j,B)=\tfrac12\|\Pi_H-\Pi_B\|_F^2\to\sum_{j=1}^k \frac{\delta^2}{n\lambda_j+\delta^2}$, estimated by $\sum_j \ell^{(p)}/\theta_j^{(p)}$.

**Non-estimability (Theorem 3).** For $k\ge2$, holding $B,F,Z,\delta^2$ and the spectrum of $K=\Sigma_f^{1/2}G_B\Sigma_f^{1/2}$ fixed, the rotation error $\sin^2\angle(\nu_j(\Sigma_f),e_j)$ attains every value in $[0,1]$ as $\Sigma_f$ ranges over admissible covariances; so the limiting total error attains every value in $[\delta^2/(n\lambda_j+\delta^2),\,1]$. The deficiency is in $n$, not $p$: adding cross-section does not help.

**Inputs.** A panel of returns for $p$ assets over $n$ dates (many assets, few dates); a chosen factor count $k$.

**Parameters / defaults from the paper.** Simulation: 3 factors, annualized vols $0.16,0.08,0.06$; specific vol $0.40$; $t$-distributed returns, df 6 (factors) and df 5 (specific); $G_B=\mathrm{diag}(1.25,1,1)$; $n=63$ ("three months of daily data") and $p$ from 100 to 50,000; $p_{\max}=50{,}000$, $n_{\max}=250$; 1000 paths.

**Observed effects.** At $p=500$, total errors were $17^\circ/39^\circ/50^\circ$ for factors 1–3; at $p=3000$, raising $n$ from 20 to 250 cut average error from $30^\circ\!\to\!8.5^\circ$, $56^\circ\!\to\!19^\circ$, $66^\circ\!\to\!24^\circ$. Even a full year of daily data ($n=250$) leaves errors "large enough to demand attention."

**Failure modes.** Assumes a **single regime** (fixed $\Sigma_f$, common cross-sectional average specific variance $\delta^2$); a shock common to factors and specific variances breaks it. Requires pervasive loadings ($G_B\succ0$) and distinct population eigenvalues; the finite-$p$ estimate $\ell/\theta_j$ *underestimates* the true error at small $p$ (worst for weak factors 2 and 3). Cross-sectional independence of specifics is assumed (weak dependence conjectured). Only the floor is measurable — never report $\ell/\theta_j$ as the total error.

### 2.2 Cap-axis bridge-alpha diagnostic

**Purpose.** Test whether an assembled factor model leaves zero alpha *inside* the market, localizing errors along a capitalization-rank coordinate that is fixed ex ante.

**Construction (arXiv:2607.01765v3).** At formation date $\tau(t)$ sort eligible stocks by descending market cap; weights $w_{i,t}=H_{i,t|\tau(t)}/\sum_j H_{j,t|\tau(t)}$; cumulative $c_{k,t}=\sum_{i\le k}w_{i,t}$. For target cap share $p\in(0,1]$, $k_t(p)=\min\{k:c_{k,t}\ge p\}$ (boundary stock included whole), realized exposure $s_t(p)=c_{k_t(p),t}$. Prefix and market returns $C_t(p)=\sum_{i\le k_t(p)}w_{i,t}R_{i,t}$, $R_{tM}=\sum_i w_{i,t}R_{i,t}$; the zero-investment bridge is

$$D_t(p)=C_t(p)-s_t(p)\,R_{tM},\qquad D_t(0)=D_t(1)=0 .$$

Regress $D_t(p_l)=\alpha_m(p_l)+\beta_m(p_l)'f_{m,t}+\varepsilon_{m,t}(p_l)$ at each grid point $p_l$.

**Functionals.** With trapezoidal weights $a_l$ summing to 1: signed area $SA=\sum_l a_l\alpha(p_l)$; $IAE=\sum_l a_l|\alpha(p_l)|$; $ISE=\sum_l a_l\alpha(p_l)^2$; $SUP=\max_l|\alpha(p_l)|$; coherence ratio $CR=|SA|/IAE\in[0,1]$.

**Rank-area scalar.** With midpoint cumulative share $m_{i,t}=\sum_{j<i}w_{j,t}+\tfrac12 w_{i,t}$, $Y_t=\sum_i w_{i,t}R_{i,t}(m_{i,t}-\tfrac12)$ is zero-investment and its alpha is a scalar directional counterpart to $SA$.

**Parameters.** Grid $P=\{0,0.005,\dots,0.995,1\}$, $L=201$; annual Jul–Jun formation, buy-and-hold with proportional dividend reinvestment; daily Newey–West lag 21, monthly lag 6.

**Observed effects.** Daily: q5 $SA=-39.6$ bp, rank-area HAC $t=-3.49$, $p<0.001$, $IAE=39.6$ bp, $ISE=1910$ bp², $SUP=68.0$ bp, $CR=1.00$; FF3/Carhart positive but borderline ($p\approx0.05$). Monthly: q5 $SA=+4.4$ bp, $t=0.40$, $p=0.690$ (attenuates); FF3/Carhart/FF5/FF6 $SA\approx+32$ bp, $t=2.60$–$2.87$, $p<0.05$, $CR\approx1.00$. Construction validation: the CRSP-based market return correlates 0.999778 with FF MKT ($R^2=0.999556$).

**Failure modes.** Not equivalent to pricing every raw size portfolio (whole-stock exposure $s_t(p)$ is time-varying) and not full SDF validity; passing means zero alpha only on the tested bridge family. Daily bridges are contaminated by non-synchronous trading (§2.3). Requires the *full* cross-section ordered by cap — a handful of names cannot produce the curve.

### 2.3 HAC-Gaussian-process functional inference and Dimson lead–lag correction

**Purpose.** Size-controlled inference on nonlinear functionals of the bridge-alpha curve, and separation of short-horizon attenuation from lower-frequency pricing-error structure.

**Null.** $\sqrt{T}(\hat\alpha_m-\alpha_m)\Rightarrow N(0,\Omega_m)$; simulate $\tilde\alpha^{(b)}_{m,0}\sim N(0,\hat\Omega_m/T)$ ($B=50{,}000$ antithetic draws) and recompute $IAE,ISE,SUP$ per draw; the upper-tail probability is the $p$-value. $\hat\Omega_m$ is the multivariate Newey–West long-run covariance of the intercept influence process $\hat\psi_{m,t}=e_1'\hat Q_m^{-1}x_{m,t}\hat\varepsilon_{m,t}$; symmetrize and floor negative eigenvalues before factoring.

**Dimson correction.** $D_t(p_l)=\alpha^{(k)}_m(p_l)+\sum_{h=-k}^{k}\beta^{(k)}_{m,h}(p_l)'f_{m,t+h}+\varepsilon^{(k)}$, corrected exposure $=\sum_h\beta^{(k)}_{m,h}$; sweep $k\in\{1,2,3,5,8,10,13,21\}$ on the same $k$-trimmed sample.

**Calibration results.** Under the zero-curve null ($\lambda=0$), rejection is 4.0% (HAC-GP) and 4.9% (six-month circular block bootstrap); at $\lambda=1$ power is 53.9%/56.4%, rising monotonically. Rebalancing-cycle variation does not reverse the frequency-by-model pattern (q5 daily $SA$ grows to $-55.2$ bp under daily formation).

**Failure modes.** Nonlinear functionals are nonnegative functions of a highly dependent alpha vector — do **not** form naive $t$-statistics for $IAE/ISE/SUP$. Dense grids produce near-singular covariance; report the eigenvalue floor adjustment. Daily bridges need lead–lag correction before interpretation.

### 2.4 Moment-weighted factor portfolios and the loading-gap specification test

**Purpose.** Build traded factors that are *coherent* (their reported loadings are their own regression loadings; residual risk unpriced) and measure the misspecification of any characteristics-based representation.

**Setup (arXiv:2409.02521v4).** $x_{t+1}=\Phi_t f_{t+1}+\epsilon_{t+1}$, $Q_t=\mathbb{E}_t[x_{t+1}x_{t+1}']$, law of one price $\mu_t\in\mathrm{Im}\,\Sigma_t$. Regression loadings $\Phi^{f}_{t}=\mathbb{E}_t[x_{t+1}f_{t+1}']Q_{f,t}^{+}$.

**Support / admissibility.** Coherence requires the *support condition* $\mathrm{Im}\,\Phi_t\subseteq\mathrm{Im}\,Q_t$ and the *risk-premium condition* $\mu_t\in\mathrm{Im}\,\Phi_t$; jointly, $\mathrm{span}\{\mu_t\}\subseteq\mathrm{Im}\,\Phi_t\subseteq\mathrm{Im}\,Q_t$.

**Moment-weighted factor portfolios (Theorem 3.1).** For a prespecified $\Phi_t$, the unique traded factor whose regression loadings equal $\Phi_t$ is

$$f^{\Phi_t}_{t+1}=W_t^\top x_{t+1},\qquad W_t^\top=(\Phi_t^\top Q_t^{+}\Phi_t)^{+}\Phi_t^\top Q_t^{+},$$

the $Q_t^{+}$-orthogonal projection of returns onto $\mathrm{Im}\,\Phi_t$; $\mathrm{rank}\,Q_{f,t}=\mathrm{rank}\,\Phi_t$. Under a regular decomposition $Q_t=\Phi_tC_t\Phi_t^\top+D_t$ this is computable from the residual part only: $W_t^\top=(\Phi_t^\top D_t^{+}\Phi_t)^{+}\Phi_t^\top D_t^{+}$ (Proposition 4.3), so no $n_t\times n_t$ square root or $Q_t$ pseudoinverse is needed.

**Loading gap (Corollary 4.2).** In any unitarily invariant norm, $\min_{\text{traded}}\|\Phi^{f}_{t}-\Phi_t\|=\|(I-Q_tQ_t^{+})\Phi_t\|$, attained at the moment-weighted portfolios; zero iff the support condition holds.

**Corollaries.** OLS factor portfolios satisfy (P1) iff $\mathrm{Im}\,\Phi_t$ is $Q_t$-invariant ($Q_t\mathrm{Im}\,\Phi_t\subseteq\mathrm{Im}\,\Phi_t$). Moment weighting coincides with GLS for admissible loadings under the law of one price, and with OLS under the structure $Q_t=\Phi_tC_t\Phi_t^\top+R_tL_tR_t^\top+\sigma_t^2I$. Residual rank deficiency: $\mathrm{rank}\,\Sigma_{\epsilon,t}\le\mathrm{rank}\,Q_{\epsilon,t}\le n_t-\mathrm{rank}\,\Pi_t$.

**Parameters / empirical (FF25, FF100 $n=94$; 756 months, Jul 1963–Jun 2026; $m\le4$ characteristics; $T_w\in\{24,48,96,120,180,240\}$).** OLS loading discrepancy averages 0.28/0.24/0.19 (FF25) and 0.48/0.39/0.31 (FF100) at $T_w=24/48/120$; the moment-weighted floor is 0.04 (FF25, $T_w=24$) and 0.31/0.19 (FF100, $T_w=24/48$), vanishing identically when $T_w\ge n$. Risk-premium gap falls from 0.50 to 0.25 (FF25) and 0.56 to 0.38 (FF100) at $T_w=48$ as characteristics are added. Pseudoinverse tolerance $10^{-10}$; largest eigenvalue carries 85%/77% of $\mathrm{tr}\,\hat Q_t$.

**Failure modes.** The theory is population-level with pseudoinverses; when $T_w\le n_t$ the sample $Q_t$ is rank-deficient and the law of one price fails *in-sample* (FF100, $T_w=96$: moment-weighted Sharpe collapses to 0.01, GLS to $-0.03$, while OLS holds 0.61 because it inverts no return moment). Use Ledoit–Wolf shrinkage on $\hat\Sigma_t$ before rebuilding $\tilde Q_t=\tilde\Sigma_t+\hat\mu_t\hat\mu_t^\top$. The discrepancy magnitude depends on characteristic standardization; whether it vanishes does not.

### 2.5 Attention-weighted / mixed-frequency factor extraction (MPTE)

**Purpose.** Estimate factor models on panels with mixed sampling frequencies and nonlinear signals, and borrow strength from an auxiliary panel.

**Model (arXiv:2601.16274v2).** Target panel $Y=\Psi_y+e_y$, auxiliary $X=\Psi_x+e_x$; linear signals $\Psi_y=F_y(\Lambda^Y_y)^\top$. Target PCA applies PCA to a $\gamma$-weighted second moment of $Z^\gamma=[X\ \sqrt{\gamma}Y]$; MPTE replaces fixed weighting with attention $\tilde Z=B[X\ Y]A_z$, where $A_z$ is the cross-sectional operator and $B$ the temporal operator (axial attention: cost $N^2+T^2$). PCA on $\tilde Z^\top\tilde Z$ gives loadings; factors by regressing $\tilde Z$ on loadings. A one-layer linear autoencoder with $k$ hidden units is equivalent to this attention-weighted PCA up to rotation.

**Theory (linear activations).** Consistency at rate

$$\bar\alpha=\frac{\mathrm{tr}(A_z^\top A_z)}{(N_x+N_y)T}+\frac{\|A_z^\top A_z\|_F^2}{(N_x+N_y)^2}+\frac{\|B\|_F^4}{T^2(N_x+N_y)}\cdot\frac{\|B\|_F^2}{(N_x+N_y)T},$$

which under the attention-regularity condition ($\|A_z\|_{op}=O(1)$, $\frac1N\mathrm{tr}(A_z^\top A_z)\to c_A\in(0,\infty)$) is $\bar\alpha=O(1/T)+O(1/N)$, reducing to the classical PCA rate $1/T+2/N$ at $A_z=B=I$. Asymptotic normality of loadings/factors with sandwich covariances; the two halves of the attention condition act jointly as an **anti-concentration** requirement, $PR/N\ge c_A/\kappa^2$ with participation ratio $PR=\mathrm{tr}(A_z^\top A_z)^2/\|A_z^\top A_z\|_F^2$.

**Transfer efficiency.** With $N_{\text{eff}}^{-1}V^{\text{joint}}\preceq N_{y,\text{eff}}^{-1}V^{Y}$, every linear combination of the $Y$-strong factors is estimated weakly more efficiently by the joint procedure; the precision gain is $\sigma_t^{-2}\Pi^X$, of order $N_{x,\text{eff}}$, strictly positive on the shared subspace $S_X$.

**Parameters / empirical.** Simulation baseline $N_x=100,N_y=50,T=200$, $k=4$ (2 $Y$-strong + 2 rest), VAR(1) AR $0.5I_2$, noise $\mathcal N(0,2)$, signal share ≈½. Empirical: 13 quarterly FRED-QD targets from 48 monthly/quarterly series, 1959:Q1–2025:Q1, two-year context window (incl. within-quarter monthly lead), eval Jun 2012–Mar 2025. GPDIC1 full-sample RMSE 0.0049 (MPTE) vs 0.0103 (MIDAS) vs 0.0682 (OLS).

**Observed effects.** Linear design RMSE 1.1778 (MPTE) vs 1.2238 (MIDAS) vs 1.3669 (AR); joint-vs-$Y$-only MSE ratio rises 0.908→1.149 as $N_x$ goes 25→400.

**Failure modes.** Learned attention can **concentrate** on a few hub variables: $PR/N$ shrinks, the middle term stalls at $1/PR$, and the distributional theory degrades even though Frobenius error still converges. Clip singular values ($\kappa_0=3$) and/or blend toward the identity ($\delta I$, $\delta\in[0,5]$) to restore the anti-concentration condition. Re-estimating attention on the evaluation sample, or residual dependence of window weights on contemporaneous idiosyncratic noise, are explicitly outside the theory — freeze attention on an independent training panel.

### 2.6 Size-augmented CAPM with VIX normalization and residual diagnostics

**Purpose.** A single-series model that folds size, market beta and stochastic volatility into one regression and yields residuals close to IID Gaussian.

**Model (arXiv:2411.19444v8).** With $C=\ln(S/S_0)$ the log relative size, price-return form $R/V=aC+(1+bC)R_0/V+m+\varepsilon$ and premium form $P/V=AC+(1+BC)P_0/V+M+\delta$; volatility on the log scale $\ln V(t)=\alpha+\beta\ln V(t-1)+W(t)$, $\hat\beta=0.88$ (unit root rejected). Long-run stability (ergodicity of the relative-size process) holds under $\mathbb{E}\ln|1+aV(\infty)+bR_0(\infty)|<0$.

**Inputs.** One target series and one benchmark series of monthly returns/premia, VIX monthly average, a short rate, and market caps for the size ratio.

**Parameters / empirical.** Monthly Jan 1986–Dec 2025, 480 obs; French 10 size deciles, decile 10 = benchmark; VIX and 3-month T-bill from FRED.

**Observed effects.** Slope $b>0$ significant for deciles 2–8 ($T_b$ 1.3–3.6); residuals IID Gaussian for deciles 6–8 (Shapiro–Wilk $p$ 45%/12–16%/11–14%); Ljung–Box (10 lags) passes all but decile 1. Dividing by VIX is what moves premia toward IID Gaussian.

**Failure modes.** Works on a *diversified portfolio* (size decile), not individual small/large stocks. Test the ACF of squares/absolute values, not just the level — zero-ACF data can still have autocorrelated magnitude. Multiple-testing across deciles is acknowledged and ignored.

## 3. Data requirements → available endpoints

Every row cites a probed endpoint from `strategies/endpoints.json` (49 rows, 14 providers). Rows marked **gap** have no provider in the inventory.

| Input | Endpoint | Category | Provider | Probe status |
|---|---|---|---|---|
| Daily/monthly OHLCV panel for the cross-section | `https://eodhd.com/api/eod/AAPL` | core_stock_apis | eodhd | ok |
| Same (fallback) | `https://api.tiingo.com/tiingo/daily/AAPL/prices` | core_stock_apis | tiingo | ok |
| Same (fallback) | `https://api.twelvedata.com/time_series` | core_stock_apis | twelvedata | ok |
| Same (fallback) | `https://api.stockdata.org/v1/data/eod` | core_stock_apis | stockdata | ok |
| Same (fallback) | `https://api.massive.com/v2/aggs/ticker/AAPL/prev` | core_stock_apis | massive | ok |
| Intraday/snapshot for lead–lag & non-sync checks | `moomoo://get_cur_kline`, `moomoo://get_market_snapshot` | technical_indicators / core_stock_apis | moomoo | gateway (local OpenD SDK; `ok=false`) |
| Universe of tickers for the cross-section | `https://eodhd.com/api/exchange-symbol-list/US` | exchange_symbols | eodhd | ok |
| Shares outstanding / fundamentals → market cap | `https://api.tiingo.com/tiingo/fundamentals/AAPL/statements` | fundamental_data | tiingo | ok |
| Same (fallback) | `https://www.alphavantage.co/query` | fundamental_data | alpha_vantage | ok |
| Dividends → dividend-inclusive total returns | `https://eodhd.com/api/div/AAPL` | corporate_actions | eodhd | ok |
| Same (fallback) | `https://api.benzinga.com/api/v2.2/calendar/dividends` | corporate_actions | benzinga | ok |
| Risk-free rate for excess returns | `https://api.stlouisfed.org/fred/series/observations` | macro_data | fred | ok |
| Treasury curve | `https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2026/all` | risk_free_curve | federal_reserve | degraded: `connect` ReadTimeout |
| VIX monthly average (paper 5) | `https://api.stlouisfed.org/fred/series/observations` (VIXCLS) | macro_data | fred | ok |
| Options-implied vol surface | `https://cdn.cboe.com/api/global/delayed_quotes/options/_SPX.json` | options_surface | cboe | degraded: `http` 307 |
| Institutional holdings (characteristic) | `moomoo://get_shareholders_institutional` | institution_data | moomoo | gateway |
| Insider trades (characteristic) | `moomoo://get_insider_trade_list` | smart_money | moomoo | gateway |
| Analyst ratings (characteristic) | `https://api.benzinga.com/api/v2.1/calendar/ratings` | analyst_ratings | benzinga | ok |
| Analyst actions/insights | `https://api.benzinga.com/api/v1/analyst/insights` | analyst_actions | benzinga | auth: HTTP 403 |
| Earnings surprise (characteristic) | `moomoo://get_financials_earnings_price_move` | earnings_surprise | moomoo | gateway |
| Market breadth (context) | `moomoo://get_rise_fall_distribution` | market_breadth | moomoo | gateway |
| Macro panel (MPTE auxiliary block) | `https://api.stlouisfed.org/fred/series/observations` | macro_data | fred | ok |
| News sentiment (optional factor) | `https://eodhd.com/api/sentiments` | news_sentiment | eodhd | ok |
| Fama–French / Carhart / q5 factor return series (SMB, HML, RMW, CMA, MOM, ME, IA, ROE, EG) | — | — | — | **gap** — no provider; must be self-constructed from the panel or sourced offline |
| CRSP-style delisting returns / survivorship-bias-free panel | — | — | — | **gap** — no provider; eodhd/tiingo panels are survivorship-prone |
| Point-in-time market cap & shares (as-of formation date) | — | — | — | **gap** — must be derived from fundamentals × price, not available as a series |
| Book equity / accounting characteristics (B/M, profitability, investment) | — | — | — | **gap** for point-in-time values; tiingo/alpha_vantage statements give current values only |

**Coverage verdict.** A price/return panel, the ticker universe, dividends, FRED macro/VIX/rates and (via moomoo OpenD) institutional/insider/earnings-side characteristics are reachable today. The two blockers for a faithful cap-axis or moment-weighted implementation are (i) **factor return series** (FF/q5) and (ii) **point-in-time market cap / book equity**. Both must be constructed or imported; no probed endpoint supplies them.

## 4. Pitfalls, validation and measurement

- **In-subspace error is not measurable from data.** Never present an eigenvector-error estimate as complete; report only the floor $\ell^{(p)}/\theta_j^{(p)}$, and state that the true error lies in $[\text{floor},1]$ (arXiv:2609.20550v1, Theorem 3).
- **More assets do not fix factor-return sampling error.** The rotation term is a finite-$n$ phenomenon; growing $p$ leaves it untouched (arXiv:2609.20550v1). Validate by re-estimating on nested cross-sections: the floor should stabilize while the total error stays bounded below by it.
- **Single-regime requirement.** The HL error theory assumes one regime ($\Sigma_f$ fixed, common average specific variance). Regime shifts invalidate the limit; test by splitting the sample and checking whether $\ell/\theta_j$ drifts (arXiv:2609.20550v1).
- **Generated-regressor bias.** In a conditional model the loadings/characteristics are estimated, then used as regressors; the loading discrepancy (19–48%) means variance decompositions and alphas attach to a matrix that is not the regression loading matrix (arXiv:2409.02521v4). Always compute and report the loading gap and the risk-premium gap.
- **Window vs dimension rank boundary.** With $T_w\le n_t$, $\hat Q_t$ and $\hat\Sigma_t$ are singular by construction; the law of one price fails in-sample and the maximal Sharpe ratio is infinite in-window (FF100, $T_w=48$: an in-sample arbitrage absorbs 27% of $\|\hat\mu_t\|$). Shrink $\hat\Sigma_t$ (Ledoit–Wolf) before rebuilding $\tilde Q_t$; report pseudoinverse tolerance (arXiv:2409.02521v4).
- **Non-synchronous trading inflates daily cap-axis alphas.** The q5 daily bridge attenuates under Dimson correction and is small monthly; without lead–lag correction the daily result is a timing artifact (arXiv:2607.01765v3). Always run the horizon profile over $k\in\{1,\dots,21\}$.
- **Test-asset dependence and multiple testing.** Joint alpha tests and distance measures depend on the chosen test assets; the 155-factor scan is explicitly descriptive, not 155 discoveries (arXiv:2607.01765v3). Fix the test-asset coordinate before looking at results.
- **Look-ahead in sorts and standardization.** Universe/characteristics must be observed by the formation date and applied from the next period; cross-sectional standardization must use trailing data only, else the loading discrepancy and alphas are contaminated (arXiv:2409.02521v4, §5.1). A zero-cost invariance check: with a constant column in $\Phi_t$, standardization must leave factor spans, pricing errors and Sharpe ratios unchanged to numerical tolerance (paper reports $2\times10^{-12}$).
- **Attention concentration breaks inference.** If learned attention concentrates, $PR/N$ shrinks and the growth conditions $\sqrt{T}\bar\alpha\to0$, $\sqrt{N_{\text{eff}}}\bar\alpha\to0$ fail; Frobenius error may still converge while confidence intervals undercover (arXiv:2601.16274v2). Diagnose with $PR/N$ and the operator norm; clip/blend to restore.
- **Residual diagnostics must test magnitudes.** Test the ACF of squares/absolute values, not just the level, and use Ljung–Box + Shapiro–Wilk/QQ, not eyeballing (arXiv:2411.19444v8).
- **Validation recipe.** (1) Reproduce the OE floor and check it is a lower bound in nested-$p$ experiments. (2) On a synthetic 3-factor panel with known $G_B$, check that $\ell/\theta_j$ matches the realized out-of-subspace error. (3) For cap-axis tests, verify size control under the zero-curve null (≈5%) and monotone power before trusting any rejection. (4) For factor construction, verify the loading gap is zero by construction for moment-weighted portfolios and positive for OLS on characteristic spans.

## 5. Recommended first implementation in FinRobot

1. **PCA estimation-error floor monitor (paper 1).** Build a helper that, given a return panel and factor count $k$, computes $\theta_j^{(p)}$ and $\ell^{(p)}$ from the dual Gram $Y^\top Y/(np)$ and reports $\ell/\theta_j$ per factor plus the aggregate $\sum_j\ell/\theta_j$. Data: `core_stock_apis` panel (eodhd/tiingo/twelvedata). Expected value: a hard, cheap lower bound on factor-model error that gates every downstream PCA use. Risk: needs enough assets per date (target $p\gtrsim500$); silently misleading if regimes are mixed. Effort: **S**.
2. **Moment-weighted factor construction + loading-gap report (paper 6).** Implement $W_t^\top=(\Phi_t^\top\hat Q_t^{+}\Phi_t)^{+}\Phi_t^\top\hat Q_t^{+}$ with an SVD pseudoinverse (tolerance $10^{-10}$), and always print the loading gap $\|(I-\hat Q_t\hat Q_t^{+})\Phi_t\|/\|\Phi_t\|$ and the risk-premium gap $\|\hat\mu_{t,\perp}\|/\|\hat\mu_t\|$. Data: panel + fundamentals-derived characteristics (tiingo/alpha_vantage). Expected value: parameter-free, coherent factor portfolios and a per-window misspecification number. Risk: rank-deficient $\hat Q_t$ when $T_w\le n_t$ — shrink or report the window/dimension boundary. Effort: **S–M**.
3. **Cap-axis bridge-alpha diagnostic (paper 2).** Implement the whole-stock bridge, the 201-point grid, the four functionals and the rank-area return, with HAC-GP functional inference and a Dimson sweep. Data: full cap-ordered cross-section (`core_stock_apis` + derived market cap), dividends for total returns, and the model's factor returns. Expected value: locates *where inside the market* a model mis-prices, at daily and monthly horizons. Risk: **factor return series are a data gap** — must be imported/constructed first; daily results need lead–lag correction. Effort: **L**.
4. **Single-series residual-quality diagnostic (paper 5).** A small routine that regresses a portfolio's VIX-normalized premium on the benchmark's VIX-normalized premium and a log-size interaction, then runs Ljung–Box (10 lags) on residuals and on $|residual|$, plus Shapiro–Wilk/QQ. Data: one target + benchmark series, FRED VIX/rates. Expected value: fast sanity check on whether a return series is even conditionally IID-Gaussian before modeling. Risk: only valid for diversified portfolios. Effort: **S**.
5. **Attention/transfer factor extraction for mixed-frequency panels (paper 3).** Only worth building if FinRobot ingests multi-frequency macro panels; start with the linear attention-weighted PCA special case (nests Target PCA) and enforce the anti-concentration condition by clipping singular values at $\kappa_0=3$ and blending toward identity. Data: target + auxiliary panels (FRED macro), frozen operators trained on a separate panel. Expected value: first-order efficiency gains for target-signal components overlapping the auxiliary block. Risk: attention concentration can silently break inference; substantial engineering. Effort: **L**.

## Appendix — papers read

| arXiv id | title | year |
|---|---|---|
| 2609.20550v1 | Principal component error in high-dimensional factor models | 2026 |
| 2607.01765v3 | A Cap–Axis Integral Diagnostic of Factor Models | 2026 |
| 2601.16274v2 | A Nonlinear Target-Factor Model with Attention Mechanism for Mixed-Frequency Data | 2026 |
| 2503.21256v1 | Dynamic Asset Pricing Theory for Life Contingent Risks *(off-topic for this category)* | 2025 |
| 2411.19444v8 | Capital Asset Pricing Model with Size Factor and Normalizing by Volatility Index | 2024 |
| 2409.02521v4 | Fundamental Properties of Linear Factor Models | 2024 |
