# Implied Volatility & Calibration — learnings from the q-fin.PR corpus
`450` of 2274 corpus papers matched this category (`444` with PDFs); this doc is based on a close reading of `6`.

## 1. What the corpus actually offers

- **A model-free representation of any static arbitrage-free smile.** De Marco proves that an arbitrage-free total implied volatility $v$ (fixed maturity, in log-forward-moneyness $k=\log(K/F_T)$) is *always* the harmonic mean of a unique strictly positive function $h$, $v(k)=\left(\tfrac{1}{k}\int_0^k \mathrm{d}y/h(y)\right)^{-1}$ for $k\neq0$ and $v(0)=h(0)$. The strict monotonicity of Fukasawa's maps $f_0,f_1$ is *necessary* for no-butterfly-arbitrage but **not** sufficient, and the positivity of $h$ is likewise necessary but not sufficient (arXiv:2007.03585v1).
- **A change of coordinates turns harmonic means into arithmetic means and exposes the skew rule.** With $z=f_{1/2}(k)=k/v(k)$, the normalized implied volatility satisfies $v_{1/2}(z)=\tfrac{1}{z}\int_0^z h_{1/2}(y)\,\mathrm{d}y$, and any arbitrage-free $v,h$ obey the "1/2-skew rule" $v'(0)=\tfrac12 h'(0)$ (arXiv:2007.03585v1). The short-maturity limit $v_{1/2}(T,z)\to\mathrm{BS}(0,0)$ is a flat constant, so this coordinate is only informative after rescaling by $\sqrt T$ (arXiv:2007.03585v1).
- **Forecasting a smile in risk-neutral parameter space keeps it arbitrage-free.** Dellaportas & Mijatović encode a co-terminal smile in the three SABR parameters $(\alpha,\nu,\rho)$ (plus the forward), model the transformed series $A_t=\log\alpha_t$, $N_t=\log\nu_t$, $R_t=\log\frac{1+\rho_t}{1-\rho_t}$ by ARMA-GARCH with Student-$t$ errors, and map forecasts back. On 1,360 days of USDJPY 1M options (1,000 in-sample, 360 out-of-sample) they beat the random walk for 1–3 days: mean absolute IV error 28 bp at 1 day rising to 65 bp at 3 days, with the gain largest (up to ~4 bp) for out-of-the-money strikes (arXiv:1407.5528v1).
- **Synthetic-surface generation can be arbitrage-free by construction.** Ning et al. calibrate arbitrage-free SDE drivers (a time-varying CTMC regime-switching model, which wins, and Lévy additive processes), embed the fitted parameters with a VAE, and sample surfaces; the CTMC-VAE matches the test distribution as closely as the training set matches it, and **as few as ~3 latent factors** suffice. A conditioning variant driven by the daily VIX (CVAE) beats every unconditional benchmark (arXiv:2108.04941v3).
- **Differential Machine Learning collapses calibration cost.** Training a twin network on Heston normalised-forward-put prices *and* their analytic differentials yields test MSE 0.44 bp, falling to **0.20 bp** with gradient clipping, versus 2.60 bp for a classical feed-forward net; 16,384 samples beat 100,000 for DML. On the full 4,625-quote SPX put surface (Aug-2022), DML reproduces the traditional calibration's parameters exactly while running **61× faster** (20 s vs 20 m 23 s for five parameters; 35× for three) (arXiv:2309.07843v2).
- **VIX and SPX can be jointly calibrated by a continuous model.** Fouque & Saporito's Heston-SVV (stochastic vol-of-vol) admits quasi-closed first-order prices for options on both the stock and the volatility index. Because $VIX_t^2=m(1-\beta)+\beta V_t$, VIX options reduce to CIR payoffs. On 21-Aug-2015 the MSE improves from $9.90\times10^{-4}$ to $3.94\times10^{-5}$ (VIX) and from $1.21\times10^{-3}$ to $7.34\times10^{-6}$ (SPX) versus plain Heston, and the fitted vol-of-vol falls (arXiv:1706.00873v1).
- **The forward variance curve is the rough model's only market input — and it is a closed form.** In rough Bergomi the VIX future is bounded analytically and a log-normal proxy is accurate to $\sim10^{-3}$ for maturities up to ~2 years; the Hurst exponent calibrated on 4-Dec-2015 SPX data is $H\approx0.09$ (published as $H_+=H-\tfrac12$) (arXiv:1701.04260v1).
- **The papers disagree on the right model class.** Markovian continuous models (Heston, SVV) give quasi-closed formulas and joint SPX/VIX fits but structurally cannot reproduce the steep short-maturity smile; rough fractional volatility does reproduce it but its VIX term structure is driven entirely by an initial forward variance curve that must be estimated through eSSVI plus variance-swap replication (arXiv:1701.04260v1), whereas SVV needs only options on both underlyings (arXiv:1706.00873v1). Lévy-additive drivers are dominated by the CTMC on Wasserstein distance (arXiv:2108.04941v3).

