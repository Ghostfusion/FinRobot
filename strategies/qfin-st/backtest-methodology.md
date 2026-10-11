# Backtest Methodology — learnings from the q-fin.ST corpus
`185` of 4372 corpus papers matched this category (183 with PDFs); this doc is based on a close reading of `6`.

Key: all claims below are from the six papers listed in the Appendix. Cross-references (Bailey &
López de Prado, Lo, Hansen, White, Romano–Wolf, Harvey–Liu) are cited *as used inside those papers*,
not read directly.

---

## 1. What the corpus actually offers

- **Composite anti-overfitting objective (GT-Score).** A single optimizable scalar (a *minimized*
  loss — see §2.1; taken as maximized it selects the worst strategy in the grid)
  $GT = \mu \cdot \ln(z) \cdot r^2 / \sigma_d$ that multiplies performance, a significance gate
  $z$, an equity-curve fit $r^2$, and downside deviation $\sigma_d$. Optimizing it raised the
  *generalization ratio* (validation ÷ training return) by **98%** in walk-forward (0.365 vs 0.185
  baseline average) at the cost of ~6% lower raw test return (43.6% vs 49.5% for a profit objective)
  (arXiv:2602.00080v1).
- **Post-selection robustness grade (MinervaScore).** A 5-gate validator
  `{DSR ≥ 0.95, PBO ≤ 0.50, SPA p ≤ 0.10, T ≥ MinTRL, regime ρ ≥ 0.60}` aggregated into a 0–100
  display that is *verdict-consistent* (≥80 iff all gates pass). Calibrated on 359,062 production
  backtests; AUROC 0.989 for separating genuine edge from luck in synthetic ground truth, but the
  corrected-DSR-alone baseline is a near-tie (0.988) and a pre-registered real-market test was null
  ($\rho_s = 0.013$, $p = 0.40$) (arXiv:2608.23808v2).
- **Explicit backtest-overfitting hypothesis test for RL/ML agents.** PBO estimated by Combinatorial
  Cross-Validation + CSCV-style rank logit, then framed as $H_0: p < \alpha$ (accept agent) vs
  $H_1: p \ge \alpha$ (reject). On 10 crypto assets through two market crashes, the least-overfit
  agent (PPO, $p=8.0\%$) beat a walk-forward agent ($p=17.5\%$), a K-fold agent ($p=7.9\%$), and the
  S&P BDM index in cumulative return and volatility (arXiv:2209.05559v6).
- **Documented leakage modes for RL/ML backtests.** Single validation block overfits one market
  situation; K-fold assumes an IID data-generating process that financial returns violate; authors
  "go back and forth between training and testing"; DRL hyperparameter sensitivity produces a
  "lucky" overoptimistic agent (arXiv:2209.05559v6). Execution-aware replay adds transaction-cost
  and settlement leakage (arXiv:2602.00133v1).
- **Benign overfitting / double descent in online time-series models.** Overparameterized
  (ridgeless, minimum-$\ell_2$-norm) RLS can generalize *better* past the interpolation threshold;
  stability is governed by the *effective condition number* of the design Gram matrix, and test
  error peaks exactly at interpolation where the condition number is largest
  (arXiv:2601.22200v1).
- **Deterministic event-driven replay harness.** Self-contained episodes + maker/taker fee model +
  fixed RNG seed ⇒ bit-reproducible backtests; naive activity loses to fees/settlement, so fee
  realism changes rankings (arXiv:2602.00133v1).
- **Baseline protocol facts worth standardizing.** Walk-forward train 4y / validate 2y / step 1y /
  30-day embargo over nine splits; Monte-Carlo 15 seeds × random search 25 evals per trial
  (arXiv:2602.00080v1). Time-series split 70/15/15 and 5 runs per model for uncertainty
  (arXiv:2510.15903v1). Combinatorial CV $N{=}5, k{=}2 \Rightarrow J{=}10$ splits with $H{=}50$
  hyperparameter trials (arXiv:2209.05559v6).
- **Off-topic check.** `2510.15903v1` (quantum vs classical ML on DeFi/AMM) is only tangentially
  about backtest methodology: its usable contributions are a clean time-series split, 5-run
  uncertainty reporting, and p-value reporting (all on a single 1-year, 3-asset sample, so its
  effect sizes are not trustworthy). `2602.00133v1` is relevant for the *replay harness* and
  execution realism, less for statistical validation. The core methodology evidence is
  arXiv:2602.00080v1, arXiv:2608.23808v2, arXiv:2209.05559v6, arXiv:2601.22200v1.

