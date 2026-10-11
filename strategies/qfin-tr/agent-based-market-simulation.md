# Agent-Based Market Simulation — learnings from the q-fin.TR corpus

`227` of 2370 corpus papers matched this category (227 with PDFs); this doc is based on a close reading of `6`.

Headline: **this category is a *simulation* literature, not a data literature.** All six build a synthetic
market whose prices emerge from a matching engine plus agent behaviour, then ask whether the emergent path reproduces
the stylized facts of real markets. That inverts the usual data-layer dependency: the engine and agents are
self-contained code, and their only external need is a *calibration target* (a historical price series and, for the
strongest validations, a limit-order book). The doc covers market *mechanics* — order-level
calibration, validation against real stylized facts, and the failure modes that make an ABM untrustworthy — and
defers the agent-behaviour survey to
[`../qfin-st/market-simulation-agent-models.md`](../qfin-st/market-simulation-agent-models.md), which already reads
arXiv:2312.14903 and derives the ZI/LLM-agent taxonomy.

## 1. What the corpus actually offers

- **A distributed ABM reaches 30 assets and ~108,500 agents on three commodity machines and reproduces six
  univariate stylized facts with zero historical calibration.** The entirely zero-intelligence baseline yields
  heavy tails, no return autocorrelation, volatility clustering, nonlinear dependence, gain/loss asymmetry and
  aggregational Gaussianity — and *fails* exactly the facts needing volume- or history-conditioned agents: long
  memory of volume, volume–volatility correlation, the leverage effect, intraday volume patterns and cross-asset
  correlations (arXiv:2312.14903). Scale: 1 / 5 / 30 assets with 70+70+2 / 650+5,850+200 / 8,000+100,000+500
  LT+LP+MM agents. Throughput was the binding constraint — 45,000 trades in 30 min at medium scale collapsed to
  2,000 at large scale because one SQLite gateway serialised order processing (arXiv:2312.14903).
- **Simulation fidelity is a *measured* object, and the accepted metric is a weighted stylized-facts distance.**
  The high-frequency E-mini S&P 500 simulator calibrates seven parameters per trading day by minimising
  \(D(\theta)=w_1\Delta_{\text{Hill}}+w_2\Delta_{V}+w_3\Delta_{ACF^1}+w_4\Delta_{ACF^2}\), with weights equal to the
  inverse block-bootstrap sampling variance of each historical moment (arXiv:2208.13654). The resulting moment
  coverage ratios — the fraction of resampled simulated paths whose moment lies inside the historical confidence
  band — range from **10.0%** (squared-return ACF at lag 60 on 2010-05-04) to **100.0%** across 9 moments and 4 days;
  tail-index coverage is 98.3/66.7/98.3/100% on May 3–6, volatility coverage 0/85/100/56.7% (arXiv:2208.13654).
- **A 100 ms-step ABM reproduces the May 6 2010 flash crash in shape, amplitude and duration.** 324,000 steps per
  9-hour day; an institutional "Sell Algorithm" targeting \(r=9\%\) of the previous minute's volume, liquidating
  \(Q=120{,}000\) E-mini contracts from 14:30, produced a ≈**7%** total drawdown with a **4.16%** drop inside
  2 minutes (14:40:50→14:42:20), an intraday low of 1053.5, and a ≈17-minute execution vs ≈20 minutes historically.
  Book depth fell from ≈5,000 to <1,000 per side (bid depth reached zero for ~30 s), and the spread widened past
  20 ticks — all as *emergent* properties, not inputs (arXiv:2208.13654).
- **Flash-crash severity is non-monotone in two of its three controls.** Over Monte Carlo sweeps the amplitude
  rises with the Sell Algorithm's POV \(r\) but **plateaus once \(r>5\%\)** (fundamental demand caps the achievable
  low); rises with the market-maker inventory limit below ≈8,000 and **falls above it** (enough capacity to absorb
  the flow); and falls monotonically as fundamental traders trade more frequently (arXiv:2208.13654). Mini crashes
  (a \(k\)-sd move, \(k\in\{2,3,4\}\), reversing within 10 min) show the same inverted-U in the inventory limit but
  are **insensitive** to fundamental-trader frequency — they complete faster than low-frequency traders can react
  (arXiv:2208.13654).
- **RL agents inside the ABM beat both rule-based agents and untrained controllers on stylized-fact realism, but
  only if training continues during the simulation.** Excess kurtosis of 10-second returns: real data **92.26**,
  100 ZI agents **3.15**, pre-trained-then-continued PPO **10.24**, pre-trained-frozen **142.65**, untrained **74.25**;
  increasing the sampling interval to 120 s decays these to 2.41 / 0.84 / 3.76 / 54.01 / 16.86 respectively
  (arXiv:2403.19781). Continual learning also gave the flattest market-maker inventory path and the only realistic
  post-shock trajectory — a drop recovering *below* the pre-shock price, i.e. permanent plus temporary impact
  (arXiv:2403.19781).
