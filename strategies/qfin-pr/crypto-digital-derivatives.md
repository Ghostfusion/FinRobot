# Crypto & Digital Asset Derivatives — learnings from the q-fin.PR corpus
`52` of 2274 corpus papers matched this category (`51` with PDFs); this doc is based on a close reading of `6`.

## 1. What the corpus actually offers

- **Rough (fractional) stochastic volatility with price–volatility co-jumps is the best-performing crypto option model in this corpus.** On two Deribit Bitcoin call sets (July 11 2020, $S_0=\$9{,}232.98$, 40 calls, $T\in\{19,47,166,257\}$ days; and Feb 19 2024, $S_0=\$52{,}108$, $T\in\{4,39,130,312\}$ days), six fractional-SV specifications beat Heston and Black–Scholes on jointly-calibrated average relative pricing error (ARPE): 3.71–5.80% versus Heston 7.20%/11.73% and BS 28.96%/23.52%. The estimated roughness exponent is below one everywhere ($\hat d\approx0.54$–$0.94$), i.e. short-range (anti-persistent) volatility dependence, and the leverage parameter is **positive** ($\hat\rho\approx0.006$–$0.43$) — an *inverse* leverage effect — where purely diffusive Heston fits a *negative* $\hat\rho$ (arXiv:2403.16006v3).
- **The corpus disagrees with itself on which crypto-SV specification wins.** The 2020 COVID sample prefers FSV-GMRTS with the type-I (exponential–Riemann–Liouville) kernel, the 2024 sample prefers FSV-ALJD with the type-III (piecewise) kernel; there is no stable "best model", only a stable *family* advantage over Heston/BS (arXiv:2403.16006v3). The same instability appears in the on-chain study, whose benchmark is not a jump/SV model at all but Black–Scholes with a regime-conditional GARCH volatility (arXiv:2512.20190v1).
- **On-chain option AMMs quote cheap relative to a regime-switching-volatility Black–Scholes benchmark.** Across all 4,090 Hegic trades on Arbitrum (Oct 24 2022 – May 21 2024; wBTC 1,315, ETH 2,775), the relative mispricing $\Delta=(C_{\text{BS}}-O)/O$ is positive on average except for ETH puts: wBTC calls mean $+0.175$ (median $+0.052$), ETH calls $+0.097$ ($+0.063$), wBTC puts $+0.025$ ($+0.011$), ETH puts $-0.065$ ($-0.024$). A two-step feasible GLS on eight trade-time regressors reaches adjusted $R^2$ 0.5617 (wBTC) / 0.4961 (ETH) (arXiv:2512.20190v1).
- **The mispricing is ordered by liquidity and size, not by the underlying return.** Per one-standard-deviation move, the wBTC spread rises with order size (+2.28%***), strike (+5.59%***), maturity (+1.66%*) and estimated volatility (+7.89%***), and falls with underlying trading volume (-7.43%***); ETH keeps only size (+3.34%***), volume (-13.53%***) and a call/put dummy (+8.69%**). Volume tightening the gap is the most robust single effect in the study (arXiv:2512.20190v1).
- **Crypto options are settled in crypto, so the native contract is an inverse (power) payoff, not a plain call.** Roughly 90% of active crypto options trade at Deribit with crypto settlement quoted in USD; the standard inverse call is $(1-K/S_T)^+$ in crypto units, and its Quanto-inverse and inverse-power generalizations are scalar rewrites of a single Fourier integral. The power $p_1>1$ increases USD exposure for BTC/ETH but *reverses* for low-priced tokens (DOGE, MATIC) and is ineffective for USD-pegged tokens such as Tether (arXiv:2403.16006v3).
- **Perpetual-future funding can be designed to pin the price exactly to an arbitrary target, and the theory is sharp about the threshold.** Funding rate $F(s)=\Phi(s,X_s,Y(s))$ makes the perpetual price equal a target $\varphi(s,X_s)$ — tradable or not — provided the demand/supply function $H$ is monotone with slope at least $\ell$, and $\ell$ exceeds an explicit bound; in a Black–Scholes market with $r=0.02,\ \sigma=0.3$ the bound is $\ell>0.26227$. The realistic *averaged* rate (8-hour window, $\delta=1/1095$) only converges to the ideal at rate $O(\sqrt\delta)$ (arXiv:2506.08573v1).
- **Perpetuals are the dominant crypto derivative — the market context the theory is built for.** Perpetual futures, introduced by BitMEX in 2016, account for >$90T cumulative volume and 93% of the cryptocurrency futures market, and most exchanges average the funding fee over the past 8 hours, i.e. $\delta=1/1095$ (arXiv:2506.08573v1).
- **Bitcoin cash-and-carry is segmented, and the measured wedge is large.** Implied carry from listed IBIT options (via put-call parity) minus matched CME bitcoin futures carry is, per the fee-adjusted definition, a mean wedge of 2.58% and median 2.52% in annual percentage points (N = 386 date-bucket observations), with SD 4.72%, 5th percentile -4.77% and 95th percentile 10.42% — not noise around zero, and consistent with collateral/margin systems not cross-margining hedged bitcoin exposure (arXiv:2605.29309v1). This is a direct empirical counterweight to the alignment theorem of arXiv:2506.08573v1: the theory says the rails *can* be aligned, the data say they presently are not.
- **DeFi liquidation can be replaced by a call option the seller may cancel, with a large measured reduction in forced selling.** A *reversible call option* (seller reimburses the buyer a constant $k>1$ to terminate before maturity) deployed as the Miqado protocol reduces liquidated collateral by up to **89.82%** ($2.32B \to 236.40M USD) at a maximum supporter-default probability of 13.48%, replayed over 48,364 Aave V1/V2 and Compound liquidations (May 1 2019 – Sep 30 2022, 41 months) (arXiv:2303.15162v2).
- **In that DeFi study the option premium factor barely changes behaviour.** Exercise-and-profit probability is 87.46% / 87.19% / 85.95% for $T=1/6/24$ hours and is **invariant** across premium factors 1–20%; the default probability falls monotonically with the premium (13.48% at 1% down to 8.45% at 20% for $T=24$h). The authors call this insensitivity to the premium "to our surprise" (arXiv:2303.15162v2).
- **Stablecoin reserves feed back into the sovereign curve — a crypto→funding channel, not a crypto-derivative one.** A 1% increase in Tether's share of outstanding U.S. Treasury bills is associated with a 3.8% (14–16 bp) reduction in 1-month yields (3.4% for 3-month); above a threshold of 0.973% market share the semi-elasticity jumps to 6.3% (1-month) / 5.82% (3-month), worth ~24 bp at Q1 2025 market share, with Tether holding ~$98.5bn = 1.6% of outstanding bills (arXiv:2505.12413v1).
- **The corpus' crypto-valuation and forecasting branch is thin on derivatives.** The shortlist's remaining members are price-prediction (GRU, Transformer, PULSE-style), token/TVL valuation and event studies; they supply market context (e.g. the cost-of-carry/funding links in the jump literature) but no additional derivative-pricing primitives beyond the six read here.