## 2. Implementable formulas & algorithms

### 2.1 Implied-volatility inversion and SABR risk-neutral encoding
**Purpose.** Convert an option chain into Black–Scholes implied volatilities and re-encode each co-terminal slice in three arbitrage-free parameters, so that time-series models operate in a space where no-arbitrage holds by construction.

$$BS(F_T,K,T,\sigma)=e^{-r_dT}\left[F_T\,\mathcal{N}(d_+)-K\,\mathcal{N}(d_-)\right],\quad d_\pm=\frac{\log(F_T/K)\pm\sigma^2T/2}{\sigma\sqrt T}$$
$$IV(K,T):\ \text{unique }\sigma>0\ \text{with}\ BS(F_T,K,T,\sigma)=C(K,T)$$
$$IV(K,T)=\frac{\alpha}{(F_TK)^{1/4}}\Big[1+\dots\Big]\frac{z}{x(z)},\qquad z=\frac{\nu}{\alpha}(F_TK)^{1/4}\log\frac{F_T}{K},\quad x(z)=\log\frac{\sqrt{1-2\rho z+z^2}+z-\rho}{1-\rho}$$
Transform to the whole real line: $A_t=\log\alpha_t,\ N_t=\log\nu_t,\ R_t=\log\frac{\rho_t+1}{1-\rho_t}$.

- **Inputs.** A co-terminal option chain (strikes $K_i$, prices $C_i$, expiry $T$), forward $F_T$, discount factor $e^{-r_dT}$.
- **Parameters.** $(\alpha,\nu,\rho)$ per slice, with $\alpha>0,\nu>0,-1<\rho<1$; $\beta=\tfrac12$ fixed.
- **Observed effects.** Parameter-space ARMA-GARCH forecasts beat the random-walk benchmark out to three days; the edge is strongest for OTM strikes (arXiv:1407.5528v1). Vega is strictly positive, so the inversion is well posed when the price lies in the image of $BS$ (arXiv:1407.5528v1).
- **Failure modes.** The closed-form SABR formula is *not* arbitrage-free in extreme wings and bid-ask widens there; in an illiquid, non-contemporaneously recorded market there is no internally consistent smile to invert, so a pricing-kernel estimator is needed first (arXiv:1407.5528v1).

### 2.2 Static no-arbitrage checks via the harmonic-mean representation
**Purpose.** Test and repair a quoted IV slice using a necessary condition that is exactly computable, and re-express it in the $f_{1/2}$ coordinate where the mean becomes arithmetic.

$$v(k)=\Big(\frac{1}{k}\int_0^k\frac{\mathrm{d}y}{h(y)}\Big)^{-1},\qquad h(k)=\Big(\frac{\mathrm{d}}{\mathrm{d}k}\frac{k}{v(k)}\Big)^{-1}$$
Butterfly condition (convexity in $K$): $\ v''(k)+v(k)f_0'(k)f_1'(k)\ge0$, with $f_0=\frac{k}{v}+\frac{v}{2}$, $f_1=\frac{k}{v}-\frac{v}{2}$.
Dupire link: $\ h(T,k)=\dfrac{\sigma_{Dup}(T,k)/\sqrt T}{\sqrt{1+Ta(T,k)+T^2b(T,k)}}$, and $z=f_{1/2}(k)$ gives the arithmetic mean $v_{1/2}(z)=\frac1z\int_0^z h_{1/2}(y)\,\mathrm{d}y$.

