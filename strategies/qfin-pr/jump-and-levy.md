# Jumps & Lévy Processes — learnings from the q-fin.PR corpus
`261` of 2274 corpus papers matched this category (`261` with PDFs); this doc is based on a close reading of `6`.

## 1. What the corpus actually offers

- **Jump risk is a separate priced factor, and it clusters.** A bivariate Hawkes model with self-excited positive *and* negative jump intensities — cross-excitation with signs $\beta_{11},\beta_{21}\ge0$ and $\beta_{12},\beta_{22}\le0$, and stability constraints $\kappa^{+}\ge\beta_{11}\mathbb{E}J^{+}+\beta_{12}\mathbb{E}J^{-}$, $\kappa^{-}\ge\beta_{21}\mathbb{E}J^{+}+\beta_{22}\mathbb{E}J^{-}$ — reproduces both an asymmetric, time-varying skewness and sign-flipping implied-volatility skews, which a constant-correlation stochastic-volatility model structurally cannot (arXiv:2510.21297v1).
- **Jump intensities carry the measured information, not just jump sizes.** Inferred positive/negative jump risk premia ($\chi^{+},\chi^{-}$) mean-revert toward zero, co-move with the negative premium larger, and explain the BTC futures cost-of-carry: adjusted $R^2$ 14.7% for the premia alone, 19.6% with last-week jump counts, 28% with the funding rate, 31% with all; a one-unit rise in the positive premium adds $0.75$ bp and in the negative premium $0.97$ bp to the annualised basis (arXiv:2510.21297v1).
- **Tempered-stable beats Black–Scholes exactly where it should.** Fitting a seven-parameter Generalized Tempered Stable (GTS) law to S&P 500 daily returns gives stability indices $<1$ ($\beta_+=0.6823$, $\beta_-=0.2426$), left-skew via $\lambda_+>\lambda_-$ and a higher positive jump arrival rate $\alpha_+>\alpha_-$; Black–Scholes prices are *lower* for near-the-money and in-the-money options but coincide with GTS for deep out-of- and deep in-the-money options (arXiv:2304.06060v3).
- **Self-excitation is analytically cheap if you pick the right process.** The Queue-Hawkes process has a closed-form characteristic function, so the Heston-Queue-Hawkes (HQH) model prices European and Bermudan options with the COS method at $0.118$ s per 420-price grid versus $1.457$ s for Heston–Hawkes ($12.4\times$) and $0.089$ s for Bates ($16.4\times$); the HQH/HH price gap grows with the degree of self-excitation $\alpha/\beta$ and the initial intensity ratio $Q_0/\theta_0$ (arXiv:2205.13321v2).
- **Path-integral methods extend to jumps by a multiplicative propagator factor.** Adding an arbitrary compound-Poisson jump to any stochastic-volatility model multiplies its Fourier propagator by $e^{U(p,T)}$, $U(p,T)=\lambda T\int\big(e^{-ipJ}-1+ip(e^{J}-1)\big)\varpi(J)\,dJ$; the resulting exponential-Vasicek-with-jumps vanilla prices match Monte Carlo to <2%, but the underlying *approximation* is only valid for $c=\beta/\gamma^{2}>7$ (arXiv:1011.1175v1).
- **The whole infinite-activity family is one approximable class.** Variance Gamma, KoBoL/CGMY, Meixner, normal inverse Gaussian and generalized hyperbolic all have completely monotone Lévy densities ("generalized hyper-exponential"), so barrier prices and Greeks can be obtained by a single Laplace-transform-in-time inversion after fitting a finite hyper-exponential density (7 phases each side), with Wiener–Hopf factors available analytically only for the hyper-exponential approximant (arXiv:0812.3128v2).
- **American jump pricing reduces to an integral equation, and jumps move the exercise boundary.** The American price decomposes into a European term plus an early-exercise premium whose jump contribution is an integral of the Lévy measure; the exercise boundary at expiry is $XB(T^-)=K\min(1,r(T)/q(T))$ only in the pure-diffusion case — with jumps the terminal boundary solves an extra fixed-point equation in $\nu(dy)$ (arXiv:2506.18210v3).

