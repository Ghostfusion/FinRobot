# Order Flow & Hawkes Processes — learnings from the q-fin.TR corpus

`303` of 2370 corpus papers matched this category (302 with PDFs); this doc is based on a close reading of `6`.

Headline: **this category is about the *estimation and calibration* of self-exciting order-flow
models, not about execution.** The six papers split cleanly into (a) statistical models of the order
flow that can be fitted to a tape — queue-reactive Hawkes (arXiv:1901.08938), flexible-residual
durations (arXiv:2604.00346), non-parametric kernel estimation (arXiv:2006.02460), a marked-Hawkes
LOB simulator with time-rescaling diagnostics (arXiv:2510.08085) — and (b) two theory papers that
explain *why* Hawkes order flow produces power-law intensities (arXiv:2102.00242) and rough
volatility (arXiv:2608.07709). Nothing here is buildable end-to-end on FinRobot's current data
layer: every estimator needs event-level timestamps, and the state-dependent and multivariate
variants additionally need a signed trade tape and best-level queue sizes. The one exception is a
*simulation-side* stack (arXiv:2510.08085) that is self-contained.
[`../qfin-st/microstructure-execution.md`](../qfin-st/microstructure-execution.md) covers impact,
fills and microprice from the q-fin.ST corpus; this doc specialises on the point-process
machinery, so the overlap is limited to shared data gaps and to the
[`../qfin-st/econometrics-forecasting.md`](../qfin-st/econometrics-forecasting.md) treatment of
high-frequency volatility.

## 1. What the corpus actually offers

- **A queue-reactive Hawkes (QRH) model that beats both of its nested restrictions, decisively.**
  Adding a Hawkes term to the Huang–Lehalle–Rosenbaum queue-reactive baseline raises the
  log-likelihood by \\(\Delta\mathcal L = 3.7\times10^{8}\\) on Bund and \\(1.8\times10^{7}\\) on
  DAX (27 extra parameters, likelihood-ratio \\(p<10^{-16}\\)); the two-sided QRH-II variant beats a
  pure 8-dimensional Hawkes model by \\(\Delta\mathcal L = 2.9\times10^{7}\\) (Bund) and
  \\(2.8\times10^{7}\\) (DAX) on 200 extra parameters (arXiv:1901.08938).
- **Order-flow endogeneity is the dominant term, and it is queue-state dependent.** The
  self/cross-exciting mechanism explains **60–80%** of the average intensity \\(e^{\ell}(q)\\)
  across all order types and both assets; the endogeneity is *largest at small queues* for cancel
  and market orders and *largest at large queues* for limit orders (arXiv:1901.08938).
- **Kernel norms are asymmetric and confirm adverse-selection logic.** Same-side kernel norm
  matrices (rows = target intensity \\(L,C,M\\), columns = triggering event) reach \\(\approx0.60\\)
  on the diagonal (self-excitation, order splitting) and market orders excite cancellations much
  more than the reverse (arXiv:1901.08938).
- **Two assets, opposite tick regimes.** Eurex Bund is a large-tick asset (average spread
  \\(1.012\\) ticks, median \\(1.0\\); average realization length \\(\bar m\approx100\\) s) and DAX a
  small-tick asset (average spread \\(1.591\\), median \\(2.0\\); \\(\bar m\approx16\\) s). The QR
  invariant distribution fits Bund poorly and QRH-I fixes it; for DAX the gap is small
  (arXiv:1901.08938).
- **One-tick mid-price durations are violently over-dispersed and non-exponential.** AAPL, Dec
  2022: 1,023,480 durations, mean \\(0.4801\\) s, median \\(0.1281\\) s, SD \\(0.9937\\) s, skewness
  \\(5.7536\\), kurtosis \\(61.4619\\), over-dispersion SD/mean \\(=2.0698\\) (arXiv:2604.00346).
- **Wrong residual family inflates every structural parameter by ~an order of magnitude.** SE-Exp
  (exponential residuals) estimates \\(\hat\mu=1.4768,\hat\alpha=90.96,\hat\beta=285.9\\), whereas
  SE-Gamma estimates \\(\hat\mu=0.2712,\hat\alpha=0.0939,\hat\beta=0.1068\\) with
  \\(\hat\kappa=0.3511\\); the exponential fit's KS residual statistic is \\(0.1381\\) vs \\(0.0507\\)
  (arXiv:2604.00346).
- **Point-forecast skill is weak even when distributional fit is good.** Best out-of-sample
  \\(R^2\\) across 14 model/residual combinations is \\(0.1382\\) (ACD-Gamma); SE-Burr wins on
  rRMSE (\\(1.8033\\)) but *loses* on LRMSE (\\(2.9127\\) vs \\(2.8629\\) for log-ACD-Exp) — the
  metric choice flips the ranking (arXiv:2604.00346).
- **A shallow neural network recovers arbitrary kernels and is competitive, but its branching
  ratio can come out supercritical.** On 83,574 Binance BTC market orders (8 May 2020, 4h10m), SNH
  NLL is \\(-40143\\) vs EM \\(-33127\\) and Wiener–Hopf \\(-29698\\), yet its estimated branching
  ratio is \\(\rho_2=1.173>1\\) (EM: \\(0.685\\); WH: \\(0.272\\)) — a fit that is not stationary
  (arXiv:2006.02460).
