# Crypto & Digital Economics — learnings from the q-fin.GN corpus

`219` of 3095 corpus papers matched this category (218 with PDFs); this doc is based on a close reading of `6`.

Headline: **this category is economics and plumbing, not a signal library.** Five of the six papers are
surveys, heuristics or event studies; only arXiv:2512.12815v1 is a quantitative time-series study, and
only arXiv:2311.12491v1 yields a checkable boolean decision rule. There is **no formula for expected
return anywhere in the set** — the honest deliverables are (i) a dated-event regime-shift harness for a
tradable crypto ETF, (ii) on-chain transaction classifiers that are computable exactly but need a node,
and (iii) a stability/peg-measurement vocabulary plus a CeFi-vs-DeFi classifier. The category's biggest
gap is data: there is no `crypto` route in `strategies/endpoints.json`, no on-chain provider, and no
stablecoin price feed, so most of §2 is **offline-only** until a provider is added. For crypto as a
*tradable asset class* (reversal, bars, realized-vol roughness, on-chain event studies) the sibling
[`../qfin-st/crypto-assets.md`](../qfin-st/crypto-assets.md) already derives the machinery; this document
stays on how crypto *systems* behave — hedging, forensics, stability mechanisms and regulation.

## 1. What the corpus actually offers

**Hedging properties: the ETF approval is a dated structural break in BTC's correlation structure, not in
its instantaneous beta.**

- Paired pre/post windows of daily adjusted closes (Yahoo Finance; BTC, S&P 500, gold, DXY): pre-event
  2023-10-01 → 2024-01-09 and post-event 2024-01-11 → 2024-04-30 (≈101 vs ≈111 observations). BTC mean
  price 26,328 → 60,503, SD 7,035 → 9,919, mean excess return −0.0008 → +0.0018 (return SD flat at
  ≈0.0322); S&P 500 SD 280 → 182 and return SD 0.0171 → 0.0070; gold 1,880 → 2,214; DXY 104.9 → 104.5,
  SD 3.1 → 0.9 (arXiv:2512.12815v1).
- ADF finds stationary excess returns for all four series (BTC −41.4453, S&P −20.2299, gold −71.0724,
  DXY −71.6057, all p = 0.0000) (arXiv:2512.12815v1).
- Chow test on **pairwise OLS excess-return regressions** at 2024-01-10: only DXY breaks decisively
  (8.7886, p = 0.0002) and gold marginally (2.3225, p = 0.0991); BTC–S&P does **not** (0.1427,
  p = 0.8670). The instantaneous beta to equities did not jump on day one (arXiv:2512.12815v1).
- Chow test on the **rolling-correlation series** breaks everywhere: BTC–S&P 30-day 139.42 and 60-day
  269.30, BTC–gold 30-day 135.96, BTC–DXY 30-day 105.86, all p = 0.0000. The *trend* in the moving
  relationship mutated even though the level regression did not (arXiv:2512.12815v1).
- Bitcoin ARMA-GARCH(1,1)-style volatility equation: $\Omega = 2.4025$ (t = 2.197, p = 0.0281),
  $\alpha_1 = 0.1184$ (t = 1.874, p = 0.0609), $\alpha_2 = 0.1683$ (n.s.), $\beta_1 = 0.1399$ (n.s.),
  $\beta_2 = 0.3563$ (n.s.), i.e. $\alpha_1$ significant and $\beta_1+\beta_2\approx 0.49$ — enough
  clustering to falsify OLS but with weak persistence (arXiv:2512.12815v1).
- Direction of the DCC-GARCH paths: after a short post-approval "dispersion" dip, dynamic correlation
  with the S&P 500 rebounds upward; with gold it drifts mildly down; with DXY it stays negative/negligible
  (arXiv:2512.12815v1). Practical consequence stated by the paper: BTC must be modelled as a high-beta
  risk asset inside VaR and allocation, not as a defensive diversifier.

**On-chain forensics: CoinJoin is detectable by exact structural predicates, per implementation.**

- CoinJoin merges $n$ users' intents into one transaction, $\Delta_{in}=\bigoplus_i \Delta_{i,in}$,
  $\Delta_{out}=\bigoplus_i \Delta_{i,out}$, deliberately breaking the common-input-ownership heuristic;
  detection must therefore be implementation-specific (JoinMarket, Wasabi 1.0 / 1.1 / 2.0, Whirlpool)
  (arXiv:2311.12491v1).
- Detection conditions are necessary (not sufficient) boolean conjunctions over output-value multisets,
  input/output script counts and, for Wasabi, a 0.1 BTC denomination band. Published parameters used in
  the scan: Wasabi 2.0 `a_max = 10`, target inputs `p = 50`, `v_min = 5000` satoshis; Whirlpool Tx0
  `a_max = 70`, fee-band `η1 = 0.5`, `η2 = 3`, surplus `ε_min = 100`, `ε_max = 100000` satoshis;
  Whirlpool mix rounds are exactly 5-input / 5-output. Samourai pool denominations and fees:
  (0.001, 0.00005), (0.01, 0.0005), (0.05, 0.00175), (0.5, 0.0175) BTC (arXiv:2311.12491v1).
