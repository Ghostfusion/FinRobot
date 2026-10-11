# Machine Learning for Pricing — learnings from the q-fin.PR corpus
`157` of 2274 corpus papers matched this category (`155` with PDFs); this doc is based on a close reading of `6`.

## 1. What the corpus actually offers

- **Deep hedging under a local downside reward does *not* learn replication — it learns a systematic delta haircut.** Training TD3 agents on 21-day S&P 500 index-option episodes under a downside-shortfall reward and comparing them with a daily-updated Black–Scholes delta, the mean Agent−BS delta gap is negative in every walk-forward test year 2015–2023 (range $-0.009$ in 2017 to $-0.052$ in 2020); the underhedged share exceeds one half in every year and 75% in seven of nine. The correction is broad but state-dependent, strongest in high-implied-volatility and out-of-the-money regions; deep in-the-money bins can be positive, so the paper is explicit that this is "a broad state-dependent downward correction," not universal underhedging (arXiv:2605.21696v1).
- **The learned haircut has a closed-form economic reading.** For a one-period linearisation $dC \approx \Delta^{BS}dS + \nu\,d\sigma$, the variance-minimising hedge is $h^{MV} = \Delta^{BS} + \nu\,\mathrm{Cov}(d\sigma,dS)/\mathrm{Var}(dS)$; because equity-index spot and implied volatility typically co-move negatively and call vega is positive, this pushes the hedge below Black–Scholes. Symbolic regression distilling the neural policy recovers exactly this structure: formulas sit below Black–Scholes in 94.2% of states on average, mean correction $-0.055$ (median $-0.048$), with average correlation $+0.565$ with forward moneyness, $-0.346$ with implied volatility and only $-0.062$ with maturity (arXiv:2605.21696v1).
- **The same correction is regime-fragile, and the metric used decides the verdict.** In 2022 the agent loses $1.905$ accumulated-reward units with no significant variance loss: index-down/call-down intervals are 54.7% of the year and the volatility channel offsets only 7.9% of the spot-driven call loss, so the smaller short position recovers $0.92$ of the call loss versus $1.01$ for Black–Scholes. In 2023 the agent *improves* downside variance (log ratio $-0.168$) yet *worsens* ordinary variance (log ratio $+0.527$, significant at 1%) because option P&amp;L is spot-dominated (spot-only $R^2 = 85.8\%$, $\rho(\Delta S/S,\Delta\sigma) = -0.084$) and Black–Scholes is an unusually tight symmetric hedge. Frozen-policy stress tests over 45 policy/year pairs show downside variance favourable in 36 cases (13 significant) with no significant unfavourable case, but ordinary variance favourable in only 10 (17 significantly unfavourable) (arXiv:2605.21696v1).
- **A structural inductive bias fixes the training difficulty of deep hedging.** The "no-transaction band network" outputs a band $[b_l,b_u]$ and sets $\delta_{t+1}=\mathrm{clamp}(\delta_t;b_l,b_u)$, so the network never takes the current action as input and the action-dependence that stalls a naive feed-forward policy disappears. The strategy is proved optimal for any twice-differentiable utility and smooth-payoff derivatives (European *and* exotics), extending Davis–Norman–Whalley–Wilmott; the asymptotic band width is $\propto (cS_t)^{1/3}$ and the price spread obeys $p(c)-p(0)\propto c^{2/3}$. Experimentally it reaches its optimum in fewer than 100 Monte-Carlo batches where a plain feed-forward network has not converged in 1,000 (arXiv:2103.01775v1).
- **Two-stage calibration is fast only if the training samples are right.** Offline-train a small network on the map $\theta \mapsto \sigma_{BS}$, then calibrate online by minimising over $\theta$ with the network's autodiff gradient. Feeding the network entire surfaces built on *random* (adaptive, maturity-scaled) grids — rather than one point per parameter draw — trains a 4-hidden-layer/64-node network to calibrate a whole market surface in nearly one second with no interpolation or extrapolation. Fixed grids bias the roughness parameter badly: for the same 16 March 2021 SPX surface, rHeston $H$ estimates are $0.0100$ (fixed), $0.0933$ (adaptive), $0.0808$ (pointwise/random-grid); the random-grid error standard deviation for $H$ is about three times smaller than the fixed grid's (arXiv:2306.11061v2).
- **PDE solvers via neural networks are viable but regionally unstable.** A black-box PINN minimising the combined loss $MSE_{ivp}+MSE_{bvp}+\beta\,MSE_{pde}$ for the Black–Scholes operator reaches $\mathrm{cor}(y_{true},y_{pinn})\approx 1$ on simulated data (American-put MSE $0.23$ vs the binomial benchmark), and on real market data beats the analytical benchmark (NDX European call RMSE $389.9$ vs $445.4$; SPXC American put RMSE $0.947$ vs $2.318$) though absolute market errors remain. A free-boundary cousin replaces the black-box penalty with a Landau-transformed, boundary-fixed formulation that reads the early-exercise boundary directly off the network output (arXiv:2312.06711v1, arXiv:2211.11803v2).
- **Time discretisation, not model expressivity, is the binding constraint in optimal-stopping pricing.** Bermudan LSMC error from a coarse exercise grid is $O(N^{-1})$, while refining $N$ makes backward-recursion approximation errors accumulate, so practitioners are pushed to coarse grids (the classic $T=3,N=9$ benchmark allows exercise only once every four months). The CARLOS reinforcement-learning solver starts from a coarse LSMC fit, halves $\Delta t$ over about a dozen loops while learning one aggregate space-time network, and closes most of the Bermudan–American gap: for the 2-D max-call M2.A, literature Bermudan prices are $13.897/13.901$ and the PDE American bound $14.214$, while CARLOS delivers $14.171$ at 3–10× the speed of a fine-grid comparator (arXiv:2606.17545v1).
- **The engineering gate is decisive for FinRobot.** Every method above is trained with a differentiable-programming stack — PyTorch in arXiv:2103.01775v1 and arXiv:2312.06711v1, TensorFlow in arXiv:2211.11803v2, PyTorch again in arXiv:2606.17545v1 — and FinRobot's runtime dependency set is pure NumPy by design (red line 11 in `finrobot_desktop/tests/audit/test_architecture.py` bans `torch`, `tensorflow`, `jax`, `scipy`, `scikit-learn`). What is *directly* implementable against served data is narrower: minimum-variance/symbolic delta corrections as regressions, no-transaction-band policy *evaluation*, and least-squares Monte-Carlo for early exercise. Training the full neural pricing maps, PINNs and CARLOS belongs in a separate environment.

