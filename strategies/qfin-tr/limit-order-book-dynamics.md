# Limit-Order-Book Dynamics — learnings from the q-fin.TR corpus

`537` of 2370 corpus papers matched this category (537 with PDFs); this doc is based on a close reading of `6`.

Headline: **this category is about mechanisms that live below the snapshot.** Two of the six papers
reconstruct the *bare* impact of every event type at the best quotes and show that the market-order-only
view is "dressed" by limit orders and cancellations (arXiv:0904.0900); one derives the stationary depth
curve of the book as a closed-form function of the order flows (arXiv:1311.5661); one shows that the
even/odd parity of the spread is a measurable discreteness statistic that also reveals strategic placement
(arXiv:0906.1387); one solves optimal limit-vs-market splitting with queue-aware fill probabilities
(arXiv:1210.1625); one proves that everything queue-dependent is only *partially* identified from
aggregate L2 snapshots (arXiv:2609.13597); and one shows how trend-following swarms fatten the tail of
continuous price moves in a pure order-book simulation (arXiv:1411.2215). FinRobot's endpoint inventory
serves top-of-book snapshots and bars only: the parity statistic is estimable today, the queue layer is
not. The doc therefore marks the event-level inputs as **gap** and spends §2 on what the queue formulas
are worth once a book feed exists — plus the one estimator that runs on snapshots alone.

## 1. What the corpus actually offers