- Validation is *event alignment*, not precision/recall: multi-denomination Wasabi detections spike at
  the 1.1 release and fall at the 2.0 release; Whirlpool Tx0 and mix detections both start at block
  ≈560,000; Wasabi 2.0 shows a known false-positive cluster between blocks 375,000 and 400,000; the
  JoinMarket predicate detects transactions dated *before* its release, so it is a proxy for other
  protocols (arXiv:2311.12491v1). No accuracy numbers are reported for any heuristic.
- Coverage: the full Bitcoin chain from genesis to **block 760,000**, parsed from a self-hosted Bitcoin
  Core full node's `blk*.dat` files (arXiv:2311.12491v1).

**Stability mechanisms: reserve-backed pegs are tight to ±1 cent; algorithmic supply adjustment is not.**

- Taxonomy of three classes — fiat/asset-backed, crypto-collateralized, algorithmic (plus hybrids)
  (arXiv:2103.01340v1); measured peg behaviour Jan 2020 → May 2021: USDT and USDC stay within
  $[0.99,1.01]$, DAI is looser but stabilising from Jan 2021, AMPL ranges $0.50–$3.83, ESD trends to
  ≈$0.1 (arXiv:2106.08157v2).
- Reserve mechanism arithmetic: authority mints against collateral, any holder may burn 1 unit for the
  pegged value; deviations are arbitraged because buying below \$1 and redeeming (or minting above \$1)
  is profitable — hence the $0.99–1.01 band (arXiv:2106.08157v2).
- Crypto-collateralized arithmetic: a Collateralized Debt Position must be **1.5× over-collateralized**
  (collateral ≥ 150% of debt) else it is liquidated; equivalently 150 units of collateral can mint at most
  100 units of stablecoin — the stated capital-inefficiency of the design (arXiv:2106.08157v2,
  arXiv:2103.01340v1).
- The March 2020 stress test: ETH fell >30% in 24h, many Dai vaults became under-collateralized, auctions
  were won by zero-bidders, and the protocol ended with a **shortfall > 5.4M DAI**, recapitalised by
  auctioning newly minted MKR (arXiv:2103.01340v1).
- Yields (the economic pull of DeFi): CeFi USD bank ≈0.01%, DeFi >8%, Dai Savings Rate 0.01%, DAI on
  Compound ≈3.18% and on Aave ≈5.65%, against a US 10-year yield of 1.623% (arXiv:2106.08157v2).
- CeFi/DeFi money-supply contrast: Ethereum inflation ≈4% versus US M1 +≈250% in 2020 (the paper reads
  the former as a monetary-mass analogue) (arXiv:2106.08157v2).

**Censorship plumbing: "DeFi" assets can be centrally frozen, and that is a systemic risk to composable
protocols.**

- USDT's contract blacklists addresses and can zero a balance; USDC has the same capability. Observed:
  **449 USDT accounts blacklisted (8 later removed) with >43.97M USDT destroyed**, and 8 USDC accounts
  blacklisted, with no overlap between the two lists (arXiv:2106.08157v2). A later survey records **420
  blacklisted USDC wallets** (Centre, 2022) and a table showing Tether, USDC, PAX and BUSD issuers can
  pause transfers and recover funds, while DAI cannot (arXiv:2304.01918v1).
- Because liquidity pools hold blacklistable tokens, a freeze on a pool address can force a **DeFi "bank
  run"** in which exiting LPs receive progressively worse rates from the pool's pricing formula, so the
  last to exit bears the loss — no circuit breaker intervenes (arXiv:2106.08157v2).
- Attack-loss magnitudes that define the risk budget: DeFi smart-contract vulnerabilities ≥128M USD
  cumulative (Lendf.Me reentrancy 25M USD in Apr 2020; Uranium Finance 57M USD in Apr 2021); oracle and
  composability attacks (Value DeFi 740M USD, Nov 2020; PancakeBunny 45M USD); flash loans (which need no
  collateral because the transaction is atomic) enabled >100M USD of 2020 losses (arXiv:2106.08157v2).
  The survey also cites the Harvest Finance pool exploit at 20M USD, elsewhere 24M USD
  (arXiv:2304.01918v1).
- CeFi baseline for comparison: the JPMorgan data breach exposed ~83M customer accounts (76M households)
  (arXiv:2304.01918v1).

**Regulation is descriptive policy, not a quantitative model — and one assigned paper supplies no
formulas at all.**

- arXiv:2304.01918v1 (Decentralized Finance) is a **broad introductory survey written in Turkish** with no
  formulas and no estimator; its usable outputs are a definitional CeFi/DeFi comparison table, the
  stablecoin-compliance table above, and DeFi scale statistics (DefiLlama: 1,445 projects with TVL
  \$39.52B on 2023-01-04; DEX share of DeFi volume >60% in Q2 2020; stablecoin market capitalisation
  >\$10B in Q2 2020). It is retained for the classification vocabulary, not for any computable quantity.
- arXiv:2407.01532v1 (Regulating Cryptocurrency and DeFi for an Inclusive Economy) is a 5-page policy
  paper: it states the crypto/DeFi market is expected to exceed \$39B by 2025, enumerates six
  regulatory challenges (KYC/AML enforcement, tax compliance, financial crime/fraud, consumer protection,
  irreversible transactions, international coordination, rapid technological change), and documents
  India's path — the 2018 RBI circular barring banks from crypto services, its 2020 reversal by the
  Supreme Court, the 2019 draft "Banning of Cryptocurrency" bill, and the June 2023 RBI framing of three
  policy options: **ban, containment, or regulation**. No estimator, no dataset.