- **A discrete-event ABM makes latency a first-class, cheap parameter.** The Figgie simulator runs 10,000 events per
  game on a min-heap queue (\(O(1)\) next event, \(O(\log n)\) insertion) and simulates per-agent market latency
  without storing historical books by delaying only the *add-order* event (arXiv:2110.00879). Over 100 simulations
  the fundamentalist averaged cash **\$407.5** / bonus **\$75.43**, best of the tested strategies; the *chartist*
  diverged — its recursive value estimate overflowed double precision within one game (arXiv:2110.00879).
- **Herding is an amplifier, not a necessary condition for momentum.** In a 400-agent 20×20 lattice model with
  Gaussian beliefs, information-diffusion alone produces gradual adjustment and even overshoot; mean time to reach
  the signal-implied mean was **15.41 periods** at degree 4 (von Neumann) vs **9.22 periods** at degree 8 (Moore).
  Adding imitation (herding intensity \(\gamma\) = 0.1→0.5) clusters trading and fattens return tails; with both
  mechanisms together the price overshoots and then reverses (arXiv:2607.27063).
- **One assigned paper is a cross-listed primer, not market evidence.** arXiv:1909.11650 is stamped `[cs.MA]`, not
  `q-fin.TR`, and is explicitly an expository explanation of ABM components. It is retained because it is the only
  paper in the set that specifies the *exogenous fundamental-value process* (discrete mean-reverting, Ornstein–
  Uhlenbeck, and "megashock" variants), the Bayesian belief recursion, and the ZI/Heuristic-Belief-Learning agents
  that the other five either assume or cite. None of the six is off-topic; 1909.11650 is retained as the
  methodological specification, used as method, not empirical findings.

## 2. Implementable formulas & algorithms

### 2.1 Discrete-event continuous-double-auction engine with cheap latency
**Purpose.** Drive a market from asynchronous agent decisions rather than fixed time steps, so that event timing,
latency and order-book matching are all explicit and testable.

**Formula.** Two event types. A *consideration* event schedules the next look by agent \(i\) at
\(t_0 + X,\ X\sim \text{Exp}(C_i),\ \mathbb{E}[X]=1/C_i\). An *add-order* event inserts an order into asset \(j\)'s
book and (because it is the only mutation point) runs that asset's matcher:
$$\text{while } b_p \ge s_p:\quad v=\min(q_b,q_s,q_{\text{seller}});\ \text{settle } v;\ \text{return residual}.$$
Latency \(\lambda\) is simulated cheaply by having the agent consider at \(t_0\) (seeing the book *as of* \(t_0\))
but injecting the resulting order at \(t_0+\lambda\); this is equivalent to letting it act on stale data but avoids
storing historical books (the memoryless-equivalent "delay the send" trick). A single machine's matching engine is
the serialisation point; agents run in parallel threads/processes.

**Required inputs.** Per-agent consideration rates \(C_i\), the price/side/size the agent elects, and a latency
\(\lambda_i\). No external data.

**Parameters & defaults.** Figgie: 4 agents, 4 assets, 10,000 events per game, per-agent latency 0 vs 100
(arXiv:2110.00879). Scalable ABM: agent decision-making and order processing computationally decoupled; price-time
priority; 30 assets simultaneously (arXiv:2312.14903). Tick granularity for the high-frequency variant: \(\Delta t =
100\) ms, 324,000 steps/day (arXiv:2208.13654).

**Observed effect sizes.** In a zero-sum homogeneous game every player ends at the same expectation (wealth \$400,
cash \$350, bonus \$50), so *any* per-strategy claim must be tested against that null; standard deviations of final
payout were 201.04 (noise), 61.75 (fundamentalist), 48.63 (bottom-feeder), with one-tailed tests \(p<10^{-5}\)
except fundamentalist-vs-noise payout at \(p=0.013\) (arXiv:2110.00879).

**Failure modes.** The cheap trick models only trader↔exchange latency, not an agent-to-agent latency *matrix*
(arXiv:2110.00879). Agents resubmit only after their order enters the book, coupling frequency to latency — the
low-latency agent traded *worse* on cash in homogeneous tests. Tests must be bootstrap/dependence-aware because a
zero-sum game makes outcomes non-independent and bimodal (arXiv:2110.00879).

### 2.2 Stylized-facts distance and moment-coverage validation
**Purpose.** Turn "the simulation looks realistic" into a minimisable loss with an out-of-sample coverage check.

