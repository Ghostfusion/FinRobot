# Risk Management & Tails — learnings from the q-fin.ST corpus
`426` of 4372 corpus papers matched this category (426 with PDFs); this doc is based on a close reading of `6`.

## 1. What the corpus actually offers

- **Multiplex Network Hawkes systemic-risk measure** (arXiv:2606.15755). Contagion is modelled as a mutually-exciting point process on firms. The *event* is an "extreme credit-spread jump": a 5-year CDS log-return exceeding the firm's own 99th percentile. Sample: $K{=}99$ firms, $N{=}1905$ events over $T{=}4696$ business days (2004–2022), median inter-event gap $\le 2$ days after removing same-day events. Weighted out-degree is read as *systemic contribution* (analogue of CoVaR) and weighted in-degree as *vulnerability* (analogue of expected shortfall); degree distributions are fit by power law (preferred by log-likelihood ratio over KDE/log-normal/exponential in every model setup). Findings: transmission is sparse and directional (low reciprocity), concentrated in a few outward hubs, and not strongly clustered/small-world; asset-similarity, solvency and profitability channels all contribute to excitation.
- **Gai–Kapadia default cascades + tail risk on equities** (arXiv:2604.19796). Extends interbank cascade logic to an equity exposure network built from price co-movements: $E_{ij}=\rho_{ij}\,\sigma_i\,P_i$, thresholded at $\theta\in\{0.3,0.5\}$. Tail risk via historical VaR/CVaR at 95% and Hill/Pareto estimates. Result: Brazilian assets are heavily clustered ($C_i\approx0.8{-}1.0$) with heavier tails (AMER3.SA Hill $\hat\alpha\approx1.84$, CCDF $\alpha\approx1.5$; CVaR $=-0.0633$) vs developed markets ($C_i\approx0.2{-}0.5$, AAPL CVaR $=-0.0210$). Cascades are localised: $n{=}1000$ Monte Carlo runs give zero probability of $>5$ failures; average failed assets $1.0$ (single shock) / $2.0$ (simultaneous).
- **Ising / QUBO financial-contagion framework** (arXiv:2609.17415). Casts the Elliott–Golub–Jackson (EGJ) cross-holding model with threshold failures as a nonlinear fixed point, then encodes *Maximum Cascade Failure* and *Optimal Bailout Allocation* as QUBO/Ising problems solvable by annealing. Introduces *bailout susceptibility* (a linear-response systemic-importance measure) and a pinning condition for guaranteed rescue.
- **Two-layer supply-chain ↔ interbank stress test** (arXiv:2502.17044). Firm-level production network (Generalized Leontief production functions) coupled to an interbank layer via bank–firm loans; calibrated on ~1M firm links and all bank/interbank loans of Hungary. Defaults propagate as firm-loan write-offs, then through the interbank layer via (linearized) DebtRank. Headline amplification: interbank contagion raises individual-firm systemic risk by up to **28%** (plateau firms **12%**); supply-chain contagion raises banking-system EL by **68%** and ES by **67%**; adding interbank contagion raises EL by **83%** and ES by **83%**.
- **Conditional reverse stress testing (RST)** (arXiv:2606.09274). Reconstructs a *coherent multivariate* stress scenario by maximising the conditional density of non-shocked assets given a single imposed shock; solved parametrically (Gaussian, closed form), semiparametrically (empirical likelihood, uniform-weight closed form) and nonparametrically (Mahalanobis-neighbourhood resampling). Validated on five asset-class indices over $T=5\times252$ days; a $-11\%$ shock to European govvies over 58 days produces equity median responses of $+12\%$ (EU) and $+11\%$ (US) with expanded inter-quantile ranges — the documented risk–reward asymmetry of stress regimes.
- **CBDC stress test in a dual-currency setting** (arXiv:2511.13384). Broadly **off-topic for tail estimation**: its stress overlays, adoption and liquidity simulations are built on *synthetic* agent populations, and the author explicitly states outputs are "scenario-based illustrations of methodological feasibility, not predictive or probabilistic forecasts." Useful only as a caution (see §4): it couples VAR/MSVAR/SVAR macroeconomic transmission with XGBoost/logistic adoption scoring — none of which yields a calibrated tail estimator. It is retained here for the caveat, not as a model to port.

