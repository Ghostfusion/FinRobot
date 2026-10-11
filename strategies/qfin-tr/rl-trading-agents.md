# Reinforcement Learning Trading Agents — learnings from the q-fin.TR corpus

`193` of 2370 corpus papers matched this category (191 with PDFs); this doc is based on a close reading of `6`.

Headline: **this category is not about signal accuracy, it is about protocol.** Supervised prediction is
[`../qfin-st/ml-price-prediction.md`](../qfin-st/ml-price-prediction.md), allocation machinery is
[`../qfin-st/portfolio-optimization.md`](../qfin-st/portfolio-optimization.md). What these six papers supply is
the *loop*: environment definition, reward shaping that expresses a financial rather than a decision-theoretic
preference, how much of the result is the simulator rather than the algorithm, and how to prove a reported edge
is not an artefact. One paper is strongly negative (RL portfolio management is often myopically sub-optimal in an
action-independent market), four are constructions that work, one works only in simulation. The most reusable
artefact is an **audit**: a myopic baseline plus a look-ahead detector, run before any RL PnL is believed.

## 1. What the corpus actually offers

- **The negative result, with a formal bound.** In an action-independent market (AIM) with mark-to-market
  accounting, spreads, transient impact, funding and taxes, myopic optimization (MO — one-period convex programs
  solved online) is dynamically sufficient relative to RL: MO contracts geometrically under a Polyak-Łojasiewicz
  geometry while policy-gradient RL carries a non-vanishing variance floor,
  $\liminf_{T}\mathcal{E}(T)\ge\frac{C}{4L}\liminf_{T}\mathbb{E}[\mathrm{Tr}(A^{\rm opt}(\theta_T))]>0$.
  Ordering: MO $>$ RL on conditional mean PnL, MO $<$ RL on variance, likewise for loss-side CVaR and the
  probability of non-negative PnL (arXiv:2509.12764).
- **The RL win is small, local, and preceded by an artefact.** RL adds value only when actions move the state
  (control-affects-dynamics), when convexification is materially loose, or when the compute window is severe; its
  CAD gain scales with the amplitude of a counterparty regime shift and inverse detection delay and "nets out to
  0–1 bps per decision day" in liquid AIM-like environments, reaching low single-digit bps/day only in rare,
  strongly CAD-dominated niches. Wall-clock cost of RL over MO at matched tolerance: 10–50 CPU min, 3–10 GPU min
  (arXiv:2509.12764). Phantom profit is the mechanism, and it is computable: if the policy is not strictly adapted
  — solver look-ahead, cross-bar leakage, latency peek-through — the MtM diffusion picks up a Skorokhod
  correction, $\Pi_{\rm ph}(\phi)=-\tfrac12\mathbb{E}[\int_0^T\mathrm{Tr}(D_t[\Sigma_t\phi_t])dt]$ for a
  look-ahead window $\Delta t$ with $\|D_s\phi_t\|\le L\mathbb{1}_{\{t\le s\le t+\Delta t\}}$, bounded by
  $\tfrac12\|\Sigma\|_\infty\|D\phi\|_{\mathcal H}$. At typical settings ($10^2$–$10^3$ iterations, per-step
  signal-to-noise $0.03$–$0.10$) the probability that the solution bias is positive is $\ge0.62$ — an unaudited
  RL backtest is optimistic *by default* (arXiv:2509.12764).
- **A model-free agent discovers price manipulation that a correctly specified but estimated model misses.**
  Discrete Almgren–Chriss market, concave permanent impact $f(v)=\theta\,\mathrm{sign}(v)|v|^{\delta}$
  ($\delta=0.1$), linear temporary impact $\kappa v$: zero-inventory round trips have positive expected cash flow.
  Baseline $T=21$ steps, $\theta=10^{-4}$, $\kappa=3\times10^{-4}$, $|v|\le15$, metaorder volatility
  $\sigma=0.0168$ (MSFT daily realized volatility $0.026$ over a $0.39$-day metaorder), $\sigma/\theta=56$,
  $\sigma/\kappa=167$. Mean terminal cash ($\times10^{-4}$, 1000 out-of-sample simulations): at $\sigma=0.003$
  DDPG $5$ ($t=2.34$, $p=0.010$) beats regSLSQP$_{5000}$ $1$ and regSLSQP$_{500}$ (negative); at $\sigma=0.002$
  regSLSQP$_{5000}$ $13$ beats DDPG $5$ ($t=3.26$, $p=0.001$) because parameters are then estimated almost
  exactly. At $\sigma=0.0168$ nothing is significantly positive (DDPG $t=0.83$, $p=0.40$) and regSLSQP is
  *significantly negative* in 46% ($N=500$) and 33% ($N=5000$) of 100 replications; $\hat\delta$ is upward
  biased, making the model-based strategy over-conservative (arXiv:2607.06121).
- **Reward shape matters more than the risk-aversion coefficient.** Homogeneous reward volatility
  $\hat\nu_\pi^2=\mathbb{E}_\pi[\sum_i\gamma^{i-1}(r_i-J_\pi)^2]$ penalises the *time split* of the return and
  therefore never chooses immediate liquidation on a 5-day, $10^6$-share unwind ($S_0=50$,
  $\sigma=0.95\ \${\rm day}^{-1/2}$, $g=2.5\times10^{-7}$, $\epsilon=1/16$, $\eta=2.5\times10^{-6}$), even at
  $\beta=10^{-1}$. Replacing the single target $J_\pi$ with a per-step target $\bar r_{\pi,i}$ restores the whole
  family, from linear ($\beta=10^{-7}$) to single-step ($\beta=10^{-1}$). Bounds: $\hat\nu^2_\pi\ge\varsigma^2_\pi$
  always, $\sigma^2_\pi\le\Gamma\varsigma^2_\pi$ if the horizon is deterministic (arXiv:2602.12030).
