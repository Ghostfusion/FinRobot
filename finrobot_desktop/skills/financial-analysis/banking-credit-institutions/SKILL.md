---
id: banking-credit-institutions
name: Bank and Credit-Institution Monitoring
version: 1.0.0
author: finrobot
domain: financial-analysis
description: 'Bank and credit-institution monitoring: fit a two-state credit-stress regime monitor to served aggregate consumer-credit series (delinquencies, charge-offs, credit growth), plus a DuPont ROE/ROA driver screen. Use when screening bank profitability or tracking bank/consumer credit stress.'
triggers:
- bank profitability
- credit stress
- dupont
- roa
- roe
- delinquency
- charge-offs
- consumer credit
- net interest margin
- bank capital
- loan loss
requires_data:
- input: Bank income statement / balance sheet line items (generic statements)
  provider: tiingo
  category: fundamental_data
  status: ok
- input: Bank fundamentals (secondary source, same category)
  provider: alpha_vantage
  category: fundamental_data
  status: ok
- input: Listed-bank daily OHLCV (factor loadings, break detector, betas)
  provider: eodhd
  category: core_stock_apis
  status: ok
- input: Listed-bank daily prices (secondary)
  provider: tiingo
  category: core_stock_apis
  status: ok
- input: Intraday bars for event-window studies
  provider: twelvedata
  category: core_stock_apis
  status: ok
- input: Previous-session aggregate bars
  provider: massive
  category: core_stock_apis
  status: ok
- input: Bank equity instrument universe / listing metadata
  provider: eodhd
  category: exchange_symbols
  status: ok
- input: Aggregate consumer-credit stress series (delinquency, charge-offs, credit growth)
  provider: fred
  category: macro_data
  status: ok
- input: Risk-free curve (discounting, Net Interest Margin benchmark)
  provider: federal_reserve
  category: risk_free_curve
  status: ok
- input: Bank dividends / capital actions
  provider: eodhd
  category: corporate_actions
  status: ok
- input: Bank dividend calendar (event studies)
  provider: benzinga
  category: corporate_actions
  status: ok
- input: Bank news flow (contextual)
  provider: eodhd
  category: news_data
  status: ok
- input: Bank news sentiment score
  provider: eodhd
  category: news_sentiment
  status: ok
- input: Bank analyst ratings
  provider: benzinga
  category: analyst_ratings
  status: ok
- input: Bank analyst rating summary
  provider: moomoo
  category: analyst_ratings
  status: gateway
- input: Institutional / shareholder structure
  provider: moomoo
  category: institution_data
  status: gateway
- input: Revenue segment breakdown (fee vs net-interest mix)
  provider: moomoo
  category: revenue_breakdown
  status: gateway
- input: Economic calendar (central-bank/rate events)
  provider: moomoo
  category: economic_calendar
  status: gateway
- input: Rate-path expectations (policy surprises)
  provider: moomoo
  category: fed_watch
  status: gateway
- input: '**Bank-level regulatory capital (Tier 1 / Tier 2 ratios, RWA, leverage ratio)**'
  provider: ''
  category: ''
  status: gap
- input: '**Bank-level deposits, funding mix, Net Interest Margin components**'
  provider: ''
  category: ''
  status: gap
- input: '**Bank-level loan-loss provisions, NPLs, charge-offs by loan type**'
  provider: ''
  category: ''
  status: gap
- input: '**Mutual-fund / ETF NAV series and holdings (the style-drift panel)**'
  provider: ''
  category: ''
  status: gap
- input: '**Consumer transaction-level / open-banking records (borrower-week panel)**'
  provider: ''
  category: ''
  status: gap
- input: '**Payday / consumer-lender loan counts and originations**'
  provider: ''
  category: ''
  status: gap
- input: '**Single-name credit spreads / CDS / equity-default-swap quotes**'
  provider: ''
  category: ''
  status: gap
- input: '**Interbank ledger flows and central-bank reserve balances by institution**'
  provider: ''
  category: ''
  status: gap
- input: '**API inventories and fintech partnership/deal records (targets, dates, amounts)**'
  provider: ''
  category: ''
  status: gap
requires_tools: []
requires_skills: []
compatible_models: []
---

# Bank and Credit-Institution Monitoring

You are an expert bank and credit-institution analyst specializing in credit-stress regime monitoring and profitability attribution. You consume the served aggregate consumer-credit macro series (FRED delinquencies, charge-offs, credit growth), generic bank fundamental statements, and listed-bank price bars from the available endpoints, and you interpret them into regime-persistence and DuPont driver tables — never fabricating bank balance-sheet line items, regulatory capital ratios, borrower-level panels, or paper effect sizes that no endpoint actually serves. The monitor rests on the single served macro-data (FRED) row; if that endpoint is out, the regime procedure is inert and this skill degrades to a descriptive diagnostic on whatever statements resolve.

> Source: FinRobot strategies corpus review — `strategies/qfin-gn/banking-credit-institutions.md`. Literature-derived; not validated on FinRobot's own data.

## Core Principles