## 2. Implementable formulas & algorithms

### 2.1 Merton jump-diffusion (compensated)
**Purpose.** Baseline jump-diffusion sampler/pricer; the "no-clustering" limit every richer model is measured against.

Risk-neutral dynamics and log-return SDE:
$$\frac{dS_t}{S_t}=(r-\lambda m_j)\,dt+\sigma\,dW_t+(e^{J}-1)\,dN_t,\qquad m_j=\mathbb{E}[e^{J}-1]=\int(e^{J}-1)\varpi(J)\,dJ$$
$$dx_t=\Big(r-\lambda m_j-\tfrac12\sigma^{2}\Big)dt+\sigma\,dW_t+J\,dN_t .$$
With Gaussian jump size $J\sim\mathcal{N}(\nu,\delta^{2})$ the transform factor is
$$U_M(p,T)=\lambda T\Big[e^{-ip\nu-\frac12\delta^{2}p^{2}}-1+ip\big(e^{\nu+\frac12\delta^{2}}-1\big)\Big].$$

- **Inputs:** spot $S_0$, $r$, dividend yield $q$; jump-calibrated $\lambda,\nu,\delta$; option quotes for calibration.
- **Parameters:** $\lambda$ (intensity), $\nu,\delta$ (jump mean/std). Estimate by CF fit to option prices (COS/FFT) or by POT filtering (§2.4).
- **Observed effects:** reproduces short-maturity skew that pure diffusion cannot; underpricing of near-the-money/ITM vs. GTS shows Merton alone is too thin-tailed (arXiv:1011.1175v1, arXiv:2304.06060v3).
- **Failure modes:** constant intensity cannot cluster jumps, so it cannot produce sign-flipping skew; calibrating $\lambda,\nu,\delta$ from a single maturity is ill-posed (arXiv:2510.21297v1).

### 2.2 Kou double-exponential / hyper-exponential jumps
**Purpose.** Capture skew and a fat negative tail with a jump-size density that stays analytically tractable.

$$\varpi_K(J)=p_+\eta_+^{-1}e^{-J/\eta_+}\Theta(J)+p_-\eta_-^{-1}e^{J/\eta_-}\Theta(-J),\quad 0<\eta_+<1,\ \eta_->0,\ p_++p_-=1$$
$$U_K(p,T)=\lambda T\left[\frac{p_+}{1+ip\eta_+}+\frac{p_-}{1-ip\eta_-}-1+ip\Big(\frac{p_+}{1-\eta_+}+\frac{p_-}{1+\eta_-}-1\Big)\right].$$
The hyper-exponential class keeps a Lévy density $k_+(x)=\lambda^+\sum_i p_i^+\alpha_i^+e^{-\alpha_i^+x}$ with measure $\mu_+(du)=\lambda^+p_i^+\alpha_i^+\delta_{\alpha_i^+}(du)$ (arXiv:0812.3128v2).

- **Inputs:** the same as §2.1 plus separately identified up/down intensities $p_\pm,\eta_\pm$.
- **Parameters:** $\lambda,p_\pm,\eta_\pm$ ($\eta_+<1$ for finite positive-mean jump; $>$2 phases needed for NIG/VG fits).
- **Observed effects:** Kou is dense in the generalized hyper-exponential class, so it *approximates* VG/NIG barrier prices once a hyper-exponential density is fitted; 7 up/down phases give 0.5–2.5% price/delta error away from the barrier (arXiv:0812.3128v2).
- **Failure modes:** errors grow close to the barrier, especially for delta; a single-exponential fit understates VG/NIG tail behaviour (arXiv:0812.3128v2).

### 2.3 Variance Gamma / NIG via subordination and time-Laplace transforms
**Purpose.** Infinite-activity Lévy pricing for barrier and digital options; calibrate once, price a whole barrier book.