---

## 2. Implementable formulas & algorithms

### 2.1 GT-Score — overfitting-resistant optimization objective
**Purpose.** Replace `max profit` / `max Sharpe` as the optimizer target with a composite that
refuses to select parameterizations that fail significance, consistency, or downside tests.

Formula (arXiv:2602.00080v1, Eq. 1–2):

$$
GT = \frac{\mu \cdot \ln(z) \cdot r^2}{\sigma_d + \epsilon}, \qquad
z = \frac{\mu - \mu_m}{\sigma / \sqrt{N}}
$$

with $\mu$ mean strategy return per observation, $\mu_m$ mean buy-and-hold (benchmark) return,
$\sigma$ std of strategy returns, $N$ number of return observations (in the paper, executed trades),
$r^2$ equity-curve fit/consistency, $\sigma_d$ downside deviation, $\epsilon = 10^{-6}$.

Piecewise definition (Algorithm 1), critical for numerical/economic behaviour:

$$
\text{score} =
\begin{cases}
100 + 100\,(1 - e^{-|z-1|}) & z \le 0 \quad\text{(underperforms; large penalty)}\\
100\,(1 - e^{-|z-1|})     & 0 < z \le 1 \quad\text{(marginal; smooth transition)}\\
-\mu\ln(z)r^2/(\sigma_d+\epsilon) & z > 1 \quad\text{(standard GT-Score; negated)}
\end{cases}
$$

**Direction — the objective is a minimized loss, not a maximized score.** Algorithm 1 line 6 writes
`score <- -mu*ln(z)*r^2/(sigma_d+eps)`, the negation of Eq. 1, and all four comparators in the
paper's §2.6 are named "Loss Function" (Simple = −Profit, Sharpe = −Sharpe, Sortino = −Sortino).
Only under minimization are the branch labels coherent: the $z \le 0$ branch evaluates to
163.2–200, which a maximizer would select as the *best* strategy in the grid. Verified against the
source PDF (arXiv:2602.00080v1 Algorithm 1, p. 5) — this section previously dropped that minus sign,
and code written from it would have inverted every selection.

**Where the paper is silent (do not attribute these to it).** A parameterization below $n_{\min}$ is
"assigned a large penalty" and nothing more — no value is given, so any sentinel is the
implementer's. $r^2$ is defined only as "the R-squared value measuring consistency of returns"; the
paper never says what is regressed against what. The stabilized-variance search direction, its
candidate ladder and its bounds come from the author's dissertation, not this paper, which states
only the 1% plateau criterion and the $n{=}50$ fallback.

