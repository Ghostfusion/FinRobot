# Energy & Commodity Markets — learnings from the q-fin.GN corpus

`97` of 3095 corpus papers matched this category (96 with PDFs); this doc is based on a close reading of `6`.

Headline: **the category is thin on constructions FinRobot can run end-to-end.** Five of the six papers
need a price series or a panel that no endpoint in `strategies/endpoints.json` serves, and only one of
them — the crude-oil statistical-arbitrage scheme (arXiv:2309.00875) — is a complete, cost-aware trading
rule. What the catalog actually reaches is *daily oil **spot*** through FRED `macro_data`
(WTI/Brent, `series/observations`) and *commodity-linked equity/ETF proxies* through the equity
providers; it reaches **no** power price, no ISO generation mix, no commodity futures term structure, no
commodity option surface and no bilateral trade-flow matrix. So this document separates:

- **quantitative estimators that are genuinely usable on FinRobot's data** — §2.3 (quantile-oil
  forecaster), §2.4 (cointegrated HMM pairs rule), §2.5 (vol–price elasticity model + option formula);
- **sharp estimators that are research-only until a feed is added** — §2.1 (VRE / electricity-price
  quantile regression), §2.2 (functional realized covariation for power panels);
- **economic context, non-actionable** — §2.6 (energy-trade-network measures): the only signal in it is a
  −0.70/−0.78 correlation, and its input (a bilateral trade matrix) is a **gap**.

## 1. What the corpus actually offers

- **Renewable penetration lowers wholesale electricity price non-linearly, and the reduction is largest in
  the extreme high tail.** Across 6 US ISOs using hourly or 5-minute real-time system price and generation
  mix for 2014–2020 (per-ISO windows; SPP reached a mean VRE share of 46.38%, CAISO 10.04%, PJM 2.62%),
  nonparametric quantile regression of detrended price on B-splines of VRE share shows the 0.90 quantile
  decreasing faster than the median; in PJM a 0–1% VRE move cuts the median detrended price by \$1.6 and the
  0.90 quantile by \$10, while a 5–6% move cuts the median by \$0.2 and the 0.90 quantile by \$0.8
  (arXiv:2112.11338).
- **Temporal price volatility falls with VRE in 5 of 6 ISOs, across all quantiles (0.50/0.75/0.90).** In PJM
  the 0.90 quantile of the EWMSD volatility drops \$5 over a 0–1% VRE increment vs \$0.8 for the median;
  the exception is SPP, where volatility falls up to ≈40% VRE and then rises as negative-price episodes
  accumulate (arXiv:2112.11338). The skew-$\alpha$ parameter of a skew-t fit moves toward symmetry for four
  ISOs and turns negative for SPP and CAISO (arXiv:2112.11338). Detrended-price dispersion across ISOs runs
  from SD \$14.73 (MISO) to \$41.34 (CAISO) (arXiv:2112.11338).
- **In European day-ahead power, mean-reversion is ≈40% of measured price variation, and ignoring it
  contaminates every volatility estimate.** For Germany/NO2/Spain, 2551 daily observations × 24 hourly
  delivery periods per zone (61,368 points; Oct 2018–Sep 2025) give 2557 rolling 7-day realized-covariation
  estimates each; the estimated *propagation share* $PS\approx0.4$ in all three zones, decreasing in the
  delivery hour — early hours are the most predictable from the current price level (arXiv:2605.13320).
- **Realized power volatility is low-dimensional and price-level-driven.** The first principal component of
  the propagation-adjusted weekly realized covariation explains >60% of variation in all three zones;
  six to eight components reproduce 95%. The price level *P* and *P²* alone explain 54% (Germany), 52%
  (Norway) and 33% (Spain) of $\log S_1(t)$, and full regressions on generation mix reach $R^2>0.80$ for
  Germany and Spain. The largest semigroup eigenvalue is $\lambda_1\approx0.8$ in Germany (common-shock
  half-life $\approx3$ days) and $\approx6$ days in Norway (arXiv:2605.13320).
- **The "inverse leverage effect" in power is largely spurious.** Unconditionally, high spot prices come with
  high volatility; conditionally, the asymmetry between up- and down-shocks vanishes. Wald tests for
  $\beta_+=\beta_-$ give $p=0.0062$ against a mean-reversion control, $p=0.0128$ against a price/level
  control, and $p=0.5898$ when both are partialled out (arXiv:2605.13320).
- **Oil-price quantile forecasting beats mean forecasting — but only in the left tail.** A Bayesian Quantile
  VAR on monthly real oil prices, 602 observations, Jan 1975–Feb 2025, improves the median by 2–5% vs a
  standard BVAR and cuts left-tail (10th-percentile) quantile scores by 10–25% relative to BVARs, with
  crisis-period left-tail gains up to 70% (2014–16 collapse, h=6). Right-tail (90th) forecasting is
  *worse* than stochastic-volatility benchmarks; every QS90 ratio against BVAR-SV exceeds 1.00 and runs
  1.10–1.50 (arXiv:2604.12927). Uncertainty and financial-stress predictors drive the asymmetry: JLN
  uncertainty delivers 12–24% left-tail gains vs a random walk, the Gilchrist–Zakrajšek spread 9–18%, while
  geopolitical-risk indices help only the right tail (arXiv:2604.12927).