- **The price is a pure jump process when all best-quote events are counted, and for large-tick stocks
  the jump sizes are constant.** Using 14 NASDAQ stocks, 53 trading days (03/03/2008–19/05/2008),
  classification of every event that changes the best bid/ask or the volume quoted there into six types
  (MO⁰, MO′, LO⁰, LO′, CA⁰, CA′), the averaged realized gaps are $2\Delta^R_{\rm MO'}=1.00$–$1.02$
  ticks for the seven large-tick names and $1.11$–$1.85$ for the small-tick names; the constant-jump
  model $p_{t+\ell}=p_t+\sum_{t'\le t'<t+\ell}\Delta^R_{\pi_{t'}}\epsilon_{t'}$ reproduces both the
  response functions $R_\pi(\ell)$ and the diffusion curve $D(\ell)/\ell$ "nearly perfect[ly]" for large
  ticks but not for small ticks (arXiv:0904.0900).
- **Price-changing events are rare in large-tick names and common in small-tick names.** Probability of
  a price-changing event totals $\approx 3\%$ for large-tick stocks versus up to $40\%$ for small-tick
  stocks; per-type probabilities for the large-tick group are MO⁰ ≈ 0.04–0.054, MO′ ≈ 0.0065–0.011,
  CA⁰ ≈ 0.32–0.41, LO⁰ ≈ 0.53–0.54, CA′ ≈ 0.0008–0.0021, LO′ ≈ 0.0081–0.013, with mean spread
  1.08–1.12 ticks and 0.068–0.17 s between events; the small-tick group has mean spreads 1.64–4.12 ticks,
  MO′ up to 0.080, LO′ up to 0.20, and 0.068–0.63 s between events (arXiv:0904.0900).
- **Signed order flow mixing restores efficiency; side flow stays long-memory.** The sign series
  $\epsilon_t$ (which flips sign for limit orders, so a buy limit order carries $\epsilon=+1$ like a buy
  market order) decorrelates after 10–100 trades ($\sim$10 s), whereas the *side* series $s_t$
  decorrelates as $\ell^{-\gamma}$ with $\gamma\approx0.7$; many signed event-event correlations decay
  as a power law with exponent $\approx0.5$. Market orders "attract" compensating limit orders — the
  "stimulated refill" — and price-changing events are clustered in time (arXiv:0904.0900).
- **A market-order-only impact model explains only about two thirds of long-horizon volatility.**
  Calibrating the temporary-impact propagator $G(\ell)$ on the response function $R(\ell)$ and computing
  $D(\ell)$ with $n_t=0$ reproduces $\approx 2/3$ of the long-term variance; the residual needs the other
  event types and/or fluctuating impact. History dependence is severe for small ticks: the bare
  propagators $G_\pi(\ell)$ and the correcting kernel $\kappa=K-\tilde K$ are non-trivial functions of
  lag, and a constant $D_0=0.04$ ticks$^2$ must be added to fit short lags (arXiv:0904.0900).
- **The average depth of the book is a closed-form function of three flow rates.** In a one-side
  $M/M/1+M$ book (limit arrivals $\lambda$, market orders $\mu$, exponential cancellation rate $\theta$,
  $\delta=\mu/\theta$), the stationary average shape satisfies the conservation law
  $b(p)=h(p)\,C(p)$, where $C(p)$ is the probability that a limit order submitted at $p$ is cancelled
  before execution; the same formula reproduces the numerically simulated shapes of Smith et al. (2003)
  and the empirical/analytical shape of Bouchaud et al. (2002) with power-law deposition
  $h(u)\propto(1+u)^{-\gamma}$, $\gamma\approx1.5$–$1.7$ (arXiv:1311.5661).
- **Reducing the number of limit orders at fixed total volume shallows the book.** Allowing geometric
  order sizes (mean $1/q$), the model predicts a *negative* relation between book depth and the *count*
  of arriving limit orders $N^\lambda$, and a *positive* relation with their average size $V^\lambda$.
  Tested on 14 Paris (CAC 40) stocks, 04/01/2010–22/02/2010, 391 half-hour intervals per name
  (5,474 panel points, stock fixed effects): depth up to 5 ticks, $\hat\beta(N^\lambda)=-0.245$
  ($t=-12.2$), $\hat\beta(V^\lambda)=+8.71$ ($t=11.6$), $R^2=0.079$; depth up to 10 ticks,
  $\hat\beta(N^\lambda)=-0.458$ ($t=-10.4$), $\hat\beta(V^\lambda)=+39.5$ ($t=24.1$), $R^2=0.142$; the
  market-order volume $N^\mu V^\mu$ carries a *negative* coefficient ($-0.00085$, $t=-5.27$) once both
  are included (arXiv:1311.5661).
- **Even and odd spreads are not equivalent, and traders exploit the parity.** For 20 NYSE stocks,
  $\approx$80 trading days (Oct 2004–Feb 2005, best bid/ask only), the fraction of odd-valued spreads
  exceeds $0.5$ and the excess is stronger for small average spreads, decaying toward $1/2$ as
  $\langle s\rangle$ grows. Uniform deposition inside the spread already predicts an excess of odd
  spreads ($P(o\mid e,s)=1/2+1/(2s)$), but real data oscillate *both* ways with probability $\approx0.8$;
  this requires non-uniform deposition, with $\alpha\approx0.7$ of inside-spread limit orders placed at
  the quote adjacent to the best (arXiv:0906.1387).
- **Discreteness is a stability parameter, not a detail.** In that microscopic model the spread process
  diverges for $\alpha>0.85$; in the realistic region $s\ge3,\ \alpha>0.5$ the relative spread reduction
  per inside-spread limit order is always below the uniform value
  $\langle\Delta s\rangle/s = 1/2$, and the non-uniform rule is what produces intermittency — long
  compact/liquid spells interrupted by volatility bursts, with exponentially decaying volatility
  autocorrelation (arXiv:0906.1387).
- **The limit-vs-market split is a convex program whose solution is a quantile of the queue-outflow
  distribution.** With queue size $Q$, horizon $T$, half-spread $h$, market fee $f$, effective limit
  rebate $r$ (net of adverse selection), impact $\lambda$ and shortfall/overfill penalties
  $\varepsilon_u,\varepsilon_o$, the one-exchange optimum splits at the quantile
  $\frac{2h+f+r}{\varepsilon_u+h+r+\lambda}$ of the outflow CDF $F$; with the paper's baseline
  ($h=0.02$, $f=0.003$, $r=0.002$, $\lambda=0.0005$, $Q=2000$, Poisson outflow 2,200 shares/min,
  $T=1$ min) the closed-form optimum is $(M^\star,L^\star)=(730,270)$ shares, with a Robbins–Monro
  scheme converging within 2% of the objective in 50 iterations (arXiv:1210.1625).
- **Spreading across venues is a rebate arbitrage that over-posts limit orders.** With $K=2$ venues and
  $S=500$ shares the optimum allocates 15% market / 44% / 44% (103% of the target *posted*), and total
  cost falls from $2.35$ cents/share (all-market) to $-0.85$ cents/share; with $K=5$ and $S=500$ the
  optimum is 1%/34%/34%/34% and $-2.05$ cents/share. The paper's own caveat: fills depend on the *tail*
  of $F$, so exponential and Pareto outflows with the same mean give different $L^\star$; TAQ carries no
  cancellation information, so $Q$ and $F$ must come from a deeper feed (arXiv:1210.1625).
- **Passive execution is only partially identified from aggregate books; aggressive is point-identified.**
  On Tokyo Stock Exchange ten-level L2 + L1 data for RICs `1301.T` and `7911.T` (Jan 6–Jul 25 2025;
  843,135 / 9,062,080 continuous L2 rows; 24,607 / 319,046 regular trades; 1,080 held-out 300 s episodes
  per name over 18 July dates), the aggressive implementation-shortfall benchmark is invariant at
  $10.010$ bps and $2.400$ bps across front/quantity-random/back cancellation-allocation rules, while
  the passive-at-touch cost ranges $8.008\to9.018$ bps (`1301.T`, a $-1.010$ bps front-minus-back effect,
  95% equal-date interval $[-1.253,-0.788]$) and $0.765\to1.149$ bps (`7911.T`,
  $-0.384$ bps $[-0.493,-0.284]$); passive preterminal completion rises 8.01 and 7.39 percentage points
  (arXiv:2609.13597).
- **The FIFO ambiguity changes decisions, not only numbers.** The lowest-cost policy flips in 0.83–4.49%
  (`1301.T`) and 3.63–14.26% (`7911.T`) of directed cross-rule comparisons; conditional on a flip the
  added cost is 14.277–17.354 bps versus 2.366–3.723 bps respectively — the larger ambiguity sits in the
  *less* sensitive instrument, which is exactly why the envelope must be reported rather than a single
  number (arXiv:2609.13597).
- **Trend-following swarms fatten the tail of continuous moves; contrarian ones do not.** In a
  unit-order stochastic book over a $\pm15$ price band with an order-removal rule, 1,000,000 simulations
  per model (30 repetitions) give a draw-size tail $P_>(x)\propto x^{-4.19\pm0.31}$ for the following
  model versus slopes $-0.04$ (plain) and $-0.06$ (shuffled, $R^2=0.99$); the sum-of-squared difference
  between the following and plain distributions exceeds the contrarian-vs-plain difference by $>13\times$;
  KS statistics are 4.79 (plain↔following), 3.33 (following↔contrary), 1.25 (contrary↔plain). Swarm
  steps are $0.92\pm0.16\%$ (following) and $0.19\pm0.03\%$ (contrary) of simulations, and $\sigma(\tau)\propto\tau^{0.5}$
  with near-zero autocorrelation beyond lag 1 — fat tails with a diffusive price
  (arXiv:1411.2215).
- **On-topic check:** five of six are squarely q-fin.TR. arXiv:2609.13597 is cross-listed with
  primary category q-fin.CP (metadata `categories: ['q-fin.CP','q-fin.TR']`); it is retained because it
  is the only paper in the set that draws the *identification boundary* for the book quantities the
  other five estimate, and it reads L2 books directly.

Cross-corpus: where the same machinery is already derived for the q-fin.ST corpus see
[`../qfin-st/microstructure-execution.md`](../qfin-st/microstructure-execution.md) (square-root impact,
negative drift of a limit fill, microprice) and
[`../qfin-st/market-simulation-agent-models.md`](../qfin-st/market-simulation-agent-models.md) (agent-based
order-book simulators). This document covers the *internal* book dynamics those two treat only as inputs.

## 2. Implementable formulas & algorithms

### 2.1 Event-time bare-impact decomposition and the constant-gap model
**Purpose.** Attribute every best-quote price change to exactly one of six event types, and deconvolve
the observed response functions into a per-event "bare" impact that is not contaminated by the
correlation between events (the dressing effect).

**Formula.** With six types $\pi\in\{{\rm MO}^0,{\rm MO}',{\rm LO}^0,{\rm LO}',{\rm CA}^0,{\rm CA}'\}$,
signed event $\xi_t = I(\pi_t=\pi)\,\epsilon_t$, side $s_t=\epsilon_t$ for MO/CA and $s_t=-\epsilon_t$ for
LO, define
$$R_{\pi}(\ell)=\big\langle (p_{t+\ell}-p_t)\,\epsilon_t \,\big|\, \pi_t=\pi \big\rangle,\qquad
C_{\pi_1,\pi_2}(\ell)=\frac{\big\langle I(\pi_t=\pi_1)\epsilon_t\, I(\pi_{t+\ell}=\pi_2)\epsilon_{t+\ell}\big\rangle}{P(\pi_1)P(\pi_2)} .$$
The additive model $p_t=\sum_{t'<t}G_{\pi_{t'}}(t-t')\epsilon_{t'}+p_{-\infty}$ gives the linear system
$$R_{\pi_1}(\ell)=\sum_{\pi_2}\sum_{n\ge0} A^{\pi_1,\pi_2}_{\ell,n}\,G_{\pi_2}(n),\qquad
A^{\pi_1,\pi_2}_{\ell,n}=P(\pi_2)\begin{cases}
C_{\pi_1,\pi_2}(\ell-n)-C_{\pi_2,\pi_1}(n), & 0<n\le\ell\le L\\
C_{\pi_2,\pi_1}(n-\ell)-C_{\pi_2,\pi_1}(n), & 0<\ell<n\le L
\end{cases}$$
which is inverted for $G_\pi$ on a lag grid $L$. The parsimonious alternative replaces each event's jump
by its mean realized gap, $p_{t+\ell}=p_t+\sum_{t\le t'<t+\ell}\Delta^R_{\pi_{t'}}\epsilon_{t'}$ with
$\Delta^R_\pi=\langle\Delta_{\pi,\epsilon_t,t}\mid\pi_t=\pi\rangle$, so that
$R_{\pi}(\ell)=\sum_{\pi_1}\Delta^R_{\pi_1}P(\pi_1)\sum_{0\le t'<\ell}C_{\pi,\pi_1}(t')$ and
$D(\ell)\approx\sum_{\pi_1,\pi_2}P(\pi_1)P(\pi_2)\Delta^R_{\pi_1}\Delta^R_{\pi_2}\sum_{0\le t',t''<\ell}C_{\pi_1,\pi_2}(t'-t'')$.
For small ticks add the history kernel
$$p_{t+\ell}=p_t+\sum_{t\le t'<t+\ell}\Big[\Delta^R_{\pi_{t'}}+\sum_{t''<t'}\kappa_{\pi_{t''},\pi_{t'}}(t'-t'')\,\epsilon_{t''}\Big]\epsilon_{t'},\qquad \kappa_{\pi,\pi_2}=K_{\pi,\pi_2}-\tilde K_{\pi,\pi_2},$$
where $K,\tilde K$ are fitted VAR kernels of the realized gaps and of the mean gaps on past order flow.