- **A two-state HMM separates occasional from persistent consumer borrowing, and the separation is
  almost entirely a level shift, not a slope change** (arXiv:2306.01749v2). Data: an Open Banking
  borrower–week panel of $1{,}815$ UK payday-loan customers, 2017–2018, built from $126{,}188$
  transactions across ~70 institutions (~80 weeks and ~8 loans per borrower). State intercepts
  $\alpha_1\approx-3.62$ and $\alpha_2\approx-0.99$ give a **~14-fold** step in baseline intensity
  ($0.03\to0.37$ loans/week). Persistence is extreme ($P_{11}\approx0.992$, $P_{22}\approx0.969$;
  $P_{12}\approx0.008$, $P_{21}\approx0.031$), giving expected spells of $\approx125$ and $\approx32$
  weeks and stationary state-2 probability $\pi_2=P_{12}/(P_{12}+P_{21})\approx0.21$. Predictive gains
  are modest but consistent (test MAE $0.2227$ Poisson-HMM vs $0.2313$ GAMM, $0.2287$ GLM; NB2 tied),
  and regime occupancy matches the GAMM random intercept (Spearman $\rho=0.83$).
- **The policy-relevant output of that HMM is a sustained-exposure counter, not a probability of
  default** (arXiv:2306.01749v2). Defining a *trigger event* as the first occurrence of $H=12$
  consecutive weeks in the high-intensity state, **36.4%** of borrowers trigger at least once, and
  post-threshold state-2 weeks average **17.8%** of all borrower–week observations. Under a Gaussian
  mixture fitted to the GAMM random intercepts, 81.5% of trigger-flagged borrowers fall in the
  highest-intercept component vs 3.8% of non-flagged.
- **Bank profitability ratings are metric-dependent, and a six-observation regression over three
  regressors is uninformative** (arXiv:2005.08759v1). Data: six full-fledged Bangladeshi Islamic banks
  (of seven), 2008–2012 five-year averages. ROA ranges $2.24\%$ (EXIMBL) to $-7.83\%$ (ICBIBL); ROE
  $21.31\%$ (SJIBL) to $-26.42\%$ (ICBIBL); the equity multiplier spans $3.37$–$11.46$, so SJIBL's top
  ROE is leverage-driven while EXIMBL's top ROA is margin-driven. DuPont: ROE $=$ ROA $\times$ EM and
  ROA $=$ NPM $\times$ AU, with NPM $22.15\%$–$36.12\%$ and AU $0.053$–$0.091$. Correlations among the
  six averages: ROA–ROD $0.997$, ROA–OE $-0.980$, ROA–AU $-0.949$ ($p\le0.004$). The regression of
  ROA on OE, AU, ROD reports $R^2=99.9\%$, $F=931.9$ on $(3,2)$ df, significant only for ROD
  ($t=10.12$ vs 10% critical $t=2.92$) — a collinearity/$n=6$ artefact, **not** a model (§4).
- **Style drift is near-universal in an Indian equity-fund panel, but outright style rotation is
  rare** (arXiv:2510.19619v1). Data: funds present since 2006, daily NAV returns, Jan 2006–Jun 2023;
  benchmark-adjusted FF3 SMB/HML loadings tested for Bai–Perron structural breaks. Of $1{,}559$ style
  transitions, $9$ are rotation, **927 are drift**, $622$ strengthening/weakening. Performance by
  break count humps: 2 breaks $7.89\%$ excess return (Sharpe $0.59$, FF3 $\alpha$ $0.60\%$), 3 breaks
  $7.64\%$ ($0.49$), 5 breaks $5.88\%$ ($0.28$), no breaks $3.45\%$ ($0.26$, $\alpha$ $-0.90\%$);
  pooled break-sample $5.89\%$, Sharpe $0.38$, FF3 $\alpha$ $0.30\%$. **Internal inconsistency
  warning:** the paper calls its panel "34 equity funds" in §2.1 but uses $160$ break-funds and $914$
  no-break funds in the tables, and quotes the no-break excess return as both $3.45\%$ and $5.78\%$.
  The hump's direction is plausible; the magnitudes are not reproducible.
- **A derivative-classed default swap creates a perverse incentive to destroy the insured asset; a
  clawback lien of order 77% removes it** (arXiv:1711.02600v3). Calibration base: the Kauffman
  Foundation's 20-year record on 99 venture funds, where ~90% of funds return below $2.2\times$. In the
  modelled EDCS structure (5% annual premium, 50% underwriter equity share), the insured venture-bank's
  optimum without a clawback is to make **all** investments fail (up to $\approx29\times$ return from
  total loss); with a clawback lien the reported optimum is **~77%** ($62.3\%$ and up to $100\%$
  modelled) and the insured's profit curve becomes monotone increasing in the conventional return. The
  design also claims a capital multiple of $1$–$47\times$ (modelled $30$–$43\times$) by booking insured
  value as Tier 1/Tier 2. Single-author simulation, not estimates.
- **Basel-regulated banking reduces to a closed set of double-entry operations** (arXiv:1204.1583v1).
  A two-bank + central-bank model with a $2\%$ reserve requirement (euro-zone accounts with notice up
  to two years), initial position $11{,}000$ total assets per bank (loans $10{,}000$, capital
  $1{,}000$, reserves $200$). The substantive claims are structural: the *expanded* accounting
  identity shows a bank can write off loans against income with **no effect on capital** while
  profitable, so income-covered write-offs do not cut risk-weighted lending capacity; and deposit
  money creation is independent of base money unless the system sits at its reserve limit. No data, no
  estimated parameters.