- arXiv:2106.08157v2 contributes the only *operational* legal artefact: a 3-question CeFi/DeFi decision
  tree, applied to conclude that reserve-backed stablecoins such as USDC/USDT are **centrally governed
  DeFi**, not pure DeFi.

## 2. Implementable formulas & algorithms

### 2.1 Dated-event regime-shift harness (rolling correlation + Chow + DCC-GARCH)

**Purpose.** Test whether a dated, exogenous event (a spot-ETF listing, a protocol upgrade, a regulatory
ruling) changed the *relationship* between a crypto asset and control assets — the one reusable
quantitative construction in this category (arXiv:2512.12815v1). This generalises the dated-event
template already derived for on-chain upgrades in
[`../qfin-st/crypto-assets.md`](../qfin-st/crypto-assets.md).

**Formula.** Forward rolling correlation over window $N$:
$$\rho_{xy,t}=\frac{\sum_{i=t-N+1}^{t}(x_i-\bar x)(y_i-\bar y)}
{\sqrt{\sum_{i=t-N+1}^{t}(x_i-\bar x)^2}\sqrt{\sum_{i=t-N+1}^{t}(y_i-\bar y)^2}}$$
Chow statistic for a break at $t^\*$ in $y=\alpha+\beta x+\epsilon$ with $k$ parameters per regime:
$$F=\frac{\big(\mathrm{RSS}_{\rm pooled}-(\mathrm{RSS}_1+\mathrm{RSS}_2)\big)/k}
{(\mathrm{RSS}_1+\mathrm{RSS}_2)/(N_1+N_2-2k)}$$
DCC-GARCH: standardise with univariate GARCH(1,1) residuals $\epsilon_t$, then
$$R_t=\mathrm{diag}(Q_t)^{-1/2}\,Q_t\,\mathrm{diag}(Q_t)^{-1/2},\qquad
Q_t=(1-a-b)\bar Q+a\,\epsilon_{t-1}\epsilon_{t-1}^{\top}+b\,Q_{t-1}$$
which isolates correlation dynamics from volatility spikes that a raw rolling correlation conflates.

**Required inputs.** Daily closes for the crypto asset and each control (equity index, gold, dollar
index); a *pre-specified* event date; aligned, stationary return series.