- **Exploration has a cap, a temperature and a closed-form price.** Randomised stopping intensities bounded by
  $M$ with Shannon entropy at temperature $\eta$ give Gibbs exploration densities and
  $0\le V_{\rm orig}-V^\eta_{\rm ent}\le CM^2|\eta\ln\eta|+CM^{-\kappa/2}$, so $(M,\eta)$ must be co-chosen along
  $M^2|\eta\ln\eta|\to0$; larger $M$ widens the action space but slows convergence quadratically. Working point
  $M=50$, $\eta=10^{-5}$: offline policy iteration (two-layer 32-unit ReLU nets, $\Delta t=0.1$, 100 steps)
  reproduces the finite-difference HJB solution, residual concentrated at the entry/exit free boundary
  (arXiv:2604.02035).
- **Ensembling three actor-critics beats each of them, narrowly and non-monotonically.** 30 DJIA constituents,
  2009-01-01→2020-05-08, 0.1% cost per trade, quarterly walk-forward selection on a 3-month validation Sharpe:
  ensemble Sharpe $1.30$ vs PPO $1.10$, A2C $1.12$, DDPG $0.87$, min-variance $0.45$, DJIA $0.47$; but PPO has
  the higher cumulative return ($83.0\%$ vs $70.4\%$), and the ensemble wins by not blowing up (max drawdown
  $-9.7\%$ vs PPO $-23.7\%$, DJIA $-37.1\%$). Validation Sharpe swings $-0.58\ldots+0.71$; the picked model
  changes 12 times in 18 quarters (arXiv:2511.12120).
- **Imitation + RL in a latent noise space: 2× faster convergence at 15.6% trainable weights.** FinFlowRL freezes
  a 2.14M-parameter MeanFlow expert and trains only a 197,664-parameter noise policy and a 199,425-parameter
  critic (397,089 of 2.54M), converting the MDP into a latent-action MDP on the noise $w$; convergence at 400K
  steps vs 800K for vanilla PPO, training time $0.8\times$, inference $6.25\ \mu$s/decision over 400M steps. In a
  Hawkes-driven market-making simulator (1M episodes per cell): FinFlowRL Sharpe $0.50/0.28/2.34/1.36$ against the
  best traditional expert GLFT $0.37/0.24/1.17/0.78$ and vanilla PPO $0.10/0.08/0.81/0.46$, and above the
  pre-trained expert it was cloned from ($0.37/0.22/1.83/1.07$). The expert pool is chosen per scenario as best of
  four candidates (AS, GLFT, GLFT-drift, PPO) over 108 parameter combinations and 3.24M state-action pairs
  (arXiv:2510.15883).
- **Off-topic note.** None of the six is off-topic. The weakest fit is arXiv:2511.12120 — a portfolio-management
  paper with a price/indicator state space, hence close to the supervised-prediction doc; retained because it is
  the only paper here that specifies a *complete* walk-forward ensemble protocol (train 2009-01→2015-09, validate
  2015-10→2015-12, trade 2016-01→2020-05 in quarterly steps) with costs and a drawdown kill-switch.

## 2. Implementable formulas & algorithms

### 2.1 Model-free discovery of price manipulation (DDPG on non-linear impact)

**Purpose.** Test whether an agent given only an inventory/time/price state can find a zero-inventory round trip
with positive expected cash flow that a correctly specified model-based optimizer cannot implement because impact
parameters are estimated from a finite sample. Also the cleanest statement of how reward misspecification
*manufactures* manipulation.

**Formula.**
$$S_t=S_{t-1}+f(v_t)\Delta t+\sigma\sqrt{\Delta t}\,\xi_t,\qquad \tilde S_t=S_{t-1}+\kappa v_t,\qquad
f(v)=\theta\,\mathrm{sign}(v)|v|^{\delta},\ \delta\in(0,1)$$
$$\mathbb{E}[X_T]=-\sum_{t=1}^{T}v_t\sum_{j=t+1}^{T}f(v_j)+\kappa\sum_{t=1}^{T}v_t^{2}
=\alpha^{\delta+1}A(n)-\alpha^{2}B(n)\quad\text{(two velocities)}$$
$$A(n)=\theta\,n\Big[(n+1)-\Big(\tfrac{n}{T-n}\Big)^{\delta}(T-n-1)\Big],\qquad
B(n)=\kappa\Big(n+\frac{n^{2}}{T-n}\Big),\qquad
\alpha^{*}=\Big(\frac{(\delta+1)A(n)}{2B(n)}\Big)^{\frac{1}{1-\delta}}$$
Environment: state $S_t=(q_t,t,S_t)$, reward $r_t=S_tv_t-\kappa v_t^{2}$, constraint $\sum_t v_t=0$; DDPG actor
$\pi$ plus double-Q critic with target networks and soft update. Impact parameters from TWAP metaorders:
$$I_i=\frac{T\theta(v^{(i)})^{\delta}}{S_0}+{\rm noise},\qquad J_i-I_i=\frac{(T-1)\kappa v^{(i)}}{2TS_0}+{\rm noise},\qquad
\hat\theta(\delta)=\frac{\sum_i(q_i/T)^{\delta}I_i}{\sum_i(q_i/T)^{2\delta}}$$

**Required inputs.** Signed metaorder executions at child-fill granularity (volume, mid before/after); the
environment needs no quotes or depth, which is why it ports to a bars-only shop.

**Parameters & defaults.** $T=21$, $\theta=10^{-4}$, $\kappa=3\times10^{-4}$, $b=15$, $\delta=0.1$; $N\in\{500,5000\}$
metaorders, $q_i\sim U[1,20]$; DDPG: memory $10^5$, batch 128, 3 layers × 64 nodes (SiLU, tanh output), lr 0.1
decaying $\times0.99$ every 100 iterations, $\gamma=0.99$, soft update $0.001$, $\epsilon$ annealed $1\to0.1$ by
$a=1/T$ per iteration, 500 episodes, features in $[-1,1]$; validation on 1000 fresh simulations; regSLSQP
replicated 100 times.

