---
id: market-structure-regulation
name: Regulatory Event Studies and Market Structure
version: 1.0.0
author: finrobot
domain: market-microstructure
description: 'Regulatory event-study and market-structure design: market-model CAR/CAV around policy events, short-selling-ban DiD with ownership conditioning, and venue-fragmentation simulators. Use when measuring rule effects on spreads, returns, drawdowns, or venue choice.'
triggers:
- regulation
- sec enforcement
- short-selling ban
- difference-in-differences
- market fragmentation
- venue choice
- bid-ask spread
- regulatory capture
- market structure
- ownership conditioning
requires_data:
- input: Daily equity OHLCV (event returns, drawdowns)
  provider: eodhd
  category: core_stock_apis
  status: ok
- input: Daily equity OHLCV (secondary)
  provider: tiingo
  category: core_stock_apis
  status: ok
- input: Previous-session aggregate bars
  provider: massive
  category: core_stock_apis
  status: ok
- input: End-of-day prices (alt venue)
  provider: stockdata
  category: core_stock_apis
  status: ok
- input: Intraday minute bars (event-day dynamics)
  provider: twelvedata
  category: core_stock_apis
  status: ok
- input: Top-of-book bid/ask snapshot (spread proxy)
  provider: moomoo
  category: core_stock_apis
  status: gateway
- input: Institutional ownership (proxy for informed share $m$)
  provider: moomoo
  category: institution_data
  status: gateway
- input: Short interest (constraint intensity)
  provider: moomoo
  category: short_interest
  status: gateway
- input: Capital flow (venue/direction proxy)
  provider: moomoo
  category: capital_flow
  status: gateway
- input: Market breadth (up/down distribution)
  provider: moomoo
  category: market_breadth
  status: gateway
- input: Equity news sentiment (regulatory news tone)
  provider: eodhd
  category: news_sentiment
  status: ok
- input: News volume/tone (GDELT)
  provider: gdelt
  category: news_sentiment
  status: fail
- input: Regulatory headlines
  provider: eodhd
  category: news_data
  status: ok
- input: Macro series (stress, rates, trade)
  provider: fred
  category: macro_data
  status: ok
- input: Macro indicator list
  provider: moomoo
  category: macro_data
  status: gateway
- input: Economic calendar (ban/announcement context)
  provider: moomoo
  category: economic_calendar
  status: gateway
- input: Tradable symbol universe / market lists
  provider: eodhd
  category: exchange_symbols
  status: ok
- input: '**Crypto daily price & volume (SEC event study)**'
  provider: ''
  category: ''
  status: gap
- input: '**Crypto Fear & Greed sentiment index**'
  provider: ''
  category: ''
  status: gap
- input: '**SEC enforcement / EDGAR classification event feed**'
  provider: ''
  category: ''
  status: gap
- input: '**Venue-level / dark-pool trade shares (fragmentation measures)**'
  provider: ''
  category: ''
  status: gap
- input: '**Sovereign CDS spreads (DiD instrument)**'
  provider: ''
  category: ''
  status: gap
- input: '**Lobbying expenditure / OpenSecrets flows (capture $t$)**'
  provider: ''
  category: ''
  status: gap
requires_tools: []
requires_skills: []
compatible_models: []
---

# Regulatory Event Studies and Market Structure

You are an expert empirical market-structure and regulation researcher specializing in event-study and difference-in-differences designs on equity prices, spreads and ownership. You consume dated regulatory event calendars, daily equity OHLCV (eodhd, tiingo), institutional-ownership and short-interest snapshots, top-of-book spread proxies, and macro instruments from the available endpoints, and turn them into CAR/CAV grids, ban DiD panels and fragmentation diagnostics. You never fabricate CARs, spreads, regression coefficients or paper effect sizes, and you refuse to report any estimate whose required feed is a catalog gap (crypto enforcement feeds, venue-level shares, CDS instruments) — those are labelled unrunnable.

> Source: FinRobot strategies corpus review — `strategies/qfin-tr/market-structure-regulation.md`. Literature-derived; not validated on FinRobot's own data.

## Core Principles

- **Fragmentation is an attractor of a two-parameter learning system, not a property of trader
  heterogeneity.** Zero-intelligence traders choose one of $M$ markets by a softmax over reinforcement
  attractions, $A_m(n{+}1)=(1-r)A_m(n)+rS_m(n)$, with memory length $1/r$ and intensity of choice $\beta$.
  With three *identical* (fair) markets the symmetric solution loses stability by a simultaneous three-way
  saddle-node bifurcation: weak fragmentation at $\beta_c=1/0.254$, strong (population-splitting) fragmentation
  at $\beta_c'=1/0.252$, and the residual central peak dies at $1/\beta=0.237$ (arXiv:2012.04103).