- **A two-regime hidden Markov mean-reverting spread is a profitable crude-oil stat-arb rule net of
  transaction costs.** On daily/weekly Brent, WTI and Shanghai (INE) crude futures, 26 Mar 2018–30 Jun 2023
  (1373 daily / 273 weekly observations; test year from 07/01/2022), the three log-prices are cointegrated
  (Johansen trace test, one relation, $p=0.0099$; VAR(2) by Schwarz IC) with normalized spread
  $S_t=F^B_t-0.6982F^S_t-0.3402F^W_t+0.4322$. The best strategy (prediction-interval, $\alpha=0.20$) earns
  annualized 15.18% with Sharpe 1.1792 over 12 completed trades, vs the crude-oil ETF's negative return and
  a max drawdown of −5.73% vs the ETF's −39.47%. The Shanghai leg carries the adjustment: its VECM
  adjustment coefficient is significant at 1%, the Brent/WTI ones are not — a unidirectional long-run
  causality into Shanghai (arXiv:2309.00875).
- **Commodity volatility rises with price (positive vol–price elasticity), unlike equities.** For Chinese
  soybean meal (263 trading days, 2020/01/02–2021/01/29) and aluminium (164 days, 2017/08/01–2018/04/02),
  regressing 30-day historical volatility on closing price gives slopes $1.53\times10^{-4}$ and
  $4.61\times10^{-5}$, $R^2=0.7471$ and $0.8207$, correlations 0.8643 and 0.9059, all $p<2\times10^{-16}$
  (arXiv:2203.09177). This motivates a SDE whose volatility is affine in price and yields a closed-form
  European call price of Black–Scholes-like shape (arXiv:2203.09177).
- **Oil's structural entanglement with the trade network is measurable but non-tradable.** On the BACI
  bilateral trade panel 1998–2007, oil has the highest binary reciprocity (0.52±0.008 vs coal 0.36, gas
  0.33, electricity 0.19) and the highest weighted reciprocity (0.25 in 2007), one order of magnitude above
  gas/coal/electricity. The time series of world-trade **reciprocity** correlates −0.70 with the real oil
  price (−0.78 after a balance-of-payments null-model filter), and begins declining three years *before*
  the 1973 shock (arXiv:1509.05894).
- **Off-topic / retained-for-cause notes.** arXiv:1509.05894 is primary `physics.soc-ph` and contains no
  return-generating rule; it is retained only because its reciprocity↔oil-price correlation is the single
  cross-sectional macro observable in the set (and is a **gap** input). arXiv:2203.09177 is primary
  `q-fin.MF` (option pricing) and arXiv:2604.12927 primary `econ.EM`; both are on-topic for commodity
  price/volatility and are retained. No assigned paper is unrelated to energy or commodities.

## 2. Implementable formulas & algorithms

### 2.1 Quantile and skew-t regression of detrended price on a penetration driver
**Purpose.** Estimate how a driver $x_t$ (here VRE generation share) shifts the *whole* conditional
distribution of electricity price and of its temporal volatility — the nonlinear, tail-specific analogue of
a linear price-on-VRE regression that institutionally understates the effect.