**Observed effect sizes.** DDPG cash $5\times10^{-4}$ at $\sigma=0.003$ ($t=2.34$, $p=0.010$) and $\sigma=0.002$
($t=3.26$, $p=0.001$); full-information SLSQP is *not* significant at $\sigma=0.003$ ($25\times10^{-4}$, $t=1.58$,
$p=0.11$); aggressiveness $A_e=\frac{1}{20}\sum_{t\le20}|v_{e,t}|$ falls with training while directionality
$D_e=\sum_tv_{e,t}/\sum_t|v_{e,t}|$ rises toward $+1$ (pump over steps 1–20, one terminal sell).

**Failure modes.** The reward sign sets the manipulation direction ($r_t=-S_tv_t-\kappa v_t^{2}$ flips it). At high
volatility nothing works and the model-based estimator is loss-making — never deploy as an alpha source. The
reward is unsafe by construction: production use needs a no-manipulation constraint. No other participants, so no
indirect impact and no transfer to a book. The SLSQP landscape is non-convex (500 random starts) and strategies at
sign-invariant distance $d=0.0855$ differ materially in cash flow.

### 2.2 Inhomogeneous reward-volatility shaping (IVO)

**Purpose.** Give RL a risk objective that expresses a *planned* per-step PnL profile instead of an implicit
preference for homogeneity; the only reward-shaping result here with a formal statement of what changes.

**Formula.** With rewards $r_i$, horizon $\varepsilon$, $\Gamma=\sum_{i=1}^{\varepsilon}\gamma^{i-1}$ and
$\bar r_{\pi,i}=\mathbb{E}_\pi[r_i\mid\varepsilon\ge i]$:
$$\varsigma^{2}_{\pi}=\mathbb{E}_\pi\Big[\textstyle\sum_{i=1}^{\varepsilon}\gamma^{i-1}(r_i-\bar r_{\pi,i})^{2}\Big],
\qquad \pi\mapsto\mathbb{E}_\pi[G]-\beta\varsigma^{2}_{\pi}$$
$$\varsigma^{\ell}_{\pi}=\inf_{\bar r^{\ell}\in\mathbb{R}^{\varepsilon}}\mathbb{E}_\pi\Big[\textstyle\sum_{i=1}^{\varepsilon}\gamma^{i-1}\ell(r_i-\bar r^{\ell}_{i})\Big],
\qquad \mathbb{E}_\pi[G]-\varsigma^{\ell}_{\pi},\qquad
\mathbb{E}_\pi[\ell'(r_i-\bar r^{\ell}_{\pi,i})\mid\varepsilon\ge i]=0$$
$$X_{\pi,i}=I_{\varepsilon>i}\mathbb{E}_{\pi,i}\big[(r_{i+1}-\bar r_{\pi,i+1})^{2}\big]+\gamma\mathbb{E}_{\pi,i}[X_{\pi,i+1}],\qquad
\nabla_\theta\varsigma^{2}_{\pi}=\mathbb{E}_\pi\Big[\textstyle\sum_{i=0}^{\varepsilon-1}\gamma^{i}X_{\pi,i}(s_i,a_i)\nabla_\theta\log\pi_{\theta,i}(a_i\mid s_i)\Big]$$
Two gradient-tractable variants: inhomogeneous optimised certainty equivalent ($\ell(x)=x-u(x)$, concave $u$) and
inhomogeneous monotone mean-volatility with $\ell_m(x)=\beta x^{2}$ for $x\le(2\beta)^{-1}$, $x-(4\beta)^{-1}$ above.

**Required inputs.** Per-step *financial* PnL $R_{t_i}=V_{t_i}-V_{t_{i-1}}$, $V_t=N_tX_t+C_t$; the horizon
(deterministic or randomised); targets $\bar r_{\pi,i}$ (conditional sample means for the quadratic case).

**Parameters & defaults.** Quadratic $\ell=\beta(\cdot)^2$, $\beta\in[10^{-7},10^{-1}]$; execution working point
$S_0=50$, $\sigma=0.95$ day$^{-1/2}$, $g=2.5\times10^{-7}$, $\epsilon=1/16$, $\eta=2.5\times10^{-6}$, $\Delta t=1$
day, $T=5$ days, $N_0=10^6$ shares; state $=(t/T,\ S_t,\ N_t)$.

**Observed effect sizes.** Under homogeneous reward volatility the optimal policy never liquidates immediately at
any $\beta$ tested, including $10^{-1}$; under the inhomogeneous objective paths span the Almgren–Chriss family,
linear at $\beta=10^{-7}$ to one-step at $10^{-1}$. On the two-step toy problem (deterministic $G\equiv1$) the
homogeneous objective picks $a_0=1/4$, the inhomogeneous one correctly picks $a_0=0$.

**Failure modes.** With a *stochastic* horizon the metric misbehaves: on a 35-step grid world (8% random-action
noise, $-1$/step, $+35$ goal, $-35$ traps) sufficiently risk-averse policies dive into a trap immediately to end
the episode, and intermediate $\beta$ produces deliberate waiting before a safe goal. Targets are policy-dependent
and must be re-estimated, coupling outer search to the inner solve. A variance penalty treats favourable and
unfavourable deviations identically; the monotone variant fixes gross cases but not the ordering of a late
high-probability reward versus an early low-probability one. The $\ell$-objective is not reducible to a
transformed-reward RL problem, so off-the-shelf tooling fails.

### 2.3 Entropy-regularized exploratory stopping for entry/exit (speculative trading)

**Purpose.** Turn a sequential optimal-stopping problem (pairs trade, or any "enter then exit" opportunity) into a
continuous-time RL problem with a *proper* exploration policy, a closed-form optimal policy, and an error budget
bounding the distance from the true stopping value.

**Formula.** $dP_t=\mu(P_t)dt+\sigma(P_t)dW_t$; entry/exit are jump times of two Cox processes with intensities
$\alpha_t,\beta_t\in\mathcal M=[0,M]$; state augmented by a stage $J\in\{0,1,2\}$ and a reference entry value $B$;
reward rate $\tilde r=\mathbb{1}_{\{J=1\}}G(P_t,B)(\int\lambda\pi^\beta_t(d\lambda))$ with
$G(p,b)=U(\gamma p-\iota b-\Psi-R)$. Entropy relative to the uniform law,
$H(\pi)=-\int\!\!\int\pi_1\pi_2\ln(M^2\pi_1\pi_2)\,d\lambda_1d\lambda_2\le0$; HJB pair with
$\Delta_1=V_1(p,p)-V_0(p)$, $\Delta_2=G(p,b)-V_1(p,b)$:
$$\rho V_0-\mathcal L_PV_0=\eta\ln\frac{e^{M\Delta_1/\eta}-1}{M\Delta_1/\eta},\qquad
\rho V_1-\mathcal L_PV_1=\eta\ln\frac{e^{M\Delta_2/\eta}-1}{M\Delta_2/\eta}$$
$$\pi^{\beta,*}(\lambda;p,b)=\frac{e^{\lambda\Delta_2/\eta}}{\eta(e^{M\Delta_2/\eta}-1)},\qquad
\bar\lambda^{\beta,*}=\frac{M}{1-e^{-M\Delta_2/\eta}}-\frac{\eta}{\Delta_2}$$
Error budget: $0\le V_{\rm orig}-V_{\rm inte}\le CM^{-\kappa/2}$ ($\kappa$ the Hölder exponent of $U$) and
$0\le V_{\rm inte}-V^\eta_{\rm ent}\le CM^2|\eta\ln\eta|$; jointly $CM^2|\eta\ln\eta|+CM^{-\kappa/2}$.

**Required inputs.** A signal series (here the spread of two co-moving assets), a utility with a reference point,
proportional costs $\gamma,\iota$, a fixed cost $\Psi$, and a discount rate $\rho>\hat A$ for finiteness.

**Parameters & defaults.** $M=50$, $\eta=10^{-5}$; OU signal with $\theta=0.1$, $\bar p=0$, $\sigma=0.2$; S-shaped
power utility ($x^{\varpi}/\varpi$ gains, $-k|x|^{\varpi}$ losses) with $\varpi=0.5$, $k=2$; $\gamma=\iota=1$,
$\Psi=0$, $R=1$, $\rho=0.05$; grid step 0.05 on $[-4,4]^2$, tolerance $10^{-6}$; RL: two-layer 32-unit ReLU nets,
$\Delta t=0.1$, 100 steps, restarts with half initialised in-stage to densify state coverage.

**Observed effect sizes.** Policy iteration matches the finite-difference HJB solution for $V_0(p)$ and $V_1(p,b)$
at $M=50$, $\eta=10^{-5}$, error concentrated on the free boundary $p^*(b)$; $V_0$ increases in both $M$ and $\eta$
(entropy is non-positive, a tighter cap shrinks the action set); the exit boundary increases with the entry price
$b$ (loss aversion); stronger mean reversion lowers $V_0$ near $\bar p$, higher volatility raises it.

**Failure modes.** The cap delays entry/exit by $O(1/M)$; a small $M$ prevents timely capture. A large $M$ widens
exploration but slows convergence as $M^2$ — pick $M$ where the value function is insensitive to $M$ and $\eta$.
One round trip and a large discount rate are assumed; zero-discount and repeated-switching versions are open. The
signal is one-dimensional, so proportional costs on *both* legs are not represented ($\gamma=\iota=1$ only).

### 2.4 Ensemble actor-critic portfolio strategy with a turbulence kill-switch

**Purpose.** The operational recipe: a multi-asset continuous-action DRL agent whose reward is a genuine portfolio
value change net of costs, wrapped in a quarterly model-selection loop and a crash circuit breaker.

**Formula.** State (181-dimensional for $D=30$) $s_t=[b_t,p_t,h_t,M_t,R_t,C_t,X_t]$ — balance, prices, shares,
MACD, RSI, CCI, ADX; action a continuous vector in $[-1,1]^{D}$; portfolio value $p^{\top}h+b$;
$$r(s_t,a_t,s_{t+1})=(b_{t+1}+p_{t+1}^{\top}h_{t+1})-(b_t+p_t^{\top}h_t)-c_t,\qquad
c_t=p^{\top}k_t\times0.1\%,\qquad \tau_t=(y_t-\mu)\Sigma^{-1}(y_t-\mu)^{\top}$$
(above the turbulence threshold: halt buying, sell all). A2C:
$\nabla_\theta J=\mathbb{E}[\sum_t\nabla_\theta\log\pi_\theta(a_t|s_t)A(s_t,a_t)]$; PPO:
$J^{\rm CLIP}=\hat{\mathbb{E}}_t[\min(r_t(\theta)\hat A_t,\mathrm{clip}(r_t(\theta),1-\epsilon,1+\epsilon)\hat A_t)]$;
DDPG: $y_i=r_i+\gamma Q'(s_{i+1},\mu'(s_{i+1}))$. Selection: retrain all three on a growing window every
3 months, pick the highest validation Sharpe, trade with it for the next quarter.