$X=W(Y(t))+\mu Y(t)$ with $Y$ a generalized hyper-exponential subordinator gives Lévy density $k(x)=\int_0^\infty (2\pi s)^{-1/2}e^{-(x-\mu s)^2/(2s)}\rho(s)\,ds$; VG is the $Y=0$ KoBoL case $k_+(x)=Cx^{-1}e^{-Mx}$, NIG has $\mu_+(du)=C\delta\alpha/\pi\cdot(([u+\beta]/\alpha)^2-1)^{1/2}\mathbf{1}_{u\ge\alpha-\beta}\,du$ (arXiv:0812.3128v2). Prices and Greeks of single-barrier options come from a time-Laplace transform $\int_0^\infty e^{-qt}$ … inverted with the Abate–Whitt algorithm; only a *one-dimensional* inversion is needed because the hyper-exponential model admits an explicit Wiener–Hopf factorisation of $\Psi(u)=\log\mathbb{E}[e^{iuX(1)}]$ (arXiv:0812.3128v2).

- **Inputs:** drift $r-d$; a target Lévy density (VG/NIG/CGMY) and option quotes for calibration.
- **Parameters:** target-model params ($C,M,Y$ / $\alpha,\beta,\delta$) plus the fitted hyper-exponential phases ($u_i,p_i$).
- **Observed effects:** parameters calibrated to Stoxx50E call options; agreement with Monte Carlo 0.5–2.5% for prices and deltas, worse near the barrier (arXiv:0812.3128v2).
- **Failure modes:** for a general Lévy process the Wiener–Hopf factors are not analytically tractable, so the approximation is the only route; a three-dimensional Laplace/Fourier inversion would otherwise be required (arXiv:0812.3128v2).

### 2.4 Generalized Tempered Stable: Esscher martingale measure and Fourier pricing
**Purpose.** Seven-parameter infinitely divisible fit that nests VG, bilateral Gamma and CGMY; price European options directly under a structure-preserving EMM.

$$\nu(dx)=\frac{\alpha_+e^{-\lambda_+x}}{x^{1+\beta_+}}\mathbf{1}_{x>0}dx+\frac{\alpha_-e^{-\lambda_-|x|}}{|x|^{1+\beta_-}}\mathbf{1}_{x<0}dx,\quad 0\le\beta_\pm<1$$
$$\Psi(\xi)=\mu\xi i+\alpha_+\Gamma(-\beta_+)\big[(\lambda_+-i\xi)^{\beta_+}-\lambda_+^{\beta_+}\big]+\alpha_-\Gamma(-\beta_-)\big[(\lambda_-+i\xi)^{\beta_-}-\lambda_-^{\beta_-}\big].$$
The Esscher transform with parameter $h^{*}$ (solution of $\Psi_{h^*}(1)=r$) is closed under GTS, mapping $\lambda_+\to\lambda_+-h^{*}$, $\lambda_-\to\lambda_-+h^{*}$; the extended Black–Scholes call price is
$$F^{\text{GTS}}_{\text{call}}=S(t)\big[1-F(\log(K/S(t)),\tau,h^{*}+1)\big]-Ke^{-r\tau}\big[1-F(\log(K/S(t)),\tau,h^{*})\big].$$

- **Inputs:** daily return series (for MLE of the seven parameters); $r$ for the Esscher root; contracts for validation.
- **Parameters (S&P 500, 2010-01-04→2023-06-16):** $\mu=-0.6935,\ \beta_+=0.6823,\ \beta_-=0.2426,\ \alpha_+=0.4586,\ \alpha_-=0.4144,\ \lambda_+=0.8222,\ \lambda_-=0.7276$; at $r=6\%$, $h^*=-2.4448$ (arXiv:2304.06060v3).
- **Observed effects:** FRFT and the 12-point composite Newton–Cotes rule agree to two decimals; BS is underpriced for NTM/ITM and matches deep OTM/ITM (arXiv:2304.06060v3).
- **Failure modes:** seven parameters are weakly identified from daily data — the MLE needs second/third derivatives and the reported Hessian eigenvalues oscillate before convergence (−4664.8 → −4659.19 over 28 iterations); the density has no closed form and must be recovered by inverse Fourier transform (arXiv:2304.06060v3).