**Required inputs.** Event-level (market-by-order) stream that resolves, at every best-quote change:
event type; sign; whether the best price changed; the gap to the second level; timestamps. Plus the
best bid/ask path. Volume of each event is *not* used.

**Parameters & defaults.** Lag cutoff $L=1000$ events (resolves $G_\pi$ well up to $\ell\sim300$);
noise floor $D_0=0.04$ ticks$^2$ for short-lag diffusion of small-tick names; exclude the first 30 and
last 40 minutes of each session; both events of a correlation pair must be same-day.

**Observed effect sizes.** For large ticks the constant-gap model reproduces $R_\pi(\ell)$ and
$D(\ell)/\ell$ almost exactly and the lag dependence of the inverted $G_\pi$ is partly a numerical
artefact of the matrix inversion; for small ticks $G_\pi$ grows then decays and $\kappa$ is
non-negligible. Realized gaps $2\Delta^R$: large tick 1.00–1.14 ticks, small tick 1.11–1.85 ticks
(unconditional $2\langle\Delta_{\rm MO'}\rangle$ 1.00–1.45). A market-order-only model reproduces $\approx2/3$
of long-horizon variance. VAR forecasts of the next event's signed jump are monotone in the realized
value with unit slope (with mild cubic corrections).

**Failure modes.** The decomposition is *tautological* only if every price-changing event is observed;
unobserved events deeper in the book and on other venues "dress" $G_\pi$ (the paper explicitly keeps $K$
interpreted as a dressed object). The brute-force inversion is ill-conditioned at large $\ell$
(finite-size error grows). Volume dependence is ignored (events are binned by "changed the price or not"),
which is an approximation the authors flag. The whole construction needs L3/MBO — see §3.

### 2.2 Queue-reactive depth: closed-form book shape and the flow-conservation law
**Purpose.** Turn three measurable flow intensities into the *stationary* depth profile of the book, and
predict how depth responds to the size distribution of incoming limit orders.

**Formula.** One side as an $M/M/1+M$ queue: arrivals (limit orders up to price $k$) at rate
$\lambda_{1\to k}$, market orders at $\mu$, each resting order cancelled at rate $\theta$; state
$n$ has death rate $\mu+n\theta$. With $\nu=\lambda/\theta$ and $\delta=\mu/\theta$,
$$\pi_{1\to k}(n)=\pi_{1\to k}(0)\prod_{i=1}^{n}\frac{\lambda_{1\to k}}{\mu+i\theta},\qquad
E[L^{1\to k}]=\nu_{1\to k}-\frac{\Gamma_{\nu_{1\to k}}(1+\delta)}{\Gamma_{\nu_{1\to k}}(\delta)},\qquad
E[L^k]=E[L^{1\to k}]-E[L^{1\to k-1}],$$
with $\Gamma_y$ the lower incomplete gamma function. In continuous price with spatial arrival intensity
$\alpha h_\lambda(p)$ and $H(p)=\int_0^p h(u)\,du$, the average shape is
$$b(p)=h(p)\,C(p),\qquad C(p)=1-\delta\,\frac{g_\delta\big(H(p)\big)}{H(p)}\Big[1-\big(1-g_\delta(H(p))\big)\Big],\qquad
g_\delta(y)=\frac{e^{-y}y^{\delta}}{\delta\,\Gamma_y(\delta)},$$
i.e. **shape = arrival intensity × probability of cancellation before execution**; the limit is
$b(0)=h(0)/(1+\delta)$ and, for a finite total arrival rate $\alpha$, $b(p)\to h(p)C_\infty$ with
$C_\infty=1-\frac{\delta}{\alpha}g_\delta(\alpha)[1-(1-g_\delta(\alpha))]$. With geometric order sizes
(mean $1/q$) the cumulative shape becomes
$$B(p)=\frac{H(p)}{q}-\delta+\frac{\delta q}{1-q}\,\Big[\frac{H(p)}{\,_{2}F_{1}\!\big(\delta,\tfrac{q}{1-q},1+\delta,1-q\big)}\Big]^{-H(p)} .$$

**Required inputs.** Arrival counts at each price level $k=1..K$ (limit and market), cancellation or
queue-outflow counts, and the average sizes $V^\lambda_k,V^\mu_k$; equivalently, at the empirical level,
$N^\lambda_t,\ V^\lambda_t,\ N^\mu_t,\ V^\mu_t$ per interval and stock, plus the average cumulative depth
$B^i_t$ at $i$ ticks from the opposite best.

**Parameters & defaults.** $\delta=\mu/\theta$ (the inverse of Smith et al.'s granularity
$\epsilon_S=1/\delta$); $q=1/\overline{\text{size}}$; deposition $h(u)=\alpha\beta e^{-\beta u}$
(exponential, Chinese stocks) or $\alpha(\gamma-1)(1+u)^{-\gamma}$, $\gamma\approx1.5$–$1.7$ (power law,
Bouchaud et al.); unit-size market orders.

**Observed effect sizes.** Panel regression (stock fixed effects) of depth on flows: the coefficients
quoted in §1; separately, the *count/size* decomposition shows that at fixed total submitted volume,
larger limit orders deepen the first limits and a larger count shallows them. Average order sizes in the
sample: market 108.2–535.6 shares, limit 205.4–876.6 shares — limit size always exceeds market size;
limit counts 1,289–6,586 versus market 141–774 per 30-minute interval.

**Failure modes.** Poisson arrivals and exponential lifetimes are crude (cancellation times are
power-law); the model is a half-book with an absorbing infinite bid; unit-size market orders mean the
model cannot describe markets whose average market order exceeds the average limit order (never observed
in the Paris sample, but not guaranteed elsewhere); the regression needs *order counts*, i.e. event-level
data, not depth snapshots; the theory is stationary, so intraday volume seasonality must be handled by
conditioning on interval.

### 2.3 Discreteness asymmetry and non-uniform inside-spread deposition
**Purpose.** Use a snapshot-estimable statistic — the parity (odd/even) of the spread — to test whether
limit orders inside the spread are placed uniformly, and to calibrate the strategic-placement parameter.

**Formula.** For a spread of $s$ ticks, the uniformly depositing model gives
$$P(o\mid e,s)=\tfrac12+\tfrac{1}{2s},\quad P(e\mid o,s)=\tfrac12,\quad P(o\mid o,s)=\tfrac12,\quad
P(e\mid e,s)=\tfrac12\Big(1-\tfrac{1}{s-2}\Big),$$
which already favours odd spreads. With deposition $g(1\mid s)=\alpha$,
$g(i\mid s)=\frac{1-\alpha}{s-2}$ for $i=2,\dots,s-1$ (distance $i$ from the best), the transition
probabilities become functions of $\alpha$ and $s$; the mean relative spread change per inside-spread
limit order is
$$\frac{\langle\Delta s\rangle}{s}=\frac{\alpha}{s}+\frac{(1-\alpha)\,[s(s-1)-2]}{2\,s\,(s-2)},\qquad s\ge3,$$
and $\langle\Delta s\rangle/s\ge1/2$ only on the sliver $2\le s\le(\alpha+1)/\alpha$, i.e. never in the
realistic region $s\ge3,\alpha>0.5$. Stability of the spread process requires $\alpha\le0.85$.

**Required inputs.** A time series of best bid and best ask (top of book only) at every quote update, plus
tick size; from it classify events as spread-decreasing (limit order inside the spread) or
spread-increasing (aggressive order), and record $(s,s')$.

**Parameters & defaults.** NYSE sample: 20 stocks, $\approx$80 days, spread quoted in integer ticks;
$\alpha\approx0.7$; model order mix $\pi=1/3$ market orders, $2/3$ limit, buy/sell with probability $1/2$;
limit price uniform on $[b(t),b(t)+ks(t)]$ (sell) with $k>1$, so $1/k$ approximates the inside-spread
probability; constant tick $\Delta q=1$ and unit volume. Cancellations are assumed not to change the
spread (negligible in the sample).

**Observed effect sizes.** Fraction of odd spreads $>0.5$ for almost all stock-days; the conditional
$P(\text{odd}\mid s)$ oscillates around $1/2$ with an amplitude near $0.8$ for $s$ up to $\approx20$;
Monte Carlo with the uniform rule alone under-fits the empirical asymmetry, the non-uniform rule with
$\alpha=0.7$ fits it (with a small overestimate for $s>6$); non-uniform deposition raises average spread
($\langle s\rangle=15.8$ at $\pi=0.33$ in the uniform case versus 2.77 at $\alpha=0.7$) and produces
volatility bursts absent in the uniform model.

**Failure modes.** The data have *only* best bid/ask, so events are inferred from spread changes and
all cancellation-driven events are dropped; unconditioned odd-spread fractions are confounded by the
mixture over $s$ and must be split by $s$. The persistence of spread means a parity statistic can be
computed from sparse snapshots, but any snapshot cadence coarser than quote updates will miss the
transitions the statistic is built from (see §3).

### 2.4 Queue-aware optimal split between market and limit orders
**Purpose.** Given a short execution horizon and a queue position, decide how much to cross and how much
to post — and at which venue — under fees, rebates and adverse selection.

**Formula.** For a buy of $S$ shares across $K$ venues, decide $X=(M,L_1,\dots,L_K)\in\mathbb R_+^{K+1}$
with exogenous queue outflows $\xi=(\xi_1,\dots,\xi_K)\sim F$. FIFO fills behind $Q_k$ shares are
$f_k=\min\{(\xi_k-Q_k)_+,L_k\}=(\xi_k-Q_k)_+ -(\xi_k-Q_k-L_k)_+$, total executed
$A(X,\xi)=M+\sum_k\big[(\xi_k-Q_k)_+ -(\xi_k-Q_k-L_k)_+\big]$, and
$$v(X,\xi)=(h+f)M-\sum_k (h+r_k)\big[(\xi_k-Q_k)_+ -(\xi_k-Q_k-L_k)_+\big]
+\lambda\Big(M+\sum_k L_k+(S-A(X,\xi))_+\Big)+\varepsilon_u(S-A(X,\xi))_++\varepsilon_o(A(X,\xi)-S)_+ ,$$
minimised over $X$ as $V(X)=\mathbb E[v(X,\xi)]$ (convex; solved in general by a Robbins–Monro
stochastic-approximation scheme with the projection gradient). For $K=1$ the explicit optimum is
$$M^\star=S-F^{-1}\!\Big(\frac{2h+f+r}{\varepsilon_u+h+r+\lambda}\Big)+Q,\qquad
L^\star=F^{-1}\!\Big(\frac{2h+f+r}{\varepsilon_u+h+r+\lambda}\Big)-Q,$$
so the limit share is a *quantile* of the outflow distribution, not a function of its mean alone.

**Required inputs.** Best bid/ask and half-spread $h$; exchange fees $f$ and rebates $r_k^e$
(public schedules); a queue-outflow distribution $F$ per venue (or its empirical CDF); queue sizes
$Q_k$ ahead of the order; penalties $\varepsilon_u,\varepsilon_o$; impact coefficient $\lambda$.

**Parameters & defaults.** Baseline $h=0.02\ \$$/share, $f=0.003$, $r=0.002$, $\lambda=0.0005$,
$\varepsilon_u=\varepsilon_o=0.05$, $Q_k=2000$, $T=1$ min, single-factor correlated Poisson outflows with
mean 2,200 shares/min and $\rho=0.6$; $K=2$ baseline; assumption set $A1$–$A3$
($\min_k r_k+h>0$, $\varepsilon_o>h+\max_k r_k$ and $\varepsilon_o>\lambda(h+f)$, $\varepsilon_u>h+f$).
MSFT calibration: $Q$ 12,392 (NASDAQ) / 8,179 (BATS Z) shares, 1-minute market sell volume 848 / 922
shares, exceeding $Q$ in $\approx15\%$ of observations; $\varepsilon_u=\varepsilon_o\in\{1.0,0.9,0.5\}$
cents/share.

**Observed effect sizes.** $K=1$: $(M^\star,L^\star)=(730,270)$; algorithm within 2% of the objective
after 50 iterations (1,000–10,000 typical), $<200$ ms for $K=12$ with $N=1000$. $K=2$, $S=500$:
15%/44%/44%, total cost $-0.85$ versus $+2.35$ cents/share for a pure market order; at $K=5$,
1%/34%×4 and $-2.05$ cents/share, with the fee term at $-2.24$ cents/share. Limit posting is *bounded*
($L^\star$ does not grow with $S$), so large parent orders migrate to the market-order leg: at $S=5000$
even $K=5$ is 75% market / 11% ×4 limit.

**Failure modes.** The formulation is static/ergodic (no HJB); market orders are assumed to fill any
size at one venue, valid only when $S$ is of the order of prevailing depth ($\approx600$ shares for an
average US stock); all limit orders sit at one price with no modification or cancellation before $T$; a
single $\lambda$ is assumed for market and limit orders; allocations are real-valued; no latency or hidden
liquidity. Most importantly for FinRobot: $Q_k$ and the *cancellation* component of $\xi_k$ are not in
TAQ — the paper's own empirical step restricts to minutes with an unchanged best quote.

### 2.5 FIFO-sensitivity envelope: partial identification from aggregate L2 books
**Purpose.** Stop a passive-execution backtest from depending on an unobserved within-queue
cancellation-allocation rule: replay the same aggregate book path under several FIFO-consistent
order-level histories and report the *range* of outcomes, not a point estimate.

**Formula.** For each side–price cell, the aggregate update is
$\Delta Q_{s,p,k}=L_{s,p,k}-D_{s,p,k}-M_{s,p,k}$ with $M$ the trade-attributed removal; residual
$r_{s,p,k}=\Delta Q_{s,p,k}+M_{s,p,k}$ splits one-sidedly into
$L=[r]_+,\ D=[-r]_+$. An order-level realization $R$ replaces each aggregate quantity by an ordered
queue of order IDs, remaining sizes and priority times, with $\Gamma(R)_{s,p,k}=\sum_{(i,q,\tau)\in O_{s,p,k}(R)}q$.
The compatibility set is
$$R(A_b)=\{R:\Gamma(R)_{s,p,k}=Q_{s,p,k}\ \forall(s,p,k);\ R \text{ preserves } (t_k,T_k,Z_k);\ R \text{ obeys valid } (L,D,M)\text{ evolution}\},$$
and within the compiler class $G=\{\text{front},\text{random},\text{back}\}$ the identified outcome
sensitivity set is $Y_C(\pi;A_b)=\{Y(\pi;R):R\in R_C(A_b)\}$. The one conditional identification result is
$$F_{\text{back}}(t)\le F_r(t)\le F_{\text{front}}(t)$$
for a passive marker during an unchanged best-price spell, given per-cancellation removal of
ahead-of-marker quantity $c_{\text{back},k}\le c_{r,k}\le c_{\text{front},k}$. Costs are implementation
shortfall in basis points, $\mathrm{IS}(\pi;R)=10^4\big[\sum_i q_i(P_i-P_0)+q_T(P_T-P_0)\big]/(\sigma X P_0)$,
$\sigma=+1$ buys, and the robust choice is
$\pi_{\rm rob}\in\arg\min_{\pi\in\Pi}\sup_{R\in R_C(A_b)}\ell(\pi;R)$.

**Required inputs.** Ten-level L2 snapshots (price, aggregate displayed size) *plus* an L1/trade feed with
exchange timestamps for reconciliation; session/rank flags to drop unresolved and boundary transitions.

**Parameters & defaults.** 300 s replay blocks; per-cancellation placement rules front / quantity-weighted
random / back; boundary-fixed view as primary (deterministic synchronization at outer-rank entry/exit);
100-share deterministic partition as a robustness variant; 5,000 equal-date resampling replicates over 18
held-out dates; aggressive actions evaluated on a discarded copy of the contemporaneous book
(price-taking counterfactual).

**Observed effect sizes.** Coverage 97.27% (`1301.T`) / 96.80% (`7911.T`) of continuous-session time;
aggressive benchmark invariant at 10.010 / 2.400 bps across all rules; passive-at-touch front vs back
8.008 vs 9.018 bps (`1301.T`) and 0.765 vs 1.149 bps (`7911.T`); front-minus-back IS difference
$-1.010$ bps $[-1.253,-0.788]$ and $-0.384$ bps $[-0.493,-0.284]$; passive preterminal completion
18.15/15.29/10.14% and 97.20/95.52/89.81% (front/random/back). Reconciliation diagnostics: exact-time
match median 100%, p99 capture lag 3.39–4.89 ms, unresolved transitions 4.14–6.59%, boundary transitions
8.39–16.00%.

**Failure modes.** Front and back are *conventions*, explicitly not sharp bounds over $R(A_b)$, and
$Y_C$ is not the full set allowed by the data — the envelope is a lower bound on the ambiguity, never an
excuse to report one rule as truth. Reconciliation gaps (unresolved 4–7%, boundary 8–16%) must be excluded
or flagged; the direction of the effect is instrument-specific (the faster instrument changes policy more
often but at smaller conditional cost); the streaks/partition machinery is a modelling choice shared by
all rules, so agreement across rules is not identification of the true history.

### 2.6 Swarm-driven order placement as a genuine-order-book simulator
**Purpose.** Generate price series whose *continuous-move* (draw-size) distribution has the fat tail of
real markets, from an entirely rule-based book — the only technique here that needs no market data.

**Formula.** One unit per step: with the base price $B$ (last execution), if any resting order lies
outside $[B-15,B+15]$ it is removed; otherwise a buy or sell is posted with probability $1/2$ at a price
uniformly drawn in $\pm15$ of $B$. Swarm variants replace the uniform price by a three-range mixture.
With $p_t$ the last 10 execution-price moves, if more than 7 are up the following model places with
probabilities $(0.1,0.1,0.8)$ over $[B-15,B-6],[-5,+5],[+6,+15]$ (and $(0.8,0.1,0.1)$ after more than 7
down-moves); the contrary model swaps the two outer probabilities. Draw size is $|\text{draw-up}|$ or
$|\text{draw-down}|$, and the tail is tested against $P_>(x)\propto x^{-m}$ (Hill/ML) and a log-normal
$C(\alpha,\beta)$.

**Required inputs.** None (simulation). Optional calibration targets: empirical draw-size tail exponent
and KS distances of three models.

**Parameters & defaults.** Price band $\pm15$; trend window 10 moves; trigger $>7/10$; probability split
$0.8/0.1/0.1$; $10^6$ simulations per model, 30 repetitions.

**Observed effect sizes.** Draw-size tail exponent $m=4.19\pm0.31$ for the following model; plain and
shuffled slopes $-0.04$ and $-0.06$ with $R^2=0.99$; log-normal fits $\alpha=4.00,\beta=0.13$
(following) and $\alpha=3.89,\beta=1.77$ (plain); KS 4.79 / 3.33 / 1.25; $\sigma(\tau)\propto\tau^{0.5}$
with autocorrelation $\approx0$ beyond lag 1; largest simulated draw size 291 versus a 15-tick maximum
single-step move ($\approx20\times$).

**Failure modes.** Orders are unit size, there are no explicit market orders, and the $\pm15$ band plus
the removal rule are empirically tuned; the tail estimate is sensitive to where the tail starts (the
max-likelihood exponent and the log-normal fit disagree at the very edge); power law and log-normal are
statistically close over most of the range, so the exponent is a calibration target, not a law.

## 3. Data requirements → available endpoints

Provider rows are real entries in `strategies/endpoints.json`; "gap" means **no current provider can
supply it**. `moomoo` rows are served by the local OpenD SDK gateway and are not live-probed HTTP.

| Input | Endpoint | Category | Provider | Probe status |
|---|---|---|---|---|
| Daily OHLCV (volatility/volume scale, ADV) | `https://eodhd.com/api/eod/AAPL` | `core_stock_apis` | eodhd | ok |
| Daily OHLCV (secondary) | `https://api.tiingo.com/tiingo/daily/AAPL/prices` | `core_stock_apis` | tiingo | ok |
| Intraday minute bars (coarsest depth proxy) | `https://api.twelvedata.com/time_series` | `core_stock_apis` | twelvedata | ok |
| Top-of-book snapshot (best bid/ask, size) | `moomoo://get_market_snapshot` | `core_stock_apis` | moomoo | gateway (not live-probed) |
| Intraday K-line via local OpenD gateway | `moomoo://get_cur_kline` | `technical_indicators` | moomoo | gateway (not live-probed) |
| Aggregate capital flow (net buy/sell, not book) | `moomoo://get_capital_flow` | `capital_flow` | moomoo | gateway (not live-probed) |
| Tradable symbol universe / tick sizes | `https://eodhd.com/api/exchange-symbol-list/US` | `exchange_symbols` | eodhd | ok |
| News (jump/`n_t` noise events) | `https://eodhd.com/api/news` | `news_data` | eodhd | ok |
| **L2/L3 book depth (≥3 ranks)** | — | — | — | **gap** |
| **Market-by-order event stream (adds/cancels with order ids)** | — | — | — | **gap** |
| **Signed trade tape with aggressor flag** | — | — | — | **gap** |
| **Queue position / per-order priority times** | — | — | — | **gap** |
| **Consolidated multi-venue NBBO + venue quotes** | — | — | — | **gap** |
| **Exchange fee/rebate schedules (machine-readable)** | — | — | — | **gap** |

**What the gap costs, quantified.** The FIFO paper's identification statement is built on
843,135–9,062,080 continuous **ten-level L2 rows** per name over seven months (Jan 6–Jul 25 2025) plus
24,607–319,046 reconciled trades, at a p99 capture lag of 3.39–4.89 ms; the reported front-minus-back
passive effect is 0.38–1.01 bps, so an 18-date × 6,480-unit held-out design is the *minimum* to bound it
— a single top-of-book snapshot per day cannot see a within-queue cancellation at all. The event-decomposition
paper needed 14 names × 53 days of *every* best-quote change, at 0.068–0.63 s between events, i.e.
$O(10^5$–$10^6)$ events per name per month, with the second-level gap (a field a top-of-book snapshot
does not carry). The queue-shape regression needed per-interval limit/market **counts** as well as sizes
or it degenerates to the flow-volume term only. The optimal-placement solver needs $Q_k$ (queue depth
ahead) and the cancellation component of $\xi_k$, absent from TAQ; the queueing model needs a
cancellation rate $\theta$ that only an event feed supplies. The parity statistic of §2.3 is the sole
exception: it needs nothing below the top of book — but it needs the top of book at **quote-update
cadence**, because it is the *transition* between two consecutive quotes that carries the signal. Concretely:
`moomoo://get_market_snapshot` can support §2.3 as a study-of-the-past only if the gateway can stream
(or replay) updates; at polling cadence the parity test loses its transitions. Everything in §2.1, §2.2,
§2.4 and §2.5 is blocked on a market-by-order or ≥3-rank L2 archive for the target names.

## 4. Pitfalls, validation and measurement

- **"Constant impact" is a tick-size regime, not a universal law.** The constant-gap model is "nearly
  perfect" for large ticks and visibly wrong for small ticks, where the correcting kernel $\kappa=K-\tilde K$
  and a noise floor $D_0=0.04$ ticks$^2$ are required; the authors also warn that part of the apparent lag
  dependence of the brute-force inverted $G_\pi$ is numerical. Always report the large-tick/small-tick
  split and do not transfer a fitted constant across it (arXiv:0904.0900).
- **Dressing, not leakage, is the dominant bias here.** If only market orders are modelled, a
  market-order pipeline silently absorbs the effect of limit orders and cancellations and reproduces only
  $\approx2/3$ of long-horizon variance; conversely, the inverted bare propagators are "dressed" by
  unobserved deeper-book and other-venue events, and $K$ is explicitly interpreted as such. Any impact
  estimate from one venue is a dressed estimate (arXiv:0904.0900).
- **Look-ahead is structural in passive backtests, not accidental.** With L2 data the aggressive
  benchmark is invariant under the FIFO rule (a genuine out-of-sample-invariant control), while the
  passive result moves by up to 1.01 bps and can change the *policy choice* in 0.8–14.3% of comparisons.
  Never report a passive cost without the front/random/back envelope; drop unresolved (4–7%) and boundary
  (8–16%) transitions or show they do not drive the result (arXiv:2609.13597).
- **Parity statistics must be conditioned.** The raw fraction of odd spreads mixes stocks and spread
  levels; reporting it without conditioning on $s$ reproduces the very confounding the paper removes.
  The paper's own acceptance test is the conditional $P(\text{odd}\mid s)$ against the uniform benchmark
  $1/2+1/(2s)$ (arXiv:0906.1387).
- **Discreteness changes stability.** A micro-model of inside-spread placement diverges for
  $\alpha>0.85$; the realistic region is $s\ge3,\alpha>0.5$ and stability then requires lowering the
  market-order rate, which erases the volatility bursts the model was built to reproduce. A parameter
  choice that "fits" $\alpha$ but ignores $\pi$ is not calibrated (arXiv:0906.1387).
- **Outflow tails, not means, drive placement.** Exponential and Pareto outflows with identical means
  yield different optimal $L^\star$ because the fill probability comes from $F^{-1}$; calibrating a
  placement rule on average queue volume alone is a misspecification (arXiv:1210.1625).
- **Metric choice can flip the conclusion about tails.** The swarm model's draw-size tail fits a
  log-normal better than a power law at the edge, while the maximum-likelihood power index is
  $4.19\pm0.31$; the authors explicitly note the two families are easily confused because the log-normal's
  local exponent drifts slowly. Report both and the slope of the linearised CDF, and never read a
  fat-tail claim from a single fit (arXiv:1411.2215).
- **Multiple testing and weak-power tests.** The 1411.2215 KS test is run at the 10% level and the
  following-vs-plain distributions are only marginally separated once the whole range is included, because
  small draw sizes dominate; the sum-of-squares comparison ($>13\times$ versus contrarian) is the more
  informative statistic. Treat the KS statistic as a screening test, not proof
  (arXiv:1411.2215, arXiv:0906.1387).
- **Non-stationarity inside the day.** The event-decomposition paper drops the first 30 and last 40
  minutes to remove intraday periodicity and overnight effects, and restricts correlation pairs to a
  single day; the FIFO paper uses 300 s blocks inside the continuous session and excludes pre-open, lunch
  and auctions. A depth or impact fit on full-day data without this filtering will absorb a time-of-day
  term (arXiv:0904.0900, arXiv:2609.13597).
- **Calibration/test splits are stated in all three empirical papers.** TAQ Jan–Mar 2012 calibration with
  an April 2012 test (arXiv:1210.1625); Paris Jan 4–Feb 22 2010 with 391 half-hour intervals
  (arXiv:1311.5661); TSE Jan–May for partition inputs, June for selecting block/probe/policy settings,
  July held out (arXiv:2609.13597). Reproduce these splits before comparing to the reported numbers.
- **Model-internal validity conditions are checkable.** The $M/M/1+M$ shape requires $\theta>0$ and has
  $b(0)=h(0)/(1+\delta)$; the queue regression requires the fixed-effect panel form; the placement program
  requires assumptions $A1$–$A3$. State them and test them rather than assuming them
  (arXiv:1311.5661, arXiv:1210.1625).

## 5. Recommended first implementation in FinRobot

Ranked by value per unit of effort against what the data layer can actually fetch today. Items 1–2 run
now; items 3–7 are offline/analytical or blocked on a book feed.

1. **Spread-parity asymmetry diagnostic (snapshot-only, buildable today).** *What:* compute the
   conditional distribution $P(\text{odd}\mid s)$ and the fraction of odd spreads as a function of
   $\langle s\rangle$ from a best-bid/ask history, and compare against the uniform-deposition benchmark
   $P(o\mid e,s)=1/2+1/(2s)$. *Data:* `moomoo://get_market_snapshot` (gateway) for the quote path;
   `https://eodhd.com/api/exchange-symbol-list/US` for tick sizes and universe. *Passing:* excess over
   $0.5$ that decays toward $1/2$ as $\langle s\rangle$ grows, and oscillating
   $P(\text{odd}\mid s)$ with amplitude $\gtrsim0.7$ (arXiv:0906.1387). *Effort:* S.
2. **Queue-reactive depth engine and flow-shape regressor (analytical, no market data).** *What:*
   implement $E[L^{1\to k}]=\nu-\Gamma_\nu(1+\delta)/\Gamma_\nu(\delta)$ and the continuous
   $b(p)=h(p)C(p)$ with $g_\delta$, plus the geometric-size version with $_2F_1$; expose
   $(\lambda,\mu,\theta,h)$ as inputs. *Data:* none to run; the Paris panel (5,474 points) as an offline
   regression fixture once per-interval order counts are available. *Passing:* reproduces Smith et al.'s
   numerically simulated shapes and the qualitative hump; the count/size sign pattern
   ($\beta_{N^\lambda}<0<\beta_{V^\lambda}$) with 5-tick depth $R^2\approx0.08$ and 10-tick
   $R^2\approx0.14$ (arXiv:1311.5661). *Effort:* S–M.
3. **Optimal split/venue-allocation solver with a user-supplied feed table (partial today).** *What:*
   implement the convex objective, the one-exchange closed form and the Robbins–Monro scheme over
   $X=(M,L_1,\dots,L_K)$; make $F$, $Q_k$ and the fee/rebate table explicit inputs. *Data:* best bid/ask
   from `moomoo://get_market_snapshot` for $h$; fees/rebates entered manually (**no endpoint**); $F$ and
   $Q_k$ as parameters until a book feed exists. *Passing:* reproduces $(M^\star,L^\star)=(730,270)$ at
   the paper's baseline and the qualitative result that limit posting is bounded in $S$ while total cost
   falls with $K$ (arXiv:1210.1625). *Effort:* S–M.
4. **FIFO-sensitivity envelope compiler and passive backtester.** *What:* implement the aggregate-path
   compiler with front/quantity-random/back cancellation allocation, the popularity projection
   $\Gamma(R)$, the IS metric and the report-the-range discipline. *Data:* ten-level L2 + L1 —
   **blocked**; build against a synthetic or vendor sample. *Passing:* aggressive benchmark invariant
   across rules (0 bp change), passive envelope width of order 0.4–1.0 bps on the two test names, and a
   policy-flip rate reported explicitly (arXiv:2609.13597). *Effort:* M.
5. **Bare-impact event decomposition and constant-gap baseline.** *What:* the six-event classification,
   $C_{\pi_1,\pi_2}$, the linear inversion for $G_\pi$, and the constant-gap predictor with the
   large-tick acceptance gate. *Data:* market-by-order event stream — **blocked**. *Passing:* constant-gap
   $R_\pi(\ell)$ agreement and $D(\ell)/\ell$ flat within a few percent for one large-tick name, with the
   gap widening on a small-tick name (the paper's own contrast) (arXiv:0904.0900). *Effort:* M.
6. **Swarm ABM draw-size generator (self-contained).** *What:* port the $\pm15$ band model, the removal
   rule and the three-range mixture; use it as a fat-tail scenario generator. *Data:* none. *Passing:*
   following-model draw-size tail exponent $\approx4.2$ and a following-vs-plain sum-of-squares gap
   $>10\times$ the contrarian gap (arXiv:1411.2215). *Effort:* M.
7. **Acquire a market-by-order (or ≥3-rank L2) archive for a small name set.** *What:* add an ingestion
   path and register a new data category (e.g. `order_book_depth` / `tick_trades`) rather than
   overloading `core_stock_apis`. *Data:* the feed itself — both `L2/L3 depth` and
   `market-by-order events` are **gap**. *Value:* unblocks items 4–5 and the calibration of items 2–3;
   without it this entire category is snapshot-only or synthetic. *Risk:* storage
   ($O(10^8)$–$10^9$ rows/name/quarter at ten ranks), licensing, and the reconciliation work the FIFO
   paper performs (fixed capture-lag limits per feed). *Effort:* L.

## Appendix — papers read

| arXiv id | Title | Year |
|---|---|---|
| 0904.0900v3 | The price impact of order book events: market orders, limit orders and cancellations | 2009 |
| 0906.1387v3 | Asymmetric statistics of order books: The role of discreteness and evidence for strategic order placement | 2009 |
| 1210.1625v4 | Optimal order placement in limit order markets | 2012 |
| 1311.5661v1 | The order book as a queueing system: average depth and influence of the size of limit orders | 2013 |
| 1411.2215v1 | Simple Stochastic Order-Book Model of Swarm Behavior in Continuous Double Auction | 2014 |
| 2609.13597v2 | Same Book, Different Fills: Partial Identification of FIFO Execution from Aggregate Order Books | 2026 |