## 2. Implementable formulas & algorithms

### 2.1 Historical / EVT tail estimators (VaR, ES, Hill)
**Purpose.** Per-instrument or portfolio downside quantiles without distributional assumptions.

$$\mathrm{VaR}_{i,\alpha}=F_i^{-1}(1-\alpha),\qquad \mathrm{CVaR}_{i,\alpha}=\mathbb{E}\!\left[r_{i,t}\,\middle|\,r_{i,t}\le \mathrm{VaR}_{i,\alpha}\right]$$

with $\alpha=0.95$ in arXiv:2604.19796 (losses reported as negative numbers, e.g. AAPL $\mathrm{CVaR}_{95}=-0.0210$). Heavy-tail severity via the Hill estimator on the $k$ largest losses $X_{(1)}\ge\dots\ge X_{(k)}$:

$$\hat\alpha(k)=\left[\frac1k\sum_{i=1}^{k}\log X_{(i)}-\log X_{(k+1)}\right]^{-1}$$

**Inputs.** Daily log-returns $r_{i,t}$.
**Parameters.** Confidence $\alpha=0.95$ (paper); Pareto fit threshold = 95th percentile of losses; Hill $k$ chosen from the stable plateau of the Hill plot (paper reads AMER3.SA $\hat\alpha\approx1.84$ over the intermediate-$k$ stable region).
**Effect sizes.** Emerging-market CVaR roughly $3\times$ developed-market CVaR ($-0.0633$ vs $-0.0210$); $\hat\alpha<2$ implies infinite-variance regime.
**Failure modes.** Requires i.i.d. (Hill); autoconditional volatility and serial correlation bias both $\hat\alpha$ and historical VaR downward. Small $k$ → high variance, large $k$ → bias.

### 2.2 Conditional reverse stress testing (Gaussian and empirical-likelihood variants)
**Purpose.** From an exogenous shock on one factor, recover the *most likely* coherent joint scenario for all others, then simulate the stressed joint distribution.

Inputs: shock index $j$ (WLOG $j=1$), cumulative shock $S$, window start $T_{\text{start}}$, window length $T_{\text{win}}$. Daily-equivalent shock:

$$s:=(1+S)^{1/T_{\text{win}}}-1 .$$

**Parametric (joint Gaussian).** With block covariance $\Sigma$, the modal scenario is the conditional mean and the stressed covariance is the Schur complement:

$$\bar r^{s}_{-1}=\mu_{-1\mid1}=\mu_{-1}+\Sigma_{-1,1}\Sigma_{11}^{-1}(s-\mu_1),\qquad
\Sigma_{-1\mid1}=\Sigma_{-1,-1}-\Sigma_{-1,1}\Sigma_{11}^{-1}\Sigma_{1,-1}.$$

**Semiparametric (empirical likelihood).** Restrict to the conditioned sub-sample $I^s=\{t:\lvert\hat r_{1,t}-s\rvert\le\varepsilon\}$, maximise the profile empirical likelihood

$$\ell(x)=\max_{w\in\Delta_{T^s}}\Big\{\textstyle\sum_t\log w_t:\sum_t w_t\hat r_t=x\Big\}.$$

For a concave log-likelihood, the unique optimum is the **uniform-weight** estimator

$$\bar r^{s}=\frac1{T^s}\sum_{t=1}^{T^s}\hat r_t .$$

Sampling around $\bar r^s$: Gaussian $N_d(\bar r^s,\hat\Sigma^s)$ or Student-$t$ via scale mixture $q_k\sim N_d(0,\hat\Sigma^s)$, $p_k\sim\chi^2_\nu$, $\hat r_{ks}=\bar r^s+\sqrt{\nu/p_k}\,q_k$ (scale matrix rescaled by $\tfrac{\nu-2}{\nu}$ to make covariance $=\hat\Sigma^s$; $\nu>2$).