- **Coexistence is the *typical* steady state only when venues are nearly indistinguishable.** Strong
  fragmentation survives the $r\to0$ limit across a broad bias range only when the competing venues are
  similar; once a "fair" venue ($\theta=0.5$) is present, fragmentation becomes weak and vanishes as $1/r$
  grows — that venue takes the monopoly (arXiv:2012.04103). In the two-market study strong fragmentation is
  what produces "market coexistence" while weak fragmentation is what produces "single-market dominance";
  the fragmentation region shrinks as the two markets become more different (arXiv:1902.06549).
- **The counting argument bounds how many loyalties a market system can support.** For $C$ trader classes and
  $M$ markets, full strong fragmentation (every class splits across every market) requires
  $M = C(M-1)$, which has an integer solution only at $(C,M)=(2,2)$; relaxing to $k^{(1)}+\dots+k^{(C)}=M+C$
  loyalty groups gives a maximum of $C+M$ groups. For 3 markets × 2 classes that is at most 5 loyalty groups,
  with the sole exception of three symmetric fair markets, which support 6 (arXiv:2012.04103).
- **Multiple equilibria exist and the *strongly* fragmented one is metastable.** In the large-population
  Fokker–Planck limit the steady distribution is $P(\gamma)\propto M_2^{-1}\exp[-f(\gamma)/r]$ with a
  free-energy-like $f(\gamma)=2\int^{\gamma} M_1/M_2\,\mathrm d\gamma'$; a population starting from blank
  attractions reaches the strongly fragmented state first, then decays to a weakly fragmented (coordinated)
  state after a lifetime that grows roughly linearly with population size $N$ (arXiv:1902.06549). Small peaks
  decay exponentially in $1/r$; the strongly fragmented state is the *only* steady state above $r_c\approx0.02$
  (indecisive traders, $p_B=0.55$) or $r_c\approx0.055$ (decisive, $p_B=0.8$).
- **Coordination, not fragmentation, maximises population return.** Average population return is highest in
  coordinated (weakly fragmented) states and *lowest* in uncoordinated states; the strongly fragmented state
  is outperformed even by random choice ($\beta=0$), and for low $\beta$ "history-based" learning is worse
  than random (arXiv:1902.06549). In the two-trader limit the coordination threshold is $\beta_c=4.16$ for
  biases $(\theta,\theta')=(0.3,0.7)$, lowest when both markets are fair (arXiv:1902.06549).
- **Measured SEC rule effects on crypto: a large, persistent negative drift with a reversal signature.**
  A Bitcoin-market-model event study of 48 SEC events that classified named crypto assets as securities (2019–2023)
  finds CARs of $-5.2\%$ $[0,2]$, $-12.2\%$ $[0,6]$, $-13.5\%$ $[0,13]$ and $-17.2\%$ $[0,30]$, against a
  statistically insignificant $-2.4\%$ pre-window; the Binance/Coinbase subsample peaks at $-22.6\%$ $[0,13]$
  after a $+2.5\%$ run-up (arXiv:2412.02452). Cumulative abnormal log-volume falls $4.95$–$10.85$ units
  $[0,30]$ over the full sample.
- **The cross-section is not uniform: volatility, illiquidity and size amplify the drop.** Volatility
  coefficient $\beta_3=-0.765$ on the event day deepening to $-5.151$ $[0,30]$; illiquidity $\beta_4=-1.622$
  on $[0,2]$ with volume effects of $-15.782$ (3-day) and $-30.332$ (13-day); market cap $\beta_1=-0.007$.
  The Alternative.me Fear & Greed index (0–100) moderates but does not reverse the effect (arXiv:2412.02452).
- **Ex-ante abnormal volumes signal informed trading before the announcement.** In the $[-7,-1]$ window,
  higher-volatility ($\beta_3=-8.534$) and more-illiquid ($\beta_4=-0.410$) assets to be named show depressed
  volume with no corresponding price move — strategic waiting or pre-positioning (arXiv:2412.02452).
- **Short-selling bans in Europe 2020: a measured trade-off.** Difference-in-differences across 17 European
  markets (bans in Austria, Belgium, France, Greece, Italy, Spain from 17 Mar 2020, ~2 months) finds spread
  widening up to $13$ bp (low institutional ownership $5$–$8$ bp, insignificant; high institutional ownership
  $22$–$29$ bp), a maximum-drawdown reduction of $310$ bp, and no support for average prices
  (arXiv:2609.08881). The model ties this to the ownership mix: a ban narrows the left tail iff $h_I^2<h_N$
  and widens the spread iff $h_I/h_N>1$, and it leaves the *mean* price unchanged while *lowering the median*.
- **Regulatory capture is a two-player collusion condition, not a behavioural puzzle.** The capture game is
  profitable for both sides iff $B\theta > t > C\theta$ (corporate benefit $B$, influence $\theta$, transfer
  $t$, regulator cost $C=\theta(RA+I)$); the documented ROI benchmark is $\$282.7$M of lobbying for
  $\$62.5$B of tax benefit ($>220{:}1$), i.e. $\approx\$530{,}000$ per legislator, roughly $2$–$3\times$ a
  legislator's salary (arXiv:1310.0057).
- **Off-topic note:** arXiv:2009.08668v1 ("International Trade Finance from the Origins to the Present") is a
  qualitative survey of trade-finance market structure from 1100 AD (bill of exchange, 1537 Antwerp
  negotiability decree, London dominance 1870–1914, the 1930–1935 collapse from 43% to 25% of world exports
  financed by US/UK acceptances, post-1970 decentralisation). It carries no estimable statistic and is
  retained only as background for the "regulatory/structural evolution" half of the scope.

## Methods & Formulas

### 2.1 Adaptive-trader venue-choice simulator (fragmentation onset)
**Purpose.** Decide, for a set of venues and their biases, whether a trader population fragments across them
(coexistence) or consolidates onto one, and locate the onset in the intensity of choice.

**Formula.** Traders hold attractions $A_m$ and pick a venue by multinomial logit
$$P(M=m)=\frac{e^{\beta A_m}}{\sum_{m'}e^{\beta A_{m'}}},\qquad
A_m(n{+}1)=(1-r)A_m(n)+r\,S_m(n)\ \text{if chosen, else }(1-r)A_m(n).$$
Venue $m$ with bias $\theta_m$ sets $\pi_m=\langle a\rangle+\theta_m(\langle b\rangle-\langle a\rangle)$;
buyers score $S=b-\pi_m$, sellers $S=\pi_m-a$. Buyer/seller ratio at venue $m$ satisfies
$f_m=\frac{P^{(1)}(M=m)p_B^{(1)}+P^{(2)}(M=m)p_B^{(2)}}{P^{(1)}(M=m)(1-p_B^{(1)})+P^{(2)}(M=m)(1-p_B^{(2)})}$.