## 2. Implementable formulas & algorithms

### 2.1 Reversible call option (DeFi liquidation replacement)
**Purpose.** Price and evaluate the top-up call that lets a supporter rescue an unhealthy lending position instead of liquidating it; also a template for any "cancellable" option primitive.

Payoff to the buyer: constant $k>1$ if the seller terminates pre-maturity, otherwise a European call:
$$PC_B=\begin{cases}k & \text{if } C_S \text{ terminates},\\ \max(A(T)-K,\;0) & \text{otherwise.}\end{cases}$$
Premium via foreign-exchange Black–Scholes (spot fixed as the debt→collateral oracle rate $p_{t_0}$, domestic rate $=IL$, foreign rate $r_f$):
$$c=S_0e^{r_fT}N(d_1)-Ke^{-rT}N(d_2),\qquad d_1=\frac{\ln(S_0/K)+\big(r-r_f+\tfrac12\sigma^2\big)T}{\sigma\sqrt T},\qquad d_2=d_1-\sigma\sqrt T,$$
and the protocol prices the top-up $C_{t_0}$ implicitly from
$$p_{t_0}e^{r_fT}N(d_1)-Ke^{-IL\,T}N(d_2)=C_{t_0}\,p_{t_0}.$$
Position algebra that drives the trigger and the coexistence buffer:
$$HF_t(P)=\frac{\theta\,C_t\,p_t}{D_t},\qquad CR_t(P)=\frac{C_t p_t}{D_t},\qquad C_{re}=C_{t_0}(1+IL)k_{re},\qquad k_{SF}=CR_{t_0}(P)(\cdot+B)<1 .$$
- **Inputs:** oracle price $p_t$ per (collateral, debt) pair; collateral discount $\theta$, close factor $k_{CF}$, spread $S$, borrow rate $IL$; real post-liquidation price paths at 1/6/24 h.
- **Parameters:** premium factor $\{1,2,5,10,20\}\%$; $T\in\{1,6,24\}$h; $k_{re}\in(0,1)$; buffer $B>1$; one debt token and one collateral token per position.
- **Observed effects:** 89.82% collateral-release reduction; accumulator restraint 281.70M / 563.40M / 1.41B / 2.82B / 5.63B USD for the 1/2/5/10/20% premiums; health-factor recovery 82.22% (Miqado @5%) vs 82.25% (fixed-spread liquidation) (arXiv:2303.15162v2).
- **Failure modes:** the BS premium *ignores the termination right* ("does not take into account the decrease in risk and lowered average payoff due to termination") and the authors defer a true model; the simulation uses **real historical prices**, not GBM, and reports **no volatility value**; results are per-liquidation-event only, exclude spiral/second-order effects, and assume borrowers never rescue (payoffs are upper bounds) (arXiv:2303.15162v2).