**Formula.** With historical (\(h\)) and simulated (\(s\)) moments,
$$D(\theta)=w_1|\text{Hill}_s-\text{Hill}_h|+w_2|V_s-V_h|+w_3\Delta_{ACF^1}+w_4\Delta_{ACF^2},\qquad
w_i=1/\sigma_i^2,\qquad \hat\theta=\arg\min_{\theta\in\Theta} D(\theta),$$
$$\Delta_{ACF^1}=\frac{1}{|\text{lags}|}\sum_l|\text{ACF}_s(l;r)-\text{ACF}_h(l;r)|,\qquad
\Delta_{ACF^2}=\frac{1}{|\text{lags}|}\sum_l|\text{ACF}_s(l;r^2)-\text{ACF}_h(l;r^2)|.$$
\(V\) = realised volatility of second-level returns; the Hill estimator of the tail index is applied to *absolute*
returns (it measures heavy-tailedness without sign asymmetry). Validation is not the loss value but the **moment
coverage ratio**: resample simulated paths, compute each moment, and report the fraction that fall within the
historical sampling band.

**Required inputs.** A millisecond/centisecond mid-price series for the historical target and the same-length
simulated series; for the high-frequency paper these came from a 10-level limit-order-book feed (both sides).

**Parameters & defaults.** Hill on 1-second returns; return-ACF lags \(\{30,31,32,60,61,62,90,91,92\}\) (9 lags) and
squared-return-ACF lags \(\{1,2,3,30,\ldots,92\}\) (12 lags), each smoothed by a 3-lag average to damp single-lag
noise; sampling variances \(\sigma_i^2\) estimated by block bootstrap on the historical series; seven parameters
calibrated per day, others frozen (arXiv:2208.13654).

**Observed effect sizes.** Calibrated coverage across four days: Hill 98.3/66.7/98.3/100%, volatility
0/85/100/56.7%, return ACF(30) 85/78.3/50/90%, squared-return ACF(1) 100/98.3/95/93.3% (arXiv:2208.13654).

**Failure modes.** The weights encode only historical sampling variability, so a moment can "pass" because the band
is wide, not because the model is right; a single low-coverage cell (10% at squared-return lag 60 on 2010-05-04)
signals a genuine miss that the averaged loss hides, and volatility matched worst on May 3 (0% coverage) — the
calibration sacrifices one moment to gain another.

### 2.3 Exogenous fundamental-value process and Bayesian belief recursion
**Purpose.** Give agents something to be right or wrong about; without a fundamental series there is no reason for a
stock to trade at \$5 rather than \$5,000 (arXiv:1909.11650). This is the input the price-clearing step (2.5)
and the demand functions (2.4) both consume.