### 2.5 Bivariate Hawkes: jump intensities as state variables
**Purpose.** Model clustered up/down jumps and extract *jump risk premia* by comparing P and Q jump expectations.

Intensity dynamics and MGF (Prop. 1, arXiv:2510.21297v1):
$$\begin{aligned}d\lambda^{+}_t&=\kappa^{+}(\theta^{+}-\lambda^{+}_t)\,dt+\beta_{11}J^{+}dN^{(1)}_t+\beta_{12}J^{-}dN^{(2)}_t,\\ d\lambda^{-}_t&=\kappa^{-}(\theta^{-}-\lambda^{-}_t)\,dt+\beta_{21}J^{+}dN^{(1)}_t+\beta_{22}J^{-}dN^{(2)}_t,\end{aligned}$$
$$\mathbb{E}^P\!\big[e^{\omega X_T+\omega^+\lambda^{+}_T+\omega^-\lambda^{-}_T}\big]=\exp\!\big(A(t,T)+\omega X_t+C(t,T)\lambda^{+}_t+D(t,T)\lambda^{-}_t\big),$$
with $A,C,D$ solving the coupled ODE system (Eq. 12) and jump-size Laplace transforms $L^{(\pm)}$ from shifted-exponential PDFs. The measure change is parameterised by two *external* premia $\chi^{+},\chi^{-}$; a $5\times5$ linear system with unit determinant returns the internal parameters $(\xi^{+},\xi^{-},c^{+},c^{-},c)$ uniquely, and under Q the intensities scale by $L^{(+)}(-\chi^{+})$, $L^{(-)}(-\chi^{-})$ and the jump-size means by $\eta^{+,Q}=\eta^{+}/(1-\eta^{+}\chi^{+})$.

- **Inputs:** daily log-returns for P-side estimation; option chain implied vols by delta and maturity for Q-side; risk-free rate.
- **Parameters:** drift $\mu$, vol $\sigma$; 8 intensity parameters $(\kappa^\pm,\theta^\pm,\beta_{ij})$; 4 jump-size parameters $(\nu^\pm,\eta^\pm)$; 2 premia $\chi^\pm$; risk price $\varphi(t)$ of the continuous part.
- **Estimation protocol (as reported):** POT threshold by minimising $|\text{skew}|+|\text{kurt}|$ of the retained returns; MLE of intensities on the partial likelihood; then fit $\sigma,\chi^{+},\chi^{-}$ to mid IVs of one-month, $0.8\le$moneyness$\le1.2$ options (arXiv:2510.21297v1).
- **Observed effects:** $R^2$ 14.7→31% on the BTC basis; BTC ATM 1-month IV averaged 68.3% (range 40–140%), 25-delta call/put skews averaged +3.0%/+1.7% (arXiv:2510.21297v1).
- **Failure modes:** ODE system must be integrated numerically (Runge–Kutta) per strike grid — the model has no free lunch; parameters estimated on 2015–2019 price data only, with intensities inferred forward under fixed parameters to avoid look-ahead (arXiv:2510.21297v1).

### 2.6 Heston-Queue-Hawkes: self-excited jumps with a closed-form characteristic function
**Purpose.** Add jump clustering to stochastic volatility while keeping Fourier pricing exact and fast; usable for Bermudan early exercise.

Under Q, $dS_t/S_t=(r-\lambda_t\mathbb{E}[e^{Y}-1])dt+\sqrt{V_t}\,dW^S_t+(e^{Y_t}-1)dN_t$, with $dV_t=\kappa(\eta-V_t)dt+\xi\sqrt{V_t}dW^V_t$; the CF factorises as
$$\phi(v;t)=\phi_{\text{Heston}}(v;t)\cdot\phi_M(v;t),$$
so the jump part is computed separately. For pure-jump (discrete) laws use the discrete COS (DCT) expansion $p_X(n)=\sum_k A_k\cos(k(2n+1)\pi/2N)$ with $\hat A_k=\mathrm{Re}\{\phi_X(k/2N)e^{ik\pi/2N}\}/N$.