### 2.2 Fractional stochastic volatility with co-jumps: inverse, Quanto-inverse and inverse-power options
**Purpose.** The crypto-option pricing engine: rough vol, price/vol jumps and crypto settlement in one characteristic-function framework, priced by one-dimensional Fourier inversion.

Risk-neutral price as crypto/USD:
$$S_t=\frac{S_0\,e^{X_{T_t}+\rho Y_t}}{\phi_{X_1}(-i)^{T_t}\,\phi_{Y_1}(-i\rho)^{t}},\qquad T_t=\int_0^t A_s\,ds,\qquad A_t=A_0e^{-\kappa t}+m(1-e^{-\kappa t})+Y^{(h)}_t,$$
with $X$ a Lévy base process (ALJD or GMRTS) and $Y$ a Lévy subordinator. The type-I kernel and its tail integral,
$$h_1(t-s)=\frac{e^{-\kappa(t-s)}(t-s)^{d-1}}{\Gamma(d)},\qquad H_1(t-s)=\frac{\Gamma(d)-\Gamma(d,\kappa(t-s))}{\kappa^d\,\Gamma(d)},$$
have the type-III **piecewise** counterpart (below), which is the only one with a closed-form $s$-integral (Proposition 3). The conditional characteristic function is
$$\phi_{\log S_t|t_0}(u)=\mathbb E_{t_0}[e^{iu\log S_t}]=\exp\Big\{iu\big(\log S_{t_0}-(t-t_0)\log\phi_{Y_1}(-i\rho)\big)+\int_{t_0}^t\log\phi_{Y_1}\big(\rho u-H(t,s)\varphi(u)\big)ds+\cdots\Big\},$$
and the calibration-friendly call price (parity form, needs only $\mathbb E[S_T]<\infty$) is
$$C_{t_0}=S_{t_0}-\frac{K}{2}+\frac1\pi\int_0^\infty\operatorname{Re}\frac{K^{-iu}\phi_{\log S_T|t_0}(u)}{u^2+iu}\,du .$$
Quanto-inverse-power call/put ($p_1,p_2\ge0$, fixed conversion $R$):
$$C^{(qip)}_{t_0}=R^{p_1}\Big[\frac{K^{p_2}}{2}+\frac1\pi\int_0^\infty\operatorname{Re}\Big(\frac{K^{-iu p_2/p_1}\phi_{\log S_T|t_0}(u)}{ip_1u-u^2}\Big)du\Big],\qquad P^{(qip)}_{t_0}=C^{(qip)}_{t_0}+R^{p_1}\big(K^{p_2}\phi_{\log S_T|t_0}(ip_1)-1\big).$$
Hedging (Corollary 1) uses spot plus a variance-swap flow, with all Greeks as one-dimensional Fourier integrals in the same integrand.
- **Inputs:** crypto option midquotes by strike/maturity (Deribit-style, European, crypto-settled), spot, risk-free rate.
- **Parameters:** ALJD 6 ($\sigma_X,\lambda_X,b_X,\eta,\lambda_Y,b_Y$) or GMRTS 8–11 ($a_X,b_X,c_X,\theta,n,a_Y,b_Y,c_Y$), plus kernel $(\kappa,d)$, $d\in(0.5,1)$, and FSV $(A_0,m,\rho)$; calibrated $\hat d\in[0.54,0.94]$, $\hat\kappa\approx1$–$13.5$.
- **Observed effects:** best ARPE 3.71030% (data set 1, FSV-GMRTS type-I) and 4.04962% (data set 2, FSV-ALJD type-III); type-III wall time 1,101.7 s vs 6,001.6 s for type-I on the same fit (~5.5×); max relative pricing error ≈15% / 29% vs BS 100% / 96% (arXiv:2403.16006v3).
- **Failure modes:** cannot generate rough volatility-of-volatility; genetic-algorithm calibration guarantees no global optimum (residuals ~4–6%); only type-III is closed form, and it is merely $C^1$; the activity rate $A$ is unobserved so the quadratic-variation hedge term must be approximated; the power mechanism is meaningless for USD-pegged tokens (arXiv:2403.16006v3).