**Required inputs.** Per-venue price bias $\theta_m\in[0,1]$; per-class buy probabilities $p_B^{(c)}$;
learning rate $r$; intensity $\beta$; bid/ask moments.

**Parameters & defaults.** Defaults from the paper: $(\theta_1,\theta_2,\theta_3)=(0.3,0.7,\cdot)$ with
$(p_B^{(1)},p_B^{(2)})=(0.8,0.2)$; $N/2=10{,}000$ traders per class; simulation $r=0.01$. Onset thresholds for
three fair markets: $\beta_c=1/0.254$, $\beta_c'=1/0.252$, kill at $1/\beta=0.237$ (arXiv:2012.04103).

**Observed effect sizes.** Three fair markets fragment into three equal peaks in the $r\to0$ limit; strong
fragmentation appears across $(\theta_2\notin[0.45,0.55])$ for the symmetric pair $(\theta_1,\theta_3)=(0.3,0.7)$;
with a fair venue present, only weak fragmentation survives. Peak appearance order at fixed $\theta_2=0.47$:
profit-max peak for class 1 at $1/\beta=0.246$, for class 2 at $0.228$, then volume-max peaks at $0.207$ and
$0.198$ (arXiv:2012.04103).

**Failure modes.** The multinomial-logit kernel assumes traders see only *their own* realised scores (no
fictitious play) — with two markets this reproduces Nash equilibria only in the $r\to0$ and no-update-of-unchosen
limits. Results are calibration-fragile when venues differ strongly (the strong-fragmentation region shrinks
with market difference), and numerical action-minimisation fails for large $\beta$.

### 2.2 Free-energy / peak-weight classifier (strong vs weak fragmentation)
**Purpose.** Classify a located fragmentation steady state as *strong* (survives long memory) or *weak*
(disappears as memory lengthens), which is the paper's operational definition of "coexistence" vs
"consolidation".

**Formula.** For the attraction difference $\gamma=A_1-A_2$ the Kramers–Moyal expansion gives the
Fokker–Planck equation (rescaled time $t=nr$)
$$\partial_t P(\gamma)=-\partial_\gamma\!\big[M_1(\gamma)P\big]+\frac{r}{2}\partial^2_\gamma\!\big[M_2(\gamma)P\big],
\qquad P(\gamma)\propto \frac{1}{M_2(\gamma)}\exp\!\Big[-\frac{f(\gamma)}{r}\Big],$$
$$f(\gamma)=2\int_0^{\gamma}\frac{M_1(\gamma')}{M_2(\gamma')}\,\mathrm d\gamma',\qquad
\frac{P(\gamma_1)}{P(\gamma_2)}=\frac{M_2(\gamma_2)}{M_2(\gamma_1)}\exp\!\Big[\frac{f(\gamma_2)-f(\gamma_1)}{r}\Big].$$
The drift is $M_1(\gamma)=\sum_m\sum_{\tau\in\{B,S\}}p_\tau T_{\tau m}\,\langle S_{\tau m}\rangle(\gamma)-\gamma$,
with $T_{\tau m}=\min(1,Q_{Bm}/(Q_{Sm}D_m))$ for buy and $T_{Sm}=\min(1,Q_{Sm}D_m/Q_{Bm})$ for sell.