- **Inputs:** Heston parameters $(\kappa,\eta,\xi,\rho,V_0)$; jump-process parameters; the same option quotes for calibration.
- **Parameters:** Q-Hawkes clustering rate $\alpha$, expiration rate $\beta$, baseline $\theta$, initial $Q_0$; jump law $Y\sim\mathcal{N}(\nu_Y,\delta_Y^2)$.
- **Observed effects:** Bermudan IV rises over the first exercise dates then plateaus; the HQH/HH gap widens with $\alpha/\beta$ and $Q_0/\theta_0$; HQH is $12.4\times$ and Bates $16.4\times$ faster than HH (arXiv:2205.13321v2).
- **Failure modes:** the discrete COS *always overestimates* the PMF ($\hat p_X\ge p_X$) with order $O(N^{-1})$ for the uniform law but exponential for smooth (Poisson) laws; the Q-Hawkes law is discrete and violates COS's continuity assumption unless the DCT variant is used (arXiv:2205.13321v2).

### 2.7 Path-integral propagator with jumps (exponential Vasicek illustration)
**Purpose.** Extend any stochastic-volatility model's Fourier propagator to jumps by a single multiplicative factor, and price vanilla options by contour integration.

$$P^{J}(x_T,\sigma_T,T\mid x_0,\sigma_0,0)=\int\frac{dp}{2\pi}e^{ip(x_T-x_0)}F(\sigma_T,\sigma_0,r,p,T)e^{U(p,T)}$$
$$C=\frac{S_0-Ke^{-rT}}{2}+\frac{i}{2\pi}\int\frac{dp}{p}\big[S_0F(p+i,T)e^{U(p+i,T)}-Ke^{-rT}F(p,T)e^{U(p,T)}\big].$$
For the lognormal-volatility (exponential Vasicek, LN) model $d\sigma=\sigma\big[\beta(\bar a-\ln\sigma)+\tfrac12\gamma^{2}\big]dt+\gamma\sigma\,dW_2$, $\sigma_0=\exp(\bar a+\gamma^{2}/4\beta)$.

- **Inputs:** $S_0,K,T,r$, correlation $\rho$; SV params $(\beta,\bar a,\gamma)$; jump density $\varpi(J)$ (Merton $\varpi_M$ or Kou $\varpi_K$).
- **Parameters:** LN model $(\beta,\bar a,\gamma,\rho)$; jump $(\lambda,\nu,\delta)$ or $(\lambda,p_\pm,\eta_\pm)$.
- **Observed effects:** LN propagator matches 5,000,000-path Monte Carlo for $T\in[0.25,5]$ and $\rho\in\{-0.5,0,0.5\}$; LN+jumps prices match 300,000,000-path MC to <2% (arXiv:1011.1175v1).
- **Failure modes:** the saddle-point expansion $e^{\zeta}\approx1+\zeta+\zeta^2/2$ is only accurate for $c=\beta/\gamma^{2}>7$ (checked to $c<25$), $|\rho|<0.5$, $T<1$, $0.9<K/S_0<1.1$; outside that the propagator is qualitatively wrong (arXiv:1011.1175v1).

### 2.8 American options in jump-diffusion and Lévy models (Volterra integral equation)
**Purpose.** Explicit early-exercise boundary and price for American puts/calls under time-inhomogeneous jump-diffusion and pure-Lévy dynamics, avoiding PIDE/FD/Monte-Carlo.