## 2. Implementable formulas & algorithms

### 2.1 No-transaction-band hedging policy (NumPy-evaluable)
**Purpose.** Derive a frictions-aware hedge rule that is the optimal structure for a wide class of utilities/derivatives, and that can be evaluated without a recurrent action input. The *training* uses PyTorch; the band-to-position map and its evaluation are pure NumPy once the band functions are fitted.

Hedge recreation and utility-indifference price:
$$P(Z;S,\delta) = -Z(S) + (\delta\!\cdot\! S)_T - C_T(S,\delta), \qquad C_{t_i}(S,\delta) = c\,S_{t_i}|\delta_{t_i}-\delta_{t_{i-1}}|, \qquad
p_u(Z) = \rho_u(-Z) - \rho_u(0).$$

Band rule and its asymptotic (Whalley–Wilmott) width:
$$(b_l,b_u) = \mathrm{NN}(I_{t_i}),\qquad \delta_{t_{i+1}} = \mathrm{clamp}(\delta_{t_i};b_l,b_u), \qquad
b_u - b_l = \left(\tfrac{3\,c\,S_t}{2\,\Gamma^{BS}}\right)^{1/3}\!\!\big/\Gamma^{BS} + o(c^{1/3}),$$
with the price spread scaling $p(c)-p(0)\propto c^{2/3}$.