### 2.3 Regime-switching volatility benchmark for on-chain (AMM) quotes
**Purpose.** Build a model-based reference price for an on-chain option AMM so the protocol's quotes can be monitored and calibrated without a full risk-neutral model.

Two-regime Markov-switching AR on daily log-returns and a regime-conditional GJR-GARCH:
$$r_t=\mu_{\rho_t}+\sum_{i=1}^{X}\phi_{\rho_t,i}r_{t-i}+\varepsilon_{\rho_t,t},\qquad \varepsilon_{\rho_t,t}\sim N(0,\sigma^2_{\rho_t}),$$
$$\sigma^2_{\rho_t,t}=\omega_{\rho_t}+\sum_{i=1}^{p}\alpha_i\epsilon^2_{t-i}+\sum_{i=1}^{o}\gamma_i\epsilon^2_{t-i}\mathbb 1[\epsilon_{t-i}<0]+\sum_{j=1}^{q}\beta_j\sigma^2_{t-j},$$
then plain Black–Scholes at the regime-conditional annualised $\sigma_t$; mispricing regressed by two-step feasible GLS:
$$\Delta price_j=\frac{C(P)_j-O_j}{O_j}=\beta_0+\beta\!\cdot\!X_j+\xi_j,\qquad \hat\beta_{GLS}=(X^\top\Omega^{-1}X)^{-1}X^\top\Omega^{-1}\Delta price .$$
- **Inputs:** a long daily crypto return history for regime/GARCH estimation (BTC/ETH here: Dec 7 2018 – May 25 2024, ~2,000 daily observations), on-chain trade records (type, strike, maturity, amount, premium, timestamp).
- **Parameters:** AR order 8 (BTC) / 10 (ETH); $(p,o,q)$ by BIC over $p,q\le10,\ o\le5$; skewed-$t$ errors with $\hat\eta\approx2.96$–3.55; $X$ = 8 regressors (Amount, Strike, Maturity, Return, Volume, Volatility, Kind, Type), all logged where non-negative then standardised.
- **Observed effects:** adjusted $R^2$ 0.5617 (wBTC) / 0.4961 (ETH); BTC low-volatility GJR asymmetry $\hat\gamma_1=-0.0895$*** is **negative** (inverse leverage); persistence $\hat\beta_1=0.63$–0.93, lower in high-volatility states; no residual autocorrelation (all Ljung–Box/Engle-ARCH $p>0.10$) (arXiv:2512.20190v1).
- **Failure modes:** the benchmark is "a reference price for short maturities, not a full structural model of the risk-neutral measure"; $\sigma$ is held constant over each option's life; all results are conditional cross-sectional associations, not causal or unique prices; AMM inventory, execution costs, stablecoin risk and bridge latency are unmodelled (arXiv:2512.20190v1).

### 2.4 Funding-rate design for perpetual futures (infinite-horizon BSDE)
**Purpose.** Choose the funding rate so the perpetual price tracks a target $\varphi(s,X_s)$ exactly, and construct the hedging portfolio.