**Required inputs.** Daily OHLCV for the universe (prices and all four indicators), a risk-free rate for the
Sharpe denominator, the return covariance for the turbulence index.

**Parameters & defaults.** $D=30$ DJIA constituents fixed at 01/01/2016; 0.1% cost per buy or sell; action
normalised to $[-1,1]$ for the Gaussian policies; train 2009-01-01→2015-09-30, validate 2015-10-01→2015-12-31,
test 2016-01-01→2020-05-08; turbulence threshold tunable; training *continues* during the trading stage.

**Observed effect sizes.** Sharpe: ensemble $1.30$, A2C $1.12$, PPO $1.10$, DDPG $0.87$, min-variance $0.45$, DJIA
$0.47$; ensemble annualised return $13.0\%$ on volatility $9.7\%$ with max drawdown $-9.7\%$, versus PPO
$15.0\%$ / $13.6\%$ / $-23.7\%$ and DJIA $7.8\%$ / $20.1\%$ / $-37.1\%$; per-quarter validation Sharpes span
$-0.58\ldots+0.71$, 12 model changes in 18 quarters.

**Failure modes.** Selection rests on a noisy 3-month Sharpe: the ensemble is a diversified overfitting device,
not evidence of adaptability. Continuing to train during the trading stage makes the test period not strictly
out-of-sample. A turbulence-triggered full liquidation turns the policy into a market-timing overlay, so crash
protection cannot be attributed to the RL algorithms. 30 correlated mega-caps span roughly one factor, so
$\Sigma^{-1}$ is ill-conditioned and the "risk aversion" knob is a single beta switch. The reward is a level change
with no per-step risk term, so risk control rests entirely on the circuit breaker.