**Formula.** First remove deterministic seasonality/diurnal structure,
$$\text{Price}(t)=\beta_1\,\text{hour}(t)+\beta_2\,\text{season}(t)+\beta_3\,\text{hour}(t)\!\cdot\!\text{season}(t)+\beta_4\,\text{weekend}(t)+\varepsilon_t ,$$
and take $\varepsilon_t$ as the detrended price. Temporal volatility is the exponentially weighted moving
standard deviation
$$\text{EWMSD}_i=(1-\omega)\sum_{k\ge0}\omega^{k}\,U_{i-k}^{2},\qquad \omega=0.94 .$$
Quantile regression estimates $Q_Y(\tau\mid x)=\inf\{t: F_{Y|x}(t)\ge\tau\}=x'\beta$ (nonparametric: replace
$x'\beta$ by a B-spline basis $\beta_0+\boldsymbol\phi(x)'\boldsymbol\beta$, degree 3) by minimizing the
check loss
$$\hat\beta(\tau)=\arg\min_\beta \sum_t \rho_\tau\!\big(y_t-x_t'\beta\big),\qquad
\rho_\tau(u)=u\,(\tau-\mathbf 1\{u<0\}).$$
Complementarily, a four-parameter skew-t fits location and scale as GLMs in the driver,
$$\mu_t=\beta_0+\beta_1\frac{x_t}{100},\qquad \log\sigma_t=\gamma_0+\gamma_1\frac{x_t}{100},$$
with constant shape $\alpha$ and tail index $\nu$.

**Required inputs.** Hourly/5-min system price; generation mix by fuel (to form the driver share); a
calendar index (hour, season, weekend).

**Parameters & defaults.** $\omega=0.94$; quantile grid $\tau\in\{0.25,0.50,0.75,0.90\}$; B-spline degree 3
with knots chosen so the spline does not overfit at the boundaries; skew-t estimated by maximum likelihood
(RS algorithm). Season blocks: winter = {12,1,2}, spring = {3,4,5}, summer = {6,7,8}, autumn = {9,10,11};
weekend is a binary flag.

**Observed effect sizes.** Loan quoted above: PJM median −\$1.6 and 0.90-quantile −\$10 per 0–1% VRE step,
shrinking to −\$0.2/−\$0.8 per 5–6% step; volatility reductions largest at the 0.90 quantile; skew→symmetry
for four ISOs, skew<0 for SPP/CAISO (arXiv:2112.11338).

**Failure modes.** The driver share is *bundled* differently per operator (NYISO/MISO report wind only), so
the coefficient is not comparable across markets; price caps can truncate the extreme tail (only ≤0.01% of
prices hit \$1000/MWh, so not binding in practice); negative prices have *no* clear relation to VRE share —
do not read "VRE ⇒ negative prices" from this; and the fitted relation is only valid over the observed
penetration range (SPP changes sign past ≈40%).

### 2.2 Propagation-adjusted functional realized covariation for power panels
**Purpose.** Estimate the weekly integrated variance/covariance of a *panel* of correlated day-ahead prices
(24 or 96 delivery periods/day) without the mean-reversion bias that inflates a naive realized-covariance
estimator.

**Formula.** Treat observed prices as local averages of a latent curve $X_t\in L^2(S^1)$,
$\tilde X_t^{(i)}=(h_i-h_{i-1})^{-1}\!\int_{h_{i-1}}^{h_i}X_t(h)\,dh=(AX_t)_i$, and write
$\Delta_n\tilde X=\tilde X_{t_n}-\tilde X_{t_{n-1}}$. The naive $w$-period realized covariation is
$$\widehat\Sigma^{\,w}_{j}=\frac{1}{\delta w}\sum_{\ell=1}^{w}
(\Delta_{(j-1)w+\ell}\tilde X)(\Delta_{(j-1)w+\ell}\tilde X)^{\top}.$$
The feasible one-step semigroup is the least-squares predictor
$$\widehat S_\delta=\Big(\sum_n \tilde X_n\tilde X_{n-1}^{\top}\Big)\Big(\sum_n \tilde X_{n-1}\tilde X_{n-1}^{\top}\Big)^{-1},$$
and the propagation-adjusted estimator uses plug-in residuals
$\hat\varepsilon^{pl}_n=\Delta_n\tilde X-(\widehat S_\delta-I_d)\tilde X_{n-1}$:
$$\widehat\Sigma^{\,w}_{j,pl}=\frac{1}{\delta w}\sum_{\ell=1}^{w}\hat\varepsilon^{pl}_{(j-1)w+\ell}
\big(\hat\varepsilon^{pl}_{(j-1)w+\ell}\big)^{\top}.$$
The realized variance of the *average* daily price is a linear functional of the matrix,
$RV^{\,w}_j=\frac{1}{d^2}\mathbf 1^{\top}\widehat\Sigma^{\,w}_{j,pl}\mathbf 1$, and the propagation share that
quantifies the bias is $PS=\big(\sum_n\|\widehat B_n\|^2\big)/\big(\sum_n\|\Delta_n\tilde X\|^2\big)$ with
$\widehat B_n=(\widehat S_\delta-I)\tilde X_{t_{n-1}}$. Standardized realized correlations are
$\rho=\widehat Q^{-1}\,\bar{\widehat\Sigma}\,\widehat Q^{-1}$, $\widehat Q=\operatorname{diag}(\bar{\widehat\Sigma})^{1/2}$.

**Required inputs.** A panel of day-ahead prices per delivery period per day (a dense $d\times N$ matrix).

**Parameters & defaults.** $w=7$ days (kills weekly periodicity); $\delta=1/365$ (annualized); rolling rather
than disjoint windows to gain sample; de-drift by local-linear regression with an **Epanechnikov kernel,
bandwidth 90 days** ($\tau=0.246$) plus day-of-week dummies; re-estimate $\widehat S_\delta$ on trailing data
**every 28 days after a 52-week burn-in**; PCA of $\widehat\Sigma_{pl}$ ranks components.

**Observed effect sizes.** $PS\approx0.4$; six to eight PCs give 95% of variance; PC1 >60% and is a humped
"level factor" peaking near 18–19h; PC2 tracks the demand "duck curve". Raw realized correlations contain a
block of *negative* early-vs-late-hour entries that all become positive after the propagation adjustment
(arXiv:2605.13320).

**Failure modes.** The semigroup is only identifiable up to smoothing by $S$; the long-span limit needs
stationarity of the *differenced* series (levels are non-stationary — KPSS rejects — while ADF rejects unit
roots, i.e. prices are mean-reverting at the level and trend-stationary in differences); estimating
$\widehat S_\delta$ on the full sample leaks look-ahead (hence the rolling re-estimation); regenerating
hourly averages after a 24→96 delivery-period market change mixes regimes; and interpreting any single
eigenvalue as "the" volatility level ignores that PC1 is not flat across hours.

### 2.3 Bayesian Quantile VAR (QBVAR) for oil-price distributional forecasting
**Purpose.** Produce a forecast of the *whole conditional distribution* of real oil-price growth, not just
its mean, so downside and upside risks can be scored separately.

**Formula.** Extend a factor-BVAR $y_t=\Phi x_t+\Lambda f_t+v_t$, $v_t\sim N(0,\Sigma)$ to quantile level
$q$:
$$y_t=\Phi_q x_t+\Lambda_q f_{t,q}+v_{t,q},\qquad v_{t,q}\sim \mathrm{AL}(0,\sigma_{i,q},q),$$
where $\mathrm{AL}$ is the asymmetric Laplace. Estimation uses the location–scale mixture
$$y_t=\Phi_q x_t+\Lambda_q f_{t,q}+\theta(q)z_{t,q}+\epsilon_{t,q},\quad
\epsilon_{t,q}\sim N\!\big(0,\tau^2(q)\operatorname{diag}(z_{t,q})\Sigma_q\big),$$
$$z_{it,q}\sim \mathrm{Exp}(1),\qquad
\theta(q)=\frac{1-2q}{q(1-q)},\qquad \tau^2(q)=\frac{2}{q(1-q)},$$
which is conditionally Gaussian given $z_{t,q}$, so all Gibbs conditionals are closed form (VAR rows,
loadings, factors, $z$ from a generalized inverse Gaussian, scales inverse-gamma). Horseshoe priors
$\phi_{ij,q}\sim N(0,\psi^2_{ij,q}\kappa^2_q)$, $\psi_{ij,q},\kappa_q\sim C^+(0,1)$ shrink irrelevant
predictors. Forecasts at horizon $h$ simulate future factors and Gaussian shocks and take the median across
posterior draws. Accuracy is scored by the **quantile (pinball) score**
$$\mathrm{QS}(q)=\sum_t \rho_q(u_t),\qquad \rho_q(u)=u\,(q-\mathbf 1\{u<0\}),\qquad u_t=y_{t+h}-\hat Q_t(q,h),$$
and quantile-forecast combination is convex with weight $\lambda$,
$\hat q^{Comb}_t(\tau,h)=\lambda\,\hat q^{QBV}_t(\tau,h)+(1-\lambda)\hat q^{BVSV}_t(\tau,h)$.

**Required inputs.** Monthly real oil price (CPI-deflated, log growth); a global oil-market-fundamentals
variable; one predictor chosen from the uncertainty / financial-conditions / activity / inventory /
geopolitical channels.

**Parameters & defaults.** $p=4$ lags (grid $\{1,2,4,12\}$); $r=1$ common factor; three-variable system;
Gibbs with 3,000 iterations, 1,000 burn-in, retain every 5th → 400 saved draws; expanding-window recursive
re-estimation with 205 forecast origins (2008M1–2025M2) and 145 (2013M1–2025M2); horizons $h=1..12$;
$q\in\{0.1,0.5,0.9\}$. Predictor menu: JLN, JLNF12, EBP, GZ spread, crack spread, GECON, Kilian index, OECD
stocks, world rig count, GPRH, GPRHA, GPRHT.

**Observed effect sizes.** QS50 ratios vs BVAR(12) of 0.93–0.99 for JLN; QS10 vs random walk 0.76–0.93 for
JLN, 0.82–0.93 for GZ spread; QS90 vs BVAR-SV 1.10–1.50 (all worse). Fixed-weight combination $\lambda=0.4$:
gains in all 36 quantile×horizon entries on JLNF12 (QS10 −9%, QS50 −1%, QS90 −4%); performance-based and
period-optimal weights push average left-tail gains to 18–21% (arXiv:2604.12927).

**Failure modes.** The asymmetric Laplace is a *working likelihood*, not the true DGP — posterior
concentration on the true quantile coefficients relies on the Sriram et al. result, so do not read the AL
parameters as a density; iterating the ALD mixture forward is explosive, hence Gaussian innovations for
multi-step; quantile estimation needs enough observations, which caps the lag order; sloppy weight
optimization overfits the right tail (JLN QS90 deteriorates at long horizons); and the target is a *monthly
average* real price, not an end-of-month price.

### 2.4 Hidden-Markov mean-reverting spread + filter-based EM for crude-oil stat arb
**Purpose.** Trade the temporary deviation of a cointegrated basket of crude oils from its equilibrium,
timing entries from a forward-looking prediction interval rather than a backward-looking band.

**Formula.** Estimate a cointegration vector $\lambda$ on the log futures $F^B,F^S,F^W$ (Johansen),
$S_t=\lambda^0+\sum_{i}\lambda^iF^i_t$, then model $S$ as an AR(1) modulated by a hidden Markov chain:
$$S_{t+1}=\gamma(X_t)+\alpha(X_t)S_t+\eta(X_t)z_{t+1},\qquad X_{t+1}=\Pi X_t+M_{t+1},$$
with $X_t\in\{e_1,\dots,e_N\}$ and $|\alpha_i|<1$ ensuring within-regime mean reversion. Filtering is online:
the likelihood weight matrix $D_t=\operatorname{diag}(d_t^{ii})$,
$$d^{ii}_t=\exp\!\Big(-\tfrac{1}{\eta_i^2}(\alpha_iS_{t-1}+\gamma_i)S_t
+\tfrac{1}{2\eta_i^2}(\alpha_iS_{t-1}+\gamma_i)^2\Big),$$
and the recursions $\widehat X_{t+1}=\Pi D_{t+1}\widehat X_t$ propagate the chain, occupation time $O$, jump
counts $J$ and moment accumulators $T^i(f)$. The filter-based EM updates are ratios of these filtered
quantities, e.g. $\widehat\pi_{ij}=\widehat J^{\,ij}_{t+1}/\widehat O^j_{t+1}$,
$\widehat\gamma_i=\big(\widehat T^i_{t+1}(S)-\widehat\alpha_i\widehat T^i_t(S)\big)/\widehat O^i_{t+1}$
(full set in eq. 2.7 of the paper). The continuous-time OU-HMM counterpart
$dS_t=a(X_t)(\beta(X_t)-S_t)dt+\xi(X_t)dW_t$ maps in via
$\alpha_i=e^{-a_i\Delta}$, $\gamma_i=\beta_i(1-e^{-a_i\Delta})$,
$\eta_i=\xi_i\sqrt{(1-e^{-2a_i\Delta})/(2a_i)}$. The **PredI** rule opens when
$$S_t\notin\Big(\mathbb E[S_t\mid\mathcal F^S_{t-1}]\pm |q_{\alpha/2}|\sqrt{\operatorname{Var}[S_t\mid\mathcal F^S_{t-1}]}\Big),$$
with $\mathbb E[S_t|\mathcal F_{t-1}]=\widehat\gamma(\widehat X_{t-1})+\widehat\alpha(\widehat X_{t-1})S_{t-1}$
and $\operatorname{Var}=\widehat\eta(\widehat X_{t-1})^2$; it closes on a zero crossing. Daily mark-to-market
return per unit gross notional $G_t=|\lambda_0|+\sum_k|\lambda_k|F_{tk}$ is
$$r_t=I_t\!\cdot\!\frac{F_t-F_{t-1}}{G_{t-1}}\!\cdot\!\sum_k\frac{|F^k_t\lambda_k|}{G_{t-1}}
-|\Delta I_t|\sum_k\frac{c_k|F^k_{t-1}\lambda_k|}{G_{t-1}},\qquad \Delta I_t=I_t-I_{t-1}.$$

**Required inputs.** Daily/weekly continuous futures price series for the cointegrated basket; per-contract
transaction-cost parameters (half bid-ask spread).

**Parameters & defaults.** VAR lag $p=2$ (Schwarz IC); normalise $\lambda$ by gross exposure; $N=2$ regimes
selected by minimum mean forecast error; $\alpha=0.20$ bandwidth (range 0.30 = ~1 SD to 0.05 = ~2 SD);
batch parameter $m=10$ (parameters updated every two weeks); initial $\widehat\pi_{11}=0.6,\widehat\pi_{22}=0.5$
(when $N=2$), other initials anchored to OLS AR(1) estimates on the first 20 points; denominator guards
truncate a new estimate to 10× the previous one.

**Observed effect sizes.** Baseline $N=2$: $\widehat\pi_{11}=0.8588$, $\widehat\pi_{22}=0.9732$,
$\widehat\alpha_1=0.6214$, $\widehat\alpha_2=0.8164$, $\widehat\eta_1=1.8343$, $\widehat\eta_2=1.2187$. PredI:
$R=15.18\%$, $SR=1.1792$ ($p<0.05$ vs $SR=0$), $N_{TW}=12$, mean trade return 1.2%; across 100 randomized
initializations mean $R=16.79\%$ (SD 3.49%), mean $SR=1.27$ (SD 0.25). PredI dominates ProbI and RI and is
identified as best by the White Reality Check; PredI MDD −5.73% vs ETF −39.47%. Transaction costs used:
Brent 5.80 bp, Shanghai 53.71 bp, WTI 20.24 bp, Dubai 1.52 bp (arXiv:2309.00875).

**Failure modes.** Cointegrating coefficients drift across windows, so a constant-$\lambda$ rule degrades;
roll yield in continuous series is only partly cancelled (the paper leans on cointegrating weights summing
≈0); EM likelihood is non-concave and initialization-sensitive (mitigated by 100-run randomization and by
state-labelling so State 1 has the larger $\gamma$); trading windows dwarf daily returns, so daily Sharpe
understates per-trade edge; the Shanghai leg alone carries the adjustment, so without it only the weaker
Brent–WTI pair remains; results are one test year (261 daily obs) and a small number of completed trades.

### 2.5 Variable Volatility Elasticity (VVE) model and commodity option pricing
**Purpose.** A continuous-time price model whose volatility is *positively* related to price — the
commodity-market stylized fact the CEV model cannot represent — with a closed-form European call.

**Formula.** Under the paper's Ito treatment of elasticity, a *constant* volatility elasticity forces
$\beta\in\{0,1\}$: $v_t=CS_t^{\beta}$, and $\beta=1$ gives $dS_t=S_t[\mu\,dt+CS_t\,dB_t]$. Allowing the
elasticity to depend on price gives the VVE SDE
$$dS_t=S_t\big[\mu\,dt+(\alpha+C_1S_t)\,dB_t\big],\qquad v_t=\alpha+C_1S_t,$$
with the closed-form mild solution (paper eq. 3.11, $B_t$ a Brownian motion)
$$S_t=\frac{S_0\,e^{\mu t+B_t}}{1-C_1S_0e^{\mu t+B_t}+C_1S_0e^{B_t}+C_1S_0},$$
and a European call price of the same structural shape as Black–Scholes,
$C(t,x)=S_0e^{-r(T-t)}\mathbb E[g(Z)\mathbf 1_{(d,\infty)}]-Ke^{-r(T-t)}(1-N(d))$ with
$g,\ d,\ f_t$ as defined in Theorem 5.1 of arXiv:2203.09177.

**Required inputs.** A commodity price series and a realized-volatility estimate (the paper uses 30-day
historical volatility HV30).

**Parameters & defaults.** $\mu$ constant (extendable to an adaptive process without changing the result);
$C_1>0$; calibration is a linear regression of HV30 on closing price.

**Observed effect sizes.** Soybean meal slope $1.53\times10^{-4}$ ($R^2=0.7471$, corr 0.8643), aluminium slope
$4.61\times10^{-5}$ ($R^2=0.8207$, corr 0.9059); intercepts −0.346 and −0.528; all $p<2\times10^{-16}$
(arXiv:2203.09177).

**Failure modes.** The positive vol–price relation is a *regime* property, not universal (the paper
validates it on two windows only — 2020 for meal, 2017–18 for aluminium); a large $C_1S_0$ makes the
denominator approach zero and the model blow up, so calibration must bound $C_1S_0<1$; the option formula
assumes completeness and a unique equivalent martingale measure; the empirical check is contemporaneous
HV30 vs price, so it is a fit, not a forecast.

### 2.6 Energy-trade-network measures (reciprocity, filling, null-model filtering)
**Purpose.** Summarise the *spatial* geometry of commodity trade — which energy commodity is most
reciprocated and least distance-constrained — as a structural diagnostic; **not** a tradable signal.

**Formula.** With adjacency $A=[a_{ij}]$ and distance matrix $D=[d_{ij}]$, the spatial filling and its
normalized form are
$$F=\sum_i\sum_{j\ne i}a_{ij}d_{ij},\qquad f=\frac{F-F_{\min}}{F_{\max}-F_{\min}};\qquad
F_{\min}=\sum_{n=1}^{L}d^{\uparrow}_n,\quad F_{\max}=\sum_{n=1}^{L}d^{\downarrow}_n,$$
and binary reciprocity and its null-model-filtered version are
$$r=\frac{L^{\leftrightarrow}}{L}=\frac{\sum_i\sum_{j\ne i}a_{ij}a_{ji}}{\sum_i\sum_{j\ne i}a_{ij}},
\qquad \rho_{NM}=\frac{r-\langle r\rangle_{NM}}{1-\langle r\rangle_{NM}},$$
with $\varphi_{NM}=(f-\langle f\rangle_{NM})/(1-\langle f\rangle_{NM})$ the filtered filling. Weighted
reciprocity uses the mutual flow $w^{\leftrightarrow}_{ij}=\min(w_{ij},w_{ji})$,
$r^W=\sum_{i}\sum_{j\ne i}w^{\leftrightarrow}_{ij}/W$. Two-layer overlapping flows are
$w^{\leftrightarrow}_{ij}(AB)_{syn}=\min(w^A_{ij}/W^A,\,w^B_{ij}/W^B)$ (and the reverse counterpart),
aggregated into $C^{syn(rev)}_{AB}=\sum_{i}\sum_{j\ge i}w^{\leftrightarrow}_{ij}$. Cross-network spatial
correlation is the Pearson index summed over node pairs, and the Mantegna distance is
$d^{c,c'}=\sqrt{(1-\varphi^{c,c'}_{w})/2}$.