- **Inputs.** IV slice $v(k)$ on a strike grid; numerical space derivatives for $v',v''$.
- **Parameters.** None; $h$ is identified uniquely by (8), $h=(k/v)'^{-1}$.
- **Observed effects.** $h>0$ and $f_0,f_1$ increasing are necessary for no-arbitrage; the arithmetic coordinate makes Dupire's small-maturity BBF harmonic-mean formula become an arithmetic-mean formula (arXiv:2007.03585v1).
- **Failure modes.** Positivity of $h$ is not sufficient for no-butterfly (eq. (10) still needs checking); smiles calibrated to real data are often non-convex, so adding convexity is restrictive; rough-volatility short-time limits break the boundedness assumptions on $\sigma_{BS}$ (arXiv:2007.03585v1).

### 2.3 SSVI / eSSVI parameterisation with no-arbitrage constraints
**Purpose.** Fit a whole surface slice with three parameters that carry explicit sufficient no-arbitrage conditions, and read off variance-swap strikes in closed form.

$$w_{SSVI}(k)=\frac{\vartheta}{2}\Big[1+\rho\varphi k+\sqrt{(\varphi k+\rho)^2+1-\rho^2}\Big],\qquad v_{SSVI}=\sqrt{w_{SSVI}}$$
Sufficient no-arbitrage (Gatheral–Jacquier): $\ \varphi(1+|\rho|)\le4$ and $\ \varphi^2(1+|\rho|)\le4$.
eSSVI adds a correlation term structure $\rho(\theta)=(A-C)e^{-B\theta}+C$ with calendar-spread condition $|\partial_\theta(\rho\theta)|\le\dots$ and per-slice $\theta\varphi^2(1+|\rho|)\le4$ (arXiv:1701.04260v1). Fair variance-swap variance:
$$\big(\sigma_0^2\big)_t\;:=\;2\,\mathbb{E}\!\left[\log\frac{S_t}{S_0}\right]=\frac{\hat b_t^2+2a_t(c_t+\vartheta_t)}{2a_t^2}.$$

- **Inputs.** SPX/SPXW option prices across strikes and maturities; ATM variance curve $\theta_t$.
- **Parameters.** $(\vartheta_t,\varphi_t,\rho_t)$, and $(A,B,C)$ for the correlation term structure.
- **Observed effects.** eSSVI fits medium/long maturities well and yields variance-swap term structures that feed the initial forward variance curve $\xi_0(t)=(\sigma_0^2)_t+t\,\partial_t(\sigma_0^2)_t$; the implied $f_{1/2}(z)=\varphi z+\sqrt{\varphi^2z^2+4}$ and $v_{1/2}$ are explicit for SSVI (arXiv:1701.04260v1, arXiv:2007.03585v1).
- **Failure modes.** Short maturities are not fully captured even by eSSVI; the forward variance curve requires interpolation/extrapolation of $\theta_t$ (cubic splines) and can be noisy, corrupting the VIX term structure (arXiv:1701.04260v1).

### 2.4 Wasserstein-regularised SDE calibration with a VAE generator
**Purpose.** Calibrate an arbitrage-free SDE model to a surface *robustly* (regularising sparse data) and then learn the parameter distribution to sample new arbitrage-free surfaces.

$$\hat\theta=\arg\min_\theta\ \big\|C^m-C^d\big\|^2+\lambda\sum_{n=1}^{N}W_1\big(F^{d,(n)},F^{m,(n)}\big),\qquad W_1(F^d,F^m)=\int_{\mathbb R}|F^d(x)-F^m(x)|\,\mathrm{d}x$$
Candidate density from a B-spline of IVs: $f_X(K)=\partial_{KK}C(S_0,K,\sigma(K))$, with $r=0$ and $C=S_0\Phi(d_+)-K\Phi(d_-)$.