- **Inputs:** $I_{t_i}=\{\log(S_{t_i}/K),\,T-t_i,\,\sigma\}$, plus cumulative maximum of log-moneyness $M_{t_i}=\max_{j\le i}\log(S_{t_j}/K)$ for path-dependent payoffs.
- **Parameters:** proportional cost $c$; exponential-risk-aversion $\lambda=1$ in the paper; network anchors the two outputs on the Black–Scholes delta: $b_u, b_l = \Delta^{BS} \pm \mathrm{LeakyReLU}(\cdot)$.
- **Observed effects:** the band learns to *stop hedging* (near-zero ratio) once $c$ is expensive; sits close to the Whalley–Wilmott asymptote for small $c$; converges faster than a feed-forward policy (arXiv:2103.01775v1).
- **Failure modes:** the clamp gradient vanishes inside the band, so a small slope (LeakyReLU, negative slope 0.01) is needed to backpropagate; an inverted $b_l>b_u$ input must be given a sane definition (author uses the midpoint); the optimality proof assumes a twice-differentiable utility and smooth payoffs, excluding early-exercise contracts.

### 2.2 Physics-informed / free-boundary PDE solver (needs `torch`)
**Purpose.** Price European and American options by solving the Black–Scholes PDE as a loss rather than a lattice; for American options, recover the early-exercise boundary as a by-product.