**Nonparametric.** Mahalanobis ball $B(\bar r^s,\varepsilon)$, selection probabilities $\pi_t\propto d_t^{-1}=\left[(\hat r_t-\bar r^s)^\top(\hat\Sigma^s)^{-1}(\hat r_t-\bar r^s)\right]^{-1/2}$, resample with replacement.
**Parameters.** $T_{\text{win}}{=}58$ days; $\varepsilon$ balances bias/variance (effective sample size vs locality); local covariance $\hat\Sigma^s$ estimated on the conditioned sub-sample ("local" vs "global" covariance are both reported).
**Effect sizes.** $-11\%$ shock (European govvies, 58 days) → equity $Q_{50}$ $+12\%$/+11%, $Q_{95}$ $+49\%$/$+62\%$, $Q_5$ $-22\%$/$-34\%$ (stress asymmetry).
**Failure modes.** Semiparametric/nonparametric variants "may overfit idiosyncratic noise" of historical stress episodes (news-driven, near-independent shocks); the Gaussian local sampler reimposes a light tail; convex-hull assumption can fail if the target scenario lies outside the observed sample.

### 2.3 Gai–Kapadia equity cascade
**Purpose.** Probabilistic and deterministic default-cascade simulation on a price-derived exposure network.

Exposure, thresholding, clustering:
$$E_{ij}=\rho_{ij}\sigma_i P_i,\quad \tilde E_{ij}=E_{ij}\,\mathbf 1[E_{ij}\ge\theta],\quad C_i=\frac{2T_i}{k_i(k_i-1)} .$$

Cascade (stochastic): capital $K_i=0.2\,P_i$, failure barrier $K_{\min,i}=0.1\,P_i$, random shock $s\sim\mathrm{Uniform}(0.1,0.5)$, $n=1000$; loss pass-through
$$L_{ij}=\max\!\big(0,\tilde E_{ij}-(K_i-D_i)\big),\qquad D_i=\textstyle\sum_j \tilde E_{ji}.$$

Deterministic: influence $I_i=\sum_j \rho_{ij}S_j$, default if $I_i>T_i$ with $T_i=0.5$; recursive form $D_i^{(t+1)}=\mathbf 1\!\big[\sum_j E_{ij}D_j^{(t)}>\tau_i\big]$.
**Parameters.** $\theta\in\{0.3,0.5\}$; $\tau_i=0.5$; 30 assets; IQR filter $1.5\times$ on raw observations before correlation.
**Observed.** $\mathbb{P}(>5\text{ failures})=0$; avg failures $1.0$/$2.0$; propagation stabilises in a few iterations.
**Failure modes.** Static thresholds ignore correlation-regime change; IQR filtering *removes the very tails* the study then measures; exposure from in-sample correlation → look-ahead; near-critical networks under-sample rare large cascades (zero observed here).

### 2.4 DebtRank / FSRI interbank amplification
**Purpose.** Propagate bank equity losses through an interbank network and measure how much a firm's failure endangers the banking system.

Linearized DebtRank (Bardoscia 2015 adaptation) with interbank leverage $\Lambda_{lk}=L_{lk}/e_k$:
$$L_k(t,\psi)=L_k(t-1,\psi)+\sum_{l=1}^{m}\Lambda_{lk}\min\!\big(L_l(t-1,\psi),1\big),$$
terminating when $\sum_k L_k(t,\psi)-L_k(t-1,\psi)\le\epsilon$, $\epsilon=0.01$. Firm default indicator $\chi_i=1$ iff $z_i-\Delta p_i\le0$ **or** $a_i-s_i-\Delta p_i\le0$ (equity or short-term liquidity exhausted), with $\Delta p_i=(1-h_i(T))(r_i-c_i)$. Bank direct / supply-chain losses:
$$DI_k=\sum_i \frac{B_{ik}}{e_k}\chi_i^{WO},\qquad SC_k=\sum_i \frac{B_{ik}}{e_k}\!\left(\chi_i^{W}-\chi_i^{WO}\right).$$

