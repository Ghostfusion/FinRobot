# Optimal Execution & Liquidation — learnings from the q-fin.TR corpus

`244` of 2370 corpus papers matched this category (241 with PDFs); this doc is based on a close reading of `6`.

Headline: **this category is the *scheduling and control* problem, and its interface is coarse.**
The corpus splits cleanly into (a) closed-form optimal-control schedules that take a daily volume
curve, an impact pair $(\theta,\eta)$ and a risk/performance objective — implementable today from
daily+intraday bars — and (b) impact-aware RL and execution-flow triggers that need a book or a
full trade tape. `../qfin-st/microstructure-execution.md` already derives the square-root impact law
and the L3 requirement; this doc does not re-derive impact *magnitude*, it derives *how to schedule
against it* and what a schedule costs. Link:
[`../qfin-st/microstructure-execution.md`](../qfin-st/microstructure-execution.md).

## 1. What the corpus actually offers

- **VWAP schedules have a closed form, and permanent impact bends them forward.** With a general
  permanent impact $f$, temporary cost $L(\rho)=\eta|\rho|^{1+\phi}$ and a *deterministic* volume
  curve $V_t$, the optimal curve is solved as a Hamiltonian system (arXiv:1306.2832); with **no**
  permanent impact the optimum *is* the relative market-volume curve, and with linear permanent
  impact $f=k$ plus quadratic cost $L(\rho)=\eta\rho^2$ it is
  $q^*(t)=q_0(1-t/T)-q_0w(t)$ with $w\ge0$ (arXiv:1306.2832). The punchline for pricing: the
  guaranteed-VWAP premium on the paper's calibration ($S_0=50$, $q_0=4\times10^5$, $V=4\times10^6$,
  $\sigma=0.45$, $\eta=0.15$, $k=5\times10^{-7}$, $T=1$ day) falls from **3 bps under a naive linear
  curve to $-3.2$ bps** ($\gamma=3\times10^{-6}$) and **$-1.3$ bps** ($\gamma=6\times10^{-6}$) under
  the optimum — i.e. the broker profitably *pushes the VWAP down* by front-loading (arXiv:1306.2832).
- **Impact is deterministic-intraday, and time variation can break the problem.** Temporary and
  permanent impact coefficients for Microsoft in June 2021 follow a J-shaped intraday path; the
  permanent coefficient for 2021-06-10 varies materially within the day (arXiv:2410.04867). In the
  time-varying Almgren–Chriss model the cost is the quadratic form $\tfrac12\xi^\top A\xi$ and the
  optimal *static* trade vector is $\xi^\star=-Q\,A^{-1}{\bf1}/({\bf1}^\top A^{-1}{\bf1})$ when $A$ is
  **symmetric positive definite** (unique minimiser); only a **B-matrix** structure additionally
  guarantees monotone (no buy-back) liquidation, i.e. strong well-posedness (arXiv:2410.04867).
- **The threshold is quantitative.** A sell program with $N$ slices is strongly well-posed (unique,
  monotone, no transaction-triggered manipulation) whenever $2\eta_i>\sum_{j<i}\theta_j+(N-i)\theta_i$,
  and under non-increasing $\theta$ whenever $2\underline{\eta}\ge N\theta_1-(N-1)\theta_N$
  (arXiv:2410.04867). In continuous time the **admissibility condition** is
  $2\eta(t)\ge\int_0^t (T-s)\,(-\dot\theta(s))\,ds$ — temporary impact must dominate the
  remaining-horizon-weighted cumulative decay of permanent impact (arXiv:2410.04867).
- **Violate it and the schedule oscillates or blows up.** With constant $\eta$ and *linearly
  decreasing* $\theta_t=a+bt$ ($b<0$), $\zeta_t\propto\sin(\sqrt{|\gamma|}(T-t))/\sin(\sqrt{|\gamma|}T)$;
  the paper's Example 6 reports manipulation onset at a critical slope $|b|>\pi^2\eta/(2T^2)$ and no
  solution at the resonant values $|b|=2n\pi^2\eta/T^2$ (arXiv:2410.04867). A 3-slice counterexample has $A$ fail to
  be SPD for $\eta_3<17/15$ with $\theta=(1,3,2),\eta=(2,2,\eta_3)$, turning the problem into an
  unbounded saddle (arXiv:2410.04867).
- **A target-performance remuneration flips the schedule from linear to exponential.** Under
  $\max_v \Pr(\text{hit }h\text{ before }k)$ on performance $Y=X+Q(S-\gamma Q)$, the optimum is
  $v^*(t)=\frac{2\gamma-b}{2l}Q^*(t)$ with $Q^*(t)=e^{\frac{b-2\gamma}{2l}t}Q_0$ — an
  **exponential** decay, versus the classical **linear** Almgren–Chriss inventory; the value function
  is $\frac{e^{-\lambda y}-e^{-\lambda k}}{e^{-\lambda h}-e^{-\lambda k}}$ with
  $\lambda=\frac{(2\gamma-b)^2}{2l\sigma^2}$ (arXiv:2505.15611). The optimal fraction is independent of
  $\sigma$ and of the two barriers (arXiv:2505.15611).
