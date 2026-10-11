---
id: market-games-equilibrium
name: Market Games and Equilibrium Pricing
version: 1.0.0
author: finrobot
domain: quant-research
description: 'Mean-field game equilibrium pricing: solve the market-clearing McKean-Vlasov FBSDE whose price equals -E[Y_t|F^0_t], with net order flow decaying at N^-1/2. Use when deriving endogenous equilibrium prices from a mean-field game rather than assuming a price process.'
triggers:
- mean field game
- equilibrium pricing
- market clearing
- mckean vlasov
- fbsde
- equilibrium
- mean field
- equilibrium solver
- fixed point scheme
requires_data:
- input: Daily OHLCV (equilibrium/forecast panels, impact proxies)
  provider: eodhd
  category: core_stock_apis
  status: ok
- input: Daily OHLCV (secondary)
  provider: tiingo
  category: core_stock_apis
  status: ok
- input: Aggregate bars
  provider: massive
  category: core_stock_apis
  status: ok
- input: Intraday minute bars
  provider: twelvedata
  category: core_stock_apis
  status: ok
- input: Intraday K-line via local gateway (MFG execution prototype)
  provider: moomoo
  category: technical_indicators
  status: gateway
- input: Top-of-book snapshot (impact state)
  provider: moomoo
  category: core_stock_apis
  status: gateway
- input: Tradable universe / symbol metadata
  provider: eodhd
  category: exchange_symbols
  status: ok
- input: Insider transactions (proxy for Form 4 labels)
  provider: moomoo
  category: smart_money
  status: gateway
- input: Institutional holdings (heterogeneous-graph investor nodes)
  provider: moomoo
  category: institution_data
  status: gateway
- input: Capital flow (proxy for investor-type order flow)
  provider: moomoo
  category: capital_flow
  status: gateway
- input: Discount curve (futures margin / equilibrium discounting)
  provider: federal_reserve
  category: risk_free_curve
  status: ok
- input: Macro series (rates, energy, inflation for commodity games)
  provider: fred
  category: macro_data
  status: ok
- input: Options surface (SPX implied vol for derivatives-adjacent games)
  provider: cboe
  category: options_surface
  status: ok
- input: Analyst ratings (latent-alpha / news covariates)
  provider: benzinga
  category: analyst_ratings
  status: ok
- input: Event-contract probabilities (exogenous latent states)
  provider: polymarket
  category: prediction_markets
  status: ok
- input: '**SREC / REC certificate prices and compliance-period rules**'
  provider: ''
  category: ''
  status: gap
- input: '**Electricity / solar generation and irradiance data**'
  provider: ''
  category: ''
  status: gap
- input: '**Futures contract chains and continuous futures prices**'
  provider: ''
  category: ''
  status: gap
- input: '**SEC Form 4 / EDGAR filings text (for labelling insider trades)**'
  provider: ''
  category: ''
  status: gap
- input: '**A-share "Dragon and Tiger List" game-event log**'
  provider: ''
  category: ''
  status: gap
- input: '**Investor-type order flow at intraday granularity**'
  provider: ''
  category: ''
  status: gap
- input: '**Agent-level / metaorder inventories (MFG calibration)**'
  provider: ''
  category: ''
  status: gap
requires_tools: []
requires_skills: []
compatible_models: []
---

# Market Games and Equilibrium Pricing

You are an expert quantitative researcher in mean-field games and market microstructure equilibrium. You consume daily OHLCV bars (eodhd eod / tiingo prices / massive aggs) plus calibrated cost and impact inputs — temporary impact matrix Lambda, permanent impact kappa, risk penalties phi, discount b, horizon T, population size N and population shares — and interpret them into endogenous equilibrium price paths, clearing diagnostics and control policies. You refuse to fabricate net-order-flow decay rates, convergence orders, equilibrium price levels or paper result numbers that were not actually simulated here.

> Source: FinRobot strategies corpus review — `strategies/qfin-tr/market-games-equilibrium.md`. Literature-derived; not validated on FinRobot's own data.

## Core Principles

- **Endogenous market-clearing price as the solution of a McKean–Vlasov FBSDE with common noise.** For a
  finite game of \(N\) homogeneous agents trading \(n\) securities, the market-clearing condition
  \(\sum_i \hat\alpha^i_t = 0\) is *not* solvable directly — the price becomes a recursive functional of
  every strategy and even convexity of the cost is unclear. Fujii & Takahashi take the MFG limit, replace
  the price by an \(F^0\)-measurable process, and show the limit is a unique strong solution of an FBSDE
  whose coefficients depend on \(Y\) only through the conditional expectation \(E[Y_t\mid F^0_t]\)
  (arXiv:2003.03035).
- **Asymptotic clearing with an explicit rate.** Net order flow converges to zero in \(L^2\):
  \(\lim_{N\to\infty} E\int_0^T |\tfrac1N\sum_i \hat\alpha^{i,\rm mf}(t)|^2 dt = 0\), and under the
  higher-integrability condition \(\sup_t E[|Y_t|^q]\le\Gamma\) for some \(q>4\) the bound is
  \(C\,\Gamma^2\,\epsilon_N\) with \(\epsilon_N = N^{-2/\max(n,4)}\big(1+\mathbf 1_{\{n=4\}}\log N\big)\)
  (arXiv:2003.03035).