### 2.5 Imitation + RL in the noise space of a frozen flow expert (FinFlowRL)

**Purpose.** Make RL tractable and low-latency in a non-Markovian, regime-switching control problem by cloning a
pool of regime specialists with a generative policy, then fine-tuning *only the noise* that generator consumes.
Also an explicit answer to "the market is not an MDP": plan an action *chunk*.

**Formula.**
$$u(z_t,r,t)\triangleq\frac{1}{t-r}\int_r^{t}v(z_\tau,\tau)d\tau,\qquad
\frac{d}{dt}u(z_t,r,t)=v(z_t,t)-(t-r)\frac{d}{dt}u(z_t,r,t),\qquad z_0=z_1-u(z_1,0,1,s)$$
$$a=w-u_\theta(w,1,0,s),\qquad \mathbf{h}=\boldsymbol\gamma\odot\mathbf{h}+\boldsymbol\beta\ \text{(FiLM)}$$
$$w\sim\pi^W_\phi(\cdot\mid s)=\mathcal N(\mu_\phi(s),\Sigma_\phi),\qquad
P_{dp}(\cdot\mid s,w):=P(\cdot\mid s,g_\theta(s,w)),\qquad r_{dp}(s,w):=r(s,g_\theta(s,w))$$
$$\mathcal L=\mathcal L_{PPO}(\phi)+c_v\mathcal L_{value}(\psi)-c_e\mathcal H[\pi^W_\phi],\qquad
\mathcal L_{PPO}=-\mathbb{E}[\min(r(\phi)A,\mathrm{clip}(r(\phi),1-\epsilon,1+\epsilon)A)]$$
Reward $r_k=\Delta W-\gamma Q^{2}\sigma^{2}$ per execution step (equivalently $\mathrm{PnL}_t-\lambda q_t^2$).
Horizons: observe $T_{obs}$, predict $T_{pred}$, execute only $T_{exec}$, then replan.

**Required inputs.** A market simulator (jump-diffusion mid on fractional Brownian noise plus Hawkes arrivals) or a
historical LOB event stream, plus a candidate expert pool whose per-regime dominance is measurable. State is small:
$s_t=(t,X_t,q_t,S_t,\mathrm{spread}_t)$.

**Parameters & defaults.** Hawkes: self-excitation $0.7$, cross-excitation $0.3$, decay $0.1$, base rates
$\mu_{a,b}\in\{10,20,40\}$, spread sensitivity $\lambda(\delta)=\lambda_0e^{-k\delta}$; price: $H=0.5$,
$\mu\in\{0.01,0.05,0.2\}$, $\sigma\in\{0.05,0.1,0.3\}$, $\lambda_J\in\{0,0.02\}$, $\Delta t\in\{0.01,0.02\}$;
108 scenario combinations × 100 episodes ⇒ 3.24M state-action pairs; expert pool $\{$AS, GLFT, GLFT-drift, PPO$\}$,
best per scenario as imitation target; frozen MeanFlow UNet1D (2,142,850 params), noise policy 3-layer 256-unit MLP
(197,664), critic 3-layer MLP (199,425); 256 parallel environments, batch 25,600, lr $5\times10^{-5}$;
$Q_{\max}=10$, inventory penalty $\gamma=0.1$, 100-step episodes. (Internal inconsistency: Fig. 4 shows
$T_{pred}=8$, $T_{exec}=4$; the appendix states $T_{obs}=2$, $T_{pred}=16$, $T_{exec}=8$.)

**Observed effect sizes.** Sharpe $0.50/0.28/2.34/1.36$ across the four volatility×demand cells versus GLFT
$0.37/0.24/1.17/0.78$; max drawdown in the low-volatility/high-demand cell $2.68\%$ vs GLFT's $6.95\%$; training:
0.4M trainable parameters, $0.8\times$ time and 400K convergence steps versus vanilla PPO's
0.5M / $1.0\times$ / 800K and end-to-end MeanFlow's 2.6M / $3.2\times$ / 1.2M; inference $6.25\ \mu$s/decision.

**Failure modes.** Each scenario's expert is the best performer *on that same scenario*, so part of the imitation
gain is in-sample selection; the fine-tuned model beating its own expert is the only clean claim. Historical LOB
replay cannot contain the policy's own impact — the paper says so explicitly and presents its real-market
extension as indicative, not as a PnL claim. The evaluation distribution is shifted from training (different
Hurst, drift, volatility, arrival rates), which is the right test but certifies no single operating point. A
frozen expert can only be corrected through noise, so behaviour outside its support is unreachable.

### 2.6 Myopic-optimality audit and phantom-profit accounting

**Purpose.** The acceptance test to run *before* believing any RL trading PnL: build the effort-matched myopic
baseline, measure the look-ahead content of the policy gradient in closed form, and fix the four distributional
metrics on which the comparison is reported.

**Formula.** KKT/HJB identity — the myopic first-order condition and the RL Hamiltonian stationarity coincide,
$$\partial_a\mathcal H_t(a)=\partial_aG_t+\mathcal P_t=0\ \Longleftrightarrow\
\vartheta_t(\phi^*)+\alpha_t-\beta_t+\sum_k\varkappa_{k,t}\nabla_\phi c_{k,t}(\phi^*)=0$$
so in an AIM market the optimal policy is a time-local soft-threshold feedback (no-trade wedge under proportional
costs). Effort comparison with PL constant $\mu_J$ and smoothness $L$:
$$\frac{d}{dT}\mathcal E(T)\le-2\mu_J\mathcal E(T)+\frac{L}{2}\mathbb{E}[\mathrm{Tr}(A^{\rm opt}(\theta_T))]
\ \Longrightarrow\ \liminf_{T}\mathcal E(T)\le\frac{CL}{4\mu_J}\limsup_T\mathbb{E}[\mathrm{Tr}(A^{\rm opt}(\theta_T))]$$
Phantom profit: enlarged filtration with information drift $a$,
$\Pi_{\rm ph}=\mathbb{E}[\int_0^T\langle\phi_t,\Sigma_ta_t\rangle dt]$; pure leakage,
$\Pi_{\rm ph}=-\tfrac12\mathbb{E}[\int_0^T\mathrm{Tr}(D_t[\Sigma_t\phi_t])dt]$; both, additive. Self-bias
$S^{\rm self}_{0\to K}=\eta\sum_{k=0}^{K-1}\langle b_k,g^{\rm naive}(\theta_k)\rangle$ equals, to first order, the
terminal phantom profit.

