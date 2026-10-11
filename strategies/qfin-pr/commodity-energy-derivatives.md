# Commodity & Energy Derivatives — learnings from the q-fin.PR corpus
`104` of 2274 corpus papers matched this category (`104` with PDFs); this doc is based on a close reading of `6`.

## 1. What the corpus actually offers

- **Once seasonal spreads narrow, essentially all natural-gas storage value is extrinsic.** Under a Seasonal-Gabillon two-factor futures model fitted to 1997–2007 curves ($\sigma_S=0.458$, $\sigma_L=0.166$, $\lambda=0.790$, $\mu_1=0.025$, $\mu_2=0.004$, $\rho=0.411$) the spot-trading (extrinsic) value beats the pure-futures intrinsic value in *every* test year of a 2003–2012 backtest, with an extrinsic/intrinsic ratio up to 500% for fast storage and up to 100% for slow storage; the authors document FERC's observation that winter/summer spreads have been shrinking (arXiv:1312.3789v1).
- **Futures hedging of a storage book is a variance reducer, not a value adder.** The tangent-process delta cuts simulated cash-flow standard deviation by up to a factor of $\approx 10$ (fast storage 2007: \$340.2M$\to$\$190.9M; slow storage: \$232.8M$\to$\$28.0M) while leaving the expectation unchanged, because futures are martingales (arXiv:1312.3789v1).
- **Storage model risk lives in the spot law, not the futures law.** Adapting Cont's measure $\pi(H)=\max_{Q\in\Gamma}E_Q[H]-\min_{Q\in\Gamma}E_Q[H]$ to the family $\Gamma$ of Garch(1,1) spot perturbations that pass a Kolmogorov–Smirnov normality test and stay within $\epsilon$ of the optimal likelihood, storage value uncertainty is dominated by spot specification (arXiv:1312.3789v1).
- **Spike modelling pays off only for fast storage and only in expectation.** Adding the Hambly-style overlay ($\beta=300$, Poisson $\lambda^+\!=0.833$, $J^+\!\sim\!N(0.258,0.391)$, $\lambda^-\!=2.949$, $J^-\!\sim\!N(-0.762,0.640)$) raises the *simulated* extrinsic value but also its standard deviation, with little effect for slow storage; the historical backtest shows no significant advantage (arXiv:1312.3789v1).
- **Swing options are a consumption-control problem whose price rises with mean reversion.** In a one-factor local-volatility linear model the swing price increases with the mean-reversion speed $a$ because the implied volatility of the one-day (day-ahead) delivery period rises with $a$; the monthly-futures strike volatility moves the opposite way, so forward-starting prices rise through the relative fixing-period volatility (arXiv:2001.08906v1).
- **Bang-bang optimality requires an integrality condition and should not be imposed blindly.** For the reference contract ($C_m=12.5$ MWh, out of Bardou et al.'s Theorem 2 hypotheses) restricting to min/max consumption lowers the price ($7.97\to7.76$, 1 s.e. $0.04$); for $C_m=12$ MWh (inside the theorem) the restriction changes nothing ($8.46$ both) (arXiv:2001.08906v1).
- **Reinforcement learning reproduces the LSMC swing price to ~1%.** PPO gives $7.92$ (out-of-theorem) and $8.40$ (within-theorem) against LSMC's $7.97$/$8.46$, with a 5-hidden-layer/4-unit network beating both shallower and wider ones; PPO is the intended route for higher-dimensional curve/vol dynamics (arXiv:2001.08906v1).
- **Battery revenue is concave in both market access and cycling.** For a 2h battery over 14 Jun 2024–1 Jul 2025, day-ahead-only earns €229/day, rolling intrinsic in continuous intraday €297/day, and day-ahead + intraday auction + rolling intrinsic €339/day; 15-min products beat hourly by ~20%; halving the trading frequency (5$\to$30 min) costs ~14%; profit for 1/2/4 daily cycles is €341/€466/€559, and a flexible annual reallocation with up to 25% suspended days improves by at most 3.2% (arXiv:2510.01956v2).
- **HDD/CDD degree-day futures have closed-form CAR($p$) prices and monotone sensitivities.** $F_{\mathrm{CDD}}(t,\tau_1,\tau_2)=\int_{\tau_1}^{\tau_2}\Sigma(t,s)\,\Psi\!\big(\frac{m_\theta(t,s,X(t))-c}{\Sigma(t,s)}\big)ds$ with $\Psi(x)=x\Phi(x)+\Phi'(x)$; the New York CAR(3) fit ($\sigma=5.25$) makes $\Phi(Z)=1$ for $s-t=1,2$ and stabilises at $0.9924$ once $s-t\ge12$ (arXiv:2403.00006v1).
- **Degree-day sensitivities are ordered by maturity, and the approximation is conservative.** $\partial F/\partial x_i$ is positive for all $i$; the deseasonalised level $Y$ dominates at very short maturity, the slope $Y'$ dominates near $s-t\approx2$, the curvature $Y''$ is always the smallest, and all sensitivities decay at the long end; the linearised price is *more* sensitive than the true price, so its Greeks are upper bounds (arXiv:2403.00006v1).
- **Carbon (EU ETS Phase 3, ICE ECFZ December futures) needs at least two variance factors plus jumps.** RV built from 5-min returns averages 9.6% ($\approx$49.5% annualised vol) with log-return kurtosis 64.9; a one-factor SV cannot reproduce the HAR coefficients, while the 2-SVJ gives $\kappa_1=0.039$/day (slow, half-life $\approx$20 days), $\kappa_2=2.03$/day (fast), $\Lambda_1=0.0083$, $\Lambda_2=0.032$, $\rho_1=-0.82$, $\rho_2=-0.11$ (arXiv:2501.17490v2).
- **Carbon option pricing needs three risk premia and stays comparable to the state of the art.** The equity premium $\phi=-7.35\text{e-}3$ and variance premia $\psi_1=2.81\text{e-}3$, $\psi_2=1.50\text{e-}2$ translate into $\kappa_j^\ast=\kappa_j-\phi\rho_j\Lambda_j-\psi_j\Lambda_j^2$, lowering risk-neutral mean reversion and raising the long-run variance level; pricing gives RMSE$_{IV}$ 19.8 ($m<0.85$), 12.0 ($0.85\le m\le1.1$) and 11.3 ($m>1.1$), essentially tied with the LHARG-ARJ benchmark (arXiv:2501.17490v2).
- **Crude oil is rough, but classical models can fake the fit only with implausible vol-of-vol.** WTI 5-min RV gives $H\in[0.14,0.21]$ depending on $q$ (Alfeus–Nikitopoulos: $H=0.153$ for WTI); rBergomi ($H=0.078$, $\eta=2.16$, $\rho=-0.309$) and rHeston ($H=0.277$, $\eta=2.06$, $\rho=-0.202$, $\kappa=5.62$) beat classical Bergomi/Heston on the joint 2025 smile fit, but the classical models need $\eta\approx16.5$ (Bergomi) and $\approx9.97$ (Heston) to compete (arXiv:2603.26514v1).
- **The Samuelson effect is governed by the mean-reversion speed, which vanilla options cannot identify.** ATM implied volatility rises toward delivery as $a$ increases ($a=0$ gives none); since any fixed $a\in[0.3,0.7]$ fits the vanillas, the paper fixes $a=0.5$ and reserves mid-curve/calendar-spread options for identifying it (arXiv:2603.26514v1).

## 2. Implementable formulas & algorithms

### 2.1 Seasonal-Gabillon two-factor curve with a joint spot process
**Purpose.** Model the natural-gas futures curve and spot jointly so that a storage book can be valued by dynamic programming and hedged with liquid futures.

**Formulas.** Futures curve (Seasonal Gabillon, short/long factor):
$$\frac{dF(t,T)}{F(t,T)}=e^{-\lambda(T-t)}\varphi(t)\sigma_S\,dW^S_t+\bigl(1-e^{-\lambda(T-t)}\bigr)\sigma_L\,dW^L_t,\qquad d\langle W^L,W^S\rangle_t=\rho\,dt,$$
$$\varphi(t)=1+\mu_1\cos\!\big(2\pi(t-t_1)\big)+\mu_2\cos\!\big(4\pi(t-t_2)\big),$$
with $t_1\!\approx$ January (winter peak) and $t_2\!\approx$ August (secondary summer peak). Spot-prompt-bound model (model 2):
$$\frac{S_t-P_t}{P_t}=a_1+a_2\frac{S_{t-1}-P_{t-1}}{P_{t-1}}+a_3\frac{P_{t-1}-B_{t-1}}{B_{t-1}}+\epsilon_t,\qquad \epsilon_t=\sigma_t z_t,\quad \sigma_t^2=\kappa+\gamma_1\sigma_{t-1}^2+\alpha_1\epsilon_{t-1}^2,$$
where $P$ is the prompt and $B$ the second-nearby (back) futures. Storage control problem and its Longstaff–Schwartz solution:
$$J^\star(t_i,x,v)=\max_{u_i\in\{\mathrm{inj},\mathrm{no},\mathrm{with}\}}\Big\{\varphi_{u_i}(S_{t_i})+E\big[J^\star(t_{i+1},X_{t_{i+1}},\hat V_{u_i}(v))\,\big|\,X_{t_i}=x,\,V_{t_i}=v\big]\Big\},$$
$$V_{t_{i+1}}=\min(V_{t_i}+a_{\mathrm{inj}}\Delta t,V_{\max})\ \text{or}\ \max(V_{t_i}-a_{\mathrm{with}}\Delta t,V_{\min}),\quad \varphi_{u_i}=S_{t_i}\big(V_{t_{i+1}}-V_{t_i}\big).$$
Hedging delta via the tangent process:
$$\Delta_2(t_i,T_j)=E_{t_i}\!\Big[\sum_{T_{j-1}\le t_l<T_j}\big(V_{l+1}(u^\star)-V_l(u^\star)\big)\frac{F(t_l,T_j)}{F(t_i,T_j)}\Big].$$

**Inputs.** Daily spot $S$; monthly futures curves $F(t,T_i)$ (72 quoted, $\le$24 liquid); prompt $P$; back $B$.

**Parameters.** $(\lambda,\mu_1,\mu_2,\sigma_S,\sigma_L,\rho)$ by MLE on futures log-returns $z_t=H_tx_t$ ($x_t=H_t^{+}z_t$-style inversion; $H_t$ stacks $e^{-\lambda(T_i-t)}\varphi(t)\sigma_S$, $(1-e^{-\lambda(T_i-t)})\sigma_L$); spot $(a_1,a_2,a_3,\kappa,\gamma_1,\alpha_1)$ by regression + Garch(1,1). Seeded by proxies $\sigma_L^2\!\approx$ long-contract (4-year) variance, $\sigma_S^2\!\approx$ prompt-contract variance, $\rho\!\approx$ their empirical correlation.

**Observed effects.** $\sigma_S=0.4580$ $[0.4462,0.4698]$, $\sigma_L=0.1655$ $[0.1617,0.1694]$, $\lambda=0.7896$ $[0.7518,0.8274]$, $\mu_1=0.0246$, $\mu_2=0.0038$, $\rho=0.4113$ $[0.3737,0.4488]$; short-term vol > long-term, winter > summer; EV/IV up to 500% (fast) / 100% (slow); hedge std reduction up to $\approx$10$\times$ (arXiv:1312.3789v1).

**Failure modes.** One-factor spot models with a time-varying $\mu(t)$ are unstable and lose the futures-hedge channel; assuming $S_t=\lim_{T\downarrow t}F(t,T)$ is wrong because futures deliver over a month and at a possibly different location; the deterministic $\mu(t)$ calibration to the initial curve is ill-conditioned.

### 2.2 Fast mean-reverting spike overlay
**Purpose.** Add electricity/gas spikes to the spot so that high-deliverability storage or battery optionality can monetise them.

**Formulas.** $$dY_t=-\beta\,Y_{t^-}\,dt+dZ_t,\quad Y_0=0,\quad Z_t=\sum_{i=1}^{N_t}J_i,$$
with $N_t$ Poisson intensity $\lambda$ and iid jumps $J_i$; explicit solution
$$Y_t=Y_0e^{-\beta t}+\sum_{i=1}^{N_t}e^{-\beta(t-\tau_i)}J_i,\qquad \tilde S_t=\exp\!\big(Y_t^++Y_t^-\big)S_t,$$
where $Y^+$ collects winter/summer (weather-driven) jumps and $Y^-$ the shoulder-month (storage-misjudgement) jumps.

**Inputs.** Spot series used only to estimate/filter the jump law.

**Parameters.** $\beta=300$ (fixed heuristic fast reversion), $\lambda^+=0.8331$, $J^+\!\sim\!N(0.2579,0.3910)$; $\lambda^-=2.9488$, $J^-\!\sim\!N(-0.7624,0.6402)$.

**Observed effects.** Raises the expected simulated cash flow but also its standard deviation; significant gain for fast storage, negligible for slow storage; the historical backtest does not confirm an advantage (arXiv:1312.3789v1).

**Failure modes.** Only monetisable if injection/withdrawal rates are high enough; two-sided because positive spikes cluster in Jan/Feb/Jun and negative spikes in Sep–Nov, so a single-sided jump law is mis-specified; it inflates single-path cash-flow variance.

### 2.3 LSMC swing-option pricing with a consumption grid
**Purpose.** Price daily-delivery swing contracts with both daily and global volume constraints.

**Formulas.** $$W_0=\max_{\mathcal N}E_0\Big[\sum_{i=1}^{n_f}N_{T_i}\big(F_{T_i}(T_i+1,1d)-K\big)\Big],$$
subject to $N_m\le N_{T_i}\le N_M$ and $C_m\le\sum_i N_{T_i}\le C_M$. Grid bounds:
$$U_i=\min\big((C_M-N_m)-(n_f-i),\,i\,N_M\big),\qquad D_i=\max\big((C_m-N_M)-(n_f-i),\,i\,N_m\big),$$
with the admissible consume set
$$\mathcal Q_{T_i}(C^{i-1})=\big\{N\in\mathcal N(C^{i-1})\cap[N_m,N_M]\ :\ C^{i-1}+N\in[C_m,C_M]\big\}.$$
Regression of the continuation value on the day-ahead futures price:
$$f_{T_i}(F;C)=\alpha^i(C)+\beta^i(C)\,F+\gamma^i(C)\,F^2,\qquad y^{(k)}=W_{T_{i+1}}(F^{(k)}_{T_{i+1}},C_{ji}),\quad x^{(k)}=F^{(k)}_{T_i}.$$

**Inputs.** Rolling day-ahead futures $F$; one-month futures for a floating (averaged) strike; PVO quotes for model calibration.

**Parameters.** $N_m,N_M,C_m,C_M$ (e.g. $0/1$ MWh and $12.5/20$ MWh); local-vol $\eta(t,k)$ and mean reversion $a$ (see §2.4).

**Observed effects.** Reference fixed-strike May-2018 gas contract prices: all strategies $7.97$, bang-bang only $7.76$ (out-of-theorem); $8.46=8.46$ (within-theorem), 1 s.e. $0.04$ (arXiv:2001.08906v1).

**Failure modes.** The regression dimension explodes with the number of risk factors; backward and forward phases must use independent path sets to avoid bias; imposing bang-bang is wrong whenever the constraint ratio is non-integer.

### 2.4 Local-volatility linear model for futures with heterogeneous delivery periods
**Purpose.** Calibrate the quoted smile of the one liquid delivery period and imply it for every other delivery period; supply the smile the swing pricer consumes.

**Formulas.** Normalised spot and instantaneous futures price:
$$ds_t=a(t)\big(1-s_t\big)dt+\eta(t,s_t)\,s_t\,dW_t,\quad s_0=1;\qquad f_t(T)=f_0(T)\Big(1+(1-s_t)e^{-\int_t^Ta(u)du}\Big),$$
delivery-period aggregation with weights $w(\tau,\delta)$ on $[T-\delta_1,T-\delta_0]$:
$$F_t(T,\delta)=\int w(u,T,\delta)\,f_t(u)\,du,\qquad
\eta(t,\delta,k)=\frac{1-\tfrac{G(t,\delta)}{1-k/G(t,\delta)}}{k}\,.$$
Dupire-style PDE for normalised calls and the smile-mapping between delivery periods $\delta,\bar\delta$ via $G(t,\delta)=F_0(T,\delta)^{-1}\int w(u,T,\delta)f_0(u)e^{\int_t^u a}\,du$.

**Inputs.** Plain-vanilla options on one delivery period (e.g. 55 PVO on NG TTF one-month futures, 29 Mar 2018); optionally mid-curve (MCO) and calendar-spread (CSO) quotes.

**Parameters.** Constant $a$; non-parametric spline $\eta(t,k)$ fitted by Anderson-accelerated fixed point + asymptotic expansion, iterating $a$ until MCO/CSO are matched.

**Observed effects.** Max calibration error of 0.1 bp within 20 iterations; CSO "volatility drops" reproduce the natural-gas seasonality pattern (arXiv:2001.08906v1).

**Failure modes.** $a$ is not identifiable from vanilla options alone (needs MCO/CSO); spikes were deliberately excluded from the numerical work; higher-dimensional curve/vol extensions break the analytic aggregation.

### 2.5 HDD/CDD degree-day futures, options and sensitivities (CAR($p$))
**Purpose.** Price temperature weather derivatives and compute their local sensitivities.

**Formulas.** $T(t)=\Lambda(t)+Y(t)$, $Y(t)=e_1'X(t)$, $dX(t)=A\,X(t)\,dt+\sigma(t)e_p\,dB(t)$ (eigenvalues $<0$). Indexes
$$\mathrm{CDD}(\tau_1,\tau_2)=\int_{\tau_1}^{\tau_2}\max(T(t)-c,0)\,dt,\qquad \mathrm{HDD}(\tau_1,\tau_2)=\int_{\tau_1}^{\tau_2}\max(c-T(t),0)\,dt,$$
$$F_{\mathrm{CDD}}(t,\tau_1,\tau_2)=\int_{\tau_1}^{\tau_2}\Sigma(t,s)\,\Psi\!\left(\frac{m_\theta(t,s,X(t))-c}{\Sigma(t,s)}\right)ds,\quad \Psi(x)=x\Phi(x)+\Phi'(x),$$
$$m_\theta(t,s,x)=\Lambda(s)+e_1'e^{A(s-t)}x+e_1'\!\int_t^s e^{A(s-u)}e_p\,\theta(u)\,du,\quad \Sigma^2(t,s)=\int_t^s\big(e_1'e^{A(s-u)}e_p\big)^2\sigma^2(u)\,du.$$
Sensitivities:
$$\frac{\partial F_{\mathrm{CDD}}}{\partial x_i}=\int_{\tau_1}^{\tau_2}\Phi\!\left(\frac{m_\theta(t,s,X(t))-c}{\Sigma(t,s)}\right)e_1'e^{A(s-t)}e_i\,ds;\qquad
\widetilde F_{\mathrm{CDD}}=\Theta(t,\tau_1,\tau_2)+a(t,\tau_1,\tau_2)X(t),$$
$$\frac{\partial\widetilde C}{\partial x_i}=e^{-r(\tau-t)}\,\Phi\!\left(\frac{d(t,\tau,\tau_1,\tau_2,\widetilde F_{\mathrm{CDD}}(t))-K}{S(t,\tau,\tau_1,\tau_2)}\right)a(t,\tau_1,\tau_2)e_i .$$

**Inputs.** Daily average temperature series; risk-free rate for option discounting.

**Parameters.** CAR order $p$ and matrix $A$ (with $Ae_1$-structure), $\sigma(t)$, seasonal $\Lambda(t)$, market price of risk $\theta$ (Girsanov); threshold $c=65°$F (or $18°$C). Empirically $p=3$, $\sigma=5.25$, $\theta=0$, measurement day 1 Aug 2011.

**Observed effects.** $\Phi(Z)=1$ for $s-t=1,2$, decays to $0.9924$ by $s-t\ge12$; sensitivities positive, ordered level$\to$slope$\to$curvature by maturity, vanishing at the long end; the approximation dominates the exact derivative (arXiv:2403.00006v1).

**Failure modes.** For measurement-*period* options the payoff is path-dependent in $X(t)$, so the Broadie–Glasserman density approach fails and only the linearised price is differentiable; the linearisation $\Psi(x)\approx x$ (or $\sqrt{1/2\pi}+x/2$) overstates sensitivity.

### 2.6 Battery rolling-intrinsic dispatch (MILP)
**Purpose.** Schedule a BESS across day-ahead auction, intraday auctions and continuous intraday with liquidity-aware spreads.

**Formulas.**
$$\text{SoC}_{i+1}=\text{SoC}_i+\eta^+c_i\Delta t-\frac{d_i\Delta t}{\eta^-},\quad 0\le c_i,d_i\le\bar P,\quad c_i(1-b_i)=0,\ d_i\,b_i=0,\ b_i\in\{0,1\},$$
$$\sum_{i=0}^{N-1}c_i\Delta t\le N^{\max}_{\text{cycles}}\,\text{SoC},\quad \text{SoC}_N=\text{SoC}_0,\qquad
\max_{c_i,d_i,b_i}\ \sum_i\Delta t\big(p_i^b d_i-p_i^a c_i\big).$$
Rolling intrinsic re-solves this at each $t^T_j$ with residual quantities
$$c^r_i=\max(c_i-\bar c_i,0)+\max(\bar d_i-d_i,0),\qquad d^r_i=\max(d_i-\bar d_i,0)+\max(\bar c_i-c_i,0),$$
using empirical-quantile bid/ask from trade buckets $\mathcal P_{i,j}=\{p_{i,t}\mid t^T_{j-1}<t\le t^T_j\}$:
$$p^b_{i,j}=q_k(\mathcal P_{i,j})\ \text{if}\ |\mathcal P_{i,j}|\ge N\ \text{else}\ -4000,\qquad p^a_{i,j}=q_{-k}(\mathcal P_{i,j})\ \text{else}\ +4000.$$

**Inputs.** Day-ahead auction prices; intraday auction prices; trade-level continuous intraday prices (for bid/ask); EPEX indices only as (non-tradeable) benchmarks.

**Parameters.** $\bar P$, SoC, $\eta^\pm$; $N^{\max}_{\text{cycles}}$; bucket size (5 min) and threshold $N=10$; bid/ask quantiles 20%/80%; $\Delta t=1$ (DA) / $0.25$ (ID).

**Observed effects.** 2h battery: DA €228.75/day, ID ROLL €296.60, DA$|$ID AUCT$|$ID ROLL €339.15; 15-min €296.60 vs 1h €240.43; 5$\to$30 min $-$14%; medians vs means show heavy right tails; 1/2/4 daily cycles €340.93/€466.16/€559.13 (arXiv:2510.01956v2).

**Failure modes.** Index-based (ID1/ID3/IDFULL/AEP) backtests overstate profit and ignore bid-ask; results depend on bucket definition and quantiles; single-market strategies lose the non-execution hedge.

### 2.7 Carbon 2-SVJ pricing with a three-risk-premium kernel and HAR-CJ indirect inference
**Purpose.** Price EUA futures options with two variance factors plus jumps and estimate both physical and risk-neutral parameters from high-frequency data.

**Formulas.** Historical dynamics (2-SVJ):
$$dX_t=\mu(\sigma_{1,t},\sigma_{2,t})dt+\sigma_{1,t}dW^{X}_{1,t}+\sigma_{2,t}dW^{X}_{2,t}+c_X\,dJ_t,\quad d\sigma^2_{j,t}=\kappa_j(\omega_j-\sigma^2_{j,t})dt+\Lambda_j\sigma_{j,t}dW^{\sigma_j}_{j,t},$$
$\mathrm{corr}(dW^X_j,dW^{\sigma_j}_j)=\rho_j$, $J$ Poisson intensity $\lambda$, $c_X\sim N(\mu_J,\sigma_J^2)$. Exponential-affine pricing kernel
$$M_t=M_0\exp\!\Big(\phi(\log p_t-\log p_0)+\!\int_0^t\!\delta\,ds+\psi_1(\sigma^2_{1,t}-\sigma^2_{1,0})+\psi_2(\sigma^2_{2,t}-\sigma^2_{2,0})\Big),$$
giving the risk-neutral map
$$\kappa_j^\ast=\kappa_j-\phi\rho_j\Lambda_j-\psi_j\Lambda_j^2,\qquad \omega_j^\ast=\omega_j\frac{\kappa_j}{\kappa^\ast_j},\qquad \lambda^\ast=\lambda E[e^{\phi c_X}],\qquad c_X^\ast\sim N(\mu_J+\phi\sigma_J^2,\sigma_J^2).$$
Closed-form CF (affine) feeds a Fourier/SINC pricer; estimation uses LHAR-CJ auxiliaries, e.g. $\log \widehat{RV}^{(h)}_{t+h}=c+\beta^{(d)}x^{(d)}_t+\beta^{(w)}x^{(w)}_t+\beta^{(m)}x^{(m)}_t+\gamma^{(d)}r^-_t+\gamma^{(w)}r^-_{t}+\varepsilon$, with indirect inference mapping structural $\to$ auxiliary coefficients.

**Inputs.** Tick-by-tick futures (ECFZ December contract) and options on futures (IV, volume, bid-ask); 5-min returns for RV and the continuous/jump (CJ) split.

**Parameters.** $\kappa_1=0.039$/day, $\kappa_2=2.03$/day, $\omega$ targeted as half the mean continuous QV, $\Lambda_1=0.0083$, $\Lambda_2=0.032$ (targeted), $\rho_1=-0.82$, $\rho_2=-0.11$, $[\lambda]=0.72$, $[\mu_J]=-7.9\text{e-}3$, $[\sigma_J]=8.5\text{e-}3$; risk premia $\phi=-7.35\text{e-}3$, $\psi_1=2.81\text{e-}3$, $\psi_2=1.50\text{e-}2$; IV via Black(1976); $r=q=0$.

**Observed effects.** RV mean 9.6% ($\approx$49.5% annualised), kurtosis 64.9; two factors required (one-factor SV cannot match HAR); adding jumps marginally improves fit; RMSE$_{IV}$ 19.80/11.96/11.33 ($m<0.85$/$0.85\le m\le1.1$/$m>1.1$) vs LHARG-ARJ 19.25/11.17/10.12 (arXiv:2501.17490v2).

**Failure modes.** One-factor SV cannot reproduce HAR coefficients in the EU ETS; indirect inference requires intraday data and careful variance targeting; jump parameters are only identifiable because intraday jump counts/sizes are observed; the variance-risk premia remain optimised (not arbitrage-pinned); carbon option liquidity is thin.

### 2.8 Commodity rough volatility (rBergomi/rHeston) with a Samuelson-consistent mean reversion
**Purpose.** Jointly calibrate commodity futures-option smiles across maturities while reproducing the Samuelson effect.

**Formulas.** General forward-variance model on the normalised fictitious spot:
$$ds_t=\big(a(t)+(\beta(t)-\partial_t\ln F_0(t))s_t\big)dt+\sqrt{\xi_{tt}}\,s_t\,dW^1_t,\qquad d\xi^u_t=\lambda(t,u)\,dW^2_t,$$
with $F_t(T)=F_0(T)\big(1+(1-s_t)e^{-\int_t^T A(u,\cdot)du}\big)$. rBergomi:
$$v_t=\xi_0(t)\exp\!\Big(-\tfrac{\eta^2}{2}t^{2H}+\eta\sqrt{2H}\int_0^t (t-s)^{H-1/2}dW^2_s\Big),$$
rHeston:
$$v_t=V_0+\int_0^t\frac{\kappa(\bar v(s)-v_s)}{\Gamma(H+0.5)(t-s)^{0.5-H}}ds+\int_0^t\frac{\eta\sqrt{v_s}}{\Gamma(H+0.5)(t-s)^{0.5-H}}dW^2_s .$$
Cost function with liquidity weighting:
$$L(\Theta)=\sum_i\Big[\sum_{j\in J_i}\omega_{i,j}\big|\sigma^{\mathrm{mkt}}_{i,j}-\sigma^{\mathrm{m}}_{i,j}\big|+\mathbb 1_{|\sigma^{\mathrm{mkt}}-\sigma^{\mathrm{m}}|>0.03}\sum_{j\in J_i}\omega_i\big|\sigma^{\mathrm{mkt}}_{i,j}-\sigma^{\mathrm{m}}_{i,j}\big|\Big],\quad \omega_{i,j}=\frac{\mathrm{vol}_{i,j}}{\max(0.01,BA_{i,j})}.$$
Hurst estimation:
$$m(q,\Delta)=\frac1N\sum_{k=1}^N\big|\log RV_{k\Delta}-\log RV_{(k-1)\Delta}\big|^q\ \propto\ \Delta^{Hq},\quad \text{regress } \log m(q,\Delta)\ \text{on}\ \log\Delta.$$

**Inputs.** WTI futures-option quotes (IV, volume, bid-ask); 5-min returns (from 10-s bins) for $H$; piecewise-linear $\xi_0(t)$ calibrated by ATM bisection.

**Parameters.** $a=0.5$ fixed; fitted rBergomi $H=0.0778$, $\eta=2.1617$, $\rho=-0.3087$ (14 Mar 2025) and $H=0.0460$, $\eta=2.5600$, $\rho=-0.2110$ (4 Jun 2025); rHeston $H=0.2774/0.3214$, $\eta=2.0567/2.7121$, $\rho=-0.2017/-0.1677$, $\kappa=5.6187/4.5931$; classical Bergomi $\eta=16.50/14.64$, Heston $\eta=9.97/13.38$.

**Observed effects.** $H\in[0.14,0.21]$ for WTI (consistent with the literature's $0.153$); rough models beat classical ones on joint smile fit; the Samuelson effect strengthens with $a$ and vanishes at $a=0$ (arXiv:2603.26514v1).

**Failure modes.** $a$ is unidentifiable from vanillas (0.3–0.7 all fit); the piecewise-linear $\xi_0(t)$ is not in the admissible rHeston set (practical approximation); the very short first maturity needs a dual mesh; Euler-Maruyama shows instabilities for the classical models.

## 3. Data requirements → available endpoints

| Input | Endpoint | Category | Provider | Probe status |
|---|---|---|---|---|
| Natural-gas spot (Henry Hub daily) | **gap** — no commodity spot feed in the inventory | — | — | gap — must be sourced externally |
| NYMEX/ICE gas futures curve (monthly, 24–72 maturities) | **gap** — no futures/commodity feed | — | — | gap |
| Power day-ahead auction prices (EPEX/PJM) | **gap** — no power-market feed | — | — | gap |
| Continuous intraday power trades (15-min, bid/ask) | **gap** — no tick/intraday power feed | — | — | gap |
| Commodity futures options (WTI/NG: IV, volume, bid-ask) | **gap** — no commodity option feed | — | — | gap |
| Carbon allowance futures & options (EUA/ICE ECF, 5-min) | **gap** — no carbon/EU-ETS feed | — | — | gap |
| Daily average temperature (HDD/CDD inputs) | **gap** — no weather feed; must be sourced externally | — | — | gap |
| 5-min intraday futures returns for RV / continuous-jump split | **gap** — no certified 5-min intraday series; `twelvedata` `interval` and `massive` aggregates are the only equity-only candidates and need verification | — | — | gap |
| Risk-free discount curve (option discounting, carry) | `https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2026/all` | risk_free_curve | federal_reserve | ok |
| Macro state (rates, energy/inflation for carry and carbon regressions) | `https://api.stlouisfed.org/fred/series/observations` | macro_data | fred | ok |
| Equity OHLCV (proxy series for cross-asset / carbon-premium regressions) | `https://eodhd.com/api/eod/AAPL` | core_stock_apis | eodhd | ok |
| Daily OHLCV (alt proxy source) | `https://api.tiingo.com/tiingo/daily/AAPL/prices` | core_stock_apis | tiingo | ok |
| Equity options surface / model-free implied vol (SPX) as an equity-vol anchor | `https://cdn.cboe.com/api/global/delayed_quotes/options/_SPX.json` | options_surface | cboe | ok |
| Equity option chain (implied-vol / skew inputs) | `moomoo://get_option_chain` | options_data | moomoo | gateway — local OpenD gateway |
| Expected move (implied, from option chain) | `moomoo://get_option_underlying_overview` | expected_move | moomoo | gateway — local OpenD gateway |
| Corporate actions (dividends; carry adjustments for equity proxies) | `https://eodhd.com/api/div/AAPL` | corporate_actions | eodhd | ok |
| News flow for carbon "open information" tests | `https://eodhd.com/api/news` | news_data | eodhd | ok |
| Global news tone (GDELT, carbon-pricing hypotheses) | `https://api.gdeltproject.org/api/v2/doc/doc` | news_sentiment | gdelt | fail — HTTP 429 rate_limited |
| Company emissions / filings (carbon-premium studies) | `https://data.sec.gov/submissions/CIK0000320193.json` | sec_filings | sec_edgar | ok |
| Technical indicators (volatility proxies) | `https://www.alphavantage.co/query` | technical_indicators | alpha_vantage | ok |
| Local-gateway quotes/klines (proxy series) | `moomoo://get_market_snapshot` | core_stock_apis | moomoo | gateway — local OpenD gateway |

## 4. Pitfalls, validation and measurement

- **Model risk can exceed strategy risk.** Storage valuation uncertainty is dominated by the *spot* specification; seasonal spreads have narrowed so the intrinsic (futures-only) number understates the book, and the paper explicitly recommends quantifying the model family rather than only polishing the trading strategy (arXiv:1312.3789v1).
- **Cont-style model-risk band.** Build $\Gamma$ by perturbing the MLE parameters with their covariance matrix, keep only perturbations whose inferred Garch(1,1) noise passes a Kolmogorov–Smirnov normality test at the chosen level and whose likelihood is within $L(\theta_i)>(1-\epsilon)L(\theta^\star)$, then report $\pi(H)=\max_{Q\in\Gamma}E_Q[H]-\min_{Q\in\Gamma}E_Q[H]$ as the uncertainty on the storage value (arXiv:1312.3789v1).
- **Non-convergence of futures to spot.** Any model that sets $S_t=\lim_{T\downarrow t}F(t,T)$ mis-measures the basis between spot and prompt; the corpus recommends a separate, correlated spot process with the prompt as mean level, because spot carries extra weather/idiosyncratic noise (arXiv:1312.3789v1).
- **Do not impose bang-bang.** Verify Bardou et al.'s integrality condition on $(C_m,N_m,N_M,C_M)$ before restricting to min/max consumption; otherwise the price is biased low (arXiv:2001.08906v1).
- **Independent backward/forward paths.** The Longstaff–Schwartz estimate of the optimal strategy must be evaluated on a freshly simulated path set, or the price is upward-biased through in-sample regression (arXiv:1312.3789v1, arXiv:2001.08906v1).
- **Non-identifiability of mean reversion.** Vanilla futures options cannot pin the Samuelson parameter $a$ (0.3–0.7 all fit); identify it from mid-curve/calendar-spread options, or fix and disclose it rather than reporting a spurious estimate (arXiv:2603.26514v1, arXiv:2001.08906v1).
- **Prefer two variance factors with jumps in carbon.** A one-factor SV model fails the HAR-moment matching that defines identifiability; adding jumps improves the fit only marginally, so treat the jump component as optional but the second factor as required (arXiv:2501.17490v2).
- **Calibration-loss design matters.** Weight each option by trading volume over bid-ask and add a penalty when $|\sigma^{\mathrm{mkt}}-\sigma^{\mathrm{m}}|>0.03$, otherwise ATM-dominated fits hide large ITM/OTM errors (arXiv:2603.26514v1).
- **Moneyness/maturity bucketing.** Report pricing error by moneyness *and* maturity: carbon errors peak for deep-OTM puts ($m<0.85$: RMSE$_{IV}\approx19.8$) and are smallest near ATM (arXiv:2501.17490v2). Use the same protocol (e.g. RV MSE/MAE/QLIKE for the RV leg, IV-RMSE for the option leg).
- **Look-ahead / in-sample leakage.** The surrogate HV/indirect-inference loop must simulate then refit auxiliaries each iteration (never fit auxiliaries on the same path used for the pricing test); one-day-ahead RV forecasts must re-estimate with an expanding window ending at $t-1$, forecast only $t{+}1$ (arXiv:2501.17490v2). For the intraday battery strategy, bid/ask quantiles are built from *preceding* buckets only (arXiv:2510.01956v2); trading indices (ID1/ID3/IDFULL/AEP) are ex-post and must never be used as tradeable inputs.
- **Statistical soundness checks.** Residual diagnostics (Ljung–Box, ARCH–LM) on the spot Garch noise; Kolmogorov–Smirnov normality for the model family; Diebold–Mariano/Model Confidence Set when comparing spot models or option pricers; report the extrinsic/intrinsic ratio and the hedge standard-deviation-reduction factor as the two headline storage metrics (arXiv:1312.3789v1, arXiv:2501.17490v2, arXiv:2510.01956v2).

## 5. Recommended first implementation in FinRobot

1. **Discounting and carry plumbing for energy contracts (S).** A shared curve object that reads the daily Treasury curve and builds discount factors and simple cost-of-carry/convenience-yield placeholders. Data: `risk_free_curve` (`federal_reserve`), `macro_data` (`fred`). Value: every derivative in this category needs discounting and a deterministic carry proxy before a commodity curve feed exists. Risk: commodity-specific carry (storage/financing) cannot be inferred from Treasuries alone and must be treated as a parameter.
2. **Storage & swing LSMC engine on a species-agnostic curve object (M).** One Longstaff–Schwartz solver that drives both the gas-storage control problem (§2.1) and the swing consumption control with daily/global constraints (§2.3), parameterised over the curve and spot models. Data: none required to build — validate on synthetic Seasonal-Gabillon paths. Value: unblocks storage valuation, swing pricing and futures-based hedging deltas from a single tested core. Risk: regression dimension and the volume grid; keep risk factors low and impose the bang-bang check as a test, not an assumption.
3. **HDD/CDD CAR($p$) weather derivatives module (M).** Implement the closed-form CAR($p$) futures price, the linearised call, and the sensitivity vector of §2.5; fit $A,\sigma,\Lambda,\theta$ to any supplied temperature series. Data: temperature series (currently a `gap`; unit-test on simulated CAR paths). Value: complete weather/degree-day pricing with analytic Greeks, independent of every market feed FinRobot lacks. Risk: the linearised Greeks are upper bounds; the period-option sensitivity is only available numerically.
4. **Fast mean-reverting spike overlay (S).** The Hambly-style jump process of §2.2 as a plug-in on top of the spot used by items 2 and 5. Data: spot series for jump-law filtering (parameter defaults from arXiv:1312.3789v1 are usable until a gas/power feed exists). Value: adds the spike optionality that drives fast storage and battery value. Risk: inflates single-path cash-flow variance and must be modelled two-sided (positive winter/summer, negative shoulder).
5. **Battery rolling-intrinsic dispatch MILP (M).** The SoC MILP plus the rolling re-solve with quantile bid/ask of §2.6. Data: day-ahead/intraday power prices (currently a `gap`; drive on synthetic or substitute prices until a power feed is wired). Value: the highest-value, most directly implementable energy-asset strategy in the corpus, with quantified sensitivity to trading frequency and cycle limits. Risk: results hinge on bid/ask construction and bucket granularity; never report index-based backtests as tradeable.
6. **Carbon 2-SVJ pricer with three-risk-premium kernel and HAR-CJ indirect inference (L).** Section 2.7 end-to-end: RV/CJ construction from 5-min returns, LHAR-CJ auxiliaries, indirect inference to the 2-SVJ, risk-neutral map, Fourier/SINC pricing and IV calibration. Data: 5-min carbon futures and EUA options (both `gap`). Value: the only corpus-validated route to carbon option pricing with estimated risk premia; also reusable for any two-factor-plus-jump commodity. Risk: data-gated and computationally heavy; variance-targeted parameters and a one-factor fallback would mis-specify the market.
7. **Commodity rough-volatility calibration (L).** rBergomi/rHeston of §2.8 with the Samuelson-consistent $a(t)$ and the volume/bid-ask-weighted loss. Data: commodity futures options and 5-min returns (`gap`). Value: the corpus' best-fitting commodity surface model and a documented Samuelson/seasonality decomposition. Risk: $a$ non-identifiable from vanillas and the classical-model calibrations need implausible $\eta$; gate behind a real commodity option feed and keep classical Bergomi/Heston as the disclosed fallback.

## Appendix — papers read

| arXiv id | title | year |
|---|---|---|
| 2603.26514v1 | Rough volatility dynamics in commodity markets | 2026 |
| 2510.01956v2 | Rolling intrinsic for battery valuation in day-ahead and intraday markets | 2025 |
| 2501.17490v2 | Pricing Carbon Allowance Options on Futures: Insights from High-Frequency Data | 2025 |
| 2403.00006v1 | Local sensitivity analysis of heating degree day and cooling degree day temperature derivatives prices | 2024 |
| 2001.08906v1 | Pricing commodity swing options | 2020 |
| 1312.3789v1 | Gas storage valuation and hedging. A quantification of the model risk | 2013 |