**Formula.** Discrete mean-reverting series (never negative):
$$r_t=\max\{0,\ \kappa\bar r+(1-\kappa)r_{t-1}+u_t\},\quad r_0=\bar r,\quad u_t\sim N(0,\sigma_s^2).$$
Continuous Ornstein–Uhlenbeck alternative, samplable directly at any future time (Markov), which lets a
sparse-arrival simulation *skip* idle periods:
$$Q_t\sim N\!\Big(\mu+(Q_0-\mu)e^{-\gamma t},\ \tfrac{\sigma^2}{2\gamma}(1-e^{-2\gamma t})\Big).$$
"Megashock" variant: layer onto the OU series a Poisson-arriving bimodal shock (two equal-variance Gaussians of
opposite sign, means far from zero, high variance) to obtain realistic intraday jumps. An agent that wakes at time
\(t\) with noisy observation \(o_t=r_t+n_t\), \(n_t\sim N(0,\sigma_n^2)\), advances its beliefs through the sleep
interval \(\delta=t-t'\) and folds in the observation:
$$\tilde r_t\leftarrow \big(1-(1-\kappa)^\delta\big)\bar r+(1-\kappa)^\delta \tilde r_{t'},\qquad
\tilde\sigma_t^2\leftarrow (1-\kappa)^{2\delta}\tilde\sigma_{t'}^2+\sigma_s^2\frac{1-(1-\kappa)^{2\delta}}{1-(1-\kappa)^2},$$
$$\tilde r_t\leftarrow \frac{\sigma_n^2}{\sigma_n^2+\tilde\sigma_{t'}^2}\tilde r_{t'}+\frac{\tilde\sigma_{t'}^2}{\sigma_n^2+\tilde\sigma_{t'}^2}o_t,\qquad
\tilde\sigma_t^2\leftarrow \frac{\sigma_n^2\tilde\sigma_{t'}^2}{\sigma_n^2+\tilde\sigma_{t'}^2},\qquad
\hat r_t\leftarrow \big(1-(1-\kappa)^{T-t}\big)\bar r+(1-\kappa)^{T-t}\tilde r_t.$$
A practical alternative used by the flash-crash simulator: treat the fundamental as the hidden state of a linear
Gaussian system and extract it from the traded price with a **Kalman smoother** (e.g. `pykalman`) applied per
trading day (arXiv:2208.13654).

**Required inputs.** A price/valuation series to anchor or extract the fundamental; the process parameters; macro or
news events for megashocks (optional).

**Parameters & defaults.** \(\bar r\), \(\kappa\in[0,1]\), shock variance \(\sigma_s^2\), observation noise
\(\sigma_n^2\); "tuned" agents are assumed to know \(\bar r,\kappa,\sigma_s^2\) but not the realised \(u_t\).
Megashock rate/variance are free. Kalman extraction is applied day-by-day to the E-mini S&P 500 series
(arXiv:2208.13654).

**Observed effect sizes.** The Bayes weights are the *inverse* of the usual intuition — the prior is weighted by
\(\sigma_n^2\) and the fresh observation by the agent's own error \(\tilde\sigma_{t'}^2\) (reversed-variance
mixing), correct because higher error should shift weight *onto* new evidence (arXiv:1909.11650). The OU form lets
nanosecond-resolution simulations skip empty time and still cover days.

**Failure modes.** The true fundamental is unobservable and "one series per equity, agent-independent,
predetermined" (agent actions never feed back into it) — false for crowded trades (arXiv:1909.11650). A
Kalman-smoothed fundamental is an extracted, not economic, quantity and inherits the price series' regime. Discrete
mean-reversion must evaluate *every* step in order, so prefer the OU form when agents arrive rarely.

### 2.4 Heterogeneous demand functions (fundamental / momentum / noise / market-maker)
**Purpose.** Populate the auction with a minimal, interpretable, stationary set of behavioural rules that can be
calibrated to real stylized facts.

**Formula.** Extended-Chiarella block (arXiv:2208.13654):
$$D^{FT}=\gamma_1(V_t-P_t)+\gamma_2(V_t-P_t)^3\quad\text{(market orders only)},$$
$$M_t=(1-\zeta)M_{t-1}+\zeta(p_t-p_{t-1}),\qquad f(M_t)=\gamma\tanh(M_t)\quad(\text{momentum}).$$
Noise traders submit buy/sell with equal probability (a random walk in aggregate demand). Market makers quote both
sides at a distance from mid sampled \(\sim U(0,p^{MM}_{edge})\), with a higher cancellation rate than other agents,
and *[INFERENCE]* a position limit that forces quoting suspension plus aggressive inventory unwinding. The
zero-intelligence scalable variant instead uses a Dirichlet(1.0, \(K\)) portfolio target for liquidity takers and a
lognormal-shifted limit price \(p^L=p_{mid}(1+X),\ X\sim N(0,\sigma_{p_{mid}})\) for liquidity providers
(arXiv:2312.14903).

**Required inputs.** The fundamental series \(V_t\) from 2.3; observed prices; order volume \(V\) per order.

**Parameters & defaults.** \(\zeta_L=0.01\) (≈hourly trend), \(\zeta_S=0.9\) (mimics HFT); \(\gamma_{NT}=0.3403\),
\(\gamma_1=0.1390\), \(\gamma_2=0.4562\), \(\gamma_L=0.3017\); \(N_{FT}=N_{LMT}=N_{SMT}=N_{NT}=30\), \(N_{MM}=20\); order
volume 100; fundamental-trader interval \(S^{FT}_{interval}=100\) vs market-maker interval 1; market-maker edge max
\(p^{MM}_{edge}=4\); \(\psi^{MM}_{limit}=7000\) (flash-crash config), \(\psi^{MM}_{safe}=101\),
\(\psi^{MM}_{rest}=12000\) (arXiv:2208.13654). Scalable ABM: MM \(\epsilon\in[-0.5,1.0]\), unit trade size 100
(arXiv:2312.14903).

**Observed effect sizes.** The calibrated values reproduce fat-tailed returns, negative short-lag return
autocorrelation and slowly decaying squared-return autocorrelation; market makers are *required* for realistic book
behaviour because ≈80% of real market-maker orders are passive (arXiv:2208.13654, citing Menkveld 2013). The
scalable baseline shows the action *structure alone* gives the first six stylized facts, so the demand block mainly
buys the *volume* and *regime* facts (arXiv:2312.14903).

**Failure modes.** Parameters are only weakly identified by macro stylized facts, so many \((\theta)\) sets pass;
the momentum demand is bounded by \(\tanh\) saturation, so it cannot generate runaway trends — deliberate, but it
removes a mechanism. Market-maker inventory limits are the single most leverage-heavy parameter for crash
outcomes (see 2.7).

### 2.5 Network herding, market clearing, and finite-speed information diffusion
**Purpose.** Model momentum/reversal as the joint effect of delayed information and local imitation, and clear the
market from heterogeneous beliefs rather than an imposed aggregate demand.

**Formula.** Agent \(i\) holds Gaussian belief \(\hat x_i\) about next-period price. Action propensities are
logistic in perceived mispricing around an inaction band \(\Delta\):
$$\pi^S_i(x)=\frac{1}{1+e^{-k[x-(1+\Delta)\hat x_i]}},\qquad
\pi^B_i(x)=\frac{1}{1+e^{k[x-(1-\Delta)\hat x_i]}},\qquad \pi^H=1-\pi^B-\pi^S.$$
Herding mixes own propensity with the observed action share \(h^a_i=n^a_i/d_i\) of network neighbours:
$$\tilde\pi^a_i(x)=(1-\gamma)\pi^a_i(x)+\gamma h^a_i,\quad a\in\{B,S,H\}.$$
Optimal mean-variance position and expected signed demand, with the price set at the feasible root of aggregate
demand nearest the previous price:
$$q^*_{i,t}=\frac{\mathbb{E}_{i,t}(X_{t+1})-X_t e^{r_f}}{2\lambda_i V_{i,t}(X_{t+1})},\qquad
D_{i,t+1}(x)=q^*_{i,t}\big(\tilde\pi^B_i(x)-\tilde\pi^S_i(x)\big),\qquad
X_{t+1}=\arg\min_{x>0}\Big\{|x-X_t|:\textstyle\sum_i D_{i,t+1}(x)=0\Big\}.$$
Information diffusion is a *separate* process: a signal \(I_t=\{x^*,\sigma^*,p\}\) reaches at most \(M\) previously
uninformed neighbours per period; a reached agent's mixture belief has mean \(\mu^I_{i,t+1}=(1-p)\hat x_i+px^*\)
and variance \(v^I_{i,t+1}=(1-p)\hat\sigma_i^2+p\sigma^{*2}+p(1-p)(\hat x_i-x^*)^2\), and it re-solves \(q^*\) with
\((\mu^I,v^I)\). Setting \(\gamma=0\) isolates rational underreaction; holding beliefs fixed and varying \(\gamma\)
isolates imitation.

**Required inputs.** Per-agent priors \((\hat x_i,\hat\sigma_i)\), the network graph \(G=(V,E)\), risk aversion
\(\lambda_i\), risk-free rate \(r_f\), and the signal tuple.

**Parameters & defaults.** \(\Delta=0.01\), \(k=0.03\), \(\lambda_i=0.5\), \(r_f\) one-period,
\(\hat x_i\sim N(3000,30^2)\), \(\hat\sigma_i\sim N(30,5^2)\) truncated positive, \(p=0.6\), \(x^*=3100\),
\(\sigma^*=10\), \(N=400\) on a 20×20 lattice; \(\gamma\in\{0.1,0.3,0.5\}\); 500 periods; von Neumann (degree 4) and
Moore (degree 8) topologies, validated on Erdős–Rényi and Watts–Strogatz graphs (arXiv:2607.27063).

**Observed effect sizes.** Herding alone raises excess kurtosis and produces spatially clustered trading; the
degree-8 lattice halves convergence time (9.22 vs 15.41 periods); information+herding produces overshoot then
reversal while information alone does not (arXiv:2607.27063).

**Failure modes.** Aggregate demand can have multiple roots, so the *nearest-root* rule is a numerical convention
that may pick a different equilibrium than a solver (arXiv:2607.27063); the network is exogenous; the Gaussian prior
and three-action rule abstract away wealth dynamics and book microstructure, and CSAD/LSV cannot separate imitation
from common information (arXiv:2607.27063).

### 2.6 RL market-maker and liquidity-taker agents trained inside the ABM
**Purpose.** Replace hard-coded agent rules with policies that adapt to conditions the rules cannot anticipate, and
study whether learning changes market realism.

**Formula.** Each agent solves an MDP \((S,A,R,P,\gamma_{disc})\) with PPO. Market-maker action = three numbers
splitting buying power and setting the quote geometry:
$$p_{ask}=p_{mid}+s\Big(\tfrac{1+\epsilon_s}{2}+\epsilon_a\Big),\qquad
p_{bid}=p_{mid}-s\Big(\tfrac{1+\epsilon_s}{2}-\epsilon_a\Big),$$
where \(s\) is the spread, \(\epsilon_s\) the symmetric (spread-width) tweak and \(\epsilon_a\) the asymmetric
(level-shift) tweak. Rewards share a PnL-plus-target term:
$$r^{(MM)i}_t=\omega\big(\alpha(\Delta \text{PnL}_t-\gamma|\Delta\text{PnL}_{inventory,t}|)\big)-(1-\omega)|P_{ti}-P_{t*,i}|,$$
$$r^{(LT)i}_t=\omega\big(\alpha(\Delta \text{PnL}_t-\gamma|\Delta\text{PnL}_{inventory,t}|)\big)
-\tfrac{1-\omega}{2}\sum_{s\in\{buy,sell\}}\Delta\big|f^{*,i}_{s}-n^{(t-\tau,t)}_{s}/\tau\big|.$$

**Required inputs.** Observation = mid-prices for the past 5 steps, prices and quantities of the top 5 LOB levels,
liquidity-provision percentage, current inventory, buying power. No external data: the simulator supplies
everything. (Contrast: historical replay cannot generate *indirect* impact — see
[`../qfin-st/microstructure-execution.md`](../qfin-st/microstructure-execution.md) §2.5.)

**Parameters & defaults.** PPO; 4 MM + 10 LT agents; MM \(\omega=0.5,\gamma=0.15,\alpha=0.09,P_{t*,i}\in\{0.5,1.0\}\);
LT \(\omega=0.5,\gamma=0.9,\alpha=0.01\), order size 18; random latency via FIX/SHIFT. Groups: A = pre-train 10 h
(36,000 steps) then train through a 10 h simulation, B = pre-trained frozen, C = untrained (arXiv:2403.19781).

**Observed effect sizes.** 10-second return kurtosis — real 92.26, ZI 3.15, Group A 10.24, Group B 142.65,
Group C 74.25 (decaying with \(\Delta t\)); Group A market makers earned \$1.26 M from spread and lost \$0.22 M on
inventory; inventory risk 3660.89 / 4565.03 / 3698.15 for A / B / C; on an imbalanced book Group A quotes deeper
(higher \(\epsilon_s\)) and lower (negative \(\epsilon_a\)), matching documented spread-widening and quote-shifting
behaviour (arXiv:2403.19781).

**Failure modes.** Calibration of a non-stationary, real-time RL-ABM is unsolved and the paper does *not* calibrate
to real data the way a rule-based ABM can; only 10 seeds; untrained agents overshoot into a permanent price drop and
frozen agents recover too fully — the *training protocol* is a hidden degree of freedom (arXiv:2403.19781).

### 2.7 Flash-crash and mini-crash scenario generation
**Purpose.** Use the calibrated ABM as a stress testbed: inject a realistic cascade trigger and measure emergent
severity.

**Formula.** The trigger is an institutional sell program that follows volume, ignoring price and time:
$$\text{execute rate } r = 9\%\ \text{of prior-minute volume};\quad
\text{child volume } vol=V\,r\,\tfrac{n}{60}\ \text{every } n\ \text{seconds},$$
forced to continue until inventory \(Q\) is exhausted. A "spiking trader" (mini-crash variant) is inactive with high
probability and, when triggered, submits \(N_{spike}\) same-direction market orders of volume \(V_{spike}\). Severity
is the *prominence* of the trough (not the raw low), so that mini-crash amplitudes are comparable across paths; a
mini crash is a \(k\)-sd price move reversing within 10 minutes, \(k\in\{2,3,4\}\), with the standard deviation
taken from minute-level returns.

**Required inputs.** An intraday volume history for the POV controller; calibrated agent block; position limits.
No live external data beyond the calibration tape.

**Parameters & defaults.** \(r=9\%\), \(Q=120{,}000\), \(n=12\) s, MM inventory limit 7000, fundamental interval
\(S^{FT}_{interval}=100\) (flash-crash config); mini-crash config: \(N_{MM}=5\), 2 spiking traders,
\(N_{spike}=4\), \(p_{spike}=0.005\), \(V_{spike}=100\) (arXiv:2208.13654). Monte Carlo uses the 50% quantile of
simulated amplitudes (40%/60% also recorded) to suppress outliers.

**Observed effect sizes.** Flash crash amplitude ≈7%, 4.16% inside <2 min, ~17 min execution vs ~20 min historical,
depth <1,000/5,000, spread >20 ticks, bid side zero for ~30 s. Amplitude is *increasing then flat* in \(r\)
(plateau past 5%), *inverted-U* in the MM inventory limit (peak ≈8,000), *decreasing* in fundamental-trader
frequency. Mini crash: ≈80 bp in seconds, ≈60 bp in 5 s; frequency falls as the inventory limit rises but is
unchanged by fundamental-trader frequency (arXiv:2208.13654).

**Failure modes.** Calibration uses only the *morning* session (8:00–12:30) to avoid overfitting the afternoon
event, but MM limit and fundamental frequency are then hand-tuned for the crash — a documented degree of freedom
(arXiv:2208.13654). The "hot-potato" cascade requires finite MM inventory limits; with infinite limits no crash
occurs, so the result is conditional on a modelling choice real risk management forces. Cross-market contagion and
circuit breakers are unimplemented; see
[`../qfin-st/correlation-networks-econophysics.md`](../qfin-st/correlation-networks-econophysics.md).

## 3. Data requirements → available endpoints

Provider rows are real entries in `strategies/endpoints.json`; **gap** = no current provider serves the input.
The engine, demand block, network and RL loop are self-contained *code* and need no live feed; the rows below are
the *calibration and stress-input* needs.

| Input | Endpoint | Category | Provider | Probe status |
|---|---|---|---|---|
| Daily OHLCV (fundamental anchor, volatility target, calibration) | `https://eodhd.com/api/eod/AAPL` | `core_stock_apis` | eodhd | ok |
| Daily OHLCV (secondary) | `https://api.tiingo.com/tiingo/daily/AAPL/prices` | `core_stock_apis` | tiingo | ok |
| Daily/prev aggregate bars | `https://api.massive.com/v2/aggs/ticker/AAPL/prev` | `core_stock_apis` | massive | ok |
| Intraday minute bars (volume profile, coarse calibration) | `https://api.twelvedata.com/time_series` | `core_stock_apis` | twelvedata | ok |
| Intraday K-line via local gateway | `moomoo://get_cur_kline` | `technical_indicators` | moomoo | gateway |
| Top-of-book snapshot (coarse mid only) | `moomoo://get_market_snapshot` | `core_stock_apis` | moomoo | gateway |
| Tradable symbol universe / tick sizes | `https://eodhd.com/api/exchange-symbol-list/US` | `exchange_symbols` | eodhd | ok |
| News stream (megashock / external-impact timing) | `https://eodhd.com/api/news` | `news_data` | eodhd | ok |
| Macro release calendar (megashock schedule) | `https://api.stlouisfed.org/fred/series/observations` | `macro_data` | fred | ok |
| Economic calendar via local gateway | `moomoo://get_economic_calendar` | `economic_calendar` | moomoo | gateway |
| Market breadth (advance/decline, aggregate stress) | `moomoo://get_rise_fall_distribution` | `market_breadth` | moomoo | gateway |
| Index option surface (implied-vol stress target) | `https://cdn.cboe.com/api/global/delayed_quotes/options/_SPX.json` | `options_surface` | cboe | ok |
| Event-outcome probabilities for scenario weighting | `https://gamma-api.polymarket.com/markets` | `prediction_markets` | polymarket | ok |
| **L2/L3 book depth (10 levels, both sides)** | — | — | — | **gap** |
| **Market-by-order tick stream with aggressor flag** | — | — | — | **gap** |
| **Order-level cancellations / queue positions** | — | — | — | **gap** |
| **Investor-level network / social-interaction panel** | — | — | — | **gap** |
| **"True" fundamental-value series (dividend-implied)** | — | — | — | **gap** |

**What each gap costs, quantified.** (i) *L2/L3 depth*: the strongest calibration in the set
(arXiv:2208.13654) targets **10 LOB levels per side** at millisecond resolution for four days of E-mini S&P 500
futures; the RL-ABM (arXiv:2403.19781) needs **top-5 levels** for one day of GOOG/AAPL/AMZN. Without depth the
stylized-facts distance of §2.2 can only target price-moment facts (Hill, volatility, ACFs) and loses depth, spread
and cancellation-rate facts entirely. (ii) *Tick/event stream with aggressor*: the §2.1 engine cannot be checked
against real order flow, and the scale gap is severe — 2312.14903 already throttled to 2,000 trades/30 min at 30
assets, against \(O(10^6)\) messages/day for one real name. (iii) *Cancellations/queue positions*: they set the
per-agent-type cancellation probability that separates market-maker (high cancel) from taker (low cancel) books in
both 2208.13654 and 2312.14903. (iv) *Network/social panel*: the graph calibration of arXiv:2607.27063 is
unavailable; its empirical proxy is daily CSAD/LSV on the SSE 50, 2015–2024, in 30-trading-day rolling windows,
which cannot identify who observes whom. (v) *True fundamental series*: all three generators in §2.3 are
unobservable, so the "value" anchor is synthetic (OU/megashock) or Kalman-extracted from the price series being
explained — a circularity managed but never eliminated.

## 4. Pitfalls, validation and measurement

- **Calibrate and validate against the same *stylized facts*, not against the price path.** A model can track the
  aggregate price while missing heavy tails; the accepted gate is the per-moment, per-day coverage matrix of §2.2,
  not an averaged loss — a 10% coverage cell on squared-return ACF(60) is a real failure (arXiv:2208.13654).
- **Do not let the trigger parameter absorb the phenomenon.** The amplitude plateau past \(r=5\%\) and the
  inverted-U in MM inventory limits mean "more aggressive sell program ⇒ worse crash" is *false* over part of the
  range; a monotonicity sanity check would reject a correct model (arXiv:2208.13654).
- **Overfitting the rare event.** The 2010 crash happened once. The simulator calibrates only the morning session,
  then hand-tunes market-maker limits and fundamental frequency for the afternoon event; any claim that the model
  *predicts* the crash must account for those two tuned knobs (arXiv:2208.13654).
- **The training protocol is a hidden variable in RL-ABM results.** Frozen (Group B) agents produce 14× the real
  market's excess kurtosis and permanent price drops; untrained agents overshoot; only continual learning lands
  near the real value. Comparing policies trained under different schedules is not comparing policies
  (arXiv:2403.19781).
- **Zero-sum games break standard tests.** Outcomes are non-independent and the difference distributions are
  bimodal, so use a bootstrap of differences, not a two-sample \(t\)-test (arXiv:2110.00879).
- **Feedback loops and numerical overflow are failure modes, not edge cases.** A chartist pricing off its own last
  order enters a self-referential loop whose estimate exceeds double-precision range within a single game; any
  adaptive agent that reads the price it helped set needs an exogenous anchor or risk penalty to stay bounded
  (arXiv:2110.00879).
- **Herding/CSAD/LSV detect correlated trading, not its motive.** A low CSAD or high LSV is equally consistent with
  rational common information and with imitation, so the rolling transformed-tail indicator (Johnson \(S_U\) map,
  then \(\text{HerdTail}_t(u)=\Pr(\hat z<-u)+\Pr(\hat z>u)-2[1-\Phi(u)]\) over 30-day windows) is a *co-movement*
  check, not causal identification (arXiv:2607.27063).
- **Report the null.** A zero-intelligence market already produces six univariate stylized facts without any
  history (arXiv:2312.14903), so "our model reproduces stylized facts" is only informative relative to a ZI
  baseline and, ideally, to real data on the same moments — as in arXiv:2403.19781's kurtosis table.
- **Check exchange-mechanism granularity.** A 100 ms step (arXiv:2208.13654) is high-frequency for an ABM but still
  100× coarser than exchange event time; statements about micro-scale phenomena (quote flickering, sub-ms
  arbitrage) are out of scope. Latency is modelled only trader↔exchange (arXiv:2110.00879).
- **Cross-corpus links.** For square-root impact and limit-fill adverse drift use
  [`../qfin-st/microstructure-execution.md`](../qfin-st/microstructure-execution.md); for order-book dynamics
  proper [`../qfin-tr/limit-order-book-dynamics.md`](../qfin-tr/limit-order-book-dynamics.md); for RL policies
  outside the simulator [`../qfin-tr/rl-trading-agents.md`](../qfin-tr/rl-trading-agents.md); for volatility
  clustering as an empirical object [`../qfin-st/volatility-modeling.md`](../qfin-st/volatility-modeling.md).

## 5. Recommended first implementation in FinRobot

Ranked by value-per-effort against a data layer that supplies bars but not a book. Items 1, 2, 4 and 7 are buildable
now; items 3, 5 and 6 are self-contained simulator code.

1. **Discrete-event CDA engine with latency (§2.1).** Min-heap event loop, price-time matching, "delay-the-send"
   latency; per-asset books, agents in threads. *Data:* none. *Pass:* homogeneous fundamentalists land at the
   \$350 cash / \$50 bonus null; \(O(1)\) lookup, \(O(\log n)\) insert. *Effort:* M.
2. **Stylized-facts harness (§2.2).** Hill, realised volatility, return/squared-return ACFs (3-lag smoothed),
   inverse-variance weights from block bootstrap, coverage report. *Data:* `eodhd` `eod`/`tiingo` `prices`,
   `twelvedata` `time_series`. *Pass:* 9-moment × N-day matrix on a real and a synthetic series. *Effort:* S.
3. **Demand block + fundamental generator (§2.3–2.4).** FT/MT/NT/MM rules plus mean-reverting/OU/Kalman
   fundamental; calibrate \(\gamma_1,\gamma_2,\gamma_{NT},\zeta_L,\zeta_S\). *Data:* bars for the Kalman anchor.
   *Pass:* Hill/volatility/ACF coverage comparable to arXiv:2208.13654; knowingly fails volume facts. *Effort:* M–L.
4. **Herding / belief-clearing module (§2.5).** Gaussian priors, logistic propensities, convex herding mix,
   nearest-root clearing, finite-speed diffusion on lattice/ER/WS graphs. *Data:* none. *Pass:* degree-8 converges
   faster than degree-4; kurtosis rises with \(\gamma\); joint dynamics overshoot then reverse. *Effort:* M.
5. **RL-inside-ABM training loop (§2.6).** PPO market-maker and liquidity-taker agents on engine observations,
   A/B/C protocol. *Data:* none. *Pass:* continual group has positive spread PnL, near-zero inventory, kurtosis
   nearer the real series than ZI. *Effort:* L.
6. **Scenario generator (§2.7).** POV sell algorithm, spiking trader, prominence-based amplitude, Monte Carlo
   quantiles. *Data:* intraday volume profile (`twelvedata`/`moomoo://get_cur_kline`). *Pass:* non-monotone POV and
   inventory-limit curves plus the ~80 bp mini crash. *Effort:* M (after 3).
7. **ZI control + validation report.** the 2312.14903-style minimal agent set as a permanent null arm; one report
   printing coverage, kurtosis by group, and the homogeneous-game null. *Data:* bars as in item 2. *Pass:* every
   ABM result is reported against the ZI arm and real data on the same moments. *Effort:* S.

## Appendix — papers read

| arXiv id | Title | Year |
|---|---|---|
| 2312.14903v2 | Scalable Agent-Based Modeling for Complex Financial Market Simulations | 2023 |
| 2110.00879v1 | Traders in a Strange Land: Agent-based discrete-event market simulation of the Figgie card game | 2021 |
| 1909.11650v1 | Explaining Agent-Based Financial Market Simulation | 2019 |
| 2403.19781v1 | Reinforcement Learning in Agent-Based Market Simulation: Unveiling Realistic Stylized Facts and Behavior | 2024 |
| 2208.13654v1 | High-frequency financial market simulation and flash crash scenarios analysis: an agent-based modelling approach | 2022 |
| 2607.27063v1 | Herding, Momentum, and Reversal in China's A-Share Market: An Agent-Based Network Model with Information Diffusion | 2026 |