With $X$ the wealth process and $Z=\phi\sigma$, the price solves the risk-neutral pricing BSDE
$$Y(s)=Y(T)-\int_s^T\big(r(u,X_u)Y(u)-\Phi(u,X_u,Y(u))\big)du-\int_s^T Z(u)\,dB(u),$$
and the *designed* rate is
$$\Phi(s,\gamma,y)=H\big(\varphi(s,\gamma),y\big)-\partial_s\varphi(s,\gamma)-\tfrac12\operatorname{tr}\!\big(\sigma\sigma^\top\partial_{xx}\varphi\big)(s,\gamma)-r(s,\gamma)\,\partial_x\varphi(s,\gamma)\,\gamma(s)+r(s,\gamma)\,y,$$
with $H(y,y)=0$ (no transaction on the solution path) and Lipschitz slope $\ge\ell$. The practical **path-dependent** rate averages the last $\delta$:
$$\Phi^{\delta}(s,\gamma,\eta)=\frac1\delta\int_{s-\delta}^s\Phi(u,\gamma,\eta(u))\,du,\qquad \delta=\frac{1}{1095}\ (8\text{h}),$$
with $\lim_{\delta\to0}\mathbb E\|Y^\delta-Y\|_T=0$ and $\|Y^{\delta}-Y\|_T\le(L_1+L_2\|X\|_T^{\rho})\sqrt{\delta}$. The replicating portfolio and the uniqueness bound:
$$\phi(s)=Z(s)\sigma^{-1}(s,X_s),\qquad \ell>\inf_{K>0}\Big(K+\tfrac12\big(\tfrac{\sqrt{r}}{2K}+M_{\rho\vee2}C_3\big)^2\Big)\rho .$$
- **Inputs:** none beyond a volatility model and a chosen target $\varphi$ (index, power, FX, geometric-mean CFMM pool value); Monte-Carlo paths for validation.
- **Parameters:** BS example $r=0.02,\sigma=0.3$: $\ell>0.26227$ for the spot rate and $1.26227<\ell<15.75125$ for $\delta=1/1095$; power target $\rho=\max_i p_i$; shape $H$ linear or piecewise-linear.
- **Observed effects:** $Y(s)=\varphi(s,X_s)$ exactly under the spot rate; the 8-hour rate deviates only at $O(\sqrt\delta)$ — e.g. $\|Y^\delta-Y\|_T\le0.11134\|X\|_T+0.02545$ in the BS example (arXiv:2506.08573v1).
- **Failure modes:** the $\ell$ bound is explicitly *not* optimal, and a too-small $\ell$ admits multiple prices (worked $\ell=1$ counterexample); uniqueness relies on $H$; only the constant-proportion path-dependent rate is analysed; geometric-mean CFMM targets are non-differentiable at the origin (arXiv:2506.08573v1).

### 2.5 Implied carry and the ETF-vs-futures wedge (basis / funding measurement)
**Purpose.** Recover, from traded option prices alone, the carry/funding embedded in a listed bitcoin vehicle and compare it with the futures rail.

Put-call-parity implied forward, converted to bitcoin units, and the wedge:
$$F^{ETF}_t(K,T)=K+e^{r_t\tau_{t,T}}\big(C_t(K,T)-P_t(K,T)\big),\quad \tau_{t,T}=\frac{\text{calendar days}}{365},\qquad \text{carry}^{ETF}=\text{exact effective annualised}\ \frac{F^{ETF}_t/q_t}{S^{ETF}_t}-1+0.25\%,$$
$$y^{CME}_t(T)=\text{effective annualised premium of the matched CME future over BRRNY},\qquad w_t(T)=y^{CME}_t(T)-y^{ETF,adj}_t(T).$$
- **Inputs:** IBIT call/put midquotes and closes, the daily holdings file (bitcoin per share $q_t$), matched CME bitcoin futures closes, BRRNY, SOFR.
- **Parameters:** 14–90 days to expiry; $|$moneyness$|<5\%$; bid-ask spread $<10\%$ of mid; open interest $\ge100$ on both legs; one selected near-the-money strike per date/expiration/bucket, target 22d and 45d maturities.
- **Observed effects:** N=386; mean 2.581%, median 2.521%, SD 4.716%, P05 -4.767%, P95 10.418%; by bucket 14–30d mean 2.222% (SD 5.527%) and 31–60d mean 2.939% (SD 3.713%) (arXiv:2605.29309v1).
- **Failure modes:** IBIT options are American, so early exercise is handled only by sample selection (no early-exercise premium model); the 61–90d bucket is excluded as too thin; BRR (settlement) and BRRNY (US close) are not time-aligned; data are vendor-licensed and not public; borrow costs are not modelled (arXiv:2605.29309v1).

### 2.6 Stablecoin-reserve semi-elasticity on short yields (threshold regression)
**Purpose.** Measure and forecast the crypto→sovereign-funding channel that sits behind stablecoin collateral and, indirectly, crypto carry.