Systemic-risk index with (and without) interbank contagion:
$$FSRI_i=\sum_{k=1}^{m}\frac{e_k}{\sum_l e_l}\min\!\big(L_k(1,\psi^i),1\big),\qquad
FSRI_i^{+}=\sum_{k=1}^{m}\frac{e_k}{\sum_l e_l}\min\!\big(L_k(T,\psi^i),1\big).$$

**Parameters.** LGD $=100\%$ (results scale proportionally for other LGD while no bank fails); convergence $\epsilon=0.01$; single-firm shock $\psi^j_i=\mathbf 1[i\neq j]$.
**Observed effect sizes.** Most-risky firms affect up to 22% of banking equity (24% with interbank); plateau firms +12% (amplification $1.12$); individual-bank amplification up to $1.28$; EL $3.6\to6.0\to6.6\%$, VaR $4.5\to7.2\to7.9\%$, ES $4.8\to8.0\to8.7\%$ across DI → DI+SC → DI+SC+IB.
**Failure modes.** Requires bilateral interbank exposures (unavailable publicly); linearized DebtRank overstates when banks actually default; LGD=100% overstates.

### 2.5 EGJ equilibrium, Maximum Cascade Failure and bailout (Ising/QUBO)
**Purpose.** Worst-case cascade and optimal bailout on a cross-holding network.

EGJ equilibrium and dependency matrix, with threshold failure penalty $b_i(v_i)=\beta_i[1-\Theta(v_i-v_i^c)]$:
$$V=(I-C)^{-1}Dp,\qquad \mathcal A=\hat C(I-C)^{-1},\qquad v=\mathcal A(Dp-b(v)).$$

The fixed point iterates $v_i^{(t)}=v_i^{(0)}-\sum_{j\in S^{(t-1)}}\mathcal A_{ij}\beta_j$ until $S^{(t)}=\{i:v_i^{(t)}<v_i^c\}$ stabilises. Maximum Cascade Failure ↔ ground state of
$$E(x)=-w\sum_i x_i+\lambda\!\!\sum_{\mathcal A_{ij}>\theta}\!\!\mathcal A_{ij}x_j(1-x_i)+M(1-x_s),\qquad x^\star=\arg\min E(x),$$
with penalty ordering $M\gg\lambda>w$. Bailout = controlled Ising Hamiltonian $H_{\text{ctrl}}(s,b)=-\sum_{i<j}J_{ij}s_is_j-\sum_i(h_i-\Omega_ib_i)s_i$; the **pinning condition** $\Omega_i>|h_i|+\sum_{j\neq i}|J_{ij}|$ guarantees a rescued institution stays in the surviving state. Bailout susceptibility $\chi_{ij}=\partial\langle s_i\rangle/\partial h_j$ is a linear-response measure of systemic importance; the paper reports that optimal policies stabilise a small number of institutions to interrupt propagation.
**Failure modes.** $\mathcal A$ is unknown without cross-holdings; NP-hard worst case (reduced from Balanced Complete Bipartite Subgraph); static, single-shock; is a deterministic optimisation, not a probabilistic tail measure.

### 2.6 Multiplex Network Hawkes systemic-risk measure
**Purpose.** Infer a directed excitation network among institutions and decompose it into contagion channels.