**Required inputs.** Execution probabilities $T_{\tau m}$ (from queues and demand-to-supply ratio $D_m$), mean
and squared returns $\langle S\rangle,\langle S^2\rangle$ per venue and side, and the crossing probabilities
$P(M=m)$.

**Parameters & defaults.** Strong fragmentation iff the two minima are equal, $f(\gamma_1)=f(\gamma_2)$;
otherwise the lower peak is weak and its height decays as $e^{-\Delta f/r}$. Endogenous order parameter
$D_m=p_B/(1-p_B)$ when the modelled population *is* the market.

**Observed effect sizes.** Two unbiased markets give strong fragmentation at equal $D_1=D_{-1}$; increasing
bias detaches the strong-fragmentation lines (arXiv:1902.06549). Decisive buyers ($p_B=0.8$) fragment strongly
only when markets are equal; indecisive traders ($p_B=0.5$) fragment strongly far more broadly.

**Failure modes.** Peak weights require minimising an Onsager–Machlup action (Freidlin–Wentzell) that is
numerically unstable at large $\beta$; the "strong vs weak" distinction is only sharp in the $r\to0$ limit and
becomes a crossover at any finite $r$. Never read *stability* off a phase diagram — multiple steady states are
an existence statement, not a basin-size statement (arXiv:1902.06549).

### 2.3 Binder-cumulant metastability tracker
**Purpose.** Follow, in a finite simulation, which steady state a population actually occupies and when it
escapes a metastable strongly-fragmented state.

**Formula.** With the population distribution of attraction differences $P(\gamma)$,
$$B=1-\frac{\langle \gamma^4\rangle_{P(\gamma)}}{3\langle \gamma^2\rangle^2_{P(\gamma)}}.$$
$B$ near the theoretical strongly-fragmented value indicates coexistence; the decay of $B$ towards the
weakly-fragmented value dates the transition.

**Required inputs.** Time series of per-agent attractions (or per-agent chosen-venue history) from the
simulator in §2.1; population size $N$; learning rate $r$.

**Parameters & defaults.** Reported run: $N=2000$, $(r,1/\beta)=(0.05,0.16)$, $(\theta_1,\theta_2)=(0.3,0.7)$,
$(p_B^{(1)},p_B^{(2)})=(0.8,0.2)$; the strong state survives to $t\approx50$ then switches by $t\approx500$.

**Observed effect sizes.** The strongly fragmented state's lifetime grows approximately linearly with $N$
while the single-agent correlation time is $N$-independent; a systematic initial bias
$|\langle\gamma\rangle|$ large enough makes the dynamics skip the metastable state entirely and consolidate
quickly (arXiv:1902.06549).

**Failure modes.** Requires rescaled-time stationarity (small $r$); at large $r$ the metastable state never
appears and the diagnostic is vacuous; the $N$-dependence is only benchmarked, not fitted, so lifetime
extrapolation to real populations is not calibrated.

### 2.4 Regulatory event-study market model (CAR / CAV)
**Purpose.** Measure the abnormal return and volume response of a named asset to a regulatory action, across
several post-event horizons.

**Formula.** Market model $R_i=\alpha_i+\beta_i R_m+\epsilon_i$ (with Bitcoin log return as $R_m$),
$\mathrm{AR}_{it}=R_{it}-(\hat\alpha_i+\hat\beta_i R_{mt})$, $\mathrm{CAR}_i=\sum_{t\in W}\mathrm{AR}_{it}$;
identically for log volume to give CAV. Expected values estimated on $[-150,-10]$ (140 days).

**Required inputs.** Daily log returns and log volumes of each named asset; a single market-proxy series
(Bitcoin); a dated, validated event list.

**Parameters & defaults.** Estimation window $[-150,-10]$; event windows $[0,2],[0,6],[0,13],[0,30]$; report
both a parametric $t$-test and the Wilcoxon (1945) signed-rank $z$-test. Subsample by shared announcement day
(e.g. the two-day Binance/Coinbase block).

**Observed effect sizes.** Full sample $\mathrm{CAR}[0,30]=-17.2\%$ ($t=-3.61$, $z=-3.39$); sub-sample peak
$-22.6\%$ $[0,13]$; $\mathrm{CAV}[0,30]\in[-10.85,-4.95]$ log units (arXiv:2412.02452).

**Failure modes.** Overlapping events contaminate cross-sectional correlation — enforce non-overlap (hence the
140-day window); pre-announcement windows can carry leakage (the Coinbase-insider subsample shows $-3.9\%$ on
day $-1$); announcement *timing* is only as good as the source list, and a market proxy dominated by one asset
(Bitcoin) mis-specifies assets that decouple from it.