- **Self-excitation is essential and Poisson/queue-reactive baselines are decisively rejected.**
  On 12.5M Binance BTCUSDT trades (Jan 2024) exponential Hawkes gives NLL \\(0.817\\), KS
  \\(0.038\\), ACF(1) \\(0.419\\), AIC \\(1634.2\\); Poisson gives NLL \\(1.425\\), KS \\(0.312\\),
  ACF(1) \\(0.011\\), AIC \\(2850.7\\), and queue-reactive gives NLL \\(1.146\\), KS \\(0.697\\),
  AIC \\(2292.4\\) (arXiv:2510.08085).
- **The realistic regime is nearly unstable.** BTCUSDT branching ratio \\(\hat n=0.799\\)
  (exp) / \\(0.812\\) (power-law), decay \\(\hat\beta=2.321\\), memory timescale \\(1/\beta\approx0.43\\)
  s, mean intensity \\(\bar\lambda=20.53\\) trades/s (arXiv:2510.08085).
- **Power-law intensity tails are a generic consequence of nonlinearity, not a parameter choice.**
  For a nonlinear Hawkes intensity \\(\lambda=g(\tau)\\) with \\(\tau=\sum_i y_i h(t-t_i)\\),
  \\(g\\) fast-accelerating, and two-sided marks with \\(E[y]\le0\\): \\(P_{ss}(\lambda)\propto
  \lambda^{-2-c/h(0)}\\), with Zipf's law \\(P_{ss}\propto\lambda^{-2}\\) exactly when
  \\(E[y]=0\\), and \\(a=c/h(0)=2m/(\sigma^2h(0))\\) for Gaussian marks (arXiv:2102.00242).
- **Rough volatility has an explicit microstructural map.** A nearly unstable heavy-tailed Hawkes
  flow with \\(1-a_T\sim\mu_0T^{-\alpha}\\), kernel \\(\phi(t)=\alpha(1+t)^{-1-\alpha}\\),
  \\(\alpha\in(1/2,1)\\), converges to the rough Hawkes–Heston variance with drift
  \\(b=\bar\xi\!\int z\nu_J(dz)-\mu_0/\Gamma(1-\alpha)<0\\) and leverage
  \\(\rho=-\sqrt{(\beta-1)q/((1+q)(1+\beta^2q))}\\); the terminal Wasserstein-1 distance between
  the finite-\\(T\\) variance proxy and its limit falls from \\(2.37\times10^{-2}\\) (\\(T=2\\)) to
  \\(3.09\times10^{-3}\\) (\\(T=50\\)) (arXiv:2608.07709).
- **Category-boundary note.** All six papers list `q-fin.TR` in their `categories`, but only two are
  primary `q-fin.TR` (arXiv:1901.08938, arXiv:2510.08085). arXiv:2604.00346 is primary `q-fin.ST`,
  arXiv:2102.00242 primary `cond-mat.stat-mech`, arXiv:2006.02460 primary `stat.ML`, and
  arXiv:2608.07709 primary `q-fin.MF`. None is off-topic: each supplies either an estimator or the
  theoretical reason the estimator works. arXiv:2102.00242 is the furthest from implementable
  trading (it is simulation-only) but is retained because it gives the only *diagnostic* for
  intensity-tail heaviness in the set.

## 2. Implementable formulas & algorithms

### 2.1 Queue-reactive Hawkes intensity (QRH-I / QRH-II)
**Purpose.** Model order-arrival intensities at the best bid/ask as a function of *both* the current
queue state and the past order flow, so that a simulator reproduces the empirical inter-event and
queue-size distributions.

**Formula.** For event types \\(\ell,m\in\{L,M,C\}\\),
$$\lambda^\ell(t)=\phi^\ell\big(q(t)\big)+\sum_m\int_0^t \varphi^{\ell m}(t-s)\,dN_s^m,$$
with exponential-sum kernels \\(\varphi^{\ell m}(t)=\sum_{u=1}^{U}\omega_u^{\ell m}\beta_u e^{-\beta_u t}\\)
and queue size \\(q(t)=q(0)+N^L_t-N^M_t-N^C_t\\) (market and cancel intensities are set to 0 at
\\(q=0\\)). The two-sided QRH-II model makes both the baseline and the Hawkes part share one
multiplicative state factor,
$$\lambda^\ell(t)=f^\ell(q_a(t),q_b(t))\Big(\mu^\ell+\sum_m\int_0^t\varphi^{\ell m}(t-s)\,dN_s^m\Big),\qquad
f^\ell(q_a^1,q_b^1)=1,$$
over the 8 event types \\(\{P^+,P^-,L^a,L^b,C^a,C^b,M^a,M^b\}\\). Log-likelihood is convex in
\\((\mu,\omega)\\) because of the exponential-sum parametrisation.

**Required inputs.** Tick-by-tick best-level events with a timestamp (microsecond precision) and an
order-type label (limit / cancel / market) — the paper uses snapshots where every trade line lets the
type be identified; plus best bid/ask prices and outstanding sizes. Average event size (AES) to
normalise \\(q(t)=v(t)/\mathrm{AES}\\) (ceiling).

**Parameters & defaults.** \\(U=3\\) exponential decays: \\(\beta^{-1}\in\{60,1500,5500\}\\) s (Bund),
\\(\{40,2100,5200\}\\) s (DAX). Restrict to periods where the reference price \\(p_{ref}\\) is
constant and keep realizations with \\(\ge20\\) events. QRH-II discretises the state into bid/ask
quintiles to bound the number of configurations. Fit by MLE (gradient recursion) or least squares
when the state space grows.