Conditional intensity for process $k$:
$$\lambda_k(t\,|\,\mathcal H_t)=\lambda_k^{(0)}+\sum_{k'=1}^{K}\sum_{\{n:s_{k',n}<t\}}\;\sum_{l=1}^{L} h^{(l)}_{k'\to k}(t-s_{k',n}),\quad h^{(l)}_{k'\to k}=G^{(l)}_{k'\to k}\,g_\theta(t-s_{k',n}),$$
$$G_{k'\to k}=\sum_{l=1}^{L}G^{(l)}_{k'\to k},\qquad G^{(l)}_{k'\to k}=A_{k'\to k}W^{(l)}_{k'\to k},$$
$$W^{(l)}_{k'\to k}\sim\mathrm{Gamma}\!\left(\tfrac1{\kappa^{(l)}},\tfrac1{\kappa^{(l)}\mu_{k'\to k}^{(l)}}\right),\quad \log\mu^{(l)}_{k'\to k}=x_{k'\to k}^{(l)\top}\beta^{(l)}.$$

Adjacency $A_{k'\to k}\sim\mathrm{Bern}(\rho)$; interactions are retained as $A\odot W^{(l)}$. Kernels $g$ are logistic-normal on $[0,\Delta t_{\max}]$.
**Inputs.** Firm event times = extreme credit-spread jumps (CDS log-return $>$ own 99th percentile).
**Parameters / conventions.** $\Delta t_{\max}=10$ days (robustness checked at 5 and 20); background $\lambda^{(0)}_k$; 20,500 MCMC draws, 10% burn-in, ASM then ASWAM; reference hyper-priors $\alpha^0_\lambda=1,\ \beta^0_\lambda=1,\ \alpha^0_\rho=\beta^0_\rho=10,\ a^0_\kappa=0.001,\ b^0_\kappa=10,\ \mu^0_\mu=-1,\ k^0_\mu=10,\ \alpha^0_\tau=10.5,\ \beta^0_\tau=1$.
**Effect sizes.** Sparsity $\hat\rho$ recovered within HDI (e.g. generated $0.085$ → posterior median $0.094$); power-law weighted-degree fit preferred in all setups; exploitability boundary at combined spectral radius $0.92$.
**Failure modes.** Event threshold computed on the full sample ⇒ look-ahead unless rolled; **label switching** across layers when channels are weakly separated (mitigated by ECR relabelling); strong prior sensitivity of $\beta,\kappa$ in sparse/low-information settings; kernel support misspecification (too-short $\Delta t_{\max}$ truncates the kernel).

## 3. Data requirements → available endpoints

Endpoint rows are the live-probed rows in `strategies/endpoints.json`; `gateway` = local moomoo OpenD SDK (not HTTP-probed), `missing`/`gap` = no current provider.

| Input | Endpoint | Category | Provider | Probe status |
|---|---|---|---|---|
| Daily OHLC / close prices (returns, drawdowns, VaR/ES) | `https://eodhd.com/api/eod/AAPL` | `CORE_STOCK_APIS` | eodhd | ok |
| Daily prices (fallback) | `https://api.tiingo.com/tiingo/daily/AAPL/prices` | `CORE_STOCK_APIS` | tiingo | ok |
| Daily prices (fallback) | `https://api.twelvedata.com/time_series` | `CORE_STOCK_APIS` | twelvedata | ok |
| Daily prices (fallback) | `https://api.stockdata.org/v1/data/eod` | `CORE_STOCK_APIS` | stockdata | ok |
| Daily prices (fallback) | `https://api.massive.com/v2/aggs/ticker/AAPL/prev` | `CORE_STOCK_APIS` | massive | ok |
| Intraday / kline (realized vol, EVT on intrada) | `moomoo://get_cur_kline` | `TECHNICAL_INDICATORS` | moomoo | gateway |
| Option chains (implied vol, expected move, tail-hedge cost) | `moomoo://get_option_chain` | `OPTIONS_DATA` | moomoo | gateway |
| SPX option surface (risk-neutral tails) | `https://cdn.cboe.com/api/global/delayed_quotes/options/_SPX.json` | `OPTIONS_SURFACE` | cboe | ok |
| Risk-free curve (excess/discounted returns) | `https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2026/all` | `RISK_FREE_CURVE` | federal_reserve | ok |
| Macro series (rates, CPI — MSVAR regime inputs) | `https://api.stlouisfed.org/fred/series/observations` | `MACRO_DATA` | fred | ok |
| Firm fundamentals (equity, revenue, costs, current assets/liabilities — default indicators) | `https://api.tiingo.com/tiingo/fundamentals/AAPL/statements` | `FUNDAMENTAL_DATA` | tiingo | ok |
| Firm fundamentals (fallback) | `https://www.alphavantage.co/query` | `FUNDAMENTAL_DATA` | alpha_vantage | ok |
| Institutional holdings (cross-holding proxy) | `moomoo://get_shareholders_institutional` | `INSTITUTION_DATA` | moomoo | gateway |
| Short interest (crowding / fragility proxy) | `moomoo://get_short_interest` | `SHORT_INTEREST` | moomoo | gateway |
| Market breadth (broad risk-off / cascade context) | `moomoo://get_rise_fall_distribution` | `MARKET_BREADTH` | moomoo | gateway |
| News text (event-time proxy for CDS jumps) | `https://eodhd.com/api/news` | `NEWS_DATA` | eodhd | ok |
| News sentiment (regime trigger) | `https://eodhd.com/api/sentiments` | `NEWS_SENTIMENT` | eodhd | ok |
| Event-probability overlay | `https://gamma-api.polymarket.com/markets` | `PREDICTION_MARKETS` | polymarket | ok |
| **CDS spreads** (Hawkes event definition, credit-tail) | — | — | — | **gap** |
| **Interbank bilateral exposures + Tier-1 equity** (DebtRank, FSRI⁺) | — | — | — | **gap** (only bank-level balance sheets via `FUNDAMENTAL_DATA`; no bilateral matrix) |
| **Firm–bank loan register / credit registry** | — | — | — | **gap** |
| **Firm-level supply-chain links (VAT/receivables)** | — | — | — | **gap** |
| **Equity cross-holdings** (EGJ `C` matrix, Ising/QUBO) | — | — | — | **gap** |

## 4. Pitfalls, validation and measurement

- **Look-ahead in the event/threshold definition.** arXiv:2606.15755 defines an extreme jump against the firm's own *full-sample* 99th percentile, and arXiv:2604.19796 estimates correlations on the entire sample. Both must be re-expressed as expanding/rolling windows before any backtest.
- **Systematic tail deletion.** arXiv:2604.19796 filters observations with the IQR rule ($Q_1-1.5\,\mathrm{IQR}$, $Q_3+1.5\,\mathrm{IQR}$) and *then* estimates VaR/CVaR/Hill on what remains — the filter removes extreme observations, biasing tail estimates toward light tails. Never apply IQR filtering ahead of a tail estimator.
- **Hill estimator assumptions.** Consistency requires i.i.d. observations and a correctly chosen $k$. Volatility clustering and serial dependence in returns break i.i.d.; the paper's use of a Hill *plot* to pick the stable-$k$ region is the minimum safeguard, not a fix.
- **Identity/symmetry failures from simulation studies.** The Hawkes paper shows label switching and prior sensitivity when channel information is weak; coefficient inference is unreliable in small/sparse networks. Treat covariate effects as "stronger/weaker evidence," not point estimates.
- **Network measures are in-sample.** Gai–Kapadia zero large-cascade probability derives from a 30-asset, single-era sample; "below the percolation threshold" is a statement about that sample, not a structural guarantee (the authors flag absent liquidity/fire-sale feedback and static thresholds).
- **Synthetic stress overlays are not tail measures.** arXiv:2511.13384 builds its adoption/liquidity stress on synthetic agents and explicitly disclaims predictive/probabilistic status. Do not use such scenario outputs to calibrate VaR/ES.
- **DebtRank/LGD scaling caveats.** arXiv:2502.17044 notes LGD results "scale proportionally" *only while no bank fails*; once banks default the mapping breaks. The linearized DebtRank spreads shocks until default/convergence and can overstate losses.
- **Kupiec/Christoffersen.** *None of the six papers runs documented Kupiec POF or Christoffersen independence/CC tests.* arXiv:2604.19796 validates tails by Hill/CCDF fit and cascade likelihood by Monte Carlo counts; arXiv:2606.15755 by posterior HDIs and WAIC; arXiv:2502.17044 by reported EL/VaR/ES levels and a non-predictive distributional comparison. A FinRobot implementation must add these tests itself (§5.2) rather than claiming the corpus supplies them.
- **Soundness tests to require.** (i) rolling-window violation rates vs nominal $\alpha$; (ii) Christoffersen independence of exceedances (clustering check); (iii) out-of-sample Hill stability across $k$; (iv) walk-forward RST scenarios checked for the documented risk–reward asymmetry (stressed $Q_5$ more negative and inter-quantile range wider than baseline); (v) network measures recomputed under expanding windows to rule out in-sample fit.

## 5. Recommended first implementation in FinRobot

1. **Tail-risk estimator module** — historical VaR/ES (95%) plus Hill $\hat\alpha$ on a rolling window. Data: `CORE_STOCK_APIS` (eodhd primary, tiingo/twelvedata/stockdata fallbacks). Value: baseline downside numbers and a tail-weight flag per symbol. Risk: IQR/tail data hygiene (see §4). Effort **S**.
2. **Backtest harness (Kupiec POF + Christoffersen independence/CC)** — rolling out-of-sample exceedance rates against nominal $\alpha$. Data: same as (1). Value: makes (§1) usable; none of the read papers provides it, so it is the highest-leverage addition. Risk: false confidence from short windows (use several window lengths). Effort **S**.
3. **Conditional reverse stress-test generator** — Gaussian closed form $\bar r^{s}_{-1}=\mu_{-1}+\Sigma_{-1,1}\Sigma_{11}^{-1}(s-\mu_1)$ with Student-$t$ local sampling. Data: `CORE_STOCK_APIS` for a multi-asset panel. Value: coherent multi-asset shock narratives instead of single-factor shocks. Risk: overfitting idiosyncratic stress episodes (prefer weekly block aggregation). Effort **M**.
4. **Equity-price cascade simulator** — the Gai–Kapadia mechanics ($E_{ij}=\rho_{ij}\sigma_iP_i$, threshold $\theta$, loss recursion) over a portfolio/universe, with 1000 Monte-Carlo shocks. Data: `CORE_STOCK_APIS` (+ `MARKET_BREADTH` for context). Value: contagion-aware stress read, cluster identification. Risk: static-threshold and in-sample-correlation caveats. Effort **M**.
5. **Firm-default financial stress index (FSRI, no interbank layer)** — $\Delta p_i=(1-h_i)(r_i-c_i)$ and $\chi_i$ from firm financials (`FUNDAMENTAL_DATA`, tiingo/alpha_vantage), aggregating bank-equity exposure by firm. Value: single-name → system loss ranking. Risk: **interbank amplification is a gap** (needs bilateral exposures); report FSRI only, and label FSRI⁺ as unavailable. Effort **M**.
6. **Multiplex Hawkes systemic-risk monitor — gated** — the full multiprocess inference requires CDS spreads (a **gap**). Interim proxy: build extreme events from `NEWS_DATA`/`NEWS_SENTIMENT` or large intraday moves (`TECHNICAL_INDICATORS` kline), which changes the event definition. Value: hub identification and channel decomposition if the proxy is accepted. Risk: proxy validity; label switching and MCMC cost. Effort **L**.
7. **Do not port** the interbank DebtRank/FSRI⁺, EGJ cross-holding QUBO, or supply-chain two-layer models until bilateral interbank, cross-holding, or firm-supply-chain data are available — all are **gaps** with no current provider. Effort **n/a**.

## Appendix — papers read

| arXiv id | title | year |
|---|---|---|
| 2609.17415v1 | Financial Contagion Networks as Annealing-Ready Ising Systems: Cascades, Bailout Optimization, and Susceptibility | 2026 |
| 2606.15755v1 | A Multiplex Network Hawkes Model for Systemic Risk Measurement | 2026 |
| 2606.09274v1 | Reverse Stress Testing for Multivariate Scenarios: A Conditional Framework for Stressed Time Series | 2026 |
| 2604.19796v1 | Systemic Risk and Default Cascades in Global Equity Markets: A Network and Tail-Risk Approach Based on the Gai Kapadia Framework | 2026 |
| 2511.13384v4 | CBDC Stress Test in a Dual-Currency Setting | 2025 |
| 2502.17044v1 | A data-driven econo-financial stress-testing framework to estimate the effect of supply chain networks on financial systemic risk | 2025 |