### 2.5 Cross-sectional heterogeneity regression (robust MM estimator)
**Purpose.** Test which asset characteristics amplify or damp the regulatory response, across windows.

**Formula.** $\mathrm{CAR}_i=\beta_0+\beta_1 \mathrm{Size}_i+\beta_2 \mathrm{Age}_i+\beta_3
\mathrm{Vol}_i+\beta_4 \mathrm{Illiq}_i+\beta_5 \mathrm{Sent}_i+\varepsilon_i$, estimated by a robust MM
estimator (Yohai-type) because of clustered outliers, reporting the Renaud–Victoria-Feser robust $R^2$.
Amihud illiquidity $\mathrm{ILLIQ}_i=\operatorname{mean}_t(|R_{it}|/\mathrm{DollarVol}_{it})$.

**Required inputs.** Log market cap (Size), listing age in days, estimation-window mean volatility, Amihud
illiquidity, and a daily sentiment index on the event date.

**Parameters & defaults.** Size $=\log$ market cap; Age in days (scaled $10^{-2}$); Illiquidity scaled
$10^{-6}$; Sentiment $=$ Alternative.me Fear & Greed (0–100).

**Observed effect sizes.** Volatility $\beta_3=-0.765\to-5.151$ ($[0,0]\to[0,30]$); illiquidity
$\beta_4=-1.622$ ($[0,2]$) and $-15.782/-30.332$ for volumes; market cap $\beta_1=-0.007$; the pre-window
$[-7,-1]$ regression on returns is insignificant (arXiv:2412.02452).

**Failure modes.** Sign flips by window and by outcome (returns vs volumes) mean the coefficients are not
invariants — always report the window; the sentiment proxy is exogenous and daily, so it cannot identify
intraday moderation; the $[-7,-1]$ null for returns does not rule out informed trading (volume does move).

### 2.6 Short-selling-ban DiD / IV design with tail-support test
**Purpose.** Estimate the causal effect of a short-selling ban on liquidity and on the left tail of returns,
and condition it on the informed-ownership share.

**Formula.** Difference-in-differences
$$Y_{it}=\alpha+\delta\,(\mathrm{Post}_t\times\mathrm{Treat}_i)+\Gamma X_{it}+\mu_i+\lambda_t+\varepsilon_{it},$$
with $Y$ = average bid–ask spread (liquidity) or maximum drawdown (tail). Instrument the (endogenous) ban
indicator with sovereign CDS spreads and a financial-stress index. Model test: a ban narrows the left tail iff
$$h_I^2<h_N,$$ and widens the spread iff $h_I/h_N>1$, with $h_I/h_N\propto m/(1-m)$ for institutional-ownership
proxy $m$; the mean price is unchanged and the median falls.

**Required inputs.** Stock-level daily close and quote (spread), institutional-ownership fraction, ban dates
and country assignment, macro instruments.

**Parameters & defaults.** Bans from 17 Mar 2020 (Austria, Belgium, France, Greece, Italy, Spain), ~2 months;
17 treated-country markets, 12 control countries; $\pm1$ month pre/post windows; robustness via
market-cap/industry matching, placebo outcomes, longer windows.

**Observed effect sizes.** Spread $+13$ bp overall; $5$–$8$ bp (low ownership, insignificant) vs $22$–$29$ bp
(high ownership); max drawdown $-310$ bp, stronger for low ownership (arXiv:2609.08881).

**Failure modes.** Ban timing is endogenous (`ban decided because markets were falling`) — the IV is doing the
causal work; parallel trends must be shown over the pre-month; spreads measured from daily data understate
intraday liquidity deterioration; the model is static and applies to intermediate horizons, not to the
resolution of the shock.

### 2.7 Regulatory-capture collusion condition
**Purpose.** Score, from a corporate benefit and a regulator cost, whether a regulation is likely to be
captured, and which lever (transparency, influence) would mitigate it.

**Formula.** With degree of influence $\theta=P(F\mid I)-P(F\mid NI)$ and transfer $t$, collusion is the
optimal action for both players iff
$$B\theta>t>C\theta \iff B\theta>t\ \text{and}\ t>C\theta,$$
profit split $\theta(B-C)$: regulator share $(t-\theta C)/[\theta(B-C)]$, corporation
$(\theta B-t)/[\theta(B-C)]$. Regulator cost $C=\theta(RA+I)$ (detection risk $R$, assets at risk $A$,
integrity $I$); effective influence price $C<t<\theta B$.

**Required inputs.** Corporate benefit $B$ (difference in firm value under favourable vs unfavourable
regulation); transfer $t$ (lobbying/contribution expenditure); degree of influence $\theta$ (empirical change
in decision probability); regulator cost components $R,A,I$.