- **Inputs.** Historical IV surfaces (Delta × TTM grid $\mathcal D=\{0.1,0.25,0.5,0.75,0.9\}$, $\mathcal M=\{1M,2M,3M,6M,9M,1Y,3Y,5Y\}$).
- **Parameters.** $\lambda$ (Wasserstein weight, 0.01–10 tested), latent dimension (3–15), CTMC regimes $K$ with cyclic transition rates, or Lévy parameters for DE/GM/CGMY.
- **Observed effects.** CTMC-VAE is the best driver; ~3 latent factors suffice; ~350 training days are enough, and *longer* windows degrade the fit because the sample becomes unrepresentative; VIX-conditioned CVAE gives the tightest metric (e.g. CAD-USD $1.67\!\to\!1.26$ at 10 dims vs the empirical floor $1.67$) (arXiv:2108.04941v3).
- **Failure modes.** No convexity guarantee from a B-spline-implied density (used only as a regulariser); Wasserstein distance is the whole evaluation and does not test dynamic consistency; historical-surface overfitting forces frequent retraining (arXiv:2108.04941v3).

### 2.5 Differential-machine-learning Heston calibration
**Purpose.** Replace repeated Monte-Carlo/COS pricing inside the calibration loop with a deterministic, differentiable surrogate so the inverse problem runs in seconds.

Weighted objective: $J(\theta)=\sqrt{\sum_{i,j}w_{i,j}\big(\hat V(\theta,T_i,m_j)-V_{Mkt}(T_i,m_j)\big)^2}$.
Twin-network cost couples values and differentials:
$$C=\frac1m\big(Y-Z^{(L)}\big)^\top\big(Y-Z^{(L)}\big)+\frac{\lambda}{m}\,\mathrm{tr}\!\left[(\dot X-\dot Z^{(0)})(\dot X-\dot Z^{(0)})^\top\right]$$
Normalised forward put (Lipton form, one integral): $\ \hat P_t=1-\frac1\pi\int_0^\infty\mathrm{Re}\!\left[e^{(iu+\frac12)\hat F_{t,T}}\phi_{T-t}(u-\tfrac i2)\frac{\mathrm{d}u}{u^2+\frac14}\right]$, with Heston $\phi$ in the numerically stable Gatheral–Taleb form $A(u)+v_0B(u)$.

- **Inputs.** Synthetic training set (model/option/market params via Latin-hypercube sampling), then a live SPX put table + Treasury curve.
- **Parameters (sampling ranges).** $m\in[-2,2]$, $\tau\in[0.05,20]$, $r\in[-0.01,0.10]$, $\kappa\in[0.005,3]$, $v_0,\theta\in[0,1]$, $\sigma\in[0.1,2]$, $\rho\in[-0.90,0]$; FFNN 4–6 hidden layers × 50 neurons, Softplus forward / Sigmoid adjoint, AdamW, gradient-clip threshold 4.
- **Observed effects.** Test MSE 3.72e-5 for the best net; DML 0.44 bp vs classical 2.60 bp (0.20 bp with clipping); calibration 61× (5-param) and 35× (3-param) faster with *identical* parameters; $\kappa=0.15$ fixed and $v_0\approx\sigma^{ATM\,2}$ gives a good three-parameter reduction (arXiv:2309.07843v2).
- **Failure modes.** The objective is non-convex: 90 DE generations returned the wrong minimum; exploding gradients (norm up to 1,107) inflated test MSE to 674 bp; breaching the Feller condition $2\kappa\theta>\sigma^2$ degrades both pricing and training (arXiv:2309.07843v2).

### 2.6 Heston-SVV joint SPX + VIX calibration
**Purpose.** Fit a continuous model to both the equity smile and the volatility-index smile, which plain Heston cannot do simultaneously.

$$dS_t=(r-q)S_t\,dt+\sqrt{V_t}S_t\,dW^S_t,\qquad dV_t=\kappa(m-V_t)\,dt+\xi(Y^{\varepsilon}_t,Z_t)\sqrt{V_t}\,dV^W_t$$
$$VIX_t^2=\frac{1}{\theta_0}\mathbb E\!\left[\int_t^{t+\theta_0}V_u\,du\,\Big|\,F_t\right]=m(1-\beta)+\beta V_t,\qquad \beta=\frac{1-e^{-\kappa\theta_0}}{\kappa\theta_0},\quad \theta_0=30/360$$
First-order prices: $P^{SVV}_S=P^0_S+P^{\varepsilon}_{1,0}+P^{\delta}_{0,1}$, each a Fourier integral $Re\int_0^\infty e^{ix}G_S\,(1+h_0+vh_1+v^2h_2)\,\hat\varphi\ \mathrm{d}\zeta$ where $G_S=e^{C(\zeta)+vD(\zeta)}$ is Heston and the $h_i$ solve small ODE systems.
Calibration: $\Theta=\arg\min\ \frac{1}{M_S+M_V}\big[\sum_{i=1}^{M_S}(\hat\sigma^i_S-\sigma^i_S)^2+\sum_{i=1}^{M_V}(\hat\sigma^i_V-\sigma^i_V)^2\big]$.