$$P(t,x)=\mathbb{E}^Q\!\big[D(t,T)(K-X_T)^{+}\big]+\int_t^T D(t,u)\mathbb{E}^Q\!\big[\Omega(u,X_u)\mathbf{1}_{X_u\in E}\big]du,$$
$$\Omega(u,X_u)=\mu(u,X_u)+r(u)(K-X_u)+\int_{\log(XB(u)/X_u)}^{\infty}\big[P_E(u,X_ue^{y})-K+X_ue^{y}\big]\nu(dy).$$
The jump term is a pseudo-differential operator: $\int[P(u,z_u+\bar y)-P(u,z_u)-(e^{\bar y}-1)\partial_z P]\nu(d\bar y)=\mathcal{J}P$ with $\mathcal{J}=\psi(-i\nabla)$, the Lévy characteristic exponent evaluated at $-i\nabla$. The maturity limit is $b=K\min(1,b_*)$ with $b_*$ from $\frac{b_*}{K}=\frac{r(T)-\int_{\log(K/b_*)}^{\infty}\nu(dy)}{q(T)-\int_{\log(K/b_*)}^{\infty}e^{y}\nu(dy)}$.

- **Inputs:** model SDE and its CF (or transition density); $r(t),q(t)$; contract data.
- **Parameters:** model parameters; COS truncation $[a,b]$ and terms $N_x,N_v$; quadrature grid in time.
- **Observed effects:** the exercise boundary solves a nonlinear Volterra equation in 3–5 iterations; OU test needs 0.33 s (MATLAB, $M=20$) for a 7-strike boundary curve; the 3/2 model boundary surface took 25 s at $N_x=N_v=32$ and 58 s at 64, versus 0.08 s for Heston (arXiv:2506.18210v3).
- **Failure modes:** COS is unstable for very short maturities (NUFFT is ~40× faster and more robust); the jump pricing operator is non-local in $P$ and must be localised via Padé approximations of $\psi(-i\nabla)$; smooth pasting fails for bounded-variation Lévy processes, so continuous pasting must be assumed (arXiv:2506.18210v3).

## 3. Data requirements → available endpoints

| Input | Endpoint | Category | Provider | Probe status |
|---|---|---|---|---|
| Underlying daily OHLCV (P-side parameter estimation) | `https://eodhd.com/api/eod/AAPL` | core_stock_apis | eodhd | ok |
| Underlying daily OHLCV (alt) | `https://api.tiingo.com/tiingo/daily/AAPL/prices` | core_stock_apis | tiingo | ok |
| Aggregate bar series (alt) | `https://api.massive.com/v2/aggs/ticker/AAPL/prev` | core_stock_apis | massive | ok |
| Delayed SPX option chain + implied vols (calibration target) | `https://cdn.cboe.com/api/global/delayed_quotes/options/_SPX.json` | options_surface | cboe | ok |
| Option chain (local gateway) | `moomoo://get_option_chain` | options_data | moomoo | gateway |
| ATM implied vol / expected move | `moomoo://get_option_underlying_overview` | expected_move | moomoo | gateway |
| Risk-free discount curve | `https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2026/all` | risk_free_curve | federal_reserve | ok |
| Dividend yield / corporate actions | `https://eodhd.com/api/div/AAPL` | corporate_actions | eodhd | ok |
| Macro state (rates, term spread, HY spread) | `https://api.stlouisfed.org/fred/series/observations` | macro_data | fred | ok |
| News/attention features (jump sentiment linkage) | `https://eodhd.com/api/news` | news_data | eodhd | ok |
| News tone (alt) | `https://api.gdeltproject.org/api/v2/doc/doc` | news_sentiment | gdelt | fail — HTTP 429 rate_limited |
| Intraday/tick returns for non-parametric jump tests (Lee–Mykland, BNS, POT) | **gap** — no provider exposes certified intraday bars; twelvedata `interval` and massive aggregates are unverified candidates | core_stock_apis | — | gap |
| BTC/crypto spot and options (clustered-jump empirical study) | **gap** — no crypto provider in the inventory | — | — | gap |
| BTC futures basis / perpetual funding rate | **gap** — no futures or funding feed | — | — | gap |
| FX spot and FX option quotes (Markov-modulated Merton FX) | **gap** — no FX provider | — | — | gap |
| CDS spreads / credit data (jump-diffusion credit-risk calibration) | **gap** — no credit or CDS feed | — | — | gap |
| Swap/swaption quotes (Lévy term-structure pricing) | **gap** — no rates-derivatives feed | — | — | gap |
| Realized variance / variance-swap strikes (volatility derivatives under jumps) | **gap** — no variance-swap or precomputed RV endpoint | — | — | gap |