**Parameters & defaults.** Benchmark calibration from the American Jobs Creation Act 2004: $t=\$282.7$M,
$B=\$62.5$B, $B/t\approx221$; $\approx\$530{,}000$ per House member and $\$810{,}000$ per favourable vote;
legislator salary $\$174$–$223.5$k (arXiv:1310.0057).

**Observed effect sizes.** Because $B$ typically exceeds $C$ by orders of magnitude, a tiny $\theta$ suffices
for collusion; reducing $t$ (anti-corruption monitoring) is shown to be a weak lever vs monitoring realised
corporate benefit (arXiv:1310.0057).

**Failure modes.** $B$ and $\theta$ are rarely observable — the model is a screening device, not an estimator;
"integrity" $I$ is a behavioural free parameter that rationalises any outcome; the static two-player structure
ignores repeated-game reputation and multi-regulator competition that the paper itself raises.

## Data Requirements

Provider rows below are real entries in `strategies/endpoints.json`; **gap** means no current provider serves
the input.

| Input | Endpoint | Category | Provider | Probe status |
|---|---|---|---|---|
| Daily equity OHLCV (event returns, drawdowns) | `https://eodhd.com/api/eod/AAPL` | `core_stock_apis` | eodhd | ok |
| Daily equity OHLCV (secondary) | `https://api.tiingo.com/tiingo/daily/AAPL/prices` | `core_stock_apis` | tiingo | ok |
| Previous-session aggregate bars | `https://api.massive.com/v2/aggs/ticker/AAPL/prev` | `core_stock_apis` | massive | ok |
| End-of-day prices (alt venue) | `https://api.stockdata.org/v1/data/eod` | `core_stock_apis` | stockdata | ok |
| Intraday minute bars (event-day dynamics) | `https://api.twelvedata.com/time_series` | `core_stock_apis` | twelvedata | ok |
| Top-of-book bid/ask snapshot (spread proxy) | `moomoo://get_market_snapshot` | `core_stock_apis` | moomoo | gateway (not live-probed) |
| Institutional ownership (proxy for informed share $m$) | `moomoo://get_shareholders_institutional` | `institution_data` | moomoo | gateway (not live-probed) |
| Short interest (constraint intensity) | `moomoo://get_short_interest` | `short_interest` | moomoo | gateway (not live-probed) |
| Capital flow (venue/direction proxy) | `moomoo://get_capital_flow` | `capital_flow` | moomoo | gateway (not live-probed) |
| Market breadth (up/down distribution) | `moomoo://get_rise_fall_distribution` | `market_breadth` | moomoo | gateway (not live-probed) |
| Equity news sentiment (regulatory news tone) | `https://eodhd.com/api/sentiments` | `news_sentiment` | eodhd | ok |
| News volume/tone (GDELT) | `https://api.gdeltproject.org/api/v2/doc/doc` | `news_sentiment` | gdelt | rate_limited |
| Regulatory headlines | `https://eodhd.com/api/news` | `news_data` | eodhd | ok |
| Macro series (stress, rates, trade) | `https://api.stlouisfed.org/fred/series/observations` | `macro_data` | fred | ok |
| Macro indicator list | `moomoo://get_macro_indicator_list` | `macro_data` | moomoo | gateway (not live-probed) |
| Economic calendar (ban/announcement context) | `moomoo://get_economic_calendar` | `economic_calendar` | moomoo | gateway (not live-probed) |
| Tradable symbol universe / market lists | `https://eodhd.com/api/exchange-symbol-list/US` | `exchange_symbols` | eodhd | ok |
| **Crypto daily price & volume (SEC event study)** | — | — | — | **gap** |
| **Crypto Fear & Greed sentiment index** | — | — | — | **gap** |
| **SEC enforcement / EDGAR classification event feed** | — | — | — | **gap** |
| **Venue-level / dark-pool trade shares (fragmentation measures)** | — | — | — | **gap** |
| **Sovereign CDS spreads (DiD instrument)** | — | — | — | **gap** |
| **Lobbying expenditure / OpenSecrets flows (capture $t$)** | — | — | — | **gap** |

**What each gap costs, quantified.** The crypto event study needed a validated 48-event list spanning
2019–2023 plus daily price/volume for ~117 named tokens against a Bitcoin benchmark (arXiv:2412.02452); with
no crypto category in the catalog this block is unrunnable as an *event* study and can only be approximated on
Bitcoin-linked equities. The ban study needed 17 European equity markets, daily quotes and institutional
ownership for ~2 months around 17 Mar 2020, plus CDS/stress instruments (arXiv:2609.08881); the equity and
ownership legs are servable (daily bars, `get_shareholders_institutional`, snapshot spreads) but the
instrument leg is a gap, so identification degrades to plain DiD. The fragmentation work needs no market data
at all — only per-venue aggregate demand-to-supply ratios and the number of venues — but no endpoint reports
*venue-level* or dark-pool shares, so a real-data calibration of §2.1–2.3 is a gap. The capture model needs
$B$ and $t$; lobbying expenditure has no endpoint and $B$ must be reconstructed from filings, which is also a
gap.