**Observed effect sizes.** Bund 1,207,099 price-plateau periods, DAX 417,581. QRH-I has 477
parameters on Bund vs 75 for QR; QRH-II 400 vs 200 for pure Hawkes. Endogenous fraction
\\(e^\ell(q)=1-\mu^\ell(q)/\bar\lambda^\ell(q)\in[60\%,80\%]\\). Queue autocorrelation decay time
\\(\tau_c\approx15\\) s (Bund) and \\(2\\) s (DAX), both below the mean realization length
\\(\bar m\\), which validates using the invariant distribution for random-time snapshots.

**Failure modes.** The model resets Hawkes memory at every reference-price change, discarding the
cross-side dynamics the paper later fixes in QRH-II; the invariant distribution is biased at small
\\(q\\) because empirical samples stop when the queue empties; large-tick (Bund) and small-tick (DAX)
assets need different state granularity. Any of these breaks a naive port.

### 2.2 Self-exciting flexible-residual duration process
**Purpose.** Forecast the time to the next one-tick mid-price move while keeping the Hawkes
self-exciting/decay structure *and* matching the heavy-tailed duration distribution.

**Formula.** With i.i.d. innovations \\(\varepsilon_n\\) and integrated-intensity transform
\\(\Phi\\),
$$\Lambda_n=\mu+(\Lambda_{n-1}-\mu+\alpha)e^{-\beta\tau_n},\qquad
\Phi(t,x)=\mu t+(x-\mu+\alpha)\frac{1-e^{-\beta t}}{\beta},\qquad
\tau_n=\Phi^{-1}(\varepsilon_n,\Lambda_{n-1}),$$
which linearises to \\(\Lambda_n=\Lambda_{n-1}+\alpha-\beta\varepsilon_n+\beta\mu\tau_n\\). The
conditional intensity is \\(\lambda_{n-1}(t)=h_\varepsilon(\Phi(t,\Lambda_{n-1}))\Psi(t,\Lambda_{n-1})\\),
and the per-observation log-likelihood is
$$\ell_n(\theta)=\log f_\varepsilon\!\big(\Phi(\tau_n,X_{n-1})\big)+\log\Psi(\tau_n,X_{n-1}).$$
Under stationarity \\(E[\tau_n]=(\beta\mu_\varepsilon-\alpha)/(\beta\mu)\\). ACD(1,1) and
log-ACD(1,1) are the special cases \\(\Phi(t,x)=t/x\\) and \\(\Phi(t,x)=xt\\) respectively.

**Required inputs.** A point process of event times — here the timestamps of successive one-tick
mid-price moves (two consecutive same-direction half-tick mid changes, since the mid moves by half a
tick when one side moves a tick).

**Parameters & defaults.** Stability \\(\alpha<\beta\mu_\varepsilon\\) with \\(\mu_\varepsilon=E[\varepsilon]<\infty\\).
Residuals all rescaled to \\(E[\varepsilon]=1\\): Gamma (shape \\(\kappa\\), scale \\(1/\kappa\\)),
generalised Gamma (\\(d,p\\)), or Burr XII (\\(s_1,s_2,c\\)), with \\(c=s_1B(s_1-1/s_2,1+1/s_2)^{-1}\\).
Rolling window of the most recent 5,000 events (\\(\approx45\\) min) re-estimated each step, forecast
the next 100; evaluate \\(E[\tau_n\mid\mathcal F_{n-1}]\\) by one-dimensional numerical integration.

**Observed effect sizes.** AAPL Dec 2022. Fitted shape \\(\hat\kappa=0.3511\\), gGamma
\\((\hat d,\hat p)=(0.3340,1.2501)\\), Burr \\((\hat s_1,\hat s_2)=(273.95,0.4765)\\). SE-Exp vs
SE-Gamma parameter inflation as in §1. Out-of-sample KS: SE-Gamma 0.0507, ACD-Gamma 0.0236,
log-ACD-gGamma 0.0186, SE-Exp 0.1381. SE-Burr best rRMSE 1.8033 and \\(R^2=0.1134\\).

**Failure modes.** Non-exponential kernels destroy the finite-state Markov property, so only the
exponential \\(\Psi\\) admits the elapsed-time representation; ACD-type updates are near unit root
(\\(a+b_1\approx0.95\\)); forecasting point accuracy is weak everywhere (\\(R^2\le0.14\\)) — use the
intensity as a *timing/burst* feature, never as a direction signal; de-seasonalise or use the rolling
window, since intraday U-shape is strong (shortest durations at open and close).

### 2.3 Shallow Neural Hawkes: non-parametric kernel estimation
**Purpose.** Estimate the excitation kernel \\(\phi_{dj}(\cdot)\\) of a \\(D\\)-dimensional Hawkes
process without assuming exponential or power-law shape, while keeping interpretability and a closed
form for the time integral.