- **Shortermism, not excessive risk: the probabilities are extreme.** At the paper's baseline
  ($b=l=0.001$, $\gamma=0.1$, $\sigma=0.1$, $\pm5\%$ barriers, 10,000 paths, $T=1$) the target
  schedule hits the upper barrier with probability **50.9%**, the lower barrier **0%**, and ends
  between them **49.1%**; the classical schedule hits upper **81.6%**, lower **9.2%**, between
  **9.2%** (arXiv:2505.15611). Short-horizon mean/variance: at $t=0.02$ the target schedule gives mean
  $1.04709$ / variance $2\times10^{-5}$ vs classical $1.03149$ / $1.5\times10^{-4}$; by $t=0.10$ the
  classical mean ($1.05062$) overtakes it ($1.04741$) — the reversal is the shortermism
  (arXiv:2505.15611).
- **Impact-aware RL beats simple schedules, and the edge scales with the deadline.** On BTC-USD
  replays (train Jan-2020, test Feb-2020, 27 days, 10 intra-day starts/day aggregated to a daily
  score) a PPO agent on depth-20 1 s books beats TWAP and a book-liquidity VWAP proxy on identical
  timestamps and costs by **+2.25 / +2.68 bps at 1,800 s**, **+7.59 / +7.70 bps at 3,600 s**, and
  **+22.96 / +23.02 bps at 7,200 s**, all one-sided Wilcoxon significant after Benjamini–Hochberg
  ($p_{\rm adj}<0.01$), win rates 67–70% / 85–89% / 96%, Cohen's $d$ 0.63–0.74 / 0.92–0.94 / 1.61–1.63
  (arXiv:2511.07434). At 30 min a +2–3 bps edge is **\$200–\$300 per \$1,000,000** program after fees,
  latency and transient impact (arXiv:2511.07434).
- **Trader inventories are Itô, not differentiable.** On TSX data for 10 stocks and all listed
  traders, Jan-2010 to Oct-2020, at 5-minute regular sampling the null of *no* Brownian component in
  the inventory is rejected on **98–100% of days** for the tracked active traders (e.g. Trader #5
  100.0% on all ten names), and similarly for the wealth process; asynchronous observation gives
  **81.9–100%** rejection (arXiv:2104.14615). The fictitious-process test is sensitive to the added
  Brownian scale $\sigma'$ (reject for $\sigma'\lesssim700$ in inventory, $\lesssim6\times10^4$ in
  wealth) and to the truncation level $\varkappa\ge3$ (arXiv:2104.14615).
- **Execution *flow* $I=dV/dt$, not traded volume, localises price singularities.** For AAPL on
  2012-09-20 the volume histogram peaks at $P\approx698$ (median) with **no** price singularity there,
  while $I_0(P)$ spikes at the 694 and 700 levels where the price actually jumps; the same holds on
  2025-04-01 (594,673 transactions) (arXiv:2511.01471). Liquidity oscillates over **several orders of
  magnitude** while same-day price changes are ~1% (arXiv:2511.01471).
- **Off-topic note:** none of the six is off-topic. arXiv:2511.01471 is the weakest *fit* to
  "scheduling/liquidation" (it is a signal-construction paper, primary category `q-fin.CP`) but is
  retained because it supplies the only *timing* variable — expected future execution flow — that a
  scheduler can act on, and it is tagged `q-fin.TR`.

## 2. Implementable formulas & algorithms

### 2.1 Guaranteed-VWAP optimal schedule and premium
**Purpose.** Produce the liquidation curve that tracks a volume benchmark, and price a
guaranteed-VWAP contract (the minimum premium at which a broker breaks even).