In the table above, `gap` inputs are not served by any provider and `derived` inputs are computed locally from the others — treat both as such rather than fetching or inventing them.

## Pitfalls & Validation

- **Look-ahead and leakage.** Regulatory event dates must be scrubbed for pre-announcement information: the
  SEC study finds abnormal *volumes* in $[-7,-1]$ with no price move, and a $+2.5\%$ run-up before the
  Binance/Coinbase block whose reversal is part of the measured CAR (arXiv:2412.02452). An estimator that
  includes a $[-1,0]$ window without checking pre-trends will double-count this reversal as "impact".
- **Event overlap and cross-correlation.** The 48 events include multi-asset days (e.g. 21 Jul 2022 names 9
  tokens; 5–6 Jun 2023 names 12+); the paper forces a 140-day non-overlap estimation window for this reason.
  Reusing the same estimation window across clustered events inflates the effective sample and the $z$-statistics
  (arXiv:2412.02452).
- **Endogenous treatment timing.** Short-selling bans were imposed *because* markets were falling; the ban
  study explicitly warns that the decision and its timing are endogenous and relies on sovereign CDS / stress-index
  instruments, matched samples, a placebo-outcome test and wider windows (arXiv:2609.08881). A naive
  pre/post comparison reproduces the crisis, not the policy.
- **Metric choice changes the sign.** Bans leave the *mean* price unchanged while *lowering the median*
  (arXiv:2609.08881); a study reporting only average returns would conclude "no effect", while the max-drawdown
  metric shows a 310 bp left-tail benefit. Likewise the SEC study's CAR and CAV disagree on short windows but
  agree on $[0,30]$ (arXiv:2412.02452). Fix the metric before the window.
- **Multiple testing across windows and subsamples.** Nine CAR windows × four panels × nine regression
  estimates is a large implicit search space; report the full grid with the non-parametric test and do not
  read significance off the single best window (arXiv:2412.02452). Correct for it.
- **Regime dependence.** Everything empirical here sits in two crisis regimes (COVID-19 March 2020; the
  2022–2023 SEC crypto enforcement wave) — coefficients are regime-averages. The short-selling model is
  explicitly static and intermediate-horizon, so its predictions do not extend to the resolution of the shock
  (arXiv:2609.08881). Re-estimate per regime; never carry a crisis coefficient into calm markets.
- **Finite-memory vs infinite-memory artefact.** The fragmentation/consolidation taxonomy is exact only in the
  $r\to0$ limit; at finite $r$ strongly and weakly fragmented states differ only by a *crossover*, and above
  $r_c\approx0.02$–$0.055$ the strongly fragmented state is the sole attractor (arXiv:1902.06549,
  arXiv:2012.04103). Any simulation claiming "life remains fragmented/consolidated" must state $r$ and $N$;
  the metastable lifetime grows with $N$, so small-$N$ runs systematically under-state coexistence.
- **Phase diagrams are existence, not stability.** Multiple self-consistent order parameters do not imply the
  intermediate solution is stable; stability must be probed with the actual dynamics (Binder cumulant) and with
  different initial conditions (arXiv:1902.06549). Feeding a phase diagram directly into a trading decision is
  a category error.
- **Null tests and measurement.** Use the papers' null designs as gates: a placebo outcome for the ban DiD
  (arXiv:2609.08881); a market-proxy sanity check for the event study (does Bitcoin as $R_m$ explain
  non-crypto-correlated assets?); an action-minimisation benchmark against the closed-form two-market solution
  for the free-energy solver (arXiv:1902.06549). For capture, the observable signature is the *corporate benefit
  realised*, not the transfer paid, because anti-corruption monitoring only raises $t_c$ relative to $t_r$
  (arXiv:1310.0057).

## Recommended Workflow

Ranked by value-per-effort against what the data layer can fetch. Items 1–3 are buildable now; items 4–6 are
simulator-only; items 7–8 are blocked on gaps.

1. **Regulatory event-study harness (equity + sentiment).** *What:* the §2.4 market-model CAR/CAV pipeline with
   a validated event calendar and non-overlap enforcement. *Consumes:* `eodhd.com/api/eod`, `tiingo` daily
   prices, `eodhd.com/api/news`, `eodhd.com/api/sentiments`. *Passing result:* reproduces the documented shape
   on a control event set (negative and deepening CARs, insignificant pre-window); serial-correlation of ARs
   within the window is within tolerance. *Effort:* S.