**Required inputs.** A directed, weighted bilateral trade matrix per commodity and year (BACI/UN Comtrade),
a country-distance matrix, and a null-model constraint (link density or degree sequence, or a
balance-of-payments constraint for the adjusted reciprocity).

**Parameters & defaults.** Null models from exponential random graphs; both synergic and reverse flow
directions are computed; correlations averaged over 10 annual panels (1998–2007).

**Observed effect sizes.** Binary filling $f$: oil 0.25, coal 0.23, gas 0.20, electricity 0.18; connectance
oil 0.10–0.16 vs electricity 0.01–0.02; weighted reciprocity oil 0.25 (2007) vs coal 0.07, gas 0.08,
electricity 0.09; oil overlapping syn 0.40 / rev 0.34; reciprocity↔oil-price correlation −0.70 (raw) and
−0.78 (adjusted); reciprocity declines three years before the 1973 shock; oil grew 554% in value 1998–2007
vs 158% for total trade (arXiv:1509.05894).

**Failure modes.** Reciprocity in balanced-flow networks (imports≈exports) is achieved by pure chance, so the
*unfiltered* measure is meaningless — always report $\rho_{NM}$; the correlation is with a *single* macro
time series over one decade and has no out-of-sample test; the entire input (a trade matrix) is a **gap** in
the endpoint catalog.