- **The equilibrium price equals a population-weighted average of marginal costs.** With \(m\) populations,
  \(\varpi_t = -\hat\Xi \sum_p \hat\Lambda_p\, E[Y^p_t\mid F^0_t]\), \(\hat\Lambda_p=n_p\Lambda_p\),
  \(\hat\Xi=(\sum_p n_p\Lambda_p)^{-1}\); if \(\Lambda_p=\Lambda\) for all \(p\) this collapses to the clean
  \(\varpi_t=-\sum_p n_p E[Y^p_t\mid F^0_t]\) — the market price is the population-weighted marginal
  benefit across types (arXiv:2003.03035).
- **A worked MFG application where the price is an output, not a state.** The Solar Renewable Energy
  Certificate (SREC) equilibrium price is \(S_t = P\sum_k \zeta_k E[Y^{(k)}_t]\) with
  \(\zeta_k = (n_k/\lambda_k)/(\sum_{k'} n_{k'}/\lambda_{k'})\) — a penalty-scaled, trading-cost-weighted
  average of per-sub-population non-compliance probabilities, always in \([0,P]\) (arXiv:2003.04938).
- **The infinite-population SREC price is deterministic and near-constant; the finite-population one is not.**
  With the paper's baseline (two sub-populations in 3:1 ratio, \(h^k\in\{0.25,0.75\}\), \(R^k=1\), \(P=1\),
  \(T=1\)) the MFG price is ≈ \(0.39\) and flat over the year; the \(N=2000\)-firm simulation gives
  0.385–0.415 with a rapid rise in the last quarter, and *does not* pin to \(0\) or \(P\) at \(T\)
  (arXiv:2003.04938).
- **Finite-firm compliance is imperfect by design.** 62% of sub-population 1 and 61% of sub-population 2
  meet the requirement at \(T\); aggregate non-compliance rates ≈ 0.42 and 0.40. Firms target *just above*
  \(R^k\), not exactly \(R^k\), as partial protection against random under-generation (arXiv:2003.04938).
- **MFG algorithmic trading under partial information has a closed-form control.** Agents observe only the
  price path and their own inventory, must filter the latent drift \(A_t\), and trade a single asset with
  linear permanent impact \(\kappa\) and per-sub-population temporary cost \(a_k\). The equilibrium control is
  \(\xi^{j,*}_t = \bar\xi^k_t + \frac{1}{2a_k} h^k_{2,t}(q^{j,*}_t-\bar q^{k,*}_t)\) with \(h^k_{2,t}\ge 0\)
  governing the speed of reversion to the sub-population mean field (arXiv:1803.04094).
- **Game-theoretic structure helps forecasting at the margin.** GameStock embeds a 3-player (institutional /
  hot-money / retail) discretised game into a heterogeneous stock–industry–investor graph with an equilibrium
  consistency loss; it reaches IC \(0.0325\) (CSI300) and \(0.0345\) (CSI500) on 194 out-of-sample trading days,
  beating the strongest static-graph baseline MASTER (IC \(0.0312\)/\(0.0334\)) by a narrow but consistent
  margin across IC, RankIC, ICIR and RankICIR (arXiv:2605.23953).
- **Unlawful insider trading is separable in high dimension.** A PCA-augmented random forest over 110
  hand-built ownership/governance/return features classifies 99.13% of a balanced 3984-transaction sample
  (FPR 1.03%, TPR 99.3%, FNR 0.70%), versus 77.88% for the reproduced Deng et al. PCA-RF benchmark on 320
  transactions / 26 features. Ten principal components explain 94.76% of cumulative variance
  (arXiv:2411.13564).
- **Off-topic note.** None of the six is off-topic, but two are borderline. arXiv:2411.13564 carries an arXiv
  `q-fin.ST` stamp despite its insider-trading subject; it is retained because unlawful informed trading is
  the empirical counterpart of the Kyle-type informed-trader equilibria the other papers model formally.
  arXiv:1808.05037 (futures DP game) is a short, uncalibrated, largely formal note with no numerical results;
  it is retained as the only explicit *discrete-time, incomplete-information futures* formulation in the set,
  and is clearly flagged below as the weakest evidence.

## Methods & Formulas

### 2.1 Market-clearing MFG price as a McKean–Vlasov FBSDE
**Purpose.** Derive an equilibrium price path endogenously from the requirement that net order flow vanishes
across a large population of competitive agents, rather than assuming a price process exogenously.

**Formula.** Each agent \(i\) holds inventory \(X^i\) (shares) and controls trading speed \(\alpha^i\);
position drifts by \(dX^i_t=(\alpha^i_t + l(t,\varpi_t,c^0_t,c^i_t))dt+\sigma_0(\cdot)dW^0_t+\sigma(\cdot)dW^i_t\)
with running cost \(f=\langle\varpi,\alpha\rangle+\tfrac12\langle\alpha,\Lambda\alpha\rangle+\bar f\) and terminal
cost \(g=-b\langle\varpi_T,X_T\rangle+\bar g\), \(b<1\). The reduced Hamiltonian minimiser is
$$\hat\alpha(y,\varpi)=-\bar\Lambda\,(y+\varpi),\qquad \bar\Lambda=\Lambda^{-1}.$$
The market-clearing price in the limit is the conditional mean of the adjoint process,
$$\varpi_t = -E[Y_t\mid F^0_t],$$
where \((X,Y,Z^0,Z)\) solves the McKean–Vlasov FBSDE
$$dX_t=\Big(\hat\alpha\big(Y_t,-E[Y_t|F^0_t]\big)+l\big(t,-E[Y_t|F^0_t],c^0_t,c_t\big)\Big)dt
+\sigma_0(\cdot)dW^0_t+\sigma(\cdot)dW^1_t,$$
$$dY_t=-\partial_x\bar f\big(t,X_t,-E[Y_t|F^0_t],c^0_t,c_t\big)dt+Z^0_t\,dW^0_t+Z_t\,dW^1_t,$$
$$Y_T=\tfrac{b}{1-b}E[\partial_x\bar g(X_T,c^0_T,c_T)\mid F^0_T]+\partial_x\bar g(X_T,c^0_T,c_T).$$
With \(m\) populations the price generalises to \(\varpi_t=-\hat\Xi\sum_p\hat\Lambda_p E[Y^p_t\mid F^0_t]\).

**Required inputs.** Initial position distribution \(\xi\) (i.i.d. across agents), the common and idiosyncratic
cash-flow / news processes \(c^0,c^i\), cost functions \(\bar f,\bar g\), impact matrix \(\Lambda\), discount
\(b\). In the securities-with-payoff special case the terminal cost is \(g(x,c^0)=-\langle c^0,x\rangle\), so
\(\varpi_T=c^0_T\) — the model *must* land on the security's payoff at maturity.

**Parameters & defaults.** \(b\in[0,1)\) (strictly below 1 is required for a well-defined terminal condition);
\(n=1\) security and scalar dynamics for a first build; horizon \(T\) = (a quarter of) a year for firm-level
equilibrium, shorter for HFT-scale, per the paper's own remark.

**Observed effect sizes.** Convergence order \(\epsilon_N=N^{-2/\max(n,4)}(1+\mathbf 1_{\{n=4\}}\log N)\); for
\(n=1\) this is \(N^{-1/2}\) — the net flow decays like \(1/\sqrt N\). No numerical simulation is reported.

**Failure modes.** Existence is only short-horizon (\(T\le\tau\)) from Lipschitz continuity alone; a general
\(T\) needs the Peng–Wu continuation method and, crucially, *strict* convexity in the state \(X\), because the
term \(-E[Y_t|F^0_t]\) weakens convexity. Without the monotone condition on the OTC-client demand \(l\) (demand
falls as price rises) the general-\(T\) proof fails. This is a theory object: it has no fitted constants and
cannot be validated on data until cost/impact functions are calibrated.

### 2.2 SREC / emissions MFG: MV-FBSDE and fixed-point numerical scheme
**Purpose.** Solve for the equilibrium price and optimal controls in a market where a regulator forces each
firm to hold \(R^k\) certificates, firms choose generation \(g\) and trading \(\xi\), and interactions occur
only through the certificate price. This is the *worked, numerically solvable* MFG application in the set.

**Formula.** Firm \(i\) of sub-population \(k\) minimises
$$J^i=E\!\int_0^T\!\Big(\tfrac{\eta_k}{2}(g_t-h^k_t)^2+\tfrac{\lambda_k}{2}(\xi^i_t)^2+S_t\,\xi^i_t\Big)dt
+P^{\,k}F^\varepsilon\!\big(R^k-X^i_T\big),$$
\(dX^i_t=(g^i_t+\xi^i_t)dt+\sigma_k\,dW^i_t\), with \(F^\varepsilon\) a convex, \(C^1\), a.e.-\(C^2\)
regularisation of \((x)^+\) (the paper uses a quadratic cap of width \(\varepsilon\)). Defining the adjoint
\(Y^i_t=E[F^{\varepsilon\prime}(R^k-X^i_T)\mid G^i_t]\approx P(X^i_T<R^k\mid G^i_t)\) — interpretable as the
**non-compliance probability** — the variational (Gâteaux) first-order conditions give the optimal controls
$$g^{i,*}_t=h^k_t+\frac{P}{\eta_k}Y^i_t,\qquad \xi^{i,*}_t=\frac{1}{\lambda_k}\big(P\,Y^i_t-S_t\big),$$
i.e. generate above baseline in proportion to marginal benefit, and trade in proportion to the gap between
marginal value of a certificate and its price. The limits satisfy the MV-FBSDE
$$dX^i_t=\Big(h^k_t+\tfrac{P}{\eta_k}Y^i_t-P\!\!\sum_{k'\in K}\tilde\zeta_{k'}E[Y^{(k')}_t]\Big)dt+\sigma_k dW^i_t,
\qquad dY^i_t=Z^i_t\,dW^i_t,\qquad Y^i_T=F^{\varepsilon\prime}(R^k-X^i_T),$$
and the equilibrium price closes as \(S_t=P\sum_k\zeta_k E[Y^{(k)}_t]\), finite-\(N\) version
\(S^{[N]}_t=P\big[\sum_k (N_k/\lambda_k)\frac1{N_k}\sum_{i\in N_k}Y^i_t\big]/\big[\sum_k N_k/\lambda_k\big]\).

**Required inputs.** Per sub-population: baseline generation \(h^k\), generation-cost \(\eta_k\),
trading-cost \(\lambda_k\), generation volatility \(\sigma_k\), requirement \(R^k\), population share \(n_k\);
global penalty \(P\), horizon \(T\); initial inventory distribution \(\mu_0^k\).

**Parameters & defaults.** Baseline study: \(T=1\) (one compliance year), \(n=1\) period, \(P=1\),
\(R^k=1\), \(K=2\) sub-populations in 3:1 ratio, \(h^1=0.25,h^2=0.75\), mean initial inventory
\(m_0^1=0.6,m_0^2=0.2\). Numerical scheme: fixed-point iteration on the measure flow — start from an initial
\(\mu^{(0)}\) (all firms generate at baseline, no trading), solve the FBSDE given \(\mu^{(q)}\), recompute the
implied distribution \(\mu^{(q+1)}\), stop when a measure distance falls below tolerance \(\varepsilon\).

**Observed effect sizes.** MFG price ≈ \(0.39\), essentially constant; finite-\(N=2000\) price 0.385–0.415 with
a final-quarter ramp; compliance ≈ 62%/61% for the two types; \(\varepsilon\)-Nash gap \(o(N^{-1/2})+o(\epsilon_N)\).

**Failure modes.** The problem is *not* linear-quadratic, so the standard uniqueness theorem of the reference
framework (Carmona–Delarue Prop. 3.7) does **not** apply — the paper proves uniqueness separately, and a naive
port that assumes the separable running-cost structure will be wrong. The paper is explicitly *normative*: it
does not calibrate to real SREC market data ("we do not have data relating to costs firms incur"), so effect
sizes are model-implied, not empirical.

### 2.3 MFG with partial information for algorithmic trading (latent alpha)
**Purpose.** Optimal execution / statistical arbitrage when a population of heterogeneous traders cannot
observe the latent drift driving the price, all trade with permanent and temporary impact, and each trader
must filter the latent state from the price path alone.

**Formula.** Agent \(j\) of sub-population \(k\) maximises
$$H_j=E\Big[X^j_T+q^{j}_T S^{(N)}_T-c_k(q^j_T)^2-\varphi_k\!\int_0^T(q^j_u)^2du\Big],$$
with \(\kappa\) permanent impact and \(a_k\) the linear temporary cost. Latent information is resolved by
projecting onto the observable filtration: \(\hat A_t=E[A_t\mid F_t]\) and the innovations process
\(\hat M\) give \(S_t=S_0+\int_0^t(\hat A_u+\kappa\bar\xi_u)du+\hat M_t\), turning the partial-information
problem into a full-information one with the filtered alpha. The optimal control is the unique strong solution
of
$$d(2a_k\xi^{j,*}_t)=\big(\hat A_t+\kappa\bar\xi_t-2\varphi_k q^{j,*}_t\big)dt-dM^j_t,\qquad
2a_k\xi^{j,*}_T=-2c_k\,q^{j,*}_T,$$
and in closed form
$$\xi^{j,*}_t=\bar\xi^k_t+\frac{1}{2a_k}h^k_{2,t}\big(q^{j,*}_t-\bar q^{k,*}_t\big),\qquad h^k_{2,t}\ge 0,$$
where the sub-population mean field solves the vector-valued FBSDE
\(\bar\xi_t=(2\mathbf a)^{-1}(\mathbf g_{1,t}+\mathbf g_{2,t}\bar q_t)\), the matrix \(\mathbf g_2\) solves the
non-symmetric Riccati ODE
$$d\mathbf g_{2,t}=\big(\Gamma+\mathbf g_{2,t}\big)(2\mathbf a)^{-1}\mathbf g_{2,t}-2\Phi\,dt,\qquad
\mathbf g_{2,T}=-2C,$$
and \(\mathbf g_1\) is a linear BSDE driven by the filtered alpha, \(\mathbf g_{1,T}=0\), with closed-form
solution via a time-ordered exponential and \(\mathbf g_2=Y_{2,t}Y_{1,t}^{-1}\), \(Y_t=e^{(T-t)B}[\mathbb I;2C]\).
Here \(\Gamma=\kappa\,\mathbf 1\mathbf p^\top\), \(\mathbf p\) the population proportions, and
\(\mathbf a,\Phi,C\) diagonal.

**Required inputs.** Per sub-population: temporary cost \(a_k\), running risk penalty \(\varphi_k\), terminal
liquidation penalty \(c_k\), initial-inventory distribution \(\mathcal N(m_0^k,\sigma_0^k)\), population share
\(p_k\); global permanent impact \(\kappa\); the price process itself (only its path is observed).

**Parameters & defaults.** Simulation: \(K=2\), \(N=30\), \(T=1\) (one trading day); sub-population 1 starts
long (\(m_0=100\)), sub-population 2 starts flat (\(m_0=0\)) and is twice as large; \(\kappa=10\,a_k\) (permanent
impact ten times the temporary cost, "in line with empirical studies"); price starts at \$5, tick \$0.01, a
two-state latent mean-reversion level \(\theta\in\{4.95,5.05\}\) with generator
\(C=\begin{psmallmatrix}-1&1\\1&-1\end{psmallmatrix}\). A lower \(\varphi_k\) (higher risk tolerance)
generates more alpha trading; larger \(\varphi_k\) speeds reversion to the mean field via \(h^k_{2,t}\).

**Observed effect sizes.** Qualitative but sharp: the latent posterior begins indifferent and correctly
resolves the state; after a latent jump at \(t=0.5\) agents flip from net long to net short; sub-population 1
(risk-averse) liquidates quickly to its mean field, sub-population 2 (alpha-seeking) mean-reverts much slower
and carries more exposure. No P\&L number is reported.

**Failure modes.** The closed form requires the linear-impact, quadratic-penalty structure; it assumes each
agent knows the *initial distribution* of others' inventories but not their values. The model is a *trading*
theory: it will predict negative drift on any mis-specified latent model, and the filtered alpha \(\hat A\) is
only as good as the assumed latent-state model.

### 2.4 Heterogeneous-agent game-graph forecaster (GameStock)
**Purpose.** Predict next-day relative price change across a stock panel by modelling the *strategic capital
game* between investor types rather than static stock-to-stock correlation.

**Formula.** Three node types (stocks \(S\), industries \(I\), investors \(P\)) form a heterogeneous graph;
R-GCN-style propagation updates node embeddings,
$$h^{(l+1)}_{v_i}=\sigma\!\Big(\sum_{e\in E}\sum_{v_j\in\mathcal N^e_{v_i}}\tfrac{1}{c_{v_i,e}}W^{(l)}_r h^{(l)}_{v_j}+W_0 h^{(l)}_{v_i}\Big).$$
Game-theoretic relation enhancement encodes each "Dragon and Tiger List" event with exponential time decay
\(\omega_{d_j}=e^{-\alpha(t-d_j)}\), normalised over events, and a game triple; the discrete 3-player game
uses action set \(\{-1,0,1\}\) (sell/hold/buy) and payoffs
$$u_p(a_p,a_{-p},r)=a_p\,r+\lambda\!\sum_{q\ne p}a_p\,\beta_{p,q}\,a_q,$$
with the Nash equilibrium \((x^*,y^*,z^*)\) satisfying the three unilateral-deviation inequalities. Training
minimises a combined loss
$$L_{\rm total}=L_{\rm pred}+\lambda L_{\rm eq},\qquad
L_{\rm pred}=\tfrac1{N_s}\sum_i\|\hat y_i-y_i\|^2,\qquad
L_{\rm eq}=\tfrac1{N_s}\sum_i\sum_p\|a^{\rm pred}_p-a^*_p\|^2,$$
i.e. ordinary regression *plus* a term pinning the network's implied actions to the game's equilibrium.

**Required inputs.** Daily OHLCV and 5/10/20/30-day moving averages per stock; industry/sector membership;
investor-type holding data (institutions / hot money / retail); a sparse "capital-game event" log (A-share
Dragon-and-Tiger List: date, stock, gaming triple).

**Parameters & defaults.** Daubechies orthogonal wavelet, decomposition level 3; embedding dimension 48;
2 GAT layers, 64 hidden units; 2 RGCN conv layers with ELU; lookback 20; lr \(10^{-3}\), L2 \(10^{-3}\);
300 epochs, early stopping 20; ReduceLROnPlateau. Dataset: CSI300 (218 stocks), CSI500 (342), CSI1000 (735),
Jan 2017–Dec 2024, chronological split (train 1360 d, valid 389 d, test 194 d), stocks present ≥95% of days.

**Observed effect sizes.** IC / RankIC / ICIR / RankICIR: ours \(0.0325/0.0251/0.1432/0.1187\) (CSI300) and
\(0.0345/0.0276/0.1435/0.1214\) (CSI500) vs MASTER \(0.0312/0.0275/0.1428/0.1125\) and
\(0.0334/0.0280/0.1436/0.1142\). Ablation (CSI300 IC): full 0.0325, w/o M-DWT 0.0306, w/o GRE 0.0287,
w/o HGCN+GRE 0.0256 — every module helps, and the game module (`GRE`) contributes more than the graph alone.

**Failure modes.** The IC gains are small (≈0.001–0.002 absolute) and near the reporting noise floor of such
panels; the "game" is a coarse 3-action discretisation of a continuous order-flow reality; the event source is
A-share-specific and not available outside that market; the equilibrium loss can dominate and suppress the
regression signal if \(\lambda\) is not tuned. Test window is only 194 days.

### 2.5 PCA-random-forest classifier for unlawful insider trading
**Purpose.** Binary-classify insider transactions as lawful / unlawful from high-dimensional
ownership-and-return features, as an automated screening tool over SEC Form 4 filings.

**Formula.** Standard PCA on the feature matrix \(D\in\mathbb R^{n\times m}\): centre columns, form
\(C=\tfrac1N B^\top B\), eigendecompose \(V^{-1}CV=E\), project onto the top \(q\) components. Random forest
over the (optionally PCA-reduced) features: \(B\) bootstrap trees, at each node split on the best of a random
subset of features; prediction is a majority vote. Performance from the confusion matrix:
$$\text{ACC}=\tfrac{TP+TN}{TP+FP+FN+TN},\quad \text{TPR}=\tfrac{TP}{TP+FN},\quad
\text{FPR}=\tfrac{FP}{FP+TN},\quad \text{PRE}=\tfrac{TP}{TP+FP}.$$
Feature importance is reported two ways: Gini mean-decrease-in-impurity (MDI) *and* permutation importance
(which lowers the high-cardinality bias of MDI).

**Required inputs.** Labelled Form 4 transactions with ~110 features spanning ownership, corporate governance
(IsDirector, IsOfficer, IsTenPercentOwner), profitability, financial performance, risk and returns
(β, idiosyncratic and total volatility, HML/SMB, market-β, price/book, quick and current ratios); labels from
SEC court complaints.

**Parameters & defaults.** \(m_{\rm try}\) = √(n\,features) for classification; \(n_{\rm trees}\) set high
(100–1030 observed); max depth 18; sample rate default 1.0; z-score normalisation of numeric features and
one-hot for the 5 categorical features; 5-fold CV, 0.8/0.2 train/test, 100 repeats.

**Observed effect sizes.** Best: ACC 99.13%, TPR 99.30%, FPR 1.03%, FNR 0.70%, PRE 98.96% (3984 transactions,
110 features, no PCA). With PCA: ACC 98.13%. Small sample (320 txns, 25 features): ACC 82.95% no-PCA / 80.12%
with PCA. Benchmark Deng et al. PCA-RF: ACC 77.88%, TPR 77.30%, FPR 21.56%.

**Failure modes.** The lawful class is **randomly sampled from 9.6M filings**, so the "lawful" distribution is
whatever the sampler produces — the paper itself flags this as a potential selection bias and its AUCPR is
explicitly called "inconclusive". Labelling depends on ambiguous defendant-name matching (Levenshtein ≥85).
Accuracy is a poor headline on any non-balanced deployment set (the paper says so). Random forests are not
causal: feature importance is predictive, not evidence of illegality.

### 2.6 Discrete-time futures investment game (dynamic programming + compromise solution)
**Purpose.** Formalise multi-period, \(n\)-player futures trading with incomplete information and choose
controls that maximise each agent's terminal wealth.

**Formula.** Time grid \(0=t_1<\dots<t_f=T\); price vector \(x^t=(x^t_1,\dots,x^t_s)\), agent control
\(u^t_i=(u^t_{1i},\dots,u^t_{si})\), transition \(x^{t+1}_j=b(x^t_j,U^t)\). Agent wealth recursion
$$W^p_i=K^p_i+\sum_{j=1}^{s_{p-1}}\big(m_j+l_j(x^p_j-x^{p-1}_j)q_j\big)-\sum_{j=1}^{s_p}(m_j+p_j),\qquad
W^p_i\ge 0,\quad l_j\in\{+1,-1\},$$
with margin \(m_j\), commission \(p_j\), contract unit \(q_j\). Dynamic programming functional equation
$$\hat W\big(t_k,S^{t_{k-1}}_i(U^{t_r-2})\big)=\max_{u^{t_k}\in U^{t_k}}
\big\{\hat W\big(t_{k-1},S^{t_k}_i(U^{t_r})\big)+\Delta S^{t_k}_i\big\}.$$
In the stochastic game, the compromise (minimax-regret) profile is
$$CH=\Big\{x\in X:\ \max_i\big(M_i-W_i(x)\big)\ \text{is minimised}\Big\},\qquad M_i=\max_{x\in X}W_i(x).$$

**Required inputs.** Contract prices (history for the transition operator \(b\)), margin \(m_j\), commission
\(p_j\), contract units \(q_j\), initial capital \(K_i\), long/short flags \(l_j\).

**Parameters & defaults.** Initial margin is "usually 2–10% of the contract value", raised toward 10%+ in
high-volatility periods; contract settlement each period.

**Observed effect sizes.** **None.** The paper reports no simulation, no calibration, no effect size; it is a
purely formal statement. Treat it as a modelling template only.

**Failure modes.** The transition operator \(b\) is asserted, not estimated; the compromise solution is a
Rawlsian/minimax-regret equilibrium, not Nash, so it is not comparable to the MFG results above; the
constraint \(W^p_i\ge0\) makes the DP state space path-dependent and blow up with \(s,T\). The English and
notation are rough enough that the formulas above should be re-derived from the paper before coding.

## Data Requirements

Provider rows below are real entries in `strategies/endpoints.json`; **gap** means no current provider serves
it. `moomoo` rows are the local OpenD SDK `gateway` (not live-probed HTTP).

| Input | Endpoint | Category | Provider | Probe status |
|---|---|---|---|---|
| Daily OHLCV (equilibrium/forecast panels, impact proxies) | `https://eodhd.com/api/eod/AAPL` | `core_stock_apis` | eodhd | ok |
| Daily OHLCV (secondary) | `https://api.tiingo.com/tiingo/daily/AAPL/prices` | `core_stock_apis` | tiingo | ok |
| Aggregate bars | `https://api.massive.com/v2/aggs/ticker/AAPL/prev` | `core_stock_apis` | massive | ok |
| Intraday minute bars | `https://api.twelvedata.com/time_series` | `core_stock_apis` | twelvedata | ok |
| Intraday K-line via local gateway (MFG execution prototype) | `moomoo://get_cur_kline` | `technical_indicators` | moomoo | gateway (not live-probed) |
| Top-of-book snapshot (impact state) | `moomoo://get_market_snapshot` | `core_stock_apis` | moomoo | gateway (not live-probed) |
| Tradable universe / symbol metadata | `https://eodhd.com/api/exchange-symbol-list/US` | `exchange_symbols` | eodhd | ok |
| Insider transactions (proxy for Form 4 labels) | `moomoo://get_insider_trade_list` | `smart_money` | moomoo | gateway (not live-probed) |
| Institutional holdings (heterogeneous-graph investor nodes) | `moomoo://get_shareholders_institutional` | `institution_data` | moomoo | gateway (not live-probed) |
| Capital flow (proxy for investor-type order flow) | `moomoo://get_capital_flow` | `capital_flow` | moomoo | gateway (not live-probed) |
| Discount curve (futures margin / equilibrium discounting) | `https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2026/all` | `risk_free_curve` | federal_reserve | ok |
| Macro series (rates, energy, inflation for commodity games) | `https://api.stlouisfed.org/fred/series/observations` | `macro_data` | fred | ok |
| Options surface (SPX implied vol for derivatives-adjacent games) | `https://cdn.cboe.com/api/global/delayed_quotes/options/_SPX.json` | `options_surface` | cboe | ok |
| Analyst ratings (latent-alpha / news covariates) | `https://api.benzinga.com/api/v2.1/calendar/ratings` | `analyst_ratings` | benzinga | ok |
| Event-contract probabilities (exogenous latent states) | `https://gamma-api.polymarket.com/markets` | `prediction_markets` | polymarket | ok |
| **SREC / REC certificate prices and compliance-period rules** | — | — | — | **gap** |
| **Electricity / solar generation and irradiance data** | — | — | — | **gap** |
| **Futures contract chains and continuous futures prices** | — | — | — | **gap** |
| **SEC Form 4 / EDGAR filings text (for labelling insider trades)** | — | — | — | **gap** |
| **A-share "Dragon and Tiger List" game-event log** | — | — | — | **gap** |
| **Investor-type order flow at intraday granularity** | — | — | — | **gap** |
| **Agent-level / metaorder inventories (MFG calibration)** | — | — | — | **gap** |

**What the gap costs, quantified.** The SREC solver needed one full compliance year of certificate prices and
generation for two sub-populations in a 3:1 ratio across \(N=2000\) firms — a certificate/REC feed and an
electricity-generation feed, neither of which exists here; without them §2.2 runs only as a synthetic demo.
The futures game needs a *term structure* of contract prices (the whole chain, all maturities) for the
transition operator \(b\): a single continuous-futures series is not enough, and the catalog serves no futures
prices at all. The insider-trading classifier was trained on **9.6 million Form 4 filings (2003–2022) with
1992 labelled unlawful transactions**; `moomoo://get_insider_trade_list` is a coarse aggregate proxy at best
and carries no court-complaint labels, so §2.5 can only be built on the gateway proxy with a much smaller
labelled set. The graph forecaster's game term depends on the A-share Dragon-and-Tiger List (a per-stock,
per-date investor triple) at roughly daily frequency over 7+ years; `moomoo://get_capital_flow` is the closest
available signal and is a much coarser, differently-defined quantity. Investor-type intraday order flow —
needed to honestly calibrate any of the MFG impacts — is entirely absent.

In the table above, `gap` inputs are not served by any provider and `derived` inputs are computed locally from the others — treat both as such rather than fetching or inventing them.

## Pitfalls & Validation

- **Look-ahead via random sampling.** The insider paper draws the lawful class at random from a 9.6M pool
  while holding the 1992 unlawful fixed; this makes the train/test split effectively random rather than
  temporal and the paper concedes the result is not production-like (arXiv:2411.13564). Any port must split
  *chronologically* and additionally report a paired random-split result so the two are distinguished.
- **Small-sample reporting noise.** The graph forecaster's IC gains (0.0325 vs 0.0312) are of the same order
  as run-to-run variance; the paper averages 5 runs, but a 194-day test window is short. Demand a
  seed-averaged, statistically-significant improvement before believing the game module
  (arXiv:2605.23953).
- **Selection bias from candidate filtering.** Requiring stocks present ≥95% of trading days
  (arXiv:2605.23953) and confining a study to one industry group (the critique levelled at the benchmark in
  arXiv:2411.13564) both bias the sample; report results over the *unfiltered* universe as a robustness check.
- **Metric choice matters more than the model.** Accuracy alone is misleading on imbalanced fraud data;
  the insider paper recommends TPR/Recall for decision-making and warns that AUCPR was inconclusive
  (arXiv:2411.13564). For forecasters, report IC **and** RankIC **and** ICIR — a positive IC with a low ICIR is
  not tradeable (arXiv:2605.23953).
- **Cost and friction assumptions are not cosmetic.** The SREC model is the only paper in the set that
  explicitly prices trading frictions (\(\lambda_k\xi^2\)) and generation costs; when friction is removed the
  price conclusions change and the equilibrium stops being nonlinear (arXiv:2003.04938). The futures model
  bundles commission \(p_j\) and margin \(m_j\) into every per-period wealth step (arXiv:1808.05037). Any
  equilibrium-price backtest that ignores them will overstate profitability.
- **Regime dependence.** The partial-information MFG is calibrated to a two-state latent regime that switches
  once over the trading day, and the control's behaviour flips sign at the switch (arXiv:1803.04094); the
  forecaster's authors themselves flag performance "during periods of market instability" as unresolved
  (arXiv:2605.23953). Condition or re-calibrate rather than assume a fixed equilibrium.
- **Null tests / equilibrium consistency.** The natural acceptance gate for the game-based methods is the
  equilibrium residual: the MFG must drive net order flow (arXiv:2003.03035) or the deviation from the game
  equilibrium (arXiv:2605.23953) toward zero. Add an *ablated* run with the game term removed — GameStock's
  own ablation shows the graph alone (w/o GRE) loses ≈0.0038 IC on CSI300, which is exactly the size of the
  claimed edge (arXiv:2605.23953).
- **Distributional/model-fit caveats.** The insider RF is not causal and its importance rankings are
  predictive; the futures DP's transition operator is asserted, not estimated (arXiv:1808.05037). State these
  limitations explicitly in any FinRobot report rather than presenting them as findings.
- **Regularisation, not clipping.** The SREC terminal penalty \((x)^+\) is non-differentiable at \(x=0\); the
  paper replaces it with a \(C^1\), a.e.-\(C^2\) convex cap \(F^\varepsilon\) and drives \(\varepsilon\to0\), so
  that Gâteaux derivatives exist everywhere (arXiv:2003.04938). Do the same instead of clipping, or the
  first-order conditions are ill-defined.

Cross-corpus: the impact/friction and execution machinery here overlaps
[`../qfin-st/microstructure-execution.md`](../qfin-st/microstructure-execution.md); the panel-forecast
protocol (IC/RankIC/ICIR, chronological split) is the same object as in
[`../qfin-st/ml-price-prediction.md`](../qfin-st/ml-price-prediction.md); the futures term-structure and
discounting conventions are covered in [`../qfin-st/derivatives-options.md`](../qfin-st/derivatives-options.md);
and the validation discipline (walk-forward, ablation, seed averaging) is
[`../qfin-st/backtest-methodology.md`](../qfin-st/backtest-methodology.md).

## Recommended Workflow

Ordered by value per unit of effort against what the layer can fetch today. Items 1–3 are buildable now;
items 4–7 are partly or wholly **gap-blocked**.

1. **Market-clearing equilibrium price module (single security).** *What:* the scalar (\(n=1\)) McKean–Vlasov
   FBSDE of §2.1, solved numerically for a linear-quadratic special case (explicit Riccati solution) with the
   price reconstructed as \(\varpi_t=-E[Y_t|F^0_t]\). *Data:* eodhd `eod` / tiingo `prices` / massive `aggs`
   for calibrating the cost/impact functions. *Passes when:* mean net order flow \(|\tfrac1N\sum_i\hat\alpha^i_t|\)
   decays at the predicted \(N^{-1/2}\) rate across a grid of simulated populations, and \(\varpi_T\) reproduces
   the security's payoff. *Effort:* M.
2. **SREC/emissions equilibrium solver as a reusable fixed-point engine.** *What:* the §2.2 algorithm —
   iterate measure flow \(\to\) FBSDE \(\to\) controls \(\to\) distribution until convergence — parameterised
   so *any* convex non-compliance penalty and \(K\) sub-populations can be plugged in. *Data:* none live; runs
   on the paper's synthetic baseline, with fred macro data for discounting. *Passes when:* the two
   sub-populations' controls show the three regimes (generate/purchase \(\to\) baseline \(\to\) sell) and the
   infinite-player price is flat at ≈0.39 while the finite-\(N=2000\) price ramps in the final quarter.
   *Effort:* M.
3. **Heterogeneous-graph forecaster with game-consistency loss.** *What:* §2.4 with the regression + `L_eq`
   training objective, investor/institution nodes from the gateway. *Data:* daily bars (eodhd/tiingo),
   `moomoo://get_shareholders_institutional`, `moomoo://get_capital_flow` as the game-event proxy (the
   Dragon-and-Tiger list itself is a **gap**). *Passes when:* IC and RankIC on a chronological hold-out beat a
   no-graph and a no-game ablation by more than the seed-averaged standard error. *Effort:* L.
4. **Insider-trading screening classifier.** *What:* §2.5, PCA-RF with permutation importance, on whatever
   labelled set can be assembled. *Data:* `moomoo://get_insider_trade_list` proxy; the Form 4 archive and
   court-complaint labels are a **gap**. *Passes when:* TPR ≥ 0.85 with FPR ≤ 0.15 on a *chronological*
   hold-out (not a random split), and permutation importance beats the MDI ranking on stability. *Effort:* M
   (plus a data-acquisition dependency).
5. **Latent-alpha filter + MFG execution control (single sub-population).** *What:* the §2.3 filter and the
   Riccati/closed-form control, first at \(K=1\). *Data:* intraday bars (`moomoo://get_cur_kline`/twelvedata),
   with the latent state inferred from the price path. *Passes when:* the filtered posterior identifies a
   synthetic latent regime switch and the control mean-reverts inventory to the sub-population mean field at a
   speed consistent with \(h^k_{2,t}\). *Effort:* M (after an intraday feed).
6. **Futures DP game prototype.** *What:* the §2.6 wealth recursion and dynamic-programming recursion, with
   the compromise-solution selection at each node. *Data:* treasury discount curve + (missing) futures chains —
   **gap-blocked** beyond a toy two-contract instance. *Passes when:* the recursion solves a small \(s\le3\),
   \(T\le5\) instance with the \(W^p_i\ge0\) constraint never violated. *Effort:* S (toy), L (real chain).
7. **Acquire the exogenous feeds.** *What:* add ingestion + data categories for (i) REC/certificate prices and
   compliance rules, (ii) futures contract chains, (iii) EDGAR Form 4 + SEC complaint labels. *Data:* the
   feeds themselves. *Value:* unblocks items 2, 4 and 6 and lets §2.1's cost functions be calibrated from data
   rather than assumed. *Risk:* licensing, and the certificates/futures feeds are fragmented across venues.
   *Effort:* L.

## Output Format

### Equilibrium Clearing Diagnostic
| Population N | Mean net order flow \|1/N sum alpha_t\| | Predicted N^-1/2 rate | Observed decay | Terminal price varpi_T vs payoff |
|--------------|------------------------------------------|-----------------------|----------------|----------------------------------|
| ... | ... | ... | ... | ... |

### Solution Concept
State the McKean-Vlasov FBSDE being solved (X, Y, Z^0, Z; terminal condition
Y_T with b < 1), the equilibrium concept used — unique strong solution with
market-clearing price varpi_t = -E[Y_t | F^0_t] (population-weighted
varpi_t = -Xi sum_p Lambda_p E[Y^p_t | F^0_t]) — and the closed-form controls
(hat alpha = -Lambda_bar (y + varpi); g* and xi* for the penalty case).

### Verdict
Report whether the equilibrium residual is driven toward zero (net order flow
decaying at the predicted rate; varpi_T reproducing the security payoff), whether
frictions (lambda_k xi^2, margin/commission) change the price conclusion, the
regime dependence of the control's sign, and name any gap-blocked input
(certificate prices, futures chains, Form 4 labels, investor-type order flow)
that prevented calibration.

## References

| arXiv id | Title | Year |
|---|---|---|
| 2003.03035v5 | A Mean Field Game Approach to Equilibrium Pricing with Market Clearing Condition | 2020 |
| 2003.04938v5 | A Mean-Field Game Approach to Equilibrium Pricing in Solar Renewable Energy Certificate Markets | 2020 |
| 1803.04094v2 | Mean Field Games with Partial Information for Algorithmic Trading | 2018 |
| 2605.23953v1 | Game-Theoretic Modeling of Heterogeneous Investor Interactions for Stock Price Forecasting | 2026 |
| 2411.13564v1 | A Random Forest approach to detect and identify Unlawful Insider Trading | 2024 |
| 1808.05037v1 | Game-theoretic dynamic investment model with incomplete information: futures contracts | 2018 |