Black–Scholes operator and combined PINN loss:
$$\mathcal{N}[V] = \frac{\partial V}{\partial t} + \tfrac12\sigma^2 S^2 \frac{\partial^2 V}{\partial S^2} + rS\frac{\partial V}{\partial S} - rV = 0, \qquad
\mathcal{L}(\beta) = MSE_{ivp} + MSE_{bvp} + \beta\, MSE_{pde}.$$
American LCP form (one of the two inequalities is an equality):
$$\Big(\tfrac{\partial V}{\partial t} + \tfrac12\sigma^2 S^2 V_{SS} + rS V_S - rV\Big)\big(\max(K-S,0)-V\big) = 0,\qquad
S_f(t) = \max\{t : V = K-S\}.$$
Landau-transformed free-boundary formulation (arXiv:2211.11803v2), with $x=\ln S - \ln s_f(t)$, $V(t,S)=U(t,x)$:
$$\frac{\partial U}{\partial t} - \frac{r}{2}\frac{\partial^2 U}{\partial x^2} + \frac{s_f'}{s_f}\frac{\partial U}{\partial x} + rU = 0,\quad x>0,\qquad U(t,x) = K - e^{x}s_f(t),\ x<0,$$
and the auxiliary function that embeds the DNN output $N(\tau,y;\theta)$ and the boundary data:
$$P(\tau,y;\theta) = e^{-y^2/2}M(\tau,y;\theta),\qquad s_f(\tau) = K - x_{max}\,N(\tau,0;\theta),\quad s_f'(\tau) = -x_{max}\,N_\tau(\tau,0;\theta).$$

- **Inputs:** $(S,t)$ grid (and the transformed $(y,\tau)$ grid for the free-boundary form); spot, strike, $r$, $\sigma$.
- **Parameters:** PDE penalty $\beta$ (larger $\beta$ improves non-linearity capture but can push Boundary-1 predictions off zero); network width $\gg$ depth is the corpus' recommendation, tanh activation; free-boundary auxiliary decay $\lambda=100$ (stable range 90–110), $y_{min}=10^{-8}$ to avoid the singularity at $\tau=0$; sigmoid activations with Adam + exponential decay in the free-boundary form.
- **Observed effects:** simulation $\mathrm{cor}\approx1$; market data beats analytical benchmarks in RMSE; stretched grid sampling concentrating points near the left boundary beats uniform and randomly-structured grids and achieves comparable accuracy with roughly a third of the training points (arXiv:2312.06711v1, arXiv:2211.11803v2).
- **Failure modes:** convergence becomes oscillatory near $S\to0$ and $t\to1$; the PINN needs correctly *fixed* $\sigma,r$ to price market data, and a wrong choice dominates the error; the free-boundary velocity $s_f'(0)$ is singular at the payoff, so the exact left boundary is only mimicked to pseudo-exact order; both methods require `torch`/`tensorflow`.

### 2.3 Two-stage deep calibration with random grids (pricing map needs `torch`)
**Purpose.** Invert the market implied-volatility surface into model parameters fast enough for repeated use, without interpolation or extrapolation of market quotes.

Calibration objective and the two stages:
$$\hat\theta = \arg\min_{\theta\in\Theta} d\big(\sigma^{M}_{BS}(\theta;K,T),\,\sigma^{mkt}_{BS}(K,T)\big),\qquad
w^\star = \arg\min_w \sum_{u,i,j}\big(F_M(\theta_u;w)_{ij}-\sigma^{M}_{BS}(\theta_u)_{ij}\big)^2,$$
then online optimise $\hat\theta = \arg\min_\theta \sum_{i,j}(F_M(\theta;w^\star)_{ij}-\sigma^{mkt}_{BS}(K_i,T_j))^2$ using the network's autodiff gradient.

- **Inputs:** parameter draws $\theta_u$; response surfaces generated by FFT (rHeston) or Monte Carlo (rBergomi); the target market surface $\sigma^{mkt}_{BS}(K_i,T_j)$.
- **Parameters:** network 4 hidden layers × 64 nodes, ELU activations, identity output, RMSE loss, Adam, ≤500 epochs with patience 50; $q$ parameter sets × $n=11$ expiries × $m=13$ strikes per set; maturity buckets span $[0.003,2.5]$ years; strike range $[S_0(1-l\sqrt T),\,S_0(1+u\sqrt T)]$ with $l=0.55,\ u=0.30$; forward variance curve piecewise-constant on the maturity buckets.
- **Observed effects:** calibrates a whole surface in nearly one second; random-grid pointwise training keeps improving out-of-sample error as data grows where a purely pointwise scheme saturates after about $2^{19}$ samples; three-fold smaller standard deviation in the recovered Hurst $H$ than a fixed grid (arXiv:2306.11061v2).
- **Failure modes:** fixed grids under-sample short expiries and bias $H$ downward (steepening the short-dated smile) — 16 March 2021 SPX $H=0.0100$ vs $0.0808$; flat spline extrapolation before the first maturity strips short-dated curvature; option-parameter draws for which Black–Scholes inversion fails must be discarded; the sample generation phase (FFT/MC) is the real cost and needs an external stack.

### 2.4 Aggregate-DNN continuous-time optimal stopping (CARLOS; needs `torch`)
**Purpose.** Price American-style contracts by learning a continuous-time exercise rule, removing the Bermudan–American gap that coarse LSMC leaves.

Timing value, Snell-envelope stopping time and LSMC recursion:
$$\mathcal{T}(t_n,x) = \tilde q(t_n,x) - h(x),\qquad \tau_n^\star = \min\{t_k\in\mathcal{T}_n : \mathcal{T}(t_k,X_{t_k})\le 0\},\qquad
\tilde q(t_n,X_{t_n}) = e^{-r\Delta t}\,\mathbb{E}\big[\tilde q(t_{n+1},X_{t_{n+1}})\,\big|\,\mathcal{F}_{t_n}\big].$$
Aggregate network $Q(s\equiv(t,x),a)$ with halved nested grids $\mathcal{T}^{(b)}\subseteq\mathcal{T}^{(b-1)}$, decayed learning rate $\eta^{[b+1]}=\alpha_{dec}\eta^{[b]}$, and an adaptive sampling mixture:
$$p^{[\ell]} = \lambda^{[b]}_{+}p^{\{b,+\}} + \lambda^{[b]}_{-}p^{\{b,-\}} + \lambda^{[b]}_{exl}p^{\{b,exl\}} + \lambda^{[b]}_{ter}p^{\{b,ter\}}.$$

- **Inputs:** simulated $d$-dimensional Black–Scholes paths (state $X_t$, time $t$); payoff $h$; discount rate $r$.
- **Parameters:** $I=4$ layers ($q_0=d+1$ inputs, 3 hidden), Swish or ReLU, Adam, $\eta^{[0]}=10^{-4}$, $\alpha_{dec}=0.7$, batch 64, 3–6 grid levels (halving per few loops), $\approx$ a dozen RL loops; 4 paths average per input to cut payoff noise.
- **Observed effects:** M2.A: literature Bermudan $13.898$–$13.901$, CARLOS $14.171$ vs PDE $14.214$; M5.B: literature $25.84/26.055/26.147$, PDE (absent), CARLOS $12.009$ interpretation per contract; 3–10× faster than a fine-grid ADNN comparator (arXiv:2606.17545v1).
- **Failure modes:** *concept drift* — training labels shift as the exercise grid refines, so grids must be traversed gradually; the stopping region shrinks as $\Delta t\to0$ and "delayed stopping" exploration is needed lest the network never re-expand the continuation region; non-smooth activations (ReLU) give zig-zag stopping boundaries; the network cannot be trusted away from the sampled boundary neighbourhood without exploratory samples.

### 2.5 Minimum-variance / symbolic delta correction (NumPy regression)
**Purpose.** Reproduce the corpus' central deep-hedging finding as a lightweight, inspectable correction to Black–Scholes that needs no neural training.

Minimum-variance hedge and a distilled closed form:
$$h^{MV} = \Delta^{BS} + \nu\,\frac{\mathrm{Cov}(d\sigma,dS)}{\mathrm{Var}(dS)},\qquad
\hat\Delta^{SR}_{2016} = \mathrm{clip}\big(\Delta^{BS} + \sigma\,(e^{m}-2.949),\,0,\,1\big),\quad m = F_t/K.$$
Daily hedging P&amp;L, and the reward whose maximisation is equivalent to minimising $\mathbb{E}\sum \gamma^{t}\,\mathrm{PnL}^{(100)-}_{t+1}$:
$$\mathrm{PnL}_{t+1} = C_{t+1}-C_t-\delta_t(S_{t+1}-S_t)-cS_t|\delta_t-\delta_{t-1}|,\qquad F_t/K = S_t e^{(r_t^f-q_t)\tau_t}/K,$$
$$r_{t+1} = 100^{0.03} + \mathrm{PnL}^{(100)}_{t+1} - \kappa\big|\mathrm{PnL}^{(100)}_{t+1}\big|^{\alpha}\ \xrightarrow{\kappa=\alpha=1}\ 0.3 - 20\,X^-_{t+1},\ X^-_{t+1}=\max(-X_{t+1},0).$$

- **Inputs:** option mid-prices $C_t$, index level $S_t$, strike $K$, maturity $\tau_t$, $r_t^f$, dividend yield $q_t$, Black–Scholes implied volatility $\sigma_t^{IV}$.
- **Parameters:** transaction cost $c$ (paper sets $c=0$ to isolate model effects); $(\kappa,\alpha)=(1,1)$ reduces the objective to local shortfall; forward-moneyness state beats spot-moneyness in higher-rate samples; state vector is $(F/K,\tau,h_t,\sigma^{IV}_t)$ with $h_t=-\delta_{t-1}$ — analytical Greeks are *not* inputs.
- **Observed effects:** the actor's advantage is asymmetric — downside variance falls significantly in 7 of 9 years while ordinary variance is insignificant in most years and significantly higher in 2023 (arXiv:2605.21696v1).
- **Failure modes:** regime fragility (2022 reward loss, 2023 variance loss) is intrinsic; the reward is path-wise, so accumulated reward, CVaR, downside variance and ordinary variance rank the same hedge differently and must all be reported; the symbolic formulas inherit the fragility and can even worsen it (2022).

### 2.6 Least-squares Monte Carlo baseline (NumPy)
**Purpose.** Provide the numpy-only lower bound against which any neural stopping solver is compared; the CARLOS initialisation stage is exactly this.

Backward recursion over a coarse grid $\mathcal{T}^{(N)}=\{t_0,\dots,t_N=T\}$, $\Delta t=T/N$, regressing pathwise timing values on the state (see §2.4); the Bermudan value $V^{(N)}(t_n,x)$ converges to the American value $V(t,x)$ at rate $O(N^{-1})$.

- **Inputs:** simulated underlying paths; payoff $h$; discount rate $r$.
- **Parameters:** exercise-grid size $N$ (kept well below 100 in practice); polynomial basis or a shallow network as the regression emulator; warm-started weights across time steps.
- **Observed effects:** the classic $T=3,N=9$ configuration exercises only every four months, materially undervaluing early-exercise optionality (arXiv:2606.17545v1).
- **Failure modes:** error back-propagation compounds with $N$; smooth-pasting at the boundary makes positive-vs-zero timing values numerically hard to classify as $\Delta t\to0$; linear bases miss non-linear stopping regions in higher dimension (motivating the neural emulators of §2.4).

## 3. Data requirements → available endpoints

| Input | Endpoint | Category | Provider | Probe status |
|---|---|---|---|---|
| Daily OHLCV (underlying paths for RL hedging / LSMC episodes) | `https://eodhd.com/api/eod/AAPL` | core_stock_apis | eodhd | ok |
| Daily OHLCV (alt) | `https://api.tiingo.com/tiingo/daily/AAPL/prices` | core_stock_apis | tiingo | ok |
| Interval bars (candidate intraday) | `https://api.twelvedata.com/time_series` | core_stock_apis | twelvedata | ok (supports `interval`; intraday not separately probed) |
| SPX delayed option chain (bid/ask, IV, strikes, expiries — deep-hedging state and calibration targets) | `https://cdn.cboe.com/api/global/delayed_quotes/options/_SPX.json` | options_surface | cboe | ok |
| Single-name option chain (e.g. SPXC put in PINN market test) | `moomoo://get_option_chain` | options_data | moomoo | gateway |
| Expected move (implied, option-chain derived) | `moomoo://get_option_underlying_overview` | expected_move | moomoo | gateway |
| Technical indicators / volatility proxies | `https://www.alphavantage.co/query` | technical_indicators | alpha_vantage | ok |
| Risk-free rate (discounting, BS benchmark, forward moneyness) | `https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2026/all` | risk_free_curve | federal_reserve | ok |
| Macro state series (rate/credit/term structure) | `https://api.stlouisfed.org/fred/series/observations` | macro_data | fred | ok |
| Dividend yield (forward moneyness, BS benchmark) | `https://eodhd.com/api/div/AAPL` | corporate_actions | eodhd | ok |
| News features for ML inputs | `https://eodhd.com/api/news` | news_data | eodhd | ok |
| News sentiment (alt) | `https://www.alphavantage.co/query` | news_sentiment | alpha_vantage | ok |
| Global news tone | `https://api.gdeltproject.org/api/v2/doc/doc` | news_sentiment | gdelt | fail — HTTP 429 rate_limited |
| 5-min intraday returns / realized-variance targets | **gap** — no certified 5-min series in the inventory; twelvedata `interval` and massive aggregates are the only candidates | technical_indicators / core_stock_apis | — | gap |
| Model-generated training labels (rHeston/rBergomi FFT/MC surfaces for §2.3) | **gap** — no endpoint; must be generated locally by an external Fourier/Monte-Carlo engine | — | — | gap |
| Credit/CDS spread feed (deep xVA / counterparty exposure) | **gap** — no provider exposes a CDS or credit-spread series | — | — | gap |
| Swap / swaption &amp; interest-rate derivative quotes | **gap** — not in the inventory | — | — | gap |
| Bond prices / bond-yield term structure beyond the Treasury curve | **gap** — not in the inventory | — | — | gap |
| Futures / commodity prices | **gap** — not in the inventory | — | — | gap |
| Crypto spot / derivative prices | **gap** — not in the inventory | — | — | gap |
| Intraday quote / order-book feed (fine-grid hedging frictions) | **gap** — no certified tick or book feed | — | — | gap |
| GPU / differentiable-training stack (`torch`, `tensorflow`, `scipy`) | **gap** — the runtime dependency set is pure NumPy by design (red line 11) | — | — | gap |

Row tally: **10 ok, 2 gateway, 1 fail, 9 gap** (22 rows).

## 4. Pitfalls, validation and measurement

- **Model-agnostic performance claims do not hold; report metric families separately.** The corpus is explicit that accumulated reward, mean terminal P&amp;L, 5% CVaR, downside variance and ordinary variance rank the same deep-hedging policy differently — 2022 is a reward failure with no variance loss, 2023 is a variance failure with a downside improvement (arXiv:2605.21696v1). Never quote a single number; always report the downside metric *and* the symmetric metric.
- **Regime fragility is a result, not noise.** The deep-hedging correction is useful only when the option surface supports it; a 45-pair frozen-policy stress test shows downside variance is persistent (36 favourable, 13 significant) while ordinary variance flips (17 significant adverse). Any implementation must ship regime diagnostics and a long-horizon stress test, not an unconditional "beats Black–Scholes" claim (arXiv:2605.21696v1).
- **Time discretisation behaves non-monotonically.** In optimal-stopping pricing, refining $\Delta t^{tr}$ can *lower* the attainable payoff through error accumulation, and the best reward often sits off the diagonal ($\Delta t^{ex}\simeq \tfrac14\Delta t^{tr}$); the smooth-pasting condition makes the boundary numerically ambiguous as $\Delta t\to0$. Validate the stopping rule against a PDE gold standard in dimensions 1–2 and against literature Bermudan lower bounds elsewhere (arXiv:2606.17545v1).
- **Calibration grid choice biases the parameters.** Short expiries carry most of the information about skew/kurtosis and the roughness $H$; fixed grids that start at $T=0.1$ produce fat, negatively-skewed $H$ errors and a systematically over-estimated roughness that propagates through interpolation/extrapolation to the whole surface. Prefer random/adaptive grids and calibrate directly on market quotes to avoid two rounds of surface processing; discard parameter draws whose Black–Scholes inversion fails (arXiv:2306.11061v2).
- **PINN convergence and parameter dependence.** The combined-loss PINN oscillates near $S\to0$ and $t\to1$; the PDE penalty $\beta$ trades non-linearity capture against non-zero boundary predictions; and because $\sigma$ and $r$ are fixed inputs, a wrong choice dominates the residual — the paper attributes part of its market-data error to exactly this (arXiv:2312.06711v1). Always compare against a deterministic finite-difference/binomial solution on the same parameters.
- **Look-ahead and in-sample leakage risks.** Walk-forward must split on calendar time (train on years $<Y-1$, validate on $Y-1$, test on $Y$) with non-overlapping 21-day episode windows in validation/testing, and feature standardisation must use training-sample moments only (arXiv:2605.21696v1); the deep-calibration training set must be generated from *synthetic* parameter draws, never from the market surface that the calibration is subsequently scored on (arXiv:2306.11061v2); CARLOS training grids must never reuse the exercise grid it is being evaluated on.
- **Inference must respect the data's correlation structure.** Resample 21-day calendar windows first, then option episodes within each window, to account for the common spot/volatility path; report the two-stage bootstrap confidence intervals per test year (arXiv:2605.21696v1). For pairwise pricing/hedging-loss comparisons use Diebold–Mariano with HAC errors and, where several models compete, the Model Confidence Set rather than a single winner.
- **Auditability.** Neural hedges and pricing maps are hard to stress-test; the corpus' remedy is policy distillation into compact formulas and explicit regime diagnostics. Any FinRobot deployment should carry a symbolic/regression surrogate alongside the network for inspection, and treat the surrogate's regime failures as part of the deliverable (arXiv:2605.21696v1).

## 5. Recommended first implementation in FinRobot

1. **(S) Equity OHLCV + risk-free ingest and a Black–Scholes delta benchmark harness.** Data: `eodhd`/`tiingo` OHLCV (`core_stock_apis`) + `federal_reserve` `risk_free_curve`. Value: the baseline every hedging/pricing experiment measures against, and it needs no options feed to start. Risk: no option P&amp;L without a chain (arXiv:2605.21696v1).
2. **(S) SPX option-chain loader and episode builder.** Data: `cboe` `options_surface` (delayed SPX quotes). Build mid-prices, strikes, expiries, IV, and forward moneyness $F/K=S_t e^{(r^f_t-q_t)\tau}/K$; split into non-overlapping calendar windows for walk-forward. Value: supplies both the deep-hedging state/reward and the calibration targets that every later item consumes. Risk: delayed SPX only — no single-name chains, so PINN-style cross-asset tests are limited (arXiv:2605.21696v1, arXiv:2312.06711v1).
3. **(S) Minimum-variance / symbolic delta correction as a NumPy regression.** Data: the option chain above + OHLCV. Fit $\hat\Delta = \mathrm{clip}(\Delta^{BS} + \sigma(e^{m}-2.949),0,1)$ or a small moneyness/IV regression. Value: reproduces the corpus' central empirical result (systematic delta haircut, mean $-0.055$) with zero heavy dependencies and a fully inspectable formula. Risk: regime fragility — it inherits the 2022/2023 failure modes and must be shipped with regime diagnostics (arXiv:2605.21696v1).
4. **(M) No-transaction-band policy *evaluation* in NumPy.** Data: OHLCV + chain. Implement $\delta_{t+1}=\mathrm{clamp}(\delta_t;b_l,b_u)$ and the P&amp;L/utility-indifference accounting, with a simple regression (or the Whalley–Wilmott $c^{1/3}$ width) supplying the band. Value: frictions-aware hedging and a utility-indifference price without a recurrent network input. Risk: only the evaluation is NumPy-feasible; *training* the band network needs `torch` and belongs in a separate environment (arXiv:2103.01775v1).
5. **(M) Least-squares Monte-Carlo early-exercise module (NumPy).** Data: OHLCV + `risk_free_curve`. Backward-regress the timing value $\mathcal{T}=\tilde q-h$ on a coarse exercise grid with a polynomial (or shallow, warm-started) basis. Value: American/Bermudan pricing on served data and the essential lower bound for any later neural stopping solver. Risk: backward-recursion error and path-count requirements; keep $N$ modest (arXiv:2606.17545v1).
6. **(L) Two-stage deep-calibration scaffold for SPX surfaces (`torch`, separate env).** Data: `cboe` `options_surface` as the live market surface; synthetic rHeston/rBergomi labels generated offline (a `gap` for FinRobot itself). Value: near-instant surface inversion into model parameters for downstream pricing. Risk: requires the banned training stack plus an external Fourier/Monte-Carlo generator; fixed-grid sampling would bias $H$, so the random/adaptive grid must be used (arXiv:2306.11061v2).
7. **(L) PINN / free-boundary solver for American puts (`torch`), validated against the NumPy binomial/FD benchmark.** Data: `cboe` chain for market comparison; `risk_free_curve` for $r$. Value: recovers the early-exercise boundary directly and prices early-exercise contracts; the free-boundary form beats a black-box penalty on training efficiency. Risk: outside the runtime set, regionally unstable convergence, and a strong dependence on correctly-fixed $\sigma,r$; only worth building after items 1–5 give a trustworthy NumPy benchmark (arXiv:2312.06711v1, arXiv:2211.11803v2).

## Appendix — papers read

| arXiv id | title | year |
|---|---|---|
| 2605.21696v1 | What Does Deep Hedging Actually Learn? Delta Corrections, Regime Fragility, and Symbolic Distillation | 2026 |
| 2606.17545v1 | Continuous-time Optimal Stopping through Deep Reinforcement Learning | 2026 |
| 2306.11061v2 | Deep calibration with random grids | 2023 |
| 2312.06711v1 | Physics Informed Neural Network for Option Pricing | 2023 |
| 2211.11803v2 | Deep learning and American options via free boundary framework | 2022 |
| 2103.01775v1 | No-Transaction Band Network: A Neural Network Architecture for Efficient Deep Hedging | 2021 |