Baseline semi-log time-trend model and Hansen threshold regression:
$$\ln(y_t)=\alpha+\beta S_t+\gamma T_t+\delta R_t+\varepsilon_t,$$
$$\ln(y_t)=\alpha+\beta_1\big[S_t\mathbb 1(S_t\le\tau)\big]+\beta_2\big[S_t\mathbb 1(S_t>\tau)\big]+\gamma T_t+\delta R_t+\varepsilon_t,\qquad \tau=0.973\%,$$
with $\mathrm{IHS}(x)=\ln\!\big(x+\sqrt{x^2+1}\big)$ used for the T-bill-issuance control, $R_t$ the residual of IHS issuance on the trend and $S_t$ (scaled ×1000), and $S_t$ = Tether's direct T-bill holdings ÷ total outstanding bills.
- **Inputs:** FRED 4-week/13-week secondary yields; Tether Consolidated Reserves Reports (direct T-bill line only); Treasury outstanding bill stock; time trend 1..13 (Q1 2022 – Q1 2025).
- **Parameters:** $\tau=0.973\%$ by per-model grid search; bootstrap likelihood-ratio test with 500 replications.
- **Observed effects:** baseline $\hat\beta=-3.795$** (1-month) and $-3.386$** (3-month); threshold high regime $-6.264$*** / $-5.824$***, low regime $-1.730$ / $-1.419$ (insignificant); LR $=34.59$, bootstrap $p=0.0060$; ~14–16 bp baseline and ~24 bp (Q1 2025) yield reduction (arXiv:2505.12413v1).
- **Failure modes:** no HAC/Newey–West or robust errors anywhere despite a time-series design; implied 13 observations against 3–6 parameters; no lag, no instrument, no causality test (language is associational); only direct T-bill holdings (excludes ~$20bn via money-market funds and reverse repo); three mutually inconsistent annual-savings figures ($15bn / $10bn / $14.8bn); low-regime significance is described inconsistently (arXiv:2505.12413v1).

## 3. Data requirements → available endpoints

| Input | Endpoint | Category | Provider | Probe status |
|---|---|---|---|---|
| Crypto spot price (BTC, ETH, …) | — | — | — | gap — no crypto/exchange price feed exists in the inventory |
| Crypto option chains / implied surfaces (Deribit) | — | — | — | gap |
| On-chain option-AMM trade records (Hegic/Arbitrum) | — | — | — | gap |
| Listed bitcoin-ETF option chain (IBIT) | — | — | — | gap — `cboe` serves only the SPX chain |
| CME bitcoin futures, BRRNY/BRR reference rates | — | — | — | gap |
| Perpetual-futures funding-rate history | — | — | — | gap |
| ETF holdings file (bitcoin per share, daily) | — | — | — | gap |
| DeFi liquidation + DEX swap events (Aave/Compound/Uniswap) | — | — | — | gap |
| On-chain oracle prices (Chainlink-style) | — | — | — | gap |
| Stablecoin reserve attestations (Tether CRR, direct T-bills) | — | — | — | gap |
| Outstanding U.S. Treasury bill stock | — | — | — | gap — the Treasury endpoint is the daily yield-curve CSV, not the outstanding-bill table |
| T-bill / SOFR short rate for carry and parity forwarding | `https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2026/all` | risk_free_curve | federal_reserve | ok — daily curve; ~17 s latency, 45 s timeout |
| Macro rates / Fed-funds path (carry, time trend control) | `https://api.stlouisfed.org/fred/series/observations` | macro_data | fred | ok |
| Equity OHLCV as a crypto-beta proxy (COIN/MSTR-style, not crypto) | `https://eodhd.com/api/eod/AAPL` | core_stock_apis | eodhd | ok |
| Equity OHLCV (alt provider, same proxy role) | `https://api.tiingo.com/tiingo/daily/AAPL/prices` | core_stock_apis | tiingo | ok |
| Listed option surface for delta hedging (SPX only — no crypto) | `https://cdn.cboe.com/api/global/delayed_quotes/options/_SPX.json` | options_surface | cboe | ok |
| Local-gateway option chain (no crypto symbols) | `moomoo://get_option_chain` | options_data | moomoo | gateway |
| Local-gateway market snapshot | `moomoo://get_market_snapshot` | core_stock_apis | moomoo | gateway |
| News flow for crypto / stablecoin events | `https://eodhd.com/api/news` | news_data | eodhd | ok |
| Global news tone | `https://api.gdeltproject.org/api/v2/doc/doc` | news_sentiment | gdelt | fail — HTTP 429 rate_limited |
| Event / prediction-market contracts | `https://gamma-api.polymarket.com/markets` | prediction_markets | polymarket | ok |
| Issuer / ETF disclosure filings | `https://data.sec.gov/submissions/CIK0000320193.json` | sec_filings | sec_edgar | ok |