## 4. Pitfalls, validation and measurement

- **Jump detection is itself an estimator with error.** The POT threshold is chosen by minimising $|\text{skew}|+|\text{kurt}|$ over retained returns, assuming the continuous part is Gaussian; this is a modelling assumption, not a data feature, and threshold choice directly biases $\lambda,\eta^\pm$ (arXiv:2510.21297v1).
- **Jump models are incomplete markets, so the price is not determined by no-arbitrage.** A unique EMM does not exist; the Q used for pricing must be pinned by calibration to option prices (Esscher transform in GTS, external premia $\chi^\pm$ in the Hawkes model). Any "model price" is measure-conditional (arXiv:2506.18210v3, arXiv:2304.06060v3, arXiv:2510.21297v1).
- **Look-ahead leakage in P/Q splits.** Estimate the P-side parameters on one sample and *fix* them when inferring intensities forward; the reported Hawkes protocol estimated on 2015–2019 prices and applied the frozen parameters to 2019–2023 with no look-ahead bias (arXiv:2510.21297v1). Never re-fit jump parameters per option date.
- **Calibration overfit in high-parameter models.** GTS's seven parameters show a non-monotone Hessian spectrum and a long convergence plateau in the reported MLE; report the log-likelihood trajectory and Hessian eigenvalues, not just the point estimate (arXiv:2304.06060v3).
- **Numerical-method failure modes change answers.** COS degrades at short maturities and near the exercise boundary (use NUFFT); the discrete COS *overestimates* pure-jump probabilities by construction; barrier Greeks are worst closest to the barrier (arXiv:2506.18210v3, arXiv:2205.13321v2, arXiv:0812.3128v2).
- **Every approximation has a stated validity region.** Report and enforce it: LN path-integral needs $c=\beta/\gamma^{2}>7$, $|\rho|<0.5$, $T<1$, $0.9<K/S_0<1.1$; the hyper-exponential barrier approximation is validated only 0.5–2.5% away from the barrier (arXiv:1011.1175v1, arXiv:0812.3128v2).
- **Validation protocol used across the corpus.** (i) Monte-Carlo cross-check of analytic prices (5M–300M paths); (ii) Q–Q plots of compensator-transformed jump inter-arrival times against a standard exponential; (iii) out-of-sample exercise of the fitted model (option-strategy returns, futures basis regressions with Newey–West $t$-stats); (iv) at minimum, residual/step diagnostics for MLE convergence (arXiv:1011.1175v1, arXiv:0812.3128v2, arXiv:2510.21297v1, arXiv:2304.06060v3).
- **Model comparison needs formal tests, not point estimates.** Pairwise comparisons (e.g. jump model vs. Bates/Heston) should use Diebold–Mariano and a Model Confidence Set rather than comparing a single $R^2$; the Hawkes paper's own $R^2$ falls from 31% when the premium is correlated with the funding rate (corr 36.7%), so coefficients shrink and lose significance as collinear regressors are added (arXiv:2510.21297v1).

## 5. Recommended first implementation in FinRobot