- **Inputs.** SPX and VIX implied-volatility surfaces at one date; futures for the forward via put-call parity.
- **Parameters.** Market group parameters $(\kappa,m,\xi(z),\rho(z),V^\varepsilon_{0,3},V^\varepsilon_{2,1},\dots)$; initialise from standard Heston with the $V^\varepsilon$ terms set to zero.
- **Observed effects.** MSE $9.9\!\times\!10^{-4}\!\to\!3.9\!\times\!10^{-5}$ (VIX) and $1.21\!\times\!10^{-3}\!\to\!7.3\!\times\!10^{-6}$ (SPX); the correction terms are small as assumed; vol-of-vol decreases versus Heston; VIX smile becomes concave (arXiv:1706.00873v1).
- **Failure modes.** Short maturities are excluded (perturbation limit); capturing VIX *term structure* needs time-dependent $m$; many local minima require a Heston initial guess (arXiv:1706.00873v1).

### 2.7 Rough-Bergomi forward variance curve and VIX futures
**Purpose.** Price and calibrate VIX futures from a single SPX smile, using the model's closed-form forward variance dynamics.

$$dX_t=-\tfrac12 V_t\,dt+\sqrt{V_t}\,dW_t,\qquad V_t=\xi_0(t)\,\mathcal E\!\left(2C_H V^H_t\right),\qquad V^H_t=\int_0^t(t-u)^{H-\frac12}dZ_u$$
$$\xi_T(t)=\xi_0(t)\,\mathcal E_T(t)\exp\!\Big[\tfrac12 C_H^2\big((t-T)^{2H}-t^{2H}\big)\Big],\quad C_H=\sqrt{\tfrac{2H\,\Gamma(\frac32-H)}{\Gamma(H+\frac12)\Gamma(2-2H)}}$$
Bounds and log-normal proxy: $\ \mathbb E[\sqrt{\frac{1}{\theta_0}\int_T^{T+\theta_0}\xi_0(t)\,dt}]\ge V_T\ge\dots$, and under log-normal VIX, $V_T=\sqrt{\frac1{\theta_0}\int_T^{T+\theta_0}\xi_0(t)\,dt}\,\exp(\tilde\sigma^2/8)$, with $\tilde\sigma^2=\frac{4\rho^2C_H^2}{H^2}\int_T^{T+\theta_0}[(T-s+\theta_0)^{H_+}-(T-s)^{H_+}]^2\,ds$.

- **Inputs.** SPX bid/ask surface (→ eSSVI → variance-swap strikes → $\xi_0(t)$) and observed VIX futures term structure.
- **Parameters.** Initial forward variance curve $\xi_0(\cdot)$ and $(H,\rho)$; eSSVI shape functions $\varphi(\theta)=\eta\theta^{-\gamma}$, $\rho(\theta)=(A-C)e^{-B\theta}+C$.
- **Observed effects.** The lower (Cauchy–Schwarz) bound is surprisingly tight; the log-normal approximation tracks Monte-Carlo to $\lesssim10^{-3}$ for $T\le2$y and is robust across flat/rising curves; hybrid-scheme and truncated-Cholesky VIX simulations agree (arXiv:1701.04260v1).
- **Failure modes.** VIX term structure depends entirely on $\xi_0$, itself a noisy derived quantity; the log-normal error grows with maturity; calibration error concentrates at short maturities where eSSVI underfits; Monte-Carlo variance grows with $T$ (arXiv:1701.04260v1).