**Required inputs.** Paired PnL paths from (i) a strictly causal adapted policy and (ii) the implemented policy
under identical costs, spreads, decision clocks and risk budgets; the implemented policy's sensitivity to future
information (a defined look-ahead window); dual information only if the dual gap is reported.

**Parameters & defaults.** Four metrics on identical rebalancing clocks: conditional mean PnL, variance, loss-side
CVaR (Rockafellar–Uryasev), probability of non-negative PnL. Resample with a dependence-respecting scheme
(moving-block or stationary bootstrap) pre-calibrated to spreads, impact and fill intensities; use higher-order
weak schemes (Ninomiya–Victoir) rather than Euler–Maruyama if the step count must be cut.

**Observed effect sizes.** Positivity of the solution bias versus
$Z_{\rm eff}=(\mathbb{E}[Z]+\mathbb{E}[\Delta])/\sqrt{\mathrm{Var}(Z)+\mathrm{Var}(\Delta)+2\mathrm{Cov}}$:
$0.3\to\ge0.62$, $0.5\to\ge0.69$, $0.7\to\ge0.76$, $1.0\to\ge0.84$, $1.6\to\ge0.95$; typical range $0.6$–$0.8$.
RL costs 10–50 CPU min or 3–10 GPU min over MO at matched tolerance. The CAD premium requires the Hamiltonian
surplus
$\langle\Lambda_t,\phi^{\rm RL,*}_t\rangle>\Lambda_t\|\phi^{\rm RL,*}_t\|+\nabla_\phi\mathrm{HC}_t(\phi^{\rm RL,*}_t)$
and vanishes in the nonatomic limit $\varepsilon_t=q_t/D_t\to0$; regime-switching counterparties are the genuine
CAD source, RL's gain scaling in the regime amplitude and inversely in the detection delay.

**Failure modes.** The sufficiency claim is tied to AIM dynamics — where actions move the state (transient impact,
state-dependent fills, queue position) the first-order conditions must include the feedback and the conclusion can
reverse. Non-convex objectives (VaR, max drawdown, Sharpe-type ratios, cardinality) fall outside the theory and
need convex or mixed-integer-convex surrogates. The Malliavin/BEL machinery needs non-degeneracy (Hörmander) and
enough data to estimate diffusion terms, intensity responses and co-states; jump-heavy and regime-switching
episodes stress the Gaussian/Chernoff tail proxies. Undetected leakage blurs edge and artefact, which is why the
audit must run on the *implemented* objective.

## 3. Data requirements → available endpoints

Real rows are copied from `strategies/endpoints.json`; "gateway" is served by the local OpenD/moomoo SDK process
rather than live-probed over HTTP; **gap** means no current provider supplies it.

| Input | Endpoint | Category | Provider | Probe status |
|---|---|---|---|---|
| Daily OHLCV (state prices, OU spread legs, covariance) | `https://eodhd.com/api/eod/AAPL` | `core_stock_apis` | eodhd | ok |
| Daily OHLCV (second source) | `https://api.tiingo.com/tiingo/daily/AAPL/prices` | `core_stock_apis` | tiingo | ok |
| Daily/previous aggregate bars | `https://api.massive.com/v2/aggs/ticker/AAPL/prev` | `core_stock_apis` | massive | ok |
| End-of-day bars (third source) | `https://api.stockdata.org/v1/data/eod` | `core_stock_apis` | stockdata | ok |
| Intraday bars (multi-asset state, shorter rebalance clock) | `https://api.twelvedata.com/time_series` | `core_stock_apis` | twelvedata | ok |
| Technical indicators (MACD/RSI/CCI/ADX state features) | `https://www.alphavantage.co/query` | `technical_indicators` | alpha_vantage | ok |
| Intraday K-line via local gateway | `moomoo://get_cur_kline` | `technical_indicators` | moomoo | gateway (not live-probed) |
| Top-of-book snapshot (mid/spread, one symbol) | `moomoo://get_market_snapshot` | `core_stock_apis` | moomoo | gateway (not live-probed) |
| Risk-free rate (Sharpe denominator) | `https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2026/all` | `risk_free_curve` | federal_reserve | ok |
| Macro/regime features | `https://api.stlouisfed.org/fred/series/observations` | `macro_data` | fred | ok |
| News text (state features) | `https://eodhd.com/api/news` | `news_data` | eodhd | ok |
| News sentiment scores | `https://eodhd.com/api/sentiments` | `news_sentiment` | eodhd | ok |
| Corporate actions (price adjustment) | `https://eodhd.com/api/div/AAPL` | `corporate_actions` | eodhd | ok |
| Option chain (RL hedging variants) | `moomoo://get_option_chain` | `options_data` | moomoo | gateway (not live-probed) |
| Capital-flow features | `moomoo://get_capital_flow` | `capital_flow` | moomoo | gateway (not live-probed) |
| **L2/L3 order-book depth (market-making state, quote reward)** | — | — | — | **gap** |
| **Order-level event stream with timestamps (Hawkes intensities)** | — | — | — | **gap** |
| **Signed / metaorder execution data (impact parameter estimation)** | — | — | — | **gap** |
| **Sub-second decision clock and latency stamps (reward timing, peek-through test)** | — | — | — | **gap** |
| **Counterfactual market reaction to own orders (indirect impact)** | — | — | — | **gap** |