## 3. Data requirements → available endpoints

Provider rows below are real entries in `strategies/endpoints.json` (exact `url`/`category`/`provider`);
`moomoo` rows are served by the local OpenD gateway and are not live-probed HTTP; "gap" means **no current
provider can supply it.**

| Input | Endpoint | Category | Provider | Probe status |
|---|---|---|---|---|
| Daily crude-oil spot (WTI/Brent, `DCOILWTICO`/`DCOILBRENTEU`) | `https://api.stlouisfed.org/fred/series/observations` | `macro_data` | fred | ok |
| Monthly oil price / CPI deflator / macro-financial series | `https://api.stlouisfed.org/fred/series/observations` | `macro_data` | fred | ok |
| Macro indicator catalogue (gateway) | `moomoo://get_macro_indicator_list` | `macro_data` | moomoo | gateway (not live-probed) |
| Commodity-linked ETF daily OHLCV (XLE/USO/DBO/DBA proxy) | `https://eodhd.com/api/eod/AAPL` | `core_stock_apis` | eodhd | ok |
| Commodity-linked ETF daily prices (secondary) | `https://api.tiingo.com/tiingo/daily/AAPL/prices` | `core_stock_apis` | tiingo | ok |
| Daily/prev aggregate bars | `https://api.massive.com/v2/aggs/ticker/AAPL/prev` | `core_stock_apis` | massive | ok |
| Daily EOD bars (tertiary) | `https://api.stockdata.org/v1/data/eod` | `core_stock_apis` | stockdata | ok |
| Intraday bars (1min+) for ETF proxies | `https://api.twelvedata.com/time_series` | `core_stock_apis` | twelvedata | ok |
| Intraday K-line via local OpenD gateway | `moomoo://get_cur_kline` | `technical_indicators` | moomoo | gateway (not live-probed) |
| Top-of-book snapshot (gateway) | `moomoo://get_market_snapshot` | `core_stock_apis` | moomoo | gateway (not live-probed) |
| Energy/commodity news headlines | `https://eodhd.com/api/news` | `news_data` | eodhd | ok |
| News sentiment scores | `https://eodhd.com/api/sentiments` | `news_sentiment` | eodhd | ok |
| News search (energy shocks) | `https://newsapi.org/v2/everything` | `news_data` | newsapi | ok |
| Macro-news sentiment | `https://www.alphavantage.co/query` | `news_sentiment` | alpha_vantage | ok |
| **Continuous crude futures (Brent/WTI, rolled) with roll schedule** | — | — | — | **gap** |
| **Shanghai (INE) crude futures** | — | — | — | **gap** |
| **Day-ahead / real-time power prices (any ISO or European zone)** | — | — | — | **gap** |
| **ISO system generation mix by fuel (wind/solar/etc.)** | — | — | — | **gap** |
| **Natural gas / coal / power futures & forward curves** | — | — | — | **gap** |
| **Commodity futures bid-ask spreads / transaction-cost inputs** | — | — | — | **gap** |
| **Commodity options chain / implied vol surface** | — | — | — | **gap** |
| **Bilateral trade-flow matrix (BACI / UN Comtrade)** | — | — | — | **gap** |
| **Chinese commodity futures (soybean meal, aluminium)** | — | — | — | **gap** |