### 2.8 Model-free 30-day variance index from one chain
**Purpose.** Reproduce a VIX-style number directly from a single index option chain — the only volatility-surface quantity that needs *no* extra feed.

$$VIX_t^2\approx\frac{2e^{r\theta_0}}{\theta_0}\sum_i \frac{\Delta K_i}{K_i^2}Q(t,t+\theta_0;K_i)-\frac{1}{\theta_0}\Big(\frac{F}{K_0}-1\Big)^2,\qquad \theta_0=30/360$$

- **Inputs.** OTM call/put quotes for the two nearest expiries straddling 30 days, forward $F$ from put-call parity, risk-free rate $r$.
- **Parameters.** None beyond the strike grid; linear interpolation between the two adjacent maturities.
- **Observed effects.** VIX² is the (discretised) integrated forward variance; under any continuous spot-variance model it equals $m(1-\beta)+\beta V_t$ (arXiv:1706.00873v1, arXiv:1701.04260v1).
- **Failure modes.** Discretisation and strike-truncation error; needs liquid OTM wings; the linear interpolation between expiries is an approximation whose error is not quantified in these papers (arXiv:1706.00873v1).

## 3. Data requirements → available endpoints

| Input | Endpoint | Category | Provider | Probe status |
|---|---|---|---|---|
| SPX option chain (strikes, expiries, prices) for IV inversion | `https://cdn.cboe.com/api/global/delayed_quotes/options/_SPX.json` | options_surface | cboe | ok — delayed quotes |
| Risk-free discount curve for forwards and discounting | `https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2026/all` | risk_free_curve | federal_reserve | ok |
| Index forward / implied carry (via put-call parity) | derived from the SPX chain above | options_surface | cboe | ok |
| Split dates / extra rate points for curve interpolation | `https://api.stlouisfed.org/fred/series/observations` | macro_data | fred | ok |
| Index level / OHLCV for returns and realised-vol context | `https://eodhd.com/api/eod/AAPL` | core_stock_apis | eodhd | ok |
| Dividend / event data for carry and jump-flag proxies | `https://eodhd.com/api/div/AAPL` | corporate_actions | eodhd | ok |
| Option bid/ask and volume for weighting | `https://cdn.cboe.com/api/global/delayed_quotes/options/_SPX.json` | options_surface | cboe | ok — confirm bid/ask fields in payload |
| Historical IV surface panel (for ARMA parameter series / VAE) | gap — no vendor serves IV history; must be archived locally from repeated chain pulls | — | — | gap |
| VIX index level time series (30-day) | gap — no probed endpoint returns `^VIX`; only reproducible from the cboe chain | — | — | gap |
| VIX futures and VIX option quotes | gap — no probed endpoint exposes VIX derivatives | — | — | gap |
| Variance-swap quotes / initial forward variance curve | gap — OTC; must be synthesised from the SPX smile | — | — | gap |
| Realised/intraday returns (RV, vol-swap validation) | gap — no certified intraday series probed | — | — | gap |
| FX option chains (native market of arXiv:1407.5528v1) | gap — no FX option data served | — | — | gap |
| Alternative option chain + expected move (local OpenD) | `moomoo://get_option_chain` | options_data | moomoo | gateway — local OpenD |
| Alternative underlying snapshot (local OpenD) | `moomoo://get_market_snapshot` | core_stock_apis | moomoo | gateway — local OpenD |

## 4. Pitfalls, validation and measurement