**Parameters & defaults.** Windows $N\in\{30,60\}$ days; break date fixed at the event, not fitted;
returns from adjusted closes, ADF-tested first; report the Chow test on both the return regression and
the rolling-correlation series (the paper's own two-layer design).

**Observed effect sizes.** Return-regression: BTC–S&P $F=0.1427$ (p=0.8670, no break), BTC–gold 2.3225
(p=0.0991), BTC–DXY 8.7886 (p=0.0002). Rolling-correlation: 139.42 / 269.30 (BTC–S&P 30/60d), 135.96
(BTC–gold), 105.86 (BTC–DXY), all p=0.0000; BTC GARCH $\alpha_1=0.1184$, $\beta_1+\beta_2\approx0.49$
(arXiv:2512.12815v1).

**Failure modes.** (i) The two windows are ~100 daily observations each — the Chow *level* test has
little power and the paper's own headline "correlation increased" rests on the DCC path, whose
coefficients are individually insignificant except $\alpha_1$; treat the result as a regime *descriptor*,
not a significance claim. (ii) The event date is not exogenous to price (the approval was anticipated
from late 2023), so the pre-window already prices it in — a classic event-study leakage. (iii) Four
assets of different volatility regimes give four correlated break tests; no multiple-testing correction
is applied, so a single significant $F$ should not be read alone. (iv) DCC needs a long, homoskedastic
sample; with ≈210 observations the $a,b$ are weakly pinned, so the smoothed path is a filter output, not
an estimate.

### 2.2 CoinJoin transaction detection (per-implementation structural predicates)

**Purpose.** Label Bitcoin transactions produced by JoinMarket, Wasabi 1.0/1.1/2.0 and Whirlpool so that
downstream chain analysis (taint, flow, crime detection) is not confounded by pooled inputs, and so that
privacy-adoption volume can be measured (arXiv:2311.12491v1).

**Formula.** Let $n_{\rm scripts,in}$ / $n_{\rm scripts,out}$ be the counts of distinct input / output
locking scripts, $\Delta_{in},\Delta_{out}$ the value multisets, and for a denomination $d$ let
$\mathrm{cnt}(v\!\in\!S)=|\{(p,v)\in\Delta_{out}:v\in S\}|$. Estimated participant count
$n=\max_{v'\in\mathbb N}\mathrm{cnt}(v=v')$. The five predicates:

*JoinMarket:*
$$\frac{|\Delta_{out}|}{2}\le n,\qquad 3\le n\le n_{\rm scripts,in},\qquad |\Delta_{out}|=n_{\rm scripts,out}$$

*Wasabi 1.0* (base denomination $d\approx0.1$ BTC, band $0.1-\epsilon\le d\le0.1+\epsilon$; let
$a_{\max}$ bound inputs per participant):
$$n\le n_{\rm scripts,in}\le|\Delta_{in}|\le a_{\max}\,n,\qquad
\frac{|\Delta_{out}|-1}{2}\le n,\qquad |\Delta_{out}|=n_{\rm scripts,out},\qquad
\hat d=\arg\min_{d'\in D}|d'-0.1|$$

*Wasabi 1.1* (mixing levels $2^i d$, $i=0..L$; bounds $\alpha_i=2^i(0.1-\epsilon)$,
$\beta_i=2^i(0.1+\epsilon)$):
$$\sum_{i=0}^{L}\mathrm{cnt}(\alpha_i\le v\le\beta_i)\;\ge\;|\Delta_{out}|-n-1$$
together with the 1.0 conditions on denomination, input bound and distinct scripts.

*Wasabi 2.0* (fixed denomination set $D$, target inputs $p$, `a_max`, minimum output $v_{\min}$):
$$\mathrm{cnt}(v\in D)\ge\frac{|\Delta_{out}|-1}{2},\quad
|\Delta_{in}|\ge p,\quad
\mathrm{cnt}(v\in D)\ge\frac{|\Delta_{in}|}{a_{\max}},\quad
\min_{v\in\Delta_{in}} v\ge v_{\min},\quad
n_{\rm scripts,out}=|\Delta_{out}|$$

*Whirlpool* (pools $P=\{(d,f)\}$; Tx0 conversion then 5-party mix). Tx0:
$$\mathrm{cnt}(v=d+\epsilon)\ge|\Delta_{out}|-3,\quad \mathrm{cnt}(v=d+\epsilon)\ge1,\quad
\mathrm{cnt}(v=0)=1,\quad \mathrm{cnt}(\eta_1 f\le v\le\eta_2 f)=1,\quad
\mathrm{cnt}(v=d+\epsilon)\le a_{\max},\quad \epsilon_{\min}\le\epsilon\le\epsilon_{\max}$$
Mix round:
$$|\Delta_{in}|=n_{\rm scripts,in}=n_{\rm scripts,out}=|\Delta_{out}|=5,\quad
\mathrm{cnt}(v=d)=5,\quad \mathrm{cnt}_{in}(v\in[d,d+\epsilon_{\max}])=5,\quad
1\le \mathrm{cnt}_{in}(v>d)\le4$$
with $(\hat d,\hat f)=\arg\min_{(d,f)\in P,\,d\le\tilde d}|d-\tilde d|$ for the pool identification.

**Required inputs.** Every transaction's input/output values and script (pubkey) identifiers, plus the
block index — a raw Bitcoin block archive. Nothing in the current data layer serves this.

**Parameters & defaults.** Wasabi 2.0: $a_{\max}=10$, $p=50$, $v_{\min}=5000$ sats. Whirlpool Tx0:
$a_{\max}=70$, $\eta_1=0.5$, $\eta_2=3$, $\epsilon_{\min}=100$, $\epsilon_{\max}=100000$ sats. Denomination
band for Wasabi 1.x: $\approx0.1$ BTC with a small $\epsilon$ that shrinks over rounds.

**Observed effect sizes.** No precision/recall is reported. The only validations are: detection spikes
aligned to software releases (Wasabi 1.1 multi-denomination, its decline at 2.0; Whirlpool from block
≈560,000), and a known false-positive cluster (Wasabi 2.0, blocks 375,000–400,000). Coverage: genesis
→ block 760,000 (arXiv:2311.12491v1).

**Failure modes.** (i) Conditions are *necessary*, so false negatives are expected to be low but false
positives are the binding risk — the JoinMarket form is deliberately broad and absorbs other protocols,
so do not read its count as JoinMarket volume. (ii) Wasabi 1.0's predicate is a subset of 1.1's, so the
two must be distinguished as single- vs multi-denomination, not by separate predicates. (iii) The output
must be treated as a labelled class for *analysis*, never as proof of intent or wrongdoing. (iv) Any
parameter drift (wasabi versions, Whirlpool fee changes, coupon system) silently reclassifies traffic;
the paper relaxes the fee equality to a band precisely for this reason.

### 2.3 CeFi/DeFi classification decision tree

**Purpose.** Classify a financial product or service into CeFi, hybrid, centrally governed DeFi, or pure
DeFi — a governance *label* that decides which risk mechanisms (custody, censorship, blacklist exposure)
apply (arXiv:2106.08157v2).

**Formula** (three sequential boolean questions on the service, not on the asset):

$$S=\begin{cases}\text{CeFi} & \text{if the user does \emph{not} retain custody/control of the assets}\\
\text{hybrid / CeFi-intermediated} & \text{if some entity can unilaterally censor a transaction}\\
\text{centrally governed DeFi} & \text{if some entity can unilaterally stop/censor the protocol}\\
\text{pure DeFi} & \text{otherwise}\end{cases}$$

**Required inputs.** Contract/issuer sources: whether the asset is non-custodial; whether a single party
can blacklist, freeze, pause, or upgrade the contract; whether any party can halt protocol execution.
For ERC-20 assets these are readable from the bytecode/source (e.g. `addBlackList`, `whenNotPaused`,
`destroyBlackFunds` in the USDT listing shown by the paper).

**Parameters & defaults.** None; the classification is deterministic given the answers. Practical
default from the paper: reserve-backed USD stablecoins are "centrally governed DeFi"; DAI's Maker
governance can shut down the system through Emergency Shutdown, so it is not unqualified pure DeFi
either.

**Observed effect sizes.** Applied to USDT (449 blacklisted addresses, >43.97M USDT destroyed) and USDC
(8 blacklisted addresses; 420 by 2022 in arXiv:2304.01918v1); the two lists never overlap
(arXiv:2106.08157v2, arXiv:2304.01918v1).

**Failure modes.** (i) The tree classifies *today's* control surface; an upgradeable proxy can change the
label, so re-run it on every implementation change. (ii) It does not price the risk — use it to *filter*
a pool's asset list, then apply 2.4 for sizing. (iii) Legal classification (security/commodity/money) is
orthogonal and unsettled (arXiv:2103.01340v1, arXiv:2407.01532v1).

### 2.4 Peg-deviation and collateral-invariant measurement for stablecoins

**Purpose.** Two cheap, continuous monitors for whether a stablecoin's stability mechanism is holding:
the peg deviation (all mechanisms) and the collateralisation ratio versus the liquidation threshold
(crypto-collateralized mechanisms) (arXiv:2103.01340v1, arXiv:2106.08157v2).

**Formula.** For target price $p^\*=1$ and bar/high-frequency market price $p_t$:
$$\text{peg deviation } \delta_t=\frac{p_t-p^\*}{p^\*},\qquad
\text{rolling breach rate } \beta_W=\frac{1}{W}\sum_{t\in W}\mathbf 1\{|p_t-p^\*|>\tau\}$$
For a CDP/vault holding collateral value $C$ against debt $D$, with liquidation ratio $r_L$ and
minting ceiling implied by $r_L$:
$$\text{CR}=\frac{C}{D},\qquad \text{liquidatable iff } \mathrm{CR}<r_L,\qquad
\text{max minted } D_{\max}=\frac{C}{r_L}$$
Mechanism response rules (sign conventions to encode, not to fit): for reserve-backed coins, mint above
the peg and allow burn-to-redeem at par; for collateralised coins, raise the **stability fee** to push
holders to close vaults (supply down, price up) and lower it to expand supply; raise/lower the **savings
rate (DSR)** symmetrically to move demand (arXiv:2103.01340v1). For rebasing algorithmic coins, expand
supply when $p>p^\*+\theta$ and contract when $p<p^\*-\theta$ (arXiv:2103.01340v1).

**Required inputs.** High-frequency/ daily stablecoin mid price (or DEX pool price), and for
crypto-collateralized coins the collateral mix, collateral price, outstanding debt and the protocol's
liquidation ratio and penalty.

**Parameters & defaults.** Reported regimes: USDT/USDC $|p-1|\le0.01$ continuously over Jan-2020 →
May-2021; DAI looser, tightening from Jan-2021; AMPL $0.50–3.83; ESD ≈$0.1. Liquidation ratio example
$r_L=1.5$ (150% over-collateralisation). Suggested breach threshold $\tau=0.01$ on $p$, matching the
observed reserve-coin band (arXiv:2106.08157v2, arXiv:2103.01340v1).

**Observed effect sizes.** The March-2020 crash produced >5.4M DAI of protocol shortfall despite the
collateral machinery operating as designed; the recapitalisation came from MKR debt auctions, i.e. from
token holders, not reserves (arXiv:2103.01340v1).

**Failure modes.** (i) A stable price is not evidence of solvency: the reserve composition and audit are
unobservable from price alone (Tether's backing transparency is explicitly flagged) — a peg monitor can
sit at \$1.00 while the backing is impaired (arXiv:2103.01340v1). (ii) For collateralised coins the
binding risk is collateral *correlation* (ETH and WBTC fall together), so a single-asset CR is optimistic
(arXiv:2103.01340v1). (iii) Rebasing coins break the "price stability" framing altogether — AMPL's
supply changes, not its price target (arXiv:2103.01340v1). (iv) Reserve-backed coins carry the blacklist
risk from 2.3 that a peg monitor cannot see.

### 2.5 Censorship/blacklist exposure filter for DeFi pools

**Purpose.** Quantify the share of a lending/AMM pool's value locked in blacklistable tokens, as a
governance risk score (arXiv:2106.08157v2, arXiv:2304.01918v1).

**Formula.** With pool asset weights $w_i$ and per-asset label $\mathrm{bl}_i\in\{0,1\}$ from 2.3:
$$\mathrm{BLR}=\sum_i w_i\,\mathrm{bl}_i,\qquad
\text{exit-penalty proxy } \text{SE}=\mathrm{BLR}\times \text{slippage curve of the pool pricing formula}$$
The DeFi bank-run mechanism is that a freeze on a pool address forces holders of the *other* assets out of
a pool whose pricing formula penalises movement away from equilibrium, so the loss materialises through
$\text{SE}$ rather than through default.

**Required inputs.** Pool composition and weights (LP token supply, asset balances), the per-token
blacklist capability flag, and the pool's invariant/pricing function.

**Parameters & defaults.** Binary $\mathrm{bl}$ from the issuer-capability table: Tether, USDC, PAX, BUSD
→ 1; DAI → 0 (arXiv:2304.01918v1). Report $\mathrm{BLR}$ per pool and in aggregate.

**Observed effect sizes.** Issuer intervention is empirically material, not hypothetical: 449 USDT and
8 USDC addresses blacklisted with >43.97M USDT destroyed (arXiv:2106.08157v2).

**Failure modes.** (i) The score is a governance-risk indicator, not a probability of loss; there is no
calibrated event rate. (ii) It cannot see the pool's own contract risk (≥128M USD of cumulative
smart-contract losses; oracle manipulations up to 740M USD) (arXiv:2106.08157v2) — track separately.

### 2.6 (Non-)technique: what cannot be built from this corpus

Stated plainly to prevent re-derivation: this category yields **no expected-return model, no volatility
forecast, no risk-premium estimate and no trading signal**. arXiv:2304.01918v1 and arXiv:2407.01532v1 are
surveys/policy; arXiv:2103.01340v1 and arXiv:2106.08157v2 are mechanism catalogues; arXiv:2311.12491v1
is a classifier with no accuracy metrics; arXiv:2512.12815v1 is a four-asset, ~210-observation event
study. Crypto *pricing/volatility* machinery lives in
[`../qfin-st/crypto-assets.md`](../qfin-st/crypto-assets.md) and
[`../qfin-st/volatility-modeling.md`](../qfin-st/volatility-modeling.md).

## 3. Data requirements → available endpoints

Rows below are real entries copied from `strategies/endpoints.json`; the probe status is that file's
`ok`/`code` value. A row whose input no provider serves has `—` for endpoint/category/provider and
**gap** in the status column. `moomoo://` rows are `gateway` (served by the local OpenD process over the
SDK, not live-probed over HTTP).

| Input | Endpoint | Category | Provider | Probe status |
|---|---|---|---|---|
| BTC / crypto daily close (for §2.1, §2.4) | `https://eodhd.com/api/eod/AAPL` | `core_stock_apis` | eodhd | ok (endpoint); **gap** — crypto tickers (`.CC`) not mapped in the adapter, EOD granularity only |
| Crypto/intraday series via generic API | `https://api.twelvedata.com/time_series` | `core_stock_apis` | twelvedata | ok; **gap** — adapter hard-codes `interval=1day`, crypto symbol map absent |
| Equity / ETF control series (S&P 500 proxy, IBIT etc.) | `https://api.tiingo.com/tiingo/daily/AAPL/prices` | `core_stock_apis` | tiingo | ok |
| Prev-close / aggregates for controls | `https://api.massive.com/v2/aggs/ticker/AAPL/prev` | `core_stock_apis` | massive | ok |
| Intraday bars / indicators (equity-focused gateway) | `moomoo://get_cur_kline` | `technical_indicators` | moomoo | gateway (not live-probed) |
| Top-of-book snapshot (equities only) | `moomoo://get_market_snapshot` | `core_stock_apis` | moomoo | gateway (not live-probed) |
| Crypto/event news stream (ETF, regulation, hacks) | `https://eodhd.com/api/news` | `news_data` | eodhd | ok |
| News sentiment score (event windows) | `https://eodhd.com/api/sentiments` | `news_sentiment` | eodhd | ok |
| Sentiment, alternative provider | `https://www.alphavantage.co/query` | `news_sentiment` | alpha_vantage | ok |
| Headline / retracted news | `https://api.benzinga.com/api/v2/news` | `news_data` | benzinga | ok |
| Headline news (global) | `https://newsapi.org/v2/everything` | `news_data` | newsapi | ok |
| Global news tone (event windows) | `https://api.gdeltproject.org/api/v2/doc/doc` | `news_sentiment` | gdelt | rate_limited (HTTP 429) |
| Risk-free curve (DeFi/ceFi yield spread, §1) | `https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2026/all` | `risk_free_curve` | federal_reserve | ok |
| Policy-rate / macro series (rate backdrop) | `https://api.stlouisfed.org/fred/series/observations` | `macro_data` | fred | ok |
| Macro indicator list (gateway) | `moomoo://get_macro_indicator_list` | `macro_data` | moomoo | gateway (not live-probed) |
| Prediction-market price on crypto events (ETF, regulation) | `https://gamma-api.polymarket.com/markets` | `prediction_markets` | polymarket | ok |
| Event contract categories (gateway) | `moomoo://get_event_contract_category` | `prediction_markets` | moomoo | gateway (not live-probed) |
| Options surface — equities only | `https://cdn.cboe.com/api/global/delayed_quotes/options/_SPX.json` | `options_surface` | cboe | ok; **gap** for crypto options (SPX-only row) |
| **Gold / DXY price series (§2.1 controls)** | — | — | — | **gap** |
| **Stablecoin market price / peg deviation (§2.4)** | — | — | — | **gap** |
| **Stablecoin supply, reserve attestations, issuer blacklist events (§2.3, §2.5)** | — | — | — | **gap** |
| **Bitcoin block/transaction archive with values + scripts (§2.2)** | — | — | — | **gap** |
| **DeFi pool composition, TVL, protocol losses (§2.5)** | — | — | — | **gap** |
| **Crypto tick trades / L2 order book** | — | — | — | **gap** |
| **Crypto derivatives (funding, basis, DVOL)** | — | — | — | **gap** |

**What each gap costs, quantified.** §2.1 needs a *daily* aligned panel: BTC + S&P 500 + gold + DXY over
≈210 trading days split at one date — three of the four legs are unfetchable today (gold, DXY, crypto),
so only the equity leg plus an equity-traded crypto ETF can be assembled; the study's own power was
already thin at ~100 observations per regime, and losing legs removes the gold/DXY contrast that carries
the "digital gold" conclusion. §2.2 needs the *entire* Bitcoin chain: 760,000 blocks, an order of
\(10^9\) transactions, each with per-output values and scripts — a full-node archive (hundreds of GB),
nothing partial substitutes, because every predicate is a property of a complete value multiset. §2.4
needs stablecoin mid prices at minute-to-daily granularity and, for DAI-type coins, live collateral and
debt state (the March-2020 shortfall of >5.4M DAI was only visible from auction-level data). §2.5 needs
per-pool asset weights plus issuer blacklist events (449 USDT / 8–420 USDC addresses). §2.6-type work
(the sibling crypto-assets doc) additionally needs tick trades and information bars, also **gap**.

## 4. Pitfalls, validation and measurement

- **Anticipation leakage around a dated listing.** The ETF approval was foreseen from late 2023, so a
  "pre" window beginning 2023-10-01 is already post-anticipation; any break attributed to 2024-01-10 is
  a lower bound on the *timing* and may be an upper bound on the *magnitude* (arXiv:2512.12815v1). For
  the intended control assets (gold, DXY) the paper finds the *level* regression stable while the
  *correlation trend* breaks — a reminder that the choice of object (level, rolling correlation,
  conditional correlation) determines the answer. Report all three, as the paper does, and never promote
  the rolling-correlation Chow significance to a statement about beta.
- **Multiple testing across four assets and many windows.** arXiv:2512.12815v1 runs four Chow tests plus
  rolling windows at 30 and 60 days with no correction; with heavy cross-asset correlation the effective
  number of tests is far below the nominal count. Pre-register the asset set and apply a family-wise or
  FDR correction before quoting any single $p$-value; the general lesson is in
  [`../qfin-st/backtest-methodology.md`](../qfin-st/backtest-methodology.md).
- **Thin-sample estimation of DCC parameters.** ≈210 observations for a two-parameter correlation
  dynamic yields individually insignificant $a,b$; a smoothed DCC path is then close to a filter output.
  Report coefficient standard errors next to the path, and prefer the descriptive rolling correlation
  when the sample is short.
- **Heuristic classifiers have no ground truth.** There is no labelled CoinJoin dataset, so
  precision/recall cannot be computed from the paper; the only available validation is *event alignment*
  with software release history and the researcher's manual version study (arXiv:2311.12491v1). Any
  implementation must (i) re-derive predicates from the current source code, not from the paper's
  snapshot, (ii) publish a false-positive audit on known-negative block ranges (the blocks 375,000–400,000
  cluster is a natural test), and (iii) never present a label as evidence of intent.
- **Required-condition logic.** Every CoinJoin predicate is necessary, not sufficient; reported counts are
  upper bounds and the JoinMarket predicate in particular is a *proxy for the residual class*
  (arXiv:2311.12491v1). Report the disagreement set between heuristics instead of a single number.
- **Metric choice for "stability".** A tight peg is measured on price, but the risk is on reserves and
  collateral. Track the peg deviation $\delta_t$ *and* a solvency/reserve signal; the paper's own
  cautionary case is Tether's unverifiable backing sitting behind an apparently \$1 price
  (arXiv:2103.01340v1). Likewise do not use "low volatility" as a synonym for "stable" for rebasing coins
  (AMPL spans \$0.50–3.83 while claiming low volatility) (arXiv:2106.08157v2).
- **Regime dependence and one-date evidence.** Every stress number here comes from March 2020
  (ETH −30%/24h; Dai >5.4M shortfall; Maker liquidation bots failing on gas congestion) or May 2021
  (ETH −40%; Coinbase outage >1h). A peg or collateral monitor tuned on one of those episodes will not
  describe the others; re-run across sub-periods and specify the volatility regime
  (arXiv:2106.08157v2, arXiv:2103.01340v1).
- **Attribution of loss to mechanism.** The attack figures mix root causes: flash loans *facilitate* but do
  not cause (arXiv:2106.08157v2), and oracle manipulation, reentrancy and governance attacks need
  different defences. Do not aggregate them into one "DeFi risk" number without the by-category split
  (smart contract ≥128M USD; oracle/composability up to 740M USD; flash-loan-enabled >100M USD in 2020).
- **Classification is a point-in-time label.** The CeFi/DeFi tree answers questions about present
  control (upgradeable contracts, emergency shutdown, blacklist functions), so it must be recomputed on
  code changes; and the legal category of a token is unsettled and jurisdiction-specific, which no
  classifier resolves (arXiv:2407.01532v1).
- **Policy claims are not measurements.** The "\$39B by 2025" market-size figure in
  arXiv:2407.01532v1 is a forecast cited from a market-research statistic, not an estimated quantity from
  a dataset; it may be quoted as context but never as an input to a model.

## 5. Recommended first implementation in FinRobot

Ordered by value-per-effort against what the data layer can fetch today. Items 1–2 are buildable now;
3–6 are blocked on new providers and should be scoped as offline research.

1. **Dated-event correlation-regime harness (S).** *What:* the §2.1 pipeline — forward rolling
   correlation (30/60d), Chow test on both the return regression and the rolling-correlation series, and
   a DCC-GARCH conditional-correlation path — packaged to accept any (crypto asset, control asset, event
   date) triple. *Data:* `core_stock_apis` (`tiingo`, `massive`, `eodhd`) for the equity/ETF legs today.
   *Passing result:* reproduces the paper's sign pattern on the equity leg (BTC–S&P rolling-correlation
   Chow $F>100$, p<0.01; return-regression Chow insignificant) and emits the pre/post descriptive table
   (BTC 26,328→60,503 etc.) as a regression test. *Risk:* two ~100-observation windows — label the output
   descriptive.
2. **CeFi/DeFi + blacklist-exposure scorer (S).** *What:* the §2.3 decision tree and the §2.5
   `BLR` pool score over a static watchlist, wired to the issuer-capability table (Tether/USDC/PAX/BUSD
   = 1, DAI = 0) and the observed blacklist counts (449 USDT accounts / >43.97M USDT destroyed; 8 USDC
   accounts). *Data:* none live — a maintained JSON manifest beside the doc. *Passing result:* every
   stablecoin in the watchlist gets a classification and a `BLR`; a unit test asserts USDC/USDT →
   "centrally governed DeFi" and DAI → not blacklistable. *Risk:* the manifest decays; timestamp entries.
3. **Stablecoin peg-deviation monitor (M, needs a crypto price feed).** *What:* $\delta_t$ and the
   rolling breach rate $\beta_W$ at $\tau=0.01$ from §2.4, plus the collateral-invariant check
   $\mathrm{CR}<r_L$ where collateral state exists. *Data:* a crypto price provider (CoinGecko/DEX
   subgraph) under a new category — **gap** today; can be prototyped on US-listed stablecoin-adjacent
   instruments only as a stub. *Passing result:* on any historical stablecoin series, USDT/USDC show
   $\beta_W\approx0$ and AMPL shows $|p-1|$ exceeding 1 within the published range. *Risk:* price ≠
   solvency; ship it with the reserve caveat attached.
4. **On-chain CoinJoin classifier (L, blocked on a node).** *What:* the §2.2 predicates as a streaming
   pass over Bitcoin blocks, emitting per-transaction version labels and per-block counts. *Data:*
   a Bitcoin Core full node / public block archive — **gap** (needs a new ingestion path, \~10^9
   transactions, hundreds of GB). *Passing result:* the detection-time profile matches the published
   release alignments (Whirlpool surge at block ≈560,000; Wasabi 1.1-vs-2.0 inversion) and a documented
   false-positive rate below 10% on the known-negative range 375,000–400,000. *Risk:* necessary-only
   predicates over-count; publish upper bounds.
5. **Regulatory/event news index (M).** *What:* a dated event feed (ETF approvals, RBI/SEC rulings,
   protocol exploits) built from the news endpoints, feeding item 1's harness as event dates and
   providing the \$5.4M / 449-address / 740M-USD context flags. *Data:* `news_data` (`eodhd`, `benzinga`,
   `newsapi`) and `news_sentiment` (`eodhd`, `alpha_vantage`); note `gdelt` is `rate_limited` (HTTP 429).
   *Passing result:* the harness's event calendar reproduces the four regulatory datelines documented in
   arXiv:2407.01532v1 (RBI 2018 circular, 2020 Supreme Court reversal, 2019 draft bill, June 2023 RBI
   options). *Risk:* headline dates vs effective dates differ; store both.
6. **Crypto derivatives/yield panel (L, blocked).** *What:* the §1 yield spread (DeFi APY vs US 10-year
   1.623% and CeFi 0.01%) and funding/basis series for a risk-premium view. *Data:* `risk_free_curve`
   (`federal_reserve`) and `macro_data` (`fred`) exist; the DeFi-APY and funding legs are **gap**.
   *Passing result:* a plotted spread with the paper's reference values as fixtures (DSR 0.01%, Compound
   3.18%, Aave 5.65%). *Risk:* DeFi APY is not risk-free; label accordingly.

## Appendix — papers read

| arXiv id | Title | Year |
|---|---|---|
| 2512.12815v1 | The Impact of Bitcoin ETF Approval on Bitcoin's Hedging Properties Against Traditional Assets | 2025 |
| 2311.12491v1 | Heuristics for Detecting CoinJoin Transactions on the Bitcoin Blockchain | 2023 |
| 2304.01918v1 | Decentralized Finance (DeFi) | 2023 |
| 2106.08157v2 | CeFi vs. DeFi — Comparing Centralized to Decentralized Finance | 2021 |
| 2103.01340v1 | Reducing the Volatility of Cryptocurrencies — A Survey of Stablecoins | 2021 |
| 2407.01532v1 | Regulating Cryptocurrency and Decentralized Finance for an Inclusive Economy | 2024 |