**What the gaps cost, quantified.** The four techniques on daily bars (2.2, 2.3, 2.4, 2.6) are buildable today from
the first five rows plus a risk-free rate; everything with an intraday or microstructure requirement is not.
**2.1** needs signed metaorder executions at child-fill granularity; the paper substitutes *simulated* TWAP
metaorders ($N$ 500–5000, $q_i\sim U[1,20]$, $T=21$), and its headline result is precisely that with only $N=500$
real-equivalent samples the model-based route is loss-making while DDPG is not — the missing tape costs nothing for
replication ($21$ steps, one asset) but everything for transfer. **2.5** is the heaviest consumer: 108 scenario
cells × 100 episodes × $1/\Delta t$ steps ($\Delta t=0.01,0.02$) ⇒ 3.24M state-action pairs from a Hawkes simulator
(self-excitation $0.7$, cross-excitation $0.3$, decay $0.1$); replacing that with history needs an event stream
resolving bid and ask arrivals separately at centisecond granularity, and the paper concedes historical LOB data
"cannot perfectly capture the market's reaction to the model's own trades" — the feed is a gap twice, as input and
as a validity limit. **2.6** needs a cost schedule and a decision clock, not exotic data, but the audit is only
meaningful at the clock the policy runs on: at a daily clock the corpus's own calibration puts the CAD premium at
$0$–$1$ bps/day, inside the cost model's noise; at a sub-second clock it does not, and there we have neither the
clock nor the latency stamps. **2.4**'s turbulence gate inverts a $30\times30$ covariance from daily returns; with
30 correlated mega-caps the effective rank is far below 30, so the gate is numerically fragile and wants a longer
history (2009→2020 in the paper) than the 2016→2020 test window.

## 4. Pitfalls, validation and measurement

- **Look-ahead is the default failure, not the exception.** Compute the Malliavin/Skorokhod correction $\Pi_{\rm ph}$
  on the implemented objective and set an explicit look-ahead window
  ($\|D_s\phi_t\|\le L\mathbb{1}_{\{t\le s\le t+\Delta t\}}$) so the bound $\tfrac12\|\Sigma\|_\infty\|D\phi\|$ is
  available. With typical settings the bias is positive with probability $0.6$–$0.8$; an unaudited RL backtest
  should be assumed optimistic (arXiv:2509.12764). Grading discipline:
  [`../qfin-st/backtest-methodology.md`](../qfin-st/backtest-methodology.md).
- **Match effort before comparing algorithms.** RL must get the same tolerance, batch size and risk budgets as the
  myopic baseline, and the comparison must be reported on mean, variance, loss-side CVaR and positivity
  probability; a mean-only comparison cannot show the documented dominance pattern (arXiv:2509.12764).
- **Train and evaluate on different draws, replicate the competitor, and report per regime.** arXiv:2607.06121
  trains on 500 episodes and validates on 1000 fresh simulations; the model-based competitor is replicated 100
  times because its out-of-sample PnL depends strongly on the finite estimation sample, reported as a mean plus the
  share of replications rejecting the zero-cash null (46%, 33%, 54%, 36% across regimes). One replication is
  uninformative. Regimes dominate the average: manipulation is unexploitable at high volatility and trivially
  exploitable at low volatility (arXiv:2607.06121); the ensemble's chosen algorithm flips 12 times in 18 quarters
  (arXiv:2511.12120); FinFlowRL's Sharpe ranges $0.28\to2.34$ across cells (arXiv:2510.15883).
- **Beware model selection masquerading as adaptation.** A 3-month validation Sharpe carries a standard error large
  enough to explain the whole ensemble-vs-single margin; freeze the selection rule before touching the test period,
  and never keep training on the test period while claiming it is out-of-sample (arXiv:2511.12120 does this).
- **Cost assumptions decide the answer.** The ensemble pays 0.1% per trade (arXiv:2511.12120); the audit counts
  commissions, spreads, depth/latency frictions, funding and a proportional tax under mark-to-market accounting
  (arXiv:2509.12764), and the corpus's own summary is that RL gains "tend to vanish" once frictions are reinstated
  and that a frictionless comparison "attenuates to statistical noise". Re-run everything with and without costs.
- **Simulator dependence is first order.** Replay cannot generate other participants' reactions, so replay-based
  execution or market-making PnL is not a realistic number (arXiv:2510.15883 states this; arXiv:2509.12764 requires
  an explicit CAD channel). Both MO and RL ride on a simulator — a calibrated SDE engine or a data-driven bootstrap
  — so discretisation and calibration errors are first-order: use weak higher-order schemes (cubature on Wiener
  space, Ninomiya–Victoir splittings) and dependence-respecting resampling pre-calibrated to spreads, impact and
  fill intensities.
- **Null tests are the acceptance gate.** An RL market-maker run across ten securities produced PnL statistically
  indistinguishable from zero under a Student $t$-test at 5% with $\mathrm{df}=9$ (arXiv:2509.12764). Adopt that
  test, plus the structural Hamiltonian-surplus inequality where applicable.
- **Reward misspecification is a compliance risk, not a tuning detail.** A model-free agent optimises exactly what
  it is given and will find the impact externality if the reward admits it (arXiv:2607.06121): constrain the action
  set or add a no-manipulation penalty before training.
- **Shaping choices have first-order behavioural consequences.** Homogeneous reward volatility never chooses
  immediate liquidation, and the stochastic-horizon grid world ends episodes early in a trap; both are correct
  answers to the objective as written and wrong answers to the financial question (arXiv:2602.12030).
- **Couple exploration and state the regularity preconditions.** $M$ and $\eta$ are not independent: the error is
  $CM^2|\eta\ln\eta|+CM^{-\kappa/2}$, so require $M^2|\eta\ln\eta|\to0$ and choose $(M,\eta)$ where the value
  function is insensitive to both (arXiv:2604.02035). The stopping-problem bounds need a Hölder utility and a large
  discount rate; the audit needs non-degenerate (Hörmander) dynamics; PPO clipping and DDPG target networks need
  stationary-enough rewards.