**What the gap costs, quantified.** The functional-volatility work (arXiv:2605.13320) needed a panel of
2551 daily observations × 24 delivery periods = **61,368 price points per zone**, regenerated weekly into
2557 rolling estimates, for each of three European zones — and the endpoint catalog serves none of it. The
VRE study (arXiv:2112.11338) needed hourly to 5-minute price plus fuel-level generation for six US ISOs
across 2014–2020 (mean VRE share up to 46.38% in SPP) — also absent. The HMM strategy (arXiv:2309.00875)
needed three continuous futures series at daily+weekly frequency plus per-contract half-spreads; FRED can
supply WTI/Brent **spot** (the oil-price endpoints above), but not the rolled futures, not Shanghai, and not
the spreads that decide profitability — Brent trades at 5.80 bp round-trip half-spread while Shanghai costs
53.71 bp, a ~9× difference that flips strategies in and out of the money. The QBVAR (arXiv:2604.12927)
needed 602 monthly observations back to 1975 plus twelve macro-financial predictors (JLN uncertainty, EBP,
GZ spread, GPR series, OECD stocks, world rig count); oil and several spreads are partly reachable via FRED,
but the uncertainty and geopolitical indices are not. The VVE work (arXiv:2203.09177) needed 263 and 164
daily observations of Chinese commodity futures — absent. The network paper (arXiv:1509.05894) needed ten
annual bilateral trade matrices for four energy commodities (1998–2007) — absent. Net: **only the oil-price
and macro sub-feeds of this category are reachable today**, and they reach spot, not futures or options.