- **Necessary ≠ sufficient for no-arbitrage.** Fukasawa monotonicity and $h>0$ are both necessary only; the butterfly condition $v''+vf_0'f_1'\ge0$ must still be enforced, and the closed-form SABR formula is non-arbitrage-free in the extreme wings (arXiv:2007.03585v1, arXiv:1407.5528v1). Check both butterfly (convexity in $K$) and calendar-spread conditions; for eSSVI/SSVI test $\varphi(1+|\rho|)\le4$, $\varphi^2(1+|\rho|)\le4$ and the term-structure inequality (arXiv:1701.04260v1).
- **The inverse problem is ill-posed.** Many parameter sets reproduce market prices; the objective has local minima. Reported evidence: 90 DE generations returned wrong parameters while ~1,000 were needed; identical final parameters only when optimising from a good Heston initial guess (arXiv:2309.07843v2, arXiv:1706.00873v1). Always report the objective and the pricing error, not just "calibrated".
- **Numerical instabilities quietly corrupt results.** Exploding gradients inflated DML test MSE from 0.20 to 674 bp at a gradient norm of 1,107; the second Heston characteristic-function form is used because the original is unstable; the Feller condition $2\kappa\theta>\sigma^2$ must hold or both pricing and learning degrade (arXiv:2309.07843v2).
- **Report which distributional distance you use.** The VAE paper's whole protocol is the 1-Wasserstein distance between generated and test IV-surface distributions, benchmarked against the *training* set distance as a floor (you cannot beat the data's own dispersion); PCA/IV-VAE/empirical baselines are essential context (arXiv:2108.04941v3).
- **Overfitting to a stale surface.** Training windows longer than ~350 days made the generative model historically accurate but unrepresentative of the near future; unconditioned VAEs need added explanatory features, and VIX conditioning markedly improves out-of-sample metric (arXiv:2108.04941v3). Retraining cadence is a first-class parameter.
- **Data cleaning materially changes the fit.** The joint-calibration study removes ITM options, moneyness outside [75%,125%], zero-volume and zero-open-interest quotes, and maturities beyond one year, and infers forwards by put-call parity on ATM options (arXiv:1706.00873v1). Calibration timestamps must be contemporaneous: a single fixing (e.g. London midday) avoids mixing non-synchronous quotes (arXiv:1407.5528v1).
- **Predictive edge decays fast.** The ARMA-GARCH parameter model beats the random walk only out to ~3 days, after which the improvement vanishes; the random walk is itself arbitrage-free and is the mandatory benchmark (arXiv:1407.5528v1).
- **Validate a pricer three ways.** (i) Confirm the Black–Scholes embedding (Heston with $\sigma\to0$, $\theta=v_0$ returns BS; SVV with $V^\varepsilon=0$ returns Heston); (ii) cross-check analytic differentials against finite differences; (iii) compare the log-normal VIX proxy and closed-form bounds against Monte-Carlo with reported standard deviations, noting that MC error and variance grow with maturity (arXiv:2309.07843v2, arXiv:1706.00873v1, arXiv:1701.04260v1).
- **Look-ahead and in-sample leakage.** Do not fit the whole-sample surface then score on it (the VAE/ARMA studies use strict train/test splits of 1,000/360 days or an 80/10/10 split); when forecasting, lag every input and use only past parameters; the co-terminal rolling-expiry structure of index options means "same maturity" is a different contract each day, so align by maturity-to-expiry, not by expiry date (arXiv:1407.5528v1, arXiv:2309.07843v2).
- **Term-structure and wing errors concentrate at short maturity and in the wings.** eSSVI underfits short maturities, which propagates into the VIX futures fit; discretising the VIX integral and interpolating between the two nearest expiries adds unquantified error (arXiv:1701.04260v1, arXiv:1706.00873v1). Weight calibration by liquidity rather than equal weights, and report per-maturity errors.

## 5. Recommended first implementation in FinRobot