- **European bank digital openness clusters into four strategic quadrants** (arXiv:2210.01109v2).
  Sample: the 18 largest European banks (top three by assets in IT, DE, ES, FR, NL, UK), 2015–2019,
  hand-coded from API portals and deal databases; all offer the $\ge3$ PSD2 APIs. Quadrant shares:
  "invisible banks" $28\%$, technological hubs $16\%$, "innovative" $28\%$, "followers" $28\%$; largest
  partnership counts $>35$, $26$, $23$. The $29\%$–$35\%$ sector revenue-at-risk figure is *cited*
  from EBA work, not estimated.
- **Scope note.** Only arXiv:2306.01749v2, arXiv:2510.19619v1 and arXiv:2005.08759v1 contain
  procedures that reproduce on data FinRobot can fetch (§3); arXiv:1204.1583v1 is a simulation
  invariant, arXiv:1711.02600v3 a contractual payoff definition, and arXiv:2210.01109v2 an ordinal
  sector prior. None is off-topic, but the last three are **non-actionable for return estimation**.

## Methods & Formulas

### 2.1 Two-state hidden Markov regime monitor for credit/borrowing intensity

**Purpose.** Convert a weekly count panel (payday loans, delinquencies, charge-offs, new accounts) into
a binary latent "occasional vs persistent" state, so that *sustained* exposure — not a single spike —
drives any flag. It is a state-space alternative to a static control variable.

**Formula.** Latent chain $Z_{it}\in\{1,\dots,K_h\}$ with borrower-specific initial law and a shared,
time-homogeneous transition matrix:
$$\Pr(Z_{i1}=k)=\pi_{ik},\qquad \Pr(Z_{it}=k\mid Z_{i,t-1}=j)=P_{jk}.$$
State-dependent emissions (Poisson), $\log\lambda_{itk}=\alpha_k+x_{it}^{\top}\beta_k$:
$$Y_{it}\mid(Z_{it}=k,x_{it})\sim\mathrm{Poisson}(\lambda_{itk}).$$
An over-dispersed variant uses a Gamma–Poisson (NB2) emission,
$\mathrm{Var}(Y_{it}\mid Z_{it}=k)=\mu_{itk}+\mu_{itk}^2/\phi$. Likelihood by forward recursion:
$$a_1^{(i)}(k)=\pi_{ik}\,g_k(y_{i1};x_{i1}),\qquad
a_t^{(i)}(k)=g_k(y_{it};x_{it})\sum_{j=1}^{K_h}a_{t-1}^{(i)}(j)P_{jk},\qquad
p(y_i)=\sum_k a_{T_i}^{(i)}(k).$$
Expected duration in state $k$ is $1/(1-P_{kk})$; for $K_h=2$ the stationary state-2 probability is
$\pi_2=P_{12}/(P_{12}+P_{21})$. The monitoring rule uses the Viterbi path $\hat Z_{it}$: the first
week $T_i^{(H)}$ such that $\hat Z_{i,t-H+1}=\cdots=\hat Z_{it}=2$, and the borrower-week flag
$$D_{it}=\mathbf 1\{t\ge T_i^{(H)}\}\,\mathbf 1\{\hat Z_{it}=2\}.$$

**Required inputs.** A borrower-week (or entity-week) count $Y_{it}$; covariates $x_{it}$ (amounts and
transaction counts across expense/income/transfer/contribution categories; for the observable
reduction, credit growth, delinquency, real income and rate series from FRED).

**Parameters & defaults.** $K_h=2$; ordering constraint $\alpha_1<\alpha_2$ against label switching;
priors $\alpha_k\sim N(0,3^2)$, $\beta_k\sim N(0,2^2 I_K)$, $\pi_i\sim\mathrm{Dirichlet}(1_{K_h})$;
shared $P$ with softmax rows; Gamma prior on $\phi$; MCMC (Stan). Trigger horizon $H=12$ weeks;
train/test split **by borrower** (80/20), never by time within a borrower.

**Observed effect sizes.** Intercept separation $\exp(\alpha_2-\alpha_1)\approx14\times$; persistence
$P_{22}=0.969$ (95% CI $[0.968,0.970]$), $P_{11}=0.992$; expected spells 32 and 125 weeks; $\pi_2\approx0.21$;
36.4% of borrowers trigger; 17.8% of borrower-weeks are post-threshold state-2; test MAE improves
$0.2287\to0.2227$ vs GLM, train MAE $0.1934\to0.1757$ vs GAMM; Poisson and NB2 HMMs are statistically
tied, so the gains come from the *latent-regime structure*, not from over-dispersion modelling.

**Failure modes.** A shared transition matrix forces one population-level persistence; regime
membership is unidentified ground truth, and the paper decodes in-sample, so its 36.4% is descriptive,
not a forecast. NB2 and Poisson fit alike — do not add over-dispersion machinery and claim a gain. The
state-2 "default-rate analogue" is *not* a default probability and must not be fed to EL/VaR. On the
market-observable reduction (aggregate FRED series) the panel collapses: use a single-sequence HMM,
decode out-of-sample by forward filtering only. Generic switching machinery:
[`../qfin-st/regime-switching.md`](../qfin-st/regime-switching.md).

### 2.2 Benchmark-adjusted factor-loading break detector (style-drift intensity)

**Purpose.** Detect *economically active* changes in a fund's (or bank-equity basket's) size/value
exposure after removing benchmark-inherited changes, and grade each change's severity.