**Required inputs.** Per-asset OHLCV to simulate the strategy; trade-level returns; benchmark
(buy-and-hold) return series.
**Parameters / defaults.** $n_{\min} = 50$ trades (below threshold ⇒ large penalty); optional
"stabilized variance" periodization: search $n^*$ where period-return variance changes < 1% across
recent candidates, fallback $n{=}50$. Optimizer: random search, 25 evals/trial (competitive with
TPE and GAs in the author's dissertation).
**Observed effect.** Walk-forward gen. ratio 0.365 vs 0.180–0.188 baselines (+98%); Monte-Carlo gen.
ratio 0.183 vs 0.116–0.117 (+56%); sacrifices ~2–6 pp of mean test return; paired $t$-test vs Sortino
$p<0.001$ (Cohen's $d=-0.083$), vs Sharpe $p=0.014$; all effect sizes small ($|d|<0.1$).
**Failure modes.** $z$ is a *parametric* Gaussian/i.i.d. screen — fat tails, heteroskedasticity, and
autocorrelation overstate effective sample size; treat $z$ as a heuristic gate, not an exact test.
$\sigma_d$ over-penalizes skewed return distributions. Higher trade counts under GT selection
(32.4 vs ~21.0) make friction-sensitive; robustness held for extra per-side costs 0–10 bps.

### 2.2 Generalization ratio
**Purpose.** Cheapest single health metric for any walk-forward run: how much of the in-sample
result survives out of sample.
$$
\text{GR} = \frac{\text{return}_{\text{validation}}}{\text{return}_{\text{training}}}
$$
Higher is better; values near 1 mean little decay. Use as a regression test between objective
functions under an identical evaluation budget (arXiv:2602.00080v1).

### 2.3 Walk-forward protocol with embargo
Fixed structure worth adopting verbatim as FinRobot's default: training window 4y, validation
window 2y, step 1y, and an **embargo of 30 days between train and validation** to prevent leakage
(arXiv:2602.00080v1). Runs 9 sequential splits; seed Monte-Carlo the optimizer 15× (seeds 42–56).

### 2.4 Combinatorial Purged Cross-Validation (CPCV)
**Purpose.** Generate many out-of-sample paths from limited history and produce the
candidate-by-fold matrix that PBO needs.
Split the timeline into $N$ groups; choose $k$ as the test groups. Number of train/test splits:
$\binom{N}{k}$; number of *distinct backtest paths* $\phi[N,k] = \frac{k}{N}\binom{N}{k}$.
Example: $N{=}6, k{=}2 \Rightarrow 15$ splits but only 5 distinct paths — do not treat fold count as
effective sample size. Apply a purge around each boundary and an embargo after it
(arXiv:2608.23808v2; also arXiv:2209.05559v6 with $N{=}5,k{=}2\Rightarrow J{=}10$).

### 2.5 Probability of Backtest Overfitting (PBO) via CSCV
**Purpose.** Fraction of cases in which the in-sample winner ranks below the median out-of-sample.
Operational procedure (arXiv:2209.05559v6):
1. For each of $H$ trials, build the average return vector over the validation sets:
   $R_{\text{avg}} \in \mathbb{R}^{T'}$.
2. Stack into $M \in \mathbb{R}^{T' \times H}$ (rows = time, columns = trial).
3. Split $M$ across rows into symmetric IS/OOS subsets $c$; rank IS and OOS columns; let
   $r^{c}[\eta]$ be the OOS rank of the best IS strategy with relative rank
   $\omega^c = r^c[\eta]/(H+1)$; logit $\lambda^c = \ln\!\frac{\omega^c}{1-\omega^c}$.
4. $p = \int_{-\infty}^{0} f(\lambda)\,d\lambda$; if $\omega < 0.5 \Rightarrow \lambda<0 \Rightarrow$ overfit.
If the full candidate-by-fold matrix is unavailable, report a labeled rank-correlation proxy rather
than claiming the true CSCV estimator (arXiv:2608.23808v2). **Watch the degeneracy:** collapsed CSCV
combinatorics give a degenerate $PBO=0$ point mass (14.4% of production rows), which a naive logit
clamp turns into a huge positive margin — clamp-inclusive dispersion was needed to stop it
dominating the score (arXiv:2608.23808v2).

### 2.6 Overfitting detection as a hypothesis test (RL/ML agents)
Frame acceptance directly (arXiv:2209.05559v6):
$$
H_0: p < \alpha \ \text{(not overfitted)} \quad\text{vs}\quad H_1: p \ge \alpha \ \text{(overfitted)}
$$
with $\alpha$ set by the Neyman–Pearson framework (they use 10%; a stricter operator can use 5%).
Reject any agent whose estimated $p$ exceeds $\alpha$. Trial count: choose $H$ so the search is
reasonably covered, $1-(1-0.05)^H \ge 0.9 \Rightarrow H \ge 50$ assuming the good region is ≥5% of the
grid. Observed: $p_{\text{PPO}}{=}8.0\%$ (accept), $p_{\text{TD3}}{=}9.6\%$ (accept),
$p_{\text{SAC}}{=}21.3\%$ (reject), vs walk-forward $17.5\%$ (reject) and K-fold $7.9\%$ (accept);
the accepted least-overfit agent earned ≥15% more cumulative return and had lower volatility.

### 2.7 Deflated Sharpe Ratio (DSR) gate
**Purpose.** Ask whether the selected Sharpe remains unusual *after* accounting for the number of
independent trials and non-Gaussian returns. Deflation uses the expected maximum under the null over
$N$ trials; the variance correction is the i.i.d. Mertens adjustment for skewness $\gamma_3$ and raw
kurtosis $\gamma_4$:
$$
\operatorname{Var}[\hat{SR}] \propto \frac{1}{T}\Big(1 - \gamma_3\,SR + \frac{\gamma_4-1}{4}SR^2\Big),
\qquad \frac{\gamma_4-1}{4} = \frac{\kappa+2}{4}
$$
where $\kappa$ is excess kurtosis. Gate threshold $\tau_{DSR}=0.95$ (arXiv:2608.23808v2).
**Practical knobs.** Use the *effective* number of independent trials (decorrelate searched parameter
vectors by an eigenvalue approach), not the raw count of configurations. Compute the deflation
benchmark variance from the null sampling variance of the Sharpe estimator, $1/\text{years}$
(≈$1/T$ per bar) from Lo (2002) — not a fixed constant, which over-deflates long histories. The
paper's ground-truth A/B showed this correction lifted true-positive rate from 1% → 41% while
keeping false-positive rate on pure noise at exactly 0%. Family-level empirical variance estimation
was *rejected* because it reduced AUROC 0.96 → 0.50.

### 2.8 Minimum Track Record Length (MinTRL)
**Purpose.** Is the track record long enough to support the observed per-bar Sharpe at
confidence $1-\alpha$?
$$
\text{MinTRL} = 1 + \Big(1 - \gamma_3\,SR + \frac{\gamma_4-1}{4}SR^2\Big)\Big(\frac{\Phi^{-1}(1-\alpha)}{SR}\Big)^2 ,
\qquad \alpha = 0.05
$$
Gate passes iff $T \ge \text{MinTRL}$. Note MinTRL depends only on the single strategy (independent
of $N$ trials) — do not confuse it with Minimum Backtest Length
$\text{MinBTL} \approx 2\ln N / E[\max]^2$, which *does* account for multiple testing
(arXiv:2608.23808v2).

### 2.9 Superior Predictive Ability (SPA) gate
White's Reality Check with a less-conservative multiple-testing correction and a **block bootstrap**;
gate passes iff $p \le 0.10$ (loosen/tighten without changing structure). Addresses benchmark luck
after accounting for dependence and repeated comparison (arXiv:2608.23808v2). Alternatives noted:
Romano–Wolf StepM, Model Confidence Set, FDR, HAC-corrected Sharpe (Lo/Newey–West).

### 2.10 Regime-stability diagnostic
The one non-standard gate (arXiv:2608.23808v2, Eq. 3):
$$
\rho = 0.5\,p_+ + 0.3\,\operatorname{clip}_{[0,1]}\!\Big(1 - \frac{s_{SR}}{\sigma_{ref}}\Big) + 0.2\,\operatorname{logistic}(SR_{\min}),
\qquad \sigma_{ref}=2
$$
with $p_+$ fraction of validation windows with positive Sharpe, $s_{SR}$ std of per-window Sharpe,
$SR_{\min}$ minimum window Sharpe, $\operatorname{logistic}(x)=1/(1+e^{-x})$; clipped to $[0,1]$;
gate threshold $\tau_\rho = 0.60$. Weights are heuristic; the paper flags this as its most ad-hoc
component and notes it contributes ~39% of the aggregate at the theoretical bound despite a 0.10
nominal weight.

### 2.11 MinervaScore aggregation & verdict-consistent display
**Purpose.** Combine gates into one ranking while guaranteeing that passing the Seal implies a
displayed score ≥ 80.
1. Convert each gate to a **signed standardized margin** on a scale where the gate stays
   informative: DSR on the *pre-Φ statistic* $u$ (so $z_{DSR} = (u - \Phi^{-1}(\tau_{DSR}))/\sigma_{DSR}$,
   $u = (SR - SR_0)/se_b$, $\text{DSR}=\Phi(u)$); bounded gates PBO/SPA/ρ via logit with clamp
   $\varepsilon=10^{-6}$; MinTRL via tanh with $\sigma_T=\max(0.2\,\text{MinTRL}, 50)$.
2. Weighted inverse-normal combination:
   $$S = \frac{w^\top z}{\sqrt{w^\top \Sigma_{eff}\, w}}, \qquad w = (0.35, 0.25, 0.20, 0.10, 0.10)$$
   $\Sigma_{eff}$ is the cross-sectional correlation matrix of margins (positive definite; smallest
   eigenvalue 0.21 in their calibration), estimated once and shared.
3. Conservative offset then map: raw $r = \Phi(S - c)$ with $c = 0.5$; display = 80 + 20·(r−r₀)/(r*−r₀)
   if Seal passed, else percentile band min(80·F_b(r), 80−δ), δ=0.1.
**Hard rule from the paper:** the pre-Φ statistic must be stored at DSR computation time. If only
the DSR value is stored, **fail closed** (emit no score), because $\Phi^{-1}(0)$ collapses to
≈−4.75 and destroys the ranking. Do not feed the MinervaScore back into the search loop
(Goodhart); keep search objective and validator separate (arXiv:2608.23808v2).

### 2.12 Execution-realistic deterministic replay
**Purpose.** Make backtests reproducible and cost-honest for binary/prediction contracts.
Requirements from PredictionMarketBench (arXiv:2602.00133v1): self-contained episode =
`metadata.json` (tickers, time bounds, bankroll, execution mode, fee-model version) +
`orderbook.parquet` + `trades.parquet` + `settlement.json`; event-driven simulator processing events
by timestamp (sequence numbers break ties); maker/taker semantics with queue position; deterministic
RNG seeded per episode; fixed decision cadence (300 s) and equity sampling (60 s); full trajectory
logging + checkpoints every 50 steps. Fee model for binary contracts:
$$
\text{taker fee} = 7\% \times \text{price} \times \big(1 - \text{price}/100\big), \qquad
\text{maker fee} = 1.75\% \times \text{price} \times \big(1-\text{price}/100\big)
$$
At 50c: taker 1.75c/contract, maker 0.44c/contract → robust fee-aware strategies must prefer GTC /
POST_ONLY maker orders.

### 2.13 Adaptive Benign Overfitting (QR-EWRLS) — overparameterized online regression
**Purpose.** For non-stationary online forecasting, deliberately overparameterize (Random Fourier
Features, $D > N$) and rely on minimum-norm implicit regularization instead of explicit ridge.
- RFF map: $z_t = \sqrt{2/D}\,\cos(A^\top x_t + b)$, $\omega_j \sim p$, $b_j \sim U[0,2\pi]$.
- Objective: minimum-$\ell_2$-norm interpolator
  $\hat\beta_t = \arg\min \|\beta\|_2 \ \text{s.t.}\ Z_t\beta = Y_t = Z_t^{\dagger}Y_t$.
- Kept numerically stable by QR factorization $Z_t = Q_tR_t$ with Givens rotations and a
  Greville/Cline pseudoinverse update, so updates cost $O(ND)$, not $O(D^2)$. Forgetting factor
  $\lambda \in (0,1]$ gives exponentially weighted RLS (EWRLS), absorbing non-stationarity.
- **Effect:** reproduces double descent; test error peaks at interpolation where the effective
  condition number of $Z^\top Z$ is largest and falls again as $D$ grows; 20–40% speed-ups vs kernel
  baselines on FX and electricity-demand forecasting (arXiv:2601.22200v1).
- **Backtest-relevant reading:** feature-dimension and forgetting-factor choices act as bias–variance
  knobs; ridge violations aside, a wider RFF model can generalize *better* but only under favourable
  spectral conditions — measure the condition number of the design matrix as a diagnostic, and treat
  the double-descent minimum as the operating point.

### 2.14 Uncertainty / robustness reporting
Run each model 5× and report std of return, Sharpe, volatility (and win rate) alongside the mean
(arXiv:2510.15903v1). Fit complexity/training-time-versus-performance trade-offs explicitly. This
catches "best-looking single run" selection.
**Time-series split** to avoid leakage: 70% train / 15% validation / 15% test, chronologically
ordered (arXiv:2510.15903v1).

---

## 3. Data requirements → available endpoints

Every row cites a real endpoint from `strategies/endpoints.json`.

| Input | Endpoint | Category | Provider | Probe status |
|---|---|---|---|---|
| Daily OHLCV (backtest engine / GT-Score / walk-forward) | `https://eodhd.com/api/eod/AAPL` | core_stock_apis | eodhd | ok |
| Daily OHLCV (failover) | `https://api.tiingo.com/tiingo/daily/AAPL/prices` | core_stock_apis | tiingo | ok |
| Daily OHLCV (failover) | `https://api.twelvedata.com/time_series` | core_stock_apis | twelvedata | ok |
| Daily OHLCV (failover) | `https://api.stockdata.org/v1/data/eod` | core_stock_apis | stockdata | ok |
| Daily OHLCV (failover) | `https://api.massive.com/v2/aggs/ticker/AAPL/prev` | core_stock_apis | massive | ok |
| Adjusted prices — splits/dividends | `https://eodhd.com/api/div/AAPL` | corporate_actions | eodhd | ok |
| Benchmark / buy-and-hold series (e.g. SPY) | `https://eodhd.com/api/eod/AAPL` | core_stock_apis | eodhd | ok |
| Risk-free rate for Sharpe / DSR | FRED series observations (e.g. DGS1MO) — `https://api.stlouisfed.org/fred/series/observations` | macro_data | fred | ok |
| Treasury curve (term-structure benchmark) | `https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2026/all` | risk_free_curve | federal_reserve | ok |
| Intraday bars for RL/ML backtests | `moomoo://get_cur_kline` | technical_indicators | moomoo | gateway (ok=false, local OpenD SDK) |
| Equity market snapshot for agent envs | `moomoo://get_market_snapshot` | core_stock_apis | moomoo | gateway (ok=false) |
| Prediction-market contracts (binary YES/NO) | `https://gamma-api.polymarket.com/markets` | prediction_markets | polymarket | ok |
| News / exogenous features for agent replay | `https://api.gdeltproject.org/api/v2/doc/doc` | news_sentiment | gdelt | **fail** (rate_limited HTTP 429) |
| News / exogenous features (failover) | `https://eodhd.com/api/news` | news_data | eodhd | ok |
| Crypto OHLCV (5-min bars for the DRL crypto backtest) | — | — | — | **gap** — no crypto bar endpoint in the 49-row inventory; equity routes only |
| Crypto volatility index (CVIX, risk-control threshold 90.1) | — | — | — | **gap** |
| S&P BDM crypto index benchmark | — | — | — | **gap** |
| Prediction-market limit-order-book + trade prints + settlement streams | polymarket gamma exposes markets/quotes only; no LOB/trade/settlement stream inventoried | prediction_markets | polymarket | **gap** (markets only; replay harness data unavailable) |
| Parameter-search trial ledger (for effective-trials / DSR deflation) | — | — | — | **schema implemented, not yet fed** — `TrialLedger` + `build_ledger_from_search` persist every trial's per-fold returns and its stored pre-Φ statistic; the `--auto` strategy agent does not write one yet, so a CLI run has no ledger to score |

**Reading of the table.** The validation machinery (GT-Score, walk-forward, CPCV, DSR, MinTRL, SPA,
MinervaScore) needs only daily equity OHLCV + a benchmark + a risk-free rate — all reachable today
(eodhd/tiingo/twelvedata/fred, all `ok`). The one hard dependency to fix first is that
**FinRobot must persist its own optimizer trial ledger** (every evaluated parameter set + its
per-fold performance + the pre-Φ DSR statistic) or PBO/effective-trials/DSR are not computable.
Crypto and prediction-market replay are **gaps**: the app routes there (`prediction_markets`,
crypto has no category) but the inventory has no LOB/trade/settlement or crypto-bar endpoints, so
§2.12 and the crypto DRL protocol are documented for design, not yet implementable end-to-end.

---

## 4. Pitfalls, validation and measurement

**Leakage the papers demonstrate.**
- *Repeated train↔test peeking.* Authors "go back and forth between training and testing periods";
  this is the most common cause of backtest overfitting (arXiv:2209.05559v6). Enforce a **locked test
  window that the iterative loop never touches** — the sealed-window discipline in
  arXiv:2608.23808v2 opened the OOS window exactly once.
- *Single validation block.* A walk-forward validation period can be biased (e.g. a bull regime);
  one split overfits "one market situation" (arXiv:2209.05559v6).
- *IID K-fold.* Standard K-fold assumes train/test come from an IID process, false for financial
  series (crypto momentum), and creates correlated folds ⇒ leakage. Use purged/embargoed
  combinatorial splits instead (arXiv:2209.05559v6, arXiv:2608.23808v2; embargo 30 days in
  arXiv:2602.00080v1).
- *Cost/settlement leakage.* Ignoring fees and settlement flips rankings: naive activity underperforms,
  and backtest engines agreed when costs were ignored but diverged significantly once included
  (arXiv:2602.00133v1). Store the cost-model configuration with every result.
- *Hyperparameter search as a hidden multiple test.* Selecting the best of many DRL configs is a
  selection effect; the winner is the maximum of many noisy draws (arXiv:2209.05559v6,
  arXiv:2608.23808v2).
- *Adaptive-data-analysis hazard.* A human iterating "submit variant → read score → choose next
  variant" on the same data reproduces selection-induced overfitting at the analyst level; the gates
  cannot see rejected variants. Mitigate with reusable-holdout discipline, query budgets, and a
  locked final window (arXiv:2608.23808v2).
- *Goodhart.* Never optimize a validator; a metric is trustworthy only if it was not the search
  target (arXiv:2608.23808v2 §9.1).

**Overfitting/regime caveats.**
- Effect sizes are small even when significant: GT-Score vs baselines has $|d|<0.1$; the MinervaScore
  beats corrected-DSR-alone by ~0.001 AUROC (a nominal tie). Report effect sizes, not just $p$-values
  (arXiv:2602.00080v1, arXiv:2608.23808v2).
- Synthetic ground truth is *cleaner* than real markets: MinervaScore's synthetic admission rate
  (8.15%) is an upper bound, and its real-market forward test was null — a conservative validator
  should stay silent when no edge exists (arXiv:2608.23808v2).
- Boundary/saturation: 60–95% of DSR values are exactly 0 in production; use the pre-Φ statistic,
  not $\Phi(u)$, or the ranking collapses. Bounded gates need clamp-inclusive dispersion (PBO clamp
  at 14.4% degenerate mass).
- Non-normal returns: Gaussian/i.i.d. significance terms are heuristics. Use bootstrap (SPA block
  bootstrap), rank-based (PBO, regime), and skew/kurtosis-corrected (DSR) machinery rather than raw
  Gaussian thresholds.
- Benign overfitting is not a free lunch: double descent requires favourable spectral conditions; if
  violated (e.g. extreme deterministic frequencies) performance degrades. Monitor the effective
  condition number (arXiv:2601.22200v1).

**How to test an implementation is sound.**
1. **Unit-test the invariant** `Display ≥ 80 ⇔ Seal passed` over synthetic records; check no failing
   record displays ≥80 and no passing record below 80 (the paper holds this with zero violations over
   359,062 rows).
2. **Rank-stability audit**: perturb every weight by ±20% and the offset; require Spearman ρ of the
   induced ordering ≥0.997 and exact rank-invariance for the offset.
3. **Ground-truth synthetic harness** (Arian-style): generate winners of searches with $n_{trials}\sim$
   LogUniform(20, 5000) folds, half containing a genuine candidate with true annualized
   $SR \sim U(0.5, 2.5)$ and half pure noise; measure AUROC for separating genuine edge; sweep
   history length $T \in \{504, 1260, 2520\}$ and edge strength; report worst-case regret.
4. **Sensitivity to search size**: score must fall ~0.7σ per tenfold increase in trials for noise
   searches and the Seal rate must fall for genuine searches as $n_{trials}$ grows.
5. **Sensitivity to history**: DSR margin for pure-noise strategies must stay flat as $T$ grows;
   genuine strategies' margin must rise (the flat-trend property is the signature of a correctly
   specified null benchmark).
6. **Pre-register** the real-market study (freeze enrollment, exclusion rules, analysis plan, and
   calibration commit before unsealing) and report the null result honestly.
7. **Determinism test**: same episode files + config + seed ⇒ identical trade log/equity curve
   (replay harness regression test, arXiv:2602.00133v1).
8. **Cost sensitivity**: rerun net returns at extra per-side cost 0–10 bps and confirm the ranking of
   objective functions is stable (arXiv:2602.00080v1 Fig. 3).

---

## 5. Recommended first implementation in FinRobot

**Implementation status (2026-10-10).** Items 1–7 below are built, as a self-contained gate in
`finrobot/engine/backtest/validation/`: GT-Score and the generalization ratio (`scores.py`),
walk-forward and combinatorial purged splits (`splits.py`), the trial ledger and its search→ledger
builder (`ledger.py`), PBO/CSCV, deflated Sharpe with an effective-trial count, MinTRL, the SPA
block bootstrap and the regime diagnostic (`overfitting.py`), and the five-gate aggregate with its
verdict-consistent display (`minerva.py`), driven end to end by `finrobot validate <ledger.jsonl>`
(`validate.py`). The same package also carries the two report primitives the LLM-corpus document
asks for beside a score — a Diebold–Mariano comparison of two forecasts and a percentile
block-bootstrap confidence interval for the Sharpe ratio (`overfitting.py`) — since a point Sharpe
with no interval is the number this whole document exists to stop trusting.

Items 8–9 are the reason this is a *gate* rather than a full backtest stack: the
RL-agent acceptance test needs intraday bars (moomoo gateway, so conditional on a local OpenD SDK),
and the prediction-market replay harness needs a limit-order-book/trade/settlement feed that §3
marks as a gap — the harness is not written, and filling it with invented fills would be worse than
leaving it absent. Item 9 also specifies a schema this repo has nowhere to store.

1. **GT-Score as an optimizer objective.** Build `gt_score(trade_returns, benchmark_returns, equity_curve)`
   implementing §2.1 with $n_{\min}=50$ and the piecewise branches. Data: eodhd daily OHLCV
   (`core_stock_apis`, ok) + benchmark. Expected value: +98% walk-forward generalization ratio under
   the paper's protocol; near-zero raw-return cost. Risk: parametric $z$ gate mis-calibrates on
   autocorrelated/fat-tailed returns — log it, never hard-gate on it. Effort **S**.
2. **Walk-forward harness with embargo.** Standardize train 4y / validate 2y / step 1y / 30-day
   embargo, 9 splits; expose the generalization ratio as a first-class report field. Data: same OHLCV.
   Value: the baseline unit every other technique plugs into. Effort **M**.
3. **CPCV + PBO gate.** Implement combinatorial purged splits ($N,k$ with $\phi[N,k]$ paths) and the
   CSCV rank-logit PBO from §2.5; emit the candidate-by-fold matrix and fail closed if it is missing.
   Data: trial ledger (see item 7). Value: the strongest single overfitting diagnostic for
   search-heavy strategies. Risk: degenerate $PBO=0$ point mass — use clamp-inclusive dispersion.
   Effort **M**.
4. **DSR + MinTRL gates.** Implement §2.7–2.8 with the Mertens skew/kurtosis correction, effective
   trial count via eigenvalue decorrelation, and the Lo null benchmark $1/\text{years}$; store the
   pre-Φ statistic. Data: trade-level returns (from OHLCV) + trial ledger. Value: selection-aware
   significance, the strongest single discriminator per the paper's grid. Effort **M**.
5. **SPA block-bootstrap gate + regime diagnostic.** §2.9–2.10; keep $\tau_{SPA}=0.10$,
   $\tau_\rho=0.60$, $\sigma_{ref}=2$. Value: covers benchmark-luck and regime-dependence failure
   modes the DSR misses. Effort **M**.
6. **MinervaScore aggregation layer.** §2.11: margins on natural scales, weighted inverse-normal
   blend with frozen $\Sigma_{eff}$, verdict-consistent 0–100 display, and the Seal. Data: outputs of
   items 3–5. Value: one auditable robustness grade per backtest. Risk: calibration is
   population-relative — version it and document the vintage. Effort **M**.
7. **Persist the optimizer trial ledger.** Every evaluated parameter set + per-fold performance + bar
   counts + the pre-Φ DSR statistic + cost-model version. This is the prerequisite for items 3–6 and
   the single biggest data-layer gap (§3). Effort **S** (schema) — **do this first**.
8. **RL/ML agent acceptance test.** Combinatorial CV + the §2.6 hypothesis test ($H\ge50$ trials,
   $\alpha=10\%$) to reject overfitted agents before deploy. Data: intraday bars (moomoo gateway) —
   mark the crypto gap explicitly. Effort **M**.
9. **Deterministic replay simulator for prediction markets.** Episode format, event-driven loop,
   maker/taker fees, fixed seeds, trajectory logging (§2.12). Data: polymarket markets (ok) + a LOB/
   trade/settlement feed that is currently a **gap**; implement the harness with the gap flagged, do
   not fake fills. Effort **L**.
10. **Uncertainty reporting standard.** Every model/strategy run reports 5-run mean ± std of return,
    Sharpe, volatility, drawdown; time-series split 70/15/15; store cost model alongside results
    (§2.14). Effort **S**.

---

## Appendix — papers read

| arXiv id | title | year |
|---|---|---|
| 2602.00080v1 | The GT-Score: A Robust Objective Function for Reducing Overfitting in Data-Driven Trading Strategies | 2026 |
| 2608.23808v2 | Equity Strategy Backtesting: Luck or Edge? The MinervaScore as a Statistical Robustness Grade | 2026 |
| 2602.00133v1 | PredictionMarketBench: A SWE-bench-Style Framework for Backtesting Trading Agents on Prediction Markets | 2026 |
| 2209.05559v6 | Deep Reinforcement Learning for Cryptocurrency Trading: Practical Approach to Address Backtest Overfitting | 2022 |
| 2601.22200v1 | Adaptive Benign Overfitting (ABO): Overparameterized RLS for Online Learning in Non-stationary Time-series | 2026 |
| 2510.15903v1 | Quantum and Classical Machine Learning in Decentralized Finance: Comparative Evidence from Multi-Asset Backtesting of Automated Market Makers | 2025 |