**Verdict:** 11 of 22 required inputs are `gap`. Every crypto-native price, quote, basis and on-chain record is unserved; what remains is the risk-free curve, macro series, US equity/ETF proxies and news. This category is **blocked on data**, not on models — the full model stack of §2 can be built and unit-tested against local files, but none of it can be calibrated or run live without a crypto venue feed.

## 4. Pitfalls, validation and measurement

- **Model risk is the dominant reported pitfall, and the corpus says so explicitly.** The on-chain study calls its own benchmark "a reference price … not a full structural model of the risk-neutral measure" (arXiv:2512.20190v1); the FSV paper's calibration leaves 3.7–5.8% ARPE residuals and relies on locally-optimal genetic-algorithm fits (arXiv:2403.16006v3); the DeFi paper states its BS premium "does not take into account the decrease in risk and lowered average payoff due to termination" (arXiv:2303.15162v2). Every crypto number in this corpus is a model-conditional number.
- **The "best" model flips with the sample.** FSV-GMRTS/type-I wins in 2020, FSV-ALJD/type-III in 2024 (arXiv:2403.16006v3); the on-chain regime/GARCH parameters differ sharply across BTC and ETH and across regimes (arXiv:2512.20190v1). Do not ship a single frozen crypto calibration; re-estimate and report per-period.
- **Loss/objective choice changes the ranking, and calibration is ill-posed by construction.** Calibrating on a single maturity (or a single strike) is under-determined — the FSV paper fits all strikes and maturities jointly by ARPE precisely to avoid this; the carry paper refuses to average across strikes to keep the series interpretable (arXiv:2403.16006v3, arXiv:2605.29309v1). Report ARPE *plus* maximum relative error, and keep the calibration set disjoint from any evaluation set.
- **Look-ahead and in-sample leakage are easy in every one of these studies.** Volatility must be estimated on data strictly before each option's trade timestamp (the on-chain study uses smoothed regime probabilities as an *ex-post* classification and flags the fixed-$\sigma$ assumption; arXiv:2512.20190v1). The FSV calibration is joint in-sample, so its reported ARPE is not out-of-sample (arXiv:2403.16006v3). The funding design infers intensity-like objects forward under fixed parameters — replicate that discipline (arXiv:2506.08573v1). Never let a maturity bucket's later quotes inform an earlier date-bucket's carry.
- **The empirical baseline contradicts the theory, and that contradiction is the finding.** The funding-rate theorem proves exact price alignment is achievable (arXiv:2506.08573v1); the ETF/futures wedge is persistently +2.5% annual (arXiv:2605.29309v1). Any implementation should carry a friction/segmentation term and be validated against *observed* wedges, not only against no-arbitrage.
- **Validation protocol.** (i) Fourier pricers: check parity $C-P=S-Ke^{-r\tau}$ to machine precision on the fitted CF, and cross-check against a compound-Poisson/Monte-Carlo truncation; (ii) model fit: **Diebold–Mariano** on per-option pricing errors with Newey–West HAC, plus a **Model Confidence Set** at 95% to identify a superior *set* rather than anointing one spec; (iii) regime/GARCH: Ljung–Box and Engle ARCH on standardised residuals, as the on-chain paper does (all $p>0.10$); (iv) threshold regression: report the LR bootstrap $p$-value and re-estimate $\tau$ per model; (v) backtests: walk-forward re-estimation with a strictly causal, expanding window, and report regime-conditioned error.
- **Measurement is fragile where the data are thin.** The on-chain sample has 4,090 trades but two addresses bought ~40% of wBTC contracts (arXiv:2512.20190v1); the stablecoin study has ~13 observations and no HAC correction, so its $p$-values are optimistic (arXiv:2505.12413v1); the DeFi replay covers only 41 months and excludes spiral dynamics, so the 89.82% figure is a per-event upper bound (arXiv:2303.15162v2). Weight conclusions by effective sample size, not raw counts.
- **Practical-metric hygiene.** Carry is reported in *annual percentage points*, not logs (arXiv:2605.29309v1); crypto inverse payoffs are denominated in the underlying, so USD-equivalent values multiply by the spot rate and must not be compared across unit conventions (arXiv:2403.16006v3); the DeFi paper's own numbers mix USD totals with per-position ratios — keep units explicit.

## 5. Recommended first implementation in FinRobot