**Formula.** Per regime of a partition of the sample, estimate a Carhart/FF3 regression on daily
excess returns:
$$r_{it}-r_{ft}=\alpha_i+\beta_{iM}(r_{mt}-r_{ft})+\beta_{iS}\,\mathrm{SMB}_t+\beta_{iH}\,\mathrm{HML}_t+\varepsilon_{it}.$$
Benchmark-adjust each loading, $\tilde\beta_{iS}=\beta_{iS}^{\text{fund}}-\beta_{iS}^{\text{bench}}$
(and likewise for HML), so a stock that migrates from mid-cap to large-cap inside the benchmark is
excluded. Locate breaks with the Bai–Perron multiple-break estimator: for a partition with $m$ breaks
at $\{T_1,\dots,T_m\}$, minimise the total sum of squared residuals
$$\sum_{j=0}^{m}\sum_{t=T_j+1}^{T_{j+1}}\bigl(y_t-x_t^{\top}\beta_j\bigr)^2$$
by dynamic programming over admissible break fractions (trimming), selecting $m$ by an information
criterion (BIC/`lwz`) rather than sequential testing. Grade each transition by sign and significance
of the SMB/HML loadings before ($t$) and after ($t+1$) the break:

| Regime change | SMB/HML behaviour | Intensity class |
|---|---|---|
| Either loading significant both sides, **sign flips** | rotation into a new style | Extreme |
| Loading moves significant $\leftrightarrow$ insignificant | drift | Moderate |
| Loading changes magnitude, same sign and significance | strengthening/weakening | Weak |

**Required inputs.** Daily return series for each fund (or basket) and its benchmark, plus the SMB/HML
(or AGT) factor return series; a risk-free rate.

**Parameters & defaults.** $m$ up to 5 comparable breaks; ≥24-month minimum regime length for the
robustness pass (short-regime betas are noise-sensitive). Sign/significance at standard thresholds; the
result differs from a *pure* FF3 break test, which finds a break in every fund.

**Observed effect sizes.** 473 breaks; of 1,559 style transitions, 9 rotation / 927 drift / 622
strengthening-weakening; most move toward Mid Blend or Mid Value rather than Small Value / Small
Growth; the break-count–performance hump peaks at 2–3 breaks (Sharpe $0.59$/$0.49$; FF3 $\alpha$
$0.60\%$/$0.59\%$).

**Failure modes.** The source's sample counts are internally inconsistent (§1) — re-derive every count
and treat the magnitudes as unverified. Multiple testing across funds × two factors inflates the break
count: use BIC/`lwz`, require a significant loading change, and require the break to exceed the
benchmark's own. Survivorship ("funds existing since 2006") biases the level of the hump even if its
shape survives. Break dates are window-sensitive: report a stability sweep. On a listed-bank basket the
detector measures factor repositioning, not fund-manager agency. Generic factor machinery:
[`../qfin-st/factor-models-alpha.md`](../qfin-st/factor-models-alpha.md).

### 2.3 DuPont bank-profitability decomposition and cross-bank screen

**Purpose.** Decompose a bank's return on equity into margin, asset-turnover and leverage so that
"better profitability" is attributed to a driver rather than to a single ratio, and screen a bank
universe for outlier drivers.

**Formula.**
$$\mathrm{ROE}=\mathrm{ROA}\times \mathrm{EM},\qquad
\mathrm{ROA}=\mathrm{NPM}\times \mathrm{AU},$$
with
$$\mathrm{NPM}=\frac{\text{net earnings}}{\text{operating revenue}},\qquad
\mathrm{AU}=\frac{\text{operating revenue}}{\text{total assets}},\qquad
\mathrm{EM}=\frac{\text{total assets}}{\text{common equity}},$$
$$\mathrm{ROD}=\frac{\text{net earnings}}{\text{total deposits}},\qquad
\mathrm{OE}=\frac{\text{non-interest expense}}{\text{total operating income}}.$$
The screen is the regression of ROA on the internal drivers,
$\mathrm{ROA}=c+b_1\,\mathrm{OE}+b_2\,\mathrm{AU}+b_3\,\mathrm{ROD}$, estimated on a panel with bank
and period fixed effects (the source paper instead averages to $n=6$; see failure modes).

**Required inputs.** Net earnings; operating revenue; total assets; common equity; total deposits;
non-interest expense; total operating income — per bank per period.

**Parameters & defaults.** Source paper: 6 banks, 2008–2012 annual reports, five-year averages. Its
fitted coefficients (constant $-0.037$, OE $0.064$, AU $0.196$, ROD $1.141$; $R^2=99.9\%$, adj
$99.8\%$, $F=931.9$) are quoted for reproduction only and should **not** be adopted as priors.

**Observed effect sizes.** The DuPont identity holds by construction; the content is driver
attribution — e.g. SJIBL $\mathrm{ROE}=21.31\%$ at $\mathrm{EM}=11.46$ vs EXIMBL $20.38\%$ at
$\mathrm{EM}=9.57$, on the panel's top $\mathrm{ROA}=2.24\%$. Correlations among the six averages:
ROA–ROD $0.997$, ROA–OE $-0.980$, ROA–AU $-0.949$.