**Formula.** Each kernel is a one-hidden-layer network with output through an exponential,
$$\hat\phi_{dj}(x)=\exp\Big(b_2+\sum_{i=1}^{p}w_i\max(u_i x+b_{1i},0)\Big),$$
i.e. \\(\exp\\) of a sum of ReLUs (\\(3p+1\\) parameters per kernel, \\(D^2\\) networks). The
integrated kernel has a closed form (piecewise, between sorted inflection points \\(s_i=-b_{1i}/u_i\\)),
so SGD uses the unbiased gradient estimator
$$\widehat{\nabla\mathcal L}=\sum_{(t_n,d_n)\in S}\nabla_\theta\log\lambda_{d_n}(t_n)-\sum_{d=1}^D\sum_{t_n^d<T}\int_0^{t_n^d}\sum_{j=1}^D\nabla_\theta\phi_{jd}(s)\,ds,$$
where \\(t_n^-\\) is the previous event time in the same node.

**Required inputs.** A sequence of \\((t_n,d_n)\\) event times and node labels — for finance,
signed market orders (buy/sell nodes). No mark/volume information is used.

**Parameters & defaults.** \\(p=100\\) neurons; weights initialised \\(\mathcal U[0,0.5]\\), inner-layer
weights positive and outer-layer negative for faster convergence; ADAM with outer-layer lr
\\(10^{-2}\\), inner-layer lr \\(10^{-5}\\), baseline lr \\(10^{-3}\\); batch size 50; 30 epochs (100
for random kernels). For non-smooth (rectangular) kernels raise the inner lr to \\(5\times10^{-4}\\)
and use 32–128 neurons.

**Observed effect sizes.** Synthetic: exponential kernel \\([\mu,\alpha,\beta]=[1,4,0.05]\\), 3,972
events in \\([0,60000)\\); power law 4,442 events; rectangular 10,196 events — SNH has the lowest
\\(L_1\\) kernel error in all three. Real BTC: NLL \\(-40143\\) vs EM \\(-33127\\), WH \\(-29698\\); 5-fold
time-series CV NLL 21,963.31 (SNH) vs 19,853.86 (EM), 147,752.28 (WH). Estimated kernels show
*self*-excitation but negligible *mutual* excitation between buy and sell market orders.

**Failure modes.** WH/EM are grid- or bin-dependent, so their comparison is not assumption-free;
the model is non-convex and only reaches a good local optimum (baselines are fixed, kernels
positive); the estimated branching ratio must be checked — the Bitcoin fit returns
\\(\rho_2=1.173>1\\), a supercritical (non-stationary) estimate that must be rejected or regularised.

### 2.4 Nonlinear-Hawkes power-law intensity diagnostic
**Purpose.** Decide whether an observed intensity distribution has a genuine power-law tail, and
read off the tail exponent as a reflexivity/endogeneity measure — a cheaper alternative to fitting a
full branching structure.