1. **(S) IV inversion + static no-arbitrage sanity from the SPX chain.** Invert the `cboe` `options_surface` chain to implied vols with the Treasury `risk_free_curve` for discounting and put-call-parity forwards; flag slices violating butterfly/calendar conditions using the §2.2 harmonic-mean diagnostics. `Data:` cboe chain + Treasury curve (both served). `Value:` unblocks every later item and cleans the input surface; the single served index chain suffices. `Risk:` extreme-wing SABR/quoting noise; delayed quotes (arXiv:1407.5528v1, arXiv:2007.03585v1).
2. **(S) Model-free 30-day variance index (§2.8).** Reproduce a VIX-style number from the same two nearest expiries. `Data:` the cboe chain only. `Value:` immediately supplies a variance-level/term signal and exercises the variance-swap machinery used later, with no extra feed. `Risk:` discretisation/interpolation error; wing liquidity (arXiv:1706.00873v1, arXiv:1701.04260v1).
3. **(M) SSVI/eSSVI slice fit with explicit no-arbitrage constraints (§2.3).** Fit each expiry, enforce $\varphi(1+|\rho|)\le4$ etc., and derive a forward variance curve. `Data:` the SPX chain + risk-free curve. `Value:` gives smooth, arbitrage-controlled surfaces and the forward-variance input needed by rough-vol models, all from served data. `Risk:` short-maturity misfit; forward-curve interpolation noise (arXiv:1701.04260v1).
4. **(M) Heston semi-analytic pricer + calibration (§2.5 pricing side).** Implement the stable characteristic-function Heston pricer and calibrate $\theta,\kappa,\sigma,\rho,v_0$ on the SPX put surface with the Treasury curve, using a good initial guess and the Feller condition. `Data:` the SPX chain + Treasury curve. `Value:` a reusable, differentiable pricing engine (and the equity-side half of joint VIX calibration). `Risk:` non-convex objective, many local minima (arXiv:2309.07843v2).
5. **(M) Risk-neutral parameter-space time-series forecast (§2.1).** Re-encode each co-terminal slice in $(\alpha,\nu,\rho)$-style parameters, model the transformed series by ARMA-GARCH with Student-$t$, and forecast forward, comparing against the random walk. `Data:` requires an archived IV panel (row marked `gap`) built by storing daily chain pulls. `Value:` arbitrage-free smile forecasts with a documented, if short-horizon, edge. `Risk:` predictive power decays by ~3 days; needs a local historical archive (arXiv:1407.5528v1).
6. **(M→L) Joint SPX + VIX calibration via Heston-SVV (§2.6).** Add the stochastic vol-of-vol correction and calibrate on both smiles; VIX options reduce to CIR payoffs. `Data:` SPX chain (served) plus VIX surface (row marked `gap` — synthesise a proxy VIX smile from the SPX chain or defer the VIX leg). `Value:` a continuous model that fits both, unlike plain Heston. `Risk:` VIX option data is unserved, so only the model-free VIX index leg is available today (arXiv:1706.00873v1).
7. **(L) Differential-ML calibration accelerator (§2.5).** Train a twin network on synthetic Heston prices+gradients to cut calibration to seconds, then reuse across symbols. `Data:` no new endpoint (synthetic training); market calibration uses the same SPX chain. `Value:` 35–61× speed-up with identical parameters. `Risk:` needs gradient-clipping and a synthetic-data pipeline; only worth it once the classical calibrator exists (arXiv:2309.07843v2).
8. **(L) VAE/CVAE arbitrage-free surface generator (§2.4).** Learn the SDE-parameter distribution from a historical surface panel and sample synthetic arbitrage-free surfaces, unconditionally and conditioned on a VIX-style index. `Data:` the archived IV panel (`gap` row) plus the model-free index from item 2. `Value:` risk-neutral scenario surfaces for downside analysis. `Risk:` historical-surface overfitting and frequent retraining; the payoff is diagnostic rather than directly tradable (arXiv:2108.04941v3).
9. **(L) Rough-Bergomi VIX futures module (§2.7).** Calibrate $H,\rho$ to observed VIX futures from the eSSVI-implied forward variance curve, with the analytic bounds and log-normal proxy as a fast pricer. `Data:` requires VIX futures and a variance-swap term structure (both `gap` rows) — blocked until such a feed exists; only the bounds/proxy on a synthesised curve can be built today. `Value:` adds rough short-maturity dynamics and a VIX term structure. `Risk:` depends entirely on an unserved forward variance input (arXiv:1701.04260v1).

## Appendix — papers read

| arXiv id | title | year |
|---|---|---|
| 2309.07843v2 | Applying Deep Learning to Calibrate Stochastic Volatility Models | 2023 |
| 2108.04941v3 | Arbitrage-Free Implied Volatility Surface Generation with Variational Autoencoders | 2021 |
| 2007.03585v1 | On the harmonic mean representation of the implied volatility | 2020 |
| 1706.00873v1 | Heston Stochastic Vol-of-Vol Model for Joint Calibration of VIX and S&P 500 Options | 2017 |
| 1701.04260v1 | On VIX Futures in the rough Bergomi model | 2017 |
| 1407.5528v1 | Arbitrage-free prediction of the implied volatility smile | 2014 |