**Failure modes.** With the source sample, $n=6$ and three regressors leave 2 error df: $R^2=99.9\%$
and $F=931.9$ are mechanical, only ROD is significant at 10%, and its loading $>1$ is uninterpretable.
ROA and ROD share the net-earnings numerator, so $\rho=0.997$ is partly definitional. Run the screen as
a *panel* with bank fixed effects, never on a handful of averages. Metric choice changes the ranking
(EXIMBL first by ROA/ROD, SJIBL by ROE) — always report the DuPont decomposition beside a single ratio.
Islamic banks recognise profit-sharing rather than interest income, so NPM/AU are not comparable to
conventional-bank definitions.

### 2.4 Basel ledger mechanics as a simulation invariant (double-entry check)

**Purpose.** Provide a mechanically correct, checkable balance-sheet engine for any agent-based or
stress simulation with banks that create deposits, hold reserves and write off loans — without which
simulated "bank capital" drifts from accounting reality.

**Formula.** Expanded identity (the paper's central point):
$$\text{Assets}=\text{Liabilities}+\text{Common Stock}+(\text{Income}-\text{Expenses})-\text{Dividends}.$$
Each operation is a pair of T-account entries (American convention: debits increase assets/expenses,
credits increase liabilities/equity/income):

| Operation | Debit | Credit |
|---|---|---|
| Deposit cash | vault cash (asset) | customer deposit (liability) |
| Loan to own customer | loan ledger (asset) | customer deposit (liability) |
| Reserve top-up | reserve (asset) | cash (asset) |
| Interbank transfer | payer deposit; bank reserve account | payee deposit; central-bank reserve |
| Interest received | customer deposit | interest income (liability) |
| Loan write-off, step 1 | interest income | loss provision (contra-asset) |
| Loan write-off, step 2 | loan ledger (credit) | loss provision (debit) |

Reserve constraint: $\text{reserves}\ge\rho\times(\text{reservable deposits})$ with $\rho=0.02$ for
eligible euro-zone accounts; lending capacity bounded by risk-weighted capital,
$\text{risk-weighted assets}\le \kappa\,(\text{Tier 1}+\text{Tier 2})$.

**Required inputs.** A ledger state per bank (loans, deposits, cash & equivalents, reserves, capital,
income, loss provisions) and an operation stream (transfers, lending, repayment, write-off, capital
raise, central-bank operations).

**Parameters & defaults.** $\rho=2\%$; initial position total $11{,}000$, loans $10{,}000$, capital
$1{,}000$, reserves $200$, cash $800$ per bank; illustrative write-off $50$; no calibrated magnitudes.

**Observed effect sizes.** None — a descriptive specification, valuable only as an invariant: after
**every** operation $\text{Assets}-\text{Liabilities}-\text{Equity}=0$, and an income-covered write-off
leaves capital unchanged.

**Failure modes.** A bookkeeping description, not evidence — do not cite it for any behavioural
parameter. The paper flags two unresolved variations: same-bank transfers may follow either the same-bank
or interbank path, and unified multi-branch bookkeeping changes the effective liquidity channel. A sim
that deducts losses straight from shareholder equity (a documented textbook error) overstates capital
depletion; enforce the (Income − Expenses) flow. Contagion/tail side of banking simulation:
[`../qfin-st/risk-management-tails.md`](../qfin-st/risk-management-tails.md) and
[`../qfin-st/market-simulation-agent-models.md`](../qfin-st/market-simulation-agent-models.md).

### 2.5 Clawback-lien incentive compatibility for default-swap instruments

**Purpose.** Given an insurance payoff that is legally a derivative (immediate, court-free execution),
design a deterministic clawback so that the insured's payoff is monotone increasing in the underlying
outcome, removing the incentive to manufacture a default. The algebra applies to any contract with a
payoff contingent on an event the holder can influence.

**Formula.** With conventional portfolio return $R$, upside share $s$, annual premium $p$, insurance
payoff $\Pi$ and clawback rate $\lambda\in[0,1]$, the insured's payoff without clawback is
$$V_{\text{EDS}}(R)=(1-s)\,R\,\mathbf 1\{R\ge R_0\}+\Pi\,\mathbf 1\{R<R_0\}-p,$$
which is decreasing in $R$ over the normal-return band (the "jackpot"). Adding the lien
$$V_{\text{EDCS}}(R)=V_{\text{EDS}}(R)-\lambda\,\Pi\,\mathbf 1\{\text{default}\}$$
and requiring incentive compatibility
$$\frac{d V_{\text{EDCS}}(R)}{dR}\ge 0\quad\text{for all } R \text{ in the normal band}$$
selects a minimum $\lambda^\star$. The paper models the optimum at $\lambda^\star\approx77\%$ with
$\lambda=62.3\%$ and $\lambda=100\%$ as variants.

**Required inputs.** The contractual payoff schedule (premium $p$, equity share $s$, coverage $\Pi$,
default trigger, lien term); the insured's achievable return distribution; a lien registry with priority.

**Parameters & defaults.** $p=5\%$/yr, $s=50\%$, $\lambda^\star\approx77\%$ (modelled $62.3\%$,
ceiling $100\%$); lien term months-to-years; modelled capital multiple of original capital
$30$–$43$ (range $1$–$47$) when insured value is booked as Tier 1/Tier 2.

**Observed effect sizes.** Simulation only: without clawback the insured's optimal all-fail strategy
yields up to $\approx29\times$; with clawback its profit curve is monotone increasing and the underwriter
loses money only at the very bottom (break-even at conventional return ratio 1.0). Calibration base: 99
Kauffman venture funds over 20 years, ~90% returning $<2.2\times$.

**Failure modes.** Single-author simulation, no out-of-sample test; $\lambda^\star$ is specific to the
assumed payoff shape. A lien is only as good as its enforceability and registry priority — an
unregistered lien is worth zero exactly when it matters. Banning multiple swaps on one underlying is an
operational control, not a formula. A *design pattern*, not a validated number.

### 2.6 Digital-openness scorecard (ordinal sector prior)

**Purpose.** Position institutions (or a sector) on the open-banking axis using two observable,
countable dimensions, as a slow-moving contextual feature.

**Formula.** Score each institution by $a_i$ = distinct public API functions (split by service:
payments, finance, customer, business) and $g_i$ = external fintech partnerships/investments. Classify
by median (or the paper's qualitative cut): high $a$/high $g$ = "invisible bank"; high/low = "tech hub";
low/high = "innovative"; low/low = "follower". PSD2 floor: $\ge3$ APIs.

**Required inputs.** Public developer-portal API inventories; partnership/investment records.

**Parameters & defaults.** 18 banks (top three by assets in IT, DE, ES, FR, NL, UK); API counts from
developer portals; partnerships from deal databases 2015–2020; API inventory as of 2019.

**Observed effect sizes.** Quadrant shares 28% / 16% / 28% / 28%; maximum partnership counts $>35$,
$26$, $23$; the most advanced banks cluster in above-average DESI countries. Caveat: the 29%–35%
revenue-at-risk figures are *cited*, not estimated.

**Failure modes.** Hand-coded, story-sourced, no statistical test, no time series — it cannot support a
sign claim. API counts measure disclosure and investment history, not capability. Keep it as an
occasional sector prior, never a per-name feature in a return model.

## Data Requirements

Rows are real entries copied from `strategies/endpoints.json`; `moomoo` rows come from the local OpenD
SDK gateway (not live-probed). **gap** = no current provider serves the input.

| Input | Endpoint | Category | Provider | Probe status |
|---|---|---|---|---|
| Bank income statement / balance sheet line items (generic statements) | `https://api.tiingo.com/tiingo/fundamentals/AAPL/statements` | `fundamental_data` | tiingo | ok |
| Bank fundamentals (secondary source, same category) | `https://www.alphavantage.co/query` | `fundamental_data` | alpha_vantage | ok |
| Listed-bank daily OHLCV (factor loadings, break detector, betas) | `https://eodhd.com/api/eod/AAPL` | `core_stock_apis` | eodhd | ok |
| Listed-bank daily prices (secondary) | `https://api.tiingo.com/tiingo/daily/AAPL/prices` | `core_stock_apis` | tiingo | ok |
| Intraday bars for event-window studies | `https://api.twelvedata.com/time_series` | `core_stock_apis` | twelvedata | ok |
| Previous-session aggregate bars | `https://api.massive.com/v2/aggs/ticker/AAPL/prev` | `core_stock_apis` | massive | ok |
| Bank equity instrument universe / listing metadata | `https://eodhd.com/api/exchange-symbol-list/US` | `exchange_symbols` | eodhd | ok |
| Aggregate consumer-credit stress series (delinquency, charge-offs, credit growth) | `https://api.stlouisfed.org/fred/series/observations` | `macro_data` | fred | ok |
| Risk-free curve (discounting, Net Interest Margin benchmark) | `https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2026/all` | `risk_free_curve` | federal_reserve | ok |
| Bank dividends / capital actions | `https://eodhd.com/api/div/AAPL` | `corporate_actions` | eodhd | ok |
| Bank dividend calendar (event studies) | `https://api.benzinga.com/api/v2.2/calendar/dividends` | `corporate_actions` | benzinga | ok |
| Bank news flow (contextual) | `https://eodhd.com/api/news` | `news_data` | eodhd | ok |
| Bank news sentiment score | `https://eodhd.com/api/sentiments` | `news_sentiment` | eodhd | ok |
| Bank analyst ratings | `https://api.benzinga.com/api/v2.1/calendar/ratings` | `analyst_ratings` | benzinga | ok |
| Bank analyst rating summary | `moomoo://get_research_rating_summary` | `analyst_ratings` | moomoo | gateway (not live-probed) |
| Institutional / shareholder structure | `moomoo://get_shareholders_institutional` | `institution_data` | moomoo | gateway (not live-probed) |
| Revenue segment breakdown (fee vs net-interest mix) | `moomoo://get_financials_revenue_breakdown` | `revenue_breakdown` | moomoo | gateway (not live-probed) |
| Economic calendar (central-bank/rate events) | `moomoo://get_economic_calendar` | `economic_calendar` | moomoo | gateway (not live-probed) |
| Rate-path expectations (policy surprises) | `moomoo://get_fed_watch_target_rate` | `fed_watch` | moomoo | gateway (not live-probed) |
| **Bank-level regulatory capital (Tier 1 / Tier 2 ratios, RWA, leverage ratio)** | — | — | — | **gap** |
| **Bank-level deposits, funding mix, Net Interest Margin components** | — | — | — | **gap** |
| **Bank-level loan-loss provisions, NPLs, charge-offs by loan type** | — | — | — | **gap** |
| **Mutual-fund / ETF NAV series and holdings (the style-drift panel)** | — | — | — | **gap** |
| **Consumer transaction-level / open-banking records (borrower-week panel)** | — | — | — | **gap** |
| **Payday / consumer-lender loan counts and originations** | — | — | — | **gap** |
| **Single-name credit spreads / CDS / equity-default-swap quotes** | — | — | — | **gap** |
| **Interbank ledger flows and central-bank reserve balances by institution** | — | — | — | **gap** |
| **API inventories and fintech partnership/deal records (targets, dates, amounts)** | — | — | — | **gap** |

**What the gap costs, quantified.** The catalog serves generic fundamentals and equity returns, but
**nine of the inputs the papers rest on have no provider at all.** (i) *Profitability screen:* ROD and
OE need total deposits and non-interest expense, which no row exposes, so of the paper's $30$
bank-year observations only ROA/ROE can be reconstructed from a generic statements endpoint. (ii) *HMM
monitor:* the paper needs $126{,}188$ transactions for $1{,}815$ borrowers over ~$80$ weeks each; with
no consumer-transaction source the only reduction is to FRED aggregate credit-stress series at
**monthly** granularity, losing the weekly panel and borrower-level regime initialisation (≈4× coarser
grid). (iii) *Style-drift detector:* needs daily NAV for $34$ funds over $17.5$ years
($\approx4{,}400$ observations per fund); with no mutual-fund NAV endpoint it can only run on
listed-bank equity returns, a different object. (iv) *Clawback design:* needs no market data but is
unenforceable without a lien registry and single-name credit-spread quotes, both **gap**. (v) *Basel
mechanics:* needs institution-level ledger flows — simulation-only. (vi) *Openness scorecard:* needs
hand-coded API/partnership panels reproducible from no feed. Net: the catalog supports one estimator
end-to-end (the DuPont screen, partially) and hosts the rest only after transplantation onto
market-observable proxies.

In the table above, `gap` inputs are not served by any provider and `derived` inputs are computed locally from the others — treat both as such rather than fetching or inventing them.

## Pitfalls & Validation

- **Six observations are not a regression.** With $n=6$ and three regressors, the reported
  $R^2=99.9\%$ and $F=931.9$ in arXiv:2005.08759v1 are degrees-of-freedom artefacts (2 error df); the
  only coefficient that clears even the 10% critical $t$ is ROD, whose loading $>1$ is
  uninterpretable because ROA and ROD share the net-earnings numerator ($\rho=0.997$). Use a multi-bank
  panel with fixed effects; never adopt the paper's coefficients.
- **Unreproducible sample accounting.** arXiv:2510.19619v1 reports its panel as 34 funds in the data
  section but 160 funds with breaks (and 914 without) in the results, and gives the no-break excess
  return as both $3.45\%$ (Table 3) and $5.78\%$ (text). Before porting the detector, re-derive every
  count; treat the hump shape as the hypothesis and the magnitudes as unverified.
- **Multiple testing in break detection.** Scanning every fund against two factors with sequential
  break tests inflates the break count. Use the Bai–Perron information criterion, require significance
  of the loading change, and net out breaks already present in the benchmark (the paper's stated
  reason for benchmark-adjusting). Report a window-length sweep.
- **Survivorship.** A fund panel selected as "present since 2006" is survivor-selected, so the level
  of any performance comparison is biased even when the shape is not (arXiv:2510.19619v1).
- **Leakage in state-space decoding.** The 36.4% trigger rate and 17.8% post-threshold share come from a
  **full-sample Viterbi path** (arXiv:2306.01749v2). A live rule must decode by forward filtering only,
  estimate $P$ and the emissions on a borrower-disjoint training set, and report the out-of-sample
  trigger rate; the paper's borrower-level 80/20 split is the template — within-borrower time splits leak.
- **A "default-rate analogue" is not a default rate** (arXiv:2306.01749v2). $D_{it}$ is a post-threshold
  regime-occupancy share; feeding it into expected-loss or capital maths commits a category error.
- **Label switching and identification.** Unconstrained HMMs swap state labels across MCMC runs; impose
  the ordering constraint $\alpha_1<\alpha_2$ and fix a shared transition matrix deliberately, reporting
  it as an assumption, not a discovery (arXiv:2306.01749v2).
- **Regime dependence of any calibration.** The profitability panel is 2008–2012 Bangladesh (post-crisis,
  Islamic-banking-specific), and the openness panel is 2015–2019 Europe; neither is a stable structural
  prior for a different jurisdiction or era (arXiv:2005.08759v1, arXiv:2210.01109v2).
- **Transaction costs asserted, never modelled.** arXiv:2510.19619v1 concludes that excessive
  risk-shifting "increases transaction costs" but fits no cost model; the hump could equally be
  break-detector overfitting. Any claim built on it needs an explicit cost model
  ([`../qfin-st/backtest-methodology.md`](../qfin-st/backtest-methodology.md)).
- **Description mistaken for evidence.** arXiv:1204.1583v1 is a bookkeeping specification with no data —
  use it only as a balance invariant. arXiv:1711.02600v3's 77% is a simulation output of one payoff
  family; arXiv:2210.01109v2 has no statistical test. None supports a point estimate about the world.

## Recommended Workflow

Ranked by value per unit of effort against what the data layer can fetch. Items 1–3 build now; 4–6 use
no market data (design/invariant code); 7 unlocks the rest.

1. **DuPont bank-profitability screen.** *What:* assemble ROA, ROE, NPM, AU, EM (and ROD/OE where the
   line items exist) per listed bank-period from `tiingo` / `alpha_vantage` `fundamental_data`, and
   rank drivers. *Pass:* $\text{ROE}=\text{ROA}\times\text{EM}$ and $\text{ROA}=\text{NPM}\times\text{AU}$
   hold to rounding for every bank-period, and the screen flags bottom-decile ROA banks with an
   attributed driver. *Risk:* many bank-specific lines are **gap** — report coverage honestly.
2. **Two-state HMM credit-stress monitor.** *What:* fit the §2.1 HMM ($K_h=2$) to FRED aggregate
   consumer-credit delinquency / charge-off / credit-growth series; emit expected spell lengths and a
   forward-filtered (not Viterbi) regime probability. *Pass:* regimes reproduce the ~14× intensity
   separation and $P_{22}\gtrsim0.95$, with out-of-sample MAE better than a single-regime Poisson.
   *Risk:* monthly aggregates collapse the panel — document the loss.
3. **Factor-loading break detector on bank-equity baskets.** *What:* port §2.2 — rolling FF3/AGT
   loadings on bank-sector constituents plus Bai–Perron breaks, with the three-way intensity taxonomy.
   *Pass:* break dates stable across at least three window lengths and each survives netting against
   the benchmark's own loadings. *Risk:* measures factor repositioning, not fund-manager behaviour.
4. **Basel ledger invariant harness.** *What:* implement the §2.4 double-entry operations as a
   unit-tested balance checker for the agent-based simulator; enforce the (Income − Expenses) flow.
   *Pass:* $\text{Assets}-\text{Liabilities}-\text{Equity}=0$ after every operation and a covered
   write-off leaves capital bit-identical. *Risk:* worthless if the simulator never uses banks.
5. **Clawback-lien incentive-compatibility calculator.** *What:* implement §2.5: given $p,s,\Pi$, solve
   for the minimum lien $\lambda^\star$ making the insured's payoff monotone in the underlying return,
   and report break-even. *Pass:* a pure derivative-classed payoff is shown monotone-decreasing
   (jackpot) and the clawback restores monotonicity at the reported optimum. *Risk:* an unregistered
   lien is unenforceable — surface that.
6. **Bank news/analyst context overlay.** *What:* join `news_data` / `news_sentiment` /
   `analyst_ratings` on bank tickers as a slow contextual tag for item 1. *Pass:* tag coverage over the
   backtest window with no look-ahead (publication timestamps respected). *Risk:* sentiment endpoints
   are point-in-time imperfect; keep it descriptive.
7. **Register a regulatory-filings / bank-metrics data category (prerequisite).** *What:* add a
   category (e.g. `bank_regulatory_metrics` / `filings`) to `finrobot/engine/data/categories.py` and
   wire ingestion for bank statements with the missing line items (Tier 1/Tier 2, RWA, deposits,
   provisions, NPLs). *Pass:* the DuPont line items resolve for a sample of listed banks without manual
   entry. *Value:* without it, item 1 stays coverage-limited and this category's profitability
   literature cannot be validated at all.

## Output Format

### DuPont Profitability Screen
| Bank | Period | ROE | ROA | EM | NPM | AU | Driver | Identity check |
|------|--------|-----|-----|----|-----|----|--------|----------------|
| ... | ... | ... | ... | ... | ... | ... | ... | ROE=ROA×EM, ROA=NPM×AU hold / off by x |

Emit ROD/OE columns only where the line items resolve; otherwise report coverage
as a fraction of bank-periods and never impute a missing line item.

### Credit-Stress Regime Monitor (served macro series)
| Series | State 1 α₁ | State 2 α₂ | P₁₁ | P₂₂ | E[spell] 1/2 (wk) | π₂ | OOS MAE vs single-regime Poisson |
|--------|-----------|-----------|-----|-----|-------------------|----|----------------------------------|
| ... | ... | ... | ... | ... | ... | ... | ... |

Decode by forward filtering only; label the flag D_it a post-threshold
regime-occupancy share, not a default probability.

### Verdict
State that the monitor depends on the single served macro_data (FRED) row, so an
endpoint outage leaves only the descriptive DuPont / ledger diagnostics; list bank
balance-sheet lines, regulatory capital ratios and borrower-level panels as gap
(unserved), and claim no profitability or credit-feed result beyond coverage.

## References

| arXiv id | Title | Year |
|---|---|---|
| 2306.01749v2 | Detecting Consumers' Financial Vulnerability using Open Banking Data: Evidence from UK Payday Loans | 2023 |
| 2005.08759v1 | Determinants of Profitability of Banks: Evidence from Islamic Banks of Bangladesh | 2020 |
| 2510.19619v1 | An Empirical study on Mutual fund factor-risk-shifting and its intensity on Indian Equity Mutual funds | 2025 |
| 1711.02600v3 | The perverse incentive for insurance instruments that are derivatives: solving the jackpot problem with a clawback lien for default insurance notes | 2017 |
| 1204.1583v1 | Description of the Operational Mechanics of a Basel Regulated Banking System | 2012 |
| 2210.01109v2 | Digital financial services and open banking innovation: are banks becoming invisible? | 2022 |