**Formula.** With tension \\(\tau(t)=\sum_{i=1}^{N(t)}y_i h(t-t_i)\\), mark density \\(\pi(y)\\),
and intensity \\(\lambda(t)=g(\tau(t))\\),
$$P_{ss}(\lambda)\propto \frac{1}{g'(\lambda)}\exp\!\Big(-\frac{c\,\tau(\lambda)}{h(0)}\Big),$$
where \\(c\ge0\\) is the non-negative root of \\(\Psi(x)=\int\pi(y)(e^{xy}-1)dy\\). Consequences:
\\(g(\tau)=\lambda_0 e^{\gamma\tau}\Rightarrow P_{ss}(\lambda)\propto\lambda^{-2-c/h(0)}\\);
\\(g(\tau)=\lambda_0+\lambda_1\tau^n\ (n>2)\Rightarrow P_{ss}(\lambda)\propto\lambda^{-(2+1/n)}\\);
zero-mean marks give Zipf \\(P_{ss}(\lambda)\propto\lambda^{-2}\\), and Gaussian marks give
\\(a=c/h(0)=2m/(\sigma^2 h(0))\\). The same exponent carries to event counts in short windows,
\\(P_{ss}(N_{t_{\rm win}})\propto N_{t_{\rm win}}^{-2}\\), up to a cutoff \\(N_{\rm cut}=O(\epsilon^{-2})\\).

**Required inputs.** A long event-time series; estimates of the intensity (e.g. kernel-smoothed
event rate) and a mark series (signed price moves or trade sizes) to check the \\(E[y]\le0\\) condition.

**Parameters & defaults.** Simulation uses \\(g(\tau)=\lambda_0 e^{\tau}\\), \\(\lambda_0=1\\),
\\(h(t)=\sum_k \tilde h_k e^{-t/\theta_k}\\) with \\((\theta_1,\theta_2,\theta_3)=(1,0.5,2)\\),
\\((\tilde h_1,\tilde h_2,\tilde h_3)=(0.5,0.6,0.1)\\), \\(K=3\\), Gaussian marks \\(\sigma=0.1\\);
\\(T=5\times10^4\\) (Zipf figure) to \\(5\times10^6\\); intensity capped at \\(\lambda_{\max}=10^7\\)
for rounding control.

**Observed effect sizes.** Zipf \\(P_{ss}(\lambda)\propto\lambda^{-2}\\) for \\(m=0\\); negative mean
\\(m<0\\) gives \\(P_{ss}(\lambda)\propto\lambda^{-2-a}\\) with the numerical exponents
\\(a=0.5,1,1.5\\) reproduced (arXiv:2102.00242).

**Failure modes.** The universality needs (i) \\(g\\) faster than any quadratic, (ii) two-sided marks
with non-positive mean, (iii) fast-decaying mark tails — a fat-tailed mark law is *excluded*, and
\\(m>0\\) makes the solution explosive. It is a theoretical diagnostic, not a calibrated trading
model; do not fit \\(P_{ss}\\) and claim a mechanism without checking the mark-mean condition.

### 2.5 Marked-Hawkes LOB simulator with time-rescaling goodness-of-fit
**Purpose.** Generate synthetic order flow that reproduces clustering, long memory and heavy tails,
drive a deterministic price-time-priority matching engine, and *test* the calibration with a
distribution-free GOF statistic.

**Formula.** Marked linear Hawkes intensity
$$\lambda_i^*(t)=\mu_i+\sum_{j=1}^{d}\sum_{k:T_k^{(j)}<t}\varphi_{ij}(t-T_k^{(j)},V_k^{(j)}),\qquad \varphi_{ij}(u,v)=v\,\phi_{ij}(u),$$
with excitation matrix \\(G_{ij}=m_j\int_0^\infty\phi_{ij}(u)du\\). Stability: \\(\rho(G)<1\\) gives a
unique stationary, geometrically ergodic process with \\(\bar\Lambda=(I-G)^{-1}\mu\\); for Lipschitz
nonlinearities \\(\psi_i\\) the condition becomes \\(\rho(LG)<1\\) with \\(L=\mathrm{diag}(\mathrm{Lip}(\psi_i))\\).
Simulate by thinning (accept with prob. \\(\lambda^*/\bar\lambda\\)) or exact immigration–birth. GOF:
the time-rescaled residuals \\(\tau_k=\Lambda(T_k)-\Lambda(T_{k-1})\\) are i.i.d. Exp(1) *iff* the
model is correct; equivalently \\(U_k=1-e^{-\tau_k}\sim\mathcal U(0,1)\\), checked by KS/Cramér–von
Mises on the PIT CDF and by ACF of \\(\{\tau_k\}\).

**Required inputs.** Trade timestamps with a buy/sell side and a volume mark; for the LOB engine,
the event type (submission/cancel/partial or full execution/hidden execution). Binance data was
aggregated in 100 ms windows with log-normal marks; LOBSTER gave 5 event types and 10 book levels.

**Parameters & defaults.** Exponential kernel MLE is \\(O(n)\\) via the recursion
\\(R(t_{i+1})=e^{-\beta(t_{i+1}-t_i)}(1+R(t_i))\\), \\(\lambda^*(t_i)=\mu+\alpha R(t_i)\\). Compare
Hawkes-Exp, Hawkes-PL, Hawkes-Exp-Det (deterministic mean marks), Poisson and Queue-Reactive.
80/20 train/test plus 5-fold CV; fixed seeds.

**Observed effect sizes.** BTCUSDT (12.5M trades, Jan 2024): Hawkes-Exp \\(\hat\mu=4.127\\),
\\(\hat\alpha=1.854\\), \\(\hat\beta=2.321\\), \\(\hat n=0.799\\), NLL 0.817, KS 0.038, AIC 1634.2;
Hawkes-PL \\(\hat n=0.812\\), NLL 0.842, KS 0.056; Poisson KS 0.312, ACF(1) 0.011; Queue-Reactive
KS 0.697. Synthetic MLE check: true \\((0.5,1.2,1.5)\\) → \\((0.487,1.234,1.512)\\), bootstrap SEs
\\((0.031,0.098,0.121)\\). LOBSTER AAPL: \\(\hat n=0.82\\), \\(\hat\mu=0.15\\), NLL 1.37, KS 0.41.

**Failure modes.** The Hawkes intensity does not condition on current depth/spread/imbalance, so it
misses what queue-reactive models capture; stationarity ignores intraday seasonality and regime
change; power-law kernels are hard to calibrate and sensitive to initialisation; a correct
time-rescaling test only says the *chosen* model fits — it does not select between two well-fitting
models.

### 2.6 Nearly unstable heavy-tailed Hawkes → rough Volterra limit
**Purpose.** Justify using a rough-volatility (rough Heston) variance process by deriving it as the
macroscopic limit of a microscopic order-flow model, and read the reduced-form coefficients off the
microstructure.

**Formula.** Take \\(\phi(t)=\alpha(1+t)^{-1-\alpha}\\), \\(1-a_T\sim\mu_0T^{-\alpha}\\),
\\(p_T=(1-a_T)^2\bar p_T\\), \\(r_T\sim r_\star/(1-a_T)\\). The near-critical resolvent
\\(\Psi_T=\sum_{k\ge1}(a_T\phi)^{*k}\\) scales to the Mittag–Leffler kernel
$$T^{1-\alpha}\Psi_T(Tu)\to K(u),\qquad \hat K(\lambda)=\frac{1}{\mu_0+\Gamma(1-\alpha)\lambda^{\alpha}},$$
which in Riemann–Liouville form gives \\(k_\alpha(t)=t^{\alpha-1}/\Gamma(\alpha)\\) and the variance
equation
$$V_t=G_0(t)+b\int_0^t k_\alpha(t-s)V_s\,ds+\bar c_B\int_0^t k_\alpha(t-s)\sqrt{V_s}\,dB_s
+\bar\xi\int_0^t\!\!\int_{(0,\infty)} k_\alpha(t-s)\,z\,\tilde\mu(ds,dz).$$
The coefficient map is
$$\nu_J(dz)=2\kappa F_J(dz),\quad \kappa=\frac{\bar p\,m_\star\mu_0}{\theta},\quad
\xi=\frac{\theta c_J r_\star}{m_\star},\quad \bar\xi=\frac{\xi}{\Gamma(1-\alpha)},$$
$$\bar c_B=\frac{c_B}{\Gamma(1-\alpha)^2},\quad
c_B=\frac{\theta\mu_0(\omega_++\beta^2\omega_-)}{m_\star(\omega_++\beta\omega_-)^2},\quad
b=\bar\xi\!\int_{(0,\infty)} z\,\nu_J(dz)-\frac{\mu_0}{\Gamma(1-\alpha)}<0,\quad
\rho=-\sqrt{\frac{(\beta-1)q}{(1+q)(1+\beta^2q)}}.$$

**Required inputs.** Only microscopic order-flow primitives — sign-specific arrival weights
\\(\omega_\pm\\), tick-size ratio \\(q\\), variance-loading asymmetry \\(\beta>1\\), immigration rate
\\(\hat h^T\\) — plus a target reduced-form tuple to invert. No market data is needed for the map
itself; the Bondi et al. calibration is used to illustrate it.

**Parameters & defaults.** \\(\alpha\in(1/2,1)\\) (roughness), \\(\mu_0>0\\) (critical gap), rare-mark
probability \\(p_T\\) with \\(p_T\asymp T^{-2\alpha}\\), amplification \\(r_T\asymp T^{\alpha}\\);
subcriticality \\(2c_Jr_\star \bar p m_1<1\Leftrightarrow \bar\xi\!\int z\nu_J(dz)<\mu_0\\).
Numerical illustration: \\(\alpha=0.65\\), \\(\mu_0=\bar p=m_\star=1\\), \\(\theta=0.2\\),
\\(c_J=0.4\\), \\(r_\star=1.25\\), \\(F_J=\mathrm{Exp}(2)\\), \\(q=0.5\\), \\(\beta=3\\), \\(g_0=0.04\\).
Bondi et al. reduced form: \\(\alpha=0.527\\), \\(\rho=-0.731\\), \\(b=-1.812\\), \\(\bar c_B=0.115\\),
\\(\Lambda=0.276\\), \\(G_0(t)=0.0079+0.049t^{\alpha}/\Gamma(\alpha+1)\\); inverted microscopic instance
\\((\mu_0,\bar p,c_J,r_\star,\theta,m_\star,\beta,q,F_J)=(5.2653,0.006772,1,26.2566,0.07131,1,8,0.041605,\mathrm{Exp}(1))\\).

**Observed effect sizes.** Terminal Wasserstein-1 distance between \\(V_1^T\\) and \\(\sigma_1^2\\):
\\(2.37\times10^{-2}\\) at \\(T=2\\) → \\(3.09\times10^{-3}\\) at \\(T=50\\); integrated variance
\\(1.20\times10^{-2}\to7.63\times10^{-4}\\) (100,000 exact-cluster paths per \\(T\\)).

**Failure modes.** The coefficient map is non-identifiable: \\(\theta/m_\star\\), \\(c_Jr_\star\\),
and \\(\Lambda/\bar\xi\\) are only identified as ratios/products, so a fitted reduced form does not
pin down a unique microstructure. The construction *requires* subcriticality to force \\(b<0\\); and
the baseline curve must lie in the realizable set \\(\mathcal G_{\mu_0}\\) — a free choice of
\\(G_0\\) may not be attainable.

## 3. Data requirements → available endpoints

Provider rows below are real entries in `strategies/endpoints.json`; **gap** means no current
provider can supply the input.

| Input | Endpoint | Category | Provider | Probe status |
|---|---|---|---|---|
| Daily OHLCV (baseline / realized-vol scale for the limit map) | `https://eodhd.com/api/eod/AAPL` | `core_stock_apis` | eodhd | ok |
| Daily OHLCV (secondary) | `https://api.tiingo.com/tiingo/daily/AAPL/prices` | `core_stock_apis` | tiingo | ok |
| Previous aggregate bar | `https://api.massive.com/v2/aggs/ticker/AAPL/prev` | `core_stock_apis` | massive | ok |
| Intraday minute bars (coarsest duration proxy) | `https://api.twelvedata.com/time_series` | `core_stock_apis` | twelvedata | ok |
| Intraday K-line via local gateway | `moomoo://get_cur_kline` | `technical_indicators` | moomoo | gateway (not live-probed) |
| Top-of-book snapshot (best bid/ask only) | `moomoo://get_market_snapshot` | `core_stock_apis` | moomoo | gateway (not live-probed) |
| Daily capital flow (coarse signed-flow proxy) | `moomoo://get_capital_flow` | `capital_flow` | moomoo | gateway (not live-probed) |
| Tradable symbol universe / tick sizes | `https://eodhd.com/api/exchange-symbol-list/US` | `exchange_symbols` | eodhd | ok |
| **Event-level trade timestamps (µs/ns)** | — | — | — | **gap** |
| **Signed trade tape with aggressor flag (buy/sell)** | — | — | — | **gap** |
| **Best-level queue sizes \\(q_a,q_b\\) (for QRH)** | — | — | — | **gap** |
| **Order-type labels (limit / cancel / market) at price level** | — | — | — | **gap** |
| **L3 market-by-order stream (LOBSTER / ITCH / DBN)** | — | — | — | **gap** |
| **Intraday \\(T\\)-horizon option surface (for rough-Heston inversion)** | `https://cdn.cboe.com/api/global/delayed_quotes/options/_SPX.json` | `options_surface` | cboe | ok |

**What the gap costs, quantified.** Every estimator here is defined on a *point process*, so the
missing object is a single one: an event-level, type-labelled tape. The QRH paper needed tick-by-tick
Eurex L1 data over a full year, split into **1,207,099** price-plateau periods for Bund and
**417,581** for DAX, with microsecond timestamps and a trade-line-derived order type
(arXiv:1901.08938). The duration model needed **1,023,480** one-tick mid-price moves for one symbol
in one month — each move requiring two consecutive same-direction half-tick changes, i.e. essentially
every best-quote update for AAPL in Dec 2022 (arXiv:2604.00346). The kernel estimator needed
**83,574** unique signed market orders in a 4h10m window (arXiv:2006.02460), and the LOB simulator
**12.5M** trades over a month of BTCUSDT plus **45,000** LOBSTER messages in one hour
(arXiv:2510.08085). FinRobot's finest live-probed granularity is 1-minute bars (`twelvedata
time_series`), which cannot resolve any of these objects: a 1-minute bar aggregates ~60 s of
nanosecond events into one point, destroying the inter-event distribution (median AAPL duration
0.128 s) and every kernel estimate. The `moomoo` gateway offers top-of-book snapshots and daily
capital flow but neither microsecond event timestamps nor queue sizes. So §2.1, §2.2, §2.3 and the
*calibration* half of §2.5 are **research-only** until a tape is ingested; §2.4 is simulation-only by
construction; and only §2.6's coefficient map plus the simulator core of §2.5 are usable without new
data. The cboe options row is the one non-tape input that is already reachable, and it is the only
route to *inverting* the rough-Heston parameters of §2.6 against a market surface.

## 4. Pitfalls, validation and measurement

- **Always test the branching ratio for subcriticality.** A non-parametric fit can return
  \\(\rho\ge1\\) without warning — SNH on Bitcoin gave \\(\rho_2=1.173\\) while EM gave \\(0.685\\) and
  WH \\(0.272\\) (arXiv:2006.02460). Report \\(\rho\\) for every fitted kernel matrix and reject or
  re-regularise any fit with \\(\rho\ge1\\); it implies a non-stationary, non-ergodic process.
- **The residual family is not cosmetic.** Exponential residuals inflate \\(\mu,\alpha,\beta\\) by
  roughly an order of magnitude (SE-Exp \\(\alpha=90.96\\) vs SE-Gamma \\(\alpha=0.094\\)) and
  degrade the KS statistic from 0.051 to 0.138 (arXiv:2604.00346). If the fitted baseline intensity
  is implausibly large, the residual distribution is wrong — do not rescale it away.
- **Point-forecast and distributional fit are different targets.** SE-Burr wins rRMSE but loses
  LRMSE; ACD-Gamma has the best KS in its class but no rRMSE gain; the FI-log-ACD model removes
  residual autocorrelation but does not improve out-of-sample forecasts (arXiv:2604.00346). Report
  both an absolute and a ratio-scale loss, and use the modified Diebold–Mariano test (all pairwise
  comparisons are significant at 1%).
- **Grid/bin choice drives non-parametric comparisons.** EM's performance "critically depends on the
  choice of bins" and WH's on the quadrature grid, so a SNH-vs-EM margin measured on one grid is not
  a general result (arXiv:2006.02460). Prefer methods with closed-form integrated kernels and report
  the kernel support/range explicitly.
- **Resetting at a reference-price change throws away the cross-side memory** that the two-sided
  model was built to capture (arXiv:1901.08938); and the invariant queue distribution is biased
  exactly where it matters (small \\(q\\), because empirical realizations stop when the queue
  empties). Validate queue distributions on snapshots taken at *random times*, not at plateau ends.
- **Large-tick and small-tick assets behave differently.** Bund (median spread 1 tick) and DAX
  (median 2 ticks) need different state granularity and give different queue-distribution fits; a
  single set of hyper-parameters does not transfer (arXiv:1901.08938).
- **Poisson and queue-reactive nulls are the acceptance gate.** A Hawkes calibration is only
  credible if it beats both: on BTCUSDT the Poisson baseline has ACF(1) \\(=0.011\\) and KS
  \\(0.312\\), and queue-reactive KS \\(0.697\\), against Hawkes KS \\(0.038\\) (arXiv:2510.08085).
  Always report the ACF of inter-event times and of time-rescaling residuals for the nulls too.
- **Time-rescaling is a necessary, not sufficient, test.** \\(\{\tau_k\}\sim\\)i.i.d. Exp(1) *iff*
  the model is correct (arXiv:2510.08085), so it can falsify a model but cannot choose between two
  models that both pass. Combine with out-of-sample NLL, KS/Cramér–von Mises and a held-out split
  (80/20 plus 5-fold time-series CV).
- **Intraday seasonality is real and must be handled.** Durations are shortest at open and close and
  longest mid-afternoon (arXiv:2604.00346); the rolling 5,000-event window is the paper's substitute
  for a deterministic seasonality term. A single global Hawkes baseline will absorb seasonality into
  spurious self-excitation.
- **Honesty about mechanism in the power-law diagnostic.** The universality result needs fast-
  accelerating \\(g\\), two-sided marks with non-positive mean, and fast-decaying mark tails; fat-tailed
  marks are explicitly out of scope and \\(m>0\\) makes the process explosive (arXiv:2102.00242).
  Never report a Zipf exponent from a fitted intensity without checking the mark-mean condition.
- **Microstructure-to-reduced-form maps are non-identifiable.** The rough Hawkes–Heston map pins
  only \\(\theta/m_\star\\), \\(c_Jr_\star\\) and \\(\Lambda/\bar\xi\\), so a calibrated reduced form
  corresponds to a whole family of microstructures; and the negative drift \\(b<0\\) is *implied* by
  subcriticality, not fitted (arXiv:2608.07709, Remark 5.3).

## 5. Recommended first implementation in FinRobot

Ranked by value-per-effort against what the layer can fetch today.

1. **Hawkes MLE + time-rescaling GOF toolkit (synthetic-first).** *What:* the exponential-kernel
   estimator with the \\(O(n)\\) recursive intensity, branching-ratio computation, and the
   time-rescaling KS/Cramér–von Mises harness from §2.5. *Consumes:* none live — unit-tested on
   simulated processes with known \\((\mu,\alpha,\beta)\\) (target: recover \\((0.487,1.234,1.512)\\)
   from truth \\((0.5,1.2,1.5)\\)). *Passes when:* estimated parameters lie within bootstrap SEs and
   the PIT residuals are uniform at 5%. *Effort:* S.
2. **Marked-Hawkes LOB simulator (C++/Python).** *What:* port the immigration–birth/thinning
   generator plus a price-time-priority matching engine, so FinRobot has a self-contained
   order-flow environment. *Consumes:* nothing live; `moomoo://get_cur_kline` only for a rough
   volume scale. *Passes when:* generated inter-event ACF and log-normal marks match the paper's
   qualitative stylized facts and a Poisson control is rejected. *Effort:* M.
3. **Duration/intensity feature service (SE-Gamma / SE-Burr).** *What:* the flexible-residual
   process of §2.2 exposed as a burst-timing feature, never a direction signal. *Consumes:* an
   event/tick stream — **blocked**; prototype only on `twelvedata time_series` 1-min bars as
   "duration to a one-tick *bar* move", labelled as a different object. *Passes when:* SE-Gamma KS
   \\(\ll\\) SE-Exp KS on the same window and \\(R^2\\) is reported honestly (\\(\le0.14\\)). *Effort:* M.
4. **Shallow Neural Hawkes kernel estimator.** *What:* the \\(\exp\\)(sum of ReLUs) non-parametric
   kernel fitter of §2.3, with a mandatory branching-ratio guard. *Consumes:* a signed trade tape —
   **blocked**; runnable today only on simulator output. *Passes when:* it recovers synthetic
   exponential/power-law/rectangular kernels with lower \\(L_1\\) error than EM/WH and \\(\rho<1\).
   *Effort:* M.
5. **Queue-reactive Hawkes extension.** *What:* the state-dependent intensity of §2.1, to be added
   once best-level queue sizes are available; it is the model that actually reproduces queue-size
   distributions. *Consumes:* L1 tape with order-type labels — **blocked**. *Passes when:* the LR test
   rejects the pure-Hawkes and pure-QR restrictions (\\(p<10^{-16}\\)) and the endogenous fraction is
   60–80%. *Effort:* L (after feed).
6. **Power-law intensity diagnostic.** *What:* estimate the intensity tail exponent
   \\(\lambda^{-2-a}\\) from a smoothed event rate and use \\(a\\) as a reflexivity monitor; check the
   mark-mean condition first. *Consumes:* any long event series — **blocked** for real use; simulation
   today. *Passes when:* simulated \\(m=0\\) gives exponent 2 and \\(m<0\\) reproduces the predicted
   \\(2+a\\). *Effort:* S.
7. **Rough-Heston coefficient inversion.** *What:* implement the §2.6 coefficient map and invert a
   market surface for \\((\alpha,\rho,b,\bar c_B)\\). *Consumes:* `https://cdn.cboe.com/api/global/delayed_quotes/options/_SPX.json`
   (`options_surface`, cboe, ok) — the one reachable non-tape input. *Passes when:* the recovered
   \\((\alpha,\rho,b,\bar c_B)\\) is close to a published calibration (e.g. \\(0.527,-0.731,-1.812,0.115\\))
   and the subcriticality check \\(\bar\xi\!\int z\nu_J(dz)<\mu_0\\) holds. *Effort:* L.
8. **Ingest an event-level tape.** *What:* add a Databento DBN / LOBSTER / exchange-ITCH ingestion
   path and register new data categories (`tick_trades`, `order_book_depth`, `order_events`). *Value:*
   unblocks items 3–6 and the calibration half of item 2; without it this whole category stays
   synthetic. *Risk:* storage (\\(10^8\\) events/name/quarter) and licensing. *Effort:* L.

## Appendix — papers read

| arXiv id | Title | Year |
|---|---|---|
| 2102.00242v2 | Ubiquitous power law scaling in nonlinear self-excited Hawkes processes | 2021 |
| 1901.08938v1 | Queue-reactive Hawkes models for the order flow | 2019 |
| 2604.00346v2 | Forecasting duration in high-frequency financial data using a self-exciting flexible residual point process | 2026 |
| 2510.08085v1 | A Deterministic Limit Order Book Simulator with Hawkes-Driven Order Flow | 2025 |
| 2006.02460v1 | Shallow Neural Hawkes: Non-parametric kernel estimation for Hawkes processes | 2020 |
| 2608.07709v1 | Microstructural Foundation for the Rough Hawkes–Heston Model | 2026 |