2. **Short-selling-constraint DiD panel.** *What:* §2.6 estimator with ownership conditioning and a drawdown
   tail metric. *Consumes:* daily bars, `moomoo://get_market_snapshot` (spread proxy),
   `moomoo://get_shareholders_institutional`, `moomoo://get_short_interest`. *Passing result:* recovers the
   qualitative trade-off (spread widening concentrated in high-ownership names; drawdown reduction concentrated
   in low-ownership names) on a historical ban episode; parallel-trend pre-test passes. *Effort:* M.
3. **Cross-sectional heterogeneity regression module.** *What:* §2.5 robust MM estimator with the window ×
   outcome grid and multiple-testing correction. *Consumes:* same as item 1 plus
   `moomoo://get_macro_indicator_list` if a macro control is added. *Passing result:* sign of the volatility and
   illiquidity interactions is stable across the $[0,2]$, $[0,13]$, $[0,30]$ windows; robust $R^2$ reported.
   *Effort:* S.
4. **Adaptive-trader venue-choice simulator.** *What:* §2.1 with $M=2,3$ venues and two buy/sell classes,
   exposed as an offline research tool; see `../qfin-st/market-simulation-agent-models.md` for the shared ABM
   scaffolding. *Consumes:* none live — venue biases and $\beta,r$ are inputs. *Passing result:* reproduces the
   documented onset thresholds (three fair markets fragment at $1/\beta\approx0.25$) and the counting bound
   ($\le C+M$ loyalty groups). *Effort:* M.
5. **Free-energy + Binder metastability diagnostic.** *What:* §2.2 and §2.3 layered on item 4, so any
   fragmentation claim ships with a strong/weak label and a measured metastable lifetime. *Consumes:* item 4
   output. *Passing result:* the diagnostic separates strong from weak states and the lifetime grows with $N$.
   *Effort:* M.
6. **Regulatory-capture screening score.** *What:* §2.7 scorer that ranks pending rule changes by
   $B\theta$ vs $C\theta$ from firm-value deltas and (where available) lobbying expenditure. *Consumes:* daily
   bars for the $B$ leg; lobbying data is a **gap** (input manually pending a provider). *Passing result:*
   reproduces the $\approx220{:}1$ benchmark ROI on the historical lobbying case and flags at least one live
   rule. *Effort:* M.
7. **Crypto regulatory-event study.** *Blocked.* Requires daily crypto price/volume, a Fear & Greed index and
   an enforcement-event feed — all three are gaps. *Passing result once unblocked:* CARs matching
   $[0,2]\approx-5\%$ and deepening through $[0,30]$. *Effort:* M (after feed).
8. **Long-run trade-finance / structural-evolution lens.** *What:* a low-priority descriptive module that
   pulls FRED trade and balance-of-payments series to track the concentration/decentralisation cycles described
   by arXiv:2009.08668v1. *Consumes:* `fred` macro series. *Passing result:* produces a venue-concentration
   series with no trading signal attached; explicitly non-causal. *Effort:* S.

## Output Format

### Regulatory Event-Study Table
| Asset | Window | CAR | CAV (log units) | t-stat | Wilcoxon z | Pre-window check |
|-------|--------|-----|-----------------|--------|------------|------------------|
| ... | [0,2] / [0,13] / [0,30] | ... | ... | ... | ... | [-7,-1] leakage test |

### Short-Selling-Ban DiD Panel
| Outcome | Treated | Control | DiD estimate | Ownership split | Parallel-trend pre-test |
|---------|---------|---------|--------------|-----------------|-------------------------|
| Avg bid-ask spread (bp) | ... | ... | ... | low vs high institutional | ... |
| Max drawdown (bp) | ... | ... | ... | ... | ... |

### Validation Verdict
State the metric fixed before the window (mean vs median; CAR vs CAV), the
non-overlap enforcement used (140-day estimation window), the parallel-trends
pre-test result, whether the sign is stable across [0,2]/[0,13]/[0,30] and
across outcomes, the regime the coefficients belong to, and which arms
(crypto event study, venue-share calibration, CDS-instrumented DiD, capture
scorer) are blocked on catalog gaps rather than estimated.

## References

| arXiv id | Title | Year |
|---|---|---|
| 2012.04103v2 | Fragmentation in trader preferences among multiple markets: Market coexistence versus single market dominance | 2020 |
| 1902.06549v2 | Market fragmentation and market consolidation: Multiple steady states in systems of adaptive traders choosing where to trade | 2019 |
| 2412.02452v1 | Uncertain Regulations, Definite Impacts: The Impact of the US SEC's Regulatory Interventions on Crypto Assets | 2024 |
| 2609.08881v1 | The Double-Edged Sword of Short-Selling Bans | 2026 |
| 1310.0057v1 | Corporations and Regulators: The Game of Influence in Regulatory Capture | 2013 |
| 2009.08668v1 | International Trade Finance from the Origins to the Present: Market Structures, Regulation and Governance | 2020 |