## 4. Pitfalls, validation and measurement

- **Look-ahead inside a volatility estimator.** The semigroup matrix in arXiv:2605.13320 is only estimable
  from past data; estimating it on the full sample and reusing it is a leak. Re-estimate on trailing data
  every 28 days after a 52-week burn-in, exactly as the paper does out-of-sample.
- **Confusing mean-reversion with volatility.** With $PS\approx0.4$, a naive realized-covariance estimator
  attributes ~40% of price variation to predictable mean-reversion (arXiv:2605.13320). Any power-vol product
  built on the raw estimator will overstate vol and, worse, will show a spurious *negative* early–late
  correlation block that vanishes after propagation adjustment.
- **Apparent leverage effects are often mechanical.** The "inverse leverage" in power disappears once price
  level and volatility mean-reversion are partialled out (Wald $p=0.5898$ joint, vs 0.0062/0.0128 partial,
  arXiv:2605.13320). Never report a leverage coefficient without the level and mean-reversion controls.
- **Detrend before any distributional regression.** Seasonality and diurnal demand drive electricity price;
  arXiv:2112.11338 removes hour, season, hour×season and weekend terms before fitting quantiles, and uses
  the *residual* for both price and EWMSD volatility. Fitting on raw prices conflates demand cycles with the
  VRE effect.
- **Metric choice is the result.** Quantile score, not RMSE, is the right loss for a quantile forecast
  (arXiv:2604.12927); the whole point is that the same model can win the left tail and lose the right tail
  (QS10≈0.8 vs QS90≈1.2–1.5 against BVAR-SV). Report QS ratios per quantile *and* per horizon, never a
  single average.
- **Baseline discipline and multiple testing.** The random walk is hard to beat (arXiv:2604.12927), so every
  commodity forecast must be scored against a no-change benchmark as well as a model benchmark. When many
  strategy variants are backtested, use the White Reality Check and a Ledoit–Wolf Sharpe test with a
  stationary bootstrap (2,000 replications, block length 20) — arXiv:2309.00875 reports both and finds RI
  never significant while PredI is.
- **Transaction costs decide the sign.** Net-of-cost profitability hinges on the spread: the Shanghai leg's
  53.71 bp cost is nearly an order of magnitude above Brent's 5.80 bp, and the paper's own robustness section
  sweeps cost levels (arXiv:2309.00875). Any pairs rule must be reported at the contract-specific cost,
  estimated as the average daily half bid-ask spread.
- **Regime dependence and structural breaks.** Germany's zone was coupled to Austria before Oct 2018 and
  European zones moved from 24 to 96 delivery periods after Sep 2025 — both reasons to *exclude* windows,
  which arXiv:2605.13320 does. Cointegration vectors for crude oil are documented as window-dependent
  (arXiv:2309.00875), which is exactly why that paper models the spread with hidden regimes rather than a
  constant.
- **Working-likelihood misspecification.** The asymmetric Laplace in QBVAR is a computational device; treat
  the quantile regression coefficients, not the AL parameters, as the object of interest (arXiv:2604.12927).
- **Small-sample initialization sensitivity.** EM likelihoods are non-concave; arXiv:2309.00875 runs 100
  randomized initializations and reports mean/SD for every parameter, with state labelling fixed by
  $\gamma$ magnitude. Replicate that before trusting a regime model.
- **Null models for network measures.** In balanced trade flows, reciprocity is largely a balancing artifact;
  only the null-model-filtered $\rho_{NM}$ and $\varphi_{NM}$ carry information (arXiv:1509.05894).