## 5. Recommended first implementation in FinRobot

Ranked by value per unit of effort against what the data layer can fetch today. Items 1–5 are buildable now on
daily/intraday bars; item 6 is simulation-only by construction; items 7–8 are blocked on a book feed.

1. **RL-vs-myopic walk-forward harness with the four-metric report.** Any policy (RL or rule-based) plus a
   train/validation/test split, an explicit rebalancing clock and a cost schedule, emitting conditional mean PnL,
   variance, loss-side CVaR and probability of non-negative PnL beside an adapted myopic baseline on identical
   clocks. *Data:* eodhd `eod` / tiingo `prices`; `federal_reserve` for $r_f$. *Passing:* no RL result published
   without the baseline on the same split and clock. *Risk:* only as honest as its cost model. *Effort:* S.
2. **Look-ahead audit gate in the training loop.** Recompute the policy gradient with future information removed
   and report the gap as
   $S^{\rm self}_{0\to K}=\eta\sum_k\langle b_k,g^{\rm impl}(\theta_k)-g^{\rm naive}(\theta_k)\rangle$; reject a
   run whose contamination is not zero within bootstrap error. *Data:* none beyond training logs. *Passing:* the
   audit runs on the implemented objective and flags edges coinciding with a look-ahead window. *Risk:* needs
   per-step gradients exposed by the loop. *Effort:* M.
3. **Inhomogeneous reward-volatility objective as a selectable risk term.** $\mathbb{E}_\pi[G]-\beta\varsigma^2_\pi$
   with per-step targets $\bar r_{\pi,i}$ and the IVO gradient, as a drop-in alternative for execution/hedging.
   *Data:* per-period mark-to-market PnL the engine already produces. *Passing:* the policy family spans
   linear-to-front-loaded as $\beta$ rises, which the homogeneous objective never does. *Risk:* target
   re-estimation couples outer search and inner solve. *Effort:* M.
4. **Ensemble actor-critic selector with a separately reported crash gate.** PPO + A2C + DDPG on the 181-dimensional
   state z-scored per window, quarterly retrain, validation-Sharpe selection, turbulence kill-switch as a removable
   overlay. *Data:* daily OHLCV (eodhd/tiingo/massive/stockdata cross-checks), `alpha_vantage` indicators,
   `federal_reserve` $r_f$. *Passing:* reproduce the reported ordering on 2016-01→2020-05 with costs and *stop
   training at the test boundary*; if the ordering disappears without the crash gate, say so. *Risk:* noisy
   3-month selection. *Effort:* M.
5. **Two-threshold speculative entry/exit controller for pair spreads.** The OU-signal stopping problem with Gibbs
   exploration densities and an intensity cap ($M=50$, $\eta=10^{-5}$), trained by offline policy iteration with
   2×32 value networks. *Data:* daily bars of both legs (eodhd `eod`), spread built offline; pair selection is
   [`../qfin-st/mean-reversion-pairs.md`](../qfin-st/mean-reversion-pairs.md). *Passing:* learned value functions
   match a finite-difference HJB solve on the same OU grid, residual at the free boundary $p^*(b)$, exit boundary
   increasing in the entry price. *Risk:* one-dimensional signal, so costs on both legs are not represented.
   *Effort:* M.
6. **Manipulation-regime stress test (simulation-only, clearly labelled).** The non-linear-impact AC environment
   with DDPG, the full-information SLSQP benchmark and an estimated-parameter variant, as a *negative control* on
   our own stack: if we cannot recover the pump-and-dump shape and positive cash at $\sigma=0.003$ while failing at
   $\sigma=0.0168$, our simulator or reward plumbing is wrong. *Data:* none. *Passing:* the volatility ordering of
   arXiv:2607.06121 reproduces; never surfaced as a tradable strategy, and the reward carries an explicit
   manipulation penalty. *Risk:* it teaches the house style of rewarding impact; fence it off. *Effort:* M.
7. **Imitation+RL market-making skeleton, expert-first.** The GLFT/AS expert pool and the frozen-generator +
   noise-policy split against a Hawkes simulator, validated against the corpus numbers before touching live data.
   *Data:* simulator; the state $(t,X_t,q_t,S_t,\mathrm{spread}_t)$ needs only a spread, so
   `moomoo://get_market_snapshot` (gateway) is the minimum real input. *Passing:* fine-tuned Sharpe beats the same
   expert it was cloned from in every cell ($0.50/0.28/2.34/1.36$ vs $0.37/0.22/1.83/1.07$), training time
   $\le1.0\times$ vanilla PPO, inference $<10\ \mu$s. *Risk:* expert selection is in-sample; only the fine-tune
   margin is evidence. *Effort:* L.
8. **Register an order-level/L2 ingestion path as a first-class data category.** Add the feed and an
   `order_book_depth` / `tick_trades` category so that $\theta,\delta,\kappa$ estimation (item 6), Hawkes
   intensities and the sub-second clock become possible. *Data:* the feed itself. *Passing:* one symbol-quarter
   loads and yields both signed metaorders and per-side arrival intensities. *Value:* without it items 6–7 stay
   simulator-bound and item 2 cannot run at the clock where the CAD premium is large. *Effort:* L.

## Appendix — papers read

| arXiv id | Title | Year |
|---|---|---|
| 2607.06121v1 | Can Reinforcement Learning Efficiently Discover Price Manipulation? | 2026 |
| 2604.02035v1 | Reinforcement Learning for Speculative Trading under Exploratory Framework | 2026 |
| 2602.12030v1 | Time-Inhomogeneous Volatility Aversion for Financial Applications of Reinforcement Learning | 2026 |
| 2511.12120v1 | Deep Reinforcement Learning for Automated Stock Trading: An Ensemble Strategy | 2025 |
| 2510.15883v1 | FinFlowRL: An Imitation-Reinforcement Learning Framework for Adaptive Stochastic Control in Finance | 2025 |
| 2509.12764v1 | Myopic Optimality: why reinforcement learning portfolio management strategies lose money | 2025 |