**Formula.** Inventory $q_t=q_0-\int_0^t v_s\,ds$, price with permanent impact
$dS_t=\sigma dW_t-f(|q_0-q_t|)v_t\,dt$, cash
$X_T=q_0S_0-\int_0^{q_0}F(z)dz-\int_0^T V_tL(v_t/V_t)dt+\int_0^T q_t\sigma dW_t$ with
$F(q)=\int_0^q f(|z|)dz$. CARA premium by indifference pricing:
$$\pi(q_0)=\frac{1}{\gamma}\log\!\Big(-\sup_{v\in\mathcal A}\mathbb E\big[-\exp(-\gamma(X_T-q_0\,\mathrm{VWAP}_T))\big]\Big),\qquad
w(t)=\frac{k}{\gamma\sigma^2T}2\sinh\!\Big(\sqrt{\tfrac{\gamma\sigma^2V}{2\eta}}\,t\Big)\Big[\tanh\!\Big(\sqrt{\tfrac{\gamma\sigma^2V}{2\eta}}\,\tfrac T2\Big)-\tanh\!\Big(\sqrt{\tfrac{\gamma\sigma^2V}{2\eta}}\,\tfrac t2\Big)\Big]$$
Deterministic-volume optimum: $\inf_v \int_0^T V_tL(v_t/V_t)dt-q_0\int_0^T\frac{V_t}{Q_T}F(q_0-q_t)dt+\frac{\gamma}{2}\sigma^2q_0^2\int_0^T(\frac{q_t}{q_0}-1-\frac{Q_t}{Q_T})^2dt$,
solved as a 1st-order Hamiltonian system and, in general, by a Newton iteration on
$\{p_{j+1}=p_j+\tau[\gamma\sigma^2(q_{j+1}-q_0(1-Q_{j+1}/Q_J))+q_0V_{j+1}f(|q_0-q_{j+1}|)],\;q_{j+1}=q_j+\tau V_{j+1}H'(p_j)\}$.
Risk-neutral closed form: $q^*(t)=q_0(1-\frac tT)(1-\frac{kVt}{4\eta})$, $\pi(q_0)=\frac{\eta}{VT}q_0^2-\frac{k^2VT}{48\eta}q_0^2$.

**Required inputs.** $q_0$ shares; relative intraday volume curve $V_t$ (only $Q_t/Q_T$ enters the
*strategy*); $Q_T$ total forecast (enters the *premium*); $\sigma$; permanent $f$ (or slope $k$);
temporary cost $L$ (or $\eta$); risk aversion $\gamma$.

**Parameters & defaults.** $L(\rho)=\eta|\rho|^{1+\phi}$ with $\phi>0$ (paper uses $\phi=0.63$,
$\eta=0.12$ for the general numerical case and $\eta=0.15$ for quadratic); $k=5\times10^{-7}$
(linear), or $f(q)=k\alpha q^{\alpha-1}$ with $k=2.2\times10^{-4},\alpha=0.6$ (nonlinear);
$\gamma\in\{3\times10^{-6},6\times10^{-6}\}$; grid $J$ slices, Newton with the TWAP curve
$q^0_j=q_0(1-Q_j/Q_J)$ as the initial guess.

**Observed effect sizes.** Naive-curve premium 3 bps → optimal $-3.2$ / $-1.3$ bps (arXiv:1306.2832);
the reduction term $-\!\int_0^T\![q_0^2w'^2-\frac\eta V q_0w'+\frac{k\gamma\sigma^2}{T}q_0^2w^2]dt>0$.

**Failure modes.** Ignoring permanent impact makes the curve coincide with the volume profile, which
is *wrong* when $k$ is large (front-loading and, at extreme $k$, overselling); the deterministic
volume assumption is only safe because the *relative* curve is stable day-to-day (witching days are
the documented exception); the premium uses a *forecast* of $Q_T$, and the whole construction cannot
see feedback from other participants.

### 2.2 Time-varying impact: well-posedness and manipulation feasibility check
**Purpose.** Decide whether a proposed time-varying impact calibration yields a usable (unique,
non-oscillating, monotone) liquidation schedule before optimising.

**Formula.** Impact matrix
$$A=\begin{bmatrix}2\eta_1&\theta_1&\cdots&\theta_1\\ \theta_1&2\eta_2&\theta_2&\cdots\\ \vdots&&\ddots&\vdots\\ \theta_1&\theta_2&\cdots&2\eta_N\end{bmatrix},\qquad
\xi^\star=-Q\,\frac{A^{-1}{\bf1}}{{\bf1}^\top A^{-1}{\bf1}}$$
$A$ SPD $\Rightarrow$ unique minimiser and $\mathbb E_0[IS]$ convex (TWAP is optimal iff
$\eta>\theta/2$; for $\eta<\theta/2$ the *worst* strategy is TWAP). Strong well-posedness (monotone
liquidation, hence no negative transaction cost) holds if $A$ is a **B-matrix**:
$\sum_k a_{ik}>0$ and $a_{ii}>\frac1N\sum_k a_{ik}\;\forall i$. Closed sufficient condition under
non-increasing $\theta$: $2\underline\eta\ge N\theta_1-(N-1)\theta_N$. Continuous-time admissibility:
$$2\eta(t)\ \ge\ \int_0^t (T-s)\big(-\dot\theta(s)\big)\,ds\quad\text{for all }t,\qquad\text{and}\qquad \sqrt{\gamma}\,T<\pi,\quad \gamma=\frac{\bar\theta}{2\bar\eta},\ \bar\theta=\max_{[0,T]}\{-\dot\theta_t,0\},\ \bar\eta=\min_{[0,T]}\eta_t$$
$\sqrt{\gamma}T<\pi\Rightarrow$ the extremal point is a maximum (weakly well-posed) and the inventory
stays non-negative.

**Required inputs.** Sampled temporary $\eta_i$ and permanent $\theta_i$ coefficients (per slice);
horizon $T$; slice count $N$; initial inventory $Q$.

**Parameters & defaults.** $N$ slices over $[0,T]$; sampling $\eta^{(N)}_i=\eta(t_{i-1})/\Delta t$,
$\theta^{(N)}_i=\theta(t_{i-1})$; shooting method (dichotomy on initial velocity) for the BVP
$2\eta_t\ddot\zeta+2\dot\eta_t\dot\zeta-\dot\theta_t\zeta=0$, $\zeta_0=Q,\zeta_T=0$; exponential
parameterisation $\theta_t=\beta_p e^{-\alpha_p t/T}$, $\eta_t=\beta_{tp}e^{-\alpha_{tp}t/T}$; the
paper's admissibility boundary $\alpha_p<2\kappa\pi^2e^{-\alpha_{tp}}$ with
$\beta_{tp}=T\kappa\beta_p$.

**Observed effect sizes.** Well-posedness/strong-well-posedness transition in the
$(\alpha_p,\alpha_{tp})$ plane is a near-power-law curve; as $\kappa=\eta_0/\theta_0$ grows from 0.1
to 10 the transaction-triggered-manipulation (red) region shrinks and the admissible region becomes
almost entirely monotone-concave; expected implementation shortfall is positive everywhere in the
admissible region (arXiv:2410.04867).

**Failure modes.** Diagonal dominance is *not* necessary and the naive condition $\eta_i>\theta_i/2$
is neither necessary nor sufficient once $\theta$ varies; B-matrix and diagonal dominance are
incomparable classes, so checking only one under-detects ill-posedness; a calibrated *smooth* impact
curve must still pass the check on the **refined** grid actually used, else the discrete
optimiser can produce a buy-sell round trip.

### 2.3 Target-performance (barrier) execution schedule
**Purpose.** Model a broker paid to reach a performance barrier without ruining, and quantify the
schedule/risk consequences of that contract.

**Formula.** Performance $Y(t)=X(t)+Q(t)(S(t)-\gamma Q(t))$, dynamics
$dQ=-v\,dt,\ dS=-bv\,dt+\sigma dW,\ \hat S=S-lv$; objective
$\sup_v\Pr(\tau_h<\tau_k)$ with $\tau_a=\inf\{t:Y(t)=a\}$. Optimal control (P1):
$$v^*(t)=\frac{2\gamma-b}{2l}Q^*(t),\qquad Q^*(t)=e^{\frac{b-2\gamma}{2l}t}Q_0,\qquad
J(y)=\frac{e^{-\lambda y}-e^{-\lambda k}}{e^{-\lambda h}-e^{-\lambda k}},\quad \lambda=\frac{(2\gamma-b)^2}{2l\sigma^2}$$
Classical finite-horizon benchmark (P0): $v^*=\frac{b-2\gamma}{2l+(2\gamma-b)(T-t)}Q^*$, i.e. linear
inventory $Q^*(t)=Q_0\frac{2l+(2\gamma-b)(T-t)}{2l+(2\gamma-b)T}$. A running-penalty variant
(P1$'$) adds $-\phi\int_0^t Q(u)^2du$ and yields $\lambda=\frac{(-b+2\gamma)^2-4l\phi}{2l\sigma^2}$.

**Required inputs.** $Q_0$; linear permanent $b$ and temporary $l$ coefficients; slippage/inventory
cost $\gamma$; $\sigma$; barriers $k<h$; the strategy is *independent* of $S$ and $\sigma$.

**Parameters & defaults.** $b=l=0.001$, $\gamma=0.1$, $\sigma=0.1$, $Q_0=Y_0=1$, barriers
$0.95/1.05$ (also a wide $0.5/1.5$ case), $T=1$, 10,000 Monte Carlo paths; HJB ansatz
$J(y)=Ce^{-\lambda y}+D$.

**Observed effect sizes.** Success/ruin/between probabilities P1 **50.9 / 0.0 / 49.1%** vs P0
**81.6 / 9.2 / 9.2%**; short-horizon mean-variance dominance of P1 reverses by $t=0.10$; the P1
inventory is exponentially below the P0 (linear) trajectory at every $t$ (arXiv:2505.15611).

**Failure modes.** The schedule is aggressive *and* conservative — it liquidates fast enough that
the downside barrier is never touched, but it traps the broker with no inventory, so long-horizon
performance is poor and dispersed; the result is a *contract-design* statement (shortermism from a
non-linear payoff), not an alpha claim, and is sensitive to the barrier geometry; the model has no
market impact interaction between $b$ and the schedule beyond the linear term.

### 2.4 Impact-aware RL liquidation on replay-with-impact
**Purpose.** Learn an opportunistic sell-only liquidation policy that beats TWAP/VWAP under a hard
deadline, with an honest cost model.

**Formula.** PPO with GAE; state = depth-20 bid/ask ladder (prices normalised by mid, sizes in
BTC) + microstructure indicators (microprice $p_{\rm micro}=\frac{p_aQ_b+p_bQ_a}{Q_b+Q_a}$,
top-of-book imbalance $I=\frac{Q_b-Q_a}{Q_b+Q_a}$, multi-level imbalance $I_n$, normalised spread
$S_{\rm norm}=100(p_a-p_b)/p_{\rm mid}$, bid/ask depth, VAMP, OFI, BPI, $\Delta p_{\rm mid}$,
$\Delta$VAMP) + time-to-go and remaining-inventory fractions; action = single scalar = fraction of
remaining inventory to execute, clipped to $[0,\text{trade fraction}]$; reward = implementation
shortfall vs mid with terminal mark-to-market and a leftover-inventory penalty. Transient impact is
applied at execution (concave in size, scaled by contemporaneous liquidity) and decays
**exponentially** with a resilience half-life; a fixed latency shifts the effective fill one tick.

**Required inputs.** Historical L2 book snapshots (time, top-20 bid/ask ladder); fee schedule
(maker/taker); latency; impact/resilience parameters (calibrated, here parametric).

**Parameters & defaults.** 1 s snapshots, depth 20, BTC-USD; horizons 1,800/3,600/7,200 s; PPO
lr $1\times10^{-4}$, clip 0.20, $\gamma_{\rm disc}=0.995$, GAE $\lambda=0.95$, entropy 0.0,
max-grad-norm 0.5, KL early-stop 0.05; two-layer MLP 256/128 with SiLU; $\sim$10M steps, 6 envs, CPU;
deterministic greedy evaluation; `VecNormalize` fit on January and frozen for February.

**Observed effect sizes.** See §1: +2.25/+7.59/+22.96 bps over TWAP and +2.68/+7.70/+23.02 bps over
the book-VWAP proxy at 1,800/3,600/7,200 s. Robust to impact half-life $\times 1/2$–$\times2$ and
impact coefficient $\times0.5$–$\times2$ (sign and significance at 3,600–7,200 s preserved)
(arXiv:2511.07434).

**Failure modes.** Impact is *parametric* — no adaptive counterparty, no queue-position dynamics
beyond partial-fill probabilities, hence no true indirect impact; evaluation is single-asset,
single-venue, sell-only, one month; the VWAP comparator is a **book-liquidity proxy**, not traded-volume
VWAP; opportunistic policies have higher day-to-day P&L dispersion than TWAP; positive day-to-day
correlation makes the Wilcoxon test conservative but the design is still one horizon-family.

### 2.5 Quadratic-variation (Itô) inventory execution model
**Purpose.** Stop assuming a differentiable inventory path; model the trader's inventory and wealth
with Brownian components and re-solve for the optimal rate.

**Formula.** Value function (relaxed liquidation, running and terminal inventory penalties):
$$V(t_0,x,s,q)=\sup_{(\nu_t)}\mathbb E\Big[X_T+Q_TS_T-A|Q_T-q_T|^2-\int_{t_0}^T|Q_t|^2dt\Big],\quad
dS_t=\nu_t dt+\sigma dW_t,\ dQ_t=\nu_t dt+\tilde\sigma d\tilde W_t,\ dX_t=\nu_t(S_t+\cdot)dt+\tilde\sigma(S_t+\cdot)d\tilde W_t$$
Solved by the stochastic maximum principle: the adjoint ansatz $Y^q_t=S_t+v(t,Q_t)$ with
$v(t,q)=p_tq+\iota_t$ closes the system with a **Riccati** equation for $p_t$ (terminal $p_T=2A$)
and a first-order *linear* equation for $\iota_t$ with zero terminal datum, whose solution is
identically $\iota_t\equiv0$; the optimal rate is the linear-in-$Q$ feedback
$$\hat\nu_t=\tfrac12 Q_t\,\nu(t,Q_t)\quad(\nu\text{ solved from the Riccati system}),$$
so the inventory volatility $\tilde\sigma$ is the *only* new parameter vs the differentiable model.
The Riccati equation has a unique solution when the damping term stays below the discriminant
threshold.

**Required inputs.** Per-trader inventory $q_i$, wealth $x_i$, trade times $\tau_i$, prices $s_i$;
price $\sigma$ (from the tape); $\tilde\sigma$ = std of the inventory increments
$(q_i-q_{i-1})$; target $q_T$; penalties $\varkappa$ and $A$.

**Parameters & defaults.** 5-minute regular sampling (also asynchronous); 10,000 Monte Carlo paths
for path comparison; $A,\varkappa,\sigma$ estimated from the data (Leal et al. 2020 recipe);
illustrated on Citadel Securities Canada's RY trading (2,357 trades on 2020-03-25, terminal inventory
144 shares; 2020-08-27 an acquisition case).

**Observed effect sizes.** Brownian component rejected-absent on **98–100%** of trader-days
(regular) and **82–100%** (asynchronous); the Itô generalisation changes the optimal feedback and the
expected inventory/wealth paths materially (path comparison via Monte Carlo) (arXiv:2104.14615).

**Failure modes.** Continuous optimal rate is *discretised* at the trader's own trade times, so the
simulated scenario does not incur the same impact as the actual trader; comparisons are vs the
*expected* optimal path, not a realised counterfactual; the result is a model-diagnosis statement
(inventories are diffusive), not a claim of profit.

### 2.6 Execution-flow timing signal (schedule trigger)
**Purpose.** Turn the transaction stream into a single actionable trigger: is liquidity *now*
abundant (take it) or scarce (expect a large future print and price move)?

**Formula.** Moments of a state function under a decaying weight,
$\langle Q_jf\rangle=\int^{t_{\rm now}}Q_j(x(t))f(t)\omega(t)dt$ with Legendre basis
$Q_j(x(t))=P_j(2e^{(t-t_{\rm now})/\tau}-1)$, $\omega=e^{(t-t_{\rm now})/\tau}$. Execution flow
$I=dV/dt$ (Radon–Nikodym derivative of the volume measure by time). Build the Rayleigh quotient
$I_\psi=\frac{\langle\psi|I|\psi\rangle}{\langle\psi|\psi\rangle}$ and solve the **generalised
eigenproblem** $E_I\psi=\lambda G\psi$, i.e.
$\sum_k\langle Q_j|I|Q_k\rangle\alpha^{(i)}_k=\lambda^{(i)}\sum_k\langle Q_j|Q_k\rangle\alpha^{(i)}_k$,
with eigenstates $\psi^{(i)}=\sum_k\alpha^{(i)}_kQ_k$. The maximal eigenvalue $\lambda^{[\max I]}$ is
the "future flow" estimate $I_0^F$; a **trigger** is
$|\langle\psi^{[\max I]}|\psi_0\rangle|^2>0.9$ (close / liquidity excess) or
$|\langle\psi^{[\min I]}|\psi_0\rangle|^2>0.9$ (open / liquidity deficit), with the directional term
$\mathrm{dir}_{PdI}=\lambda^{[\max I]}P^{\rm last}-P^{[\max I]}-\mathrm{Tr}\,\rho\,\frac{IdP}{dt}$
and the position $S=I-\lambda^{[\max I]}$ (i.e. $dS=dI$).

**Required inputs.** A **transaction tape** $(t_l,P_l,dV_l)$ (time, execution price, shares); a
decaying time scale $\tau$; basis dimension $n$.

**Parameters & defaults.** $n=12$, $\tau=128$ s (effective scale range $\tau/(2n-1)$ to $\tau$);
$n=10$ with $\omega=1$ for the whole-day price basis; incremental (recurrent) moment update so the
eigenproblem runs in real time.

**Observed effect sizes.** Price singularities coincide with high $I_0$ at the 694 and 700 levels
for AAPL (2012-09-20) and on 2025-04-01 (594,673 transactions); the $\psi^{[\max I]}$ state is
stable for far longer than a price tick, enabling the "impact from the future" assumption
(arXiv:2511.01471).

**Failure modes.** Needs *individual executed trades* — daily closes are explicitly insufficient and
impose a spurious one-day scale; if $\tau$ or $n$ is mismatched the $\psi^{[\max I]}$ state cannot be
constructed and the signal degrades to random (observed near 14:00 in slow ITCH data); a strategy with
only two trigger types "will inevitably fail eventually, resulting in catastrophic P&L loss" — at
least four entry/exit event types are required (arXiv:2511.01471).

## 3. Data requirements → available endpoints

Provider rows are real entries in `strategies/endpoints.json`; the **Probe status** column carries
the catalogue's `code` field. "**gap**" means no current provider serves the input.

| Input | Endpoint | Category | Provider | Probe status |
|---|---|---|---|---|
| Daily OHLCV (for $\sigma$, ADV, impact calibration) | `https://eodhd.com/api/eod/AAPL` | `core_stock_apis` | eodhd | ok |
| Daily OHLCV (secondary) | `https://api.tiingo.com/tiingo/daily/AAPL/prices` | `core_stock_apis` | tiingo | ok |
| Daily/prev aggregate bars | `https://api.massive.com/v2/aggs/ticker/AAPL/prev` | `core_stock_apis` | massive | ok |
| Intraday minute bars → relative volume curve $Q_t/Q_T$ | `https://api.twelvedata.com/time_series` | `core_stock_apis` | twelvedata | ok |
| Intraday K-line via local OpenD gateway | `moomoo://get_cur_kline` | `technical_indicators` | moomoo | gateway |
| Top-of-book snapshot (best bid/ask, size) | `moomoo://get_market_snapshot` | `core_stock_apis` | moomoo | gateway |
| Capital-flow / volume-pressure proxy for liquidity timing | `moomoo://get_capital_flow` | `capital_flow` | moomoo | gateway |
| Tradable symbol universe / tick sizes | `https://eodhd.com/api/exchange-symbol-list/US` | `exchange_symbols` | eodhd | ok |
| **L2/L3 book depth (≥20 levels, 1 s)** | — | — | — | **gap** |
| **Transaction tape (time, price, shares) at click/sub-second grain** | — | — | — | **gap** |
| **Per-trade aggressor sign / full TAQ (CTS)** | — | — | — | **gap** |
| **Maker/taker fee schedule, rebate tiers, latency** | — | — | — | **gap** |
| **Venue-tagged metaorders / parent-order reconstruction** | — | — | — | **gap** |
| **Crypto (BTC-USD) depth-20 book for RL replay** | — | — | — | **gap** |

**What the gaps cost, quantified.** (i) **Transaction tape:** arXiv:2511.01471 processes ~$10^8$
execution lines/day per TAQ file (>10 GB uncompressed) at nanosecond resolution, and 594,673 trades
for a single name-day; the coarse `core_stock_apis` minute bars give ~390 points/day for one symbol —
five orders of magnitude fewer events, enough for a volume *profile* but not for the flow trigger of
§2.6. (ii) **Book depth:** arXiv:2511.07434 trains and evaluates on depth-20 book snapshots for
BTC-USD over 31+28 days at 1 s resolution; `moomoo://get_market_snapshot` returns only best bid/ask,
so §2.4 cannot be trained at all and §2.2's $\eta_t$ can only be approximated (no book-walking).
(iii) **Fee schedule / latency:** the RL result's edge is +2–3 bps at 30 min, of the same order as
retail taker fees, so without the venue fee table and a latency model any schedule comparison is
unfalsifiable — the paper makes both explicit for exactly this reason. (iv) **Aggressor sign /
venue tags:** §2.2 and §2.5 need to know *who* traded and in which direction to sign inventory and
wealth; without it, the Brownian tests and the metaorder reconstruction degrade to the anonymous-tape
bias already documented in `../qfin-st/microstructure-execution.md`.

## 4. Pitfalls, validation and measurement

- **Look-ahead / leakage.** arXiv:2511.07434 freezes `VecNormalize` statistics fit on January and
  reloads them at inference with `training=False, norm_reward=False`, and evaluates on a strict
  temporal split (Jan train → Feb test) — do the same for any execution model; do **not** re-fit
  normalisers on the test month. arXiv:1306.2832 stresses that the VWAP definition
  $\int_0^T S_t\,dx_t$ with $x_t=Q_t/Q_T$ is not $\mathcal F$-adapted (its natural filtration is
  $\mathcal G_t=\mathcal F_t\vee\sigma(Q_T)$), so any implementation that uses the realised $Q_T$ in
  the *strategy* is cheating — $Q_T$ may only enter the *premium*.
- **Pseudo-replication.** Raw per-episode execution results are not independent: arXiv:2511.07434 runs
  10 intra-day starts per day and aggregates to a **single daily score** before testing, using days as
  the unit of inference; it notes daily pairs are still positively autocorrelated, which makes the
  one-sided Wilcoxon **conservative**, not anti-conservative. Never test on raw episodes.
- **Multiple testing.** Two baselines per horizon, horizons as separate families, Benjamini–Hochberg
  FDR; report effect sizes (Cohen's $d$) and bootstrap 95% CIs alongside $p$-values; sensitivity to
  1% winsorisation and to daily-mean vs daily-median aggregation was checked and left conclusions
  unchanged (arXiv:2511.07434).
- **Cost assumptions decide the sign.** The VWAP result hinges on permanent impact: with $k=0$ the
  optimum is the volume curve, with $k>0$ it front-loads and the premium can go **negative**
  (arXiv:1306.2832). Never report a VWAP/guaranteed-VWAP edge without stating whether permanent impact
  is in the cost model.
- **Regime dependence of the schedule.** In arXiv:2505.15611 the target schedule beats the classical
  one over short horizons and loses over long horizons (mean $1.04741$ vs $1.05062$ at $t=0.10$);
  liquidation aggressiveness is *not* invariant to the evaluation horizon, so any comparison must fix
  and report the horizon.
- **Model-diagnosis nulls.** The Brownian-component tests in arXiv:2104.14615 are one-sided with a
  *fictitious* injected Brownian motion; the conclusion is sensitive to $\sigma'$ (test loses power for
  $\sigma'\gtrsim700$ inventory / $\gtrsim6\times10^4$ wealth) and to the truncation $\varkappa\ge3$ —
  report the (in)ability to reject as a function of both, not a single $p$-value.
- **Metric choice.** Use the papers' own metrics: implementation shortfall in bps vs TWAP/VWAP
  (arXiv:2511.07434), premium in bps of the initial price or of the realised VWAP (arXiv:1306.2832),
  hit/ruin/between probabilities and the mean-variance of $Y$ (arXiv:2505.15611), expected
  implementation shortfall sign as the no-arbitrage gate (arXiv:2410.04867), and the Rayleigh-quotient
  eigenvalues / trigger projections (arXiv:2511.01471).
- **Sample split and length.** One month out-of-sample (28 days, 27 usable) is the entire RL evidence
  base (arXiv:2511.07434); TSX trader evidence spans ~10.8 years and 10 names (arXiv:2104.14615);
  the impact coefficients come from one month on one name (arXiv:2410.04867). Flag the resulting
  external-validity limits rather than pooling them.

## 5. Recommended first implementation in FinRobot

Ordered by value-per-effort against what the data layer can fetch today. Items 1–3 are buildable now;
items 4–6 are blocked on a tape/book feed and should be simulator-side only.

1. **Guaranteed-VWAP / VWAP schedule engine (§2.1).** *What:* the deterministic-volume Hamiltonian
   solver plus the risk-neutral closed form, returning a curve $q^*(t)$ and a premium
   $\pi(q_0)$. *Data:* `eodhd eod` / `tiingo prices` for daily $\sigma,V_D$; `twelvedata time_series`
   (`interval=1min`) for the relative volume curve. *Value:* every large-order suggestion gets a
   defensible cost and a benchmark-tracking curve instead of a flat TWAP. *Risk:* needs a forecast of
   $Q_T$; permanent-impact slope $k$ must be carried as a conservative constant. *Passing result:*
   the schedule replicates the relative volume curve when $k\!\to\!0$ and front-loads monotonically as
   $k$ rises.
2. **Time-varying-impact well-posedness gate (§2.2).** *What:* build $A$ from sampled $(\theta_i,\eta_i)$,
   test SPD/B-matrix/diagonal dominance and the continuous admissibility inequality; reject or warn
   before optimising. *Data:* intraday bars for a book-walk $\eta_t$ proxy and the score-driven
   VAR/Hasbrouck $\theta_t$ proxy (paper recipe). *Value:* prevents the discrete optimiser from
   emitting oscillating or buy-back schedules. *Risk:* proxy $\eta_t$ is bookless. *Passing result:*
   the gate flags the paper's known ill-posed 3-slice counterexample and passes all monotone cases.
3. **Barrier-remuneration analyser (§2.3).** *What:* compute the exponential target schedule, the
   linear classical schedule, and the hit/ruin/between probabilities by Monte Carlo. *Data:* none live
   beyond $b,l,\gamma,\sigma$. *Value:* exposes the shortermism of target-based contracts in FinRobot's
   execution advice. *Passing result:* reproduces 50.9/0.0/49.1% vs 81.6/9.2/9.2% at the paper's
   baseline parameters.
4. **Impact-aware RL liquidation on a replay-with-impact environment (§2.4).** *What:* port the
   transient-impact-with-resilience replay, partial fills, maker/taker fees and latency, then the PPO
   agent and TWAP/book-VWAP baselines on identical timestamps. *Data:* needs depth-20 book snapshots —
   **blocked today**; prototype on `moomoo://get_market_snapshot` top-of-book only as a degraded
   benchmark. *Value:* the only route in this repo to an opportunistic, statistically tested schedule.
   *Risk:* parametric impact → no true indirect impact; single asset/venue. *Passing result:* the
   per-day paired Wilcoxon of RL minus TWAP is positive and FDR-significant at 3,600 s and 7,200 s.
5. **Itô-inventory execution diagnostic (§2.5).** *What:* the Brownian-component rejection tests on
   per-trader inventory/wealth at 5-minute bins, plus the Riccati optimal-rate feedback. *Data:*
   needs per-trader signed trades with counterparty identity — **gap**; with anonymous fills only the
   price-side test is possible. *Value:* calibrates $\tilde\sigma$, the one extra parameter the
   differentiable model ignores. *Risk:* without identity data the test degenerates. *Passing result:*
   rejection of the no-Brownian null on the large majority of trader-days, matching 98–100%.
6. **Execution-flow trigger service (§2.6).** *What:* incremental moments, the generalised
   eigenvalue problem, and the $\psi^{[\max I]}/\psi^{[\min I]}$ projections as actionable thresholds.
   *Data:* a **transaction tape** $(t,P,dV)$ — **blocked**; cannot be approximated from minute bars
   without imposing exactly the artificial time scale the paper warns against. *Value:* high once a
   tape exists; low as a bars hack. *Risk:* mismatched $\tau/n$ silently degrades to noise. *Passing
   result:* trigger switch precedes observed price singularities on a held-out name-day.

## Appendix — papers read

| arXiv id | Title | Year |
|---|---|---|
| 2511.07434v1 | RL-Exec: Impact-Aware Reinforcement Learning for Opportunistic Optimal Liquidation, Outperforms TWAP and a Book-Liquidity VWAP on BTC-USD Replays | 2025 |
| 1306.2832v4 | VWAP execution and guaranteed VWAP | 2013 |
| 2511.01471v2 | Trade Execution Flow as the Underlying Source of Market Dynamics | 2025 |
| 2505.15611v1 | Shortermism and excessive risk taking in optimal execution with a target performance | 2025 |
| 2410.04867v2 | Optimal execution with deterministically time varying liquidity: well posedness and price manipulation | 2024 |
| 2104.14615v1 | Optimal Execution with Quadratic Variation Inventories | 2021 |