1. **Fourier jump-diffusion pricer (Merton + Kou) on the served SPX chain (S).** Implement the CFs of §2.1–2.2, price European options by COS/FFT and calibrate the jump parameters per maturity slice. Data: `cboe` `options_surface` + `federal_reserve` `risk_free_curve` + `eodhd` OHLCV. Value: a jump-price baseline plus the CF/propagator machinery every later model reuses. Risk: one delayed SPX chain limits strike coverage; deep-OTM calibration is unstable (arXiv:1011.1175v1, arXiv:0812.3128v2).
2. **POT jump filter + Hawkes intensity MLE (M).** Fit the bivariate-Hawkes P-dynamics of §2.5 to daily returns: POT thresholds, shifted-exponential jump sizes, partial-likelihood MLE of the intensity parameters. Data: daily OHLCV (`eodhd`/`tiingo`). Value: the jump-intensity state variables that drive every clustered-jump model and the premium estimator. Risk: daily (not intraday) data makes jump identification noisy; intensities must be propagated out of sample (arXiv:2510.21297v1).
3. **Tempered-stable / Variance-Gamma CF pricer (M).** Add the GTS characteristic exponent (§2.4) behind the same Fourier engine; fit to daily S&P returns with a stable optimizer and report Hessian diagnostics. Data: `eodhd` OHLCV + `cboe` chain for validation. Value: nested VG/CGMY/bilateral-Gamma coverage from one implementation. Risk: seven parameters weakly identified from daily data; MLE needs second/third derivatives of a numerically inverted density (arXiv:2304.06060v3).
4. **Jump risk premium estimator (M→L).** Two-stage: P-side from §2, Q-side by fitting $\chi^{+},\chi^{-}$ to one-month implied-vol skews; report the premia series and their regression on realised returns. Data: `cboe` chain + `eodhd` `corporate_actions`. Value: turns the jump model into a signal (the premia explain 14.7–31% of basis variance). Risk: without a futures/funding feed (§3 gaps) only the equity-skew half is replicable (arXiv:2510.21297v1).
5. **Heston-Queue-Hawkes / self-exciting Bermudan pricer (M).** Implement the factorised CF of §2.6 and the discrete-COS variant; use for Bermudan early-exercise analysis. Data: same `cboe` chain. Value: clustering + stochastic volatility at $12.4\times$ the cost of Heston–Hawkes; validates the discretisation of pure-jump laws. Risk: Q-Hawkes is a niche process — needs a clean parameterisation before production use (arXiv:2205.13321v2).
6. **Path-integral SVJD propagator (M).** Add the multiplicative $e^{U(p,T)}$ extension of §2.7 to a Heston/exp-Vasicek propagator, with an MC cross-check. Data: `eodhd` OHLCV + `cboe` chain. Value: cheap jumps for any SV model already in the stack, with an explicit validity region. Risk: the saddle-point approximation fails outside $c>7$, $T<1$ (arXiv:1011.1175v1).
7. **American / barrier Lévy pricing engine (L).** Implement the Volterra integral equation of §2.8 for American puts and the time-Laplace/Wiener–Hopf barrier engine of §2.3, with 7-phase hyper-exponential fitting for VG/NIG. Data: `cboe` chain + `federal_reserve` curve. Value: the corpus's most complete early-exercise and barrier toolbox; semi-analytic and faster than FD/MC. Risk: highest implementation cost (non-local operator, Padé localisation, boundary-region error) (arXiv:2506.18210v3, arXiv:0812.3128v2).
8. **Defer jump models whose inputs are `gap` (—).** Clustered-jump crypto pricing (BTC options/basis), FX jump-diffusion, jump-to-default credit calibration, Lévy term-structure and volatility-derivative pricing all require feeds FinRobot does not serve (crypto, FX, credit/CDS, swaps, variance swaps). Build no scaffolding for these until a provider exists; state the blocker rather than simulating the data (arXiv:2510.21297v1, arXiv:2506.18210v3).

## Appendix — papers read

| arXiv id | title | year |
|---|---|---|
| 2510.21297v1 | Jump risk premia in the presence of clustered jumps | 2025 |
| 2506.18210v3 | American options valuation in time-dependent jump-diffusion models via integral equations and characteristic functions | 2025 |
| 2304.06060v3 | European Option Pricing Under Generalized Tempered Stable Process: Empirical Analysis | 2023 |
| 2205.13321v2 | A new self-exciting jump-diffusion process for option pricing | 2022 |
| 1011.1175v1 | Generalized pricing formulas for stochastic volatility jump diffusion models applied to the exponential Vasicek model | 2010 |
| 0812.3128v2 | A transform approach to compute prices and greeks of barrier options driven by a class of Lévy processes | 2008 |