1. **Crypto option-pricing research harness on a local file adapter (S).** Implement §2.2's parity-form call price and §2.3's BS-with-regime-volatility benchmark behind one `CryptoChainSource` interface whose first implementation reads a CSV/JSON drop; ship the ALJD/GMRTS characteristic functions with the type-I and type-III kernels. Data: a local option-chain file (no served feed), `federal_reserve` `risk_free_curve` for $r$. Value: the whole model stack of this category becomes runnable and testable today, and plugs into a live venue feed the day one is added. Risk: in-sample calibration only; ARPE-style errors must be labelled as such (arXiv:2403.16006v3, arXiv:2512.20190v1).
2. **Put-call-parity implied carry / funding primitive (S).** $F=K+e^{r\tau}(C-P)$, annualise exactly, convert by bitcoin-per-share, and expose the wedge of §2.5 as a reusable function. Data: any option chain file plus `federal_reserve` `risk_free_curve` (ok). Value: the basis/funding measurement every other crypto-derivative idea needs, and the fastest path to a number once a chain exists. Risk: American early exercise and benchmark-timing error; the annualisation convention must be fixed explicitly (arXiv:2605.29309v1).
3. **Perpetual-futures funding-rate design module (M).** Implement $\Phi(s,\gamma,y)$, the 8-hour averaged $\Phi^\delta$, the replicating portfolio $\phi=Z\sigma^{-1}$ and the $\ell$ threshold; validate by Monte-Carlo that a simulated perp price tracks the target $\varphi$ to $O(\sqrt\delta)$. Data: none (synthetic paths) beyond a volatility model. Value: the only exact alignment theorem in the corpus, and it is purely computational. Risk: the $\ell$ bound is conservative and non-optimal; uniqueness depends on $H$ (arXiv:2506.08573v1).
4. **Stablecoin→curve channel monitor (S–M).** Fit the semi-log and threshold regressions of §2.6 with HAC errors and a bootstrap LR test, re-estimating $\tau$ per vintage. Data: `fred` `macro_data` and `federal_reserve` `risk_free_curve` are served (ok); Tether's CRR series (gap) must be loaded from a local file. Value: the only crypto→macro link reachable on served data today, and an input to crypto carry. Risk: tiny sample, no causality, inconsistent published magnitudes — treat as monitoring, not prediction (arXiv:2505.12413v1).
5. **On-chain option-AMM mispricing monitor (M).** Reproduce §2.3's two-step FGLS on an on-chain trade export joined to a daily-return regime/GARCH estimate; report coefficients per standardised unit. Data: on-chain trade records (gap) plus a crypto return history (gap) — both local files. Value: quantifies whether a venue's quotes are systematically cheap, which is the precondition for any AMM-facing strategy. Risk: conditional associations only, and the benchmark's fixed-$\sigma$ assumption breaks across regimes (arXiv:2512.20190v1).
6. **Miqado-style liquidation-replacement simulator (M).** Replay §2.1 on a local liquidation dataset: health-factor trigger, top-up premium, maturity exercise/default, and the collateral-restraint accumulator. Data: Aave/Compound liquidation events and DEX swap logs (gap) plus real post-event price paths (gap). Value: a concrete, measurable DeFi primitive (89.82% reduction target) that also stresses oracle and default assumptions. Risk: BS premium ignores termination; results are per-event and assume no borrower rescue (arXiv:2303.15162v2).
7. **Cross-venue basis monitor for bitcoin (L).** Full §2.5 implementation (IBIT chain + holdings file + CME futures + BRRNY) to track the segmentation wedge over time. Data: four `gap` inputs, all vendor-licensed. Value: the cleanest empirical test of arbitrage limits in crypto. Risk: heaviest data lift and the lowest marginal modelling payoff; defer until items 1–2 have a chain source (arXiv:2605.29309v1).

## Appendix — papers read

| arXiv id | title | year |
|---|---|---|
| 2512.20190v1 | Pricing of wrapped Bitcoin and Ethereum on-chain options | 2025 |
| 2506.08573v1 | Designing funding rates for perpetual futures in cryptocurrency markets | 2025 |
| 2605.29309v1 | Implied ETF Carry Rates and the Limits of Arbitrage in Segmented Bitcoin Markets | 2026 |
| 2403.16006v3 | Crypto Inverse-Power Options and Fractional Stochastic Volatility | 2024 |
| 2303.15162v2 | Mitigating Decentralized Finance Liquidations with Reversible Call Options | 2023 |
| 2505.12413v1 | The Stablecoin Discount: Evidence of Tether's U.S. Treasury Bill Market Share in Lowering Yields | 2025 |