## 5. Recommended first implementation in FinRobot

Ordered by value-per-effort against data the layer can fetch today. Items 1–2 run now on the endpoints in
§3; items 3–6 are research-only and need a user-supplied panel or a new feed.

1. **Oil-price quantile forecaster (QBVAR-lite) on FRED data.** *What:* §2.3 reduced to a small Bayesian
   quantile regression / quantile VAR on monthly real WTI or Brent (CPI-deflated, log growth) plus the
   reachable financial-condition predictors. *Data:* fred `series/observations` (oil + CPI + spreads).
   *Passing result:* QS10 ratio < 1.00 vs a random walk over the 2013M1–2025M2 evaluation window at
   $h\le6$, and QS50 ratio ≤1.00 — i.e. reproduce the left-tail gain, not the right-tail loss.
2. **Cointegrated HMM pairs rule on Brent–WTI spot.** *What:* §2.4 with the reachable two-leg basket
   (drop the Shanghai leg, which is a gap) — Johansen cointegration on daily log prices, two-regime AR-HMM,
   filter-based EM with the paper's defaults ($m=10$, $\alpha=0.20$), PredI entry, zero-cross exit, and the
   paper's transaction-cost term. *Data:* fred daily spot for Brent and WTI. *Passing result:* PredI Sharpe
   > ProbI Sharpe on a held-out year, positive annualized return after the Brent/WTI half-spreads, and a
   completed-trade count and mean trade return consistent with the paper's order of magnitude.
3. **Power realized-covariation estimator as a research module.** *What:* §2.2 implemented against any
   user-supplied day-ahead panel; expose $PS$, the adjusted $\widehat\Sigma$, realized correlations and the
   first few PCs. *Data:* none live — **blocked on a power feed**. *Passing result:* $PS\approx0.4$, and the
   negative early–late realized-correlation block flips positive after adjustment.
4. **VRE quantile / skew-t regression as a scenario tool.** *What:* §2.1 on a user-supplied ISO price +
   generation panel; report the 0.50 and 0.90 quantile slopes and the skew-t shape path. *Data:* none live —
   **blocked**. *Passing result:* sign and monotone tail compression as in the paper, with the price-cap
   fraction reported.
5. **VVE vol–price calibration and option pricer.** *What:* §2.5 fit $v_t=\alpha+C_1S_t$ on any commodity
   series FinRobot holds (start with a commodity ETF's realized vol vs price, unblocked), then expose the
   European call formula. *Data:* eodhd/tiingo/massive daily bars for ETF proxies. *Passing result:*
   $R^2>0.70$ with a positive slope over a rolling window, and a no-arbitrage sanity check on the option
   price.
6. **Energy-trade-network diagnostic.** *What:* §2.6 on a user-supplied BACI/Comtrade panel; output
   reciprocity, filling, filtered variants and the reciprocity↔oil-price correlation. *Data:* none live —
   **gap**. *Passing result:* reproduce the ordering oil > coal ≈ gas > electricity in weighted reciprocity
   and the negative reciprocity–price correlation.
7. **Register a commodity/electricity data category.** *What:* add ingestion for continuous futures,
   power day-ahead prices and ISO generation mix as new categories (mirroring the pattern used for the
   equity feed), since §2.1, §2.2 and the full three-leg §2.4 are otherwise permanently research-only.
   *Data:* the feed itself. *Risk:* licensing and storage; the power panel alone is $O(10^5)$ points/zone.
   *Effort:* L.
8. **Cost-and-benchmark wrapper for every commodity signal.** *What:* a shared harness that forces each
   signal through contract-specific half-spreads, a random-walk benchmark, and a White Reality Check over
   the strategy set. *Data:* none beyond the signal. *Passing result:* standard output for every future
   commodity experiment, matching the reporting of arXiv:2309.00875.

Overlap note: the generic quantile-forecast and realized-volatility machinery is also treated in
[`../qfin-st/econometrics-forecasting.md`](../qfin-st/econometrics-forecasting.md) and
[`../qfin-st/volatility-modeling.md`](../qfin-st/volatility-modeling.md); the pairs/cointegration execution
in [`../qfin-st/mean-reversion-pairs.md`](../qfin-st/mean-reversion-pairs.md) and
[`../qfin-st/regime-switching.md`](../qfin-st/regime-switching.md); the option formula in
[`../qfin-st/derivatives-options.md`](../qfin-st/derivatives-options.md); the tail-scores and drawdown
reporting in [`../qfin-st/risk-management-tails.md`](../qfin-st/risk-management-tails.md); and the network
measures in [`../qfin-st/correlation-networks-econophysics.md`](../qfin-st/correlation-networks-econophysics.md).
This document spends its space on what is new here: the electricity-price/volatility estimators, the
commodity-specific positive vol–price elasticity, and the crude-oil HMM stat-arb rule.

## Appendix — papers read

| arXiv id | title | year |
|---|---|---|
| 2112.11338v3 | Role of Variable Renewable Energy Penetration on Electricity Price and its Volatility Across Independent System Operators in the United States | 2021 |
| 1509.05894v2 | A network analysis of the global energy market: an insight on the entanglement between crude oil and the world economy | 2015 |
| 2605.13320v1 | The fine structure of electricity price volatility | 2026 |
| 2604.12927v1 | Forecasting Oil Prices Across the Distribution: A Quantile VAR Approach | 2026 |
| 2309.00875v3 | A hidden Markov model for statistical arbitrage in international crude oil futures markets | 2023 |
| 2203.09177v1 | The Variable Volatility Elasticity Model from Commodity Markets | 2022 |